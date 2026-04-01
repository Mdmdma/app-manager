"""SQLite-backed persistence for the jam project.

All database interactions go through this module.  Tables:
- settings          key-value store for user preferences / API keys
- providers/models/provider_fields   LLM catalog (seeded on first run)
- applications      job application records
- application_meta  extensible key-value metadata per application
- documents         LaTeX documents (CVs / cover letters) per application
- document_versions version history snapshots created on each compile
- extra_questions   interview / application-form questions per application
- interview_rounds  interview round tracking per application
- offers            job offer details per application

The database file lives at <project_root>/jam.db by default and can be
overridden via the JAM_DB_PATH environment variable.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "jam.db"


def get_db_path() -> Path:
    custom = os.getenv("JAM_DB_PATH")
    return Path(custom) if custom else _DEFAULT_DB_PATH


@contextmanager
def _connect(db_path: Path | None = None):
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema helpers ────────────────────────────────────────────────────────────

def _create_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _create_catalog_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS providers (
            id         TEXT PRIMARY KEY,
            label      TEXT NOT NULL,
            type       TEXT NOT NULL CHECK (type IN ('llm', 'embedding', 'both')),
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS models (
            id              TEXT PRIMARY KEY,
            provider_id     TEXT NOT NULL REFERENCES providers(id),
            model_id        TEXT NOT NULL,
            label           TEXT NOT NULL,
            type            TEXT NOT NULL CHECK (type IN ('llm', 'embedding')),
            context_window  INTEGER,
            prompt_cost     REAL,
            completion_cost REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_fields (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id TEXT NOT NULL REFERENCES providers(id),
            key         TEXT NOT NULL,
            label       TEXT NOT NULL,
            input_type  TEXT NOT NULL DEFAULT 'text'
                            CHECK (input_type IN ('text', 'password', 'number', 'url')),
            placeholder TEXT NOT NULL DEFAULT '',
            required    INTEGER NOT NULL DEFAULT 0,
            applies_to  TEXT NOT NULL DEFAULT 'both'
                            CHECK (applies_to IN ('llm', 'embedding', 'both')),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            UNIQUE(provider_id, key)
        )
        """
    )


