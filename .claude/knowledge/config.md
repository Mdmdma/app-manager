# config Knowledge
<!-- source: jam/config.py -->
<!-- hash: 171c931bd572 -->
<!-- updated: 2026-03-28 -->

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
| `llm_provider` | `str` | `LLM_PROVIDER` | `openai` |
| `llm_model` | `str` | `LLM_MODEL` | `gpt-4o` |
| `cv_latex_template` | `str` | `JAM_CV_LATEX_TEMPLATE` | `""` |
| `cover_letter_latex_template` | `str` | `JAM_COVER_LETTER_LATEX_TEMPLATE` | `""` |
| `gmail_client_id` | `str` | `GMAIL_CLIENT_ID` | `""` |
| `gmail_client_secret` | `str` | `GMAIL_CLIENT_SECRET` | `""` |
| `gmail_refresh_token` | `str` | `GMAIL_REFRESH_TOKEN` | `""` |
| `gmail_user_email` | `str` | `GMAIL_USER_EMAIL` | `""` |
| `kb_retrieval_namespaces` | `str` | `JAM_KB_RETRIEVAL_NAMESPACES` | `""` |
| `kb_retrieval_n_results` | `int` | `JAM_KB_RETRIEVAL_N_RESULTS` | `5` |
| `kb_retrieval_padding` | `int` | `JAM_KB_RETRIEVAL_PADDING` | `0` |
| `kb_include_namespaces` | `str` | `JAM_KB_INCLUDE_NAMESPACES` | `""` |

## Dependencies
- Imports from: `dataclasses`, `os`
- Imported by: `jam/server.py`, `jam/llm.py`, `jam/kb_client.py`, `jam/generation.py`

## Testing
- File: `tests/unit/test_config.py`
- Tests: `test_defaults`, `test_env_overrides`

## Known Limitations and Design Notes

- `kb_retrieval_namespaces` and `kb_include_namespaces` are JSON-encoded lists stored as strings
- **KB Retrieval Settings**: The four KB retrieval fields (`kb_retrieval_namespaces`, `kb_retrieval_n_results`, `kb_retrieval_padding`, `kb_include_namespaces`) are defined here but are primarily DB-backed when used in the generation workflow (`jam/generation.py`). Env vars defined here serve as fallback defaults when the DB has no value.
  - DB values take precedence over env var defaults
  - Fallback order: DB → env var → hardcoded default
- `kb_retrieval_padding`: Over-fetches `n_results + padding` from KB search, then trims back to `n_results` for RAG quality tuning
