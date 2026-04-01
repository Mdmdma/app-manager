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
    create_interview_round, list_interview_rounds, get_interview_round,
    update_interview_round, delete_interview_round,
    _connect, _create_catalog_tables, _migrate_catalog_add_cliproxy,
    _migrate_dedupe_provider_fields, _migrate_catalog_add_cliproxy_api_key,
    _migrate_interview_rounds_add_scheduled_time,
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
        assert field_count == 2  # cliproxy_base_url + cliproxy_api_key


# ── Dedupe provider_fields migration ─────────────────────────────────────────

def test_migrate_dedupe_provider_fields_removes_duplicates():
    """Duplicate (provider_id, key) rows are reduced to the one with the lowest id.

    The old provider_fields schema had no UNIQUE constraint, which allowed
    duplicate rows.  This test recreates that schema directly (without using
    _create_catalog_tables) so we can seed the duplicates that triggered the bug.
    """
    db = _tmp_db()
    with _connect(db) as conn:
        # Create providers table (needed for FK)
        conn.execute(
            """
            CREATE TABLE providers (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                type TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Create provider_fields WITHOUT the UNIQUE constraint (old schema)
        conn.execute(
            """
            CREATE TABLE provider_fields (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT NOT NULL REFERENCES providers(id),
                key         TEXT NOT NULL,
                label       TEXT NOT NULL,
                input_type  TEXT NOT NULL DEFAULT 'text',
                placeholder TEXT NOT NULL DEFAULT '',
                required    INTEGER NOT NULL DEFAULT 0,
                applies_to  TEXT NOT NULL DEFAULT 'both',
                sort_order  INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO providers (id, label, type, sort_order) VALUES (?,?,?,?)",
            ("openai", "OpenAI", "llm", 0),
        )
        # First insert — this is the one that should survive
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("openai", "openai_api_key", "OpenAI API Key", "password", "sk-...", 1, "llm", 0),
        )
        first_id = conn.execute(
            "SELECT id FROM provider_fields WHERE provider_id='openai' AND key='openai_api_key'"
        ).fetchone()[0]
        # Duplicate insert (simulates the bug: seed + migration both inserted)
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("openai", "openai_api_key", "OpenAI API Key duplicate", "password", "sk-dup", 1, "llm", 0),
        )
        count_before = conn.execute(
            "SELECT COUNT(*) FROM provider_fields WHERE provider_id='openai' AND key='openai_api_key'"
        ).fetchone()[0]
        assert count_before == 2

    # Run the dedup migration
    with _connect(db) as conn:
        _migrate_dedupe_provider_fields(conn)

    # Only one row should remain, and it must be the original (lowest id)
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT id, label FROM provider_fields WHERE provider_id='openai' AND key='openai_api_key'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == first_id
        assert rows[0]["label"] == "OpenAI API Key"


def test_migrate_dedupe_provider_fields_is_noop_when_no_duplicates():
    """Migration must not delete anything when all (provider_id, key) pairs are unique."""
    db = _tmp_db()
    init_db(db)

    with _connect(db) as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM provider_fields").fetchone()[0]

    with _connect(db) as conn:
        _migrate_dedupe_provider_fields(conn)

    with _connect(db) as conn:
        count_after = conn.execute("SELECT COUNT(*) FROM provider_fields").fetchone()[0]

    assert count_after == count_before


def test_init_db_has_no_duplicate_provider_fields():
    """init_db() must produce exactly one provider_fields row per (provider_id, key)."""
    db = _tmp_db()
    init_db(db)

    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT provider_id, key, COUNT(*) as cnt FROM provider_fields GROUP BY provider_id, key HAVING cnt > 1"
        ).fetchall()
    assert rows == [], f"Duplicate provider_fields rows found: {list(rows)}"


# ── cliproxy_api_key migration ────────────────────────────────────────────────

def test_catalog_cliproxy_provider_has_api_key_field():
    """After init_db the cliproxy provider must expose a cliproxy_api_key field."""
    db = _tmp_db()
    init_db(db)
    catalog = get_catalog(db)
    cliproxy = next(p for p in catalog["providers"] if p["id"] == "cliproxy")
    keys = [f["key"] for f in cliproxy["fields"]]
    assert "cliproxy_api_key" in keys


def test_migrate_catalog_add_cliproxy_api_key_inserts_on_existing_db():
    """Migration inserts cliproxy_api_key into a db that already has cliproxy_base_url."""
    db = _tmp_db()
    # Simulate a database that has cliproxy but only the base_url field
    with _connect(db) as conn:
        _create_catalog_tables(conn)
        conn.execute(
            "INSERT INTO providers (id, label, type, sort_order) VALUES (?,?,?,?)",
            ("cliproxy", "CLIProxy (Claude Max)", "llm", 4),
        )
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("cliproxy", "cliproxy_base_url", "CLIProxy Base URL", "url", "http://localhost:8317", 1, "llm", 0),
        )

    # Run the migration
    with _connect(db) as conn:
        _migrate_catalog_add_cliproxy_api_key(conn)

    # Verify the new field was inserted and the existing one was preserved
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT key, input_type, placeholder, sort_order FROM provider_fields WHERE provider_id = 'cliproxy' ORDER BY sort_order"
        ).fetchall()
        keys = [r["key"] for r in rows]
        assert "cliproxy_base_url" in keys
        assert "cliproxy_api_key" in keys
        api_key_row = next(r for r in rows if r["key"] == "cliproxy_api_key")
        assert api_key_row["input_type"] == "password"
        assert api_key_row["placeholder"] == "sk-..."
        assert api_key_row["sort_order"] == 1


