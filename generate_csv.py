"""Generate all sample CSV data files used by sample_data.py.
Run once: python data/generate_csv.py
"""
import sys
import csv
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).parent
DATA = ROOT


def w(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def customers():
    d = [
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
    return [{"name": n, "email": e, "phone": p, "company": c, "address": a}
            for n, e, p, c, a in d]


def invoices():
    today = date.today()
    rows = []
    spec = [
        (0, 12500.00, 10, 20, "issued"),
        (1, 23000.00, 15, 15, "issued"),
        (2, 8400.00, 5, 25, "issued"),
        (3, 16000.00, 40, -10, "issued"),
        (4, 9100.00, 60, -25, "issued"),
        (5, 1500.00, 45, -15, "issued"),
        (6, 18200.00, 8, 22, "issued"),
        (7, 5400.00, 20, 10, "issued"),
        (8, 27700.00, 12, 18, "issued"),
        (9, 9900.00, 3, 27, "issued"),
        (0, 7200.00, 30, -5, "issued"),
        (1, 3400.00, 90, -45, "issued"),
        (2, 6100.00, 25, -8, "issued"),
        (3, 8300.00, 7, 23, "issued"),
        (4, 11200.00, 2, 28, "issued"),
    ]
    for i, (ci, amt, issue_ago, due_off, status) in enumerate(spec):
        issue = today - timedelta(days=issue_ago)
        due = today + timedelta(days=due_off)
        rows.append({
            "invoice_number": f"INV-{1001 + i}",
            "customer_id": ci + 1, "amount": amt, "currency": "USD",
            "issue_date": issue.isoformat(), "due_date": due.isoformat(),
            "status": status, "description": f"Services INV-{1001 + i}",
        })
    return rows


def expenses():
    today = date.today()
    rows = []
    spec = [
        ("Rent", 3500, 30, 1, "Office rent"),
        ("Salaries", 12000, 30, 1, "Monthly payroll"),
        ("Software", 800, 30, 1, "SaaS subscriptions"),
        ("Utilities", 450, 30, 1, "Electric + internet"),
        ("Insurance", 600, 30, 1, "Business insurance"),
        ("Marketing", 1200, 12, 0, "Ad campaign"),
        ("Marketing", 900, 8, 0, "Social ads"),
        ("Office Supplies", 250, 6, 0, "Stationery"),
        ("Travel", 750, 20, 0, "Client visit"),
        ("Consulting", 2000, 10, 0, "Legal consult"),
        ("Equipment", 1500, 60, 0, "Laptop purchase"),
        ("Software", 120, 15, 0, "One-time license"),
        ("Utilities", 480, 0, 0, "Water bill"),
        ("Subscriptions", 99, 4, 1, "Newsletter tool"),
        ("Marketing", 600, 25, 0, "Trade show"),
        ("Office Supplies", 300, 18, 0, "Printer cartridges"),
        ("Travel", 420, 14, 0, "Client lunch"),
        ("Consulting", 1500, 5, 0, "Tax prep"),
        ("Equipment", 2200, 70, 0, "Monitor + desk"),
        ("Insurance", 600, 90, 1, "Quarterly premium"),
    ]
    for i, (cat, amt, days_ago, rec, desc) in enumerate(spec):
        d = today - timedelta(days=days_ago)
        rows.append({
            "category": cat, "description": desc, "amount": amt,
            "expense_date": d.isoformat(), "vendor": "Various",
            "recurring": rec,
        })
    return rows


def transactions():
    today = date.today()
    rows = []
    income = [
        (15, 8000.0, "Invoice payment INV-1001"),
        (13, 12000.0, "Client milestone payment"),
        (10, 15000.0, "Invoice INV-1002 partial"),
        (25, 10000.0, "Retainer"),
        (8, 9000.0, "Project payment"),
        (5, 7000.0, "Invoice INV-1003"),
        (20, 6000.0, "Contract work"),
        (30, 13000.0, "Quarterly maintenance"),
    ]
    for d, amt, desc in income:
        rows.append({"date": (today - timedelta(days=d)).isoformat(),
                     "description": desc, "category": "revenue", "amount": amt,
                     "type": "income", "account": "main", "balance_after": "",
                     "source": "sample"})
    expense = [
        (1, 3500.0, "Rent"),
        (1, 450.0, "Utilities"),
        (2, 1200.0, "Marketing"),
        (3, 800.0, "Software"),
        (4, 600.0, "Insurance"),
        (9, 2000.0, "Consulting"),
        (12, 1500.0, "Equipment"),
        (16, 250.0, "Office Supplies"),
        (21, 750.0, "Travel"),
        (27, 420.0, "Travel"),
        (33, 990.0, "Subscriptions"),
        (39, 480.0, "Utilities"),
    ]
    for d, amt, cat in expense:
        rows.append({"date": (today - timedelta(days=d)).isoformat(),
                     "description": f"Expense - {cat}", "category": cat,
                     "amount": -amt, "type": "expense", "account": "main",
                     "balance_after": "", "source": "sample"})
    # Pad to 30
    i = 0
    while len(rows) < 30:
        days_ago = (i * 7) % 45
        if i % 3 == 0:
            rows.append({"date": (today - timedelta(days=days_ago)).isoformat(),
                         "description": f"Operating income {i}",
                         "category": "revenue", "amount": 5000.0 + i * 100,
                         "type": "income", "account": "main",
                         "balance_after": "", "source": "sample"})
        else:
            rows.append({"date": (today - timedelta(days=days_ago)).isoformat(),
                         "description": f"Operating cost {i}", "category": "misc",
                         "amount": -(300.0 + i * 25), "type": "expense",
                         "account": "main", "balance_after": "", "source": "sample"})
        i += 1
    return rows


def emails():
    return [
        {"from_address": "billing@acmecorp.com",
         "subject": "Invoice INV-1001 payment received",
         "body": "We have transferred $12,500 for invoice INV-1001.",
         "days_ago": 14, "classification": "payment"},
        {"from_address": "ap@gamma-solutions.com",
         "subject": "Re: Invoice INV-1003",
         "body": "Attached is confirmation of payment of $8,400.",
         "days_ago": 12, "classification": "payment"},
        {"from_address": "accounts@betaindustries.com",
         "subject": "Invoice number INV-1002 due",
         "body": "Please send the full statement for invoice INV-1002 amount $23,000.",
         "days_ago": 9, "classification": "invoice"},
        {"from_address": "finance@deltaltd.com",
         "subject": "Overdue invoice INV-1010",
         "body": "We noticed invoice INV-1010 for $9,900 is now overdue. Reminder.",
         "days_ago": 6, "classification": "reminder"},
        {"from_address": "ap@iotaholdings.com",
         "subject": "Payment for INV-1012",
         "body": "We have processed payment of $7,200.",
         "days_ago": 5, "classification": "payment"},
        {"from_address": "payables@etaventures.co",
         "subject": "Invoice INV-1009",
         "body": "New invoice INV-1009 for $18,200 due within 30 days.",
         "days_ago": 4, "classification": "invoice"},
        {"from_address": "accounts@kappaltd.com",
         "subject": "Receipt for services",
         "body": "Please find receipt for $9900 payment.",
         "days_ago": 3, "classification": "payment"},
        {"from_address": "vendor@supplies.com",
         "subject": "Office supplies invoice",
         "body": "Invoice for $300 office supplies.",
         "days_ago": 2, "classification": "expense"},
        {"from_address": "billing@epsilongroup.io",
         "subject": "Payment due reminder",
         "body": "Invoice INV-1014 for $9,100 is overdue, please pay.",
         "days_ago": 1, "classification": "reminder"},
        {"from_address": "finance@thetasys.net",
         "subject": "Payment received INV-1015",
         "body": "We paid $5,400 for invoice INV-1015.",
         "days_ago": 0, "classification": "payment"},
    ]


SCENARIOS = {
    0: ("scenario_0_emails.csv", "scenario_0_overrides.csv", []),
    1: ("scenario_1_emails.csv", "scenario_1_overrides.csv",
        [{"from_address": "bank@notifications.example.com",
          "subject": "Low account balance alert",
          "body": "Your cash balance has fallen below $5,000.",
          "days_ago": 2, "classification": "other"}]),
    2: ("scenario_2_emails.csv", "scenario_2_overrides.csv",
        [{"from_address": "finance@deltaltd.com",
          "subject": "Invoice INV-1004 overdue 30 days",
          "body": "Final notice invoice INV-1004 $16,000 overdue.",
          "days_ago": 5, "classification": "reminder"},
         {"from_address": "accounts@betaindustries.com",
          "subject": "INV-1012 payment delay",
          "body": "Unable to process payment for INV-1012 this month.",
          "days_ago": 3, "classification": "reminder"}]),
    3: ("scenario_3_emails.csv", "scenario_3_overrides.csv",
        [{"from_address": "landlord@office.com",
          "subject": "Rent increase notice",
          "body": "Monthly rent $5,500 effective next month.",
          "days_ago": 4, "classification": "expense"}]),
}


def main():
    w(DATA / "sample_customers.csv", customers())
    w(DATA / "sample_invoices.csv", invoices())
    w(DATA / "sample_expenses.csv", expenses())
    w(DATA / "sample_transactions.csv", transactions())
    w(DATA / "sample_emails.csv", emails())
    for k in range(4):
        fname, ofname, extra = SCENARIOS[k]
        w(DATA / fname, extra)
        w(DATA / ofname, [])
    print("CSV data files generated successfully.")


if __name__ == "__main__":
    main()