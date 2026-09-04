import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import List, Optional

from config import Config


class GmailUnavailableError(Exception):
    """Raised when the Gmail API is not available."""


class GmailClient:
    def __init__(self, credentials_file=None, token_file=None, scopes=None):
        self.credentials_file = credentials_file or Config.GMAIL_CREDENTIALS_FILE
        self.token_file = token_file or Config.GMAIL_TOKEN_FILE
        self.scopes = scopes or Config.GMAIL_SCOPES
        self._service = None

    @property
    def available(self) -> bool:
        return Path(self.credentials_file).exists() or Path(self.token_file).exists()

    def _get_service(self):
        if self._service is not None:
            return self._service
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            raise GmailUnavailableError(
                "Google API libraries not installed. Run: pip install "
                "google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        creds = None
        token_path = Path(self.token_file)
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def fetch_emails(self, query: str = "is:inbox newer_than:7d",
                     max_results: int = 20) -> List[dict]:
        """Fetch emails matching a query and return parsed metadata + bodies."""
        service = self._get_service()
        try:
            results = service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
        except Exception as e:
            raise GmailUnavailableError(f"Gmail fetch failed: {e}")

        messages = results.get("messages", [])
        emails = []
        for msg in messages:
            try:
                detail = service.users().messages().get(
                    userId="me", id=msg["id"], format="full"
                ).execute()
                email = self._parse_message(detail)
                if email:
                    emails.append(email)
            except Exception:
                continue
        return emails

    def _parse_message(self, message: dict) -> Optional[dict]:
        headers = {}
        payload = message.get("payload", {})
        for h in payload.get("headers", []):
            headers[h["name"].lower()] = h["value"]

        gmail_id = message.get("id")
        internal_date = int(message.get("internalDate", 0)) / 1000
        from datetime import datetime, timezone
        received = datetime.fromtimestamp(internal_date, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        body, attachments = self._extract_body_and_attachments(payload)

        return {
            "gmail_message_id": gmail_id,
            "from_address": headers.get("from", ""),
            "to_address": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "body": body,
            "received_at": received,
            "attachments": attachments,
        }

    def _extract_body_and_attachments(self, payload, body_parts=None,
                                      attachments=None):
        if body_parts is None:
            body_parts = []
        if attachments is None:
            attachments = []

        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})

        if mime_type in ("text/plain", "text/html") and body.get("data"):
            try:
                decoded = base64.urlsafe_b64decode(
                    body["data"].encode("ASCII")
                ).decode("utf-8", errors="ignore")
                body_parts.append(decoded)
            except Exception:
                pass

        if mime_type.startswith("multipart/"):
            for part in payload.get("parts", []):
                self._extract_body_and_attachments(part, body_parts, attachments)
        elif payload.get("filename"):
            attachments.append({
                "filename": payload.get("filename"),
                "data": body.get("data"),
                "mimeType": mime_type,
            })

        text = " ".join(
            p for p in body_parts if p and not p.startswith("<")
        )
        if not text.strip():
            html = " ".join(p for p in body_parts if p.startswith("<"))
            text = html
        return text.strip(), attachments

    def send_email(self, to: str, subject: str, body: str,
                   attachments: List[dict] = None) -> dict:
        """Send an email, optionally with attachments.

        attachments: list of dicts with keys 'filename', 'data' (base64),
                     and 'mimeType'.
        """
        service = self._get_service()
        msg = self._build_message(to, subject, body, attachments or [])
        try:
            sent = service.users().messages().send(
                userId="me", body={"raw": msg["raw"]}
            ).execute()
            return sent
        except Exception as e:
            raise GmailUnavailableError(f"Gmail send failed: {e}")

    def _build_message(self, to, subject, body, attachments):
        msg = MIMEMultipart()
        msg["to"] = to
        msg["subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        for att in attachments:
            if att.get("data") is None:
                continue
            try:
                data = base64.urlsafe_b64decode(
                    att["data"].encode("ASCII")
                )
            except Exception:
                data = att["data"]
            part = MIMEApplication(data)
            part.add_header("Content-Disposition", "attachment",
                            filename=att["filename"])
            msg.attach(part)

        raw = base64.urlsafe_b64encode(
            msg.as_bytes()
        ).decode("ASCII")
        return {"raw": raw}

    def mark_as_read(self, message_id: str) -> bool:
        service = self._get_service()
        try:
            service.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except Exception:
            return False


def get_gmail_client() -> GmailClient:
    return GmailClient()