def _seed_catalog(conn: sqlite3.Connection) -> None:
    """Insert catalog rows once — skipped if each table already has data."""
    if conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0] > 0:
        return

    # ── Providers ─────────────────────────────────────────────────────────────
    conn.executemany(
        "INSERT INTO providers (id, label, type, sort_order) VALUES (?,?,?,?)",
        [
            ("openai",    "OpenAI",                "llm", 0),
            ("anthropic", "Anthropic",             "llm", 1),
            ("groq",      "Groq",                  "llm", 2),
            ("ollama",    "Ollama (local)",         "llm", 3),
            ("cliproxy",  "CLIProxy (Claude Max)",  "llm", 4),
        ],
    )

    # ── Models ────────────────────────────────────────────────────────────────
    conn.executemany(
        """INSERT INTO models
           (id, provider_id, model_id, label, type, context_window, prompt_cost, completion_cost)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            # OpenAI LLM
            ("openai:gpt-4o",        "openai", "gpt-4o",        "GPT-4o",        "llm", 128000, None, None),
            ("openai:gpt-4o-mini",   "openai", "gpt-4o-mini",   "GPT-4o mini",   "llm", 128000, None, None),
            ("openai:gpt-4-turbo",   "openai", "gpt-4-turbo",   "GPT-4 Turbo",   "llm", 128000, None, None),
            ("openai:gpt-3.5-turbo", "openai", "gpt-3.5-turbo", "GPT-3.5 Turbo", "llm", 16385,  None, None),
            # Anthropic LLM
            ("anthropic:claude-opus-4-6",   "anthropic", "claude-opus-4-6",   "Claude Opus 4.6",   "llm", 200000, None, None),
            ("anthropic:claude-sonnet-4-6", "anthropic", "claude-sonnet-4-6", "Claude Sonnet 4.6", "llm", 200000, None, None),
            ("anthropic:claude-haiku-4-5",  "anthropic", "claude-haiku-4-5",  "Claude Haiku 4.5",  "llm", 200000, None, None),
            # Groq LLM
            ("groq:llama-3.3-70b-versatile", "groq", "llama-3.3-70b-versatile", "Llama 3.3 70B", "llm", 128000, None, None),
            ("groq:llama-3.1-8b-instant",   "groq", "llama-3.1-8b-instant",   "Llama 3.1 8B",  "llm", 128000, None, None),
            ("groq:mixtral-8x7b-32768",     "groq", "mixtral-8x7b-32768",     "Mixtral 8x7B",  "llm", 32768,  None, None),
            ("groq:gemma2-9b-it",           "groq", "gemma2-9b-it",           "Gemma 2 9B",    "llm", 8192,   None, None),
            # Ollama LLM
            ("ollama:llama3.2", "ollama", "llama3.2", "Llama 3.2", "llm", None, None, None),
            ("ollama:mistral",  "ollama", "mistral",  "Mistral",   "llm", None, None, None),
            ("ollama:phi3",     "ollama", "phi3",     "Phi-3",     "llm", None, None, None),
            # CLIProxy LLM (routes through CLIProxyAPI to Claude Max)
            ("cliproxy:claude-opus-4-6",   "cliproxy", "claude-opus-4-6",   "Claude Opus 4.6",   "llm", 200000, None, None),
            ("cliproxy:claude-sonnet-4-6", "cliproxy", "claude-sonnet-4-6", "Claude Sonnet 4.6", "llm", 200000, None, None),
            ("cliproxy:claude-haiku-4-5",  "cliproxy", "claude-haiku-4-5",  "Claude Haiku 4.5",  "llm", 200000, None, None),
        ],
    )

    # ── Provider fields ───────────────────────────────────────────────────────
    conn.executemany(
        """INSERT INTO provider_fields
           (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            ("openai",    "openai_api_key",    "OpenAI API Key",    "password", "sk-...",                  1, "llm", 0),
            ("anthropic", "anthropic_api_key", "Anthropic API Key", "password", "sk-ant-...",              1, "llm", 0),
            ("groq",      "groq_api_key",      "Groq API Key",      "password", "gsk_...",                 1, "llm", 0),
            ("ollama",    "ollama_base_url",   "Ollama Base URL",   "url",      "http://localhost:11434",  1, "llm", 0),
            ("cliproxy",  "cliproxy_base_url", "CLIProxy Base URL", "url",      "http://localhost:8317",   1, "llm", 0),
            ("cliproxy",  "cliproxy_api_key",  "CLIProxy API Key",  "password", "sk-...",                  1, "llm", 1),
        ],
    )


def _create_applications_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id             TEXT PRIMARY KEY,
            company        TEXT NOT NULL,
            position       TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'not_applied_yet'
                               CHECK (status IN ('not_applied_yet','applied','screening','interviewing','offered','rejected','accepted','withdrawn')),
            url            TEXT,
            notes          TEXT,
            applied_date   TEXT NOT NULL,
            salary_range   TEXT,
            location       TEXT,
            work_mode      TEXT CHECK (work_mode IN ('remote','hybrid','onsite')),
            contact_person TEXT,
            opening_date   TEXT,
            closing_date   TEXT,
            description    TEXT,
            full_text      TEXT,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS application_meta (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            key            TEXT NOT NULL,
            value          TEXT NOT NULL,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(application_id, key)
        )
        """
    )


def _create_documents_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id             TEXT PRIMARY KEY,
            application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            doc_type       TEXT NOT NULL CHECK (doc_type IN ('cv', 'cover_letter')),
            title          TEXT NOT NULL DEFAULT 'Untitled',
            latex_source   TEXT NOT NULL DEFAULT '',
            prompt_text    TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_versions (
            id             TEXT PRIMARY KEY,
            document_id    TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            latex_source   TEXT NOT NULL,
            prompt_text    TEXT NOT NULL DEFAULT '',
            compiled_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(document_id, version_number)
        )
        """
    )


# ── Migrations ────────────────────────────────────────────────────────────────

