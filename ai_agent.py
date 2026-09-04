import json
import re
from typing import Optional

from config import Config


class AIUnavailableError(Exception):
    """Raised when the OpenAI API is not available."""


class AIEmailAgent:
    """Intelligent email classification and financial data extraction."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.OPENAI_MODEL
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise AIUnavailableError(
                    "OpenAI SDK not installed. Run: pip install openai"
                )
        return self._client

    def classify_email(self, subject: str, body: str) -> dict:
        """Classify an email and extract financial data."""
        if not self.available:
            raise AIUnavailableError("OPENAI_API_KEY not set.")

        return self._classify_by_llm(subject, body)

    def _classify_by_llm(self, subject, body) -> dict:
        client = self._get_client()
        prompt = self._build_classification_prompt(subject, body)
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": (
                        "You are a financial email classification agent for an SME."
                        "Return ONLY a valid JSON object with fields: "
                        "classification, client_name, amount, invoice_number, "
                        "due_date, action_required, confidence. "
                        "classification is one of: invoice, payment, reminder, "
                        "expense, other. Use ISO date format YYYY-MM-DD. "
                        "Use null for unknown fields."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            return self._safe_parse_json(raw)
        except Exception as e:
            raise AIUnavailableError(f"AI classification failed: {e}")

    def _build_classification_prompt(self, subject, body):
        text = (subject + "\n" + body)[:4000]
        return f"Classify this email:\n---EMAIL START---\n{text}\n---EMAIL END---"

    def _safe_parse_json(self, raw: str) -> dict:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    raise AIUnavailableError("Could not parse AI JSON output.")
            else:
                raise AIUnavailableError("AI returned no JSON.")
        return parsed

    def financial_recommendations(self, metrics: dict) -> list:
        """Generate AI financial recommendations based on metrics."""
        if not self.available:
            raise AIUnavailableError("OPENAI_API_KEY not set for recommendations.")
        client = self._get_client()
        try:
            prompt = (
                "You are a financial advisor for an SME. Based on these metrics, "
                "provide 5 concise, actionable recommendations. Return a JSON array "
                "of strings.\n\nMetrics:\n" + json.dumps(metrics)
            )
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": (
                        "Return ONLY a JSON array of strings, each a short "
                        "actionable financial recommendation."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            raw = resp.choices[0].message.content.strip()
            try:
                recs = json.loads(raw)
                return [r for r in recs if isinstance(r, str)]
            except json.JSONDecodeError:
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                return [raw]
        except Exception as e:
            raise AIUnavailableError(f"AI recommendation failed: {e}")


class AIRuleEngine:
    """Rule-based fallback engine used when AI is unavailable or for
    independent financial calculations. Keeps the system functional without AI."""

    def classify_email(self, subject: str, body: str) -> dict:
        text = (subject + " " + body).lower()
        original = subject + " " + body
        result = {
            "classification": "other",
            "client_name": None,
            "amount": None,
            "invoice_number": None,
            "due_date": None,
            "action_required": None,
            "confidence": 0.0,
        }

        found_client = self._find_client(text)
        found_amount = self._find_amount(text)
        found_invoice = self._find_invoice_number(original)
        found_due = self._find_due_date(original)

        result.update({
            "client_name": found_client,
            "amount": found_amount,
            "invoice_number": found_invoice,
            "due_date": found_due,
        })

        # Reminder/overdue takes priority (an invoice can be overdue)
        if any(k in text for k in ("reminder", "overdue", "past due",
                                   "late payment", "final notice",
                                   "collections")):
            result["classification"] = "reminder"
            result["action_required"] = "send_reminder"
            result["confidence"] = 0.75
        # Outgoing invoice request: references an invoice number and requests
        # payment (e.g. "please remit payment for invoice INV-...")
        elif found_invoice and any(k in text for k in (
                "remit", "arrange payment", "please pay", "pay for",
                "requesting payment", "request payment", "payable")):
            result["classification"] = "invoice"
            result["action_required"] = "record_invoice"
            result["confidence"] = 0.7
        elif any(k in text for k in ("payment received", "payment made", "paid",
                                     "bank transfer", "payment of", "payment for",
                                     "we have transferred", "we paid",
                                     "we have paid", "payment confirmation")):
            result["classification"] = "payment"
            result["action_required"] = "record_payment"
            result["confidence"] = 0.8
        elif "invoice" in text or "payment due" in text or "amount due" in text:
            result["classification"] = "invoice"
            result["action_required"] = "record_invoice"
            result["confidence"] = 0.8
        elif any(k in text for k in ("expense", "receipt", "purchase", "refund",
                                     "bill")):
            result["classification"] = "expense"
            result["action_required"] = "record_expense"
            result["confidence"] = 0.7

        if result["classification"] == "other" and not result["client_name"] \
                and not result["amount"]:
            result["action_required"] = None

        return result

    def _find_client(self, text):
        email_match = re.search(r"from:\s*([^<\s]+(?:@[^\s]+)?)", text)
        if email_match:
            return email_match.group(1).strip()
        return None

    def _find_amount(self, text):
        patterns = [
            r"amount\s*(?:of|:)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            r"\$\s*([\d,]+(?:\.\d{1,2})?)",
            r"(?:invoice|payment)\s*(?:of|for)?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                val = m.group(1).replace(",", "")
                try:
                    return float(val)
                except ValueError:
                    continue
        return None

    def _find_invoice_number(self, text):
        patterns = [
            r"invoice\s*(?:#|number|no\.?)?\s*[:#]?\s*([A-Za-z0-9\-]+)",
            r"inv[-_]?\s*([A-Za-z0-9\-]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(1)
        return None

    def _find_due_date(self, text):
        iso = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
        if iso:
            return iso.group(0)
        mdy = re.search(
            r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", text)
        if mdy:
            return f"{mdy.group(3)}-{int(mdy.group(1)):02d}-{int(mdy.group(2)):02d}"
        month_names = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        named = re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
            r"(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b", text, re.IGNORECASE)
        if named:
            mon = month_names[named.group(1).lower()[:3]]
            day = int(named.group(2))
            year = named.group(3)
            return f"{year}-{mon:02d}-{day:02d}"
        return None


def get_ai_agent() -> AIEmailAgent:
    return AIEmailAgent()


def get_rule_engine() -> AIRuleEngine:
    return AIRuleEngine()
