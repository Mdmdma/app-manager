"""Microsoft Graph client for Outlook Calendar integration.

Provides OAuth 2.0 authorization flow and Graph API access for calendar event
management.  All public functions accept ``settings: Settings | None = None``
and resolve it internally.  No global state at import time.

OAuth constants
--------------
- Authority:    https://login.microsoftonline.com/{tenant}
- Token URL:    {authority}/oauth2/v2.0/token
- Graph base:   https://graph.microsoft.com/v1.0
- Scopes:       offline_access Calendars.ReadWrite User.Read
"""

from __future__ import annotations

import html
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from jam.config import Settings

# ── OAuth constants ───────────────────────────────────────────────────────────

_AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant}"
_AUTHORIZE_PATH = "/oauth2/v2.0/authorize"
_TOKEN_PATH = "/oauth2/v2.0/token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SCOPES = "offline_access Calendars.ReadWrite User.Read"

# Treat tokens expiring within this many seconds as already expired.
_EXPIRY_BUFFER_SECONDS = 30


# ── Internal helpers ──────────────────────────────────────────────────────────


def _authority(tenant: str) -> str:
    return _AUTHORITY_TEMPLATE.format(tenant=tenant)


def _build_client() -> httpx.AsyncClient:
    """Return a fresh AsyncClient.  Tests may monkey-patch this function."""
    return httpx.AsyncClient(timeout=30)


def _build_event_body(round_row: dict, app_row: dict, settings: "Settings") -> dict:
    """Construct the Graph API event body dict from DB row dicts.

    ``round_row`` fields used: scheduled_at, scheduled_time, location, links,
    prep_notes, round_type, round_number, graph_event_id.
    ``app_row`` fields used: company, position.

    Raises ValueError if ``scheduled_time`` is present but malformed.
    """
    company = app_row.get("company", "")
    position = app_row.get("position", "")
    round_number = round_row.get("round_number") or 1
    round_type = round_row.get("round_type") or "other"

    subject = f"Interview: {company} — {position} (Round {round_number} · {round_type})"

    # ── Build HTML body ───────────────────────────────────────────────────────
    raw_notes = round_row.get("prep_notes") or ""
    notes_html = html.escape(raw_notes)

    raw_links = round_row.get("links") or ""
    link_lines = [ln.strip() for ln in raw_links.splitlines() if ln.strip()]
    links_html = "<br>".join(
        f'<a href="{html.escape(ln)}">{html.escape(ln)}</a>' for ln in link_lines
    )

    body_content = f"<p>{notes_html}</p><p>{links_html}</p>"

    # ── Location ──────────────────────────────────────────────────────────────
    location_name = (round_row.get("location") or "").strip()
    if not location_name and link_lines:
        location_name = link_lines[0]

    # ── Timing ───────────────────────────────────────────────────────────────
    scheduled_at: str = round_row.get("scheduled_at") or ""
    scheduled_time: str = (round_row.get("scheduled_time") or "").strip()
    tz = settings.calendar_timezone
    duration_minutes: int = settings.calendar_default_duration_minutes

    if scheduled_time:
        # Parse HH:MM strictly.
        parts = scheduled_time.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(
                f"scheduled_time '{scheduled_time}' is not valid HH:MM"
            )
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(
                f"scheduled_time '{scheduled_time}' is out of range"
            )

        # scheduled_at is YYYY-MM-DD (or YYYY-MM-DDT..., take date part).
        date_part = scheduled_at[:10] if scheduled_at else ""
        if not date_part:
            raise ValueError("scheduled_at is required when scheduled_time is present")

        start_dt_str = f"{date_part}T{hour:02d}:{minute:02d}:00"
        # Compute end by parsing as naive datetime, adding duration.
        start_naive = datetime.strptime(start_dt_str, "%Y-%m-%dT%H:%M:%S")
        end_naive = start_naive + timedelta(minutes=duration_minutes)
        end_dt_str = end_naive.strftime("%Y-%m-%dT%H:%M:%S")

        return {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_content},
            "location": {"displayName": location_name},
            "start": {"dateTime": start_dt_str, "timeZone": tz},
            "end": {"dateTime": end_dt_str, "timeZone": tz},
            "isAllDay": False,
            "reminderMinutesBeforeStart": 15,
            "attendees": [],
        }
    else:
        # All-day event: use date part only.
        date_part = scheduled_at[:10] if scheduled_at else ""
        if not date_part:
            raise ValueError("scheduled_at is required for all-day events")

        start_date = datetime.strptime(date_part, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        start_dt_str = start_date.strftime("%Y-%m-%dT00:00:00")
        end_dt_str = end_date.strftime("%Y-%m-%dT00:00:00")

        return {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_content},
            "location": {"displayName": location_name},
            "start": {"dateTime": start_dt_str, "timeZone": tz},
            "end": {"dateTime": end_dt_str, "timeZone": tz},
            "isAllDay": True,
            "reminderMinutesBeforeStart": 15,
            "attendees": [],
        }


