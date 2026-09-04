from datetime import date, timedelta

from models import Customer, Invoice, Payment, Expense
from services import FinanceService
from cashflow import CashFlowAnalyzer, ForecastEngine


class TestCashFlow:
    def test_current_balance(self, tmp_db):
        svc = FinanceService(tmp_db)
        cf = CashFlowAnalyzer(tmp_db)
        cid = svc.create_customer(Customer(name="CF Test", email="cf@x.com"))
        svc.create_invoice_unique("INV-CF1", cid, 5000, "2026-01-01",
                                  "2026-02-01")
        svc.record_payment(Payment(invoice_id=1, customer_id=cid,
                                   amount=5000, payment_date=date.today().isoformat()))
        balance = cf.current_balance()
        assert isinstance(balance, float)

    def test_cashflow_series(self, tmp_db):
        cf = CashFlowAnalyzer(tmp_db)
        series = cf.cashflow_series(3)
        assert isinstance(series, list)
        assert len(series) == 3
        assert all(k in s for s in series for k in ("month", "income", "expense"))


class TestForecast:
    def test_forecast_basic(self, tmp_db):
        fc = ForecastEngine(tmp_db)
        results = fc.forecast((30, 60, 90))
        assert len(results) == 3
        assert all(k in r for r in results for k in
                   ("period", "projected_income", "projected_expense",
                    "projected_balance"))

    def test_breakeven_point(self, tmp_db):
        fc = ForecastEngine(tmp_db)
        bp = fc.breakeven_point()
        assert isinstance(bp, float)
        assert bp >= 0.0

    def test_risk_metrics(self, tmp_db):
        fc = ForecastEngine(tmp_db)
        metrics = fc.risk_metrics()
        assert "current_balance" in metrics
        assert "accounts_receivable" in metrics
