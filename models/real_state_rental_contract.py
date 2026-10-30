from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class RealEstateRentalContract(models.Model):
    _name = 'real.estate.rental.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Real Estate Rental Contract'
    _order = 'id desc'

    # اسم العقد (بيتولد تلقائيًا من الـ Sequence)
    name = fields.Char(
        string='Contract Reference', 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('New'),
        tracking=True
    )
    
    # المستأجر (مأخوذ من جدول res.partner)
    tenant_id = fields.Many2one(
        'res.partner', 
        string='Tenant', 
        required=True,
        tracking=True
    )
    
    # الوحدة المؤجرة
    unit_id = fields.Many2one(
        'real.estate.unit', 
        string='Rented Unit', 
        required=True,
        tracking=True,
        domain="[('state', '=', 'vacant')]"  # بيظهر فقط الوحدات الفاضية المتاحة للإيجار
    )
    
    # تواريخ العقد
    date_start = fields.Date(
        string='Contract Start Date', 
        required=True, 
        default=fields.Date.context_today,
        tracking=True
    )
    date_end = fields.Date(
        string='Contract End Date', 
        required=True,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )

    rent_amount = fields.Monetary(
        string='Monthly Rent Amount', 
        currency_field='currency_id', 
        required=True,
        tracking=True
    )

    payment_frequency = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        string='Payment Frequency',
        default='monthly',
        required=True,
    )

    # 4. جدول الأقساط/المدفوعات والحالات
    payment_ids = fields.One2many(
        'real.estate.rental.payment', 
        'contract_id', 
        string='Rental Payments'
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('renewing', 'Renewing'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True
    )

    # 5. الحقل المحسوب: إجمالي قيمة العقد
    total_contract_value = fields.Monetary(
        string='Total Contract Value', 
        currency_field='currency_id', 
        compute='_compute_total_contract_value',
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.user.has_group('real_state_addon.group_real_estate_sales_agent')
            and not self.env.user.has_group('real_state_addon.group_real_estate_general_manager')
            and any(vals.get('state', 'draft') != 'draft' for vals in vals_list)
        ):
            raise AccessError(_("Sales agents can only create draft contracts."))

        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.rental.contract'
                ) or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if (
            self.env.user.has_group('real_state_addon.group_real_estate_sales_agent')
            and not self.env.user.has_group('real_state_addon.group_real_estate_general_manager')
        ):
            for record in self:
                if record.state != 'draft':
                    raise AccessError(_("Sales agents can only modify contracts in Draft state."))
        return super().write(vals)


    def action_active(self):
        for record in self:
            if record.unit_id.state == 'rented':
                raise ValidationError(_("Unit '%s' is already marked as rented. Cannot activate another contract on it!") % record.unit_id.name)
            record.write({'state': 'active'})
            if record.unit_id:
                record.unit_id.write({'state': 'rented'})

    def action_renew(self):
        self.write({'state': 'renewing'})

    def action_expire(self):
        for record in self:
            record.write({'state': 'expired'})
            if record.unit_id:
                record.unit_id.write({'state': 'vacant'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            if record.unit_id and record.unit_id.state == 'rented':
                record.unit_id.write({'state': 'vacant'})

    def action_cancel(self):
        if not self.env.user.has_group('real_state_addon.group_real_estate_general_manager'):
            raise AccessError(_("Only General Managers can cancel rental contracts."))
        for record in self:
            record.write({'state': 'cancelled'})
            if record.unit_id and record.unit_id.state == 'rented':
                record.unit_id.write({'state': 'vacant'})

    @api.depends('payment_ids.amount')
    def _compute_total_contract_value(self):
        for record in self:
            record.total_contract_value = sum(record.payment_ids.mapped('amount'))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end and record.date_start and record.date_end <= record.date_start:
                raise ValidationError(_("Contract End Date must be after Start Date!"))

    @api.constrains('unit_id', 'state', 'date_start', 'date_end')
    def _check_unit_active_contract(self):
        for record in self:
            if record.state == 'active' and record.unit_id:
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('unit_id', '=', record.unit_id.id),
                    ('state', '=', 'active'),
                    ('date_start', '<=', record.date_end),
                    ('date_end', '>=', record.date_start),
                ], limit=1)
                if overlapping:
                    raise ValidationError(
                        _("Unit '%s' already has an active overlapping contract (%s)!") %
                        (record.unit_id.name, overlapping.name)
                    )


