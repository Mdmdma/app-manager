# server-api Knowledge
<!-- source: jam/server.py -->
<!-- hash: 8c1688b62827 -->
<!-- updated: 2026-03-20 -->

## Public API

### Endpoints

| Method | Path | Response | Purpose |
|---|---|---|---|
| GET | `/api/v1/` | HTML | Serve main web UI (HTML_PAGE) |
| GET | `/api/v1/health` | JSON `{status: "ok"}` | Basic health check |

### App configuration
- Title: "jam API"
- Version: "0.1.0"
- CORS: allow all origins, methods, headers
- Router prefix: `/api/v1`

## Key Constants / Schema
- No Pydantic models yet

## Dependencies
- Imports from: `fastapi`, `jam.html_page`
- Imported by: `scripts/serve.py` (via `jam.server:app`)

## Testing
- File: `tests/unit/test_server.py`
- Mock targets: none yet
- Uses `httpx.ASGITransport` for async test client

## Known Limitations
- No settings injection yet — will be added when endpoints need configuration
- No lifespan handler yet — will be added for startup tasks
