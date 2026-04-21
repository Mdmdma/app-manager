# server-api Knowledge
<!-- source: jam/server.py -->
<!-- hash: dab8b157f540 -->
<!-- updated: 2026-04-21 -->

## Public API

### Endpoints

| Method | Path | Response | Purpose |
|---|---|---|---|
| GET | `/` | HTML | Serve main web UI at site root (on `app` directly, not router) |
| GET | `/api/v1/` | HTML | Serve main web UI (legacy, via router) |
| GET | `/api/v1/health` | JSON `{status: "ok", kb_status: "ok"\|"unreachable", cliproxy_status: "ok"\|"unreachable"}` | Health check -- reports jam status, kb and CLIProxy reachability |
| GET | `/api/v1/applications` | `list[Application]` | List all applications |
| POST | `/api/v1/applications` | `Application` (201) | Create a new application (auto-creates CV + Cover Letter docs) |
| POST | `/api/v1/applications/from-url` | `ImportFromUrlResponse` (201) | Import job posting from URL via LLM (auto-creates CV + Cover Letter docs) |
| POST | `/api/v1/applications/from-text` | `ImportFromTextResponse` (201) | Import job posting from pasted JD text via LLM (auto-creates CV + Cover Letter docs) |
| GET | `/api/v1/applications/{app_id}` | `Application` | Get application by UUID |
| PUT | `/api/v1/applications/{app_id}` | `Application` | Update application fields |
| DELETE | `/api/v1/applications/{app_id}` | 204 No Content | Delete an application |
| GET | `/api/v1/applications/{app_id}/documents` | `list[DocumentResponse]` | List documents for app (optional `?doc_type=cv\|cover_letter`) |
| POST | `/api/v1/applications/{app_id}/documents` | `DocumentResponse` (201) | Create a new document for app |
| GET | `/api/v1/documents/{doc_id}` | `DocumentResponse` | Get a single document |
| PUT | `/api/v1/documents/{doc_id}` | `DocumentResponse` | Update document fields |
| DELETE | `/api/v1/documents/{doc_id}` | 204 No Content | Delete a document |
| POST | `/api/v1/documents/{doc_id}/compile` | PDF bytes (`application/pdf`) | Compile LaTeX via tectonic, store in cache (no version created) |
| GET | `/api/v1/documents/{doc_id}/pdf` | PDF bytes (`application/pdf`) | Retrieve the most recently compiled PDF from cache (404 if not yet compiled) |
| GET | `/api/v1/documents/{doc_id}/versions` | `list[DocumentVersionResponse]` | List version history for document |
| POST | `/api/v1/documents/versions/{version_id}/compile` | PDF bytes (`application/pdf`) | Re-compile an old version to PDF |
| POST | `/api/v1/documents/{doc_id}/generate` | SSE stream (`text/event-stream`) | Stream agentic document generation progress |
| GET | `/api/v1/catalog` | JSON | LLM provider/model catalog |
| GET | `/api/v1/settings` | JSON | Retrieve current settings (keys masked) |
| POST | `/api/v1/settings` | JSON `{ok, saved}` | Persist settings to database |
| GET | `/api/v1/templates/defaults` | JSON `{cv, cover_letter}` | Return built-in default LaTeX templates |
| GET | `/api/v1/prompts/defaults` | JSON | Return built-in default system prompts (9 keys: 3 shared + 6 doc-type-specific; shared include `prompt_generate_prep_guide`) |
| GET | `/api/v1/kb/namespaces` | JSON list | Proxy: list all namespaces from the kb knowledge base |
| GET | `/api/v1/applications/{app_id}/interviews` | `list[InterviewRoundResponse]` | List all interview rounds for an application |
| POST | `/api/v1/applications/{app_id}/interviews` | `InterviewRoundResponse` (201) | Create a new interview round |
| PUT | `/api/v1/interviews/{interview_id}` | `InterviewRoundResponse` | Update an interview round |
| DELETE | `/api/v1/interviews/{interview_id}` | 204 No Content | Delete an interview round |
| GET | `/api/v1/interviews/{interview_id}/prep-guide` | `PrepGuideResponse` | Return stored interview prep guide (all fields None/empty if never generated — never 404s on missing guide) |
| PUT | `/api/v1/interviews/{interview_id}/prep-guide` | `PrepGuideResponse` | Save user edits to markdown; keeps other fields intact |
| POST | `/api/v1/interviews/{interview_id}/prep-guide/generate` | SSE `text/event-stream` | Stream prep-guide generation progress; 400 if `llm_provider` not in (`anthropic`, `cliproxy`) |
| GET | `/api/v1/applications/{app_id}/offers` | `list[OfferResponse]` | List all offers for an application |
| POST | `/api/v1/applications/{app_id}/offers` | `OfferResponse` (201) | Create a new offer |
| PUT | `/api/v1/offers/{offer_id}` | `OfferResponse` | Update an offer |
| DELETE | `/api/v1/offers/{offer_id}` | 204 No Content | Delete an offer |
| GET | `/api/v1/applications/{app_id}/rejections` | `list[RejectionResponse]` | List all rejections for an application (normally 0 or 1) |
| POST | `/api/v1/applications/{app_id}/rejections` | `RejectionResponse` (201) | Manually create a rejection record |
| PUT | `/api/v1/rejections/{rejection_id}` | `RejectionResponse` | Update a rejection |
| DELETE | `/api/v1/rejections/{rejection_id}` | 204 No Content | Delete a rejection |
| POST | `/api/v1/applications/{app_id}/email/ingest` | `EmailIngestResponse` (201) | Paste an email → LLM classifies as `interview_invite` / `rejection` / `unknown`; creates interview_round or rejection (flipping app status to `rejected` in the latter case); 422 on unknown or LLM failure |
| GET | `/api/v1/gmail/auth-url` | JSON `{url}` | Return Gmail OAuth authorization URL |
| GET | `/api/v1/gmail/status` | JSON `{connected, email}` | Return Gmail connection status |
| POST | `/api/v1/gmail/disconnect` | JSON `{ok}` | Clear stored Gmail tokens |
| GET | `/gmail/callback` | Redirect | Exchange OAuth code, store tokens, redirect to settings |
| GET | `/api/v1/ms_graph/auth-url` | JSON `{url}` | Return Microsoft Graph OAuth authorization URL |
| GET | `/api/v1/ms_graph/status` | `MSGraphSettingsResponse` | `{connected: bool, user_email: str}` |
| POST | `/api/v1/ms_graph/disconnect` | JSON `{disconnected: true, rounds_cleared: int}` | Clear stored Graph tokens + NULL every `interview_rounds.graph_event_id` |
| POST | `/api/v1/ms_graph/sync` | JSON `{synced: int, errors: int}` | Iterate all scheduled rounds across all applications, push each to Graph via `_sync_round_to_graph` |
| GET | `/ms_graph/callback` | Redirect | Exchange OAuth code, persist tokens, redirect to `/?ms_graph_connected=1` |

