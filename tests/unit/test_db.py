import tempfile
from pathlib import Path

from jam.db import (
    init_db, get_setting, set_setting, delete_setting, get_all_settings,
    get_catalog, create_application, get_application, list_applications,
    update_application, delete_application, set_application_meta,
    get_application_meta, delete_application_meta,
    create_document, get_document, list_documents, update_document,
    delete_document, create_version, list_versions, get_version,
)


def _tmp_db():
    return Path(tempfile.mktemp(suffix=".db"))


def test_init_db_creates_tables():
    db = _tmp_db()
    init_db(db)
    # Should be idempotent
    init_db(db)


def test_set_and_get_setting():
    db = _tmp_db()
    init_db(db)
    assert get_setting("foo", db) is None
    set_setting("foo", "bar", db)
    assert get_setting("foo", db) == "bar"


def test_set_setting_upsert():
    db = _tmp_db()
    init_db(db)
    set_setting("key", "v1", db)
    set_setting("key", "v2", db)
    assert get_setting("key", db) == "v2"


def test_delete_setting():
    db = _tmp_db()
    init_db(db)
    set_setting("key", "val", db)
    delete_setting("key", db)
    assert get_setting("key", db) is None


def test_get_all_settings():
    db = _tmp_db()
    init_db(db)
    set_setting("a", "1", db)
    set_setting("b", "2", db)
    result = get_all_settings(db)
    assert result == {"a": "1", "b": "2"}


def test_catalog_has_providers():
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    assert "providers" in catalog
    ids = [p["id"] for p in catalog["providers"]]
    assert "openai" in ids
    assert "anthropic" in ids
    assert "groq" in ids
    assert "ollama" in ids


def test_catalog_provider_has_models():
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    openai = next(p for p in catalog["providers"] if p["id"] == "openai")
    assert len(openai["llm_models"]) > 0
    model_ids = [m["model_id"] for m in openai["llm_models"]]
    assert "gpt-4o" in model_ids


def test_catalog_provider_has_fields():
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    openai = next(p for p in catalog["providers"] if p["id"] == "openai")
    assert len(openai["fields"]) > 0
    keys = [f["key"] for f in openai["fields"]]
    assert "openai_api_key" in keys


# ── Application CRUD ─────────────────────────────────────────────────────────

_APP_KWARGS = dict(
    id="aaaa-bbbb",
    company="Acme",
    position="Engineer",
    status="applied",
    url="https://example.com/job",
    notes="Great role",
    applied_date="2026-03-22",
    created_at="2026-03-22T10:00:00+00:00",
    updated_at="2026-03-22T10:00:00+00:00",
)


def test_create_application():
    db = _tmp_db()
    init_db(db)
    result = create_application(**_APP_KWARGS, db_path=db)
    assert result["id"] == "aaaa-bbbb"
    assert result["company"] == "Acme"
    assert result["status"] == "applied"


def test_get_application():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    result = get_application("aaaa-bbbb", db)
    assert result is not None
    assert result["position"] == "Engineer"


def test_get_application_not_found():
    db = _tmp_db()
    init_db(db)
    assert get_application("missing", db) is None


def test_list_applications():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    create_application(
        **{**_APP_KWARGS, "id": "cccc-dddd", "company": "Other"},
        db_path=db,
    )
    results = list_applications(db)
    assert len(results) == 2


def test_list_applications_empty():
    db = _tmp_db()
    init_db(db)
    assert list_applications(db) == []


def test_update_application():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    result = update_application(
        "aaaa-bbbb",
        {"company": "NewCo", "updated_at": "2026-03-22T12:00:00+00:00"},
        db,
    )
    assert result is not None
    assert result["company"] == "NewCo"
    assert result["position"] == "Engineer"  # unchanged


def test_update_application_not_found():
    db = _tmp_db()
    init_db(db)
    assert update_application("missing", {"company": "X"}, db) is None


def test_delete_application():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    assert delete_application("aaaa-bbbb", db) is True
    assert get_application("aaaa-bbbb", db) is None


def test_delete_application_not_found():
    db = _tmp_db()
    init_db(db)
    assert delete_application("missing", db) is False


def test_delete_application_cascades_meta():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    set_application_meta("aaaa-bbbb", "salary", "100k", db)
    delete_application("aaaa-bbbb", db)
    assert get_application_meta("aaaa-bbbb", db_path=db) == {}


# ── Application meta ─────────────────────────────────────────────────────────

