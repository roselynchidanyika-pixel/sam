import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")


class Config:
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "financial_os.db"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    GMAIL_SCOPES = os.getenv(
        "GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.modify"
    ).split(",")
    BUSINESS_OWNER_EMAIL = os.getenv("BUSINESS_OWNER_EMAIL", "")
    HUMAN_APPROVAL_REQUIRED = os.getenv("HUMAN_APPROVAL_REQUIRED", "true").lower() == "true"
    GMAIL_CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL_MINUTES", "5"))
    REMINDER_ENABLED = os.getenv("REMINDER_ENABLED", "true").lower() == "true"
    TIMEZONE = os.getenv("TIMEZONE", "UTC")

    TAX_RATE = 0.10
    CURRENCY = "USD"

    ESCALATION_LEVELS = {
        "gentle": {"days_before": 7, "days_after": 0, "template": "gentle"},
        "firm": {"days_before": 0, "days_after": 0, "template": "firm"},
        "final": {"days_before": 0, "days_after": 7, "template": "final"},
        "legal": {"days_before": 0, "days_after": 30, "template": "legal"},
    }

    EXPENSE_CATEGORIES = [
        "Rent", "Utilities", "Salaries", "Software", "Marketing",
        "Office Supplies", "Travel", "Insurance", "Legal", "Consulting",
        "Equipment", "Maintenance", "Subscriptions", "Taxes", "Other",
    ]
