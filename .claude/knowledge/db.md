# db Knowledge
<!-- source: jam/db.py -->
<!-- hash: fbaf5dee60c1 -->
<!-- updated: 2026-03-31 -->

## Public API

| Function | Signature | Purpose |
|---|---|---|
| `get_db_path` | `() -> Path` | Return DB path from `JAM_DB_PATH` env var or default `<project>/jam.db` |
| `init_db` | `(db_path: Path \| None = None) -> None` | Create all tables, seed catalog, run migrations |
| `get_setting` | `(key: str, db_path?) -> str \| None` | Return stored value for key, or None |
| `set_setting` | `(key: str, value: str, db_path?) -> None` | Upsert a setting value |
| `set_settings_batch` | `(updates: dict, db_path?) -> None` | Upsert multiple settings atomically |
| `delete_setting` | `(key: str, db_path?) -> None` | Remove a setting entry |
| `get_all_settings` | `(db_path?) -> dict[str, str]` | Return all settings as `{key: value}` |
| `get_catalog` | `(db_path?) -> dict` | Return full provider/model/field catalog for settings UI |
| `create_application` | `(id, company, position, status, url, notes, applied_date, created_at, updated_at, *, salary_range?, location?, work_mode?, contact_person?, opening_date?, closing_date?, description?, full_text?, db_path?) -> dict` | Insert new application |
| `get_application` | `(app_id: str, db_path?) -> dict \| None` | Return single application or None |
| `list_applications` | `(db_path?) -> list[dict]` | Return all applications (newest first) |
| `list_applications_by_status` | `(status: str, db_path?) -> list[dict]` | Return applications matching status, newest first |
| `count_applications` | `(db_path?) -> int` | Return the total number of applications |
| `update_application` | `(app_id: str, fields: dict, db_path?) -> dict \| None` | Update application fields |
| `delete_application` | `(app_id: str, db_path?) -> bool` | Delete application, returns True if removed |
| `set_application_meta` | `(app_id: str, key: str, value: str, db_path?) -> None` | Upsert key-value metadata for an application |
| `get_application_meta` | `(app_id: str, key?: str, db_path?) -> dict[str, str]` | Return metadata as `{key: value}`, optionally filtered by key |
| `delete_application_meta` | `(app_id: str, key: str, db_path?) -> None` | Remove a single metadata entry |
| `create_document` | `(application_id, doc_type, title?, latex_source?, prompt_text?, db_path?) -> dict` | Insert new document (auto-generates UUID) |
| `get_document` | `(doc_id: str, db_path?) -> dict \| None` | Return single document or None |
| `list_documents` | `(application_id: str, doc_type?: str, db_path?) -> list[dict]` | Return documents for application, optionally by type |
| `update_document` | `(doc_id: str, fields: dict, db_path?) -> dict \| None` | Update document fields (auto-sets updated_at) |
| `delete_document` | `(doc_id: str, db_path?) -> bool` | Delete document, returns True if removed |
| `create_version` | `(document_id, latex_source, prompt_text?, db_path?) -> dict` | Create version snapshot (auto-increments version_number) |
| `list_versions` | `(document_id: str, db_path?) -> list[dict]` | Return all versions for document (newest first) |
| `get_version` | `(version_id: str, db_path?) -> dict \| None` | Return single version or None |
| `create_extra_question` | `(application_id, question?, answer?, word_cap?, sort_order?, db_path?) -> dict` | Insert new extra question (auto-generates UUID) |
| `list_extra_questions` | `(application_id: str, db_path?) -> list[dict]` | Return extra questions ordered by sort_order, then created_at |
| `get_extra_question` | `(question_id: str, db_path?) -> dict \| None` | Return single extra question or None |
| `update_extra_question` | `(question_id: str, fields: dict, db_path?) -> dict \| None` | Update extra question fields (auto-sets updated_at) |
| `delete_extra_question` | `(question_id: str, db_path?) -> bool` | Delete extra question, returns True if removed |
| `create_interview_round` | `(application_id, round_type?, round_number?, scheduled_at?, completed_at?, interviewer_names?, location?, status?, prep_notes?, debrief_notes?, questions_asked?, went_well?, to_improve?, confidence?, sort_order?, db_path?) -> dict` | Insert new interview round (auto-generates UUID) |
| `list_interview_rounds` | `(application_id: str, db_path?) -> list[dict]` | Return interview rounds ordered by sort_order, then created_at |
| `get_interview_round` | `(round_id: str, db_path?) -> dict \| None` | Return single interview round or None |
| `update_interview_round` | `(round_id: str, fields: dict, db_path?) -> dict \| None` | Update interview round fields (auto-sets updated_at) |
| `delete_interview_round` | `(round_id: str, db_path?) -> bool` | Delete interview round, returns True if removed |
| `create_offer` | `(application_id, status?, base_salary?, currency?, bonus?, equity?, signing_bonus?, benefits?, pto_days?, remote_policy?, start_date?, expiry_date?, notes?, sort_order?, db_path?) -> dict` | Insert new offer (auto-generates UUID) |
| `list_offers` | `(application_id: str, db_path?) -> list[dict]` | Return offers ordered by sort_order, then created_at |
| `get_offer` | `(offer_id: str, db_path?) -> dict \| None` | Return single offer or None |
| `update_offer` | `(offer_id: str, fields: dict, db_path?) -> dict \| None` | Update offer fields (auto-sets updated_at) |
| `delete_offer` | `(offer_id: str, db_path?) -> bool` | Delete offer, returns True if removed |