def _migrate_applications_table(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the initial schema."""
    for col in ("salary_range TEXT", "location TEXT", "work_mode TEXT", "contact_person TEXT",
                 "opening_date TEXT", "closing_date TEXT", "description TEXT", "full_text TEXT"):
        try:
            conn.execute(f"ALTER TABLE applications ADD COLUMN {col}")  # noqa: S608
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc):
                raise

    # Rebuild table to update CHECK constraint (adds 'not_applied_yet' status).
    # Uses individual execute() calls (NOT executescript) to stay inside the
    # _connect() transaction — if any step fails, the whole migration rolls back.
    table_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='applications'"
    ).fetchone()
    if table_sql and "not_applied_yet" not in table_sql["sql"]:
        old_count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        conn.execute("ALTER TABLE applications RENAME TO _applications_old")
        conn.execute(
            """
            CREATE TABLE applications (
                id             TEXT PRIMARY KEY,
                company        TEXT NOT NULL,
                position       TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'not_applied_yet'
                                   CHECK (status IN ('not_applied_yet','applied','screening','interviewing','offered','rejected','accepted','withdrawn')),
                url            TEXT,
                notes          TEXT,
                applied_date   TEXT NOT NULL,
                salary_range   TEXT,
                location       TEXT,
                work_mode      TEXT CHECK (work_mode IN ('remote','hybrid','onsite')),
                contact_person TEXT,
                opening_date   TEXT,
                closing_date   TEXT,
                description    TEXT,
                full_text      TEXT,
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            )
            """
        )
        # Copy only columns that existed in the old table
        old_cols = [row[1] for row in conn.execute("PRAGMA table_info(_applications_old)").fetchall()]
        new_cols = [row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()]
        common = [c for c in new_cols if c in old_cols]
        cols_str = ", ".join(common)
        conn.execute(f"INSERT INTO applications ({cols_str}) SELECT {cols_str} FROM _applications_old")
        new_count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        if new_count != old_count:
            raise RuntimeError(
                f"Migration row count mismatch: {old_count} -> {new_count}"
            )
        conn.execute("DROP TABLE _applications_old")


def _migrate_catalog_add_cliproxy(conn: sqlite3.Connection) -> None:
    """Add the CLIProxy provider, models, and field to existing databases.

    Uses INSERT OR IGNORE so this migration is idempotent — safe to run on
    both fresh databases (where _seed_catalog already inserted the rows) and
    on existing databases that were seeded before CLIProxy was added.
    """
    conn.execute(
        "INSERT OR IGNORE INTO providers (id, label, type, sort_order) VALUES (?,?,?,?)",
        ("cliproxy", "CLIProxy (Claude Max)", "llm", 4),
    )
    conn.executemany(
        """INSERT OR IGNORE INTO models
           (id, provider_id, model_id, label, type, context_window, prompt_cost, completion_cost)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            ("cliproxy:claude-opus-4-6",   "cliproxy", "claude-opus-4-6",   "Claude Opus 4.6",   "llm", 200000, None, None),
            ("cliproxy:claude-sonnet-4-6", "cliproxy", "claude-sonnet-4-6", "Claude Sonnet 4.6", "llm", 200000, None, None),
            ("cliproxy:claude-haiku-4-5",  "cliproxy", "claude-haiku-4-5",  "Claude Haiku 4.5",  "llm", 200000, None, None),
        ],
    )
    exists = conn.execute(
        "SELECT COUNT(*) FROM provider_fields WHERE provider_id = ? AND key = ?",
        ("cliproxy", "cliproxy_base_url"),
    ).fetchone()[0]
    if not exists:
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("cliproxy", "cliproxy_base_url", "CLIProxy Base URL", "url", "http://localhost:8317", 1, "llm", 0),
        )


def _migrate_dedupe_provider_fields(conn: sqlite3.Connection) -> None:
    """Remove duplicate provider_fields rows, keeping the one with the lowest id.

    Duplicates can arise on databases that were created before the
    UNIQUE(provider_id, key) constraint was added to provider_fields — the
    original _seed_catalog used a plain executemany (no conflict handling) and
    _migrate_catalog_add_cliproxy guarded with a SELECT COUNT check, but both
    could still insert the same row twice in certain upgrade sequences.

    This migration is idempotent: if there are no duplicates it is a no-op.
    """
    conn.execute(
        """
        DELETE FROM provider_fields
        WHERE id NOT IN (
            SELECT MIN(id) FROM provider_fields GROUP BY provider_id, key
        )
        """
    )


