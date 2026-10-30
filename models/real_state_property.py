from odoo import api, fields, models


class RealEstateProperty(models.Model):
    _name = 'real.estate.property'
    _description = 'Real Estate Property'
    _rec_name = 'building_name'

    building_name = fields.Char(string='Building Name', required=True)
    address = fields.Char(string='Address', required=True)
    location = fields.Char(string='Location')  # أو Text حسب احتياجك
    owner_id = fields.Many2one('res.partner', string='Owner', required=True)
    
    type = fields.Selection(
        selection=[
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
            ('office', 'Office'),
        ],
        string='Property Type',
        required=True,
    )
    
    # حقل العلاقات (Many2one inverse field name هو property_id)
    unit_ids = fields.One2many(
        'real.estate.unit', 
        'property_id', 
        string='Units'
    )
    
    unit_count = fields.Integer(
        string='Unit Count',
        compute='_compute_unit_count',
        store=True,
    )

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for record in self:
            record.unit_count = len(record.unit_ids)

    def action_view_units(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Units',
            'res_model': 'real.estate.unit',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }
