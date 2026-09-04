from datetime import date, timedelta

from services import FinanceService
from models import Customer, Invoice, Expense
from reports import ReportingService
from cashflow import CashFlowAnalyzer


class TestReportingService:
    def _setup(self, db):
        svc = FinanceService(db)
        today = date.today()
        cid = svc.create_customer(Customer(name="Report Test", email="rt@x.com"))
        svc.create_invoice_unique("INV-RPT1", cid, 10000,
                                  (today - timedelta(days=20)).isoformat(),
                                  (today + timedelta(days=10)).isoformat())
        svc.create_expense(Expense(
            category="Software", amount=500, expense_date=today.isoformat(),
        ))
        svc._record_transaction(
            date=(today - timedelta(days=3)).isoformat(),
            description="Income", category="revenue",
            amount=5000, type="income", source="test",
        )
        return svc

    def test_weekly_report(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        report = rpt.weekly_report()
        assert "period" in report
        assert "revenue" in report
        assert "expenses" in report
        assert "net" in report
        assert isinstance(report["net"], float)

    def test_weekly_report_text(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        report = rpt.weekly_report()
        text = rpt.render_weekly_report_text(report)
        assert "WEEKLY FINANCIAL REPORT" in text
        assert "Revenue" in text

    def test_risk_report(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        risk = rpt.risk_report()
        assert "current_balance" in risk
        assert "risks" in risk
        assert isinstance(risk["risks"], list)

    def test_ai_insights_fallback(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        risk = rpt.risk_report()
        insights = rpt.ai_insights(risk)
        assert insights["source"] in ("ai", "rule")
        assert len(insights["recommendations"]) >= 1

    def test_expense_breakdown(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        breakdown = rpt.expense_breakdown()
        assert isinstance(breakdown, list)

    def test_rule_based_recommendations(self, tmp_db):
        self._setup(tmp_db)
        rpt = ReportingService(tmp_db)
        risk = rpt.risk_report()
        recs = rpt._rule_based_recommendations(risk)
        assert isinstance(recs, list)
        assert len(recs) >= 1
