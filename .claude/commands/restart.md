# Restart jam Server

Stop then start the jam server without user intervention. Analyse any errors that occur.

## Steps

### 1. Stop the server

```bash
pkill -f "scripts/serve.py" 2>/dev/null; pkill -f "jam.server:app" 2>/dev/null; KILL_EXIT=$?; sleep 1
if curl -s --max-time 2 http://localhost:8001/api/v1/health > /dev/null 2>&1; then
  echo "STOP_FAILED"
else
  echo "STOP_OK"
fi
```

If output is `STOP_FAILED`, report: "Kill failed — a process is still holding port 8001. This can happen if the process ignored SIGTERM (e.g. a zombie/orphan uvicorn worker). The start step will be skipped." and stop.

### 2. Start the server

```bash
cd /home/mathis/Documents/app-manager && uv run scripts/serve.py --reload > /tmp/jam-restart.log 2>&1 &
START_PID=$!
echo "pid=$START_PID"
```

### 3. Wait for startup

```bash
for i in 1 2 3 4 5 6 7 8; do
  sleep 1
  if curl -s --max-time 2 http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "READY"
    break
  fi
  echo "waiting $i..."
done
```

If `READY` was not printed, the server failed to start within 8 seconds — go to step 4 (error analysis). Otherwise print the health response:

```bash
curl -s http://localhost:8001/api/v1/health
```

and report: "Server restarted successfully on http://localhost:8001" — stop here.

### 4. Error analysis (only if startup failed)

Read the startup log and analyse the error:

```bash
cat /tmp/jam-restart.log
```

Then check if the port is still occupied:

```bash
ss -tlnp | grep 8001
```

Based on what you find, give a short diagnosis. Common causes:
- **Import error / syntax error** — a Python exception in the log means a code change broke the module. Show the traceback.
- **Port already in use** — `ss` output shows something on 8001. The old process may not have died in time; suggest waiting a moment and retrying.
- **uv / dependency error** — `uv` failed to resolve or install packages. Show the relevant log lines.
- **Permission error** — unlikely on localhost but flag it if seen.

End with: "Run `/start` once the issue is resolved."
