import sys
from pathlib import Path
from datetime import date, timedelta

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from services import FinanceService
from cashflow import CashFlowAnalyzer, ForecastEngine
from models import Customer, Invoice, Payment, Expense
from ai_agent import AIRuleEngine


@pytest.fixture
def tmp_db(tmp_path):
    """Return a fresh in-memory-like temp DB."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    # cleanup automatic via tmp_path


@pytest.fixture
def db_and_svc(tmp_db):
    return tmp_db, FinanceService(tmp_db)


@pytest.fixture
def rule_engine():
    return AIRuleEngine()
