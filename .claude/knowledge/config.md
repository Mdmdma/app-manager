# config Knowledge
<!-- source: jam/config.py -->
<!-- hash: 40be0fb63a57 -->
<!-- updated: 2026-04-21 -->

## Public API

| Function/Class | Signature | Purpose |
|---|---|---|
| `Settings` | `@dataclass` | Configuration dataclass with env var defaults |

## Key Constants / Schema

| Field | Type | Env Var | Default |
|---|---|---|---|
| `kb_api_url` | `str` | `JAM_KB_API_URL` | `http://localhost:8000/api/v1` |
| `port` | `int` | `JAM_PORT` | `8001` |
| `openai_api_key` | `str` | `OPENAI_API_KEY` | `""` |
| `anthropic_api_key` | `str` | `ANTHROPIC_API_KEY` | `""` |
| `groq_api_key` | `str` | `GROQ_API_KEY` | `""` |
| `ollama_base_url` | `str` | `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `cliproxy_base_url` | `str` | `CLIPROXY_BASE_URL` | `http://localhost:8317` |
| `cliproxy_api_key` | `str` | `CLIPROXY_API_KEY` | `""` |
| `llm_provider` | `str` | `LLM_PROVIDER` | `openai` |
| `llm_model` | `str` | `LLM_MODEL` | `gpt-4o` |
| `cv_latex_template` | `str` | `JAM_CV_LATEX_TEMPLATE` | `""` |
| `cover_letter_latex_template` | `str` | `JAM_COVER_LETTER_LATEX_TEMPLATE` | `""` |
| `gmail_client_id` | `str` | `GMAIL_CLIENT_ID` | `""` |
| `gmail_client_secret` | `str` | `GMAIL_CLIENT_SECRET` | `""` |
| `gmail_refresh_token` | `str` | `GMAIL_REFRESH_TOKEN` | `""` |
| `gmail_user_email` | `str` | `GMAIL_USER_EMAIL` | `""` |
| `ms_graph_client_id` | `str` | `MS_GRAPH_CLIENT_ID` | `""` |
| `ms_graph_client_secret` | `str` | `MS_GRAPH_CLIENT_SECRET` | `""` |
| `ms_graph_tenant` | `str` | `MS_GRAPH_TENANT` | `"common"` |
| `ms_graph_redirect_uri` | `str` | `MS_GRAPH_REDIRECT_URI` | `http://localhost:8001/ms_graph/callback` |
| `ms_graph_refresh_token` | `str` | `MS_GRAPH_REFRESH_TOKEN` | `""` |
| `ms_graph_access_token` | `str` | `MS_GRAPH_ACCESS_TOKEN` | `""` |
| `ms_graph_token_expires_at` | `str` | `MS_GRAPH_TOKEN_EXPIRES_AT` | `""` (ISO-8601 timestamp) |
| `ms_graph_user_email` | `str` | `MS_GRAPH_USER_EMAIL` | `""` |
| `ms_graph_calendar_id` | `str` | `MS_GRAPH_CALENDAR_ID` | `""` (empty = default Outlook calendar) |
| `calendar_timezone` | `str` | `JAM_CALENDAR_TIMEZONE` | `"UTC"` (IANA name, e.g. `Europe/Berlin`) |
| `calendar_default_duration_minutes` | `int` | `JAM_CALENDAR_DEFAULT_DURATION_MINUTES` | `60` |
| `search_enrichment_enabled` | `bool` | `JAM_SEARCH_ENRICHMENT_ENABLED` | `True` (truthy set: `{"1","true","yes","on"}` case-insensitive) |
| `kb_retrieval_namespaces` | `str` | `JAM_KB_RETRIEVAL_NAMESPACES` | `""` |
| `kb_retrieval_n_results` | `int` | `JAM_KB_RETRIEVAL_N_RESULTS` | `5` |
| `kb_retrieval_padding` | `int` | `JAM_KB_RETRIEVAL_PADDING` | `0` |
| `kb_include_namespaces` | `str` | `JAM_KB_INCLUDE_NAMESPACES` | `""` |
| `personal_full_name` | `str` | `JAM_PERSONAL_FULL_NAME` | `""` |
| `personal_email` | `str` | `JAM_PERSONAL_EMAIL` | `""` |
| `personal_phone` | `str` | `JAM_PERSONAL_PHONE` | `""` |
| `personal_website` | `str` | `JAM_PERSONAL_WEBSITE` | `""` |
| `personal_address` | `str` | `JAM_PERSONAL_ADDRESS` | `""` |
| `personal_photo` | `str` | `JAM_PERSONAL_PHOTO` | `""` |
| `personal_signature` | `str` | `JAM_PERSONAL_SIGNATURE` | `""` |
| `prompt_generate_prep_guide` | `str` | `JAM_PROMPT_GENERATE_PREP_GUIDE` | `""` |
| `prep_guide_max_web_searches` | `int` | `JAM_PREP_GUIDE_MAX_WEB_SEARCHES` | `100` |
| `prep_guide_thinking_budget` | `int` | `JAM_PREP_GUIDE_THINKING_BUDGET` | `16000` |
| `step_model_generate_prep_guide` | `str` | `JAM_STEP_MODEL_GENERATE_PREP_GUIDE` | `""` |

