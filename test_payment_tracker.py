from models import Customer, Invoice, Payment
from services import FinanceService


class TestPayments:
    def test_record_payment(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="P", email="p@x.com"))
        iid = svc.create_invoice_unique("INV-P01", cid, 5000, "2026-01-01",
                                        "2026-02-01")
        pid = svc.record_payment(Payment(
            invoice_id=iid, customer_id=cid, amount=5000,
            payment_date="2026-01-20", method="transfer", reference="ref1",
        ))
        assert pid > 0
        inv = svc.get_invoice(iid)
        assert inv["status"] == "paid"

    def test_partial_payment(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="P", email="p@x.com"))
        iid = svc.create_invoice_unique("INV-PP1", cid, 5000, "2026-01-01",
                                        "2026-02-01")
        svc.record_payment(Payment(
            invoice_id=iid, customer_id=cid, amount=2000,
            payment_date="2026-01-15",
        ))
        inv = svc.get_invoice(iid)
        assert inv["status"] == "partial"
        paid = svc.subtotal_invoice(iid)
        assert paid == 2000.0

    def test_payments_for_invoice(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="P", email="p@x.com"))
        iid = svc.create_invoice_unique("INV-PF", cid, 3000, "2026-01-01",
                                        "2026-02-01")
        svc.record_payment(Payment(invoice_id=iid, customer_id=cid,
                                   amount=1000, payment_date="2026-01-10"))
        svc.record_payment(Payment(invoice_id=iid, customer_id=cid,
                                   amount=2000, payment_date="2026-01-20"))
        ps = svc.payments_for_invoice(iid)
        assert len(ps) == 2
        assert sum(p["amount"] for p in ps) == 3000.0

    def test_list_payments(self, db_and_svc):
        db, svc = db_and_svc
        cid = svc.create_customer(Customer(name="P", email="p@x.com"))
        iid = svc.create_invoice_unique("INV-PL", cid, 1000, "2026-01-01",
                                        "2026-02-01")
        svc.record_payment(Payment(invoice_id=iid, customer_id=cid,
                                   amount=500, payment_date="2026-01-05"))
        assert len(svc.list_payments()) >= 1

    def test_total_revenue(self, db_and_svc):
        db, svc = db_and_svc
        assert isinstance(svc.total_revenue(), float)
