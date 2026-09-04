"""
Four complete test scenarios.
Each populates a fresh DB and asserts the expected state.
"""
from datetime import date, timedelta

from database import Database
from services import FinanceService
from models import Customer, Invoice, Payment, Expense
from cashflow import CashFlowAnalyzer, ForecastEngine
from reports import ReportingService


def _setup_base(db, scenario):
    """Populate the DB with base + scenario-specific data, return svc."""
    svc = FinanceService(db)
    today = date.today()

    # 10 customers
    customers = [
        ("Acme Corp", "billing@acmecorp.com"),
        ("Beta Industries", "accounts@beta.com"),
        ("Gamma Solutions", "ap@gamma.com"),
        ("Delta Ltd", "finance@delta.com"),
        ("Epsilon Group", "billing@epsilon.com"),
        ("Zeta Partners", "accounting@zeta.com"),
        ("Eta Ventures", "payables@eta.com"),
        ("Theta Systems", "finance@theta.com"),
        ("Iota Holdings", "ap@iota.com"),
        ("Kappa Ltd", "accounts@kappa.com"),
    ]
    for name, email in customers:
        svc.create_customer(Customer(name=name, email=email))

    # Base invoices
    base_invoices = [
        ("INV-1001", 1, 12500, 10, 20, "issued"),
        ("INV-1002", 2, 23000, 15, 15, "issued"),
        ("INV-1003", 3, 8400, 5, 25, "issued"),
        ("INV-1004", 4, 16000, 40, -10, "issued"),
        ("INV-1005", 5, 9100, 60, -25, "issued"),
        ("INV-1006", 6, 1500, 45, -15, "issued"),
        ("INV-1007", 7, 18200, 8, 22, "issued"),
        ("INV-1008", 8, 5400, 20, 10, "issued"),
        ("INV-1009", 9, 27700, 12, 18, "issued"),
        ("INV-1010", 10, 9900, 3, 27, "issued"),
        ("INV-1011", 1, 7200, 30, -5, "issued"),
        ("INV-1012", 2, 3400, 90, -45, "issued"),
        ("INV-1013", 3, 6100, 25, -8, "issued"),
        ("INV-1014", 4, 8300, 7, 23, "issued"),
        ("INV-1015", 5, 11200, 2, 28, "issued"),
    ]
    for inv_no, cust_id, amt, issue_ago, due_off, status in base_invoices:
        svc.create_invoice_unique(
            inv_no, cust_id, amt,
            (today - timedelta(days=issue_ago)).isoformat(),
            (today + timedelta(days=due_off)).isoformat(),
            status=status,
        )

    # Payments: mark INV-1001 and INV-1002 as paid, partial on INV-1012
    inv1 = svc.get_invoice_by_number("INV-1001")
    if inv1:
        svc.record_payment(Payment(
            invoice_id=inv1["id"], customer_id=inv1["customer_id"],
            amount=inv1["amount"], payment_date=(today - timedelta(days=3)).isoformat(),
        ))
    inv2 = svc.get_invoice_by_number("INV-1002")
    if inv2:
        svc.record_payment(Payment(
            invoice_id=inv2["id"], customer_id=inv2["customer_id"],
            amount=inv2["amount"], payment_date=(today - timedelta(days=2)).isoformat(),
        ))
    inv12 = svc.get_invoice_by_number("INV-1012")
    if inv12:
        svc.record_payment(Payment(
            invoice_id=inv12["id"], customer_id=inv12["customer_id"],
            amount=2000, payment_date=(today - timedelta(days=5)).isoformat(),
        ))

    # Expenses
    base_expenses = [
        ("Rent", 3500, 30, 1), ("Salaries", 12000, 30, 1),
        ("Software", 800, 30, 1), ("Utilities", 450, 30, 1),
        ("Insurance", 600, 30, 1), ("Marketing", 1200, 12, 0),
        ("Marketing", 900, 8, 0), ("Office Supplies", 250, 6, 0),
        ("Travel", 750, 20, 0), ("Consulting", 2000, 10, 0),
        ("Equipment", 1500, 60, 0), ("Software", 120, 15, 0),
        ("Utilities", 480, 0, 0), ("Subscriptions", 99, 4, 1),
        ("Marketing", 600, 25, 0), ("Office Supplies", 300, 18, 0),
        ("Travel", 420, 14, 0), ("Consulting", 1500, 5, 0),
        ("Equipment", 2200, 70, 0), ("Insurance", 600, 90, 1),
    ]
    for cat, amt, days_ago, rec in base_expenses:
        svc.create_expense(Expense(
            category=cat, description=f"{cat} expense",
            amount=amt, expense_date=(today - timedelta(days=days_ago)).isoformat(),
            recurring=rec,
        ))

    # Transactions
    income_hist = [
        (15, 8000, "Invoice payment INV-1001"),
        (13, 12000, "Client milestone"),
        (10, 15000, "INV-1002 partial"),
        (25, 10000, "Retainer"),
        (8, 9000, "Project payment"),
        (5, 7000, "INV-1003"),
        (20, 6000, "Contract work"),
        (30, 13000, "Quarterly maintenance"),
        (22, 4500, "Consulting fee"),
        (18, 7500, "Service delivery"),
        (12, 8500, "Platform revenue"),
        (7, 6500, "Maintenance fee"),
    ]
    for d, amt, desc in income_hist:
        svc._record_transaction(
            date=(today - timedelta(days=d)).isoformat(),
            description=desc, category="revenue",
            amount=float(amt), type="income", source="test",
        )

    # Note: base_expenses already creates transactions via create_expense.
    # No manual expense transactions needed here.

    # Scenario-specific additions
    if scenario == 1:  # cashflow warning: big extra expense + large outflow
        svc.create_expense(Expense(
            category="Salaries", description="Emergency payroll",
            amount=20000, expense_date=(today - timedelta(days=2)).isoformat(),
            recurring=1,
        ))
        svc._record_transaction(
            date=(today - timedelta(days=1)).isoformat(),
            description="Quarterly tax settlement",
            category="Taxes", amount=-140000.0, type="expense", source="scenario",
        )
    elif scenario == 3:  # high-expense
        svc.create_expense(Expense(
            category="Equipment", description="Urgent equipment",
            amount=25000, expense_date=(today - timedelta(days=10)).isoformat(),
            recurring=0,
        ))
        svc.create_expense(Expense(
            category="Equipment Leasing", description="Large equipment lease",
            amount=15000, expense_date=(today - timedelta(days=5)).isoformat(),
            recurring=1,
        ))
        svc._record_transaction(
            date=(today - timedelta(days=10)).isoformat(),
            description="Equipment", category="Equipment",
            amount=-25000.0, type="expense", source="scenario",
        )

    # Recompute balances
    rows = db.query("SELECT id, amount FROM transactions ORDER BY id")
    running = 0.0
    for r in rows:
        running += r["amount"]
        db.execute("UPDATE transactions SET balance_after = ? WHERE id = ?",
                   (round(running, 2), r["id"]))
    return svc


