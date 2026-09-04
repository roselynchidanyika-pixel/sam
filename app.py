import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta

from config import Config
from database import Database, get_setting, set_setting
from services import FinanceService
from cashflow import CashFlowAnalyzer, ForecastEngine
from reports import ReportingService
from email_agent import EmailProcessor
from gmail_client import GmailClient, GmailUnavailableError
from email_composer import EmailComposer
from reminders import ReminderEngine
from ai_agent import get_ai_agent, get_rule_engine, AIUnavailableError
from sample_data import load_sample_data
from models import Customer, Invoice, Payment, Expense

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Financial OS",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme: professional dark blue + dark green palette
# ---------------------------------------------------------------------------
THEME = {
    "bg": "#0d1b2a",          # dark navy background
    "panel": "#14283c",       # card / secondary background
    "panel_alt": "#1b3a52",   # elevated card
    "border": "#274b66",      # borders
    "text": "#e6f0f7",        # light text
    "muted": "#8aa7bf",       # muted text
    "green": "#00c875",       # dark green accent
    "green_dark": "#0a9d5c",
    "blue": "#1f6feb",        # dark blue accent
    "blue_deep": "#0b3fa0",
    "red": "#ff5c5c",
    "amber": "#ffb020",
    "plotly_bg": "rgba(13,27,42,0)",
}

# Plotly template tuned to the dark theme
PLOTLY_TEMPLATE = go.layout.Template(
    layout=dict(
        font=dict(color=THEME["text"]),
        xaxis=dict(
            gridcolor="rgba(139,167,191,0.12)",
            linecolor=THEME["border"],
            tickfont=dict(color=THEME["muted"]),
            title_font=dict(color=THEME["muted"]),
            zerolinecolor=THEME["border"],
        ),
        yaxis=dict(
            gridcolor="rgba(139,167,191,0.12)",
            linecolor=THEME["border"],
            tickfont=dict(color=THEME["muted"]),
            title_font=dict(color=THEME["muted"]),
            zerolinecolor=THEME["border"],
        ),
    )
)


