# clients Knowledge
<!-- source: jam/llm.py, jam/kb_client.py, jam/gmail_client.py, jam/msgraph_client.py -->
<!-- hash: d95f1804d429 -->
<!-- updated: 2026-04-21 -->

## llm.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `llm_call` | `async (system: str, user: str, settings: Settings \| None = None, *, provider: str \| None = None, model: str \| None = None, tools: list \| None = None) -> str` | Generic LLM call dispatching to configured provider; optional `provider`/`model`/`tools` keyword args. `tools` is honored for `anthropic` and `cliproxy` (passed through to Claude); silently dropped for OpenAI-compatible providers |
| `llm_call_with_trace` | `async (system: str, user: str, settings: Settings \| None = None, *, provider: str \| None = None, model: str \| None = None, tools: list \| None = None, thinking_budget: int \| None = None) -> LLMTraceResult` | Anthropic/cliproxy-only sibling of `llm_call` that returns `{text, thinking, search_log}`. Raises `ValueError` for other providers. When `thinking_budget` is set, adds `thinking={type:"enabled", budget_tokens}`, forces `temperature=1`, sets `max_tokens=max(16384, budget+8192)`. Parses `thinking` + `server_tool_use`/`web_search_tool_result` blocks into `search_log` entries `{query,url,title}` |
| `_web_search_tool` | `(max_uses: int = 3) -> dict` | Helper returning the Claude server-side `web_search_20250305` tool spec. Single source of truth for the `max_uses` budget |
| `extract_job_info` | `async (text: str, settings: Settings \| None = None) -> dict` | Parse job posting text via LLM; returns structured dict with company, position, location, salary_range, requirements, description, opening_date, closing_date |
| `extract_email_info` | `async (text: str, settings: Settings \| None = None) -> dict` | Classify a job-application email and extract structured fields. Returns `{kind: "interview_invite"\|"rejection"\|"unknown", confidence, interview:{round_type, scheduled_at, scheduled_time, interviewer_names, location, prep_notes, links[]}, rejection:{summary, reasons, links[]}, received_at}`. Prompt enforces: only populate when high-confidence; leave `scheduled_at/scheduled_time` null if multiple candidate slots are offered; `links` always array (deduped). |

### Provider dispatch

| Provider | URL | Auth header |
|---|---|---|
| `openai` | `https://api.openai.com/v1/chat/completions` | `Bearer {openai_api_key}` |
| `groq` | `https://api.groq.com/openai/v1/chat/completions` | `Bearer {groq_api_key}` |
| `ollama` | `{ollama_base_url}/v1/chat/completions` | none |
| `anthropic` | `https://api.anthropic.com/v1/messages` | `x-api-key` header, anthropic-version `2023-06-01` |
| `cliproxy` | `{cliproxy_base_url}/v1/messages` | `x-api-key: {cliproxy_api_key}`, anthropic-version `2023-06-01` |

- OpenAI, Groq, and Ollama use the same `_call_openai_compatible` path (OpenAI chat completions format).
- Anthropic AND cliproxy use `_call_anthropic` (Messages API format). Cliproxy's `/v1/messages` endpoint transparently relays Claude's server-side `web_search_20250305` tool.
- **Shared helper**: `_anthropic_request(url, api_key, model, system, user, *, tools=None, thinking_budget=None) -> list[dict]` executes the HTTP call and returns the raw `content` block list. Used by both `_call_anthropic` (concatenates text blocks, returns str) and `llm_call_with_trace` (parses thinking + tool blocks, returns structured result).
- `_call_anthropic(url, api_key, model, system, user, *, tools=None)` — `url` is a required first arg (so cliproxy and direct Anthropic share the same function). `max_tokens` is 8192 normally, 16384 when `tools` is passed.
- **Response parsing (llm_call path):** concatenates the `text` of EVERY `type=="text"` block in `content` (in order). Tool-using responses contain `server_tool_use` + `web_search_tool_result` blocks followed by multiple consecutive `text` blocks — all text blocks must be joined to reconstruct the reply. Raises `ValueError("Claude returned no text content")` if there are zero text blocks.
- **Response parsing (llm_call_with_trace path):** iterates `content` blocks once, accumulating `text` blocks → `text`, `thinking` blocks → `thinking`, and pairing each `server_tool_use(name="web_search")` with the subsequent `web_search_tool_result` to flatten `{query, url, title}` entries per result into `search_log`. Missing/empty result blocks are skipped silently.
- All calls use `temperature: 0.1`. Timeouts: 60s for OpenAI-compatible, 120s for Anthropic/cliproxy.
- **Extended thinking**: when `thinking_budget > 0` is passed to `_anthropic_request`, temperature is forced to `1` (Anthropic requirement) and `max_tokens` is raised to `max(16384, budget + 8192)`.