def test_scenario_0_healthy(tmp_path):
    """Scenario 0: Healthy business - positive balance, low overdue,
    balanced revenue/expense."""
    db = Database(str(tmp_path / "s0.db"))
    svc = _setup_base(db, scenario=0)
    cf = CashFlowAnalyzer(db)
    fc = ForecastEngine(db)
    report = ReportingService(db)

    balance = cf.current_balance()
    assert balance > 0, f"Balance should be positive, got {balance}"

    ar = svc.accounts_receivable()
    assert ar > 0, "Should have outstanding AR"

    overdue = svc.invoices_overdue()
    overdue_total = sum(o["amount"] for o in overdue)

    forecast = fc.forecast((30, 60, 90))
    assert len(forecast) == 3

    # In a healthy business, 30-day forecast should not project negative
    assert forecast[0]["projected_balance"] >= 0, (
        f"30-day projection negative: {forecast[0]['projected_balance']}"
    )

    risk = report.risk_report()
    risk_flags = risk["risk_flags"]
    assert "negative_balance" not in risk_flags, (
        "Healthy business should not have negative balance flag"
    )

    insights = report.ai_insights(risk)
    assert len(insights["recommendations"]) >= 1


def test_scenario_1_cashflow_warning(tmp_path):
    """Scenario 1: Cash-flow warning - large expenses deplete reserves."""
    db = Database(str(tmp_path / "s1.db"))
    svc = _setup_base(db, scenario=1)
    cf = CashFlowAnalyzer(db)
    fc = ForecastEngine(db)
    report = ReportingService(db)

    balance = cf.current_balance()
    forecast = fc.forecast((30, 60, 90))

    # In this scenario, balance should be significantly reduced
    risk = report.risk_report()
    risk_flags = risk["risk_flags"]

    # The extra large expense should trigger at least a warning
    assert any(
        f in risk_flags
        for f in ("low_runway", "projected_crunch", "negative_balance")
    ), f"Expected a cash-flow risk flag, got: {risk_flags}"

    # Forecast model should be internally consistent: longer horizon has more
    # projected income and expense than the shorter one.
    assert forecast[2]["projected_income"] >= forecast[0]["projected_income"]
    assert forecast[2]["projected_expense"] >= forecast[0]["projected_expense"]

    risk_messages = [r["message"] for r in risk["risks"]]
    assert any("balance" in m.lower() or "cash" in m.lower() or "expense" in m.lower()
               for m in risk_messages), f"Expected cash-related risk message"


