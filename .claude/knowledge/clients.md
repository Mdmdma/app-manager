# clients Knowledge
<!-- source: jam/llm.py, jam/kb_client.py, jam/gmail_client.py -->
<!-- hash: 5830475f380f -->
<!-- updated: 2026-03-31 -->

## llm.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `llm_call` | `async (system: str, user: str, settings: Settings \| None = None) -> str` | Generic LLM call dispatching to configured provider; used by generation nodes |
| `extract_job_info` | `async (text: str, settings: Settings \| None = None) -> dict` | Parse job posting text via LLM; returns structured dict with company, position, location, salary_range, requirements, description, opening_date, closing_date |

### Provider dispatch

| Provider | URL | Auth header |
|---|---|---|
| `openai` | `https://api.openai.com/v1/chat/completions` | `Bearer {openai_api_key}` |
| `groq` | `https://api.groq.com/openai/v1/chat/completions` | `Bearer {groq_api_key}` |
| `ollama` | `{ollama_base_url}/v1/chat/completions` | none |
| `anthropic` | `https://api.anthropic.com/v1/messages` | `x-api-key` header, anthropic-version `2023-06-01` |

- OpenAI, Groq, and Ollama use the same `_call_openai_compatible` path (OpenAI chat completions format).
- Anthropic uses a dedicated `_call_anthropic` path (Messages API format, max_tokens 8192).
- All calls use `temperature: 0.1`. Timeouts: 60s for OpenAI-compatible, 120s for Anthropic.

### Internal helpers

| Function | Purpose |
|---|---|
| `_api_key_for(settings)` | Resolve API key string from provider name |
| `_get_ollama_url(settings)` | Build Ollama chat completions URL from `ollama_base_url` |
| `_call_openai_compatible(url, api_key, model, system, user)` | HTTP call for OpenAI-format APIs |
| `_call_anthropic(api_key, model, system, user)` | HTTP call for Anthropic Messages API |
| `_parse_json(raw)` | Extract JSON from LLM response, tolerating markdown fences |

### Constants

- `_SYSTEM_PROMPT` -- job posting parser instructions; outputs JSON with: company, position, location, salary_range, requirements, description, opening_date, closing_date
- `_OPENAI_COMPATIBLE_URLS` -- maps `"openai"` and `"groq"` to their endpoints

## kb_client.py -- Public API

| Function | Signature | Purpose |
|---|---|---|
| `search_documents` | `async (query: str, n_results: int = 5, namespace_ids: list[str] \| None = None, settings: Settings \| None = None) -> list[dict]` | Semantic search across KB; degrades to `[]` on error/404 |
| `list_namespace_documents` | `async (namespace_ids: list[str], settings: Settings \| None = None) -> list[dict]` | Fetch all chunks for given namespaces via search endpoint (neutral query, top_k=100); groups and sorts by doc_id + chunk_index |
| `ingest_url` | `async (url: str, settings: Settings \| None = None) -> dict` | Ingest a URL into `job-applications` namespace; auto-creates namespace |
| `ingest_text` | `async (text: str, source_url: str, settings: Settings \| None = None) -> dict` | Two-step upload-batch/confirm-batch flow for pre-extracted text (PDFs etc.) |

### KB API contract

| Endpoint | Method | Used by |
|---|---|---|
| `/namespaces/{id}` | GET | `_ensure_namespace` -- check existence |
| `/namespaces` | POST | `_ensure_namespace` -- create if missing |
| `/search` | POST | `search_documents`, `list_namespace_documents` |
| `/ingest` | POST | `ingest_url` |
| `/ingest/upload-batch` | POST | `ingest_text` step 1 |
| `/ingest/confirm-batch` | POST | `ingest_text` step 2 |

### Constants

| Name | Value | Purpose |
|---|---|---|
| `_JOB_APPS_NS` | `"job-applications"` | Default namespace ID |
| `_JOB_APPS_LABEL` | `"Job Applications"` | Namespace display label |

### Graceful degradation

- `search_documents`: returns `[]` on 404, network errors, or any exception.
- `list_namespace_documents`: returns `[]` on 404, network errors; logs warning.
- `ingest_url` / `ingest_text`: raise `httpx.HTTPStatusError` on failure.

### Timeouts

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

## Dependencies

- **llm.py** imports from: `json`, `re`, `httpx`, `jam.config.Settings`
- **kb_client.py** imports from: `httpx`, `logging`, `collections.defaultdict` (deferred), `urllib.parse` (deferred), `jam.config.Settings`
- **gmail_client.py** imports from: `base64`, `hashlib`, `secrets`, `email.mime.text`, `google_auth_oauthlib.flow.Flow`, `google.oauth2.credentials.Credentials`, `googleapiclient.discovery.build`, `jam.config.Settings` (TYPE_CHECKING), `jam.db.set_setting` (deferred), `jam.db.get_all_settings` (deferred)

### Imported by

| Module | Imports |
|---|---|
| `jam/server.py` | `extract_job_info` from llm; `ingest_url`, `ingest_text` from kb_client; `get_auth_url`, `exchange_code` from gmail_client (deferred) |
| `jam/server.py` | `list_namespace_documents`, `search_documents` from kb_client (deferred, inside endpoint) |
| `jam/generation.py` | `llm_call` from llm (deferred, 5 call sites); `search_documents`, `list_namespace_documents` from kb_client (deferred) |

## Shared patterns

- **Settings injection**: All public functions accept `settings: Settings | None = None` and resolve via `settings = settings or Settings()`.
- **No global state at import**: No `Settings()` calls or HTTP clients created at module level.
- **httpx.AsyncClient**: Used as async context manager in both `llm.py` and `kb_client.py`; never shared across calls.
- **gmail_client.py** uses synchronous Google API client (`googleapiclient.discovery.build`), not httpx.

## Testing

- **Files**: `tests/unit/test_llm.py`, `tests/unit/test_kb_client.py`, `tests/unit/test_gmail_client.py`
- **Mock targets**:
  - `jam.llm.httpx.AsyncClient` -- mock HTTP for all LLM provider tests
  - `jam.kb_client.httpx.AsyncClient` -- mock HTTP for all KB API tests
  - `jam.gmail_client.get_credentials` -- mock credential building
  - `jam.gmail_client.build` -- mock Google API service construction
  - `jam.gmail_client.Flow.from_client_config` -- mock OAuth flow (via `google_auth_oauthlib`)
- **Pattern**: All LLM/KB tests use `AsyncMock` with `__aenter__`/`__aexit__` to mock the async context manager. Gmail tests use synchronous `MagicMock`.

## Known Limitations

- `list_namespace_documents` is capped at 100 chunks (KB API `top_k` limit); namespaces with more content will be truncated.
- `list_namespace_documents` uses a neutral single-space query which may introduce semantic bias in ranking.
- `gmail_client.py` hardcodes `REDIRECT_URI` to `localhost:8001`; not configurable for deployment.
- Gmail functions are synchronous (blocking) despite the rest of the codebase being async.
- No retry logic in any client; transient failures propagate or silently degrade.
- `ingest_text` derives filename from URL path; URLs without a path segment fall back to `"document.txt"`.
- Anthropic calls use a fixed `max_tokens: 8192`; not configurable via Settings.