def test_set_and_get_application_meta():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    set_application_meta("aaaa-bbbb", "salary", "100k", db)
    set_application_meta("aaaa-bbbb", "location", "Remote", db)
    meta = get_application_meta("aaaa-bbbb", db_path=db)
    assert meta == {"salary": "100k", "location": "Remote"}


def test_application_meta_upsert():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    set_application_meta("aaaa-bbbb", "salary", "100k", db)
    set_application_meta("aaaa-bbbb", "salary", "120k", db)
    meta = get_application_meta("aaaa-bbbb", "salary", db)
    assert meta == {"salary": "120k"}


def test_delete_application_meta():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    set_application_meta("aaaa-bbbb", "salary", "100k", db)
    delete_application_meta("aaaa-bbbb", "salary", db)
    assert get_application_meta("aaaa-bbbb", "salary", db) == {}


# ── Document CRUD ────────────────────────────────────────────────────────────

def test_create_document():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", title="My CV", db_path=db)
    assert doc["application_id"] == "aaaa-bbbb"
    assert doc["doc_type"] == "cv"
    assert doc["title"] == "My CV"
    assert doc["latex_source"] == ""
    assert doc["prompt_text"] == ""
    assert doc["id"]  # non-empty


def test_get_document():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    result = get_document(doc["id"], db)
    assert result is not None
    assert result["id"] == doc["id"]


def test_get_document_not_found():
    db = _tmp_db()
    init_db(db)
    assert get_document("missing", db) is None


def test_list_documents():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    create_document("aaaa-bbbb", "cv", title="CV 1", db_path=db)
    create_document("aaaa-bbbb", "cover_letter", title="CL 1", db_path=db)
    create_document("aaaa-bbbb", "cv", title="CV 2", db_path=db)
    all_docs = list_documents("aaaa-bbbb", db_path=db)
    assert len(all_docs) == 3


def test_list_documents_by_type():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    create_document("aaaa-bbbb", "cv", title="CV 1", db_path=db)
    create_document("aaaa-bbbb", "cover_letter", title="CL 1", db_path=db)
    create_document("aaaa-bbbb", "cv", title="CV 2", db_path=db)
    cvs = list_documents("aaaa-bbbb", doc_type="cv", db_path=db)
    assert len(cvs) == 2
    cls = list_documents("aaaa-bbbb", doc_type="cover_letter", db_path=db)
    assert len(cls) == 1


def test_update_document():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    updated = update_document(
        doc["id"],
        {"title": "Updated", "latex_source": "\\documentclass{article}"},
        db,
    )
    assert updated is not None
    assert updated["title"] == "Updated"
    assert updated["latex_source"] == "\\documentclass{article}"


def test_update_document_not_found():
    db = _tmp_db()
    init_db(db)
    assert update_document("missing", {"title": "X"}, db) is None


def test_delete_document():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    assert delete_document(doc["id"], db) is True
    assert get_document(doc["id"], db) is None


def test_delete_document_not_found():
    db = _tmp_db()
    init_db(db)
    assert delete_document("missing", db) is False


def test_delete_application_cascades_documents():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    delete_application("aaaa-bbbb", db)
    assert get_document(doc["id"], db) is None


# ── Document version CRUD ────────────────────────────────────────────────────

def test_create_version_auto_increments():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    v1 = create_version(doc["id"], "\\begin{document}v1\\end{document}", db_path=db)
    v2 = create_version(doc["id"], "\\begin{document}v2\\end{document}", db_path=db)
    assert v1["version_number"] == 1
    assert v2["version_number"] == 2


def test_list_versions():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    create_version(doc["id"], "src1", db_path=db)
    create_version(doc["id"], "src2", db_path=db)
    versions = list_versions(doc["id"], db)
    assert len(versions) == 2
    # Ordered by version_number DESC
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1


def test_get_version():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    v = create_version(doc["id"], "src", prompt_text="prompt", db_path=db)
    result = get_version(v["id"], db)
    assert result is not None
    assert result["latex_source"] == "src"
    assert result["prompt_text"] == "prompt"


def test_get_version_not_found():
    db = _tmp_db()
    init_db(db)
    assert get_version("missing", db) is None


def test_delete_document_cascades_versions():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    doc = create_document("aaaa-bbbb", "cv", db_path=db)
    v = create_version(doc["id"], "src", db_path=db)
    delete_document(doc["id"], db)
    assert get_version(v["id"], db) is None