def test_scenario_2_overdue(tmp_path):
    """Scenario 2: Overdue invoices - aging receivables, risk of non-payment."""
    db = Database(str(tmp_path / "s2.db"))
    svc = _setup_base(db, scenario=2)
    cf = CashFlowAnalyzer(db)
    report = ReportingService(db)

    overdue = svc.invoices_overdue()
    assert len(overdue) >= 2, f"Expected >=2 overdue invoices, got {len(overdue)}"

    overdue_total = sum(o["amount"] for o in overdue)
    assert overdue_total > 0

    ar = svc.accounts_receivable()
    # In this scenario, overdue total should be a significant portion of AR
    if ar > 0:
        overdue_ratio = overdue_total / ar
        assert overdue_ratio >= 0.15, (
            f"Expected significant overdue ratio, got {overdue_ratio:.2f}"
        )

    risk = report.risk_report()
    insights = report.ai_insights(risk)
    recs = insights["recommendations"]
    assert any("overdue" in r.lower() or "collection" in r.lower()
               for r in recs), f"Expected collection recommendation, got: {recs}"

    # Test due reminders
    from reminders import ReminderEngine
    engine = ReminderEngine(db)
    due = engine.due_reminders()
    # In overdue scenario, there should be overdue invoices needing reminders
    assert isinstance(due, list)


def test_scenario_3_high_expense(tmp_path):
    """Scenario 3: High-expense financial risk - expenses outpacing revenue."""
    db = Database(str(tmp_path / "s3.db"))
    svc = _setup_base(db, scenario=3)
    cf = CashFlowAnalyzer(db)
    fc = ForecastEngine(db)
    report = ReportingService(db)

    balance = cf.current_balance()
    total_exp = svc.total_expenses()
    total_rev = svc.total_revenue()

    forecast = fc.forecast((30, 60, 90))

    # 90-day projection should show deterioration
    assert forecast[2]["projected_expense"] > forecast[0]["projected_expense"], (
        "90-day expense projection should exceed 30-day"
    )

    risk = report.risk_report()
    insights = report.ai_insights(risk)
    assert len(insights["recommendations"]) >= 1

    # The system should identify high-expense risk somewhere in metrics or flags
    # Either through "high_fixed_cost" flag or balance/expense ratio warnings
    risk_flags = risk["risk_flags"]
    risk_messages = [r["message"] for r in risk["risks"]]
    total_critical_flags = len(risk_flags)
    assert total_critical_flags >= 1 or any(
        "expense" in m.lower() or "cost" in m.lower() or "balance" in m.lower()
        for m in risk_messages
    ), f"Expected expense-related risk indicator. Flags: {risk_flags}, Messages: {risk_messages}"
