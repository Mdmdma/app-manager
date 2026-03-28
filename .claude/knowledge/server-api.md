# server-api Knowledge
<!-- source: jam/server.py -->
<!-- hash: f40d665335a6 -->
<!-- updated: 2026-03-28 -->

## Public API

### Endpoints

| Method | Path | Response | Purpose |
|---|---|---|---|
| GET | `/api/v1/` | HTML | Serve main web UI (HTML_PAGE) |
| GET | `/api/v1/health` | JSON `{status: "ok", kb_status: "ok"\|"unreachable"}` | Health check — reports jam status and kb reachability |
| GET | `/api/v1/applications` | `list[Application]` | List all applications |
| POST | `/api/v1/applications` | `Application` (201) | Create a new application (auto-creates CV + Cover Letter docs) |
| POST | `/api/v1/applications/from-url` | `ImportFromUrlResponse` (201) | Import job posting from URL via LLM (auto-creates CV + Cover Letter docs) |
| GET | `/api/v1/applications/{app_id}` | `Application` | Get application by UUID |
| PUT | `/api/v1/applications/{app_id}` | `Application` | Update application fields |
| DELETE | `/api/v1/applications/{app_id}` | 204 No Content | Delete an application |
| GET | `/api/v1/applications/{app_id}/documents` | `list[DocumentResponse]` | List documents for app (optional `?doc_type=cv\|cover_letter`) |
| POST | `/api/v1/applications/{app_id}/documents` | `DocumentResponse` (201) | Create a new document for app |
| GET | `/api/v1/documents/{doc_id}` | `DocumentResponse` | Get a single document |
| PUT | `/api/v1/documents/{doc_id}` | `DocumentResponse` | Update document fields |
| DELETE | `/api/v1/documents/{doc_id}` | 204 No Content | Delete a document |
| POST | `/api/v1/documents/{doc_id}/compile` | PDF bytes (`application/pdf`) | Compile LaTeX via tectonic, save version, store in cache |
| GET | `/api/v1/documents/{doc_id}/pdf` | PDF bytes (`application/pdf`) | Retrieve the most recently compiled PDF from cache (404 if not yet compiled) |
| GET | `/api/v1/documents/{doc_id}/versions` | `list[DocumentVersionResponse]` | List version history for document |
| POST | `/api/v1/documents/versions/{version_id}/compile` | PDF bytes (`application/pdf`) | Re-compile an old version to PDF |
| POST | `/api/v1/documents/{doc_id}/generate` | SSE stream (`text/event-stream`) | Stream agentic document generation progress |
| GET | `/api/v1/catalog` | JSON | LLM provider/model catalog |
| GET | `/api/v1/settings` | JSON | Retrieve current settings (keys masked) |
| POST | `/api/v1/settings` | JSON `{ok, saved}` | Persist settings to database |
| GET | `/api/v1/templates/defaults` | JSON `{cv, cover_letter}` | Return built-in default LaTeX templates |
| GET | `/api/v1/kb/namespaces` | JSON list | Proxy: list all namespaces from the kb knowledge base |
| GET | `/api/v1/gmail/auth-url` | JSON `{url}` | Return Gmail OAuth authorization URL |
| GET | `/api/v1/gmail/status` | JSON `{connected, email}` | Return Gmail connection status |
| POST | `/api/v1/gmail/disconnect` | JSON `{ok}` | Clear stored Gmail tokens |
| GET | `/gmail/callback` | Redirect | Exchange OAuth code, store tokens, redirect to settings |

### App configuration
- Title: "jam API"
- Version: "0.1.0"
- CORS: allow all origins, methods, headers
- Router prefix: `/api/v1`

## Key Constants / Schema