## Dependencies
- Imports from: `dataclasses`, `os`
- Imported by: `jam/server.py`, `jam/llm.py`, `jam/kb_client.py`, `jam/generation.py`, `jam/msgraph_client.py` (planned)

## Testing
- File: `tests/unit/test_config.py`
- Tests: `test_defaults`, `test_env_overrides`

## Known Limitations and Design Notes

- `kb_retrieval_namespaces` and `kb_include_namespaces` are JSON-encoded lists stored as strings
- **KB Retrieval Settings**: The four KB retrieval fields (`kb_retrieval_namespaces`, `kb_retrieval_n_results`, `kb_retrieval_padding`, `kb_include_namespaces`) are defined here but are primarily DB-backed when used in the generation workflow (`jam/generation.py`). Env vars defined here serve as fallback defaults when the DB has no value.
  - DB values take precedence over env var defaults
  - Fallback order: DB → env var → hardcoded default
- `kb_retrieval_padding`: Over-fetches `n_results + padding` from KB search, then trims back to `n_results` for RAG quality tuning
- **Personal info fields**: Used for PDF metadata injection (author, etc.). Stored in DB via settings; env vars serve as fallback defaults.
- **System prompts** are NOT in config — they are DB-only settings read in `jam/generation.py` via `_get_prompt()`. Too long for env vars. Exception: `prompt_generate_prep_guide` appears here as a fallback-default env var (same pattern as the KB retrieval fields); the actual prompt is DB-backed.
- **Prep guide settings**:
  - `prep_guide_max_web_searches` bounds the Anthropic `web_search_20250305` tool budget for the interview-prep generator (high by design: 100, to let the model explore company + field + project context).
  - `prep_guide_thinking_budget` enables Anthropic extended thinking (≥1024) so the model can plan, search, draft, and self-critique for coherence.
  - `step_model_generate_prep_guide` is the per-step LLM override (`provider:model`). Empty = use default `llm_provider`/`llm_model`. Prep guide generation is gated to `anthropic` / `cliproxy` providers only because it relies on server-side web search + thinking.
- **Microsoft Graph (Outlook Calendar) settings**:
  - Tokens are env-var-defaulted but primarily persisted in the DB `settings` table (same dual pattern as Gmail OAuth). `/ms_graph/callback` writes refresh_token, access_token, expiry, user_email via `set_settings_batch`.
  - `ms_graph_tenant` defaults to `"common"` — supports both personal and work/school accounts. Set a specific tenant ID to lock to one org.
  - `ms_graph_calendar_id` empty → writes to user's default calendar; set to a specific calendar id to target a sub-calendar.
- **Calendar settings**:
  - `calendar_timezone` is a single global IANA timezone used for all interview events (no per-round tz in the schema).
  - `calendar_default_duration_minutes` is the fallback event length when an interview has only `scheduled_time` (no end time stored).
