from datetime import date

from ai_agent import AIRuleEngine
from email_agent import EmailProcessor
from services import FinanceService
from models import Customer


class TestRuleEngine:
    def test_classify_invoice(self, rule_engine):
        r = rule_engine.classify_email(
            "Invoice #INV-2001", "Please pay invoice INV-2001 amount $5000"
        )
        assert r["classification"] == "invoice"
        assert r["amount"] == 5000.0
        assert r["invoice_number"] == "INV-2001"

    def test_classify_payment(self, rule_engine):
        r = rule_engine.classify_email(
            "Payment received", "We made payment of $3000 for invoice INV-1001"
        )
        assert r["classification"] == "payment"
        assert r["amount"] == 3000.0

    def test_classify_reminder(self, rule_engine):
        r = rule_engine.classify_email(
            "Overdue notice", "Your invoice is past due and overdue. Reminder."
        )
        assert r["classification"] == "reminder"

    def test_classify_expense(self, rule_engine):
        r = rule_engine.classify_email(
            "Purchase receipt", "Receipt for office supplies expense $150"
        )
        assert r["classification"] == "expense"
        assert r["amount"] == 150.0

    def test_classify_other(self, rule_engine):
        r = rule_engine.classify_email("Hello team", "Team meeting tomorrow at 3pm")
        assert r["classification"] == "other"

    def test_extract_date(self, rule_engine):
        r = rule_engine.classify_email(
            "Invoice due",
            "Invoice due by 2026-12-01 for $500"
        )
        assert r["due_date"] == "2026-12-01"


class TestEmailProcessor:
    def test_process_message_creates_record(self, tmp_db):
        email_processor = EmailProcessor(tmp_db, gmail=None, use_ai=False)
        msg = {
            "from_address": "test@example.com",
            "subject": "Invoice INV-TEST1",
            "body": "Invoice INV-TEST1 for $1200 due by 2026-12-01",
            "received_at": "2026-09-01 10:00:00",
            "gmail_message_id": "gmail-001",
        }
        result = email_processor.process_message(msg)
        assert result["classification"] in ("invoice", "payment", "other")
        assert result["email_id"] > 0

    def test_process_message_deduplicates(self, tmp_db):
        ep = EmailProcessor(tmp_db, gmail=None, use_ai=False)
        msg = {
            "from_address": "dup@example.com",
            "subject": "Test dedup",
            "body": "Payment of $500",
            "received_at": "2026-09-01 10:00:00",
            "gmail_message_id": "gmail-dup-001",
        }
        ep.process_message(msg)
        ep.process_message(msg)
        count = tmp_db.query_one(
            "SELECT COUNT(*) as c FROM emails WHERE gmail_message_id = 'gmail-dup-001'"
        )["c"]
        assert count == 1