### Web-search enrichment for extract_job_info

When `settings.search_enrichment_enabled` is True AND `settings.llm_provider in ("anthropic", "cliproxy")`, `extract_job_info` passes `tools=[_web_search_tool()]` (max_uses=3) via `llm_call`, and appends a salary-grade resolution instruction to the user-turn envelope ("If the posting references a salary grade... use the web_search tool to resolve it..."). Verified live: ESA A2 grade JD with no € figure resolves to a concrete monthly/annual range.

For other providers, or when the flag is False, extraction falls back to the existing no-tool path unchanged.

### Internal helpers

| Function | Purpose |
|---|---|
| `_api_key_for(settings, provider=None)` | Resolve API key string from explicit provider or `settings.llm_provider` |
| `_get_ollama_url(settings)` | Build Ollama chat completions URL from `ollama_base_url` |
| `_call_openai_compatible(url, api_key, model, system, user)` | HTTP call for OpenAI-format APIs |
| `_call_anthropic(url, api_key, model, system, user, *, tools=None)` | Thin wrapper: calls `_anthropic_request`, joins text blocks, returns str |
| `_anthropic_request(url, api_key, model, system, user, *, tools=None, thinking_budget=None)` | Shared HTTP helper; returns raw `content` block list |
| `_parse_json(raw)` | Extract JSON from LLM response, tolerating markdown fences |

### Constants

- `_SYSTEM_PROMPT` -- job posting parser instructions; outputs JSON with: company, position, location, salary_range, requirements, description, opening_date, closing_date
- `_EMAIL_SYSTEM_PROMPT` -- job-application email classifier/extractor instructions; produces the `extract_email_info` JSON shape
- `_OPENAI_COMPATIBLE_URLS` -- maps `"openai"` and `"groq"` to their endpoints

### LLMTraceResult dataclass

`@dataclass` with fields `text: str = ""`, `thinking: str = ""`, `search_log: list[dict] = field(default_factory=list)`. Each `search_log` entry is `{query: str, url: str, title: str}`.

## kb_client.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `search_documents` | `async (query: str, n_results: int = 5, namespace_ids: list[str] \| None = None, settings: Settings \| None = None) -> list[dict]` | Semantic search across KB; degrades to `[]` on error/404 |
| `list_namespace_documents` | `async (namespace_ids: list[str], settings: Settings \| None = None) -> list[dict]` | Fetch all chunks for given namespaces via `POST /documents/chunks` (Qdrant scroll, no embedding); server-side sorting by `(doc_id, chunk_index)`; **cached for 60s** |
| `ingest_url` | `async (url: str, settings: Settings \| None = None) -> dict` | Ingest a URL into `job-applications` namespace; auto-creates namespace |
| `ingest_text` | `async (text: str, source_url: str, settings: Settings \| None = None) -> dict` | Two-step upload-batch/confirm-batch flow for pre-extracted text (PDFs etc.) |
| `close_client` | `async () -> None` | Close the shared AsyncClient singleton; call on server shutdown |
| `clear_ns_cache` | `() -> None` | Manually invalidate the list_namespace_documents TTL cache |

### Shared AsyncClient singleton

All public functions use a lazily-created module-level `httpx.AsyncClient` singleton (`_get_client()`). Connection pool: `max_connections=20`, `max_keepalive_connections=10`, `keepalive_expiry=30`. Per-request timeouts are passed as kwargs. `close_client()` must be called on shutdown (wired into `jam/server.py` via `@app.on_event("shutdown")`).

