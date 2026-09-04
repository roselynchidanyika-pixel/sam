from datetime import date, timedelta
import random
import csv
from pathlib import Path

from database import Database
from services import FinanceService
from models import Customer, Invoice, Payment, Expense
from cashflow import CashFlowAnalyzer


def generate_sample_data(db: Database, seed: int = 42):
    """Populate the database with realistic sample data.

    Scenarios controlled by `scenario` parameter via csv / callers:
    0 = healthy, 1 = cash-flow warning, 2 = overdue, 3 = high expense.
    """
    raise NotImplementedError(
        "Use generate_datasets() or load from CSV instead."
    )


def generate_datasets(db: Database):
    """Generate datasets for all 4 scenarios into CSV files and load baseline."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    base = {
        "customers": _customers(),
        "invoices": _invoices(),
        "expenses": _expenses(),
        "transactions": _transactions(),
        "emails": _emails(),
    }
    for name, rows in base.items():
        _write_csv(data_dir / f"sample_{name}.csv", rows)

    scenarios = {
        0: _healthy_scenario(base),
        1: _cashflow_warning_scenario(base),
        2: _overdue_scenario(base),
        3: _high_expense_scenario(base),
    }
    for idx, rows in scenarios.items():
        _write_csv(data_dir / f"scenario_{idx}_emails.csv",
                   rows["extra_emails"])
        _write_csv(data_dir / f"scenario_{idx}_overrides.csv",
                   rows.get("overrides", []))
    return base, scenarios


def _write_csv(path, rows):
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    fieldnames = rows[0].keys()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _customers():
    data = [
        ("Acme Corp", "billing@acmecorp.com", "+1-555-0101", "Acme Corp", "100 Market St"),
        ("Beta Industries", "accounts@betaindustries.com", "+1-555-0102", "Beta Industries", "200 Oak Ave"),
        ("Gamma Solutions", "ap@gamma-solutions.com", "+1-555-0103", "Gamma Solutions", "300 Pine Rd"),
        ("Delta Ltd", "finance@deltaltd.com", "+1-555-0104", "Delta Ltd", "400 Cedar Blvd"),
        ("Epsilon Group", "billing@epsilongroup.io", "+1-555-0105", "Epsilon Group", "500 Elm St"),
        ("Zeta Partners", "accounting@zetapartners.com", "+1-555-0106", "Zeta Partners", "600 Birch Way"),
        ("Eta Ventures", "payables@etaventures.co", "+1-555-0107", "Eta Ventures", "700 Maple Dr"),
        ("Theta Systems", "finance@thetasys.net", "+1-555-0108", "Theta Systems", "800 Walnut Ct"),
        ("Iota Holdings", "ap@iotaholdings.com", "+1-555-0109", "Iota Holdings", "900 Spruce Ln"),
        ("Kappa Ltd", "accounts@kappaltd.com", "+1-555-0110", "Kappa Ltd", "1000 Ash Ave"),
    ]
    return [{
        "name": n, "email": e, "phone": ph, "company": c, "address": a
    } for n, e, ph, c, a in data]


def _invoices():
    invoices = []
    today = date.today()
    number = 1001
    spec = [
        # (cust_index, amount, days_ago_issue, days_to_due, status)
        (0, 12500.00, 10, 20, "issued"),
        (1, 23000.00, 15, 15, "issued"),
        (2, 8400.00, 5, 25, "issued"),
        (3, 16000.00, 40, -10, "issued"),       # overdue
        (4, 9100.00, 60, -25, "issued"),        # overdue
        (5, 1500.00, 45, -15, "issued"),        # overdue young
        (6, 18200.00, 8, 22, "issued"),
        (7, 5400.00, 20, 10, "issued"),
        (8, 27700.00, 12, 18, "issued"),
        (9, 9900.00, 3, 27, "issued"),
        (0, 7200.00, 30, -5, "issued"),         # slightly overdue
        (1, 3400.00, 90, -45, "issued"),        # very overdue
        (2, 6100.00, 25, -8, "issued"),         # overdue
        (3, 8300.00, 7, 23, "issued"),
        (4, 11200.00, 2, 28, "issued"),
    ]
    for cust_idx, amount, issue_ago, due_offset, status in spec:
        issue = today - timedelta(days=issue_ago)
        due = today + timedelta(days=due_offset)
        invoices.append({
            "invoice_number": f"INV-{number}",
            "customer_id": cust_idx + 1,
            "amount": amount,
            "issue_date": issue.isoformat(),
            "due_date": due.isoformat(),
            "status": status,
            "description": f"Services - invoice {number}",
        })
        number += 1
    return invoices


def _expenses():
    expenses = []
    today = date.today()
    cats = ["Rent", "Salaries", "Software", "Marketing", "Utilities",
            "Office Supplies", "Insurance", "Travel", "Consulting",
            "Equipment", "Subscriptions"]
    spec = [
        ("Rent", 3500, 30, True, "Office rent"),
        ("Salaries", 12000, 30, True, "Monthly payroll"),
        ("Software", 800, 30, True, "SaaS subscriptions"),
        ("Utilities", 450, 30, True, "Electric + internet"),
        ("Insurance", 600, 30, True, "Business insurance"),
        ("Marketing", 1200, 12, False, "Ad campaign"),
        ("Marketing", 900, 8, False, "Social ads"),
        ("Office Supplies", 250, 6, False, "Stationery"),
        ("Travel", 750, 20, False, "Client visit"),
        ("Consulting", 2000, 10, False, "Legal consult"),
        ("Equipment", 1500, 60, False, "Laptop purchase"),
        ("Software", 120, 15, False, "One-time license"),
        ("Utilities", 480, 0, False, "Water bill"),
        ("Subscriptions", 99, 4, True, "Newsletter tool"),
        ("Marketing", 600, 25, False, "Trade show"),
        ("Office Supplies", 300, 18, False, "Printer cartridges"),
        ("Travel", 420, 14, False, "Client lunch"),
        ("Consulting", 1500, 5, False, "Tax prep"),
        ("Equipment", 2200, 70, False, "Monitor + desk"),
        ("Insurance", 600, 90, True, "Quarterly premium"),
    ]
    for cat, amount, days_ago, recurring, desc in spec:
        d = today - timedelta(days=days_ago)
        expenses.append({
            "category": cat,
            "description": desc,
            "amount": amount,
            "expense_date": d.isoformat(),
            "vendor": "Various",
            "recurring": 1 if recurring else 0,
        })
    return expenses


def _transactions():
    txns = []
    today = date.today()
    # Income from invoices and payments, expenses
    income_spec = [
        (15, 8000.0, "Invoice payment INV-1001"),
        (13, 12000.0, "Client milestone payment"),
        (10, 15000.0, "Invoice INV-1002 partial"),
        (25, 10000.0, "Retainer"),
        (8, 9000.0, "Project payment"),
        (5, 7000.0, "Invoice INV-1003"),
    ]
    expense_spec = [
        (1, 3500.0, "Rent"),
        (1, 450.0, "Utilities"),
        (2, 1200.0, "Marketing"),
        (3, 800.0, "Software"),
        (4, 600.0, "Insurance"),
    ]
    for days_ago, amt, desc in income_spec:
        txns.append({
            "date": (today - timedelta(days=days_ago)).isoformat(),
            "description": desc,
            "category": "revenue",
            "amount": amt,
            "type": "income",
            "account": "main",
            "balance_after": None,
            "source": "sample",
        })
    for days_ago, amt, cat in expense_spec:
        txns.append({
            "date": (today - timedelta(days=days_ago)).isoformat(),
            "description": f"Expense - {cat}",
            "category": cat,
            "amount": -amt,
            "type": "expense",
            "account": "main",
            "balance_after": None,
            "source": "sample",
        })
    # Add more to reach 30
    idx = len(txns)
    while idx < 30:
        days_ago = (idx * 3) % 30
        txns.append({
            "date": (today - timedelta(days=days_ago)).isoformat(),
            "description": f"Operating transaction {idx}",
            "category": "misc" if idx % 2 else "revenue",
            "amount": 1000.0 + idx * 10,
            "type": "income" if idx % 2 == 0 else "expense",
            "account": "main",
            "balance_after": None,
            "source": "sample",
        })
        idx += 1
    return txns


def _emails():
    return [
        {
            "from_address": "billing@acmecorp.com", "subject":
            "Invoice INV-1001 payment received",
            "body": "We have transferred $12,500 for invoice INV-1001.", "days_ago": 14,
            "classification": "payment",
        },
        {
            "from_address": "ap@gamma-solutions.com", "subject":
            "Re: Invoice INV-1003",
            "body": "Attached is confirmation of payment of $8,400.", "days_ago": 12,
            "classification": "payment",
        },
        {
            "from_address": "accounts@betaindustries.com", "subject":
            "Invoice number INV-1002 due",
            "body": "Please send the full statement for invoice INV-1002 amount $23,000 due on ...",
            "days_ago": 9, "classification": "invoice",
        },
        {
            "from_address": "finance@deltaltd.com", "subject":
            "Overdue invoice INV-1010",
            "body": "We noticed invoice INV-1010 for $9,900 is now overdue. Reminder.", "days_ago": 6,
            "classification": "reminder",
        },
        {
            "from_address": "ap@iotaholdings.com", "subject":
            "Payment for INV-1012",
            "body": "We have processed payment of $7,200.", "days_ago": 5,
            "classification": "payment",
        },
        {
            "from_address": "payables@etaventures.co", "subject":
            "Invoice INV-1009",
            "body": "New invoice INV-1009 for $18,200 due within 30 days.", "days_ago": 4,
            "classification": "invoice",
        },
        {
            "from_address": "accounts@kappaltd.com", "subject":
            "Receipt for services",
            "body": "Please find receipt for $9900 payment.", "days_ago": 3,
            "classification": "payment",
        },
        {
            "from_address": "vendor@supplies.com", "subject":
            "Office supplies invoice",
            "body": "Invoice for $300 office supplies.", "days_ago": 2,
            "classification": "expense",
        },
        {
            "from_address": "billing@epsilongroup.io", "subject":
            "Payment due reminder",
            "body": "Invoice INV-1014 for $9,100 is overdue, please pay.", "days_ago": 1,
            "classification": "reminder",
        },
        {
            "from_address": "finance@thetasys.net", "subject":
            "Payment received INV-1015",
            "body": "We paid $5,400 for invoice INV-1015.", "days_ago": 0,
            "classification": "payment",
        },
    ]


def _healthy_scenario(base):
    return {
        "extra_emails": [],
        "overrides": [],
    }


def _cashflow_warning_scenario(base):
    return {
        "extra_emails": [
            {
                "from_address": "bank@notifications.example.com",
                "subject": "Low account balance alert",
                "body": "Your cash balance has fallen below $5,000. Recurring "
                        "payments due soon may not be covered.",
                "days_ago": 2, "classification": "other",
            }
        ],
        "overrides": [
            {"type": "expense", "category": "Salaries", "amount": 20000,
             "days_ago": 15, "recurring": 1},
        ],
    }


def _overdue_scenario(base):
    extra = [
        {
            "from_address": "finance@deltaltd.com",
            "subject": "Invoice INV-1004 overdue 30 days",
            "body": "Final notice: invoice INV-1004 for $16,000 is 30 days "
                    "overdue. Please arrange immediate payment.",
            "days_ago": 5, "classification": "reminder",
        },
        {
            "from_address": "accounts@betaindustries.com",
            "subject": "INV-1012 payment delay",
            "body": "We are unable to process payment for INV-1012 this month.",
            "days_ago": 3, "classification": "reminder",
        },
    ]
    return {"extra_emails": extra, "overrides": []}


def _high_expense_scenario(base):
    overrides = {
        "expenses": [
            ("Equipment", 25000, 10, False),
        ],
        "emails": [
            {
                "from_address": "landlord@office.com",
                "subject": "Rent increase notice",
                "body": "Monthly rent will increase to $5,500 effective "
                        "next month.",
                "days_ago": 4, "classification": "expense",
            },
        ],
    }
    return {"extra_emails": overrides["emails"],
            "overrides": overrides["expenses"]}


def load_sample_data(db: Database, scenario: int = 0):
    """Load sample data into the DB. Does NOT use AI - deterministic."""
    db.clear_all()
    svc = FinanceService(db)
    data_dir = Path(__file__).parent / "data"
    import csv as _csv

    # Customers
    cust_rows = _read_csv(data_dir / "sample_customers.csv")
    for r in cust_rows:
        svc.create_customer(Customer(
            name=r["name"], email=r.get("email"), phone=r.get("phone"),
            company=r.get("company"), address=r.get("address"),
        ))

    # Invoices
    inv_rows = _read_csv(data_dir / "sample_invoices.csv")
    for r in inv_rows:
        svc.create_invoice_unique(
            invoice_number=r["invoice_number"],
            customer_id=int(r["customer_id"]),
            amount=float(r["amount"]),
            issue_date=r["issue_date"],
            due_date=r["due_date"],
            status=r["status"],
            description=r.get("description"),
        )

    # Payments for partially paid / consistent history
    _seed_payments(svc)

    # Expenses
    exp_rows = _read_csv(data_dir / "sample_expenses.csv")
    for r in exp_rows:
        svc.create_expense(Expense(
            category=r["category"], description=r.get("description"),
            amount=float(r["amount"]), expense_date=r["expense_date"],
            vendor=r.get("vendor"), recurring=int(r.get("recurring", 0)),
        ))

    # Scenario-specific adjustments
    _apply_scenario(db, svc, scenario)

    # Transactions (cash history) - only load income transactions.
    # Expense transactions are auto-created by create_expense above.
    tx_rows = _read_csv(data_dir / "sample_transactions.csv")
    for r in tx_rows:
        if r.get("type") == "income":
            svc._record_transaction(
                date=r["date"], description=r["description"],
                category=r.get("category"), amount=float(r["amount"]),
                type=r["type"], source=r.get("source", "sample"),
                balance_after=r.get("balance_after"),
            )

    # Emails
    em_rows = _read_csv(data_dir / "sample_emails.csv")
    for r in em_rows:
        db.execute(
            "INSERT INTO emails (from_address, subject, body, received_at, "
            "classification, processed) VALUES (?, ?, ?, ?, ?, 1)",
            (r["from_address"], r["subject"], r["body"],
             (date.today() - __import__("datetime").timedelta(
                 days=int(r["days_ago"]))).strftime("%Y-%m-%d %H:%M:%S"),
             r["classification"]),
        )

    extra = _read_csv(data_dir / f"scenario_{scenario}_emails.csv")
    for r in extra:
        db.execute(
            "INSERT INTO emails (from_address, subject, body, received_at, "
            "classification, processed) VALUES (?, ?, ?, ?, ?, 1)",
            (r["from_address"], r["subject"], r["body"],
             (date.today() - __import__("datetime").timedelta(
                 days=int(r["days_ago"]))).strftime("%Y-%m-%d %H:%M:%S"),
             r.get("classification", "other")),
        )

    # Recompute transaction balances
    _recompute_balances(db)
    return db


def _read_csv(path):
    if not Path(path).exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _seed_payments(svc):
    """Create plausible payment history for some invoices."""
    today = date.today()
    # Mark a couple invoices as paid
    paid_invoices = ["INV-1001", "INV-1002"]
    for num in paid_invoices:
        inv = svc.get_invoice_by_number(num)
        if inv and inv["status"] != "paid":
            from models import Payment
            svc.record_payment(Payment(
                invoice_id=inv["id"], customer_id=inv["customer_id"],
                amount=inv["amount"],
                payment_date=(today - timedelta(days=3)).isoformat(),
                method="transfer", reference="sample", recorded_by="sample",
            ))
    # Partial payment on another
    inv = svc.get_invoice_by_number("INV-1012")
    if inv and inv["status"] != "paid":
        from models import Payment
        svc.record_payment(Payment(
            invoice_id=inv["id"], customer_id=inv["customer_id"],
            amount=2000.0, payment_date=(today - timedelta(days=5)).isoformat(),
            method="transfer", reference="partial", recorded_by="sample",
        ))


def _apply_scenario(db, svc, scenario):
    """Scenario-specific overrides."""
    if scenario == 0:
        return
    if scenario == 1:  # cash-flow warning: big recurring expense
        svc.create_expense(Expense(
            category="Salaries", description="Emergency payroll",
            amount=20000.0, expense_date=(date.today() - timedelta(days=2))
            .isoformat(), vendor="Staff", recurring=1,
        ))
        # Large outflow to deplete cash reserves
        svc._record_transaction(
            date=(date.today() - timedelta(days=1)).isoformat(),
            description="Quarterly tax settlement",
            category="Taxes", amount=-140000.0, type="expense",
            source="scenario",
        )
    elif scenario == 2:  # overdue: already some overdue from base; escalate
        # Advance a given invoice due date if needed
        pass
    elif scenario == 3:  # high expense
        svc.create_expense(Expense(
            category="Equipment", description="Urgent equipment purchase",
            amount=25000.0, expense_date=(date.today() - timedelta(days=10))
            .isoformat(), vendor="VendorX", recurring=0,
        ))
        svc.create_expense(Expense(
            category="Equipment Leasing", description="Large equipment lease",
            amount=15000.0, expense_date=(date.today() - timedelta(days=5))
            .isoformat(), vendor="LeaseCo", recurring=1,
        ))
        svc._record_transaction(
            date=(date.today() - timedelta(days=10)).isoformat(),
            description="Equipment purchase",
            category="Equipment", amount=-25000.0, type="expense",
            source="scenario",
        )


def _recompute_balances(db):
    rows = db.query("SELECT id, amount FROM transactions ORDER BY id")
    running = 0.0
    for r in rows:
        running += r["amount"]
        db.execute("UPDATE transactions SET balance_after = ? WHERE id = ?",
                   (round(running, 2), r["id"]))