def test_migrate_catalog_add_cliproxy_api_key_is_idempotent():
    """Running the migration twice must not raise or duplicate rows."""
    db = _tmp_db()
    init_db(db)  # cliproxy_api_key already seeded via _seed_catalog

    # Second run must succeed silently
    with _connect(db) as conn:
        _migrate_catalog_add_cliproxy_api_key(conn)

    with _connect(db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM provider_fields WHERE provider_id = 'cliproxy' AND key = 'cliproxy_api_key'"
        ).fetchone()[0]
    assert count == 1


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


# ── interview_rounds ──────────────────────────────────────────────────────────

def test_create_interview_round_defaults():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    r = create_interview_round("aaaa-bbbb", db_path=db)
    assert r["id"]
    assert r["application_id"] == "aaaa-bbbb"
    assert r["round_type"] == "other"
    assert r["scheduled_time"] == ""
    assert r["status"] == "scheduled"


def test_create_interview_round_with_scheduled_time():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    r = create_interview_round(
        "aaaa-bbbb",
        scheduled_at="2026-05-01",
        scheduled_time="14:30",
        db_path=db,
    )
    assert r["scheduled_at"] == "2026-05-01"
    assert r["scheduled_time"] == "14:30"


def test_update_interview_round_scheduled_time():
    db = _tmp_db()
    init_db(db)
    create_application(**_APP_KWARGS, db_path=db)
    r = create_interview_round("aaaa-bbbb", scheduled_time="09:00", db_path=db)
    updated = update_interview_round(r["id"], {"scheduled_time": "10:00"}, db_path=db)
    assert updated["scheduled_time"] == "10:00"


def test_migrate_interview_rounds_add_scheduled_time():
    """Migration adds scheduled_time to an existing table that lacks it."""
    db = _tmp_db()
    # Build a database that has interview_rounds WITHOUT scheduled_time by
    # creating it directly, bypassing init_db's migration call.
    with _connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id           TEXT PRIMARY KEY,
                company      TEXT NOT NULL,
                position     TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'applied',
                url          TEXT,
                notes        TEXT,
                applied_date TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_rounds (
                id               TEXT PRIMARY KEY,
                application_id   TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                round_type       TEXT NOT NULL DEFAULT 'other',
                round_number     INTEGER NOT NULL DEFAULT 1,
                scheduled_at     TEXT,
                completed_at     TEXT,
                interviewer_names TEXT NOT NULL DEFAULT '',
                location         TEXT NOT NULL DEFAULT '',
                status           TEXT NOT NULL DEFAULT 'scheduled',
                prep_notes       TEXT NOT NULL DEFAULT '',
                debrief_notes    TEXT NOT NULL DEFAULT '',
                questions_asked  TEXT NOT NULL DEFAULT '',
                went_well        TEXT NOT NULL DEFAULT '',
                to_improve       TEXT NOT NULL DEFAULT '',
                confidence       INTEGER,
                sort_order       INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Seed an existing row to verify data is preserved
        conn.execute(
            "INSERT INTO applications (id, company, position, status, applied_date, created_at, updated_at) "
            "VALUES ('app-1', 'ACME', 'Dev', 'applied', '2026-01-01', datetime('now'), datetime('now'))"
        )
        conn.execute(
            "INSERT INTO interview_rounds (id, application_id) VALUES ('rnd-1', 'app-1')"
        )

    # Verify the column is absent before migration
    with _connect(db) as conn:
        cols_before = [row[1] for row in conn.execute("PRAGMA table_info(interview_rounds)").fetchall()]
        assert "scheduled_time" not in cols_before

    # Run the migration
    with _connect(db) as conn:
        _migrate_interview_rounds_add_scheduled_time(conn)

    # Verify column was added and existing data preserved
    with _connect(db) as conn:
        cols_after = [row[1] for row in conn.execute("PRAGMA table_info(interview_rounds)").fetchall()]
        assert "scheduled_time" in cols_after
        row = conn.execute("SELECT * FROM interview_rounds WHERE id = 'rnd-1'").fetchone()
        assert row is not None
        assert row["scheduled_time"] == ""


def test_migrate_interview_rounds_idempotent():
    """Running the migration twice does not raise an error."""
    db = _tmp_db()
    init_db(db)
    with _connect(db) as conn:
        _migrate_interview_rounds_add_scheduled_time(conn)
        _migrate_interview_rounds_add_scheduled_time(conn)
    # Column still present, no error
    with _connect(db) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(interview_rounds)").fetchall()]
    assert "scheduled_time" in cols