### TTL cache (list_namespace_documents)

- `_NS_CACHE_TTL = 60.0` seconds
- Key: `tuple(sorted(namespace_ids))`, Value: `(monotonic_timestamp, results)`
- On cache hit (within TTL): returns immediately, no HTTP call
- On error: cache is **not** populated (stale entry may still be evicted)
- `clear_ns_cache()` empties the entire cache dict

### KB API contract

| Endpoint | Method | Used by |
|---|---|---|
| `/namespaces/{id}` | GET | `_ensure_namespace` -- check existence |
| `/namespaces` | POST | `_ensure_namespace` -- create if missing |
| `/search` | POST | `search_documents` |
| `/documents/chunks` | POST | `list_namespace_documents` (namespace_ids + limit=500; no embedding) |
| `/ingest` | POST | `ingest_url` |
| `/ingest/upload-batch` | POST | `ingest_text` step 1 |
| `/ingest/confirm-batch` | POST | `ingest_text` step 2 |

### Constants

| Name | Value | Purpose |
|---|---|---|
| `_JOB_APPS_NS` | `"job-applications"` | Default namespace ID |
| `_JOB_APPS_LABEL` | `"Job Applications"` | Namespace display label |
| `_NS_CACHE_TTL` | `60.0` | Cache lifetime in seconds |

### Graceful degradation

- `search_documents`: returns `[]` on 404, network errors, or any exception.
- `list_namespace_documents`: returns `[]` on 404, network errors; logs warning. Does not populate cache on error.
- `ingest_url` / `ingest_text`: raise `httpx.HTTPStatusError` on failure.

### Timeouts (per-request, not on shared client)

- `search_documents`: 10s
- `list_namespace_documents`: 15s
- `ingest_url` / `ingest_text`: 60s

## gmail_client.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `get_auth_url` | `(settings: Settings \| None = None) -> str` | Build OAuth 2.0 authorization URL with PKCE; stores code_verifier in DB |
| `exchange_code` | `(code: str, settings: Settings \| None = None) -> dict` | Exchange auth code for tokens; returns `{"refresh_token": str, "email": str}` |
| `get_credentials` | `(settings: Settings \| None = None) -> Credentials` | Build `google.oauth2.credentials.Credentials` from stored refresh_token |
| `list_emails` | `(query: str = "", max_results: int = 10, settings: Settings \| None = None) -> list[dict]` | Search Gmail; returns list of `{id, subject, from, date, snippet}` |
| `get_email` | `(message_id: str, settings: Settings \| None = None) -> dict` | Fetch full email; returns `{id, subject, from, to, date, body_text}` |
| `create_draft` | `(to: str, subject: str, body: str, settings: Settings \| None = None) -> str` | Create Gmail draft; returns draft ID |
| `send_email` | `(to: str, subject: str, body: str, settings: Settings \| None = None) -> str` | Send email; returns message ID |

### OAuth flow

1. `get_auth_url` generates PKCE pair (`secrets.token_urlsafe(64)` + SHA256 challenge), stores `code_verifier` in DB via `jam.db.set_setting`.
2. User authorizes in browser, Google redirects to `http://localhost:8001/gmail/callback`.
3. `exchange_code` retrieves `code_verifier` from DB via `jam.db.get_all_settings`, exchanges code for tokens via `google_auth_oauthlib.flow.Flow`, fetches user email from Gmail profile.
4. Subsequent API calls use `get_credentials` which builds `Credentials` from stored `refresh_token`.

### Constants

| Name | Value |
|---|---|
| `SCOPES` | `["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.compose"]` |
| `REDIRECT_URI` | `"http://localhost:8001/gmail/callback"` |

### Settings injection pattern

Unlike `llm.py` and `kb_client.py` which import `Settings` at module level, `gmail_client.py` uses `TYPE_CHECKING` guard and deferred `from jam.config import Settings as _Settings` inside each function body to avoid circular imports with `jam.db`.

