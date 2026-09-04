import hashlib
from datetime import date, datetime

from database import Database, AuditLogger
from services import FinanceService
from ai_agent import get_ai_agent, get_rule_engine, AIUnavailableError
from gmail_client import GmailClient, GmailUnavailableError
from config import Config
from models import Payment, Invoice, Expense


class EmailProcessor:
    """Processes incoming emails: classify, extract, and update the system."""

    def __init__(self, db: Database, gmail: GmailClient = None,
                 ai_agent=None, rule_engine=None, use_ai: bool = True):
        self.db = db
        self.finance = FinanceService(db)
        self.audit = AuditLogger(db)
        self.gmail = gmail
        self.ai_agent = ai_agent or get_ai_agent()
        self.rule_engine = rule_engine or get_rule_engine()
        self.use_ai = use_ai and self.ai_agent.available

    def classify(self, subject: str, body: str) -> dict:
        if self.use_ai:
            try:
                return self.ai_agent.classify_email(subject, body)
            except AIUnavailableError:
                pass
        return self.rule_engine.classify_email(subject, body)

    def process_message(self, email: dict, allow_record: bool = True) -> dict:
        """Process a single email dict and update DB records.

        Returns an analysis summary dict.
        """
        subject = email.get("subject", "")
        body = email.get("body", "")
        classification = self.classify(subject, body)

        # Deduplicate by gmail_message_id
        existing = None
        if email.get("gmail_message_id"):
            existing = self.db.query_one(
                "SELECT id FROM emails WHERE gmail_message_id = ?",
                (email["gmail_message_id"],),
            )
        email_id = existing["id"] if existing else self.db.execute(
            "INSERT INTO emails (gmail_message_id, from_address, to_address, "
            "subject, body, received_at, classification, client_name, amount, "
            "invoice_number, due_date, action_required, processed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (email.get("gmail_message_id"), email.get("from_address"),
             email.get("to_address"), subject, body,
             email.get("received_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
             classification.get("classification"),
             classification.get("client_name"),
             classification.get("amount"),
             classification.get("invoice_number"),
             classification.get("due_date"),
             classification.get("action_required"), 0),
        )

        summary = {
            "email_id": email_id,
            "classification": classification.get("classification", "other"),
            "client_name": classification.get("client_name"),
            "amount": classification.get("amount"),
            "invoice_number": classification.get("invoice_number"),
            "due_date": classification.get("due_date"),
            "action_required": classification.get("action_required"),
            "updates": [],
        }

        if allow_record:
            try:
                result = self._apply_action(classification, email, subject, body)
                summary["updates"] = result.get("updates", [])
                summary["applied"] = result.get("applied", False)
            except Exception as e:
                summary["applied"] = False
                summary["error"] = str(e)

        self.db.execute(
            "UPDATE emails SET processed = 1 WHERE id = ?", (email_id,)
        )
        self.audit.log("system", "process_email", "emails", email_id,
                       f"Classified as {summary['classification']}")
        return summary

    def _apply_action(self, classification, email, subject, body) -> dict:
        cls = classification.get("classification")
        action = classification.get("action_required")
        result = {"applied": False, "updates": []}

        if cls == "invoice":
            result.update(self._handle_invoice(classification, email))
        elif cls == "payment":
            result.update(self._handle_payment(classification, email))
        elif cls == "expense":
            result.update(self._handle_expense(classification, email))
        elif cls == "reminder":
            result["applied"] = True
            result["updates"].append("Classified as reminder for follow-up.")
        return result

    def _match_customer(self, classification):
        name = classification.get("client_name")
        if name:
            return self.finance.get_or_create_customer_by_name(name)
        return None

    def _handle_invoice(self, classification, email) -> dict:
        inv_no = classification.get("invoice_number")
        amount = classification.get("amount")
        customer_id = self._match_customer(classification)

        if not inv_no or amount is None:
            return {"applied": False,
                    "updates": ["Invoice missing number or amount."]}

        due = classification.get("due_date") or (
            date.today() + __import__("datetime").timedelta(days=30)).isoformat()

        existing = self.db.query_one(
            "SELECT * FROM invoices WHERE invoice_number = ?", (inv_no,)
        )
        if existing:
            if abs(existing["amount"] - amount) > 0.01:
                self.db.execute(
                    "UPDATE invoices SET amount = ?, customer_id = COALESCE(?, "
                    "customer_id), description = ? WHERE id = ?",
                    (amount, customer_id, email.get("subject"), existing["id"]),
                )
                return {"applied": True, "updates": [f"Updated invoice {inv_no}."]}
            return {"applied": True, "updates": [f"Invoice {inv_no} already exists."]}

        iid = self.finance.create_invoice_unique(
            invoice_number=inv_no, customer_id=customer_id, amount=amount,
            issue_date=date.today().isoformat(), due_date=due,
            description=email.get("subject"),
        )
        return {"applied": True, "updates": [f"Created invoice {inv_no} for {amount}."]}

    def _handle_payment(self, classification, email) -> dict:
        amount = classification.get("amount")
        paid_by = self._match_customer(classification)
        if amount is None:
            return {"applied": False, "updates": ["Payment missing amount."]}

        inv_no = classification.get("invoice_number")
        invoice = None
        if inv_no:
            invoice = self.finance.get_invoice_by_number(inv_no)

        invoice_id = invoice["id"] if invoice else None
        cust_id = paid_by
        if invoice and invoice["customer_id"]:
            cust_id = invoice["customer_id"]

        self.finance.record_payment(Payment(
            invoice_id=invoice_id,
            customer_id=cust_id,
            amount=amount,
            payment_date=date.today().isoformat(),
            method="email",
            reference=email.get("gmail_message_id"),
            recorded_by="email_agent",
        ))
        msg = f"Recorded payment of {amount}"
        if inv_no:
            msg += f" for invoice {inv_no}"
        if invoice_id and self.finance.is_invoice_paid(invoice_id):
            msg += ". Invoice marked paid."
        return {"applied": True, "updates": [msg]}

    def _handle_expense(self, classification, email) -> dict:
        amount = classification.get("amount")
        if amount is None:
            return {"applied": False, "updates": ["Expense missing amount."]}
        eid = self.finance.create_expense(Expense(
            category="Other", amount=amount,
            expense_date=date.today().isoformat(),
            description=email.get("subject", "Expense from email"),
            vendor=classification.get("client_name"),
        ))
        return {"applied": True, "updates": [f"Recorded expense of {amount}."]}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
