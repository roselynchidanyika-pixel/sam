import base64
from datetime import date

from database import Database, AuditLogger
from email_agent import EmailProcessor
from gmail_client import GmailClient, GmailUnavailableError
from config import Config


class EmailComposer:
    """Handles the outbound email flow: process -> extract -> update -> summarize
    -> send to owner -> audit log."""

    def __init__(self, db: Database, gmail: GmailClient = None,
                 email_processor: EmailProcessor = None):
        self.db = db
        self.audit = AuditLogger(db)
        self.gmail = gmail
        self.processor = email_processor or EmailProcessor(db, gmail)
        self.business_owner = Config.BUSINESS_OWNER_EMAIL

    def compose_and_send(self, recipient: str, subject: str, body: str,
                         attachments: list = None,
                         human_approval: bool = None) -> dict:
        """The full outbound logic.

        Steps:
        1. Process email via AI Email Agent (classify + extract).
        2. Update relevant DB records.
        3. Generate a financial summary.
        4. Send the full summary to the BUSINESS OWNER via Gmail.
        5. Record the action in the audit log.

        Returns a result dict.
        """
        require_approval = Config.HUMAN_APPROVAL_REQUIRED if human_approval is None \
            else human_approval

        # 1. Process via Email Agent
        email_record = self._record_outgoing(recipient, subject, body,
                                             attachments)
        classification = self.processor.classify(subject, body)

        # 2. Apply action to DB records
        updates = []
        try:
            applied = self._apply_to_db(classification, recipient, subject, body)
            updates = applied.get("updates", [])
        except Exception as e:
            updates = [f"DB update failed: {e}"]

        # 3. Generate summary
        summary = self._build_summary(recipient, subject, body, classification,
                                      updates)

        # 4. Send to business owner (full processed info + summary)
        owner_notified = False
        if self.gmail and self.gmail.available and self.business_owner:
            owner_body = self._build_owner_message(recipient, subject, body,
                                                   classification, summary, updates)
            try:
                self.gmail.send_email(
                    self.business_owner,
                    f"[AI Finance OS] Outbound processed: {subject}",
                    owner_body,
                )
                owner_notified = True
            except GmailUnavailableError:
                owner_notified = False

        # Also send the original email to the recipient
        recipient_sent = False
        if self.gmail and self.gmail.available and not require_approval:
            try:
                self.gmail.send_email(recipient, subject, body,
                                      attachments or [])
                recipient_sent = True
            except GmailUnavailableError:
                recipient_sent = False

        # 5. Audit log
        self.audit.log(
            "email_composer",
            "compose_and_send",
            "emails",
            email_record,
            (f"Subject: {subject} | Recipient: {recipient} | "
             f"Classification: {classification.get('classification')} | "
             f"Owner notified: {owner_notified} | Recipient sent: {recipient_sent} | "
             f"Updates: {'; '.join(updates) if updates else 'none'}"),
        )

        return {
            "email_record_id": email_record,
            "recipient": recipient,
            "subject": subject,
            "classification": classification,
            "updates": updates,
            "summary": summary,
            "owner_notified": owner_notified,
            "recipient_sent": recipient_sent,
            "approval_required": require_approval and not recipient_sent,
        }

    def _record_outgoing(self, recipient, subject, body, attachments):
        return self.db.execute(
            "INSERT INTO emails (gmail_message_id, from_address, to_address, "
            "subject, body, received_at, processed, sent) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'), 1, 0)",
            (f"out-{date.today().isoformat()}-{recipient}-{abs(hash(subject)) % 100000}",
             recipient, self.business_owner, subject, body),
        )

    def _apply_to_db(self, classification, recipient, subject, body):
        cls = classification.get("classification")
        if cls == "invoice":
            return self.processor._handle_invoice(classification,
                                                  {"subject": subject, "body": body})
        elif cls == "payment":
            return self.processor._handle_payment(
                classification, {"subject": subject, "body": body})
        elif cls == "expense":
            return self.processor._handle_expense(
                classification, {"subject": subject, "body": body})
        return {"applied": False, "updates": ["No financial action detected."]}

    def _build_summary(self, recipient, subject, body, classification, updates) -> str:
        cls = classification.get("classification", "other")
        lines = [
            "=== AI FINANCIAL SUMMARY ===",
            f"Recipient: {recipient}",
            f"Subject: {subject}",
            f"Classification: {cls}",
            f"Client: {classification.get('client_name') or 'N/A'}",
            f"Amount: {classification.get('amount') or 'N/A'}",
            f"Invoice #: {classification.get('invoice_number') or 'N/A'}",
            f"Due date: {classification.get('due_date') or 'N/A'}",
            f"Action required: {classification.get('action_required') or 'N/A'}",
            "",
            "Applied changes:",
        ]
        if updates:
            lines.extend(f"  - {u}" for u in updates)
        else:
            lines.append("  - None")
        return "\n".join(lines)

    def _build_owner_message(self, recipient, subject, body, classification,
                             summary, updates) -> str:
        return (
            f"Subject: {subject}\n"
            f"Recipient: {recipient}\n\n"
            f"{'-' * 40}\n"
            f"ORIGINAL EMAIL\n"
            f"{'-' * 40}\n\n"
            f"{body}\n\n"
            f"{'-' * 40}\n"
            f"{summary}\n"
            f"{'-' * 40}\n"
            f"AI ACTION: {classification.get('action_required') or 'None'}\n"
            f"Updates applied: {len(updates)}\n"
        )
