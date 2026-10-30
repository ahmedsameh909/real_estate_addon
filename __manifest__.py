{
    'name': 'Real Estate Rental',
    'summary': 'Manage properties, units, rental contracts, payments, and reports.',
    'description': """
Real Estate Rental Management System
=====================================
- Manage Properties & Units (Residential, Commercial, Office).
- Track Rental Contracts with automatic sequences and state workflow.
- Payment schedules, due dates tracking, overdue automation.
- PDF Reports: Contract & Tenant Statement.
- Renewal Wizard with payment generation.
- Smart Buttons on res.partner.
- Kanban & Calendar views.
- Automated cron jobs for expiry reminders and overdue marking.
    """,
    'author': 'Ahmed Sameh',
    'category': 'Real Estate',
    'version': '1.0.0',
    'depends': ['base', 'account', 'mail'],

    'data': [
        # 1. Sequences first
        'data/real_estate_sequence.xml',
        
        # 2. Security
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/demo.xml',
        
        # 3. Wizards / Actions referenced in views (MUST load before views)
        'wizard/real_estate_contract_renew_views.xml',
        
        # 4. Core Views
        'views/real_state_property.xml',
        'views/real_state_unit.xml',
        'views/real_state_rental_contract.xml',
        'views/real_state_rental_payment.xml',
        'views/res_partner_views.xml',
        
        # 5. Reports
        'reports/real_estate_reports.xml',
        
        # 6. Automated actions (cron jobs)
        'data/automated_actions.xml',
        
        # 7. Menu always last
        'views/menu.xml',
    ],

  

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}