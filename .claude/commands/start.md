# Start jam Server

Start the job application manager server and CLIProxy.

## Steps

### 1. Check if already running
```bash
curl -s --max-time 2 http://localhost:8001/api/v1/health
```
If the server responds with JSON, print "Server already running on port 8001" and stop.

### 2. Start CLIProxy (if not already running)
```bash
curl -s --max-time 2 http://localhost:8317/v1/models > /dev/null 2>&1
```
If CLIProxy is not reachable, start it:
```bash
cd /home/mathis/cliproxyapi && ./cli-proxy-api > /tmp/cliproxy.log 2>&1 &
```
Wait up to 5 seconds for it to become reachable:
```bash
for i in 1 2 3 4 5; do
  sleep 1
  if curl -s --max-time 2 http://localhost:8317/v1/models > /dev/null 2>&1; then
    echo "CLIProxy started on http://localhost:8317"
    break
  fi
done
```
If it fails to start, print a warning but continue (CLIProxy is optional).

### 3. Start the jam server
```bash
cd /home/mathis/Documents/app-manager && uv run scripts/serve.py --reload > /tmp/jam-start.log 2>&1 &
```

### 4. Wait for startup
```bash
for i in 1 2 3 4 5 6 7 8; do
  sleep 1
  if curl -s --max-time 2 http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "Server started on http://localhost:8001/api/v1/"
    exit 0
  fi
done
echo "Server failed to start within 8 seconds"
```

### 5. Report
If the server started, print the health check response:
```bash
curl -s http://localhost:8001/api/v1/health
```

If it failed, read the log and give a short diagnosis:
```bash
cat /tmp/jam-start.log
```

Common causes:
- **Import error / syntax error** — a Python exception means a code change broke the module. Show the traceback.
- **Port already in use** — check `ss -tlnp | grep 8001`; a stale process may be holding the port. Run `/stop` first.
- **uv / dependency error** — `uv` failed to resolve or install packages. Show the relevant log lines.
