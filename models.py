from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Customer:
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self):
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Invoice:
    invoice_number: str
    customer_id: Optional[int]
    amount: float
    issue_date: str
    due_date: str
    status: str = "issued"
    currency: str = "USD"
    description: Optional[str] = None
    id: Optional[int] = None

    @property
    def is_overdue(self):
        from datetime import date
        try:
            due = date.fromisoformat(self.due_date)
            return due < date.today() and self.status != "paid"
        except ValueError:
            return False


@dataclass
class Payment:
    invoice_id: Optional[int]
    customer_id: Optional[int]
    amount: float
    payment_date: str
    method: str = "transfer"
    reference: Optional[str] = None
    recorded_by: str = "system"
    id: Optional[int] = None


@dataclass
class Expense:
    category: str
    amount: float
    expense_date: str
    description: Optional[str] = None
    vendor: Optional[str] = None
    recurring: int = 0
    id: Optional[int] = None


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    type: str  # income | expense
    category: Optional[str] = None
    account: str = "main"
    balance_after: Optional[float] = None
    source: str = "manual"
    id: Optional[int] = None


@dataclass
class Email(Invoice):
    pass