## Key Constants / Schema

### Module-level

| Constant | Value | Purpose |
|---|---|---|
| `_DEFAULT_DB_PATH` | `Path(__file__).parent.parent / "jam.db"` | Default SQLite file location |

### `_connect()` context manager

`_connect(db_path: Path | None = None)` -- Internal context manager used by all public functions. Opens a SQLite connection with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row`. Auto-commits on success, rolls back on exception, always closes.

### Tables

**settings** -- Key-value store for user preferences / API keys

| Column | Type | Constraints |
|---|---|---|
| `key` | TEXT | PRIMARY KEY |
| `value` | TEXT | NOT NULL |
| `updated_at` | TEXT | NOT NULL, DEFAULT datetime('now') |

**providers** -- LLM provider catalog (seeded on first run)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `label` | TEXT | NOT NULL |
| `type` | TEXT | NOT NULL, CHECK IN ('llm', 'embedding', 'both') |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 |

**models** -- LLM model catalog (seeded on first run)

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `provider_id` | TEXT | NOT NULL, FK -> providers(id) |
| `model_id` | TEXT | NOT NULL |
| `label` | TEXT | NOT NULL |
| `type` | TEXT | NOT NULL, CHECK IN ('llm', 'embedding') |
| `context_window` | INTEGER | nullable |
| `prompt_cost` | REAL | nullable |
| `completion_cost` | REAL | nullable |

**provider_fields** -- Configuration fields per provider (seeded on first run)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `provider_id` | TEXT | NOT NULL, FK -> providers(id) |
| `key` | TEXT | NOT NULL |
| `label` | TEXT | NOT NULL |
| `input_type` | TEXT | NOT NULL, DEFAULT 'text', CHECK IN ('text', 'password', 'number', 'url') |
| `placeholder` | TEXT | NOT NULL, DEFAULT '' |
| `required` | INTEGER | NOT NULL, DEFAULT 0 |
| `applies_to` | TEXT | NOT NULL, DEFAULT 'both', CHECK IN ('llm', 'embedding', 'both') |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 |

**applications** -- Job application records

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `company` | TEXT | NOT NULL |
| `position` | TEXT | NOT NULL |
| `status` | TEXT | NOT NULL, DEFAULT 'not_applied_yet', CHECK IN ('not_applied_yet','applied','screening','interviewing','offered','rejected','accepted','withdrawn') |
| `url` | TEXT | nullable |
| `notes` | TEXT | nullable |
| `applied_date` | TEXT | NOT NULL |
| `salary_range` | TEXT | nullable |
| `location` | TEXT | nullable |
| `work_mode` | TEXT | CHECK IN ('remote','hybrid','onsite') |
| `contact_person` | TEXT | nullable |
| `opening_date` | TEXT | nullable |
| `closing_date` | TEXT | nullable |
| `description` | TEXT | nullable |
| `full_text` | TEXT | nullable |
| `created_at` | TEXT | NOT NULL |
| `updated_at` | TEXT | NOT NULL |

**application_meta** -- Extensible key-value metadata per application

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `application_id` | TEXT | NOT NULL, FK -> applications(id) ON DELETE CASCADE |
| `key` | TEXT | NOT NULL |
| `value` | TEXT | NOT NULL |
| `created_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| | | UNIQUE(application_id, key) |

**documents** -- LaTeX documents (CVs / cover letters) per application

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `application_id` | TEXT | NOT NULL, FK -> applications(id) ON DELETE CASCADE |
| `doc_type` | TEXT | NOT NULL, CHECK IN ('cv', 'cover_letter') |
| `title` | TEXT | NOT NULL, DEFAULT 'Untitled' |
| `latex_source` | TEXT | NOT NULL, DEFAULT '' |
| `prompt_text` | TEXT | NOT NULL, DEFAULT '' |
| `created_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| `updated_at` | TEXT | NOT NULL, DEFAULT datetime('now') |

**document_versions** -- Version history snapshots created on each compile

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `document_id` | TEXT | NOT NULL, FK -> documents(id) ON DELETE CASCADE |
| `version_number` | INTEGER | NOT NULL |
| `latex_source` | TEXT | NOT NULL |
| `prompt_text` | TEXT | NOT NULL, DEFAULT '' |
| `compiled_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| | | UNIQUE(document_id, version_number) |

