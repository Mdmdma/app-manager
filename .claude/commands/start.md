# Start jam Server

Start the job application manager server.

## Steps

### 1. Check if already running
```bash
curl -s --max-time 2 http://localhost:8001/api/v1/health
```
If the server responds with JSON, print "Server already running on port 8001" and stop.

### 2. Start the server
```bash
cd /home/mathis/Documents/app-manager && uv run scripts/serve.py --reload > /tmp/jam-start.log 2>&1 &
```

### 3. Wait for startup
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

### 4. Report
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
