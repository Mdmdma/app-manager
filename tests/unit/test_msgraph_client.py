"""Unit tests for jam.msgraph_client — Microsoft Graph / Outlook Calendar client."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jam.config import Settings
from jam.msgraph_client import (
    _build_event_body,
    _GRAPH_BASE,
    _SCOPES,
    delete_event,
    ensure_access_token,
    exchange_code,
    get_auth_url,
    upsert_event,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _future_expires_at(seconds: int = 3600) -> str:
    """Return an ISO-format UTC datetime that is *seconds* from now."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _past_expires_at(seconds: int = 3600) -> str:
    """Return an ISO-format UTC datetime that was *seconds* ago."""
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _make_settings(**overrides) -> Settings:
    """Return a Settings instance with MS Graph fields populated."""
    defaults = dict(
        ms_graph_client_id="test-client-id",
        ms_graph_client_secret="test-client-secret",
        ms_graph_tenant="test-tenant",
        ms_graph_redirect_uri="http://localhost:8001/ms_graph/callback",
        ms_graph_refresh_token="test-refresh-token",
        ms_graph_access_token="test-access-token",
        ms_graph_token_expires_at=_future_expires_at(),
        ms_graph_user_email="user@example.com",
        ms_graph_calendar_id="",
        calendar_timezone="Europe/Berlin",
        calendar_default_duration_minutes=60,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_round_row(**overrides) -> dict:
    """Return a minimal interview round row dict."""
    defaults = dict(
        round_number=1,
        round_type="technical",
        scheduled_at="2026-05-15",
        scheduled_time="14:00",
        location="Meeting Room A",
        links="https://meet.example.com/abc\nhttps://docs.example.com/prep",
        prep_notes="Review Python basics.",
        graph_event_id="",
    )
    defaults.update(overrides)
    return defaults


def _make_app_row(**overrides) -> dict:
    """Return a minimal application row dict."""
    defaults = dict(
        company="Acme Corp",
        position="Software Engineer",
    )
    defaults.update(overrides)
    return defaults


def _make_sync_response(
    status_code: int = 200,
    body: dict | None = None,
) -> MagicMock:
    """Return a MagicMock that looks like an httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            str(status_code),
            request=httpx.Request("GET", "http://x"),
            response=httpx.Response(status_code),
        )
    else:
        resp.raise_for_status = MagicMock(return_value=None)
    return resp


class _MockAsyncClient:
    """Async context manager that exposes configurable get/post/patch/delete."""

    def __init__(self, responses: list[MagicMock]):
        self._responses = iter(responses)
        self.calls: list[tuple[str, str]] = []  # (method, url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def _record(self, method: str, url: str, **_kwargs) -> MagicMock:
        self.calls.append((method, url))
        return next(self._responses)

    async def get(self, url: str, **kwargs):
        return await self._record("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self._record("POST", url, **kwargs)

    async def patch(self, url: str, **kwargs):
        return await self._record("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs):
        return await self._record("DELETE", url, **kwargs)


# ── get_auth_url ──────────────────────────────────────────────────────────────


def test_get_auth_url_contains_required_params():
    """Auth URL must include client_id, redirect_uri, scope, response_type=code, state=jam."""
    settings = _make_settings()
    url = get_auth_url(settings)

    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "state=jam" in url
    # redirect_uri is URL-encoded in the query string
    assert "redirect_uri=" in url
    assert "localhost" in url  # part of redirect_uri
    # scope tokens are present (may be encoded)
    assert "Calendars.ReadWrite" in url
    assert "offline_access" in url


def test_get_auth_url_interpolates_tenant():
    """The authority URL must contain the tenant string."""
    settings = _make_settings(ms_graph_tenant="my-tenant-id")
    url = get_auth_url(settings)

    assert "my-tenant-id" in url
    assert "login.microsoftonline.com" in url


def test_get_auth_url_response_mode_query():
    """Auth URL must include response_mode=query."""
    settings = _make_settings()
    url = get_auth_url(settings)
    assert "response_mode=query" in url


# ── exchange_code ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exchange_code_returns_tokens_and_user_email():
    """exchange_code must return all 4 required keys."""
    settings = _make_settings()

    future_ts = _future_expires_at()
    token_response = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
    }
    me_response = {
        "mail": "user@example.com",
        "userPrincipalName": "user@example.com",
    }

    mock_client = _MockAsyncClient([
        _make_sync_response(200, token_response),
        _make_sync_response(200, me_response),
    ])

    with patch("jam.msgraph_client._build_client", return_value=mock_client):
        result = await exchange_code("auth-code-xyz", settings)

    assert "refresh_token" in result
    assert "access_token" in result
    assert "expires_at" in result
    assert "user_email" in result
    assert result["refresh_token"] == "new-refresh-token"
    assert result["access_token"] == "new-access-token"
    assert result["user_email"] == "user@example.com"
    # expires_at must be a parseable ISO datetime
    datetime.fromisoformat(result["expires_at"])


@pytest.mark.asyncio
async def test_exchange_code_falls_back_to_user_principal_name():
    """When 'mail' is absent, user_email is set from userPrincipalName."""
    settings = _make_settings()

    token_response = {
        "access_token": "tok",
        "refresh_token": "rt",
        "expires_in": 3600,
    }
    me_response = {"userPrincipalName": "upn@tenant.onmicrosoft.com"}

    mock_client = _MockAsyncClient([
        _make_sync_response(200, token_response),
        _make_sync_response(200, me_response),
    ])

    with patch("jam.msgraph_client._build_client", return_value=mock_client):
        result = await exchange_code("code", settings)

    assert result["user_email"] == "upn@tenant.onmicrosoft.com"


# ── ensure_access_token ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ensure_access_token_returns_cached_when_fresh():
    """If stored token is still valid (far-future expiry), return it without HTTP."""
    settings = _make_settings(
        ms_graph_access_token="cached-token",
        ms_graph_token_expires_at=_future_expires_at(7200),
    )

    # No HTTP call should happen — _build_client must not be invoked.
    with patch("jam.msgraph_client._build_client") as mock_build:
        result = await ensure_access_token(settings)

    assert result == "cached-token"
    mock_build.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_access_token_refreshes_when_expired():
    """When stored token is expired, POST to token URL and persist results."""
    settings = _make_settings(
        ms_graph_access_token="old-token",
        ms_graph_token_expires_at=_past_expires_at(3600),
        ms_graph_refresh_token="my-refresh-token",
    )

    token_response = {
        "access_token": "fresh-token",
        "expires_in": 3600,
    }

    mock_client = _MockAsyncClient([_make_sync_response(200, token_response)])

    with patch("jam.msgraph_client._build_client", return_value=mock_client):
        with patch("jam.db.set_settings_batch") as mock_persist:
            result = await ensure_access_token(settings)

    assert result == "fresh-token"
    # Verify a POST to the token endpoint happened.
    assert any(method == "POST" for method, _ in mock_client.calls)
    token_url_call = [url for method, url in mock_client.calls if method == "POST"][0]
    assert "oauth2/v2.0/token" in token_url_call
    assert "test-tenant" in token_url_call
    # Verify persistence was called with the new values.
    mock_persist.assert_called_once()
    persisted = mock_persist.call_args[0][0]
    assert persisted["ms_graph_access_token"] == "fresh-token"
    assert "ms_graph_token_expires_at" in persisted


@pytest.mark.asyncio
async def test_ensure_access_token_persists_rotated_refresh_token():
    """When the server returns a new refresh_token, it must also be persisted."""
    settings = _make_settings(
        ms_graph_access_token="",
        ms_graph_token_expires_at="",
        ms_graph_refresh_token="old-rt",
    )

    token_response = {
        "access_token": "new-at",
        "refresh_token": "rotated-rt",
        "expires_in": 3600,
    }

    mock_client = _MockAsyncClient([_make_sync_response(200, token_response)])

    with patch("jam.msgraph_client._build_client", return_value=mock_client):
        with patch("jam.db.set_settings_batch") as mock_persist:
            await ensure_access_token(settings)

    persisted = mock_persist.call_args[0][0]
    assert persisted.get("ms_graph_refresh_token") == "rotated-rt"


@pytest.mark.asyncio
async def test_ensure_access_token_raises_without_refresh_token():
    """RuntimeError is raised when no refresh token is available."""
    settings = _make_settings(
        ms_graph_access_token="",
        ms_graph_token_expires_at="",
        ms_graph_refresh_token="",
    )

    with pytest.raises(RuntimeError, match="ms_graph_refresh_token"):
        await ensure_access_token(settings)


@pytest.mark.asyncio
async def test_ensure_access_token_treats_near_expiry_as_expired():
    """Token expiring in <30 s (within the buffer) must trigger a refresh."""
    settings = _make_settings(
        ms_graph_access_token="soon-expiring",
        # expires in 10 seconds — within the 30 s buffer
        ms_graph_token_expires_at=_future_expires_at(10),
        ms_graph_refresh_token="my-refresh-token",
    )

    token_response = {"access_token": "refreshed", "expires_in": 3600}
    mock_client = _MockAsyncClient([_make_sync_response(200, token_response)])

    with patch("jam.msgraph_client._build_client", return_value=mock_client):
        with patch("jam.db.set_settings_batch"):
            result = await ensure_access_token(settings)

    assert result == "refreshed"


# ── _build_event_body ─────────────────────────────────────────────────────────


def test_build_event_body_timed():
    """Round with date + HH:MM produces correct start/end ISO strings."""
    settings = _make_settings(
        calendar_timezone="Europe/Berlin",
        calendar_default_duration_minutes=60,
    )
    round_row = _make_round_row(
        scheduled_at="2026-05-15",
        scheduled_time="14:00",
    )
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["isAllDay"] is False
    assert body["start"]["dateTime"] == "2026-05-15T14:00:00"
    assert body["end"]["dateTime"] == "2026-05-15T15:00:00"
    assert body["start"]["timeZone"] == "Europe/Berlin"
    assert body["end"]["timeZone"] == "Europe/Berlin"


def test_build_event_body_timed_90_minutes():
    """Duration of 90 minutes is correctly added to start time."""
    settings = _make_settings(calendar_default_duration_minutes=90)
    round_row = _make_round_row(scheduled_at="2026-06-01", scheduled_time="09:30")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["start"]["dateTime"] == "2026-06-01T09:30:00"
    assert body["end"]["dateTime"] == "2026-06-01T11:00:00"
    assert body["isAllDay"] is False


def test_build_event_body_all_day_when_time_missing():
    """Round with date but empty scheduled_time produces an all-day event."""
    settings = _make_settings(calendar_timezone="UTC")
    round_row = _make_round_row(scheduled_at="2026-05-20", scheduled_time="")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["isAllDay"] is True
    assert body["start"]["dateTime"] == "2026-05-20T00:00:00"
    assert body["end"]["dateTime"] == "2026-05-21T00:00:00"
    assert body["start"]["timeZone"] == "UTC"


def test_build_event_body_all_day_crosses_month_boundary():
    """All-day event on last day of month rolls end over to next month."""
    settings = _make_settings(calendar_timezone="UTC")
    round_row = _make_round_row(scheduled_at="2026-01-31", scheduled_time="")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["end"]["dateTime"] == "2026-02-01T00:00:00"


def test_build_event_body_subject_and_location():
    """Subject contains company, position, round_number, round_type; location from row."""
    settings = _make_settings()
    round_row = _make_round_row(
        round_number=2,
        round_type="hr",
        location="Room 42",
    )
    app_row = _make_app_row(company="BigCo", position="Staff Engineer")

    body = _build_event_body(round_row, app_row, settings)

    assert "BigCo" in body["subject"]
    assert "Staff Engineer" in body["subject"]
    assert "2" in body["subject"]
    assert "hr" in body["subject"]
    assert body["location"]["displayName"] == "Room 42"


def test_build_event_body_location_falls_back_to_first_link():
    """When location is empty, location.displayName is the first link."""
    settings = _make_settings()
    round_row = _make_round_row(
        location="",
        links="https://meet.example.com/room\nhttps://other.example.com",
    )
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["location"]["displayName"] == "https://meet.example.com/room"


def test_build_event_body_location_empty_when_no_links():
    """When both location and links are empty, displayName is empty string."""
    settings = _make_settings()
    round_row = _make_round_row(location="", links="")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert body["location"]["displayName"] == ""


def test_build_event_body_escapes_html_in_prep_notes():
    """prep_notes containing HTML characters must be escaped in the body content."""
    settings = _make_settings()
    round_row = _make_round_row(prep_notes="<script>alert('xss')</script>")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert "<script>" not in body["body"]["content"]
    assert "&lt;script&gt;" in body["body"]["content"]


def test_build_event_body_links_rendered_as_anchors():
    """Links are rendered as <a href="...">...</a> elements in the HTML body."""
    settings = _make_settings()
    round_row = _make_round_row(
        links="https://meet.example.com/abc\nhttps://docs.example.com/prep"
    )
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert '<a href="https://meet.example.com/abc">' in body["body"]["content"]
    assert '<a href="https://docs.example.com/prep">' in body["body"]["content"]


def test_build_event_body_missing_round_fields_use_defaults():
    """round_type defaults to 'other', round_number defaults to 1."""
    settings = _make_settings()
    round_row = _make_round_row()
    round_row.pop("round_type")
    round_row.pop("round_number")
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    assert "other" in body["subject"]
    assert "1" in body["subject"]


def test_build_event_body_malformed_scheduled_time_raises():
    """A malformed scheduled_time (not HH:MM) must raise ValueError."""
    settings = _make_settings()
    round_row = _make_round_row(scheduled_time="25:99")
    app_row = _make_app_row()

    with pytest.raises(ValueError):
        _build_event_body(round_row, app_row, settings)


def test_build_event_body_non_numeric_scheduled_time_raises():
    """Non-numeric scheduled_time must raise ValueError."""
    settings = _make_settings()
    round_row = _make_round_row(scheduled_time="ab:cd")
    app_row = _make_app_row()

    with pytest.raises(ValueError):
        _build_event_body(round_row, app_row, settings)


def test_build_event_body_has_required_fields():
    """Event body always includes subject, body, location, start, end, isAllDay, attendees."""
    settings = _make_settings()
    round_row = _make_round_row()
    app_row = _make_app_row()

    body = _build_event_body(round_row, app_row, settings)

    for key in ("subject", "body", "location", "start", "end", "isAllDay", "attendees"):
        assert key in body, f"Missing key: {key}"
    assert body["reminderMinutesBeforeStart"] == 15
    assert body["attendees"] == []


# ── upsert_event ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_event_creates_when_no_id():
    """Round with empty graph_event_id causes a POST to /me/events; returns new id."""
    settings = _make_settings(ms_graph_calendar_id="")
    round_row = _make_round_row(graph_event_id="")
    app_row = _make_app_row()

    create_response = {"id": "new-event-id-123"}
    mock_client = _MockAsyncClient([_make_sync_response(200, create_response)])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            result = await upsert_event(round_row, app_row, settings)

    assert result == "new-event-id-123"
    methods = [m for m, _ in mock_client.calls]
    assert "POST" in methods
    assert "PATCH" not in methods


@pytest.mark.asyncio
async def test_upsert_event_uses_calendar_id_when_set():
    """When calendar_id is set, POST goes to /me/calendars/{id}/events."""
    settings = _make_settings(ms_graph_calendar_id="my-cal-id")
    round_row = _make_round_row(graph_event_id="")
    app_row = _make_app_row()

    create_response = {"id": "evt-abc"}
    mock_client = _MockAsyncClient([_make_sync_response(200, create_response)])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            result = await upsert_event(round_row, app_row, settings)

    assert result == "evt-abc"
    post_url = [url for m, url in mock_client.calls if m == "POST"][0]
    assert "my-cal-id" in post_url


@pytest.mark.asyncio
async def test_upsert_event_patches_when_id_present():
    """Round with graph_event_id causes a PATCH to /me/events/{id}; returns same id."""
    settings = _make_settings()
    event_id = "existing-event-id"
    round_row = _make_round_row(graph_event_id=event_id)
    app_row = _make_app_row()

    # PATCH returns success (204 / any 2xx with empty body is fine).
    mock_client = _MockAsyncClient([_make_sync_response(200, {})])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            result = await upsert_event(round_row, app_row, settings)

    assert result == event_id
    methods = [m for m, _ in mock_client.calls]
    assert "PATCH" in methods
    assert "POST" not in methods
    patch_url = [url for m, url in mock_client.calls if m == "PATCH"][0]
    assert event_id in patch_url


@pytest.mark.asyncio
async def test_upsert_event_falls_back_to_create_on_404_patch():
    """When PATCH returns 404, the function falls back to POST and returns the new id."""
    settings = _make_settings(ms_graph_calendar_id="")
    event_id = "deleted-event-id"
    round_row = _make_round_row(graph_event_id=event_id)
    app_row = _make_app_row()

    patch_404 = MagicMock()
    patch_404.status_code = 404
    patch_404.raise_for_status = MagicMock(return_value=None)

    create_response = {"id": "brand-new-event-id"}
    mock_client = _MockAsyncClient([
        patch_404,
        _make_sync_response(200, create_response),
    ])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            result = await upsert_event(round_row, app_row, settings)

    assert result == "brand-new-event-id"
    methods = [m for m, _ in mock_client.calls]
    assert "PATCH" in methods
    assert "POST" in methods


# ── delete_event ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_event_sends_delete_request():
    """delete_event issues DELETE to /me/events/{id}."""
    settings = _make_settings()
    event_id = "event-to-delete"

    delete_resp = MagicMock()
    delete_resp.status_code = 204
    delete_resp.raise_for_status = MagicMock(return_value=None)

    mock_client = _MockAsyncClient([delete_resp])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            await delete_event(event_id, settings)

    methods = [m for m, _ in mock_client.calls]
    assert "DELETE" in methods
    delete_url = [url for m, url in mock_client.calls if m == "DELETE"][0]
    assert event_id in delete_url


@pytest.mark.asyncio
async def test_delete_event_swallows_404():
    """DELETE returning 404 must not raise an exception."""
    settings = _make_settings()

    not_found = MagicMock()
    not_found.status_code = 404
    not_found.raise_for_status = MagicMock(return_value=None)

    mock_client = _MockAsyncClient([not_found])

    with patch("jam.msgraph_client.ensure_access_token", return_value="tok"):
        with patch("jam.msgraph_client._build_client", return_value=mock_client):
            # Must not raise.
            await delete_event("already-gone-id", settings)
