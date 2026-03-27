import re
import shutil
import subprocess

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from jam.server import app
from jam import db as _db_module


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Point every db call to a fresh SQLite db for each test."""
    db_path = tmp_path / "test.db"
    _db_module.init_db(db_path)

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
    }

    patchers = []
    for server_name, db_name in alias_to_db.items():
        original = getattr(_db_module, db_name)

        def _make_side_effect(fn, p):
            return lambda *a, **kw: fn(*a, db_path=p, **kw)

        patchers.append(
            patch(
                f"jam.server.{server_name}",
                side_effect=_make_side_effect(original, db_path),
            )
        )

    for p in patchers:
        p.start()
    yield
    for p in patchers:
        p.stop()


@pytest.mark.asyncio
async def test_full_page_load(client):
    """Integration: full page loads with all expected sections."""
    resp = await client.get("/api/v1/")
    assert resp.status_code == 200
    body = resp.text
    # Check title and header
    assert "Job Application Manager" in body
    # Check JS is present
    assert "apiFetch" in body


@pytest.mark.asyncio
async def test_inline_js_has_no_syntax_errors(client):
    """Integration: all inline <script> blocks must be valid JavaScript."""
    resp = await client.get("/api/v1/")
    assert resp.status_code == 200
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", resp.text, re.DOTALL)
    assert scripts, "Expected at least one <script> block"
    for i, script in enumerate(scripts):
        if not script.strip():
            continue
        result = subprocess.run(
            ["node", "--check"],
            input=script,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"JS syntax error in <script> block {i}:\n{result.stderr}"
        )


@pytest.mark.asyncio
async def test_create_and_list_applications_flow(client):
    """Integration: create applications and list them."""
    # Create first application
    create1 = await client.post(
        "/api/v1/applications",
        json={
            "company": "Google",
            "position": "Software Engineer",
            "status": "applied",
            "url": "https://google.com/jobs/123",
            "notes": "Great company",
        },
    )
    assert create1.status_code == 201
    app1 = create1.json()
    
    # Create second application
    create2 = await client.post(
        "/api/v1/applications",
        json={
            "company": "Microsoft",
            "position": "Product Manager",
            "status": "screening",
        },
    )
    assert create2.status_code == 201
    app2 = create2.json()
    
    # List all applications
    list_resp = await client.get("/api/v1/applications")
    assert list_resp.status_code == 200
    apps = list_resp.json()
    assert len(apps) == 2
    
    # Verify both apps are in the list
    ids = {app["id"] for app in apps}
    assert app1["id"] in ids
    assert app2["id"] in ids


@pytest.mark.asyncio
async def test_crud_flow(client):
    """Integration: full CRUD flow for an application."""
    # Create
    create_resp = await client.post(
        "/api/v1/applications",
        json={
            "company": "Apple",
            "position": "Engineer",
            "status": "applied",
        },
    )
    assert create_resp.status_code == 201
    app_id = create_resp.json()["id"]
    
    # Read
    get_resp = await client.get(f"/api/v1/applications/{app_id}")
    assert get_resp.status_code == 200
    app_data = get_resp.json()
    assert app_data["company"] == "Apple"
    
    # Update
    update_resp = await client.put(
        f"/api/v1/applications/{app_id}",
        json={
            "status": "interviewing",
            "notes": "First round passed",
        },
    )
    assert update_resp.status_code == 200
    updated_app = update_resp.json()
    assert updated_app["status"] == "interviewing"
    assert updated_app["notes"] == "First round passed"
    
    # Delete
    delete_resp = await client.delete(f"/api/v1/applications/{app_id}")
    assert delete_resp.status_code == 204
    
    # Verify it's gone
    get_resp = await client.get(f"/api/v1/applications/{app_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_catalog_returns_providers(client):
    """Integration: GET /catalog returns a non-empty providers list."""
    resp = await client.get("/api/v1/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    providers = data["providers"]
    assert len(providers) > 0
    ids = {p["id"] for p in providers}
    assert "openai" in ids
    assert "anthropic" in ids


@pytest.mark.asyncio
async def test_import_from_url_integration(client):
    """Integration: POST /applications/from-url creates an application with mocked externals."""
    extracted = {
        "company": "Integration Corp",
        "position": "Site Reliability Engineer",
        "location": "New York",
    }
    with patch("jam.server._fetch_page_text", return_value=("x" * 200, "html")), \
         patch("jam.server.extract_job_info", return_value=extracted), \
         patch("jam.server.ingest_url", return_value=None):
        resp = await client.post(
            "/api/v1/applications/from-url",
            json={"url": "https://integration.example.com/jobs/sre"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["application"]["company"] == "Integration Corp"
    assert data["application"]["position"] == "Site Reliability Engineer"
    assert data["application"]["url"] == "https://integration.example.com/jobs/sre"
    assert data["kb_ingested"] is True
    assert data["extraction"]["location"] == "New York"

    # Application is also retrievable via GET
    app_id = data["application"]["id"]
    get_resp = await client.get(f"/api/v1/applications/{app_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["company"] == "Integration Corp"


@pytest.mark.asyncio
async def test_settings_roundtrip(client):
    """Integration: save settings then retrieve them masked."""
    with patch("jam.server.set_setting") as mock_set, \
         patch("jam.server.get_all_settings", return_value={"llm_provider": "openai", "openai_api_key": "sk-test"}):
        save_resp = await client.post(
            "/api/v1/settings",
            json={"llm_provider": "openai"},
        )
        assert save_resp.status_code == 200
        assert save_resp.json()["ok"] is True

        get_resp = await client.get("/api/v1/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["openai_api_key_set"] is True
        assert data["llm_provider"] == "openai"
        assert "openai_api_key" not in data


# ── PDF compilation integration tests ────────────────────────────────────────

_requires_tectonic = pytest.mark.skipif(
    not shutil.which("tectonic"),
    reason="tectonic is not installed",
)

MINIMAL_LATEX = r"""\documentclass{article}
\begin{document}
Hello, world!
\end{document}
"""


@_requires_tectonic
@pytest.mark.asyncio
async def test_compile_document_produces_valid_pdf(client):
    """Integration: create an app + document with LaTeX, compile it, verify PDF output."""
    # Create an application
    app_resp = await client.post(
        "/api/v1/applications",
        json={"company": "PDFCorp", "position": "Engineer", "status": "applied"},
    )
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # Create a document with valid LaTeX
    doc_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={
            "doc_type": "cv",
            "title": "Test CV",
            "latex_source": MINIMAL_LATEX,
        },
    )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    # Compile
    compile_resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert compile_resp.status_code == 200
    assert compile_resp.headers["content-type"] == "application/pdf"

    pdf_bytes = compile_resp.content
    # PDF files start with %PDF
    assert pdf_bytes[:5] == b"%PDF-"
    # Sanity: non-trivial size
    assert len(pdf_bytes) > 500


@_requires_tectonic
@pytest.mark.asyncio
async def test_compile_creates_version_snapshot(client):
    """Integration: compiling a document creates a version snapshot."""
    app_resp = await client.post(
        "/api/v1/applications",
        json={"company": "VerCorp", "position": "Dev", "status": "applied"},
    )
    app_id = app_resp.json()["id"]

    doc_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cover_letter", "title": "Test CL", "latex_source": MINIMAL_LATEX},
    )
    doc_id = doc_resp.json()["id"]

    # No versions before compilation
    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    assert ver_resp.status_code == 200
    assert len(ver_resp.json()) == 0

    # Compile
    compile_resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert compile_resp.status_code == 200

    # Now there should be exactly one version
    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    assert ver_resp.status_code == 200
    versions = ver_resp.json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["latex_source"] == MINIMAL_LATEX


@_requires_tectonic
@pytest.mark.asyncio
async def test_compile_invalid_latex_returns_422(client):
    """Integration: invalid LaTeX source returns a 422 with error details."""
    app_resp = await client.post(
        "/api/v1/applications",
        json={"company": "BadTex", "position": "Dev", "status": "applied"},
    )
    app_id = app_resp.json()["id"]

    doc_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "Broken", "latex_source": r"\invalid{broken}"},
    )
    doc_id = doc_resp.json()["id"]

    compile_resp = await client.post(f"/api/v1/documents/{doc_id}/compile")
    assert compile_resp.status_code == 422
    assert "compilation failed" in compile_resp.json()["detail"].lower()


@_requires_tectonic
@pytest.mark.asyncio
async def test_compile_version_produces_valid_pdf(client):
    """Integration: compile from a version snapshot produces a valid PDF."""
    app_resp = await client.post(
        "/api/v1/applications",
        json={"company": "VerPDF", "position": "Dev", "status": "applied"},
    )
    app_id = app_resp.json()["id"]

    doc_resp = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        json={"doc_type": "cv", "title": "CV", "latex_source": MINIMAL_LATEX},
    )
    doc_id = doc_resp.json()["id"]

    # First compile to create a version
    await client.post(f"/api/v1/documents/{doc_id}/compile")

    # Get version id
    ver_resp = await client.get(f"/api/v1/documents/{doc_id}/versions")
    version_id = ver_resp.json()[0]["id"]

    # Compile from version
    compile_resp = await client.post(f"/api/v1/documents/versions/{version_id}/compile")
    assert compile_resp.status_code == 200
    assert compile_resp.headers["content-type"] == "application/pdf"
    assert compile_resp.content[:5] == b"%PDF-"