# ── Public API ────────────────────────────────────────────────────────────────


def get_auth_url(settings: "Settings | None" = None) -> str:
    """Build the Microsoft OAuth consent URL.

    Uses ``response_type=code``, ``response_mode=query``, and includes
    ``client_id``, ``redirect_uri``, ``scope``, and ``state=jam``.
    No PKCE is needed for a confidential client with a client secret.
    """
    from jam.config import Settings as _Settings

    settings = settings or _Settings()

    authority = _authority(settings.ms_graph_tenant)
    params = {
        "client_id": settings.ms_graph_client_id,
        "response_type": "code",
        "response_mode": "query",
        "redirect_uri": settings.ms_graph_redirect_uri,
        "scope": _SCOPES,
        "state": "jam",
    }
    query = "&".join(f"{k}={httpx.URL('', params={k: v}).params}" for k, v in params.items())
    # Use httpx to encode the query string reliably.
    url = httpx.URL(authority + _AUTHORIZE_PATH).copy_with(params=params)
    return str(url)


async def exchange_code(code: str, settings: "Settings | None" = None) -> dict:
    """Exchange an authorization code for tokens plus user email.

    POSTs to the token endpoint, then fetches ``/me`` to retrieve the user
    email address.

    Returns a dict with keys: ``refresh_token``, ``access_token``,
    ``expires_at`` (ISO string in UTC), ``user_email``.
    """
    from jam.config import Settings as _Settings

    settings = settings or _Settings()

    authority = _authority(settings.ms_graph_tenant)
    token_url = authority + _TOKEN_PATH

    data = {
        "client_id": settings.ms_graph_client_id,
        "client_secret": settings.ms_graph_client_secret,
        "code": code,
        "redirect_uri": settings.ms_graph_redirect_uri,
        "scope": _SCOPES,
        "grant_type": "authorization_code",
    }

    client = _build_client()
    async with client:
        token_resp = await client.post(token_url, data=data)
        token_resp.raise_for_status()
        token_data = token_resp.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = int(token_data.get("expires_in", 3600))
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat()

        # Fetch user email from Graph.
        me_resp = await client.get(
            f"{_GRAPH_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        me_data = me_resp.json()
        user_email = me_data.get("mail") or me_data.get("userPrincipalName", "")

    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "expires_at": expires_at,
        "user_email": user_email,
    }


