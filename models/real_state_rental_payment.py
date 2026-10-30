from odoo import api, fields, models, _


class RealEstateRentalPayment(models.Model):
    _name = 'real.estate.rental.payment'
    _description = 'Real Estate Rental Payment'
    _order = 'due_date asc, id asc'

    # 1. علاقة الربط مع العقد الرئيسي
    contract_id = fields.Many2one(
        'real.estate.rental.contract', 
        string='Contract', 
        required=True, 
        ondelete='cascade'
    )
    
    # 2. تاريخ استحقاق القسط
    due_date = fields.Date(
        string='Due Date', 
        required=True
    )

    # 3. فيلد العملة (بياخد العملة من العقد مباشرة عبر Related Field)
    currency_id = fields.Many2one(
        related='contract_id.currency_id', 
        string='Currency', 
        store=True, 
        readonly=True
    )

    # 4. مبلغ القسط
    amount = fields.Monetary(
        string='Payment Amount', 
        currency_field='currency_id', 
        required=True
    )
    
    # 5. حالة الدفع
    payment_state = fields.Selection(
        selection=[
            ('due', 'Due'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        string='Payment Status',
        default='due',
        required=True,
    )

    def _compute_display_name(self):
        for record in self:
            contract_ref = record.contract_id.name if record.contract_id else ""
            date_str = str(record.due_date) if record.due_date else ""
            record.display_name = f"{contract_ref} - {date_str}" if contract_ref and date_str else (contract_ref or date_str or "Payment")

    def action_send_overdue_reminder(self):
        """إرسال تذكير بالدفعة المتأخرة للمستأجر عبر Chatter العقد"""
        for record in self:
            if record.payment_state != 'overdue':
                continue
            
            if record.contract_id and record.contract_id.tenant_id:
                tenant = record.contract_id.tenant_id
                subject = _("Overdue Payment Reminder: %s", record.contract_id.name)
                body = _(
                    "<p>Dear <b>%(tenant_name)s</b>,</p>"
                    "<p>This is a friendly reminder regarding your installment due on <b>%(due_date)s</b> "
                    "for the amount of <b>%(amount)s %(currency)s</b>, which is currently overdue.</p>"
                    "<p>Please process the payment at your earliest convenience.</p>",
                    tenant_name=tenant.name,
                    due_date=record.due_date,
                    amount=record.amount,
                    currency=record.currency_id.symbol or ''
                )
                # تسجيل الرسالة في Chatter العقد
                record.contract_id.message_post(
                    body=body,
                    subject=subject,
                    partner_ids=[tenant.id]
                )