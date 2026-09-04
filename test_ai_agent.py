import os

import pytest
from unittest.mock import patch, MagicMock

from ai_agent import AIEmailAgent, AIRuleEngine, AIUnavailableError


class TestAIRuleEngine:
    def test_classify_invoice(self, engine):
        r = engine.classify_email(
            "Invoice #INV-500",
            "Please find attached invoice INV-500 for $2500"
        )
        assert r["classification"] == "invoice"
        assert r["amount"] == 2500.0

    def test_classify_payment_received(self, engine):
        r = engine.classify_email(
            "Payment received",
            "We have made a bank transfer payment of $7500"
        )
        assert r["classification"] == "payment"

    def test_classify_reminder(self, engine):
        r = engine.classify_email(
            "Reminder - overdue invoice",
            "Your invoice is now overdue. This is a reminder."
        )
        assert r["classification"] == "reminder"

    def test_classify_expense(self, engine):
        r = engine.classify_email(
            "Purchase receipt",
            "Here is your receipt for $300 purchase"
        )
        assert r["classification"] == "expense"

    def test_classify_general(self, engine):
        r = engine.classify_email("Lunch plans", "Want to grab lunch?")
        assert r["classification"] == "other"

    def test_find_amount_with_comma(self, engine):
        r = engine.classify_email(
            "Invoice", "Amount of $1,250,000 due"
        )
        assert r["amount"] == 1250000.0

    def test_find_invoice_number(self, engine):
        r = engine.classify_email(
            "Re: INV-2026-001",
            "Regarding invoice number INV-2026-001"
        )
        assert r["invoice_number"] is not None

    def test_find_iso_date(self, engine):
        r = engine.classify_email(
            "Invoice due 2026-10-15",
            "Payment due by 2026-10-15"
        )
        assert r["due_date"] == "2026-10-15"


@pytest.fixture
def engine():
    return AIRuleEngine()


class TestAIEmailAgent:
    def test_unavailable_without_key(self):
        agent = AIEmailAgent(api_key="")
        assert not agent.available
        with patch("ai_agent.Config.OPENAI_API_KEY", ""):
            agent2 = AIEmailAgent()
            assert not agent2.available

    def test_classify_raises_without_key(self):
        agent = AIEmailAgent(api_key="")
        try:
            agent.classify_email("test", "test body")
            assert False, "Should have raised"
        except AIUnavailableError:
            pass

    def test_recommendations_raises_without_key(self):
        agent = AIEmailAgent(api_key="")
        try:
            agent.financial_recommendations({})
            assert False, "Should have raised"
        except AIUnavailableError:
            pass
