# config Knowledge
<!-- source: jam/config.py -->
<!-- hash: 26102afa830a -->
<!-- updated: 2026-03-20 -->

## Public API

| Function/Class | Signature | Purpose |
|---|---|---|
| `Settings` | `@dataclass` | Configuration dataclass with env var defaults |

## Key Constants / Schema

| Field | Type | Env Var | Default |
|---|---|---|---|
| `kb_api_url` | `str` | `JAM_KB_API_URL` | `http://localhost:8000/api/v1` |
| `port` | `int` | `JAM_PORT` | `8001` |

## Dependencies
- Imports from: `dataclasses`, `os`
- Imported by: `jam/server.py` (future), `tests/conftest.py`

## Testing
- File: `tests/unit/test_config.py`
- Tests: `test_defaults`, `test_env_overrides`

## Known Limitations
- No persistence to DB yet (future: SQLite like kb)
