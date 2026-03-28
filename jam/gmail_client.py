"""Gmail API client for the jam project.

Provides OAuth 2.0 authorization flow and Gmail API access for email operations.
All functions accept `settings: Settings | None = None` and resolve internally.
No global state at import time.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from jam.config import Settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]
REDIRECT_URI = "http://localhost:8001/gmail/callback"


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def get_auth_url(settings: Settings | None = None) -> str:
    """Build OAuth 2.0 authorization URL.
    
    Raises ValueError if client_id or client_secret is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    if not settings.gmail_client_id:
        raise ValueError("gmail_client_id not configured")
    if not settings.gmail_client_secret:
        raise ValueError("gmail_client_secret not configured")
    
    config = {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    
    code_verifier, code_challenge = _pkce_pair()
    from jam.db import set_setting
    set_setting("gmail_code_verifier", code_verifier)

    flow = Flow.from_client_config(config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return auth_url


def exchange_code(code: str, settings: Settings | None = None) -> dict:
    """Exchange authorization code for tokens.
    
    Returns {"refresh_token": str, "email": str}.
    Raises ValueError if client credentials are not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    if not settings.gmail_client_id:
        raise ValueError("gmail_client_id not configured")
    if not settings.gmail_client_secret:
        raise ValueError("gmail_client_secret not configured")
    
    config = {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    
    from jam.db import get_all_settings
    stored = get_all_settings()
    code_verifier = stored.get("gmail_code_verifier")

    flow = Flow.from_client_config(config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=code, code_verifier=code_verifier)
    
    credentials = flow.credentials

    if not credentials.refresh_token:
        raise ValueError(
            "Google did not return a refresh token. In Google Cloud Console, "
            "ensure the OAuth app is set to 'Web application' type and that "
            "you are authorising with a fresh consent screen. "
            "If you previously granted access, revoke it at "
            "https://myaccount.google.com/permissions and try again."
        )

    # Get user email via Gmail profile (avoids needing the oauth2 v2 API)
    gmail = build("gmail", "v1", credentials=credentials)
    profile = gmail.users().getProfile(userId="me").execute()

    return {
        "refresh_token": credentials.refresh_token,
        "email": profile.get("emailAddress", ""),
    }


def get_credentials(settings: Settings | None = None) -> Credentials:
    """Build Credentials from stored refresh_token.
    
    Raises ValueError if refresh_token is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    if not settings.gmail_refresh_token:
        raise ValueError("gmail_refresh_token not configured")
    
    return Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        scopes=SCOPES,
    )


def list_emails(
    query: str = "",
    max_results: int = 10,
    settings: Settings | None = None,
) -> list[dict]:
    """Search Gmail for emails matching the query.
    
    Returns a list of dicts with: id, subject, from, date, snippet.
    Raises ValueError if refresh_token is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    credentials = get_credentials(settings)
    service = build("gmail", "v1", credentials=credentials)
    
    # List matching messages
    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()
    
    messages = results.get("messages", [])
    emails = []
    
    for msg in messages:
        # Get full message metadata
        full_msg = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()
        
        headers = {h["name"]: h["value"] for h in full_msg.get("payload", {}).get("headers", [])}
        snippet = full_msg.get("snippet", "")
        
        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": snippet,
        })
    
    return emails


def get_email(message_id: str, settings: Settings | None = None) -> dict:
    """Fetch full email by message ID.
    
    Returns {id, subject, from, to, date, body_text}.
    Raises ValueError if refresh_token is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    credentials = get_credentials(settings)
    service = build("gmail", "v1", credentials=credentials)
    
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()
    
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    
    # Extract body text from the payload
    body_text = ""
    payload = msg.get("payload", {})
    
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                if "data" in part.get("body", {}):
                    body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
    elif "body" in payload and "data" in payload["body"]:
        if payload.get("mimeType", "").startswith("text/plain"):
            body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    
    return {
        "id": message_id,
        "subject": headers.get("Subject", "(no subject)"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "body_text": body_text,
    }


def create_draft(
    to: str,
    subject: str,
    body: str,
    settings: Settings | None = None,
) -> str:
    """Create a Gmail draft.
    
    Returns the draft ID.
    Raises ValueError if refresh_token is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    credentials = get_credentials(settings)
    service = build("gmail", "v1", credentials=credentials)
    
    # Build RFC 2822 message
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}},
    ).execute()
    
    return draft["id"]


def send_email(
    to: str,
    subject: str,
    body: str,
    settings: Settings | None = None,
) -> str:
    """Send an email.
    
    Returns the message ID.
    Raises ValueError if refresh_token is not set.
    """
    from jam.config import Settings as _Settings
    settings = settings or _Settings()
    
    credentials = get_credentials(settings)
    service = build("gmail", "v1", credentials=credentials)
    
    # Build RFC 2822 message
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()
    
    return result["id"]
