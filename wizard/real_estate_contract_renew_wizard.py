from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RealEstateContractRenewWizard(models.TransientModel):
    _name = 'real.estate.contract.renew.wizard'
    _description = 'Renew Rental Contract Wizard'

    contract_id = fields.Many2one(
        'real.estate.rental.contract',
        string='Contract',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    currency_id = fields.Many2one(
        related='contract_id.currency_id',
        string='Currency',
    )
    current_end_date = fields.Date(
        related='contract_id.date_end',
        string='Current End Date',
        readonly=True,
    )
    renewal_months = fields.Integer(
        string='Renewal Duration (Months)',
        default=12,
        required=True,
    )
    new_end_date = fields.Date(
        string='New End Date',
        required=True,
    )
    new_rent_amount = fields.Monetary(
        string='New Monthly Rent',
        currency_field='currency_id',
        required=True,
    )
    generate_payments = fields.Boolean(
        string='Generate Renewal Payment Schedule',
        default=True,
    )

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.new_rent_amount = self.contract_id.rent_amount
            if self.contract_id.date_end:
                self.new_end_date = self.contract_id.date_end + relativedelta(months=self.renewal_months or 12)

    @api.onchange('renewal_months', 'current_end_date')
    def _onchange_renewal_months(self):
        if self.current_end_date and self.renewal_months:
            self.new_end_date = self.current_end_date + relativedelta(months=self.renewal_months)

    def action_confirm_renewal(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            raise UserError(_("No contract selected for renewal."))

        if self.new_end_date <= contract.date_end:
            raise ValidationError(_("New end date must be strictly after current contract end date (%s)!") % contract.date_end)

        old_end_date = contract.date_end
        old_rent = contract.rent_amount

        # Update contract dates and rent
        contract.write({
            'date_end': self.new_end_date,
            'rent_amount': self.new_rent_amount,
            'state': 'active',
        })

        # Generate new payment schedule if requested
        generated_count = 0
        if self.generate_payments:
            months_step = 1
            if contract.payment_frequency == 'quarterly':
                months_step = 3
            elif contract.payment_frequency == 'yearly':
                months_step = 12

            amount_per_period = self.new_rent_amount * months_step
            current_due = old_end_date + relativedelta(days=1)
            
            payments_to_create = []
            while current_due < self.new_end_date:
                payments_to_create.append({
                    'contract_id': contract.id,
                    'due_date': current_due,
                    'amount': amount_per_period,
                    'payment_state': 'due',
                })
                current_due += relativedelta(months=months_step)

            if payments_to_create:
                self.env['real.estate.rental.payment'].create(payments_to_create)
                generated_count = len(payments_to_create)

        # Log professional chatter message
        message_body = _(
            "<p><strong>Contract Successfully Renewed!</strong></p>"
            "<ul>"
            "<li><strong>Previous End Date:</strong> %s</li>"
            "<li><strong>New End Date:</strong> %s</li>"
            "<li><strong>Updated Monthly Rent:</strong> %s %s</li>"
            "<li><strong>New Installments Generated:</strong> %d</li>"
            "</ul>"
        ) % (
            old_end_date,
            self.new_end_date,
            f"{self.new_rent_amount:,.2f}",
            contract.currency_id.symbol or contract.currency_id.name or "",
            generated_count
        )
        contract.message_post(
            body=message_body,
            subject=_("Contract Renewal: %s") % contract.name,
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

        return {'type': 'ir.actions.act_window_close'}
