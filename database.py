import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    address TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT DEFAULT 'issued',
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER REFERENCES invoices(id),
    customer_id INTEGER REFERENCES customers(id),
    amount REAL NOT NULL,
    payment_date TEXT NOT NULL,
    method TEXT DEFAULT 'transfer',
    reference TEXT,
    recorded_by TEXT DEFAULT 'system',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    description TEXT,
    amount REAL NOT NULL,
    expense_date TEXT NOT NULL,
    vendor TEXT,
    recurring INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    description TEXT,
    category TEXT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,          -- 'income' | 'expense'
    account TEXT DEFAULT 'main',
    balance_after REAL,
    source TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id TEXT UNIQUE,
    from_address TEXT,
    to_address TEXT,
    subject TEXT,
    body TEXT,
    received_at TEXT NOT NULL,
    classification TEXT,          -- invoice | payment | reminder | expense | other
    client_name TEXT,
    amount REAL,
    invoice_number TEXT,
    due_date TEXT,
    action_required TEXT,
    processed INTEGER DEFAULT 0,
    sent INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER REFERENCES invoices(id),
    customer_id INTEGER REFERENCES customers(id),
    level TEXT NOT NULL,
    due_date TEXT NOT NULL,
    sent_date TEXT,
    status TEXT DEFAULT 'pending',
    email_subject TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS forecast_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    period INTEGER,
    projected_income REAL,
    projected_expense REAL,
    net_cashflow REAL
);

CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(processed);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
"""


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).parent / "financial_os.db"
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def execute(self, sql, params=()):
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid

    def executemany(self, sql, params_list):
        with self.connect() as conn:
            conn.executemany(sql, params_list)

    def query(self, sql, params=()):
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def clear_all(self):
        with self.connect() as conn:
            for table in [
                "forecast_cache", "settings", "audit_log", "reminders", "emails",
                "transactions", "expenses", "payments", "invoices", "customers",
            ]:
                conn.execute(f"DELETE FROM {table}")
                conn.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")


class AuditLogger:
    def __init__(self, db: Database):
        self.db = db

    def log(self, actor: str, action: str, entity_type=None,
            entity_id=None, details=None):
        self.db.execute(
            "INSERT INTO audit_log (actor, action, entity_type, entity_id, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (actor, action, entity_type, entity_id, details),
        )


def get_setting(db: Database, key: str, default=None):
    row = db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row and "value" in row else default


def set_setting(db: Database, key: str, value: str):
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
