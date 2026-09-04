from datetime import date, timedelta

from database import Database, AuditLogger
from models import Customer, Invoice, Payment, Expense, Transaction


class FinanceService:
    def __init__(self, db: Database):
        self.db = db
        self.audit = AuditLogger(db)

    # ---------------- Customers ----------------
    def create_customer(self, customer: Customer) -> int:
        cid = self.db.execute(
            "INSERT INTO customers (name, email, phone, company, address) "
            "VALUES (?, ?, ?, ?, ?)",
            (customer.name, customer.email, customer.phone,
             customer.company, customer.address),
        )
        self.audit.log("system", "create_customer", "customers", cid,
                       f"Created customer {customer.name}")
        return cid

    def get_customer(self, customer_id: int) -> dict:
        return self.db.query_one(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        )

    def get_or_create_customer_by_name(self, name: str, email: str = None) -> int:
        if name:
            row = self.db.query_one(
                "SELECT id FROM customers WHERE LOWER(name) = LOWER(?)", (name,)
            )
            if row:
                return row["id"]
        if email:
            row = self.db.query_one(
                "SELECT id FROM customers WHERE email = ?", (email,)
            )
            if row:
                return row["id"]
        default_email = email or f"{name.lower().replace(' ', '.')}@example.com"
        return self.create_customer(Customer(name=name, email=default_email))

    def list_customers(self) -> list:
        return self.db.query(
            "SELECT * FROM customers ORDER BY name"
        )

    # ---------------- Invoices ----------------
    def create_invoice(self, invoice: Invoice) -> int:
        iid = self.db.execute(
            "INSERT INTO invoices (invoice_number, customer_id, amount, currency, "
            "issue_date, due_date, status, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (invoice.invoice_number, invoice.customer_id, invoice.amount,
             invoice.currency, invoice.issue_date, invoice.due_date,
             invoice.status, invoice.description),
        )
        # NOTE: An invoice creates a receivable, not immediate cash.
        # Income transactions are only recorded when a payment is received.
        self.audit.log("system", "create_invoice", "invoices", iid,
                       f"Invoice {invoice.invoice_number} amount {invoice.amount}")
        return iid

    def create_invoice_unique(self, invoice_number: str, customer_id, amount,
                              issue_date, due_date, status="issued",
                              description=None) -> int:
        existing = self.db.query_one(
            "SELECT id FROM invoices WHERE invoice_number = ?", (invoice_number,)
        )
        if existing:
            return existing["id"]
        inv = Invoice(
            invoice_number=invoice_number, customer_id=customer_id, amount=amount,
            issue_date=issue_date, due_date=due_date, status=status,
            description=description,
        )
        return self.create_invoice(inv)

    def get_invoice(self, invoice_id: int) -> dict:
        return self.db.query_one("SELECT * FROM invoices WHERE id = ?", (invoice_id,))

    def get_invoice_by_number(self, number: str) -> dict:
        return self.db.query_one(
            "SELECT * FROM invoices WHERE invoice_number = ?", (number,)
        )

    def update_invoice_status(self, invoice_id: int, status: str):
        self.db.execute(
            "UPDATE invoices SET status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (status, invoice_id),
        )
        self.audit.log("system", "update_invoice_status", "invoices", invoice_id,
                       f"Status -> {status}")

    def list_invoices(self, include_paid: bool = True):
        q = "SELECT * FROM invoices"
        if not include_paid:
            q += " WHERE status != 'paid'"
        return self.db.query(q + " ORDER BY due_date")

    def invoices_outstanding(self):
        return self.db.query(
            "SELECT * FROM invoices WHERE status != 'paid' ORDER BY due_date"
        )

    def invoices_overdue(self, as_of=None):
        as_of = as_of or date.today().isoformat()
        return self.db.query(
            "SELECT * FROM invoices WHERE status != 'paid' AND due_date < ? "
            "ORDER BY due_date",
            (as_of,),
        )

    def accounts_receivable(self):
        """Sum of all outstanding invoice amounts (unpaid)."""
        rows = self.db.query(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM invoices "
            "WHERE status != 'paid'"
        )
        return float(rows[0]["total"]) if rows else 0.0

    def subtotal_invoice(self, invoice_id: int) -> float:
        """Amount paid toward an invoice."""
        row = self.db.query_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payments "
            "WHERE invoice_id = ?",
            (invoice_id,),
        )
        return row["total"] if row else 0.0

    def is_invoice_paid(self, invoice_id: int) -> bool:
        inv = self.get_invoice(invoice_id)
        if not inv or inv["status"] == "paid":
            return True
        paid = self.subtotal_invoice(invoice_id)
        return paid >= inv["amount"]

    # ---------------- Payments ----------------
    def record_payment(self, payment: Payment):
        pid = self.db.execute(
            "INSERT INTO payments (invoice_id, customer_id, amount, payment_date, "
            "method, reference, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (payment.invoice_id, payment.customer_id, payment.amount,
             payment.payment_date, payment.method, payment.reference,
             payment.recorded_by),
        )
        if payment.invoice_id:
            if self.is_invoice_paid(payment.invoice_id):
                self.update_invoice_status(payment.invoice_id, "paid")
            else:
                self.update_invoice_status(payment.invoice_id, "partial")

        self._record_transaction(
            date=payment.payment_date, description="Client payment",
            category="receipts", amount=payment.amount, type="income",
            source="payment", balance_after=None,
        )
        self.audit.log(payment.recorded_by, "record_payment", "payments", pid,
                       f"Payment {payment.amount} on invoice {payment.invoice_id}")
        return pid

    def list_payments(self, limit: int = 200):
        return self.db.query(
            "SELECT * FROM payments ORDER BY payment_date DESC LIMIT ?", (limit,)
        )

    def payments_for_invoice(self, invoice_id: int):
        return self.db.query(
            "SELECT * FROM payments WHERE invoice_id = ? ORDER BY payment_date",
            (invoice_id,),
        )

    # ---------------- Expenses ----------------
    def create_expense(self, expense: Expense) -> int:
        eid = self.db.execute(
            "INSERT INTO expenses (category, description, amount, expense_date, "
            "vendor, recurring) VALUES (?, ?, ?, ?, ?, ?)",
            (expense.category, expense.description, expense.amount,
             expense.expense_date, expense.vendor, expense.recurring),
        )
        self._record_transaction(
            date=expense.expense_date, description=expense.description or expense.category,
            category=expense.category, amount=-abs(expense.amount), type="expense",
            source="expense", balance_after=None,
        )
        self.audit.log("system", "create_expense", "expenses", eid,
                       f"Expense {expense.amount} in {expense.category}")
        return eid

    def list_expenses(self, limit: int = 500):
        return self.db.query(
            "SELECT * FROM expenses ORDER BY expense_date DESC LIMIT ?", (limit,)
        )

    def expenses_by_category(self):
        return self.db.query(
            "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses GROUP BY category ORDER BY total DESC"
        )

    def total_expenses(self, start=None, end=None) -> float:
        q = "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
        params = []
        conditions = []
        if start:
            conditions.append("expense_date >= ?")
            params.append(start)
        if end:
            conditions.append("expense_date <= ?")
            params.append(end)
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        row = self.db.query_one(q, tuple(params))
        return float(row["total"]) if row else 0.0

    def recurring_expenses_monthly(self) -> float:
        """Sum of recurring expenses (assumed monthly)."""
        row = self.db.query_one(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE recurring = 1"
        )
        return float(row["total"]) if row else 0.0

    # ---------------- Transactions ----------------
    def _record_transaction(self, date, description, category, amount, type,
                            source, balance_after=None):
        self.db.execute(
            "INSERT INTO transactions (date, description, category, amount, type, "
            "account, balance_after, source) VALUES (?, ?, ?, ?, ?, 'main', ?, ?)",
            (date, description, category, amount, type, balance_after, source),
        )

    def list_transactions(self, limit: int = 500):
        return self.db.query(
            "SELECT * FROM transactions ORDER BY date DESC, id DESC LIMIT ?",
            (limit,),
        )

    def total_revenue(self, start=None, end=None) -> float:
        q = "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type='income'"
        params = []
        conditions = []
        if start:
            conditions.append("date >= ?")
            params.append(start)
        if end:
            conditions.append("date <= ?")
            params.append(end)
        if conditions:
            q += " AND " + " AND ".join(conditions)
        row = self.db.query_one(q, tuple(params))
        return float(row["total"]) if row else 0.0

    def net_cashflow_period(self, start=None, end=None) -> float:
        income = self.total_revenue(start, end)
        expense = self.total_expenses(start, end)
        return income - expense
