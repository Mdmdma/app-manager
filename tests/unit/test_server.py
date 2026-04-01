import json
import re
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID
from datetime import date

from jam.server import app, ApplicationStatus
from jam import db as _db_module
from jam.html_page import HTML_PAGE


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")



@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Point every db call to a fresh SQLite db for each test."""
    db_path = tmp_path / "test.db"
    _db_module.init_db(db_path)

    # Map server alias -> db module function name
    alias_to_db = {
        "db_create_application": "create_application",
        "db_get_application": "get_application",
        "db_list_applications": "list_applications",
        "db_update_application": "update_application",
        "db_delete_application": "delete_application",
        "db_create_document": "create_document",
        "db_get_document": "get_document",
        "db_list_documents": "list_documents",
        "db_update_document": "update_document",
        "db_delete_document": "delete_document",
        "db_create_version": "create_version",
        "db_list_versions": "list_versions",
        "db_get_version": "get_version",
        "db_create_extra_question": "create_extra_question",
        "db_list_extra_questions": "list_extra_questions",
        "db_get_extra_question": "get_extra_question",
        "db_update_extra_question": "update_extra_question",
        "db_delete_extra_question": "delete_extra_question",
        "db_create_interview_round": "create_interview_round",
        "db_list_interview_rounds": "list_interview_rounds",
        "db_get_interview_round": "get_interview_round",
        "db_update_interview_round": "update_interview_round",
        "db_delete_interview_round": "delete_interview_round",
        "db_create_offer": "create_offer",
        "db_list_offers": "list_offers",
        "db_get_offer": "get_offer",
        "db_update_offer": "update_offer",
        "db_delete_offer": "delete_offer",
    }

    patchers = []
    for server_name, db_name in alias_to_db.items():
        original = getattr(_db_module, db_name)
        # capture db_path and original in closure
        def _make_side_effect(fn, p):
            return lambda *a, **kw: fn(*a, db_path=p, **kw)

        patchers.append(
            patch(
                f"jam.server.{server_name}",
                side_effect=_make_side_effect(original, db_path),
            )
        )

    # Also route settings and catalog functions to the test DB
    for fn_name in ("get_all_settings", "set_setting", "set_settings_batch", "get_catalog"):
        original = getattr(_db_module, fn_name)
        patchers.append(
            patch(
                f"jam.server.{fn_name}",
                side_effect=_make_side_effect(original, db_path),
            )
        )

    for p in patchers:
        p.start()
    yield db_path
    for p in patchers:
        p.stop()


@pytest.mark.asyncio
async def test_index_returns_html(client):
    """GET / should return the HTML page."""
    resp = await client.get("/api/v1/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Job Application Manager" in resp.text


@pytest.mark.asyncio
async def test_health_kb_reachable(client):
    """GET /health should report kb_status ok when kb is reachable."""
    mock_resp = MagicMock(status_code=200)

    async def fake_get(*args, **kwargs):
        return mock_resp

    mock_client = MagicMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = lambda self: _async_return(mock_client)
    mock_client.__aexit__ = lambda self, *a: _async_return(None)

    with patch("jam.server.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["kb_status"] == "ok"


@pytest.mark.asyncio
async def test_health_kb_unreachable(client):
    """GET /health should report kb_status unreachable when kb is down."""
    import httpx as _httpx

    async def fake_get(*args, **kwargs):
        raise _httpx.ConnectError("Connection refused")

    mock_client = MagicMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = lambda self: _async_return(mock_client)
    mock_client.__aexit__ = lambda self, *a: _async_return(None)

    with patch("jam.server.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["kb_status"] == "unreachable"


async def _async_return(val):
    return val


@pytest.mark.asyncio
async def test_list_applications_empty(client):
    """GET /applications should return empty list initially."""
    resp = await client.get("/api/v1/applications")
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


@pytest.mark.asyncio
async def test_create_application(client):
    """POST /applications should create a new application."""
    resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Google",
            "position": "Software Engineer",
            "status": "applied",
            "url": "https://google.com/jobs/123",
            "notes": "Great company",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["company"] == "Google"
    assert data["position"] == "Software Engineer"
    assert data["status"] == "applied"
    assert data["url"] == "https://google.com/jobs/123"
    assert data["notes"] == "Great company"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # Default applied_date should be today
    assert data["applied_date"] == date.today().isoformat()


@pytest.mark.asyncio
async def test_create_application_with_custom_date(client):
    """POST /applications with custom applied_date."""
    resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Microsoft",
            "position": "Product Manager",
            "applied_date": "2025-01-15",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["applied_date"] == "2025-01-15"


@pytest.mark.asyncio
async def test_create_application_minimal(client):
    """POST /applications with minimal required fields."""
    resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Amazon",
            "position": "Data Scientist",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["company"] == "Amazon"
    assert data["position"] == "Data Scientist"
    assert data["status"] == "not_applied_yet"
    assert data["url"] is None
    assert data["notes"] is None


@pytest.mark.asyncio
async def test_create_application_invalid_company(client):
    """POST /applications with empty company should fail."""
    resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "",
            "position": "Engineer",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_application_auto_creates_documents(client):
    """POST /applications should auto-create CV and Cover Letter documents."""
    resp = await client.post(
        "/api/v1/applications",
        json={"company": "Test Co", "position": "Dev"},
    )
    assert resp.status_code == 201
    app_id = resp.json()["id"]
    docs_resp = await client.get(f"/api/v1/applications/{app_id}/documents")
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    assert len(docs) == 2
    doc_types = {d["doc_type"] for d in docs}
    assert doc_types == {"cv", "cover_letter"}
    # Both should have non-empty latex from default templates
    for doc in docs:
        assert doc["latex_source"].strip() != ""
        assert "\\documentclass" in doc["latex_source"]


@pytest.mark.asyncio
async def test_create_application_uses_settings_templates(client, isolated_db):
    """Auto-created docs should use templates from settings when available."""
    custom_cv = "\\documentclass{article}\\begin{document}Custom CV\\end{document}"
    custom_cl = "\\documentclass{letter}\\begin{document}Custom CL\\end{document}"
    _db_module.set_setting("cv_latex_template", custom_cv, db_path=isolated_db)
    _db_module.set_setting("cover_letter_latex_template", custom_cl, db_path=isolated_db)
    resp = await client.post(
        "/api/v1/applications",
        json={"company": "Tpl Co", "position": "Eng"},
    )
    assert resp.status_code == 201
    app_id = resp.json()["id"]
    docs_resp = await client.get(f"/api/v1/applications/{app_id}/documents")
    docs = docs_resp.json()
    by_type = {d["doc_type"]: d for d in docs}
    assert by_type["cv"]["latex_source"] == custom_cv
    assert by_type["cover_letter"]["latex_source"] == custom_cl


@pytest.mark.asyncio
async def test_import_from_url_auto_creates_documents(client):
    """POST /applications/from-url should auto-create CV and Cover Letter documents."""
    extracted = {"company": "Acme", "position": "Dev"}
    with patch("jam.server._fetch_page_text", return_value=("x" * 200, "html")), \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_url", return_value=None):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/job"},
        )
    assert resp.status_code == 201
    app_id = resp.json()["application"]["id"]
    docs_resp = await client.get(f"/api/v1/applications/{app_id}/documents")
    docs = docs_resp.json()
    assert len(docs) == 2
    doc_types = {d["doc_type"] for d in docs}
    assert doc_types == {"cv", "cover_letter"}


@pytest.mark.asyncio
async def test_list_applications_after_create(client):
    """GET /applications should list created applications."""
    # Create two applications
    resp1 = await client.post(
        "/api/v1/applications",
        json={"company": "Google", "position": "Engineer"},
    )
    app1_id = resp1.json()["id"]
    
    resp2 = await client.post(
        "/api/v1/applications",
        json={"company": "Microsoft", "position": "Manager"},
    )
    app2_id = resp2.json()["id"]
    
    # List all
    resp = await client.get("/api/v1/applications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    companies = {app["company"] for app in data}
    assert companies == {"Google", "Microsoft"}


@pytest.mark.asyncio
async def test_get_application(client):
    """GET /applications/{id} should return the application."""
    # Create
    create_resp = await client.post(
        "/api/v1/applications",
        json={"company": "Apple", "position": "Engineer"},
    )
    app_id = create_resp.json()["id"]
    
    # Get
    resp = await client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == app_id
    assert data["company"] == "Apple"
    assert data["position"] == "Engineer"


@pytest.mark.asyncio
async def test_get_application_not_found(client):
    """GET /applications/{id} should return 404 for missing app."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/applications/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_application(client):
    """PUT /applications/{id} should update the application."""
    # Create
    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Facebook",
            "position": "Junior Engineer",
            "status": "applied",
        },
    )
    app_id = create_resp.json()["id"]
    
    # Update
    resp = await client.put(
        f"/api/v1/applications/{app_id}",
        json={
            "position": "Senior Engineer",
            "status": "interviewing",
            "notes": "Phone screen passed",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == app_id
    assert data["company"] == "Facebook"  # unchanged
    assert data["position"] == "Senior Engineer"  # changed
    assert data["status"] == "interviewing"  # changed
    assert data["notes"] == "Phone screen passed"  # changed
    # created_at should be unchanged, updated_at should be newer
    create_data = create_resp.json()
    assert data["created_at"] == create_data["created_at"]
    assert data["updated_at"] > create_data["updated_at"]


@pytest.mark.asyncio
async def test_update_application_partial(client):
    """PUT /applications/{id} with partial fields."""
    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Tesla",
            "position": "Engineer",
            "notes": "Original notes",
        },
    )
    app_id = create_resp.json()["id"]
    
    # Update only status
    resp = await client.put(
        f"/api/v1/applications/{app_id}",
        json={"status": "rejected"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["company"] == "Tesla"  # unchanged
    assert data["notes"] == "Original notes"  # unchanged
    assert data["status"] == "rejected"  # changed


@pytest.mark.asyncio
async def test_update_application_not_found(client):
    """PUT /applications/{id} should return 404 for missing app."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.put(
        f"/api/v1/applications/{fake_id}",
        json={"status": "accepted"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_application(client):
    """DELETE /applications/{id} should remove the application."""
    # Create
    create_resp = await client.post(
        "/api/v1/applications",
        json={"company": "Netflix", "position": "Engineer"},
    )
    app_id = create_resp.json()["id"]
    
    # Verify it exists
    get_resp = await client.get(f"/api/v1/applications/{app_id}")
    assert get_resp.status_code == 200
    
    # Delete
    resp = await client.delete(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 204
    
    # Verify it's gone
    get_resp = await client.get(f"/api/v1/applications/{app_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_application_not_found(client):
    """DELETE /applications/{id} should return 404 for missing app."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/v1/applications/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_application_status_enum(client):
    """Test all valid application statuses."""
    statuses = [
        "applied",
        "screening",
        "interviewing",
        "offered",
        "rejected",
        "accepted",
        "withdrawn",
    ]
    
    for status in statuses:
        resp = await client.post(
            "/api/v1/applications",
            json={
                "company": f"Company-{status}",
                "position": "Role",
                "status": status,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == status


@pytest.mark.asyncio
async def test_catalog_endpoint(client):
    """GET /catalog should return providers list."""
    resp = await client.get("/api/v1/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


@pytest.mark.asyncio
async def test_get_settings_empty(client):
    """GET /settings should return masked key flags when no settings stored."""
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["openai_api_key_set"] is False
    assert data["anthropic_api_key_set"] is False
    assert data["groq_api_key_set"] is False


@pytest.mark.asyncio
async def test_get_settings_with_stored_values(client, isolated_db):
    """GET /settings should show key_set=True and plain keys when stored."""
    _db_module.set_setting("openai_api_key", "sk-abc", db_path=isolated_db)
    _db_module.set_setting("llm_provider", "openai", db_path=isolated_db)
    _db_module.set_setting("llm_model", "gpt-4o", db_path=isolated_db)
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["openai_api_key_set"] is True
    assert data["anthropic_api_key_set"] is False
    assert data["llm_provider"] == "openai"
    assert data["llm_model"] == "gpt-4o"
    # Raw key must NOT be in response
    assert "openai_api_key" not in data


@pytest.mark.asyncio
async def test_save_settings_success(client):
    """POST /settings should persist provided keys and return saved list."""
    resp = await client.post(
        "/api/v1/settings",
        json={"llm_provider": "anthropic", "llm_model": "claude-sonnet-4-6"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert set(data["saved"]) == {"llm_provider", "llm_model"}


@pytest.mark.asyncio
async def test_save_settings_empty_body(client):
    """POST /settings with no fields should return 422."""
    resp = await client.post("/api/v1/settings", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_settings_sets_env(client):
    """POST /settings should set corresponding environment variables."""
    import os
    resp = await client.post(
        "/api/v1/settings",
        json={"llm_provider": "groq"},
    )
    assert resp.status_code == 200
    assert os.environ.get("LLM_PROVIDER") == "groq"


@pytest.mark.asyncio
async def test_save_and_get_template_settings(client):
    """POST /settings with templates should persist and GET should return them."""
    cv_tpl = "\\documentclass{article}\\begin{document}CV\\end{document}"
    cl_tpl = "\\documentclass{letter}\\begin{document}CL\\end{document}"
    resp = await client.post(
        "/api/v1/settings",
        json={"cv_latex_template": cv_tpl, "cover_letter_latex_template": cl_tpl},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "cv_latex_template" in data["saved"]
    assert "cover_letter_latex_template" in data["saved"]


@pytest.mark.asyncio
async def test_get_settings_returns_templates(client, isolated_db):
    """GET /settings should include template fields when stored."""
    _db_module.set_setting("cv_latex_template", "tpl-cv", db_path=isolated_db)
    _db_module.set_setting("cover_letter_latex_template", "tpl-cl", db_path=isolated_db)
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cv_latex_template"] == "tpl-cv"
    assert data["cover_letter_latex_template"] == "tpl-cl"


@pytest.mark.asyncio
async def test_save_settings_batch_is_atomic(client):
    """If set_settings_batch raises, the error propagates (nothing partially saved)."""
    import pytest as _pytest
    with patch("jam.server.set_settings_batch", side_effect=Exception("db error")):
        with _pytest.raises(Exception, match="db error"):
            await client.post(
                "/api/v1/settings",
                json={"llm_provider": "openai", "llm_model": "gpt-4o"},
            )


# --- Gmail endpoints ---

@pytest.mark.asyncio
async def test_get_settings_includes_gmail_fields(client, isolated_db):
    """GET /settings should include gmail_client_id and masked Gmail fields."""
    _db_module.set_setting("gmail_client_id", "123456.apps.googleusercontent.com", db_path=isolated_db)
    _db_module.set_setting("gmail_client_secret", "secret-key", db_path=isolated_db)
    _db_module.set_setting("gmail_refresh_token", "refresh-token", db_path=isolated_db)
    _db_module.set_setting("gmail_user_email", "user@example.com", db_path=isolated_db)
    
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    
    # Plain keys should be in response
    assert data["gmail_client_id"] == "123456.apps.googleusercontent.com"
    assert data["gmail_user_email"] == "user@example.com"
    
    # Secret and refresh token should be masked
    assert data["gmail_client_secret_set"] is True
    assert data["gmail_refresh_token_set"] is True
    
    # Raw secret and token should NOT be in response
    assert "gmail_client_secret" not in data
    assert "gmail_refresh_token" not in data


@pytest.mark.asyncio
async def test_save_settings_gmail_fields(client):
    """POST /settings should save Gmail fields."""
    resp = await client.post(
        "/api/v1/settings",
        json={
            "gmail_client_id": "123456.apps.googleusercontent.com",
            "gmail_client_secret": "secret-key",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "gmail_client_id" in data["saved"]
    assert "gmail_client_secret" in data["saved"]


@pytest.mark.asyncio
async def test_list_kb_namespaces(client):
    """GET /kb/namespaces proxies the kb API and returns namespace list."""
    sample = [{"id": "ns1", "name": "Resume"}, {"id": "ns2", "name": "Cover Letters"}]

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample
    mock_resp.raise_for_status = MagicMock()

    mock_http_client = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with patch("jam.server.httpx.AsyncClient", return_value=mock_http_client):
        resp = await client.get("/api/v1/kb/namespaces")

    assert resp.status_code == 200
    data = resp.json()
    assert data == sample


@pytest.mark.asyncio
async def test_list_kb_namespaces_kb_unavailable(client):
    """GET /kb/namespaces returns empty list when kb is unreachable."""
    import httpx as _httpx

    mock_http_client = MagicMock()
    mock_http_client.get = AsyncMock(side_effect=_httpx.ConnectError("refused"))
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with patch("jam.server.httpx.AsyncClient", return_value=mock_http_client):
        resp = await client.get("/api/v1/kb/namespaces")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_save_settings_kb_retrieval_fields(client):
    """POST /settings should save KB retrieval fields and return them in saved list."""
    resp = await client.post(
        "/api/v1/settings",
        json={
            "kb_retrieval_namespaces": '["ns1", "ns2"]',
            "kb_retrieval_n_results": 5,
            "kb_retrieval_padding": 1,
            "kb_include_namespaces": '["ns3"]',
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert set(data["saved"]) == {
        "kb_retrieval_namespaces",
        "kb_retrieval_n_results",
        "kb_retrieval_padding",
        "kb_include_namespaces",
    }


@pytest.mark.asyncio
async def test_get_settings_returns_kb_retrieval_fields(client, isolated_db):
    """GET /settings should return kb retrieval plain keys when stored."""
    _db_module.set_setting("kb_retrieval_namespaces", '["ns1"]', db_path=isolated_db)
    _db_module.set_setting("kb_retrieval_n_results", "5", db_path=isolated_db)
    _db_module.set_setting("kb_retrieval_padding", "2", db_path=isolated_db)
    _db_module.set_setting("kb_include_namespaces", '["ns2"]', db_path=isolated_db)

    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kb_retrieval_namespaces"] == '["ns1"]'
    assert data["kb_retrieval_n_results"] == "5"
    assert data["kb_retrieval_padding"] == "2"
    assert data["kb_include_namespaces"] == '["ns2"]'


@pytest.mark.asyncio
async def test_save_settings_rejects_model_provider_mismatch(client):
    """POST /settings should reject a model that doesn't belong to the given provider."""
    resp = await client.post(
        "/api/v1/settings",
        json={"llm_provider": "openai", "llm_model": "claude-sonnet-4-6"},
    )
    assert resp.status_code == 422
    assert "does not belong to provider" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_save_settings_accepts_valid_model_provider_pair(client):
    """POST /settings should accept a model that belongs to the given provider."""
    resp = await client.post(
        "/api/v1/settings",
        json={"llm_provider": "anthropic", "llm_model": "claude-sonnet-4-6"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_save_settings_allows_provider_only(client):
    """POST /settings with only llm_provider (no model) should succeed without validation."""
    resp = await client.post(
        "/api/v1/settings",
        json={"llm_provider": "openai"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_gmail_auth_url_with_valid_credentials(client, isolated_db):
    """GET /gmail/auth-url should return an auth URL when credentials are configured."""
    _db_module.set_setting("gmail_client_id", "123456.apps.googleusercontent.com", db_path=isolated_db)
    _db_module.set_setting("gmail_client_secret", "secret-key", db_path=isolated_db)
    
    with patch("jam.gmail_client.get_auth_url") as mock_get_auth:
        mock_get_auth.return_value = "https://accounts.google.com/auth?..."
        resp = await client.get("/api/v1/gmail/auth-url")
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data


@pytest.mark.asyncio
async def test_gmail_status_not_connected(client):
    """GET /gmail/status should return connected=false when no refresh_token."""
    resp = await client.get("/api/v1/gmail/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["email"] is None


@pytest.mark.asyncio
async def test_gmail_disconnect(client):
    """POST /gmail/disconnect should clear Gmail tokens."""
    import os
    
    # First set some values
    resp = await client.post(
        "/api/v1/settings",
        json={
            "gmail_refresh_token": "token-123",
            "gmail_user_email": "user@example.com",
        },
    )
    assert resp.status_code == 200
    
    # Now disconnect
    resp = await client.post("/api/v1/gmail/disconnect", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


# --- POST /applications/from-url ---
# --- POST /applications/from-url ---

@pytest.mark.asyncio
async def test_import_from_url_success(client):
    """POST /applications/from-url should create an application from a URL."""
    extracted = {
        "company": "Acme Corp",
        "position": "Backend Engineer",
        "location": "Remote",
        "salary_range": "$120k-$150k",
        "requirements": "Python, FastAPI",
        "description": "Great role",
        "opening_date": "2026-03-01",
        "closing_date": "2026-04-15",
    }
    page_text = "x" * 200
    with patch("jam.server._fetch_page_text", return_value=(page_text, "html")) as mock_fetch, \
         patch("jam.server.extract_job_info", return_value=extracted) as mock_llm, \
         patch("jam.server.ingest_url", return_value=None) as mock_kb:
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://acme.example.com/jobs/1"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["application"]["company"] == "Acme Corp"
    assert data["application"]["position"] == "Backend Engineer"
    assert data["application"]["url"] == "https://acme.example.com/jobs/1"
    assert data["application"]["status"] == "not_applied_yet"
    assert data["application"]["location"] == "Remote"
    assert data["application"]["salary_range"] == "$120k-$150k"
    assert data["application"]["opening_date"] == "2026-03-01"
    assert data["application"]["closing_date"] == "2026-04-15"
    assert data["application"]["description"] == "Great role"
    assert data["application"]["full_text"] == page_text
    assert data["extraction"] == extracted
    assert data["kb_ingested"] is True
    mock_fetch.assert_awaited_once_with("https://acme.example.com/jobs/1")
    mock_llm.assert_awaited_once()
    mock_kb.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_from_url_kb_down_still_succeeds(client):
    """POST /applications/from-url should succeed even when kb ingest fails."""
    extracted = {"company": "Startup", "position": "Fullstack Dev"}
    with patch("jam.server._fetch_page_text", return_value=("x" * 200, "html")), \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_url", side_effect=Exception("kb is down")):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://startup.example.com/jobs/2"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kb_ingested"] is False
    assert data["application"]["company"] == "Startup"


@pytest.mark.asyncio
async def test_import_from_url_fetch_failure_returns_422(client):
    """POST /applications/from-url should return 422 when URL fetch fails."""
    import httpx as _httpx
    with patch("jam.server._fetch_page_text", side_effect=_httpx.HTTPError("connection refused")):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://unreachable.example.com/"},
        )
    assert resp.status_code == 422
    assert "Failed to fetch URL" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_from_url_short_content_returns_422(client):
    """POST /applications/from-url should return 422 when page content is too short."""
    with patch("jam.server._fetch_page_text", return_value=("too short", "html")):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/empty"},
        )
    assert resp.status_code == 422
    assert "too short" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_from_url_llm_failure_returns_502(client):
    """POST /applications/from-url should return 502 when LLM extraction fails."""
    with patch("jam.server._fetch_page_text", return_value=("x" * 200, "html")), \
         patch("jam.server.extract_job_info", side_effect=RuntimeError("LLM timeout")):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/jobs/3"},
        )
    assert resp.status_code == 502
    assert "LLM extraction failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_import_from_url_missing_llm_fields_use_unknown(client):
    """POST /applications/from-url should fall back to 'Unknown' for missing company/position."""
    extracted = {}
    with patch("jam.server._fetch_page_text", return_value=("x" * 200, "html")), \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_url", return_value=None):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/jobs/4"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["application"]["company"] == "Unknown"
    assert data["application"]["position"] == "Unknown"


@pytest.mark.asyncio
async def test_import_from_url_empty_url_returns_422(client):
    """POST /applications/from-url with empty url should fail validation."""
    resp = await client.post(
        "/api/v1/applications/from-url",
        json={"url": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_import_from_url_pdf_uses_ingest_text(client):
    """POST /applications/from-url with PDF should call ingest_text, not ingest_url."""
    extracted = {
        "company": "Tech Corp",
        "position": "Senior Engineer",
        "location": "NYC",
    }
    with patch("jam.server._fetch_page_text", return_value=("PDF content here " * 5, "pdf")) as mock_fetch, \
         patch("jam.server.extract_job_info", return_value=extracted) as mock_llm, \
         patch("jam.server.ingest_text", return_value=None) as mock_kb_text, \
         patch("jam.server.ingest_url") as mock_kb_url:
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/job.pdf"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["application"]["company"] == "Tech Corp"
    assert data["kb_ingested"] is True
    # Verify ingest_text was called, not ingest_url
    mock_kb_text.assert_awaited_once()
    mock_kb_url.assert_not_awaited()
    # Verify it passed the extracted text and URL
    call_args = mock_kb_text.call_args
    assert "PDF content here" in call_args[0][0]  # text arg
    assert "https://example.com/job.pdf" in call_args[0][1]  # url arg


@pytest.mark.asyncio
async def test_import_from_url_text_uses_ingest_text(client):
    """POST /applications/from-url with plain text should call ingest_text."""
    extracted = {
        "company": "Startup Inc",
        "position": "Full Stack Dev",
    }
    with patch("jam.server._fetch_page_text", return_value=("Plain text job posting " * 5, "text")) as mock_fetch, \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_text", return_value=None) as mock_kb_text, \
         patch("jam.server.ingest_url") as mock_kb_url:
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/job.txt"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kb_ingested"] is True
    # Verify ingest_text was called, not ingest_url
    mock_kb_text.assert_awaited_once()
    mock_kb_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_from_url_html_uses_ingest_url(client):
    """POST /applications/from-url with HTML should call ingest_url, not ingest_text."""
    extracted = {
        "company": "Web Co",
        "position": "Frontend Dev",
    }
    with patch("jam.server._fetch_page_text", return_value=("<html>job posting</html>" * 5, "html")) as mock_fetch, \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_url", return_value=None) as mock_kb_url, \
         patch("jam.server.ingest_text") as mock_kb_text:
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://example.com/job"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["kb_ingested"] is True
    # Verify ingest_url was called, not ingest_text
    mock_kb_url.assert_awaited_once()
    mock_kb_text.assert_not_awaited()


# --- Document endpoints ---

async def _create_test_app(client):
    """Helper: create an application and return its ID."""
    resp = await client.post(
        "/api/v1/applications",
        json={"company": "TestCo", "position": "Engineer"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_document(client):
    app_id = await _create_test_app(client)
    resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "My CV", "latex_source": "\\documentclass{article}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "cv"
    assert data["title"] == "My CV"
    assert data["latex_source"] == "\\documentclass{article}"
    assert data["application_id"] == app_id
    assert data["id"]


@pytest.mark.asyncio
async def test_create_document_cover_letter(client):
    app_id = await _create_test_app(client)
    resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cover_letter", "title": "My CL"},
    )
    assert resp.status_code == 201
    assert resp.json()["doc_type"] == "cover_letter"


@pytest.mark.asyncio
async def test_create_document_invalid_app(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/applications/{fake_id}/documents",
        json={"doc_type": "cv", "title": "Test"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_documents(client):
    app_id = await _create_test_app(client)
    # 2 auto-created (CV + Cover Letter) + 2 manually created = 4
    await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "CV 1"},
    )
    await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cover_letter", "title": "CL 1"},
    )
    resp = await client.get(f"/api/v1/applications/{app_id}/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 4


@pytest.mark.asyncio
async def test_list_documents_filter_by_type(client):
    app_id = await _create_test_app(client)
    # 1 auto-created CV + 1 manually created CV = 2 CVs
    await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "CV 1"},
    )
    await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cover_letter", "title": "CL 1"},
    )
    resp = await client.get(
        f"/api/v1/applications/{app_id}/documents?doc_type=cv"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(d["doc_type"] == "cv" for d in data)


@pytest.mark.asyncio
async def test_list_documents_invalid_app(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/applications/{fake_id}/documents")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_document(client):
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "My CV"},
    )
    doc_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My CV"


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    resp = await client.get("/api/v1/documents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_document(client):
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "Old Title"},
    )
    doc_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "New Title", "latex_source": "new src"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["latex_source"] == "new src"


@pytest.mark.asyncio
async def test_update_document_not_found(client):
    resp = await client.put(
        "/api/v1/documents/nonexistent",
        json={"title": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client):
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv"},
    )
    doc_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client):
    resp = await client.delete("/api/v1/documents/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compile_document_no_tectonic(client):
    """Compile should return 503 when tectonic is not installed."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "\\documentclass{article}\\begin{document}Hi\\end{document}"},
    )
    doc_id = create_resp.json()["id"]
    with patch("jam.server.shutil.which", return_value=None):
        resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert resp.status_code == 503
    assert "tectonic" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_compile_document_empty_source(client):
    """Compile should return 422 when LaTeX source is empty."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": ""},
    )
    doc_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_compile_document_success(client):
    """Compile should return PDF bytes without creating a version."""
    import asyncio

    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "\\documentclass{article}\\begin{document}Hi\\end{document}"},
    )
    doc_id = create_resp.json()["id"]

    fake_pdf = b"%PDF-1.4 fake pdf content"

    async def fake_subprocess(*args, **kwargs):
        # Write a fake PDF file
        cwd = kwargs.get("cwd", ".")
        import os
        pdf_path = os.path.join(cwd, "document.pdf")
        with open(pdf_path, "wb") as f:
            f.write(fake_pdf)
        proc = MagicMock()
        proc.returncode = 0

        async def communicate():
            return b"", b""
        proc.communicate = communicate
        return proc

    with patch("jam.server.shutil.which", return_value="/usr/bin/tectonic"), \
         patch("jam.server.asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch("jam.server._inject_pdf_metadata", side_effect=lambda pdf, **kw: pdf):
        resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf

    # Compile creates a version snapshot
    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    assert ver_resp.status_code == 200
    versions = ver_resp.json()
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_compile_document_failure(client):
    """Compile should return 422 when tectonic fails."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "bad latex"},
    )
    doc_id = create_resp.json()["id"]

    async def fake_subprocess(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 1
        async def communicate():
            return b"", b"error: undefined control sequence"
        proc.communicate = communicate
        return proc

    with patch("jam.server.shutil.which", return_value="/usr/bin/tectonic"), \
         patch("jam.server.asyncio.create_subprocess_exec", side_effect=fake_subprocess):
        resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert resp.status_code == 422
    assert "compilation failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_versions(client):
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "src"},
    )
    doc_id = create_resp.json()["id"]
    # No versions yet
    resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_versions_not_found(client):
    resp = await client.get("/api/v1/documents/nonexistent/versions")
    assert resp.status_code == 404


# ── Compile version endpoint tests ──────────────────────────────────────────


async def _create_version_via_compile(client, doc_id, db_path=None):
    """Helper: create a version snapshot via API GET + DB, then compile to populate PDF cache."""
    fake_pdf = b"%PDF-1.4 fake pdf content"

    # Fetch doc via API (uses the isolated DB) and create version directly
    doc_resp = await client.get(f"/api/v1/documents/{doc_id}")
    doc = doc_resp.json()
    kwargs = {"document_id": doc_id, "latex_source": doc["latex_source"],
              "prompt_text": doc.get("prompt_text", "")}
    if db_path:
        kwargs["db_path"] = db_path
    _db_module.create_version(**kwargs)

    async def fake_subprocess(*args, **kwargs):
        import os
        cwd = kwargs.get("cwd", ".")
        with open(os.path.join(cwd, "document.pdf"), "wb") as f:
            f.write(fake_pdf)
        proc = MagicMock()
        proc.returncode = 0
        async def communicate():
            return b"", b""
        proc.communicate = communicate
        return proc

    with patch("jam.server.shutil.which", return_value="/usr/bin/tectonic"), \
         patch("jam.server.asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch("jam.server._inject_pdf_metadata", side_effect=lambda pdf, **kw: pdf):
        resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert resp.status_code == 200
    return fake_pdf


@pytest.mark.asyncio
async def test_compile_version_not_found(client):
    resp = await client.post("/api/v1/documents/versions/nonexistent/compile")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compile_version_empty_source(client, isolated_db):
    """Version with empty LaTeX should return 422."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "some latex"},
    )
    doc_id = create_resp.json()["id"]

    # Compile to create a version
    await _create_version_via_compile(client, doc_id, db_path=isolated_db)

    # Manually create a version with empty source via the DB (using test db_path)
    from jam.db import create_version as db_create_version_fn
    ver = db_create_version_fn(document_id=doc_id, latex_source="", prompt_text="", db_path=isolated_db)

    resp = await client.post(f"/api/v1/documents/versions/{ver['id']}/compile")
    assert resp.status_code == 422
    assert "empty" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_compile_version_no_tectonic(client, isolated_db):
    """Should return 503 when tectonic is not installed."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "\\documentclass{article}\\begin{document}Hi\\end{document}"},
    )
    doc_id = create_resp.json()["id"]
    await _create_version_via_compile(client, doc_id, db_path=isolated_db)

    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    version_id = ver_resp.json()[0]["id"]

    with patch("jam.server.shutil.which", return_value=None):
        resp = await client.post(f"/api/v1/documents/versions/{version_id}/compile")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_compile_version_success(client, isolated_db):
    """Compile a version should return PDF bytes."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "\\documentclass{article}\\begin{document}Hi\\end{document}"},
    )
    doc_id = create_resp.json()["id"]
    fake_pdf = await _create_version_via_compile(client, doc_id, db_path=isolated_db)

    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    version_id = ver_resp.json()[0]["id"]

    async def fake_subprocess(*args, **kwargs):
        import os
        cwd = kwargs.get("cwd", ".")
        with open(os.path.join(cwd, "document.pdf"), "wb") as f:
            f.write(fake_pdf)
        proc = MagicMock()
        proc.returncode = 0
        async def communicate():
            return b"", b""
        proc.communicate = communicate
        return proc

    with patch("jam.server.shutil.which", return_value="/usr/bin/tectonic"), \
         patch("jam.server.asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch("jam.server._inject_pdf_metadata", side_effect=lambda pdf, **kw: pdf):
        resp = await client.post(f"/api/v1/documents/versions/{version_id}/compile")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf


@pytest.mark.asyncio
async def test_compile_version_failure(client, isolated_db):
    """Compile version should return 422 when tectonic fails."""
    app_id = await _create_test_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "latex_source": "bad latex"},
    )
    doc_id = create_resp.json()["id"]
    await _create_version_via_compile(client, doc_id, db_path=isolated_db)

    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    version_id = ver_resp.json()[0]["id"]

    async def fake_subprocess(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 1
        async def communicate():
            return b"", b"error: undefined control sequence"
        proc.communicate = communicate
        return proc

    with patch("jam.server.shutil.which", return_value="/usr/bin/tectonic"), \
         patch("jam.server.asyncio.create_subprocess_exec", side_effect=fake_subprocess):
        resp = await client.post(f"/api/v1/documents/versions/{version_id}/compile")
    assert resp.status_code == 422
    assert "compilation failed" in resp.json()["detail"]


# ── Default templates endpoint tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_default_templates(client):
    """GET /templates/defaults should return both built-in templates."""
    resp = await client.get("/api/v1/templates/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "cv" in data
    assert "cover_letter" in data
    assert "\\documentclass" in data["cv"]
    assert "\\documentclass" in data["cover_letter"]


# ── PDF cache endpoint tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_document_pdf_not_found(client):
    """GET /documents/{doc_id}/pdf returns 404 when nothing compiled."""
    response = await client.get("/api/v1/documents/nonexistent-doc/pdf")
    assert response.status_code == 404
    assert "No compiled PDF available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_pdf_after_compile(client):
    """GET /documents/{doc_id}/pdf returns cached PDF after compile."""
    from jam import server
    
    doc_id = "test-doc-123"
    fake_pdf = b"PDF mock content"
    server._pdf_cache[doc_id] = fake_pdf
    
    response = await client.get(f"/api/v1/documents/{doc_id}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == fake_pdf


def test_html_page_instruction_regex_patterns():
    """JS regex patterns for \\section and \\paragraph must be correctly escaped.

    Catches Python-escaping mistakes that would produce the wrong regex in the
    browser (e.g. \\\\section vs \\section vs section).
    """
    # CV: emits \\section in JS source → regex matches literal \section in LaTeX
    assert r'\\section\{' in HTML_PAGE, (
        r"CV regex pattern '\\section\{' not found in HTML_PAGE — "
        "check Python escaping of the \\section regex in _buildInstructionsFromLatex"
    )
    # Cover letter primary: <<NAME-PARAGRAPH: pattern for template markers
    assert "<<([A-Z][A-Z-]*)-PARAGRAPH:" in HTML_PAGE, (
        "Cover letter primary regex '<<([A-Z][A-Z-]*)-PARAGRAPH:' not found in HTML_PAGE — "
        "check _buildInstructionsFromLatex cover letter section detection"
    )
    # Cover letter fallback: \\paragraph for generated documents
    assert r'\\paragraph\{' in HTML_PAGE, (
        r"Cover letter fallback regex '\\paragraph\{' not found in HTML_PAGE — "
        "check Python escaping of the \\paragraph regex in _buildInstructionsFromLatex"
    )


def test_html_page_no_multiline_js_regex_literals():
    """
    Detect JS regex literals that contain actual newline characters.

    This class of bug arises when Python's \\n (or \\n\\n etc.) inside a
    triple-quoted HTML_PAGE string becomes a real newline embedded in a JS
    regex literal, causing browsers to throw:
        Uncaught SyntaxError: Invalid regular expression: missing /

    The test scans for the pattern  = /…<newline>  or  fn(/…<newline>
    which are the common contexts where an unclosed regex literal would appear.
    """
    bad = re.findall(
        r'(?:\.split|\.match|\.replace|\.search|\.test|[=(,])\s*/(?!/)[^\n/]*\n',
        HTML_PAGE,
    )
    assert not bad, (
        "JS regex literal(s) in HTML_PAGE contain actual newline characters "
        "(browser syntax error 'missing /').  Escape \\n as \\\\n in the "
        f"Python source string.\nOffending snippets: {bad}"
    )


# ── Generate endpoint ────────────────────────────────────────────────────────

def _make_app_and_doc(isolated_db):
    """Helper: create a test application with job description and a CV document."""
    from jam.db import create_application, create_document
    from datetime import datetime, timezone
    from uuid import uuid4

    now = datetime.now(timezone.utc).isoformat()
    app_id = str(uuid4())
    create_application(
        app_id,
        "Acme",
        "Engineer",
        "not_applied_yet",
        None,
        None,
        "2026-01-01",
        now,
        now,
        full_text="Python engineer position requiring FastAPI and PostgreSQL experience.",
        db_path=isolated_db,
    )
    doc = create_document(
        application_id=app_id,
        doc_type="cv",
        title="CV",
        latex_source=r"\documentclass{article}\begin{document}<<NAME: Test>>\end{document}",
        db_path=isolated_db,
    )
    return app_id, doc["id"]


@pytest.mark.asyncio
async def test_generate_404_no_doc(client):
    resp = await client.post("/api/v1/documents/nonexistent-doc/generate", json={"is_first_generation": True})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_422_no_job_description(client, isolated_db):
    from jam.db import create_application, create_document
    from datetime import datetime, timezone
    from uuid import uuid4

    now = datetime.now(timezone.utc).isoformat()
    app_id = str(uuid4())
    create_application(
        app_id,
        "Acme",
        "Eng",
        "not_applied_yet",
        None,
        None,
        "2026-01-01",
        now,
        now,
        full_text=None,
        description=None,
        db_path=isolated_db,
    )
    doc = create_document(
        application_id=app_id,
        doc_type="cv",
        title="CV",
        latex_source=r"\documentclass{article}\begin{document}\end{document}",
        db_path=isolated_db,
    )
    resp = await client.post(
        f"/api/v1/documents/{doc['id']}/generate",
        json={"is_first_generation": True},
    )
    assert resp.status_code == 422
    assert "job description" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_streams_sse(client, isolated_db):
    """SSE stream returns progress events and a final done event."""
    _app_id, doc_id = _make_app_and_doc(isolated_db)

    # Simulate graph yielding two node chunks then a final state
    async def _fake_astream(state, stream_mode=None):
        yield {
            "progress_events": [{"node": "retrieve_kb_docs", "status": "done", "detail": "0 KB docs retrieved"}],
            "kb_docs": [],
            "inline_comments": [],
            "locked_sections": [],
        }
        yield {
            "progress_events": [
                {"node": "retrieve_kb_docs", "status": "done", "detail": "0 KB docs retrieved"},
                {"node": "generate_or_revise", "status": "done"},
            ],
            "current_latex": r"\documentclass{article}\begin{document}Generated.\end{document}",
            "final_latex": r"\documentclass{article}\begin{document}Generated.\end{document}",
            "final_pdf": b"%PDF-1.4",
            "fit_feedback": "Good fit.",
            "quality_feedback": "Clean writing.",
            "page_count": 1,
        }

    with patch("jam.generation.generation_graph") as mock_graph, \
         patch("jam.server._inject_pdf_metadata", side_effect=lambda pdf, **kw: pdf):
        mock_graph.astream = _fake_astream
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/generate",
            json={"is_first_generation": True},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    lines = [l for l in resp.text.splitlines() if l.startswith("data: ")]
    assert len(lines) >= 2

    events = [json.loads(l[6:]) for l in lines]
    node_names = [e["node"] for e in events]
    assert "retrieve_kb_docs" in node_names
    # Final event should be "done"
    assert events[-1]["node"] == "done"
    assert events[-1]["fit_feedback"] == "Good fit."


@pytest.mark.asyncio
async def test_generate_updates_db_on_success(client, isolated_db):
    """After successful generation the document's latex_source is updated in DB."""
    _app_id, doc_id = _make_app_and_doc(isolated_db)
    new_latex = r"\documentclass{article}\begin{document}Updated content.\end{document}"

    async def _fake_astream(state, stream_mode=None):
        yield {
            "progress_events": [{"node": "finalize", "status": "done"}],
            "final_latex": new_latex,
            "final_pdf": b"%PDF-1.4",
            "fit_feedback": "",
            "quality_feedback": "",
            "page_count": 1,
            "current_latex": new_latex,
        }

    with patch("jam.generation.generation_graph") as mock_graph, \
         patch("jam.server._inject_pdf_metadata", side_effect=lambda pdf, **kw: pdf):
        mock_graph.astream = _fake_astream
        await client.post(
            f"/api/v1/documents/{doc_id}/generate",
            json={"is_first_generation": True},
        )

    # Verify DB was updated
    from jam.db import get_document
    updated = get_document(doc_id, db_path=isolated_db)
    assert updated["latex_source"] == new_latex


@pytest.mark.asyncio
async def test_critique_only_returns_feedback_without_modifying_doc(client, isolated_db):
    """critique_only=True streams feedback but does not update the DB document."""
    _app_id, doc_id = _make_app_and_doc(isolated_db)

    original_latex = r"\documentclass{article}\begin{document}Original.\end{document}"
    from jam.db import update_document
    update_document(doc_id, {"latex_source": original_latex}, db_path=isolated_db)

    async def _fake_astream(state, stream_mode=None):
        yield {
            "progress_events": [{"node": "analyze_fit", "status": "done"}],
            "fit_feedback": "Fit feedback here.",
            "quality_feedback": "Quality feedback here.",
            "final_latex": original_latex,
            "final_pdf": None,
            "page_count": 0,
        }

    with patch("jam.generation.critique_graph") as mock_graph:
        mock_graph.astream = _fake_astream
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/generate",
            json={"critique_only": True},
        )

    assert resp.status_code == 200
    lines = [l for l in resp.text.splitlines() if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in lines]
    done = events[-1]
    assert done["node"] == "done"
    assert done["fit_feedback"] == "Fit feedback here."
    assert done["quality_feedback"] == "Quality feedback here."

    # DB document must NOT have been updated
    from jam.db import get_document
    doc = get_document(doc_id, db_path=isolated_db)
    assert doc["latex_source"] == original_latex


@pytest.mark.asyncio
async def test_critique_only_does_not_create_version(client, isolated_db):
    """critique_only=True must not create a new version entry."""
    from jam.db import list_versions
    _app_id, doc_id = _make_app_and_doc(isolated_db)

    async def _fake_astream(state, stream_mode=None):
        yield {
            "progress_events": [{"node": "finalize", "status": "done"}],
            "fit_feedback": "ok",
            "quality_feedback": "ok",
            "final_latex": r"\documentclass{article}\begin{document}X.\end{document}",
            "final_pdf": None,
            "page_count": 0,
        }

    versions_before = list_versions(doc_id, db_path=isolated_db)

    with patch("jam.generation.critique_graph") as mock_graph:
        mock_graph.astream = _fake_astream
        await client.post(
            f"/api/v1/documents/{doc_id}/generate",
            json={"critique_only": True},
        )

    versions_after = list_versions(doc_id, db_path=isolated_db)
    assert len(versions_after) == len(versions_before)


# ── Extra questions endpoint tests ───────────────────────────────────────────

async def _make_app(client):
    resp = await client.post(
        "/api/v1/applications",
        json={"company": "Acme", "position": "Dev"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_questions_empty(client):
    app_id = await _make_app(client)
    resp = await client.get(f"/api/v1/applications/{app_id}/questions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_question(client):
    app_id = await _make_app(client)
    resp = await client.post(
        f"/api/v1/applications/{app_id}/questions",
        json={"question": "Why us?", "answer": "Great fit", "word_cap": 150},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["question"] == "Why us?"
    assert data["answer"] == "Great fit"
    assert data["word_cap"] == 150
    assert data["application_id"] == app_id


@pytest.mark.asyncio
async def test_update_question(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/questions",
        json={"question": "Old"},
    )
    q_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/questions/{q_id}",
        json={"question": "New", "word_cap": 200},
    )
    assert resp.status_code == 200
    assert resp.json()["question"] == "New"
    assert resp.json()["word_cap"] == 200


@pytest.mark.asyncio
async def test_delete_question(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/questions",
        json={"question": "Q"},
    )
    q_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/questions/{q_id}")
    assert resp.status_code == 204

    # Verify gone
    list_resp = await client.get(f"/api/v1/applications/{app_id}/questions")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_question_not_found(client):
    resp = await client.put(
        "/api/v1/questions/nonexistent",
        json={"question": "Q"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_question_app_not_found(client):
    resp = await client.get("/api/v1/applications/nonexistent/questions")
    assert resp.status_code == 404

    resp = await client.post(
        "/api/v1/applications/nonexistent/questions",
        json={"question": "Q"},
    )
    assert resp.status_code == 404


# ── Interview rounds ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_interviews_empty(client):
    app_id = await _make_app(client)
    resp = await client.get(f"/api/v1/applications/{app_id}/interviews")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_interview(client):
    app_id = await _make_app(client)
    resp = await client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json={"round_type": "technical", "round_number": 1, "status": "scheduled"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["round_type"] == "technical"
    assert data["round_number"] == 1
    assert data["status"] == "scheduled"
    assert data["application_id"] == app_id


@pytest.mark.asyncio
async def test_update_interview(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json={"round_type": "hr"},
    )
    iv_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/interviews/{iv_id}",
        json={"status": "completed", "went_well": "Good rapport"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["went_well"] == "Good rapport"


@pytest.mark.asyncio
async def test_delete_interview(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json={"round_type": "technical"},
    )
    iv_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/interviews/{iv_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/applications/{app_id}/interviews")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_interview_not_found(client):
    resp = await client.put(
        "/api/v1/interviews/nonexistent",
        json={"status": "completed"},
    )
    assert resp.status_code == 404

    resp = await client.delete("/api/v1/interviews/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_interview_app_not_found(client):
    resp = await client.get("/api/v1/applications/nonexistent/interviews")
    assert resp.status_code == 404

    resp = await client.post(
        "/api/v1/applications/nonexistent/interviews",
        json={"round_type": "hr"},
    )
    assert resp.status_code == 404


# ── Offers ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_offers_empty(client):
    app_id = await _make_app(client)
    resp = await client.get(f"/api/v1/applications/{app_id}/offers")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_offer(client):
    app_id = await _make_app(client)
    resp = await client.post(
        f"/api/v1/applications/{app_id}/offers",
        json={"status": "received", "base_salary": 75000.0, "currency": "EUR"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "received"
    assert data["base_salary"] == 75000.0
    assert data["currency"] == "EUR"
    assert data["application_id"] == app_id


@pytest.mark.asyncio
async def test_update_offer(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/offers",
        json={"status": "pending"},
    )
    offer_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/v1/offers/{offer_id}",
        json={"status": "accepted", "notes": "Signed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["notes"] == "Signed"


@pytest.mark.asyncio
async def test_delete_offer(client):
    app_id = await _make_app(client)
    create_resp = await client.post(
        f"/api/v1/applications/{app_id}/offers",
        json={"status": "pending"},
    )
    offer_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/offers/{offer_id}")
    assert resp.status_code == 204

    list_resp = await client.get(f"/api/v1/applications/{app_id}/offers")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_offer_not_found(client):
    resp = await client.put(
        "/api/v1/offers/nonexistent",
        json={"status": "accepted"},
    )
    assert resp.status_code == 404

    resp = await client.delete("/api/v1/offers/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_offer_app_not_found(client):
    resp = await client.get("/api/v1/applications/nonexistent/offers")
    assert resp.status_code == 404

    resp = await client.post(
        "/api/v1/applications/nonexistent/offers",
        json={"status": "pending"},
    )
    assert resp.status_code == 404


# ── Personal info settings ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_personal_info_settings_roundtrip(client):
    """POST personal info fields to /settings, then GET and verify they appear."""
    resp = await client.post(
        "/api/v1/settings",
        json={
            "personal_full_name": "Jane Doe",
            "personal_email": "jane@example.com",
            "personal_phone": "+49 170 123 4567",
            "personal_website": "https://janedoe.dev",
            "personal_address": "Berlin, Germany",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    get_resp = await client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["personal_full_name"] == "Jane Doe"
    assert data["personal_email"] == "jane@example.com"
    assert data["personal_phone"] == "+49 170 123 4567"
    assert data["personal_website"] == "https://janedoe.dev"
    assert data["personal_address"] == "Berlin, Germany"


@pytest.mark.asyncio
async def test_personal_photo_roundtrip(client):
    """POST personal_photo data-URI to /settings, then GET and verify it appears unmasked."""
    photo_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    resp = await client.post(
        "/api/v1/settings",
        json={"personal_photo": photo_uri},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "personal_photo" in resp.json()["saved"]

    get_resp = await client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["personal_photo"] == photo_uri


@pytest.mark.asyncio
async def test_personal_signature_roundtrip(client):
    """POST personal_signature data-URI to /settings, then GET and verify it appears unmasked."""
    sig_uri = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAARC=="
    resp = await client.post(
        "/api/v1/settings",
        json={"personal_signature": sig_uri},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "personal_signature" in resp.json()["saved"]

    get_resp = await client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["personal_signature"] == sig_uri


@pytest.mark.asyncio
async def test_personal_image_fields_not_masked(client, isolated_db):
    """personal_photo and personal_signature should appear as plain values, not masked."""
    import jam.db as _db_module_local
    photo_uri = "data:image/png;base64,abc123"
    sig_uri = "data:image/png;base64,def456"
    _db_module_local.set_setting("personal_photo", photo_uri, db_path=isolated_db)
    _db_module_local.set_setting("personal_signature", sig_uri, db_path=isolated_db)

    get_resp = await client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["personal_photo"] == photo_uri
    assert data["personal_signature"] == sig_uri
    # Must not appear as masked flags
    assert "personal_photo_set" not in data
    assert "personal_signature_set" not in data


# ── PDF metadata helpers ──────────────────────────────────────────────────────

def test_inject_pdf_metadata():
    """_inject_pdf_metadata sets title and author."""
    from jam.server import _inject_pdf_metadata
    import fitz

    doc = fitz.open()
    doc.new_page()
    original = doc.tobytes()
    doc.close()

    result = _inject_pdf_metadata(original, title="Software Engineer", author="Jane Doe")

    doc2 = fitz.open(stream=result, filetype="pdf")
    md = doc2.metadata
    assert md["title"] == "Software Engineer"
    assert md["author"] == "Jane Doe"
    doc2.close()


def test_build_pdf_metadata():
    """_build_pdf_metadata assembles title and author from settings."""
    from jam.server import _build_pdf_metadata

    with patch("jam.server.get_all_settings", return_value={"personal_full_name": "Jane Doe"}):
        meta = _build_pdf_metadata(position="Backend Engineer")

    assert meta == {"title": "Backend Engineer", "author": "Jane Doe"}


# ── Default prompts endpoint tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_default_prompts_returns_all_keys(client):
    """GET /prompts/defaults should return all 6 prompt keys."""
    fake_prompts = {
        "PROMPT_GENERATE_FIRST": "gen-first",
        "PROMPT_GENERATE_REVISE": "gen-revise",
        "PROMPT_ANALYZE_FIT": "analyze-fit",
        "PROMPT_ANALYZE_QUALITY": "analyze-quality",
        "PROMPT_APPLY_SUGGESTIONS": "apply-suggestions",
        "PROMPT_REDUCE_SIZE": "reduce-size",
    }
    with patch.dict("jam.generation.__dict__", fake_prompts):
        resp = await client.get("/api/v1/prompts/defaults")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "prompt_generate_first",
        "prompt_generate_revise",
        "prompt_analyze_fit",
        "prompt_analyze_quality",
        "prompt_apply_suggestions",
        "prompt_reduce_size",
    }
    assert expected_keys == set(data.keys())
    # Values should be non-empty strings (actual generation constants)
    for key in expected_keys:
        assert isinstance(data[key], str)
        assert len(data[key]) > 0


@pytest.mark.asyncio
async def test_save_prompt_setting_via_post_settings(client):
    """POST /settings with a prompt field should persist and return it in saved."""
    custom_prompt = "You are a CV writer. Write a great CV."
    resp = await client.post(
        "/api/v1/settings",
        json={"prompt_generate_first": custom_prompt},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "prompt_generate_first" in data["saved"]


@pytest.mark.asyncio
async def test_get_settings_returns_prompt_fields(client, isolated_db):
    """GET /settings should include prompt fields when stored."""
    custom_prompt = "Custom generate prompt."
    _db_module.set_setting("prompt_generate_first", custom_prompt, db_path=isolated_db)
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt_generate_first"] == custom_prompt


# --- Per-step model settings ---

_MOCK_CATALOG_WITH_GPT4O = {
    "providers": [
        {
            "id": "openai",
            "label": "OpenAI",
            "type": "llm",
            "llm_models": [
                {"id": "openai:gpt-4o", "model_id": "gpt-4o", "label": "GPT-4o",
                 "context_window": 128000, "prompt_cost": None, "completion_cost": None},
            ],
            "fields": [],
        }
    ]
}


@pytest.mark.asyncio
async def test_save_step_model_valid(client):
    """POST /settings with a valid step model ID should succeed and save the key."""
    with patch("jam.server.get_catalog", return_value=_MOCK_CATALOG_WITH_GPT4O):
        with patch("jam.server.set_settings_batch") as mock_batch:
            resp = await client.post(
                "/api/v1/settings",
                json={"step_model_analyze_fit": "openai:gpt-4o"},
            )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_batch.assert_called_once_with({"step_model_analyze_fit": "openai:gpt-4o"})


@pytest.mark.asyncio
async def test_save_step_model_invalid(client):
    """POST /settings with an unknown step model ID should return 422."""
    with patch("jam.server.get_catalog", return_value=_MOCK_CATALOG_WITH_GPT4O):
        resp = await client.post(
            "/api/v1/settings",
            json={"step_model_analyze_fit": "nonexistent:model"},
        )
    assert resp.status_code == 422
    assert "nonexistent:model" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_save_step_model_empty_clears(client):
    """POST /settings with an empty string step model should succeed (clears override)."""
    with patch("jam.server.set_settings_batch") as mock_batch:
        resp = await client.post(
            "/api/v1/settings",
            json={"step_model_analyze_fit": ""},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    mock_batch.assert_called_once_with({"step_model_analyze_fit": ""})


@pytest.mark.asyncio
async def test_get_settings_returns_step_models(client, isolated_db):
    """GET /settings should include step_model fields when stored."""
    _db_module.set_setting("step_model_analyze_fit", "openai:gpt-4o", db_path=isolated_db)
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["step_model_analyze_fit"] == "openai:gpt-4o"
