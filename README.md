# AI Financial Operating System (AI Financial OS)

A complete, AI-powered financial management system for SMEs, built with Python + Streamlit + SQLite + OpenAI API + Gmail API.

## Features

- **Automated Gmail Monitoring** – Reads and classifies incoming financial emails
- **AI Email Agent** – Classifies emails as invoice/payment/reminder/expense using OpenAI (with rule-based fallback)
- **Invoice Management** – Create, track, update invoices with automatic status management
- **Payment Tracking** – Record payments, auto-update invoice status (partial/paid)
- **Automatic Payment Reminders** – 4-level escalation (gentle → firm → final → legal)
- **Expense Management** – Track and categorize all business expenses
- **Cash Flow Analysis** – Monthly cash flow series, running balance
- **30/60/90-Day Forecast** – Projected income, expense, and cash balance
- **Weekly Financial Report** – Automated summary of weekly financial activity
- **AI Recommendations** – Rule-based financial insights (with OpenAI upgrade)
- **Email Composer** – Send emails with AI processing and owner notification
- **Audit Log** – Complete trace of all system actions
- **Human Approval Mode** – Optional safety gate before sending financial emails
- **Demo Data & Test Scenarios** – One-click load of realistic sample data or 4 business stress-test scenarios (auto-loads on first run)

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Overview with KPIs, charts, forecasts, risks, AI insights |
| **Invoices** | View/create invoices, filter by status |
| **Payments** | View/record payments, link to invoices |
| **Expenses** | View/add expenses, category breakdown |
| **Cash Flow & Forecast** | Monthly trends, 30/60/90-day projections |
| **Emails** | View processed emails, manual Gmail fetch |
| **Reports** | Weekly report, risk analysis, recommendations |
| **Email Composer** | Compose → AI process → DB update → send → audit |
| **Audit Log** | View all system actions |
| **Demo Data** | Load sample data or run one of 4 business stress-test scenarios |
| **Settings** | Configuration, demo data, reminders |

> **Visual theme**: the dashboard ships with a professional **dark navy + dark green**
> theme (see `.streamlit/config.toml` and the `THEME` dict in `app.py`).

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/youruser/ai-financial-os.git
cd ai-financial-os
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt        # runtime deps
pip install -r requirements-dev.txt   # optional: pytest + schedule
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env with your keys
```

### 3. Run

```bash
streamlit run app.py
```

On the **first run** (empty database) the app auto-loads healthy sample data so the
dashboard is never empty. To explore the other business situations or reload demo
data at any time, use the **🎛️ Demo Data** page or the **🎛️ Demo Data** expander in
the sidebar (loads scenarios 0–3).

---

## Project Structure

```
ai_financial_os/
├── app.py                  # Main Streamlit dashboard
├── config.py               # Configuration (from .env)
├── database.py             # SQLite schema + CRUD
├── models.py               # Data models
├── services.py             # Core business logic
├── cashflow.py             # Cash-flow analysis + forecasting
├── reports.py              # Reporting + AI recommendations
├── email_agent.py          # Email classification + processing
├── email_composer.py       # Outbound email flow
├── gmail_client.py         # Gmail API integration
├── ai_agent.py             # OpenAI API + rule-based fallback
├── reminders.py            # Payment reminder engine
├── sample_data.py          # Sample data generator
├── setup_gmail.py          # Gmail API setup helper
├── requirements.txt        # Runtime deps (used by Streamlit Cloud/Docker)
├── requirements-dev.txt    # Dev/test deps (pytest, schedule)
├── .env.example
├── .gitignore
├── Dockerfile
├── .streamlit/
│   └── config.toml
├── data/
│   ├── generate_csv.py     # One-time CSV generator
│   ├── sample_customers.csv
│   ├── sample_invoices.csv
│   ├── sample_expenses.csv
│   ├── sample_transactions.csv
│   ├── sample_emails.csv
│   └── scenario_*.csv
└── tests/
    ├── conftest.py
    ├── test_database.py
    ├── test_invoice_manager.py
    ├── test_payment_tracker.py
    ├── test_expense_manager.py
    ├── test_cashflow.py
    ├── test_forecast.py
    ├── test_email_processor.py
    ├── test_ai_agent.py
    ├── test_scenarios.py
    └── test_report.py
```

---

## Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. **Enable Gmail API**: APIs & Services → Library → search "Gmail API" → Enable
4. **Create OAuth credentials**: APIs & Services → Credentials → Create Credentials → OAuth client ID → Application type: **Desktop app** → Name: "AI Financial OS"
5. **Download credentials.json** and place in project root
6. **Run setup**: `python setup_gmail.py`
7. Browser opens → log in → authorise
8. `token.json` is saved automatically

### Gmail Scopes Required
- `gmail.readonly` – Read incoming emails
- `gmail.send` – Send emails (reminders, owner notifications)
- `gmail.modify` – Mark emails as read

---

## OpenAI API Setup

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an API key
3. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

**Without OpenAI**: The system works fully using the rule-based fallback engine. All financial calculations (cash flow, forecasting, payment tracking) are independent of AI.

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_scenarios.py -v
```

---

## Test Scenarios

| Scenario | Description | Key Metrics |
|----------|-------------|-------------|
| **0 – Healthy** | Regular payments, moderate expenses, positive cash flow | Positive balance, low overdue, 30-day forecast positive |
| **1 – Cash-flow Warning** | Large unexpected expense depletes reserves | Low runway, possible negative 90-day projection |
| **2 – Overdue Invoices** | Multiple unpaid invoices past due | High overdue ratio, aging AR |
| **3 – High-Expense Risk** | Expenses growing faster than revenue | High burn rate, deteriorating 90-day forecast |

---

## Streamlit Cloud Deployment

1. Push to GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io)
3. Click "New app" → select your repo → set path to `ai_financial_os/app.py`
4. Add secrets in Streamlit Cloud settings:
   ```toml
   [env]
   OPENAI_API_KEY = "sk-..."
   BUSINESS_OWNER_EMAIL = "you@gmail.com"
   HUMAN_APPROVAL_REQUIRED = "true"
   ```
5. Click "Deploy"

> **Troubleshooting "Error installing requirements"**
> `requirements.txt` contains **only runtime dependencies** with relaxed,
> resolver-compatible version ranges. Test-only packages (`pytest`,
> `pytest-cov`, `schedule`) live in `requirements-dev.txt`, so they are **not**
> installed on the Streamlit Cloud build. If you still hit an install error,
> the most likely cause is an incompatible pinned transitive version:
> remove the exact version pins (or widen them) and retry. Verified working
> on Streamlit Cloud with Python 3.11.

**Note**: Gmail API requires credentials.json and token.json (OAuth). For Streamlit Cloud, you'll need to handle auth differently (service account or manual token setup). For production, consider a server-based deployment.

---

## Docker Deployment

```bash
docker build -t ai-financial-os .
docker run -p 8501:8501 \
  -v $(pwd)/financial_os.db:/app/financial_os.db \
  ai-financial-os
```

---

## Architecture Notes

- **Financial calculations are 100% independent of AI** – cash flow, forecasting, payment tracking, and all arithmetic use pure Python
- **AI is optional** – provides smarter email classification and recommendations when available
- **SQLite** is used for simplicity; replace with PostgreSQL for production
- **Gmail polling** is manual in the Streamlit app (button-based) for MVP; add `schedule` for automated background polling in production
- **Human approval mode** adds a safety gate before any outbound financial email is sent