### Module-level constants
- `DEFAULT_CV_TEMPLATE` — raw LaTeX string: article-class CV scaffold with sections for Experience, Education, Skills
- `DEFAULT_COVER_LETTER_TEMPLATE` — raw LaTeX string: letter-class cover letter scaffold with opening/body/closing
- `_ENV_MAP` — dict mapping settings key → environment variable name (for keys that set env vars on save)
- `_PLAIN_KEYS` — set of settings keys returned as-is (not masked): `llm_provider`, `llm_model`, `ollama_base_url`, `cv_latex_template`, `cover_letter_latex_template`, `gmail_client_id`, `gmail_user_email`, `kb_retrieval_namespaces`, `kb_retrieval_n_results`, `kb_retrieval_padding`, `kb_include_namespaces`
- `_pdf_cache: dict[str, bytes]` — in-memory cache mapping document IDs to their most recently compiled PDF bytes

### Helper functions
- `_auto_create_documents(app_id: str) -> None` — creates CV and Cover Letter documents for a new application using templates from settings (falls back to `DEFAULT_CV_TEMPLATE` / `DEFAULT_COVER_LETTER_TEMPLATE`)
- `_fetch_page_text(url)` — async; fetches URL, dispatches on Content-Type: PDF (via pymupdf/fitz), plain-text, or HTML (strips tags); returns `(text, content_kind)`. Timeout 60s.
- `_parse_tectonic_error(raw_stderr)` — extracts most useful error line from tectonic output
- `_compile_latex(latex_source)` — async; compiles LaTeX to PDF bytes via tectonic subprocess; raises HTTPException on failure

### Pydantic Models
- `ApplicationStatus` — str enum: `not_applied_yet`, `applied`, `screening`, `interviewing`, `offered`, `rejected`, `accepted`, `withdrawn`
- `WorkMode` — str enum: `remote`, `hybrid`, `onsite`
- `ApplicationCreate` — `company`, `position`, `status`, `url`, `notes`, `salary_range`, `location`, `work_mode`, `contact_person`, `applied_date`, `opening_date`, `closing_date`, `description`, `full_text`
- `ApplicationUpdate` — all optional: same fields as ApplicationCreate
- `Application` — domain model: `id` (UUID), all fields above plus `created_at`, `updated_at`
- `ImportFromUrlRequest` — `url: str` (min_length=1, max_length=2048)
- `ImportFromUrlResponse` — `application: Application`, `extraction: dict`, `kb_ingested: bool`
- `SettingsRequest` — `openai_api_key`, `anthropic_api_key`, `groq_api_key`, `ollama_base_url`, `llm_provider`, `llm_model`, `cv_latex_template`, `cover_letter_latex_template`, `gmail_client_id`, `gmail_client_secret`, `gmail_refresh_token`, `gmail_user_email`, `kb_retrieval_namespaces` (str), `kb_retrieval_n_results` (int), `kb_retrieval_padding` (int), `kb_include_namespaces` (str) — all optional
- `DocType` — str enum: `cv`, `cover_letter`
- `DocumentCreate` — `doc_type: DocType`, `title`, `latex_source`, `prompt_text`
- `DocumentUpdate` — optional: `title`, `latex_source`, `prompt_text`
- `DocumentResponse` — `id`, `application_id`, `doc_type`, `title`, `latex_source`, `prompt_text`, `created_at`, `updated_at`
- `DocumentVersionResponse` — `id`, `document_id`, `version_number`, `latex_source`, `prompt_text`, `compiled_at`
- `GenerateRequest` — `is_first_generation: bool` (default False)

### Auto-create documents on application creation
Both `POST /applications` and `POST /applications/from-url` call `_auto_create_documents(app_id)` after inserting the application row. This creates two documents (CV + Cover Letter) pre-populated with LaTeX templates from stored settings or built-in defaults.

### Compile endpoint logic
- Writes LaTeX source to temp `.tex` file
- Runs `tectonic <file> --untrusted` as async subprocess
- Returns PDF bytes with `Content-Type: application/pdf`
- **Stores PDF bytes in `_pdf_cache[doc_id]`** for retrieval via GET endpoint
- Auto-saves a version snapshot (`db_create_version`) on successful compile
- Returns 503 if tectonic not installed, 422 if compilation fails

