# config Knowledge
<!-- source: jam/config.py -->
<!-- hash: 3928d66329cf -->
<!-- updated: 2026-03-26 -->

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

## Dependencies
- Imports from: `dataclasses`, `os`
- Imported by: `jam/server.py`, `jam/llm.py`

## Testing
- File: `tests/unit/test_config.py`
- Tests: `test_defaults`, `test_env_overrides`

## Known Limitations
- No persistence to DB yet (future: SQLite like kb)
