from datetime import date, timedelta
import tempfile
import base64

from database import Database, AuditLogger
from services import FinanceService
from gmail_client import GmailClient, GmailUnavailableError
from config import Config

REMINDER_TEMPLATES = {
    "gentle": (
        "Dear {client},\n\n"
        "We hope this message finds you well. This is a friendly reminder that "
        "invoice {invoice_number} for {amount} is due on {due_date}.\n\n"
        "If you have already made the payment, please disregard this notice. "
        "If you have any questions, please don't hesitate to reach out.\n\n"
        "Thank you for your business!\nBest regards,\nFinance Team"
    ),
    "firm": (
        "Dear {client},\n\n"
        "We're writing to remind you that invoice {invoice_number} for {amount} "
        "was due on {due_date} and remains outstanding.\n\n"
        "We kindly request that you arrange payment at your earliest convenience. "
        "Please let us know if there are any issues preventing payment.\n\n"
        "Best regards,\nFinance Team"
    ),
    "final": (
        "Dear {client},\n\n"
        "This is a final reminder regarding invoice {invoice_number} for {amount}, "
        "which is now significantly past its due date of {due_date}.\n\n"
        "Immediate payment is requested. Continued non-payment may result in "
        "referral to a collections agency.\n\n"
        "Regards,\nFinance Team"
    ),
    "legal": (
        "Dear {client},\n\n"
        "FINAL NOTICE: Despite previous reminders, invoice {invoice_number} for "
        "{amount} (due {due_date}) remains unpaid.\n\n"
        "This matter is being escalated and may be referred for legal action if "
        "not resolved within 7 days.\n\n"
        "Finance Team / Legal Department"
    ),
}

LEVELS = ["gentle", "firm", "final", "legal"]
LEVEL_DUE_INTERVAL = {"gentle": 14, "firm": 21, "final": 30, "legal": 45}


class ReminderEngine:
    def __init__(self, db: Database, gmail: GmailClient = None):
        self.db = db
        self.finance = FinanceService(db)
        self.audit = AuditLogger(db)
        self.gmail = gmail
        self.business_owner = Config.BUSINESS_OWNER_EMAIL

    def due_reminders(self, as_of: date = None) -> list:
        """Determine which invoices need which reminder level today."""
        as_of = as_of or date.today()
        invoices = self.finance.invoices_outstanding()
        due = []
        for inv in invoices:
            due_date = date.fromisoformat(inv["due_date"])
            days_overdue = (as_of - due_date).days
            level = None
            if days_overdue < -7:
                continue  # not yet close to due
            if due_date >= as_of:
                # gentle reminder before due (within 7 days)
                if (due_date - as_of).days <= 7:
                    level = "gentle"
            elif 0 <= days_overdue < 7:
                level = "firm"
            elif 7 <= days_overdue < 30:
                level = "final"
            elif days_overdue >= 30:
                level = "legal"

            if not level:
                continue

            # Check if we already sent this level
            sent = self.db.query_one(
                "SELECT id FROM reminders WHERE invoice_id = ? AND level = ? "
                "AND status = 'sent'",
                (inv["id"], level),
            )
            if sent:
                continue

            customer = None
            if inv["customer_id"]:
                customer = self.finance.get_customer(inv["customer_id"])

            due.append({
                "invoice": inv,
                "customer": customer,
                "level": level,
                "days_overdue": days_overdue,
            })
        return due

    def _render(self, level: str, data: dict) -> (str, str):
        template = REMINDER_TEMPLATES[level]
        from_address = data.get("owner_email") or self.business_owner
        subject = (
            f"Payment Reminder ({level.title()}) - Invoice {data['invoice_number']}"
        )
        body = template.format(**data)
        return subject, body

    def send_reminders(self, dry_run: bool = False, as_of: date = None) -> list:
        """Send all due reminders. Returns list of sent reminders."""
        if not Config.REMINDER_ENABLED and not dry_run:
            return []
        due = self.due_reminders(as_of)
        results = []
        for item in due:
            inv = item["invoice"]
            customer = item["customer"]
            client_name = customer["name"] if customer else inv.get("invoice_number")
            recipient = customer["email"] if customer else self.business_owner

            data = {
                "client": client_name,
                "invoice_number": inv["invoice_number"],
                "amount": f"${inv['amount']:,.2f}",
                "due_date": inv["due_date"],
                "owner_email": self.business_owner,
            }
            subject, body = self._render(item["level"], data)

            record = self._record_reminder(inv["id"],
                                           inv["customer_id"],
                                           item["level"],
                                           inv["due_date"],
                                           subject,
                                           status="pending")

            sent = False
            if not dry_run and recipient and self.gmail and self.gmail.available:
                try:
                    self.gmail.send_email(recipient, subject, body)
                    sent = True
                except GmailUnavailableError:
                    sent = False

            if not dry_run and sent:
                self.db.execute(
                    "UPDATE reminders SET status = 'sent', sent_date = date('now') "
                    "WHERE id = ?", (record,),
                )
                self.audit.log("system", "send_reminder", "reminders", record,
                               f"{item['level']} reminder for " f"{inv['invoice_number']}")
            elif dry_run and recipient:
                self.db.execute(
                    "UPDATE reminders SET status = 'queued' WHERE id = ?", (record,)
                )

            results.append({
                "reminder_id": record,
                "invoice_number": inv["invoice_number"],
                "level": item["level"],
                "recipient": recipient,
                "subject": subject,
                "sent": sent,
                "status": "sent" if sent else "queued" if dry_run else "pending",
            })
        return results

    def _record_reminder(self, invoice_id, customer_id, level, due_date,
                         subject, status="pending"):
        return self.db.execute(
            "INSERT INTO reminders (invoice_id, customer_id, level, due_date, "
            "status, email_subject) VALUES (?, ?, ?, ?, ?, ?)",
            (invoice_id, customer_id, level, due_date, status, subject),
        )

    def list_reminders(self, limit=100):
        return self.db.query(
            "SELECT * FROM reminders ORDER BY id DESC LIMIT ?", (limit,)
        )