### App configuration
- Title: "jam API"
- Version: "0.1.0"
- CORS: allow all origins, methods, headers
- Router prefix: `/api/v1`

## Key Constants / Schema

### Module-level constants
- `DEFAULT_CV_TEMPLATE` -- raw LaTeX string: article-class CV scaffold with 3-minipage header (headshot via `\includegraphics{photo.png}`, name/role, contact links) + sections for Summary, Experience, Education, Skills; requires `graphicx` package
- `DEFAULT_COVER_LETTER_TEMPLATE` -- raw LaTeX string: letter-class cover letter scaffold with opening/body/closing paragraphs + `\fromsig{\includegraphics[height=1.2cm]{signature.png}}` after closing; requires `graphicx` package
- `_ENV_MAP` -- dict mapping settings key -> environment variable name (for keys that set env vars on save)
- `_PLAIN_KEYS` -- set of settings keys returned as-is (not masked): includes all prompt keys (shared + doc-type-specific with colon format), `llm_provider`, `llm_model`, `ollama_base_url`, `cliproxy_base_url`, `cv_latex_template`, `cover_letter_latex_template`, `gmail_client_id`, `gmail_user_email`, `kb_retrieval_*`, `personal_*`, `step_model_*`, `search_enrichment_enabled`
- `_BOOL_PLAIN_KEYS` -- subset of `_PLAIN_KEYS` whose DB-stored string values (`"1"`/`"0"`/`"true"`/`"false"`) are coerced to JSON `bool` on GET and stringified back to `"1"`/`"0"` on POST. Currently: `{"search_enrichment_enabled"}`
- **Per-step model validation**: `save_settings_endpoint` validates `step_model_*` values against the catalog's model IDs (format: `"provider:model_id"`). Empty string clears the override. Values not in `_ENV_MAP` (read from DB directly by generation module).
- `_pdf_cache: dict[str, bytes]` -- in-memory cache mapping document IDs to their most recently compiled PDF bytes