def _migrate_catalog_add_cliproxy_api_key(conn: sqlite3.Connection) -> None:
    """Add cliproxy_api_key field to existing databases."""
    exists = conn.execute(
        "SELECT COUNT(*) FROM provider_fields WHERE provider_id = ? AND key = ?",
        ("cliproxy", "cliproxy_api_key"),
    ).fetchone()[0]
    if not exists:
        conn.execute(
            """INSERT INTO provider_fields
               (provider_id, key, label, input_type, placeholder, required, applies_to, sort_order)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("cliproxy", "cliproxy_api_key", "CLIProxy API Key", "password", "sk-...", 1, "llm", 1),
        )


def _create_extra_questions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS extra_questions (
            id             TEXT PRIMARY KEY,
            application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            question       TEXT NOT NULL DEFAULT '',
            answer         TEXT NOT NULL DEFAULT '',
            word_cap       INTEGER,
            sort_order     INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _create_interview_rounds_table(conn: sqlite3.Connection) -> None:
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


def _create_offers_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id              TEXT PRIMARY KEY,
            application_id  TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            status          TEXT NOT NULL DEFAULT 'pending',
            base_salary     REAL,
            currency        TEXT NOT NULL DEFAULT 'EUR',
            bonus           TEXT NOT NULL DEFAULT '',
            equity          TEXT NOT NULL DEFAULT '',
            signing_bonus   TEXT NOT NULL DEFAULT '',
            benefits        TEXT NOT NULL DEFAULT '',
            pto_days        INTEGER,
            remote_policy   TEXT NOT NULL DEFAULT '',
            start_date      TEXT,
            expiry_date     TEXT,
            notes           TEXT NOT NULL DEFAULT '',
            sort_order      INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def init_db(db_path: Path | None = None) -> None:
    """Create all tables and seed initial data."""
    with _connect(db_path) as conn:
        _create_settings_table(conn)
        _create_catalog_tables(conn)
        _seed_catalog(conn)
        _migrate_catalog_add_cliproxy(conn)
        _migrate_dedupe_provider_fields(conn)
        _migrate_catalog_add_cliproxy_api_key(conn)
        _create_applications_tables(conn)
        _migrate_applications_table(conn)
        _create_documents_tables(conn)
        _create_extra_questions_table(conn)
        _create_interview_rounds_table(conn)
        _create_offers_table(conn)


# ── Settings CRUD ─────────────────────────────────────────────────────────────

def get_setting(key: str, db_path: Path | None = None) -> str | None:
    """Return the stored value for *key*, or None if not set."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str, db_path: Path | None = None) -> None:
    """Upsert a setting value."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value),
        )


def set_settings_batch(updates: dict, db_path: Path | None = None) -> None:
    """Upsert multiple settings atomically. Rolls back all on failure."""
    with _connect(db_path) as conn:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value      = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value),
            )


def delete_setting(key: str, db_path: Path | None = None) -> None:
    """Remove a setting entry entirely."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))


def get_all_settings(db_path: Path | None = None) -> dict[str, str]:
    """Return all stored settings as a plain dict."""
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


# ── Catalog query ─────────────────────────────────────────────────────────────

def get_catalog(db_path: Path | None = None) -> dict:
    """Return the full provider/model/field catalog for the settings UI."""
    with _connect(db_path) as conn:
        providers = conn.execute(
            "SELECT id, label, type FROM providers ORDER BY sort_order, id"
        ).fetchall()

        models = conn.execute(
            "SELECT id, provider_id, model_id, label, type, "
            "context_window, prompt_cost, completion_cost "
            "FROM models ORDER BY provider_id, type, label"
        ).fetchall()

        fields = conn.execute(
            "SELECT provider_id, key, label, input_type, placeholder, required, applies_to "
            "FROM provider_fields ORDER BY provider_id, sort_order"
        ).fetchall()

    # Group models and fields by provider
    llm_models: dict[str, list] = {}
    for m in models:
        if m["type"] == "llm":
            llm_models.setdefault(m["provider_id"], []).append({
                "id": m["id"],
                "model_id": m["model_id"],
                "label": m["label"],
                "context_window": m["context_window"],
                "prompt_cost": m["prompt_cost"],
                "completion_cost": m["completion_cost"],
            })

    prov_fields: dict[str, list] = {}
    for f in fields:
        prov_fields.setdefault(f["provider_id"], []).append({
            "key": f["key"],
            "label": f["label"],
            "input_type": f["input_type"],
            "placeholder": f["placeholder"],
            "required": bool(f["required"]),
            "applies_to": f["applies_to"],
        })

    result = []
    for p in providers:
        result.append({
            "id": p["id"],
            "label": p["label"],
            "type": p["type"],
            "llm_models": llm_models.get(p["id"], []),
            "fields": prov_fields.get(p["id"], []),
        })

    return {"providers": result}


# ── Application CRUD ─────────────────────────────────────────────────────────

def _row_to_app(row: sqlite3.Row) -> dict:
    return dict(row)


def create_application(
    id: str,
    company: str,
    position: str,
    status: str,
    url: str | None,
    notes: str | None,
    applied_date: str,
    created_at: str,
    updated_at: str,
    *,
    salary_range: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    contact_person: str | None = None,
    opening_date: str | None = None,
    closing_date: str | None = None,
    description: str | None = None,
    full_text: str | None = None,
    db_path: Path | None = None,
) -> dict:
    """Insert a new application and return it as a dict."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO applications
                (id, company, position, status, url, notes,
                 applied_date, salary_range, location, work_mode,
                 contact_person, opening_date, closing_date,
                 description, full_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, company, position, status, url, notes,
             applied_date, salary_range, location, work_mode,
             contact_person, opening_date, closing_date,
             description, full_text, created_at, updated_at),
        )
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (id,)
        ).fetchone()
    return _row_to_app(row)


def get_application(app_id: str, db_path: Path | None = None) -> dict | None:
    """Return a single application dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    return _row_to_app(row) if row else None


def list_applications(db_path: Path | None = None) -> list[dict]:
    """Return all applications ordered by creation time (newest first)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_app(r) for r in rows]


def list_applications_by_status(
    status: str, db_path: Path | None = None
) -> list[dict]:
    """Return all applications with the given status, newest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    return [_row_to_app(r) for r in rows]


def count_applications(db_path: Path | None = None) -> int:
    """Return the total number of applications."""
    with _connect(db_path) as conn:
        result = conn.execute("SELECT COUNT(*) as count FROM applications").fetchone()
    return result["count"] if result else 0


def update_application(
    app_id: str, fields: dict, db_path: Path | None = None,
) -> dict | None:
    """Update an application's fields. Returns the updated dict, or None."""
    if not fields:
        return get_application(app_id, db_path)
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [app_id]
        conn.execute(
            f"UPDATE applications SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    return _row_to_app(row) if row else None


def delete_application(app_id: str, db_path: Path | None = None) -> bool:
    """Delete an application. Returns True if a row was removed."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM applications WHERE id = ?", (app_id,)
        )
    return cursor.rowcount > 0


# ── Application meta (extensible key-value per application) ──────────────────

def set_application_meta(
    app_id: str, key: str, value: str, db_path: Path | None = None,
) -> None:
    """Upsert a metadata entry for an application."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO application_meta (application_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(application_id, key) DO UPDATE SET
                value = excluded.value
            """,
            (app_id, key, value),
        )


def get_application_meta(
    app_id: str,
    key: str | None = None,
    db_path: Path | None = None,
) -> dict[str, str]:
    """Return metadata for an application as ``{key: value}``."""
    with _connect(db_path) as conn:
        if key is not None:
            rows = conn.execute(
                "SELECT key, value FROM application_meta "
                "WHERE application_id = ? AND key = ?",
                (app_id, key),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value FROM application_meta "
                "WHERE application_id = ?",
                (app_id,),
            ).fetchall()
    return {r["key"]: r["value"] for r in rows}


def delete_application_meta(
    app_id: str, key: str, db_path: Path | None = None,
) -> None:
    """Remove a single metadata entry."""
    with _connect(db_path) as conn:
        conn.execute(
            "DELETE FROM application_meta WHERE application_id = ? AND key = ?",
            (app_id, key),
        )


# ── Document CRUD ────────────────────────────────────────────────────────────

def create_document(
    application_id: str,
    doc_type: str,
    title: str = "Untitled",
    latex_source: str = "",
    prompt_text: str = "",
    db_path: Path | None = None,
) -> dict:
    """Insert a new document and return it as a dict."""
    doc_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO documents
                (id, application_id, doc_type, title, latex_source, prompt_text,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (doc_id, application_id, doc_type, title, latex_source, prompt_text),
        )
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row)


def get_document(doc_id: str, db_path: Path | None = None) -> dict | None:
    """Return a single document dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def list_documents(
    application_id: str,
    doc_type: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Return documents for an application, optionally filtered by type."""
    with _connect(db_path) as conn:
        if doc_type is not None:
            rows = conn.execute(
                "SELECT * FROM documents WHERE application_id = ? AND doc_type = ? "
                "ORDER BY created_at DESC",
                (application_id, doc_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents WHERE application_id = ? "
                "ORDER BY created_at DESC",
                (application_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def update_document(
    doc_id: str, fields: dict, db_path: Path | None = None,
) -> dict | None:
    """Update a document's fields. Returns the updated dict, or None."""
    if not fields:
        return get_document(doc_id, db_path)
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [doc_id]
        conn.execute(
            f"UPDATE documents SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_document(doc_id: str, db_path: Path | None = None) -> bool:
    """Delete a document. Returns True if a row was removed."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM documents WHERE id = ?", (doc_id,)
        )
    return cursor.rowcount > 0


# ── Document version CRUD ────────────────────────────────────────────────────

def create_version(
    document_id: str,
    latex_source: str,
    prompt_text: str = "",
    db_path: Path | None = None,
) -> dict:
    """Create a new version snapshot. Auto-increments version_number."""
    ver_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) AS max_ver "
            "FROM document_versions WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        next_ver = row["max_ver"] + 1
        conn.execute(
            """
            INSERT INTO document_versions
                (id, document_id, version_number, latex_source, prompt_text, compiled_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (ver_id, document_id, next_ver, latex_source, prompt_text),
        )
        result = conn.execute(
            "SELECT * FROM document_versions WHERE id = ?", (ver_id,)
        ).fetchone()
    return dict(result)


def list_versions(
    document_id: str, db_path: Path | None = None,
) -> list[dict]:
    """Return all versions for a document, ordered by version_number desc."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM document_versions WHERE document_id = ? "
            "ORDER BY version_number DESC",
            (document_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_version(version_id: str, db_path: Path | None = None) -> dict | None:
    """Return a single version dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM document_versions WHERE id = ?", (version_id,)
        ).fetchone()
    return dict(row) if row else None


# ── Extra questions CRUD ─────────────────────────────────────────────────────

def create_extra_question(
    application_id: str,
    question: str = "",
    answer: str = "",
    word_cap: int | None = None,
    sort_order: int = 0,
    db_path: Path | None = None,
) -> dict:
    """Insert a new extra question and return it as a dict."""
    q_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO extra_questions
                (id, application_id, question, answer, word_cap, sort_order,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (q_id, application_id, question, answer, word_cap, sort_order),
        )
        row = conn.execute(
            "SELECT * FROM extra_questions WHERE id = ?", (q_id,)
        ).fetchone()
    return dict(row)


def list_extra_questions(
    application_id: str, db_path: Path | None = None,
) -> list[dict]:
    """Return extra questions for an application, ordered by sort_order."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM extra_questions WHERE application_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (application_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_extra_question(
    question_id: str, db_path: Path | None = None,
) -> dict | None:
    """Return a single extra question dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM extra_questions WHERE id = ?", (question_id,)
        ).fetchone()
    return dict(row) if row else None


def update_extra_question(
    question_id: str, fields: dict, db_path: Path | None = None,
) -> dict | None:
    """Update an extra question's fields. Returns the updated dict, or None."""
    if not fields:
        return get_extra_question(question_id, db_path)
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [question_id]
        conn.execute(
            f"UPDATE extra_questions SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM extra_questions WHERE id = ?", (question_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_extra_question(
    question_id: str, db_path: Path | None = None,
) -> bool:
    """Delete an extra question. Returns True if a row was removed."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM extra_questions WHERE id = ?", (question_id,)
        )
    return cursor.rowcount > 0


# ── Interview rounds CRUD ───────────────────────────────────────────────────

def create_interview_round(
    application_id: str,
    round_type: str = "other",
    round_number: int = 1,
    scheduled_at: str | None = None,
    completed_at: str | None = None,
    interviewer_names: str = "",
    location: str = "",
    status: str = "scheduled",
    prep_notes: str = "",
    debrief_notes: str = "",
    questions_asked: str = "",
    went_well: str = "",
    to_improve: str = "",
    confidence: int | None = None,
    sort_order: int = 0,
    db_path: Path | None = None,
) -> dict:
    """Insert a new interview round and return it as a dict."""
    r_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO interview_rounds
                (id, application_id, round_type, round_number, scheduled_at,
                 completed_at, interviewer_names, location, status, prep_notes,
                 debrief_notes, questions_asked, went_well, to_improve,
                 confidence, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    datetime('now'), datetime('now'))
            """,
            (r_id, application_id, round_type, round_number, scheduled_at,
             completed_at, interviewer_names, location, status, prep_notes,
             debrief_notes, questions_asked, went_well, to_improve,
             confidence, sort_order),
        )
        row = conn.execute(
            "SELECT * FROM interview_rounds WHERE id = ?", (r_id,)
        ).fetchone()
    return dict(row)


def list_interview_rounds(
    application_id: str, db_path: Path | None = None,
) -> list[dict]:
    """Return interview rounds for an application, ordered by sort_order."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM interview_rounds WHERE application_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (application_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_interview_round(
    round_id: str, db_path: Path | None = None,
) -> dict | None:
    """Return a single interview round dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM interview_rounds WHERE id = ?", (round_id,)
        ).fetchone()
    return dict(row) if row else None


def update_interview_round(
    round_id: str, fields: dict, db_path: Path | None = None,
) -> dict | None:
    """Update an interview round's fields. Returns the updated dict, or None."""
    if not fields:
        return get_interview_round(round_id, db_path)
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [round_id]
        conn.execute(
            f"UPDATE interview_rounds SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM interview_rounds WHERE id = ?", (round_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_interview_round(
    round_id: str, db_path: Path | None = None,
) -> bool:
    """Delete an interview round. Returns True if a row was removed."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM interview_rounds WHERE id = ?", (round_id,)
        )
    return cursor.rowcount > 0


# ── Offers CRUD ─────────────────────────────────────────────────────────────

def create_offer(
    application_id: str,
    status: str = "pending",
    base_salary: float | None = None,
    currency: str = "EUR",
    bonus: str = "",
    equity: str = "",
    signing_bonus: str = "",
    benefits: str = "",
    pto_days: int | None = None,
    remote_policy: str = "",
    start_date: str | None = None,
    expiry_date: str | None = None,
    notes: str = "",
    sort_order: int = 0,
    db_path: Path | None = None,
) -> dict:
    """Insert a new offer and return it as a dict."""
    o_id = uuid.uuid4().hex
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO offers
                (id, application_id, status, base_salary, currency, bonus,
                 equity, signing_bonus, benefits, pto_days, remote_policy,
                 start_date, expiry_date, notes, sort_order,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    datetime('now'), datetime('now'))
            """,
            (o_id, application_id, status, base_salary, currency, bonus,
             equity, signing_bonus, benefits, pto_days, remote_policy,
             start_date, expiry_date, notes, sort_order),
        )
        row = conn.execute(
            "SELECT * FROM offers WHERE id = ?", (o_id,)
        ).fetchone()
    return dict(row)


def list_offers(
    application_id: str, db_path: Path | None = None,
) -> list[dict]:
    """Return offers for an application, ordered by sort_order."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM offers WHERE application_id = ? "
            "ORDER BY sort_order ASC, created_at ASC",
            (application_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_offer(
    offer_id: str, db_path: Path | None = None,
) -> dict | None:
    """Return a single offer dict, or None if not found."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM offers WHERE id = ?", (offer_id,)
        ).fetchone()
    return dict(row) if row else None


def update_offer(
    offer_id: str, fields: dict, db_path: Path | None = None,
) -> dict | None:
    """Update an offer's fields. Returns the updated dict, or None."""
    if not fields:
        return get_offer(offer_id, db_path)
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [offer_id]
        conn.execute(
            f"UPDATE offers SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM offers WHERE id = ?", (offer_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_offer(
    offer_id: str, db_path: Path | None = None,
) -> bool:
    """Delete an offer. Returns True if a row was removed."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM offers WHERE id = ?", (offer_id,)
        )
    return cursor.rowcount > 0
