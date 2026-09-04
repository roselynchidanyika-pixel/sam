from datetime import date, timedelta

from database import Database, AuditLogger
from services import FinanceService
from cashflow import CashFlowAnalyzer, ForecastEngine
from ai_agent import get_ai_agent, get_rule_engine, AIUnavailableError
from config import Config


class ReportingService:
    def __init__(self, db: Database):
        self.db = db
        self.finance = FinanceService(db)
        self.cashflow = CashFlowAnalyzer(db)
        self.forecast = ForecastEngine(db)
        self.audit = AuditLogger(db)
        self.ai = get_ai_agent()

    def weekly_report(self, as_of: date = None) -> dict:
        as_of = as_of or date.today()
        week_start = as_of - timedelta(days=as_of.weekday())
        week_end = week_start + timedelta(days=6)

        revenue = self.finance.total_revenue(week_start.isoformat(),
                                             week_end.isoformat())
        expenses = self.finance.total_expenses(week_start.isoformat(),
                                               week_end.isoformat())
        payments = self.finance.list_payments(200)
        week_payments = [p for p in payments
                         if week_start.isoformat() <= p["payment_date"]
                         <= week_end.isoformat()]
        new_invoices = [i for i in self.finance.list_invoices()
                        if week_start.isoformat() <= i["issue_date"]
                        <= week_end.isoformat()]

        report = {
            "period": f"{week_start.isoformat()} to {week_end.isoformat()}",
            "revenue": round(revenue, 2),
            "expenses": round(expenses, 2),
            "net": round(revenue - expenses, 2),
            "num_invoices_created": len(new_invoices),
            "num_payments": len(week_payments),
            "payments_total": round(sum(p["amount"] for p in week_payments), 2),
            "accounts_receivable": round(self.finance.accounts_receivable(), 2),
            "overdue_invoices": len(self.finance.invoices_overdue()),
            "current_balance": round(self.cashflow.current_balance(), 2),
        }
        self.audit.log("system", "weekly_report", None, None,
                       f"Generated weekly report {report['period']}")
        return report

    def render_weekly_report_text(self, report: dict) -> str:
        lines = [
            "======== WEEKLY FINANCIAL REPORT ========",
            f"Period: {report['period']}",
            "",
            f"Revenue (week):        ${report['revenue']:,.2f}",
            f"Expenses (week):       ${report['expenses']:,.2f}",
            f"Net (week):            ${report['net']:,.2f}",
            "",
            f"Invoices created:      {report['num_invoices_created']}",
            f"Payments received:     {report['num_payments']} "
            f"(${report['payments_total']:,.2f})",
            f"Accounts receivable:   ${report['accounts_receivable']:,.2f}",
            f"Overdue invoices:      {report['overdue_invoices']}",
            f"Current cash balance:  ${report['current_balance']:,.2f}",
            "=========================================",
        ]
        return "\n".join(lines)

    def risk_report(self) -> dict:
        """Compute risk metrics suitable for AI + display."""
        current_balance = self.cashflow.current_balance()
        overdue = self.finance.invoices_overdue()
        overdue_total = sum(o["amount"] for o in overdue)
        ar = self.finance.accounts_receivable()
        avg_monthly_expense = self.forecast.average_monthly_expenses()
        monthly_committed = self.finance.recurring_expenses_monthly()
        forecasts = self.forecast.forecast((30, 60, 90))

        risks = []
        flags = []
        if current_balance < 0:
            risks.append({"type": "critical", "message":
                          "Negative cash balance."})
            flags.append("negative_balance")
        if avg_monthly_expense > 0 and current_balance < avg_monthly_expense:
            risks.append({"type": "warning", "message":
                          "Balance below one month of expenses."})
            flags.append("low_runway")
        if overdue_total > 0.3 * (ar or 1):
            risks.append({"type": "warning", "message":
                          "Significant portion of AR is overdue."})
            flags.append("overdue_concentration")
        if monthly_committed > 0.6 * self.forecast.average_monthly_income():
            risks.append({"type": "warning", "message":
                          "Recurring expense commitments high relative to income."})
            flags.append("high_fixed_cost")
        if forecasts and forecasts[-1]["projected_balance"] < 0:
            risks.append({"type": "critical", "message":
                          "Projected cash crunch within 90 days."})
            flags.append("projected_crunch")

        return {
            "current_balance": round(current_balance, 2),
            "accounts_receivable": round(ar, 2),
            "overdue_total": round(overdue_total, 2),
            "overdue_count": len(overdue),
            "avg_monthly_expense": round(avg_monthly_expense, 2),
            "recurring_monthly": round(monthly_committed, 2),
            "risk_flags": flags,
            "risks": risks,
            "forecast_30d": forecasts[0] if forecasts else None,
            "forecast_60d": forecasts[1] if len(forecasts) > 1 else None,
            "forecast_90d": forecasts[2] if len(forecasts) > 2 else None,
        }

    def ai_insights(self, risk_report: dict) -> dict:
        """Get AI-generated insights with rule-based fallback."""
        metrics = {
            "current_balance": risk_report["current_balance"],
            "accounts_receivable": risk_report["accounts_receivable"],
            "overdue_total": risk_report["overdue_total"],
            "avg_monthly_expense": risk_report["avg_monthly_expense"],
            "forecast_30d": risk_report["forecast_30d"]["projected_balance"]
            if risk_report["forecast_30d"] else None,
            "forecast_90d": risk_report["forecast_90d"]["projected_balance"]
            if risk_report["forecast_90d"] else None,
            "risk_flags": risk_report["risk_flags"],
        }
        try:
            recs = self.ai.financial_recommendations(metrics)
            return {"source": "ai", "recommendations": recs}
        except AIUnavailableError:
            return {"source": "rule", "recommendations":
                    self._rule_based_recommendations(risk_report)}

    def _rule_based_recommendations(self, rr: dict) -> list:
        recs = []
        if rr["current_balance"] < 0:
            recs.append("Immediate action: your cash balance is negative. "
                        "Consider negotiating payment terms or securing a "
                        "short-term line of credit.")
        if rr["overdue_total"] > 0:
            recs.append(f"You have {rr['overdue_count']} overdue invoice(s) "
                        f"totaling ${rr['overdue_total']:,.2f}. Prioritize "
                        "escalating collection efforts (firm/final reminders).")
        if rr["forecast_90d"] and rr["forecast_90d"]["projected_balance"] < 0:
            recs.append("Projected 90-day cash crunch detected. Reduce "
                        "discretionary spending and accelerate receivables.")
        if rr["recurring_monthly"] > 0.6 * rr["avg_monthly_expense"]:
            recs.append("High fixed recurring costs. Review subscriptions and "
                        "renegotiate vendor contracts.")
        if rr["accounts_receivable"] > 2 * rr["current_balance"]:
            recs.append("Accounts receivable is large vs cash. Tighten "
                        "invoice terms and chase collections.")
        if not recs:
            recs.append("Financial position looks balanced. Maintain current "
                        "cash-flow management and monitor receivables weekly.")
        if len(recs) < 5:
            recs.append("Maintain a cash buffer of at least 1-2 months of "
                        "operating expenses.")
        return recs[:5]

    def expense_breakdown(self):
        return self.finance.expenses_by_category()