## msgraph_client.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `get_auth_url` | `(settings: Settings \| None = None) -> str` | Build Microsoft OAuth consent URL (`response_type=code`, `response_mode=query`, `state=jam`). Confidential-client flow — no PKCE. |
| `exchange_code` | `async (code: str, settings: Settings \| None = None) -> dict` | POST auth code to token endpoint, then GET `/me` for user email. Returns `{refresh_token, access_token, expires_at (ISO UTC), user_email}`. |
| `ensure_access_token` | `async (settings: Settings \| None = None) -> str` | Returns cached access_token if still valid (30s buffer). Otherwise refreshes via `grant_type=refresh_token` and persists the new `{access_token, expires_at}` (and rotated refresh_token if returned) via `jam.db.set_settings_batch` + `os.environ` dual-write. Raises `RuntimeError` if no refresh_token is set. |
| `upsert_event` | `async (round_row: dict, app_row: dict, settings: Settings \| None = None) -> str` | POST new event when `round_row['graph_event_id']` is empty; PATCH otherwise. 404 on PATCH falls back to POST. Returns Graph event id. |
| `delete_event` | `async (graph_event_id: str, settings: Settings \| None = None) -> None` | DELETE `/me/events/{id}`; swallows 404 silently. |

### OAuth & API endpoints

| Constant | Value |
|---|---|
| `_AUTHORITY_TEMPLATE` | `https://login.microsoftonline.com/{tenant}` (tenant from `settings.ms_graph_tenant`, default `"common"`) |
| `_AUTHORIZE_PATH` | `/oauth2/v2.0/authorize` |
| `_TOKEN_PATH` | `/oauth2/v2.0/token` |
| `_GRAPH_BASE` | `https://graph.microsoft.com/v1.0` |
| `_SCOPES` | `offline_access Calendars.ReadWrite User.Read` |
| `_EXPIRY_BUFFER_SECONDS` | `30` — tokens expiring within 30s are treated as expired |

### Event body construction (`_build_event_body`)

- `subject`: `"Interview: {company} — {position} (Round {round_number} · {round_type})"`
- `body.contentType`: `"HTML"`; content = `<p>{escaped prep_notes}</p><p>{anchor tags for each link}</p>`. `html.escape` applied to every user-supplied string.
- `location.displayName`: `round_row['location']`, falling back to the first non-empty line in `round_row['links']` if location is blank.
- `start` / `end`:
  - If `scheduled_time` is present: parsed strictly as `HH:MM`; start = `{YYYY-MM-DDTHH:MM:00, timeZone=settings.calendar_timezone}`, end = start + `settings.calendar_default_duration_minutes`; `isAllDay: false`.
  - If `scheduled_time` is empty: all-day event; start = `YYYY-MM-DDT00:00:00`, end = next-day `00:00:00`, `isAllDay: true`.
- `reminderMinutesBeforeStart`: `15`
- `attendees`: always `[]` (interviewer_names is free text, not emails — never invite strangers).
- Raises `ValueError` for malformed `scheduled_time` (non `HH:MM`, out-of-range hours/minutes) or missing `scheduled_at`.

### Calendar targeting

If `settings.ms_graph_calendar_id` is set, new events go to `/me/calendars/{id}/events`; otherwise the user's default calendar via `/me/events`. PATCH and DELETE always use `/me/events/{event_id}` (the event id is calendar-scoped on the Graph side).

### Settings injection pattern

Uses `TYPE_CHECKING` guard + deferred `from jam.config import Settings as _Settings` inside each function body (same pattern as `gmail_client.py`) to avoid circular imports with `jam.db` during the token-refresh persistence step. HTTP client created via `_build_client()` (returns fresh `httpx.AsyncClient(timeout=30)`) — tests monkey-patch this helper to inject a mock.

## Dependencies

