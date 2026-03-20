# Test Runner Skill for jam

You are the test runner for the `jam` project. Run this skill after every edit session to confirm the service is healthy and all tests pass.

## Working directory
`/home/mathis/Documents/app-manager`

## Steps — run in order, stop and report on first failure

### 0. Knowledge file freshness check

Compare source hashes against knowledge file hashes:

```bash
stale=""
for src in jam/config.py jam/server.py; do
  mod=$(basename "$src" .py)
  case "$mod" in
    server) kf=".claude/knowledge/server-api.md" ;;
    *) kf=".claude/knowledge/${mod}.md" ;;
  esac
  [ -f "$kf" ] || continue
  actual=$(sha256sum "$src" | cut -c1-12)
  stored=$(grep -oP '(?<=<!-- hash: )[a-f0-9]+' "$kf")
  if [ "$actual" != "$stored" ]; then
    stale="$stale $mod"
  fi
done
# html_page.py -> server-ui
if [ -f "jam/html_page.py" ] && [ -f ".claude/knowledge/server-ui.md" ]; then
  actual=$(sha256sum jam/html_page.py | cut -c1-12)
  stored=$(grep -oP '(?<=<!-- hash: )[a-f0-9]+' ".claude/knowledge/server-ui.md")
  [ "$actual" = "$stored" ] || stale="$stale server-ui"
fi
if [ -n "$stale" ]; then
  echo "STALE:$stale"
else
  echo "OK"
fi
```

If any are stale, print `WARNING: Run /update-knowledge all` but continue with tests (non-blocking).

### 1. Unit tests (always run, no network needed)

```bash
uv run pytest tests/unit -x -q 2>&1
```

- All tests must pass (`N passed`).
- If any fail: print the full failure output and stop. Do NOT proceed to step 2.

### 2. Integration tests — mocked subset (always run, no network needed)

```bash
uv run pytest tests/integration -x -q -m "not integration" 2>&1
```

- All tests must pass.
- If any fail: print the full failure output and stop.

### 3. Live service health check (only if server is reachable)

```bash
curl -s --max-time 3 http://localhost:8001/api/v1/health 2>&1
```

- If the curl fails or times out: print "Server not running — skipping live health check" and continue.
- If the server responds: pretty-print the JSON and check the `status` field.

## Output format

Print a summary at the end:

```
────────────────────────────────────
TEST RESULTS
  Knowledge files:               OK (all fresh)
  Unit tests:                    PASS (N passed)
  Integration (mocked):          PASS (N passed)
  Live /health:                  OK — status ok
────────────────────────────────────
```

Use `PASS` / `FAIL` / `SKIPPED` for each row. If anything is FAIL, clearly state what broke.
