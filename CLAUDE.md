# CLAUDE.md — Agent Instructions for the `jam` Project

## What this project is
A job application manager that tracks and organizes job applications. It is a
downstream app in the kb ecosystem, communicating with the knowledge base via
REST APIs. The web UI shares the kb design system for visual consistency.

## Architecture overview

```
app-manager/
├── jam/config.py      # Single source of truth for all configuration
├── jam/html_page.py   # HTML_PAGE constant — all inline HTML/CSS/JS for the web UI
├── jam/server.py      # FastAPI app — endpoints + static page serving
├── shared -> ../kb/shared  # Symlink to shared design system + conventions
scripts/
└── serve.py           # thin uvicorn shim
tests/
├── unit/              # mocked, no network
└── integration/       # real HTTP calls gated with @pytest.mark.integration
```

## Key conventions

1. **Settings injection**: All public functions accept `settings: Settings | None = None`
   and resolve it inside the function body:
   ```python
   settings = settings or Settings()
   ```
   Never read `os.environ` directly outside `jam/config.py`.

2. **No global state at import**: Do not call `Settings()` or configure anything
   at the module level. Only inside function bodies.

3. **Shared design system**: UI uses design tokens from `shared/design-system/tokens.json`
   and component classes from `shared/design-system/components.css`. Both are inlined
   into `jam/html_page.py` following the kb pattern (no external CSS files at runtime).

4. **kb API access**: All communication with the knowledge base goes through a typed
   client module (to be added). Never call `httpx` or `fetch` directly from other modules.

## Running the project

```bash
# Install dependencies
uv sync

# Start the server (port 8001)
uv run scripts/serve.py

# Or with auto-reload for development
uv run scripts/serve.py --reload
```

The kb knowledge base should be running on port 8000 for full functionality.

## Testing strategy

| Test type      | Location               | Network       |
|----------------|------------------------|---------------|
| Unit           | `tests/unit/`          | mocked        |
| Integration    | `tests/integration/`   | real HTTP     |

```bash
# Run unit tests only (no network needed)
uv run pytest tests/unit -x -q

# Run all non-integration tests (safe for CI)
uv run pytest -m "not integration"

# Run with coverage report
uv run pytest --cov=jam --cov-report=term-missing
```

## Testing requirements

**Always add tests when you add or change behaviour.**

- Every new public function -> at least one unit test in `tests/unit/`.
- Every new API endpoint -> unit tests in `tests/unit/test_server.py`;
  integration tests in `tests/integration/test_server_integration.py`.
- Every new `Settings` field -> add it to `test_defaults` and `test_env_overrides`
  in `tests/unit/test_config.py`.
- Run `uv run pytest tests/unit -x` before considering a task done.

## Database migrations

- **Never use `executescript()`** — it issues an implicit COMMIT, bypassing the
  `_connect()` context manager's transaction safety. Use individual `conn.execute()`
  calls so the migration runs inside a single transaction and rolls back on failure.
- **All migrations must be atomic** — run inside a single `_connect()` transaction.
- **Table rebuilds require row-count verification** — when doing SQLite table
  rebuilds (rename → create → copy → drop), assert that the row count matches
  before dropping the old table.
- **Never drop or rename tables outside a transaction.**
- **Test migrations with existing data** — unit tests for schema migrations should
  seed data first, run the migration, and assert data is preserved.

## Delegation protocol

**Every edit to `jam/*.py` MUST go through the module agent that owns the file.**
Do not edit these files directly from the orchestrator — even for single-line
changes. This is the single most important rule for token efficiency and
consistency. Agents read compact knowledge files instead of full source, run
scoped tests, and report cross-module needs back to you.

### Routing table

| Task touches | Delegate to | `subagent_type` |
|---|---|---|
| Settings, env vars (`config.py`) | config-agent | `config-agent` |
| API endpoints, Pydantic models (`server.py`) | server-api-agent | `server-api-agent` |
| Web UI, HTML/CSS/JS (`html_page.py`) | ui-agent | `ui-agent` |
| Database, schema, migrations (`db.py`) | db-agent | `db-agent` |
| Generation pipeline, LangGraph (`generation.py`) | generation-agent | `generation-agent` |
| LLM, KB client, Gmail client | clients-agent | `clients-agent` |

**Module dependency order** (modify in this order):
`config` -> `{clients, db}` -> `generation` -> `server` (html_page is a leaf)