**extra_questions** -- Interview / application-form questions per application

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `application_id` | TEXT | NOT NULL, FK -> applications(id) ON DELETE CASCADE |
| `question` | TEXT | NOT NULL, DEFAULT '' |
| `answer` | TEXT | NOT NULL, DEFAULT '' |
| `word_cap` | INTEGER | nullable |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 |
| `created_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| `updated_at` | TEXT | NOT NULL, DEFAULT datetime('now') |

**interview_rounds** -- Interview round tracking per application

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `application_id` | TEXT | NOT NULL, FK -> applications(id) ON DELETE CASCADE |
| `round_type` | TEXT | NOT NULL, DEFAULT 'other' |
| `round_number` | INTEGER | NOT NULL, DEFAULT 1 |
| `scheduled_at` | TEXT | nullable |
| `completed_at` | TEXT | nullable |
| `interviewer_names` | TEXT | NOT NULL, DEFAULT '' |
| `location` | TEXT | NOT NULL, DEFAULT '' |
| `status` | TEXT | NOT NULL, DEFAULT 'scheduled' |
| `prep_notes` | TEXT | NOT NULL, DEFAULT '' |
| `debrief_notes` | TEXT | NOT NULL, DEFAULT '' |
| `questions_asked` | TEXT | NOT NULL, DEFAULT '' |
| `went_well` | TEXT | NOT NULL, DEFAULT '' |
| `to_improve` | TEXT | NOT NULL, DEFAULT '' |
| `confidence` | INTEGER | nullable |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 |
| `created_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| `updated_at` | TEXT | NOT NULL, DEFAULT datetime('now') |

**offers** -- Job offer details per application

| Column | Type | Constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `application_id` | TEXT | NOT NULL, FK -> applications(id) ON DELETE CASCADE |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' |
| `base_salary` | REAL | nullable |
| `currency` | TEXT | NOT NULL, DEFAULT 'EUR' |
| `bonus` | TEXT | NOT NULL, DEFAULT '' |
| `equity` | TEXT | NOT NULL, DEFAULT '' |
| `signing_bonus` | TEXT | NOT NULL, DEFAULT '' |
| `benefits` | TEXT | NOT NULL, DEFAULT '' |
| `pto_days` | INTEGER | nullable |
| `remote_policy` | TEXT | NOT NULL, DEFAULT '' |
| `start_date` | TEXT | nullable |
| `expiry_date` | TEXT | nullable |
| `notes` | TEXT | NOT NULL, DEFAULT '' |
| `sort_order` | INTEGER | NOT NULL, DEFAULT 0 |
| `created_at` | TEXT | NOT NULL, DEFAULT datetime('now') |
| `updated_at` | TEXT | NOT NULL, DEFAULT datetime('now') |

### Seeded catalog data

Providers: `openai`, `anthropic`, `groq`, `ollama`

Models (14 total): GPT-4o, GPT-4o mini, GPT-4 Turbo, GPT-3.5 Turbo, Claude Opus 4.6, Claude Sonnet 4.6, Claude Haiku 4.5, Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2 9B, Llama 3.2, Mistral, Phi-3

Provider fields: `openai_api_key`, `anthropic_api_key`, `groq_api_key`, `ollama_base_url`

### Cascade deletes

- Deleting an `application` cascades to: `application_meta`, `documents`, `extra_questions`, `interview_rounds`, `offers`
- Deleting a `document` cascades to: `document_versions`

## Dependencies

- Imports from: `os`, `sqlite3`, `uuid`, `contextlib`, `pathlib`
- Imported by: `jam/server.py` (primary consumer -- all CRUD functions + `init_db`, `get_catalog`, settings functions), `jam/generation.py` (imports `get_all_settings`)

## Testing

- File: `tests/unit/test_db.py`
- Mock targets: Tests use an in-memory or temporary SQLite database (via `db_path` parameter) -- no mocking needed; the `db_path` parameter on every public function enables test isolation
- Pattern: Each test calls `init_db(db_path=tmp_path)` to create a fresh database, then exercises CRUD functions directly

## Migration Safety Rules

From CLAUDE.md -- these rules MUST be followed when writing migrations:

1. **Never use `executescript()`** -- it issues an implicit COMMIT, bypassing the `_connect()` context manager's transaction safety
2. **All migrations must be atomic** -- run inside a single `_connect()` transaction (use individual `conn.execute()` calls)
3. **Table rebuilds require row-count verification** -- when doing SQLite table rebuilds (rename -> create -> copy -> drop), assert that the row count matches before dropping the old table
4. **Never drop or rename tables outside a transaction**
5. **Test migrations with existing data** -- unit tests should seed data first, run the migration, and assert data is preserved

The existing `_migrate_applications_table` demonstrates all of these patterns.

## Known Limitations

- No connection pooling -- each public function call opens and closes its own connection via `_connect()`
- `update_application` does not auto-set `updated_at` (caller must include it in `fields`), unlike `update_document`, `update_extra_question`, `update_interview_round`, and `update_offer` which auto-set `updated_at = datetime('now')`
- Dynamic SQL in update functions (`set_clause = ", ".join(...)`) -- field names come from caller; no column allowlist validation
- `create_application` requires caller to generate the UUID and timestamps; other create functions (`create_document`, `create_extra_question`, etc.) auto-generate UUIDs and timestamps internally
- No pagination on list functions -- all rows returned
- The `_seed_catalog` function is idempotent (checks `COUNT(*) > 0` on providers) but does not handle partial seeds or catalog updates