def style_chart(fig, title=None, height=320, legend=True):
    """Apply the dark professional theme to a Plotly figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=THEME["plotly_bg"],
        plot_bgcolor="rgba(13,27,42,0.35)",
        font=dict(color=THEME["text"], family="'Inter', 'Segoe UI', sans-serif"),
        title=dict(
            text=title,
            font=dict(color=THEME["text"], size=15, family="'Inter', 'Segoe UI', sans-serif"),
            x=0.03,
            xanchor="left",
        ),
        margin=dict(l=10, r=10, t=45 if title else 20, b=10),
        height=height,
        showlegend=legend,
        legend=dict(
            bgcolor="rgba(13,27,42,0)",
            font=dict(color=THEME["muted"]),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    return fig


def apply_theme_css():
    """Inject dark-theme CSS for a polished, glassy look."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Base surface */
        .stApp, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(1200px 600px at 15% -10%, rgba(27,58,82,0.55), transparent 60%),
                radial-gradient(1000px 500px at 110% 10%, rgba(11,63,160,0.28), transparent 55%),
                linear-gradient(180deg, {THEME['bg']} 0%, #0a1622 100%);
            color: {THEME['text']};
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}

        /* Block container / cards */
        .block-container {{ padding-top: 1.6rem; padding-bottom: 2.5rem; }}

        /* Headings */
        h1, h2, h3, h4 {{
            color: {THEME['text']} !important;
            letter-spacing: -0.01em;
        }}
        h1 {{
            background: linear-gradient(90deg, {THEME['green']}, {THEME['blue']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}

        /* Plain markdown text */
        .stMarkdown p {{ color: {THEME['text']}; }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background: linear-gradient(160deg, {THEME['panel']} 0%, {THEME['panel_alt']} 100%);
            border: 1px solid {THEME['border']};
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.35);
        }}
        [data-testid="stMetric"] label {{ color: {THEME['muted']} !important; }}
        [data-testid="stMetricValue"] {{
            color: {THEME['text']} !important;
            font-weight: 700;
        }}
        [data-testid="stMetricDelta"] {{ color: {THEME['green']} !important; }}

        /* Dataframes */
        [data-testid="stDataFrame"] {{
            background: {THEME['panel']};
            border: 1px solid {THEME['border']};
            border-radius: 12px;
            overflow: hidden;
        }}
        [data-testid="stDataFrame"] .stTable thead th {{
            background: {THEME['panel_alt']} !important;
            color: {THEME['green']} !important;
            font-weight: 600;
        }}

        /* Buttons */
        .stButton > button {{
            background: linear-gradient(90deg, {THEME['blue_deep']}, {THEME['green_dark']});
            color: {THEME['text']};
            border: none;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            box-shadow: 0 4px 12px rgba(0,200,117,0.18);
            transition: all .15s ease;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(0,200,117,0.30);
        }}

        /* Branded blue -> emerald -> white upload button */
        .stButton > button[kind="secondary"][data-testid="baseButton-secondary"] {{
            background: linear-gradient(90deg, #1266e3 0%, #0aa26b 55%, #00c875 100%);
            color: #ffffff;
            border: 1px solid rgba(255,255,255,0.25);
        }}
        .stButton > button[kind="secondary"][data-testid="baseButton-secondary"]:hover {{
            background: linear-gradient(90deg, #1b74f0 0%, #0fbb7c 55%, #14d983 100%);
            box-shadow: 0 6px 18px rgba(18,200,117,0.45);
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{
            background: {THEME['panel']};
            border-radius: 8px 8px 0 0;
            padding: 6px 16px;
        }}
        .stTabs [aria-selected="true"] {{ background: {THEME['blue_deep']}; }}

        /* Inputs / text / textarea / select */
        .stTextInput input, .stTextArea textarea, .stNumberInput input,
        .stDateInput input, .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {{
            background-color: {THEME['panel']} !important;
            color: {THEME['text']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 10px !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0a1622 0%, {THEME['panel']} 100%);
            border-right: 1px solid {THEME['border']};
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {{
            -webkit-text-fill-color: {THEME['green']} !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            color: {THEME['muted']};
        }}
        [data-testid="stSidebar"] .stRadio label:hover {{
            color: {THEME['green']};
        }}

        /* Alerts / success / warning / info boxes */
        .stAlert {{
            background: {THEME['panel']};
            border: 1px solid {THEME['border']};
            border-radius: 12px;
        }}
        .stSuccess {{ border-left: 4px solid {THEME['green']}; }}
        .stWarning {{ border-left: 4px solid {THEME['amber']}; }}
        .stError   {{ border-left: 4px solid {THEME['red']}; }}
        .stInfo    {{ border-left: 4px solid {THEME['blue']}; }}

        /* Custom demo-data / status cards */
        .fos-card {{
            background: linear-gradient(160deg, {THEME['panel']}, {THEME['panel_alt']});
            border: 1px solid {THEME['border']};
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .fos-card h4 {{ margin: 0 0 4px 0; color: {THEME['green']}; }}
        .fos-card p {{ margin: 0; color: {THEME['muted']}; }}
        .fos-green {{ color: {THEME['green']}; font-weight: 700; }}
        .fos-red {{ color: {THEME['red']}; font-weight: 700; }}
        .fos-amber {{ color: {THEME['amber']}; font-weight: 700; }}

        /* Expander */
        [data-testid="stExpander"] {{
            background: {THEME['panel']};
            border: 1px solid {THEME['border']};
            border-radius: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme_css()

# ---------------------------------------------------------------------------
# Initialise DB (singleton in session_state)
# ---------------------------------------------------------------------------
@st.cache_resource
def _init_db():
    return Database(Config.DATABASE_PATH)

db = _init_db()
svc = FinanceService(db)
cashflow = CashFlowAnalyzer(db)
forecast = ForecastEngine(db)
reporting = ReportingService(db)
gmail = GmailClient()
email_processor = EmailProcessor(db, gmail)
email_composer = EmailComposer(db, gmail, email_processor)
reminder_engine = ReminderEngine(db, gmail)
audit_logger = __import__("database", fromlist=["AuditLogger"]).AuditLogger(db)


# ---------------------------------------------------------------------------
# Demo data: load on first run so the dashboard is never empty
# ---------------------------------------------------------------------------
HAS_DATA_KEY = "fos_has_data"

def _db_has_data():
    c = db.query_one("SELECT COUNT(*) AS c FROM customers")["c"]
    i = db.query_one("SELECT COUNT(*) AS c FROM invoices")["c"]
    return (c or 0) > 0 or (i or 0) > 0


def load_demo_data(scenario: int = 0):
    with st.spinner(f"Loading demo data for Scenario {scenario}..."):
        load_sample_data(db, scenario)
        st.session_state[HAS_DATA_KEY] = True
    st.success("Demo data loaded. Explore the dashboard below.")
    st.rerun()


# Auto-load healthy sample data on first ever run (only when table is empty)
if not _db_has_data():
    with st.spinner("First run detected — loading demo data (Scenario 0: Healthy)..."):
        try:
            load_sample_data(db, scenario=0)
            st.session_state[HAS_DATA_KEY] = True
        except Exception as e:
            st.sidebar.error(f"Could not auto-load demo data: {e}")

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("💼 AI Financial OS")
st.sidebar.caption("SME Financial Operating System")
PAGE_OPTIONS = ["Dashboard", "Invoices", "Payments", "Expenses",
                "Cash Flow & Forecast", "Emails", "Reports",
                "Email Composer", "Audit Log", "Demo Data", "Settings"]
# Allow programmatic navigation (e.g. "Settings -> Demo Data") while keeping
# the sidebar radio as the source of truth.
if "nav_target" not in st.session_state:
    st.session_state["nav_target"] = "Dashboard"
idx = PAGE_OPTIONS.index(st.session_state["nav_target"]) \
    if st.session_state["nav_target"] in PAGE_OPTIONS else 0
page = st.sidebar.radio(
    "Navigate",
    PAGE_OPTIONS,
    index=idx,
)
# Sync: a manual radio change updates the session target so programmatic buttons
# don't fight the widget on the next rerun.
if page != st.session_state["nav_target"]:
    st.session_state["nav_target"] = page
st.sidebar.markdown("---")

# Gmail status
if gmail.available:
    st.sidebar.success("✅ Gmail connected")
else:
    st.sidebar.warning("⚠️ Gmail not configured")

if Config.OPENAI_API_KEY:
    st.sidebar.success("✅ AI enabled")
else:
    st.sidebar.info("ℹ️ AI unavailable (rule-based fallback active)")

# Quick demo-data switcher in the sidebar
with st.sidebar.expander("🎛️ Demo Data", expanded=False):
    st.caption("Upload demo data or load a test scenario. Scenarios reshape the "
               "data to show a different business situation.")
    if st.button("🚀 Upload Sample Data", use_container_width=True,
                 key="upload_sample_side"):
        with st.spinner("Uploading sample data..."):
            load_sample_data(db, scenario=0)
            st.session_state[HAS_DATA_KEY] = True
        st.success("Sample data uploaded.")
        st.rerun()
    st.markdown("---")
    scenario_map = {
        "0 - Healthy Business": 0,
        "1 - Cash-flow Warning": 1,
        "2 - Overdue Invoices": 2,
        "3 - High-Expense Risk": 3,
    }
    choice = st.selectbox("Scenario", list(scenario_map.keys()),
                          label_visibility="collapsed")
    if st.button("Load Demo Scenario", use_container_width=True):
        load_demo_data(scenario_map[choice])

# ---------------------------------------------------------------------------
# Helper: currency format
# ---------------------------------------------------------------------------
def usd(v):
    if v is None:
        return "$0.00"
    return f"${v:,.2f}"


def delta_color(v):
    return "normal" if v >= 0 else "inverse"


def _header_banner(title, subtitle=None):
    """Rich page header band."""
    sub = f"<p style='color:{THEME['muted']};margin:6px 0 0 0;font-size:14px;'>{subtitle}</p>" \
        if subtitle else ""
    st.markdown(
        f"""
        <div style='padding:4px 0 12px 0;'>
            <span style='font-size:26px;font-weight:800;
                 background:linear-gradient(90deg,{THEME['green']},{THEME['blue']});
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                {title}</span>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _status_chip(label, tone):
    """Small tonal badge: green / amber / red."""
    colors = {
        "green": ("#0a9d5c", "#d4fbe9"),
        "amber": ("#b26a00", "#ffe7b3"),
        "red": ("#c0392b", "#fdd3cf"),
        "blue": ("#1f6feb", "#d3e3ff"),
    }
    bg, fg = colors.get(tone, colors["blue"])
    return (f"<span style='background:{bg};color:{fg};padding:3px 10px;"
            f"border-radius:20px;font-size:12px;font-weight:600;'>{label}</span>")


# ---------------------------------------------------------------------------
# PAGES
# ---------------------------------------------------------------------------

def page_dashboard():
    st.caption("Finance &nbsp;·&nbsp; Overview")
    _header_banner(
        "Financial Dashboard",
        "Live health of your business — cash, receivables, risk and AI insights.",
    )
    balance = cashflow.current_balance()
    ar = svc.accounts_receivable()
    overdue = svc.invoices_overdue()
    overdue_total = sum(o["amount"] for o in overdue)
    revenue_30 = svc.total_revenue(
        (date.today() - timedelta(days=30)).isoformat(), date.today().isoformat()
    )
    expenses_30 = svc.total_expenses(
        (date.today() - timedelta(days=30)).isoformat(), date.today().isoformat()
    )

    risk = reporting.risk_report()
    health_flag = ("green" if balance >= 0 and not risk["risks"]
                   else "amber" if any(r["type"] == "warning" for r in risk["risks"])
                   else "red")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash Balance", usd(balance))
    c2.metric("Accounts Receivable", usd(ar))
    c3.metric("Overdue Amount", usd(overdue_total),
              delta=f"{len(overdue)} invoices", delta_color=delta_color(-overdue_total))
    c4.metric("30-day Net", usd(revenue_30 - expenses_30),
              delta=f"Rev {usd(revenue_30)}")

    st.markdown("---")

    # Revenue vs Expense trend
    col1, col2 = st.columns(2)
    with col1:
        series = cashflow.cashflow_series(6)
        if series:
            df = pd.DataFrame(series)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Income", x=df["month"], y=df["income"],
                                 marker_color=THEME["green"]))
            fig.add_trace(go.Bar(name="Expense", x=df["month"], y=df["expense"],
                                 marker_color=THEME["red"]))
            fig.update_layout(barmode="group")
            fig = style_chart(fig, "Monthly Revenue vs Expenses")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if series:
            df = pd.DataFrame(series)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                name="Cash balance", x=df["month"], y=df["balance"],
                mode="lines+markers",
                line=dict(color=THEME["blue"], width=3),
                fill="tozeroy", fillcolor="rgba(31,111,235,0.15)",
            ))
            fig = style_chart(fig, "Running Cash Balance")
            st.plotly_chart(fig, use_container_width=True)

    # Forecast
    fc = forecast.forecast((30, 60, 90))
    if fc:
        st.subheader("Cash Flow Forecast")
        c1, c2, c3 = st.columns(3)
        for i, (label, col) in enumerate(zip(["30-day", "60-day", "90-day"], [c1, c2, c3])):
            with col:
                f = fc[i]
                st.metric(
                    label, usd(f["projected_balance"]),
                    delta=f"In {usd(f['projected_income'])} / Out {usd(f['projected_expense'])}",
                    delta_color=delta_color(f["projected_net"]),
                )

    # Risk & Insights
    st.markdown("---")
    col_r, col_i = st.columns([1, 1.25])
    with col_r:
        st.subheader("🛡️ Risk Analysis")
        if risk["risks"]:
            for r in risk["risks"]:
                tone = "red" if r["type"] == "critical" else "amber"
                st.markdown(
                    f"{_status_chip(r['type'].upper(), tone)} "
                    f"<span style='color:{THEME['text']}'>{r['message']}</span> "
                    f"<span style='color:{THEME['muted']};font-size:13px;'>"
                    f"· flag: <code>{','.join(risk['risk_flags']) or 'none'}</code></span>",
                    unsafe_allow_html=True,
                )
                st.write("")
        else:
            st.markdown(_status_chip("No serious risks", "green") + "  Capital is healthy — no critical flags triggered.", unsafe_allow_html=True)
    with col_i:
        st.subheader("💡 AI Financial Insights")
        insights = reporting.ai_insights(risk)
        st.markdown(
            f"<span style='color:{THEME['muted']};font-size:12px;'>Source: {insights['source']}</span>",
            unsafe_allow_html=True,
        )
        if insights["recommendations"]:
            for rec in insights["recommendations"]:
                st.markdown(f"- {rec}")


def page_invoices():
    _header_banner(
        "Invoices",
        "Create, track and manage outstanding receivables across your customers.",
    )
    invoices = svc.list_invoices()

    col1, col2, col3 = st.columns(3)
    total = sum(i["amount"] for i in invoices)
    paid = sum(i["amount"] for i in invoices if i["status"] == "paid")
    outstanding = total - paid
    col1.metric("Total Invoiced", usd(total))
    col2.metric("Paid", usd(paid))
    col3.metric("Outstanding", usd(outstanding))

    st.markdown("---")

    # Filter
    status_filter = st.selectbox("Status", ["all", "issued", "paid", "partial"])
    if status_filter != "all":
        invoices = [i for i in invoices if i["status"] == status_filter]

    if invoices:
        df = pd.DataFrame(invoices)
        # Enrich with customer name
        def _cust(cid):
            c = svc.get_customer(cid) if cid else None
            return c["name"] if c else "N/A"
        df["customer"] = df["customer_id"].apply(_cust)
        st.dataframe(
            df[["invoice_number", "customer", "amount", "issue_date",
                "due_date", "status"]].reset_index(drop=True),
            use_container_width=True,
        )

    # Create invoice
    st.markdown("---")
    st.subheader("Create Invoice")
    with st.form("new_invoice"):
        cols = st.columns(2)
        inv_no = cols[0].text_input("Invoice Number", value=f"INV-{1001 + len(svc.list_invoices())}")
        customer_id = cols[1].number_input("Customer ID", min_value=1, step=1)
        amount = cols[0].number_input("Amount ($)", min_value=0.0, step=100.0)
        issue_date = cols[1].date_input("Issue Date", value=date.today())
        due = cols[0].date_input("Due Date", value=date.today() + timedelta(days=30))
        desc = cols[1].text_input("Description")
        if st.form_submit_button("Create Invoice"):
            inv = Invoice(invoice_number=inv_no, customer_id=customer_id,
                          amount=amount, issue_date=issue_date.isoformat(),
                          due_date=due.isoformat(), description=desc)
            svc.create_invoice(inv)
            st.success(f"Invoice {inv_no} created!")
            st.rerun()


def page_payments():
    _header_banner(
        "Payments",
        "Incoming payments applied against open invoices.",
    )
    payments = svc.list_payments()
    if payments:
        st.dataframe(
            pd.DataFrame(payments)[["id", "invoice_id", "amount",
                                     "payment_date", "method", "reference"]]
            .reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("No payments recorded yet.")

    st.markdown("---")
    st.subheader("Record Payment")
    with st.form("new_payment"):
        cols = st.columns(2)
        inv_no = cols[0].text_input("Invoice Number (optional)")
        cust_id = cols[1].number_input("Customer ID", min_value=1, step=1)
        amount = cols[0].number_input("Amount ($)", min_value=0.0, step=100.0)
        pay_date = cols[1].date_input("Payment Date", value=date.today())
        method = cols[0].selectbox("Method", ["transfer", "credit_card", "cash", "check"])
        ref = cols[1].text_input("Reference")
        if st.form_submit_button("Record Payment"):
            inv = None
            invoice_id = None
            if inv_no:
                inv = svc.get_invoice_by_number(inv_no)
                if inv:
                    invoice_id = inv["id"]
                    cust_id = inv["customer_id"]
            pay = Payment(invoice_id=invoice_id, customer_id=cust_id,
                          amount=amount, payment_date=pay_date.isoformat(),
                          method=method, reference=ref)
            svc.record_payment(pay)
            st.success(f"Payment of {usd(amount)} recorded!")
            st.rerun()


def page_expenses():
    _header_banner(
        "Expenses",
        "Track operating spend by category and spot cost trends.",
    )
    expenses = svc.list_expenses()
    total = svc.total_expenses()
    recurring = svc.recurring_expenses_monthly()
    col1, col2 = st.columns(2)
    col1.metric("Total Expenses", usd(total))
    col2.metric("Monthly Recurring", usd(recurring))

    if expenses:
        df = pd.DataFrame(expenses)
        st.dataframe(
            df[["category", "description", "amount", "expense_date", "vendor",
                "recurring"]].reset_index(drop=True),
            use_container_width=True,
        )

    # Category breakdown
    cats = svc.expenses_by_category()
    if cats:
        st.subheader("Expense by Category")
        cat_df = pd.DataFrame(cats)
        fig = px.pie(cat_df, names="category", values="total",
                     color_discrete_sequence=[THEME["green"], THEME["blue"],
                                              THEME["amber"], THEME["red"],
                                              "#2fa4e7", "#7957d5", "#12b5cb",
                                              "#f39c12", "#6c63ff", "#0a9d5c"])
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          marker=dict(line=dict(color=THEME["bg"], width=2)))
        fig = style_chart(fig, "Spend by Category", height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Add Expense")
    with st.form("new_expense"):
        cols = st.columns(2)
        cat = cols[0].selectbox("Category", Config.EXPENSE_CATEGORIES)
        amt = cols[1].number_input("Amount ($)", min_value=0.0, step=50.0)
        exp_date = cols[0].date_input("Date", value=date.today())
        vendor = cols[1].text_input("Vendor")
        desc = cols[0].text_input("Description")
        recurring = cols[1].checkbox("Recurring (monthly)")
        if st.form_submit_button("Add Expense"):
            exp = Expense(category=cat, description=desc, amount=amt,
                          expense_date=exp_date.isoformat(), vendor=vendor,
                          recurring=1 if recurring else 0)
            svc.create_expense(exp)
            st.success("Expense added!")
            st.rerun()


def page_cashflow():
    _header_banner(
        "Cash Flow & Forecast",
        "Monthly trends plus 30 / 60 / 90-day projections of cash, income and spend.",
    )

    balance = cashflow.current_balance()
    st.metric("Current Cash Balance", usd(balance))

    # Monthly series
    series = cashflow.cashflow_series(6)
    if series:
        df = pd.DataFrame(series)
        st.subheader("Monthly Cash Flow")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Income", x=df["month"], y=df["income"],
                             marker_color=THEME["green"]))
        fig.add_trace(go.Bar(name="Expense", x=df["month"], y=df["expense"],
                             marker_color=THEME["red"]))
        fig.add_trace(go.Scatter(name="Net", x=df["month"], y=df["net"],
                                 mode="lines+markers",
                                 line=dict(color=THEME["blue"], width=3)))
        fig.update_layout(barmode="group")
        fig = style_chart(fig, "Income / Expense / Net", height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Forecast
    fc = forecast.forecast((30, 60, 90))
    if fc:
        st.subheader("30 / 60 / 90-Day Forecast")
        fc_df = pd.DataFrame(fc)
        fc_df["period"] = fc_df["period"].apply(lambda d: f"{d}-day")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Projected Income", x=fc_df["period"],
                             y=fc_df["projected_income"], marker_color=THEME["green"]))
        fig.add_trace(go.Bar(name="Projected Expense", x=fc_df["period"],
                             y=fc_df["projected_expense"], marker_color=THEME["red"]))
        fig.add_trace(go.Scatter(name="Projected Balance", x=fc_df["period"],
                                 y=fc_df["projected_balance"], mode="lines+markers",
                                 line=dict(color=THEME["blue"], width=3)))
        fig.update_layout(barmode="group")
        fig = style_chart(fig, "Projected Cash Position", height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(fc_df, use_container_width=True)


def page_emails():
    _header_banner(
        "Incoming Emails",
        "Gmail inbox monitored by the AI — classified as invoice, reminder or other.",
    )
    rows = db.query("SELECT * FROM emails ORDER BY received_at DESC LIMIT 100")
    if rows:
        df = pd.DataFrame(rows)
        cols_show = ["received_at", "from_address", "subject", "classification",
                     "client_name", "amount", "action_required", "processed"]
        display_cols = [c for c in cols_show if c in df.columns]
        st.dataframe(df[display_cols].reset_index(drop=True), use_container_width=True)
    else:
        st.info("No emails processed yet.")

    st.markdown("---")
    st.subheader("Process Incoming Gmail (Manual)")
    query = st.text_input("Gmail query", value="is:inbox newer_than:1d")
    if st.button("Fetch & Process"):
        if gmail.available:
            with st.spinner("Fetching emails from Gmail..."):
                try:
                    msgs = gmail.fetch_emails(query, max_results=10)
                    if not msgs:
                        st.info("No emails found.")
                    for m in msgs:
                        summary = email_processor.process_message(m)
                        st.write(f"**{m['subject']}** → {summary['classification']}")
                        if summary.get("updates"):
                            for u in summary["updates"]:
                                st.success(f"  {u}")
                except GmailUnavailableError as e:
                    st.error(f"Gmail API error: {e}")
        else:
            st.warning("Gmail API is not configured. Add credentials.json to project root.")


def page_reports():
    _header_banner(
        "Weekly Financial Report",
        "A structured summary of the period — cash, AR, expenses, risks and next steps.",
    )
    week_report = reporting.weekly_report()
    st.metric("Net (week)", usd(week_report["net"]))
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue (week)", usd(week_report["revenue"]))
    c2.metric("Expenses (week)", usd(week_report["expenses"]))
    c3.metric("Payments (week)", usd(week_report["payments_total"]))

    st.text(render_report(week_report))

    st.markdown("---")
    st.subheader("Risk Report")
    risk = reporting.risk_report()
    for r in risk["risks"]:
        color = "red" if r["type"] == "critical" else "orange"
        st.warning(r["message"])

    st.subheader("AI Insights")
    insights = reporting.ai_insights(risk)
    st.caption(f"Source: {insights['source']}")
    for rec in insights["recommendations"]:
        st.markdown(f"- {rec}")


def render_report(report):
    return (
        f"Period: {report['period']}\n"
        f"Revenue (week): ${report['revenue']:,.2f}\n"
        f"Expenses (week): ${report['expenses']:,.2f}\n"
        f"Net (week): ${report['net']:,.2f}\n"
        f"Invoices created: {report['num_invoices_created']}\n"
        f"Payments received: {report['num_payments']} "
        f"(${report['payments_total']:,.2f})\n"
        f"Accounts receivable: ${report['accounts_receivable']:,.2f}\n"
        f"Overdue invoices: {report['overdue_invoices']}\n"
        f"Current cash balance: ${report['current_balance']:,.2f}"
    )


def page_email_composer():
    _header_banner(
        "Email Composer",
        "Draft, review and send financial emails generated by the AI.",
    )
    st.info(
        "Composing an email here processes it through the AI Email Agent, "
        "updates financial records if relevant, and sends the full processed "
        "summary to the business owner."
    )
    owner = Config.BUSINESS_OWNER_EMAIL or st.text_input(
        "Business Owner Email (fallback)", value=""
    )

    with st.form("email_composer"):
        recipient = st.text_input("Recipient Email *", placeholder="client@example.com")
        subject = st.text_input("Subject *", placeholder="Invoice details")
        body = st.text_area("Message *", height=200,
                            placeholder="Type your email here...")
        attachments = st.file_uploader("Attachments (optional)", accept_multiple_files=True)
        require_approval = st.checkbox("Require human approval before sending",
                                       value=Config.HUMAN_APPROVAL_REQUIRED)
        submitted = st.form_submit_button("📤 Process & Send")

    if submitted:
        if not recipient or not subject or not body:
            st.error("Recipient, Subject and Message are required.")
            return

        att_list = []
        for f in (attachments or []):
            import base64
            att_list.append({
                "filename": f.name,
                "data": base64.b64encode(f.read()).decode("ASCII"),
                "mimeType": f.type or "application/octet-stream",
            })

        Config.BUSINESS_OWNER_EMAIL = owner or Config.BUSINESS_OWNER_EMAIL
        with st.spinner("Processing via AI and sending..."):
            result = email_composer.compose_and_send(
                recipient=recipient, subject=subject, body=body,
                attachments=att_list, human_approval=require_approval,
            )

        st.success("Email processed!")
        st.json(result)


def page_audit_log():
    _header_banner(
        "Audit Log",
        "Every AI action and financial mutation, recorded for accountability.",
    )
    logs = db.query(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT 200"
    )
    if logs:
        df = pd.DataFrame(logs)
        st.dataframe(df.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No audit logs yet.")


def page_demo_data():
    _header_banner(
        "Demo Data & Test Scenarios",
        "Load realistic sample data or run one of four business stress-test scenarios.",
    )
    st.markdown(
        "The system ships with realistic sample data and **4 test scenarios** so you "
        "can evaluate how the model behaves under different business conditions. "
        "Loading a scenario replaces the current data in the database."
    )

    # Branded hero section: upload sample data (blue -> emerald -> white)
    h1, h2 = st.columns([2.2, 1])
    with h1:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,{THEME['blue_deep']} 0%,#0aa26b 100%);
                 border:1px solid {THEME['border']};border-radius:16px;
                 padding:18px 22px;box-shadow:0 10px 30px rgba(11,63,160,0.35);">
                <span style="font-size:19px;font-weight:800;color:#ffffff;">
                    ⬆️ Upload Sample Data</span>
                <p style="margin:6px 0 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                    Load the standard demo dataset into the database. This is the
                    quickest way to fill the dashboard with realistic records.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with h2:
        st.write("")
        if st.button("🚀 Upload Sample Data", type="secondary",
                     use_container_width=True, key="upload_sample_hero"):
            with st.spinner("Uploading sample data..."):
                load_sample_data(db, scenario=0)
                st.session_state[HAS_DATA_KEY] = True
            st.success("Sample data uploaded.")
            st.rerun()

    st.markdown("---")

    sc_info = {
        0: {
            "name": "Scenario 0 — Healthy Business",
            "desc": "Strong revenue, steady payments, moderate expenses and "
                    "positive cash flow. A well-run SME.",
            "tone": "green",
            "flags": ["✅ Positive cash balance", "✅ Low overdue ratio",
                      "✅ 30-day forecast in the black",
                      "📈 Revenue comfortably exceeds expenses"],
        },
        1: {
            "name": "Scenario 1 — Cash-flow Warning",
            "desc": "A large unexpected expense (quarterly tax settlement) drains "
                    "reserves, leaving the business short on runway.",
            "tone": "amber",
            "flags": ["⚠️ Cash balance near or below zero",
                      "⚠️ Balance below one month of expenses",
                      "⚠️ Short-term liquidity risk detected"],
        },
        2: {
            "name": "Scenario 2 — Overdue Invoices",
            "desc": "Multiple clients behind on payment. Accounts receivable age and "
                    "collection risk rises.",
            "tone": "amber",
            "flags": ["⏰ Several invoices past due",
                      "⏰ High overdue-to-AR ratio",
                      "📧 Escalating payment reminders triggered"],
        },
        3: {
            "name": "Scenario 3 — High-Expense Risk",
            "desc": "Expenses (equipment + a large lease) grow faster than revenue, "
                    "driving a high fixed-cost burden and burn rate.",
            "tone": "red",
            "flags": ["🔥 High recurring/committed costs",
                      "🔥 Expenses outpacing revenue",
                      "🔥 Deteriorating 90-day projection"],
        },
    }

    cols = st.columns(2)
    for i, (sc, info) in enumerate(sc_info.items()):
        with cols[i % 2]:
            chip = _status_chip(info["name"].split("—")[1].strip(), info["tone"])
            flag_html = "<br>".join(
                f"<span style='color:{THEME['text']};font-size:13px;'>{f}</span>"
                for f in info["flags"]
            )
            st.markdown(
                f"""
                <div style="background:{THEME['panel']};border:1px solid {THEME['border']};
                     border-radius:14px;padding:18px;margin-bottom:16px;">
                    <h4 style="margin:0 0 10px 0;color:{THEME['text']};">
                        {info['name']} &nbsp;{chip}</h4>
                    <p style="font-size:14px;margin:0 0 12px 0;color:{THEME['muted']};">
                        {info['desc']}</p>
                    {flag_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Load {info['name']}", key=f"demo_btn_{sc}",
                         use_container_width=True):
                load_demo_data(sc)

    st.markdown("---")

    # Live state of the current database
    st.subheader("Current Data State")
    counts = {
        "Customers": db.query_one("SELECT COUNT(*) c FROM customers")["c"],
        "Invoices": db.query_one("SELECT COUNT(*) c FROM invoices")["c"],
        "Payments": db.query_one("SELECT COUNT(*) c FROM payments")["c"],
        "Expenses": db.query_one("SELECT COUNT(*) c FROM expenses")["c"],
        "Transactions": db.query_one("SELECT COUNT(*) c FROM transactions")["c"],
        "Emails": db.query_one("SELECT COUNT(*) c FROM emails")["c"],
    }
    mcols = st.columns(len(counts))
    for (label, val), col in zip(counts.items(), mcols):
        col.metric(label, val)

    st.caption("Tip: use the **" + "🎛️ Demo Data" + "** expander in the sidebar to "
               "switch scenarios from any page.")


def page_settings():
    _header_banner(
        "Settings",
        "Configure AI, approvals, reminders and Gmail automation.",
    )

    st.subheader("System Settings")
    with st.form("settings_form"):
        require_approval = st.checkbox(
            "Human approval required before sending financial emails",
            value=Config.HUMAN_APPROVAL_REQUIRED,
        )
        reminder_enabled = st.checkbox(
            "Enable automatic payment reminders",
            value=Config.REMINDER_ENABLED,
        )
        gmail_interval = st.number_input(
            "Gmail check interval (minutes)", value=Config.GMAIL_CHECK_INTERVAL,
            min_value=1,
        )
        owner_email = st.text_input("Business Owner Email",
                                    value=Config.BUSINESS_OWNER_EMAIL)
        openai_key = st.text_input("OpenAI API Key (optional)",
                                   value=Config.OPENAI_API_KEY,
                                   type="password")
        if st.form_submit_button("Save Settings"):
            Config.HUMAN_APPROVAL_REQUIRED = require_approval
            Config.REMINDER_ENABLED = reminder_enabled
            Config.GMAIL_CHECK_INTERVAL = gmail_interval
            Config.BUSINESS_OWNER_EMAIL = owner_email
            Config.OPENAI_API_KEY = openai_key
            set_setting(db, "human_approval", str(require_approval))
            set_setting(db, "reminder_enabled", str(reminder_enabled))
            set_setting(db, "owner_email", owner_email)
            st.success("Settings saved.")

    st.markdown("---")
    st.subheader("Demo Data")
    st.info("Load sample data or run one of the 4 business stress-test scenarios from "
            "the **🎛️ Demo Data** page, or use the **🎛️ Demo Data** expander in the "
            "sidebar.")
    if st.button("Go to Demo Data page", key="goto_demo"):
        st.session_state["nav_target"] = "Demo Data"
        st.rerun()

    st.markdown("---")
    st.subheader("Send Payment Reminders (Dry Run)")
    if st.button("Preview Reminders"):
        due = reminder_engine.due_reminders()
        if due:
            for item in due:
                inv = item["invoice"]
                st.write(
                    f"**{inv['invoice_number']}** → {item['level']} "
                    f"(overdue {item['days_overdue']} days)"
                )
        else:
            st.info("No reminders due.")

    if st.button("Send All Due Reminders"):
        results = reminder_engine.send_reminders(dry_run=False)
        st.success(f"Processed {len(results)} reminder(s).")
        for r in results:
            st.write(f"  {r['invoice_number']}: {r['level']} → {r['status']}")

    st.markdown("---")
    st.subheader("Debug")
    if st.button("Show DB stats"):
        stats = {
            "customers": db.query_one("SELECT COUNT(*) as c FROM customers")["c"],
            "invoices": db.query_one("SELECT COUNT(*) as c FROM invoices")["c"],
            "payments": db.query_one("SELECT COUNT(*) as c FROM payments")["c"],
            "expenses": db.query_one("SELECT COUNT(*) as c FROM expenses")["c"],
            "transactions": db.query_one("SELECT COUNT(*) as c FROM transactions")["c"],
            "emails": db.query_one("SELECT COUNT(*) as c FROM emails")["c"],
            "reminders": db.query_one("SELECT COUNT(*) as c FROM reminders")["c"],
            "audit_logs": db.query_one("SELECT COUNT(*) as c FROM audit_log")["c"],
        }
        st.json(stats)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
PAGE_MAP = {
    "Dashboard": page_dashboard,
    "Invoices": page_invoices,
    "Payments": page_payments,
    "Expenses": page_expenses,
    "Cash Flow & Forecast": page_cashflow,
    "Emails": page_emails,
    "Reports": page_reports,
    "Email Composer": page_email_composer,
    "Audit Log": page_audit_log,
    "Demo Data": page_demo_data,
    "Settings": page_settings,
}

PAGE_MAP[page]()