### Helper functions
- `_auto_create_documents(app_id: str) -> None` -- creates CV and Cover Letter documents for a new application using templates from settings (falls back to `DEFAULT_CV_TEMPLATE` / `DEFAULT_COVER_LETTER_TEMPLATE`)
- `async _sync_round_to_graph(round_id: str, settings=None)` -- idempotent Outlook push for one interview round. Loads round + parent application, upserts via `msgraph_client.upsert_event` when `status='scheduled'` and `scheduled_at` is set, writes the returned event id back via `db_update_interview_round(id, {"graph_event_id": ...})`. If the round becomes ineligible and already has a `graph_event_id`, deletes the Graph event and clears the id. Skips entirely (no exception) if `ms_graph_refresh_token` is empty. Swallows ALL exceptions and logs warnings — NEVER raises (runs in a `BackgroundTask`).
- `async _delete_graph_event_by_id(graph_event_id: str, settings=None)` -- thin wrapper around `msgraph_client.delete_event` that swallows exceptions. Called from the DELETE `/interviews/{id}` handler after successful DB delete.
- `_fetch_page_text(url)` -- async; fetches URL, dispatches on Content-Type: PDF (via pymupdf/fitz), plain-text, or HTML (strips tags); returns `(text, content_kind)`. Timeout 60s.
- `_parse_tectonic_error(raw_stderr)` -- extracts most useful error line from tectonic output
- `_compile_latex(latex_source)` -- async; compiles LaTeX to PDF bytes via tectonic subprocess; raises HTTPException on failure
- `_inject_pdf_metadata(pdf_bytes, title, author)` -- opens PDF with pymupdf/fitz, sets metadata fields (title, author), returns modified bytes
- `_build_pdf_metadata(position)` -- reads `personal_full_name` from stored settings, assembles `{title, author}` dict

