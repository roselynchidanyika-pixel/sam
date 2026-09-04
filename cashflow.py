from datetime import date, timedelta
from collections import defaultdict

from database import Database
from services import FinanceService


class CashFlowAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.finance = FinanceService(db)

    def opening_balance(self, as_of: date = None) -> float:
        """Cash balance at the start of a period (default: all time, 0)."""
        as_of = as_of or date.today()
        row = self.db.query_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE date < ?",
            (as_of.isoformat(),),
        )
        return float(row["total"]) if row else 0.0

    def current_balance(self) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions"
        )
        return float(row["total"]) if row else 0.0

    def cashflow_series(self, months: int = 6) -> list:
        """Return monthly income/expense/net for the last N months."""
        today = date.today()
        start_month = (today.replace(day=1) - timedelta(days=months * 31)).replace(day=1)
        rows = self.db.query(
            "SELECT date, amount, type FROM transactions WHERE date >= ?",
            (start_month.isoformat(),),
        )
        monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        for r in rows:
            ym = r["date"][:7]
            t = r["type"]
            if t == "income":
                monthly[ym]["income"] += r["amount"]
            else:
                monthly[ym]["expense"] += abs(r["amount"])

        series = []
        cursor = start_month
        i = 0
        while i < months:
            ym = cursor.strftime("%Y-%m")
            inc = round(monthly[ym]["income"], 2)
            exp = round(monthly[ym]["expense"], 2)
            series.append({
                "month": ym,
                "income": inc,
                "expense": exp,
                "net": round(inc - exp, 2),
                "balance": 0.0,  # filled below
            })
            cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            i += 1

        running = 0.0
        for s in series:
            running += s["net"]
            s["balance"] = round(running, 2)
        return series


class ForecastEngine:
    def __init__(self, db: Database):
        self.db = db
        self.finance = FinanceService(db)

    def average_monthly_income(self, months: int = 3) -> float:
        rows = self.db.query(
            "SELECT date, amount FROM transactions WHERE type='income' "
            "ORDER BY date DESC LIMIT ?",
            (months * 50,),
        )
        total = sum(r["amount"] for r in rows)
        return float(total) / max(months, 1)

    def average_monthly_expenses(self, months: int = 3) -> float:
        rows = self.db.query(
            "SELECT expense_date, amount FROM expenses ORDER BY expense_date DESC LIMIT ?",
            (months * 100,),
        )
        total = sum(abs(r["amount"]) for r in rows)
        return float(total) / max(months, 1)

    def _expected_inflow(self, start: date, days: int) -> float:
        """Expected income: average_income + scheduled payments due."""
        end = start + timedelta(days=days)
        avg_income = self.average_monthly_income() * (days / 30.0)
        invoices_due = self.db.query(
            "SELECT amount, status FROM invoices WHERE due_date >= ? AND due_date < ? "
            "AND status != 'paid'",
            (start.isoformat(), end.isoformat()),
        )
        expected = avg_income + sum(i["amount"] for i in invoices_due)
        return expected

    def _expected_outflow(self, start: date, days: int) -> float:
        end = start + timedelta(days=days)
        avg_expense = self.average_monthly_expenses() * (days / 30.0)
        scheduled = self.db.query(
            "SELECT amount, expense_date FROM expenses WHERE expense_date >= ? "
            "AND expense_date < ? AND recurring = 1",
            (start.isoformat(), end.isoformat()),
        )
        return avg_expense + sum(e["amount"] for e in scheduled)

    def forecast(self, periods=(30, 60, 90)) -> list:
        """Project cash balance over each horizon."""
        start = date.today()
        current_balance = self._cash_balance()
        results = []
        for days in periods:
            inflow = self._expected_inflow(start, days)
            outflow = self._expected_outflow(start, days)
            projected = current_balance + inflow - outflow
            results.append({
                "period": days,
                "start_balance": round(current_balance, 2),
                "projected_income": round(inflow, 2),
                "projected_expense": round(outflow, 2),
                "projected_net": round(inflow - outflow, 2),
                "projected_balance": round(projected, 2),
            })
            self._cache(days, inflow, outflow, projected)
        return results

    def _cash_balance(self) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions"
        )
        return float(row["total"]) if row else 0.0

    def _cache(self, period, income, expense, net):
        self.db.execute(
            "INSERT INTO forecast_cache (created_at, period, projected_income, "
            "projected_expense, net_cashflow) VALUES (datetime('now'), ?, ?, ?, ?)",
            (period, income, expense, net),
        )

    def breakeven_point(self) -> float:
        """Monthly revenue needed to cover monthly expenses."""
        avg_exp = self.average_monthly_expenses()
        return round(avg_exp, 2)

    def risk_metrics(self) -> dict:
        current = self.finance.current_balance() if hasattr(self.finance, 'current_balance') else self._cash_balance()
        ar = self.finance.accounts_receivable()
        overdue = self.finance.invoices_overdue()
        overdue_total = sum(o["amount"] for o in overdue)
        expenses = self._cash_balance()  # placeholder, see below

        metrics = {
            "current_balance": round(current, 2),
            "accounts_receivable": round(ar, 2),
            "overdue_total": round(overdue_total, 2),
            "overdue_count": len(overdue),
            "forecast_90d": None,
        }
        return metrics
