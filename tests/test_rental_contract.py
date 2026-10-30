from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo import fields


class TestRentalContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Property
        cls.property = cls.env['real.estate.property'].create({
            'building_name': 'Test Tower',
            'address': '1 Test Street',
            'property_type': 'residential',
        })

        # Units
        cls.unit_a = cls.env['real.estate.unit'].create({
            'name': 'Unit A',
            'property_id': cls.property.id,
            'area': 100.0,
            'rooms_count': 2,
            'rent_price': 5000,
            'state': 'vacant',
        })
        cls.unit_b = cls.env['real.estate.unit'].create({
            'name': 'Unit B',
            'property_id': cls.property.id,
            'area': 80.0,
            'rooms_count': 1,
            'rent_price': 3000,
            'state': 'vacant',
        })

        # Tenants
        cls.tenant_1 = cls.env['res.partner'].create({'name': 'Tenant 1'})
        cls.tenant_2 = cls.env['res.partner'].create({'name': 'Tenant 2'})

    def _create_contract(self, unit, tenant, state='draft'):
        return self.env['real.estate.rental.contract'].create({
            'tenant_id': tenant.id,
            'unit_id': unit.id,
            'date_start': '2025-01-01',
            'date_end': '2025-12-31',
            'rent_amount': unit.rent_price,
            'payment_frequency': 'monthly',
            'state': state,
        })

    # ------------------------------------------------------------------ #
    # Test 1: Date validation — end must be after start                   #
    # ------------------------------------------------------------------ #
    def test_01_date_end_after_start(self):
        with self.assertRaises(ValidationError):
            self.env['real.estate.rental.contract'].create({
                'tenant_id': self.tenant_1.id,
                'unit_id': self.unit_a.id,
                'date_start': '2025-12-31',
                'date_end': '2025-01-01',  # before start — should fail
                'rent_amount': 5000,
                'payment_frequency': 'monthly',
                'state': 'draft',
            })

    # ------------------------------------------------------------------ #
    # Test 2: Activating contract marks unit as rented                    #
    # ------------------------------------------------------------------ #
    def test_02_activate_contract_marks_unit_rented(self):
        contract = self._create_contract(self.unit_a, self.tenant_1)
        self.assertEqual(self.unit_a.state, 'vacant')
        contract.action_active()
        self.assertEqual(contract.state, 'active')
        self.assertEqual(self.unit_a.state, 'rented')

    # ------------------------------------------------------------------ #
    # Test 3: Cannot activate second contract on a rented unit            #
    # ------------------------------------------------------------------ #
    def test_03_no_double_active_contract_on_unit(self):
        # Activate first contract
        contract1 = self._create_contract(self.unit_b, self.tenant_1)
        contract1.action_active()
        self.assertEqual(self.unit_b.state, 'rented')

        # Try to activate a second contract on the same unit
        contract2 = self.env['real.estate.rental.contract'].create({
            'tenant_id': self.tenant_2.id,
            'unit_id': self.unit_b.id,
            'date_start': '2025-06-01',
            'date_end': '2026-05-31',
            'rent_amount': 3000,
            'payment_frequency': 'monthly',
            'state': 'draft',
        })
        with self.assertRaises(ValidationError):
            contract2.action_active()

    # ------------------------------------------------------------------ #
    # Test 4: Expiring contract marks unit as vacant                      #
    # ------------------------------------------------------------------ #
    def test_04_expire_contract_marks_unit_vacant(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'Unit C',
            'property_id': self.property.id,
            'area': 60.0,
            'rooms_count': 1,
            'rent_price': 2000,
            'state': 'vacant',
        })
        contract = self._create_contract(unit, self.tenant_1)
        contract.action_active()
        self.assertEqual(unit.state, 'rented')
        contract.action_expire()
        self.assertEqual(contract.state, 'expired')
        self.assertEqual(unit.state, 'vacant')

    # ------------------------------------------------------------------ #
    # Test 5: Cancel contract marks unit as vacant                        #
    # ------------------------------------------------------------------ #
    def test_05_cancel_contract_marks_unit_vacant(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'Unit D',
            'property_id': self.property.id,
            'area': 70.0,
            'rooms_count': 2,
            'rent_price': 4000,
            'state': 'vacant',
        })
        contract = self._create_contract(unit, self.tenant_1)
        contract.action_active()
        self.assertEqual(unit.state, 'rented')
        contract.action_cancel()
        self.assertEqual(contract.state, 'cancelled')
        self.assertEqual(unit.state, 'vacant')

    # ------------------------------------------------------------------ #
    # Test 6: Total contract value computed from payment_ids              #
    # ------------------------------------------------------------------ #
    def test_06_total_contract_value(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'Unit E',
            'property_id': self.property.id,
            'area': 90.0,
            'rooms_count': 3,
            'rent_price': 6000,
            'state': 'vacant',
        })
        contract = self._create_contract(unit, self.tenant_1)
        self.env['real.estate.rental.payment'].create([
            {'contract_id': contract.id, 'due_date': '2025-01-31', 'amount': 6000, 'payment_state': 'paid'},
            {'contract_id': contract.id, 'due_date': '2025-02-28', 'amount': 6000, 'payment_state': 'due'},
            {'contract_id': contract.id, 'due_date': '2025-03-31', 'amount': 6000, 'payment_state': 'overdue'},
        ])
        self.assertEqual(contract.total_contract_value, 18000)

    # ------------------------------------------------------------------ #
    # Test 7: Overlap constraint — same unit, overlapping dates           #
    # ------------------------------------------------------------------ #
    def test_07_overlapping_active_contracts_blocked(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'Unit F',
            'property_id': self.property.id,
            'area': 55.0,
            'rooms_count': 1,
            'rent_price': 2500,
            'state': 'vacant',
        })
        contract1 = self.env['real.estate.rental.contract'].create({
            'tenant_id': self.tenant_1.id,
            'unit_id': unit.id,
            'date_start': '2025-01-01',
            'date_end': '2025-06-30',
            'rent_amount': 2500,
            'payment_frequency': 'monthly',
            'state': 'active',
        })
        # Force mark it as active directly to bypass the unit-rented check
        # so we can test the constrains
        unit.state = 'vacant'
        with self.assertRaises(ValidationError):
            self.env['real.estate.rental.contract'].create({
                'tenant_id': self.tenant_2.id,
                'unit_id': unit.id,
                'date_start': '2025-03-01',
                'date_end': '2025-09-30',
                'rent_amount': 2500,
                'payment_frequency': 'monthly',
                'state': 'active',
            })

    # ------------------------------------------------------------------ #
    # Test 8: Renewal wizard updates contract dates and generates payments #
    # ------------------------------------------------------------------ #
    def test_08_renewal_wizard(self):
        unit = self.env['real.estate.unit'].create({
            'name': 'Unit G',
            'property_id': self.property.id,
            'area': 110.0,
            'rooms_count': 3,
            'rent_price': 7000,
            'state': 'vacant',
        })
        contract = self._create_contract(unit, self.tenant_1)
        contract.action_active()

        wizard = self.env['real.estate.contract.renew.wizard'].with_context(
            active_id=contract.id
        ).create({
            'contract_id': contract.id,
            'new_end_date': '2026-12-31',
            'new_rent_amount': 7500,
            'generate_payments': True,
            'renewal_months': 12,
        })
        wizard.action_confirm_renewal()

        self.assertEqual(contract.date_end, fields.Date.from_string('2026-12-31'))
        self.assertEqual(contract.rent_amount, 7500)
        self.assertTrue(len(contract.payment_ids) > 0, "Renewal should generate payments")