### Pydantic Models
- `ApplicationStatus` -- str enum: `not_applied_yet`, `applied`, `screening`, `interviewing`, `offered`, `rejected`, `accepted`, `withdrawn`
- `WorkMode` -- str enum: `remote`, `hybrid`, `onsite`
- `ApplicationCreate` -- `company`, `position`, `status`, `url`, `notes`, `salary_range`, `location`, `work_mode`, `contact_person`, `applied_date`, `opening_date`, `closing_date`, `description`, `full_text`
- `ApplicationUpdate` -- all optional: same fields as ApplicationCreate
- `Application` -- domain model: `id` (UUID), all fields above plus `created_at`, `updated_at`
- `ImportFromUrlRequest` -- `url: str` (min_length=1, max_length=2048)
- `ImportFromUrlResponse` -- `application: Application`, `extraction: dict`, `kb_ingested: bool`
- `ImportFromTextRequest` -- `text: str` (min_length=1, with `@field_validator` rejecting whitespace-only input)
- `ImportFromTextResponse` -- type alias for `ImportFromUrlResponse` (identical shape)
- `SettingsRequest` -- includes `search_enrichment_enabled: Optional[bool]` (toggle gating Claude's web_search tool for JD extraction); `model_config = ConfigDict(populate_by_name=True)`. Fields: `openai_api_key`, `anthropic_api_key`, `groq_api_key`, `ollama_base_url`, `cliproxy_base_url`, `cliproxy_api_key`, `llm_provider`, `llm_model`, `cv_latex_template`, `cover_letter_latex_template`, `gmail_client_id`, `gmail_client_secret`, `gmail_refresh_token`, `gmail_user_email`, `kb_retrieval_namespaces` (str), `kb_retrieval_n_results` (int), `kb_retrieval_padding` (int), `kb_include_namespaces` (str), `personal_full_name`, `personal_email`, `personal_phone`, `personal_website`, `personal_address`, `personal_photo`, `personal_signature`, `prompt_analyze_fit`, `prompt_analyze_compress`, `prompt_generate_first_cv` (alias `prompt_generate_first:cv`), `prompt_generate_first_cl` (alias `prompt_generate_first:cover_letter`), `prompt_generate_revise_cv` (alias `prompt_generate_revise:cv`), `prompt_generate_revise_cl` (alias `prompt_generate_revise:cover_letter`), `prompt_analyze_quality_cv` (alias `prompt_analyze_quality:cv`), `prompt_analyze_quality_cl` (alias `prompt_analyze_quality:cover_letter`), `step_model_generate_or_revise`, `step_model_analyze_fit`, `step_model_analyze_quality`, `step_model_analyze_compress` -- all optional. `model_dump(by_alias=True)` produces colon-keyed DB keys for doc-type prompts.
- `DocType` -- str enum: `cv`, `cover_letter`
- `DocumentCreate` -- `doc_type: DocType`, `title`, `latex_source`, `prompt_text`
- `DocumentUpdate` -- optional: `title`, `latex_source`, `prompt_text`
- `DocumentResponse` -- `id`, `application_id`, `doc_type`, `title`, `latex_source`, `prompt_text`, `created_at`, `updated_at`
- `DocumentVersionResponse` -- `id`, `document_id`, `version_number`, `latex_source`, `prompt_text`, `compiled_at`
- `GenerateRequest` -- `is_first_generation: bool` (default False), `critique_only: bool` (default False), `fit_feedback: str | None` (default None), `quality_feedback: str | None` (default None)
- `InterviewRoundCreate` -- `round_type`, `round_number`, `scheduled_at`, `scheduled_time`, `completed_at`, `interviewer_names`, `location`, `links`, `status`, `prep_notes`, `debrief_notes`, `questions_asked`, `went_well`, `to_improve`, `confidence`, `sort_order` (`links: str = ""`, newline-separated URLs)
- `InterviewRoundUpdate` -- all optional: same fields as InterviewRoundCreate (incl. `links: Optional[str] = None`)
- `InterviewRoundResponse` -- `id`, `application_id`, plus all InterviewRoundCreate fields plus `created_at`, `updated_at`, `graph_event_id: Optional[str] = None` (Microsoft Graph event id when synced to Outlook)
- `MSGraphSettingsResponse` -- `connected: bool`, `user_email: str = ""`
- `PrepGuideResponse` -- `markdown: str = ""`, `generation_system_prompt: Optional[str] = None`, `generation_user_prompt: Optional[str] = None`, `web_search_log: Optional[str] = None` (JSON-encoded list `[{query,url,title}]`), `thinking_summary: Optional[str] = None`, `last_generated_at: Optional[str] = None`, `created_at: Optional[str] = None`, `updated_at: Optional[str] = None`
- `PrepGuideUpdateRequest` -- `markdown: str`
- `OfferCreate` -- `status`, `base_salary`, `currency`, `bonus`, `equity`, `signing_bonus`, `benefits`, `pto_days`, `remote_policy`, `start_date`, `expiry_date`, `notes`, `sort_order`
- `OfferUpdate` -- all optional: same fields as OfferCreate
- `OfferResponse` -- `id`, `application_id`, plus all OfferCreate fields plus `created_at`, `updated_at`
- `RejectionCreate` -- all defaults match DB defaults: `summary=""`, `reasons=""`, `links=""`, `raw_email=""`, `received_at=None`, `followup_status="none"`, `followup_notes=""`
- `RejectionUpdate` -- all optional (Optional[str]/None defaults)
- `RejectionResponse` -- `id`, `application_id`, `summary`, `reasons`, `links`, `raw_email`, `received_at`, `followup_status`, `followup_notes`, `created_at`, `updated_at`
- `EmailIngestRequest` -- `email_text: str` with `min_length=20`
- `EmailIngestResponse` -- `kind`, `confidence`, `interview: InterviewRoundResponse \| None`, `rejection: RejectionResponse \| None`, `extraction: dict` (raw LLM output echoed for client-side fallback/debug)

### Auto-create documents on application creation
`POST /applications`, `POST /applications/from-url`, and `POST /applications/from-text` all call `_auto_create_documents(app_id)` after inserting the application row. This creates two documents (CV + Cover Letter) pre-populated with LaTeX templates from stored settings or built-in defaults.

### import_from_text flow
- Strips `req.text`; returns 400 if `len(text) < 50` (treats very short input as invalid).
- Calls `extract_job_info(text, settings)` directly (no URL fetch); returns 400 on LLM failure.
- Creates application with `url=None` and `full_text=<pasted text>`; extracted `location`, `salary_range`, `description` fill their dedicated columns (requirements + description also go into `notes`, mirroring the URL path).
- KB ingest via `ingest_text(text, "", settings)` (empty `source_url` — kb falls back to `document.txt` filename); failures are non-fatal (`kb_ingested=False`).

### Compile endpoint logic
- Writes LaTeX source to temp `.tex` file
- Runs `tectonic <file> --untrusted` as async subprocess
- **Injects PDF metadata** via `_inject_pdf_metadata` (title=position, author=personal_full_name)
- Returns PDF bytes with `Content-Type: application/pdf`
- **Stores PDF bytes in `_pdf_cache[doc_id]`** for retrieval via GET endpoint
- **Does NOT create a version** -- versions are only created by the generate endpoint
- Returns 503 if tectonic not installed, 422 if compilation fails

### PDF cache endpoint logic
- `GET /documents/{doc_id}/pdf` retrieves the most recently compiled PDF from the in-memory cache
- Returns 404 if document has never been compiled
- Avoids blob URL issues in Vivaldi by serving PDFs from a regular HTTP endpoint

### Generate endpoint logic (SSE)
- `POST /documents/{doc_id}/generate` streams progress via Server-Sent Events
- Uses `generation_graph` from `jam.generation` (LangGraph)
- **Feedback precedence** (3-way): request value if not None → `""` if first gen → DB value
- `compress_feedback` always initialised to `""` (internal to compact loop)
- Initialises `compact_iteration: 0` and `max_compact_iterations: 3` in state
- SSE streams ALL new events per superstep (tracks `sent_count`); each `data:` line is JSON with `node` and `status` fields
- Final event has `node: "done"` with `latex`, `page_count`, `fit_feedback`, `quality_feedback`, `error` (no `compress_feedback`)
- **Persists feedback to DB** after generation: fit_feedback, quality_feedback, compress_feedback, last_page_count
- Persists final LaTeX to DB and stores PDF in cache on success

### Prompt defaults endpoint
- `GET /prompts/defaults` calls `get_all_prompt_defaults()` from `jam.generation` and returns 9 keys: 3 shared (`prompt_analyze_fit`, `prompt_analyze_compress`, `prompt_generate_prep_guide`) + 6 doc-type-specific (e.g. `prompt_generate_first:cv`, `prompt_generate_first:cover_letter`)

### Prep guide endpoints
- `GET /interviews/{id}/prep-guide` — 404 if interview missing; returns a `PrepGuideResponse` with all fields None/empty if no guide row exists (never 404s on missing guide).
- `PUT /interviews/{id}/prep-guide` — accepts `{"markdown": "..."}`, calls `db_upsert_prep_guide(interview_id, markdown_source=body.markdown)`; preserves existing `generation_*`, `web_search_log`, `thinking_summary` (helper leaves unset kwargs untouched on update).
- `POST /interviews/{id}/prep-guide/generate` — SSE. Gates on `settings.llm_provider in ("anthropic", "cliproxy")` (400 otherwise). Builds a `PrepGuideState` from interview + application + first CV/cover-letter documents, streams events from `run_prep_guide_graph`. Each SSE frame is `data: <json>\n\n`. Final event: `{node:"done", markdown, generation_system_prompt, generation_user_prompt, web_search_log, thinking_summary, error}`.

### Microsoft Graph (Outlook Calendar) endpoints
- `GET /ms_graph/auth-url` — returns `{url: <msgraph_client.get_auth_url()>}`.
- `GET /ms_graph/callback?code=...` — calls `await msgraph_client.exchange_code(code)`, persists `ms_graph_refresh_token`, `ms_graph_access_token`, `ms_graph_token_expires_at`, `ms_graph_user_email` via `set_settings_batch` AND writes the same keys to `os.environ` (dual-write, mirrors Gmail callback). Returns `RedirectResponse("/?ms_graph_connected=1")`.
- `GET /ms_graph/status` — `{connected: bool(settings.ms_graph_refresh_token), user_email: settings.ms_graph_user_email}`.
- `POST /ms_graph/disconnect` — clears the 4 token settings via `delete_setting`, pops matching `os.environ` keys, iterates every round with a non-null `graph_event_id` and NULLs it via `db_update_interview_round(id, {"graph_event_id": None})`. Returns `{disconnected: True, rounds_cleared: int}`. Events already in Outlook are left in place by design.
- `POST /ms_graph/sync` — walks `db_list_applications()` → `db_list_interview_rounds(app_id)` and calls `_sync_round_to_graph(round_id)` for every round with `status='scheduled'` and non-empty `scheduled_at`. Counts `synced` and `errors`.

### Interview CRUD → Graph sync hooks
- `POST /applications/{app_id}/interviews` and `PUT /interviews/{id}` accept `background_tasks: BackgroundTasks` and schedule `_sync_round_to_graph(round_id)` after the DB write. The helper itself handles the eligibility transition (round becomes non-scheduled → delete Graph event, clear id).
- `DELETE /interviews/{id}` captures `graph_event_id` before deletion and schedules `_delete_graph_event_by_id(graph_event_id)` if it was set.
- Background tasks run after the response is sent; in the pytest `ASGITransport` client they execute synchronously before the test regains control.

### KB namespaces proxy
- `GET /kb/namespaces` proxies `{kb_api_url}/namespaces` -- returns the JSON list on success, empty list `[]` on any error

### SQLite persistence (via jam.db)
- Application CRUD: `db_create_application`, `db_get_application`, `db_list_applications`, `db_update_application`, `db_delete_application`
- Document CRUD: `db_create_document`, `db_get_document`, `db_list_documents`, `db_update_document`, `db_delete_document`
- Version CRUD: `db_create_version`, `db_list_versions`, `db_get_version`
- Interview round CRUD: `db_create_interview_round`, `db_list_interview_rounds`, `db_get_interview_round`, `db_update_interview_round`, `db_delete_interview_round`
- Offer CRUD: `db_create_offer`, `db_list_offers`, `db_get_offer`, `db_update_offer`, `db_delete_offer`
- Rejection CRUD: `db_create_rejection`, `db_list_rejections`, `db_get_rejection`, `db_update_rejection`, `db_delete_rejection`

### Email ingest endpoint logic (`POST /applications/{app_id}/email/ingest`)

1. 404 if `db_get_application(app_id)` is missing.
2. Strip + length-check `email_text` (Pydantic enforces `min_length=20`).
3. `await extract_email_info(text, Settings())`; any exception → 422 with detail `"LLM extraction failed: ..."`.
4. Branch on `info["kind"]`:
   - `"interview_invite"`: filter non-null fields from `info["interview"]` (`round_type`, `scheduled_at`, `scheduled_time`, `interviewer_names`, `location`, `prep_notes`); join `info["interview"]["links"]` with `"\n"`; call `db_create_interview_round(application_id=app_id, status="scheduled", links=..., **non_null)`. **Does not** change application status.
   - `"rejection"`: call `db_create_rejection(application_id=app_id, summary, reasons, links="\n".join(...), raw_email=text, received_at)`; then `db_update_application(app_id, {"status": "rejected", "updated_at": <now>})`.
   - `"unknown"` (or anything else): raise 422 with `detail={"message": "Could not classify email as interview or rejection", "extraction": info}` so the client can fall back to manual entry.
5. Return `EmailIngestResponse` with the matching field populated; `extraction` always echoes the raw LLM dict.

### Field behaviour notes
- `import_from_url`: `location` and `salary_range` extracted by LLM are stored in their dedicated columns; they are NOT concatenated into `notes`. Only `requirements` and `description` go into `notes`.
- `update_application`: both `status` (ApplicationStatus enum) and `work_mode` (WorkMode enum) are converted to `.value` before db storage.

## Dependencies
- Imports from: `fastapi` (incl. `BackgroundTasks`), `fastapi.middleware.cors`, `fastapi.responses` (incl. `RedirectResponse`), `pydantic`, `httpx`, `asyncio`, `logging`, `shutil`, `tempfile`, `jam.html_page`, `jam.db`, `jam.llm`, `jam.kb_client` (incl. `close_client`), `jam.generation`, `jam.gmail_client`, `jam.msgraph_client` (as `msgraph_client`), `jam.config`
- Imported by: `scripts/serve.py` (via `jam.server:app`)

## Testing
- Unit files: `tests/unit/test_server.py`, `tests/unit/test_fetch_page_text.py`
- Integration file: `tests/integration/test_server_integration.py`
- Mock targets (patch at `jam.server.*`): `get_catalog`, `get_all_settings`, `set_setting`, `set_settings_batch`, `_fetch_page_text`, `extract_job_info`, `extract_email_info`, `ingest_url`, `ingest_text`, `db_create_application`, `db_get_application`, `db_list_applications`, `db_update_application`, `db_delete_application`, `db_create_document`, `db_get_document`, `db_list_documents`, `db_update_document`, `db_delete_document`, `db_create_version`, `db_list_versions`, `db_get_version`, `db_create_interview_round`, `db_list_interview_rounds`, `db_get_interview_round`, `db_update_interview_round`, `db_delete_interview_round`, `db_create_offer`, `db_list_offers`, `db_get_offer`, `db_update_offer`, `db_delete_offer`, `db_create_rejection`, `db_list_rejections`, `db_get_rejection`, `db_update_rejection`, `db_delete_rejection`, `shutil.which`, `asyncio.create_subprocess_exec`, `httpx.AsyncClient`
- Uses `httpx.ASGITransport` for async test client
- `isolated_db` autouse fixture creates a per-test SQLite db and patches all `db_*`, `get_all_settings`, `set_setting`, `set_settings_batch`, and `get_catalog` functions in `jam.server` to use it; yields `db_path` for tests that need to seed data

## Database migration safety
- **Never use `executescript()`** -- it auto-commits and breaks `_connect()` transaction safety.
- Use individual `conn.execute()` calls so migrations are atomic (rollback on failure).
- Table rebuilds (rename -> create -> copy -> drop) must verify row counts before dropping the old table.

## Known Limitations
- `on_event("startup")`/`on_event("shutdown")` are deprecated; should migrate to `lifespan` handler. Shutdown hook calls `close_client()` from `jam.kb_client`.
- `Settings()` is instantiated per-request in `import_from_url`, `health`, `list_kb_namespaces` (no caching)
- Compile endpoint requires `tectonic` system binary installed
- PDF cache is in-memory only; PDFs are lost on server restart
