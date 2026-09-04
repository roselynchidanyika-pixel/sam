from datetime import date, timedelta

from models import Customer, Invoice, Expense
from services import FinanceService
from cashflow import ForecastEngine


class TestForecastEngine:
    def _setup(self, tmp_db):
        svc = FinanceService(tmp_db)
        today = date.today()
        cid = svc.create_customer(Customer(name="F Test", email="f@x.com"))
        # Create invoices with future due dates
        svc.create_invoice_unique("INV-F01", cid, 10000, today.isoformat(),
                                  (today + timedelta(days=20)).isoformat())
        svc.create_invoice_unique("INV-F02", cid, 5000, today.isoformat(),
                                  (today + timedelta(days=50)).isoformat())
        # Add some history
        svc._record_transaction(
            date=(today - timedelta(days=15)).isoformat(),
            description="Past income", category="revenue",
            amount=8000.0, type="income", source="test",
        )
        svc._record_transaction(
            date=(today - timedelta(days=10)).isoformat(),
            description="Past income", category="revenue",
            amount=6000.0, type="income", source="test",
        )
        svc.create_expense(Expense(category="Software", amount=500,
                                   expense_date=today.isoformat(),
                                   recurring=1))
        return svc

    def test_average_monthly_income(self, tmp_db):
        self._setup(tmp_db)
        fc = ForecastEngine(tmp_db)
        avg = fc.average_monthly_income()
        assert avg > 0

    def test_forecast_periods(self, tmp_db):
        self._setup(tmp_db)
        fc = ForecastEngine(tmp_db)
        results = fc.forecast((30, 60, 90))
        assert results[0]["period"] == 30
        assert results[1]["period"] == 60
        assert results[2]["period"] == 90
        # 90-day expense should be >= 30-day expense
        assert results[2]["projected_expense"] >= results[0]["projected_expense"]

    def test_forecast_cashflow_direction(self, tmp_db):
        self._setup(tmp_db)
        fc = ForecastEngine(tmp_db)
        results = fc.forecast((30,))
        r = results[0]
        assert r["projected_income"] >= 0
        assert r["projected_expense"] >= 0