### PDF cache endpoint logic
- `GET /documents/{doc_id}/pdf` retrieves the most recently compiled PDF from the in-memory cache
- Returns 404 if document has never been compiled
- Avoids blob URL issues in Vivaldi by serving PDFs from a regular HTTP endpoint

### Generate endpoint logic (SSE)
- `POST /documents/{doc_id}/generate` streams progress via Server-Sent Events
- Uses `generation_graph` from `jam.generation` (LangGraph)
- Each SSE `data:` line is JSON with `node` and `status` fields
- Final event has `node: "done"` with `latex`, `page_count`, `fit_feedback`, `quality_feedback`, `error`
- Persists final LaTeX to DB and stores PDF in cache on success

### KB namespaces proxy
- `GET /kb/namespaces` proxies `{kb_api_url}/namespaces` — returns the JSON list on success, empty list `[]` on any error

### SQLite persistence (via jam.db)
- Application CRUD: `db_create_application`, `db_get_application`, `db_list_applications`, `db_update_application`, `db_delete_application`
- Document CRUD: `db_create_document`, `db_get_document`, `db_list_documents`, `db_update_document`, `db_delete_document`
- Version CRUD: `db_create_version`, `db_list_versions`, `db_get_version`

### Field behaviour notes
- `import_from_url`: `location` and `salary_range` extracted by LLM are stored in their dedicated columns; they are NOT concatenated into `notes`. Only `requirements` and `description` go into `notes`.
- `update_application`: both `status` (ApplicationStatus enum) and `work_mode` (WorkMode enum) are converted to `.value` before db storage.

## Dependencies
- Imports from: `fastapi`, `fastapi.middleware.cors`, `fastapi.responses`, `pydantic`, `httpx`, `asyncio`, `shutil`, `tempfile`, `jam.html_page`, `jam.db`, `jam.llm`, `jam.kb_client`, `jam.generation`, `jam.gmail_client`, `jam.config`
- Imported by: `scripts/serve.py` (via `jam.server:app`)

## Testing
- Unit files: `tests/unit/test_server.py`, `tests/unit/test_fetch_page_text.py`
- Integration file: `tests/integration/test_server_integration.py`
- Mock targets (patch at `jam.server.*`): `get_catalog`, `get_all_settings`, `set_setting`, `set_settings_batch`, `_fetch_page_text`, `extract_job_info`, `ingest_url`, `ingest_text`, `db_create_application`, `db_get_application`, `db_list_applications`, `db_update_application`, `db_delete_application`, `db_create_document`, `db_get_document`, `db_list_documents`, `db_update_document`, `db_delete_document`, `db_create_version`, `db_list_versions`, `db_get_version`, `shutil.which`, `asyncio.create_subprocess_exec`, `httpx.AsyncClient`
- Uses `httpx.ASGITransport` for async test client
- `isolated_db` autouse fixture creates a per-test SQLite db and patches all `db_*`, `get_all_settings`, `set_setting`, `set_settings_batch`, and `get_catalog` functions in `jam.server` to use it; yields `db_path` for tests that need to seed data

## Database migration safety
- **Never use `executescript()`** — it auto-commits and breaks `_connect()` transaction safety.
- Use individual `conn.execute()` calls so migrations are atomic (rollback on failure).
- Table rebuilds (rename → create → copy → drop) must verify row counts before dropping the old table.

## Known Limitations
- `on_event("startup")` is deprecated; should migrate to `lifespan` handler
- `Settings()` is instantiated per-request in `import_from_url`, `health`, `list_kb_namespaces` (no caching)
- Compile endpoint requires `tectonic` system binary installed
- PDF cache is in-memory only; PDFs are lost on server restart