async def ensure_access_token(settings: "Settings | None" = None) -> str:
    """Return a valid access token, refreshing it if necessary.

    If the stored token is still valid (with a 30-second buffer before expiry),
    return it directly.  Otherwise, use ``ms_graph_refresh_token`` to obtain a
    new pair and persist it via ``jam.db.set_settings_batch`` and ``os.environ``.

    Raises RuntimeError if no refresh token is available.
    """
    from jam.config import Settings as _Settings

    settings = settings or _Settings()

    # ── Check if cached token is still fresh ─────────────────────────────────
    access_token = settings.ms_graph_access_token
    expires_at_str = settings.ms_graph_token_expires_at

    if access_token and expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            # Normalise to UTC-aware if naive.
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) + timedelta(seconds=_EXPIRY_BUFFER_SECONDS)
            if expires_at > cutoff:
                return access_token
        except ValueError:
            pass  # Malformed expiry — fall through to refresh.

    # ── Refresh ───────────────────────────────────────────────────────────────
    refresh_token = settings.ms_graph_refresh_token
    if not refresh_token:
        raise RuntimeError(
            "No ms_graph_refresh_token available. "
            "Complete the OAuth flow first via /ms_graph/auth."
        )

    authority = _authority(settings.ms_graph_tenant)
    token_url = authority + _TOKEN_PATH

    data = {
        "client_id": settings.ms_graph_client_id,
        "client_secret": settings.ms_graph_client_secret,
        "scope": _SCOPES,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    client = _build_client()
    async with client:
        resp = await client.post(token_url, data=data)
        resp.raise_for_status()
        token_data = resp.json()

    new_access_token: str = token_data["access_token"]
    expires_in = int(token_data.get("expires_in", 3600))
    new_expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    updates: dict[str, str] = {
        "ms_graph_access_token": new_access_token,
        "ms_graph_token_expires_at": new_expires_at,
    }

    # Persist a new refresh_token if the server rotated it.
    if token_data.get("refresh_token"):
        new_rt: str = token_data["refresh_token"]
        updates["ms_graph_refresh_token"] = new_rt
        os.environ["MS_GRAPH_REFRESH_TOKEN"] = new_rt

    # Dual-write: DB + os.environ so subsequent Settings() reads pick them up.
    # Deferred import to avoid circular dependency at module level.
    import jam.db as _db

    _db.set_settings_batch(updates)
    os.environ["MS_GRAPH_ACCESS_TOKEN"] = new_access_token
    os.environ["MS_GRAPH_TOKEN_EXPIRES_AT"] = new_expires_at

    return new_access_token


async def upsert_event(
    round_row: dict,
    app_row: dict,
    settings: "Settings | None" = None,
) -> str:
    """Create or update an Outlook Calendar event for an interview round.

    - When ``round_row['graph_event_id']`` is falsy: POST to create a new event.
    - When it is set: PATCH the existing event.  Falls back to POST if the
      event was deleted in Outlook (404 on PATCH).

    Returns the Graph event ``id``.
    """
    from jam.config import Settings as _Settings

    settings = settings or _Settings()

    access_token = await ensure_access_token(settings)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    event_body = _build_event_body(round_row, app_row, settings)
    graph_event_id = round_row.get("graph_event_id") or ""

    client = _build_client()
    async with client:
        if graph_event_id:
            # Attempt PATCH first.
            patch_url = f"{_GRAPH_BASE}/me/events/{graph_event_id}"
            resp = await client.patch(patch_url, json=event_body, headers=headers)
            if resp.status_code == 404:
                # Event was deleted in Outlook — fall back to create.
                graph_event_id = ""
            else:
                resp.raise_for_status()
                return graph_event_id

        # Create a new event.
        calendar_id = (settings.ms_graph_calendar_id or "").strip()
        if calendar_id:
            create_url = f"{_GRAPH_BASE}/me/calendars/{calendar_id}/events"
        else:
            create_url = f"{_GRAPH_BASE}/me/events"

        resp = await client.post(create_url, json=event_body, headers=headers)
        resp.raise_for_status()
        return resp.json()["id"]


async def delete_event(
    graph_event_id: str,
    settings: "Settings | None" = None,
) -> None:
    """Delete an Outlook Calendar event by its Graph event ID.

    Swallows 404 responses silently (event already gone).
    """
    from jam.config import Settings as _Settings

    settings = settings or _Settings()

    access_token = await ensure_access_token(settings)
    headers = {"Authorization": f"Bearer {access_token}"}

    client = _build_client()
    async with client:
        resp = await client.delete(
            f"{_GRAPH_BASE}/me/events/{graph_event_id}",
            headers=headers,
        )
        if resp.status_code == 404:
            return
        resp.raise_for_status()