- **llm.py** imports from: `json`, `re`, `httpx`, `jam.config.Settings`
- **kb_client.py** imports from: `httpx`, `logging`, `time`, `urllib.parse` (deferred), `jam.config.Settings`
- **gmail_client.py** imports from: `base64`, `hashlib`, `secrets`, `email.mime.text`, `google_auth_oauthlib.flow.Flow`, `google.oauth2.credentials.Credentials`, `googleapiclient.discovery.build`, `jam.config.Settings` (TYPE_CHECKING), `jam.db.set_setting` (deferred), `jam.db.get_all_settings` (deferred)
- **msgraph_client.py** imports from: `html`, `os`, `datetime`, `httpx`, `jam.config.Settings` (TYPE_CHECKING), `jam.db.set_settings_batch` (deferred)

### Imported by

| Module | Imports |
|---|---|
| `jam/server.py` | `extract_job_info`, `extract_email_info` from llm; `ingest_url`, `ingest_text`, `close_client` from kb_client; `get_auth_url`, `exchange_code` from gmail_client (deferred); `get_auth_url`, `exchange_code`, `upsert_event`, `delete_event` from msgraph_client (planned) |
| `jam/server.py` | `list_namespace_documents`, `search_documents` from kb_client (deferred, inside endpoint) |
| `jam/generation.py` | `llm_call` from llm (deferred, 5 call sites); `search_documents`, `list_namespace_documents` from kb_client (deferred) |

## Shared patterns

- **Settings injection**: All public functions accept `settings: Settings | None = None` and resolve via `settings = settings or Settings()`.
- **No global state at import**: No `Settings()` calls or HTTP clients created at module level. `kb_client._client` is declared `None` and lazily initialised on first use.
- **httpx.AsyncClient**: `llm.py` uses `async with httpx.AsyncClient(...)` per call. `kb_client.py` uses a **shared singleton** (`_get_client()`) with connection pooling; per-request timeouts passed as kwargs.
- **gmail_client.py** uses synchronous Google API client (`googleapiclient.discovery.build`), not httpx.

## Testing

- **Files**: `tests/unit/test_llm.py`, `tests/unit/test_kb_client.py`, `tests/unit/test_gmail_client.py`, `tests/unit/test_msgraph_client.py`
- **Mock targets**:
  - `jam.llm.httpx.AsyncClient` -- mock HTTP for all LLM provider tests (async context manager)
  - `jam.kb_client._get_client` -- mock the shared singleton; returns a plain `AsyncMock` instance (no context manager)
  - `jam.gmail_client.get_credentials` -- mock credential building
  - `jam.gmail_client.build` -- mock Google API service construction
  - `jam.gmail_client.Flow.from_client_config` -- mock OAuth flow (via `google_auth_oauthlib`)
  - `jam.msgraph_client._build_client` -- monkey-patched to return a `_MockAsyncClient` that serves pre-configured responses in sequence; `jam.db.set_settings_batch` is patched to verify persistence on refresh
- **Pattern**: LLM tests use `AsyncMock` with `__aenter__`/`__aexit__` to mock the async context manager. KB tests mock `_get_client` returning a plain `AsyncMock` (no context manager needed). Gmail tests use synchronous `MagicMock`. msgraph tests use a custom `_MockAsyncClient` async context manager with a response queue.
- **KB cache isolation**: Tests use a `clear_cache` autouse fixture that calls `clear_ns_cache()` before each test.

## Known Limitations

- `list_namespace_documents` requests up to 500 chunks (configurable via `limit` param in request body); namespaces with more content will be truncated.
- TTL cache (60s) means KB changes within that window won't be reflected until expiry or manual `clear_ns_cache()`.
- `gmail_client.py` hardcodes `REDIRECT_URI` to `localhost:8001`; not configurable for deployment.
- Gmail functions are synchronous (blocking) despite the rest of the codebase being async.
- No retry logic in any client; transient failures propagate or silently degrade.
- `ingest_text` derives filename from URL path; URLs without a path segment fall back to `"document.txt"`.
- Anthropic `max_tokens` ladder: 8192 plain, 16384 with tools, `max(16384, thinking_budget + 8192)` with extended thinking. Not further configurable via Settings.
- `llm_call_with_trace` is strictly Anthropic/cliproxy; raising `ValueError` for other providers so callers must handle the gate (see the interview prep-guide generator in `jam/generation.py`).
