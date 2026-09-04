from datetime import date, timedelta

from models import Expense
from services import FinanceService


class TestExpenses:
    def test_create_expense(self, db_and_svc):
        db, svc = db_and_svc
        eid = svc.create_expense(Expense(
            category="Software", description="SaaS", amount=200,
            expense_date="2026-01-01", vendor="Acme",
        ))
        assert eid > 0

    def test_list_expenses(self, db_and_svc):
        db, svc = db_and_svc
        for i in range(3):
            svc.create_expense(Expense(
                category="Office Supplies", amount=50 + i,
                expense_date=date.today().isoformat(),
            ))
        assert len(svc.list_expenses()) >= 3

    def test_total_expenses(self, db_and_svc):
        db, svc = db_and_svc
        today = date.today()
        svc.create_expense(Expense(category="Rent", amount=1000,
                                   expense_date=today.isoformat()))
        svc.create_expense(Expense(category="Utilities", amount=200,
                                   expense_date=today.isoformat()))
        total = svc.total_expenses(
            (today - timedelta(days=1)).isoformat(),
            (today + timedelta(days=1)).isoformat(),
        )
        assert total >= 1200.0

    def test_expenses_by_category(self, db_and_svc):
        db, svc = db_and_svc
        svc.create_expense(Expense(category="Software", amount=100,
                                   expense_date=date.today().isoformat()))
        cats = svc.expenses_by_category()
        assert len(cats) >= 1

    def test_recurring_expenses(self, db_and_svc):
        db, svc = db_and_svc
        svc.create_expense(Expense(category="Rent", amount=1000,
                                   expense_date=date.today().isoformat(),
                                   recurring=1))
        total = svc.recurring_expenses_monthly()
        assert total >= 1000.0
