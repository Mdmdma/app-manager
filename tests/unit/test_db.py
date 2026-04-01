import tempfile
from pathlib import Path

import sqlite3

from jam.db import (
    init_db, get_setting, set_setting, delete_setting, get_all_settings,
    get_catalog, create_application, get_application, list_applications,
    list_applications_by_status,
    count_applications, update_application, delete_application, set_application_meta,
    get_application_meta, delete_application_meta,
    create_document, get_document, list_documents, update_document,
    delete_document, create_version, list_versions, get_version,
    create_extra_question, list_extra_questions, get_extra_question,
    update_extra_question, delete_extra_question,
    _connect, _create_catalog_tables, _migrate_catalog_add_cliproxy,
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
    assert "cliproxy" in ids


def test_catalog_cliproxy_provider_has_models():
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    cliproxy = next(p for p in catalog["providers"] if p["id"] == "cliproxy")
    model_ids = [m["model_id"] for m in cliproxy["llm_models"]]
    assert "claude-opus-4-6" in model_ids
    assert "claude-sonnet-4-6" in model_ids
    assert "claude-haiku-4-5" in model_ids


def test_catalog_cliproxy_provider_has_field():
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    cliproxy = next(p for p in catalog["providers"] if p["id"] == "cliproxy")
    keys = [f["key"] for f in cliproxy["fields"]]
    assert "cliproxy_base_url" in keys


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


# ── Catalog migration ─────────────────────────────────────────────────────────

def test_migrate_catalog_add_cliproxy_inserts_on_existing_db():
    """Migration inserts cliproxy rows into a db that was seeded without them."""
    db = _tmp_db()
    # Bootstrap catalog tables and seed only the original four providers
    with _connect(db) as conn:
        _create_catalog_tables(conn)
        conn.executemany(
            "INSERT INTO providers (id, label, type, sort_order) VALUES (?,?,?,?)",
            [
                ("openai",    "OpenAI",        "llm", 0),
                ("anthropic", "Anthropic",     "llm", 1),
                ("groq",      "Groq",          "llm", 2),
                ("ollama",    "Ollama (local)", "llm", 3),
            ],
        )
        conn.execute(
            """INSERT INTO models (id, provider_id, model_id, label, type,
               context_window, prompt_cost, completion_cost)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("openai:gpt-4o", "openai", "gpt-4o", "GPT-4o", "llm", 128000, None, None),
        )
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("openai", "openai_api_key", "OpenAI API Key", "password", "sk-...", 1, "llm", 0),
        )

    # Run migration
    with _connect(db) as conn:
        _migrate_catalog_add_cliproxy(conn)

    # Verify cliproxy rows were inserted
    with _connect(db) as conn:
        provider = conn.execute(
            "SELECT * FROM providers WHERE id = 'cliproxy'"
        ).fetchone()
        assert provider is not None
        assert provider["label"] == "CLIProxy (Claude Max)"

        model_ids = [
            row["model_id"] for row in conn.execute(
                "SELECT model_id FROM models WHERE provider_id = 'cliproxy'"
            ).fetchall()
        ]
        assert "claude-opus-4-6" in model_ids
        assert "claude-sonnet-4-6" in model_ids
        assert "claude-haiku-4-5" in model_ids

        field = conn.execute(
            "SELECT * FROM provider_fields WHERE provider_id = 'cliproxy'"
        ).fetchone()
        assert field is not None
        assert field["key"] == "cliproxy_base_url"
        assert field["placeholder"] == "http://localhost:8317"

        # Original data must still be present
        assert conn.execute(
            "SELECT COUNT(*) FROM providers WHERE id = 'openai'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM models WHERE id = 'openai:gpt-4o'"
        ).fetchone()[0] == 1


def test_migrate_catalog_add_cliproxy_is_idempotent():
    """Running the migration twice must not raise or duplicate rows."""
    db = _tmp_db()
    init_db(db)  # cliproxy already seeded

    # Second run must succeed silently
    with _connect(db) as conn:
        _migrate_catalog_add_cliproxy(conn)

    with _connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM providers WHERE id = 'cliproxy'"
        ).fetchone()[0]
        assert count == 1

        model_count = conn.execute(
            "SELECT COUNT(*) FROM models WHERE provider_id = 'cliproxy'"
        ).fetchone()[0]
        assert model_count == 3

        field_count = conn.execute(
            "SELECT COUNT(*) FROM provider_fields WHERE provider_id = 'cliproxy'"
        ).fetchone()[0]
        assert field_count == 1


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



def test_count_applications():
    db = _tmp_db()
    init_db(db)
    assert count_applications(db) == 0
    create_application(**_APP_KWARGS, db_path=db)
    assert count_applications(db) == 1
    create_application(
        **{**_APP_KWARGS, "id": "cccc-dddd", "company": "Other"},
        db_path=db,
    )
    assert count_applications(db) == 2


def test_count_applications_empty():
    db = _tmp_db()
    init_db(db)
    assert count_applications(db) == 0

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


# ── Extra questions ──────────────────────────────────────────────────────────

def test_create_extra_question():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    q = create_extra_question("aaaa-bbbb", question="Why us?", answer="Great fit", word_cap=150, db_path=db)
    assert q["id"]
    assert q["application_id"] == "aaaa-bbbb"
    assert q["question"] == "Why us?"
    assert q["answer"] == "Great fit"
    assert q["word_cap"] == 150
    assert q["sort_order"] == 0


def test_list_extra_questions_ordered():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    q1 = create_extra_question("aaaa-bbbb", question="Second", sort_order=2, db_path=db)
    q2 = create_extra_question("aaaa-bbbb", question="First", sort_order=1, db_path=db)
    qs = list_extra_questions("aaaa-bbbb", db_path=db)
    assert len(qs) == 2
    assert qs[0]["question"] == "First"
    assert qs[1]["question"] == "Second"


def test_update_extra_question():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    q = create_extra_question("aaaa-bbbb", question="Old", db_path=db)
    updated = update_extra_question(q["id"], {"question": "New", "word_cap": 200}, db_path=db)
    assert updated["question"] == "New"
    assert updated["word_cap"] == 200


def test_delete_extra_question():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    q = create_extra_question("aaaa-bbbb", question="Q", db_path=db)
    assert delete_extra_question(q["id"], db_path=db) is True
    assert get_extra_question(q["id"], db_path=db) is None
    assert delete_extra_question(q["id"], db_path=db) is False


def test_cascade_delete_extra_questions():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    q = create_extra_question("aaaa-bbbb", question="Q", db_path=db)
    delete_application("aaaa-bbbb", db_path=db)
    assert get_extra_question(q["id"], db_path=db) is None


# ── list_applications_by_status ───────────────────────────────────────────────

def test_list_applications_by_status_returns_matching():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)  # status="applied"
    create_application(
        **{**_APP_KWARGS, "id": "cccc-dddd", "company": "Other", "status": "interviewing"},
        db_path=db,
    )
    results = list_applications_by_status("applied", db)
    assert len(results) == 1
    assert results[0]["id"] == "aaaa-bbbb"
    assert results[0]["status"] == "applied"


def test_list_applications_by_status_empty_when_none_match():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)  # status="applied"
    results = list_applications_by_status("rejected", db)
    assert results == []


def test_list_applications_by_status_ordered_newest_first():
    db = _tmp_db()
    init_db(db)
    create_application(
        **{**_APP_KWARGS, "id": "app-1", "created_at": "2026-01-01T10:00:00+00:00",
           "updated_at": "2026-01-01T10:00:00+00:00"},
        db_path=db,
    )
    create_application(
        **{**_APP_KWARGS, "id": "app-2", "created_at": "2026-03-01T10:00:00+00:00",
           "updated_at": "2026-03-01T10:00:00+00:00"},
        db_path=db,
    )
    create_application(
        **{**_APP_KWARGS, "id": "app-3", "created_at": "2026-02-01T10:00:00+00:00",
           "updated_at": "2026-02-01T10:00:00+00:00"},
        db_path=db,
    )
    results = list_applications_by_status("applied", db)
    assert len(results) == 3
    assert results[0]["id"] == "app-2"
    assert results[1]["id"] == "app-3"
    assert results[2]["id"] == "app-1"


def test_list_applications_by_status_multiple_statuses_isolated():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)  # status="applied"
    create_application(
        **{**_APP_KWARGS, "id": "id-2", "status": "interviewing"},
        db_path=db,
    )
    create_application(
        **{**_APP_KWARGS, "id": "id-3", "status": "applied"},
        db_path=db,
    )
    applied = list_applications_by_status("applied", db)
    interviewing = list_applications_by_status("interviewing", db)
    assert len(applied) == 2
    assert len(interviewing) == 1
    assert interviewing[0]["id"] == "id-2"


def test_list_applications_by_status_returns_full_row():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    results = list_applications_by_status("applied", db)
    assert len(results) == 1
    row = results[0]
    assert row["company"] == "Acme"
    assert row["position"] == "Engineer"
    assert row["url"] == "https://example.com/job"
