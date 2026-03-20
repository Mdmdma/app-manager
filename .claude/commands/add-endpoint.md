# Add Endpoint

Guided workflow for adding a new FastAPI endpoint to `jam/server.py`.

## Preconditions
1. Run `/test` first. If tests fail, fix them before adding a new endpoint.
2. Read `.claude/knowledge/server-api.md` to understand existing endpoints.

## Steps

### 1. Gather requirements
Ask the user:
- HTTP method (GET, POST, PUT, DELETE, PATCH)
- Path (e.g., `/applications`, `/applications/{id}`)
- Request model (if POST/PUT/PATCH): field names, types, defaults
- Response shape: what data does it return?
- Any side effects (DB writes, external API calls)?

### 2. Implement
1. Add any new Pydantic models to `jam/server.py`
2. Add the endpoint function to `jam/server.py`
3. Follow existing patterns: `async def`, type hints, HTTPException for errors

### 3. Add tests
1. Add unit test(s) in `tests/unit/test_server.py`:
   - Happy path
   - Error cases (404, 422, etc.)
2. Add integration test in `tests/integration/test_server_integration.py` if the endpoint
   involves external services.

### 4. Verify
1. Run `/update-knowledge server-api`
2. Run `/test`
