from datetime import date

from database import Database, AuditLogger, get_setting, set_setting
from models import Customer, Invoice, Payment, Expense


class TestDatabaseSchema:
    def test_initialize_creates_tables(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        tables = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('customers','invoices','payments','expenses',"
            "'transactions','emails','reminders','audit_log','settings')"
        )
        table_names = {t["name"] for t in tables}
        assert "customers" in table_names
        assert "invoices" in table_names
        assert "payments" in table_names
        assert "expenses" in table_names

    def test_clear_all(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        db.execute("INSERT INTO customers (name, email) VALUES ('X', 'x@x.com')")
        assert db.query_one("SELECT COUNT(*) as c FROM customers")["c"] == 1
        db.clear_all()
        assert db.query_one("SELECT COUNT(*) as c FROM customers")["c"] == 0


class TestAuditLogger:
    def test_log_entry(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        audit = AuditLogger(db)
        audit.log("test_user", "create", "customers", 1, "Created test")
        row = db.query_one("SELECT * FROM audit_log WHERE action = 'create'")
        assert row is not None
        assert row["actor"] == "test_user"
        assert row["details"] == "Created test"


class TestSettings:
    def test_set_get(self, tmp_path):
        db = Database(str(tmp_path / "test.db"))
        set_setting(db, "k", "v")
        assert get_setting(db, "k") == "v"
        assert get_setting(db, "missing", "default") == "default"
        set_setting(db, "k", "v2")
        assert get_setting(db, "k") == "v2"
