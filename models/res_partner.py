from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rental_contract_ids = fields.One2many(
        'real.estate.rental.contract',
        'tenant_id',
        string='Rental Contracts'
    )
    active_contract_count = fields.Integer(
        string='Active Contracts',
        compute='_compute_rental_counts'
    )
    rented_unit_count = fields.Integer(
        string='Rented Units',
        compute='_compute_rental_counts'
    )

    @api.depends('rental_contract_ids.state', 'rental_contract_ids.unit_id')
    def _compute_rental_counts(self):
        for partner in self:
            active_contracts = partner.rental_contract_ids.filtered(lambda c: c.state == 'active')
            partner.active_contract_count = len(active_contracts)
            partner.rented_unit_count = len(active_contracts.mapped('unit_id'))

    def action_view_rental_contracts(self):
        self.ensure_one()
        return {
            'name': 'Rental Contracts',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.rental.contract',
            'view_mode': 'list,form,calendar',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