### Responsibility split

| Responsibility | Who does it |
|---|---|
| Read knowledge file, edit source, edit tests, run scoped tests | **Agent** |
| Run `/update-knowledge` after agent completes | **Orchestrator** |
| Run `/test` for final validation | **Orchestrator** |
| Route **Needs attention** items to sibling agents | **Orchestrator** |

Agents do NOT have the Skill tool. Never instruct them to run `/test` or
`/update-knowledge` — they cannot. The orchestrator handles all skill
invocations after agents return.

### Cross-module workflow

When a task spans multiple modules:

1. Identify all affected modules from the routing table.
2. Launch agents in dependency order (or in parallel when independent).
3. When an agent returns a **Needs attention** block, route each item to the
   named sibling agent with full context from the first agent's response.
4. After all agents complete, run `/update-knowledge` for each changed module.
5. Run `/test` once at the end.

Agents cannot spawn other agents. All cross-module coordination flows through
the orchestrator using the **Needs attention** pattern.

## Knowledge files and skills

### Module agents (`.claude/agents/`)

| Agent file | Owns | Knowledge file |
|---|---|---|
| `config-agent.md` | `jam/config.py` | `.claude/knowledge/config.md` |
| `server-api-agent.md` | `jam/server.py` | `.claude/knowledge/server-api.md` |
| `ui-agent.md` | `jam/html_page.py` | `.claude/knowledge/server-ui.md` |
| `db-agent.md` | `jam/db.py` | `.claude/knowledge/db.md` |
| `generation-agent.md` | `jam/generation.py` | `.claude/knowledge/generation.md` |
| `clients-agent.md` | `jam/llm.py`, `jam/kb_client.py`, `jam/gmail_client.py` | `.claude/knowledge/clients.md` |

### Knowledge files (`.claude/knowledge/`)

Each module has a knowledge file with a snapshot of its public API, constants,
schema, dependencies, and known limitations. These are the **first thing agents
read** instead of re-reading source files. Each file contains a `<!-- hash: ... -->`
comment for staleness detection.

| File | Covers |
|---|---|
| `config.md` | `jam/config.py` — Settings fields, env vars, defaults |
| `server-api.md` | `jam/server.py` — All FastAPI endpoints, Pydantic models |
| `server-ui.md` | `jam/html_page.py` — Web UI structure, JS state machine |
| `db.md` | `jam/db.py` — Tables, CRUD functions, migrations |
| `generation.md` | `jam/generation.py` — LangGraph nodes, state, compile loop |
| `clients.md` | `jam/llm.py`, `jam/kb_client.py`, `jam/gmail_client.py` — External service clients |
| `chrome-extension.md` | `extensions/chrome/` — Chrome extension architecture, states, API contract |

**Knowledge update rule**: The orchestrator runs `/update-knowledge <module>`
after each agent completes its work. Agents do not run this themselves. The
`chrome-extension` knowledge file is static — update it manually after editing
extension files.

### Skills (`.claude/commands/`)

| Skill | Invocation | Purpose |
|---|---|---|
| `test.md` | `/test` | Run unit tests, integration tests, and live health check |
| `update-knowledge.md` | `/update-knowledge <module\|all>` | Regenerate knowledge files from source |
| `add-endpoint.md` | `/add-endpoint` | Guided workflow: new FastAPI endpoint + tests |
| `start.md` | `/start` | Start the jam server |
| `stop.md` | `/stop` | Stop the jam server |
| `chrome-extension.md` | `/chrome-extension` | Verify extension files and guide the user through Chrome installation |

## Environment variables

| Variable         | Required | Default                         | Description                    |
|------------------|----------|---------------------------------|--------------------------------|
| `JAM_KB_API_URL` | No       | `http://localhost:8000/api/v1`  | kb knowledge base API URL      |
| `JAM_PORT`       | No       | `8001`                          | Server port                    |

## Shared files

Design tokens and component CSS live in the kb repo at `kb/shared/`. This project
symlinks to them at `./shared -> ../kb/shared`. Reference:

- `shared/design-system/tokens.json` — colors, typography, spacing, radii
- `shared/design-system/components.css` — reusable component classes
- `shared/conventions/web-standards.md` — JS/API patterns

## Files never to touch
- `.env` is gitignored — never commit it.
- `uv.lock` must be committed; update via `uv sync` after dependency changes.
