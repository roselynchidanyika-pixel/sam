"""
Gmail API Setup Script
=====================
Run this script to set up Gmail API access.

1. Go to https://console.cloud.google.com
2. Create a project (or select an existing one)
3. Enable the Gmail API:
   APIs & Services → Library → Search "Gmail API" → Enable
4. Create OAuth2 credentials:
   APIs & Services → Credentials → Create Credentials → OAuth client ID
   Application type: Desktop app
   Name: AI Financial OS
5. Download the credentials JSON and save it as 'credentials.json' in this
   directory.
6. Run this script: python setup_gmail.py
7. A browser window will open; log in and authorise.
8. token.json is saved automatically and will be used by the app.
"""

import os
import json
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


def check():
    print("=" * 50)
    print("  Gmail API Setup Helper")
    print("=" * 50)
    if CREDS_FILE.exists():
        print(f"[OK] credentials.json found at {CREDS_FILE.resolve()}")
    else:
        print(f"[!!] credentials.json NOT found at {CREDS_FILE.resolve()}")
        print("     Download it from Google Cloud Console (see above).")
        return False

    if TOKEN_FILE.exists():
        print(f"[OK] token.json found at {TOKEN_FILE.resolve()}")
    else:
        print(f"[..] token.json not yet created (will be created on first auth).")

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
    except ImportError:
        print("[!!] Google API libraries not installed.")
        print("     pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False

    print("[OK] Google API libraries installed.")

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[..] Refreshing expired token...")
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            print("[OK] Token refreshed.")
        else:
            print("[..] Starting OAuth flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json())
            print("[OK] Authentication successful. token.json saved.")

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        print(f"[OK] Gmail account: {profile.get('emailAddress')}")
        print(f"[OK] Total messages: {profile.get('messagesTotal', 0)}")
        return True
    except Exception as e:
        print(f"[!!] Gmail connection test failed: {e}")
        return False


if __name__ == "__main__":
    ok = check()
    if ok:
        print("\nGmail API is ready! Run the app with: streamlit run app.py")
    else:
        print("\nGmail setup incomplete. Follow instructions above.")
