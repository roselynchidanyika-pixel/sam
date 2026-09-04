from datetime import date, timedelta

from models import Customer, Invoice, Payment
from services import FinanceService


class TestCustomers:
    def test_create_and_get(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="TestCo", email="t@t.com"))
        c = svc.get_customer(cid)
        assert c["name"] == "TestCo"

    def test_get_or_create_by_name(self, db_and_svc):
        db, svc = db_and_svc
        cid1 = svc.get_or_create_customer_by_name("Alpha", "a@b.com")
        cid2 = svc.get_or_create_customer_by_name("Alpha")
        assert cid1 == cid2

    def test_list_customers(self, db_and_svc):
        db, svc = db_and_svc
        svc.create_customer(Customer(name="X"))
        svc.create_customer(Customer(name="Y"))
        assert len(svc.list_customers()) == 2


class TestInvoices:
    def test_create_invoice(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C1", email="c1@x.com"))
        inv = Invoice(invoice_number="INV-001", customer_id=cid, amount=1000.0,
                      issue_date="2026-01-01", due_date="2026-02-01")
        iid = svc.create_invoice(inv)
        row = svc.get_invoice(iid)
        assert row["amount"] == 1000.0
        assert row["status"] == "issued"

    def test_create_invoice_unique_dedup(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        id1 = svc.create_invoice_unique("INV-DUP", cid, 500, "2026-01-01",
                                        "2026-02-01")
        id2 = svc.create_invoice_unique("INV-DUP", cid, 500, "2026-01-01",
                                        "2026-02-01")
        assert id1 == id2

    def test_update_status(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        iid = svc.create_invoice_unique("INV-U01", cid, 800, "2026-01-01",
                                        "2026-02-01")
        svc.update_invoice_status(iid, "paid")
        assert svc.get_invoice(iid)["status"] == "paid"

    def test_invoices_overdue(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        svc.create_invoice_unique("INV-OVR", cid, 2000, "2025-12-01",
                                  "2026-01-01")
        overdue = svc.invoices_overdue("2026-06-01")
        assert len(overdue) >= 1
        assert any(o["invoice_number"] == "INV-OVR" for o in overdue)

    def test_accounts_receivable(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        svc.create_invoice_unique("INV-AR1", cid, 3000, "2026-01-01",
                                  "2026-02-01")
        svc.create_invoice_unique("INV-AR2", cid, 2000, "2026-01-01",
                                  "2026-02-01")
        ar = svc.accounts_receivable()
        assert ar >= 5000.0

    def test_is_invoice_paid(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        iid = svc.create_invoice_unique("INV-PAID", cid, 1000, "2026-01-01",
                                        "2026-02-01")
        assert not svc.is_invoice_paid(iid)
        svc.record_payment(Payment(invoice_id=iid, customer_id=cid,
                                   amount=1000, payment_date="2026-01-15"))
        assert svc.is_invoice_paid(iid)

    def test_list_invoices(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="C", email="c@x.com"))
        for i in range(3):
            svc.create_invoice_unique(f"INV-L{i}", cid, 100, "2026-01-01",
                                      "2026-02-01")
        assert len(svc.list_invoices()) >= 3
