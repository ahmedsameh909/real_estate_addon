from odoo import _, fields, models
from odoo.exceptions import AccessError


class RealEstateUnit(models.Model):
    _name = 'real.estate.unit'
    _description = 'Real Estate Unit'

    name = fields.Char(string='Unit Number / Reference', required=True)    
    
    property_id = fields.Many2one(
        'real.estate.property', 
        string='Parent Property', 
        required=True, 
        ondelete='cascade'
    )
    area = fields.Float(string='Area (sqm)', digits=(16, 2))
    rooms_count = fields.Integer(string='Rooms Count', default=1)

    state = fields.Selection(
        selection=[
            ('vacant', 'Vacant'),
            ('rented', 'Rented'),
            ('maintenance', 'Under Maintenance'),
        ],
        string='Status',
        default='vacant',
        required=True,
    )

    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        default=lambda self: self.env.company.currency_id,
        readonly=True  # عشان القيمة ما تتغيرش من الشاشة
    )
    
    # سعر الإيجار بالمصري
    rent_price = fields.Monetary(
        string='Suggested Monthly Rent', 
        currency_field='currency_id'
    )

    contract_ids = fields.One2many(
        'real.estate.rental.contract', 
        'unit_id', 
        string='Rental Contracts'
    )

    def write(self, vals):
        if (
            self.env.user.has_group('real_state_addon.group_real_estate_property_manager')
            and not self.env.user.has_group('real_state_addon.group_real_estate_general_manager')
            and set(vals) - {'state'}
        ):
            raise AccessError(_("Property Managers can only update a unit's status."))
        return super().write(vals)
