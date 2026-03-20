# Stop jam Server

Stop the job application manager server.

## Steps

### 1. Find and kill the process
```bash
pkill -f "uvicorn jam.server:app" 2>/dev/null
```

### 2. Verify
```bash
sleep 1
if curl -s --max-time 2 http://localhost:8001/api/v1/health > /dev/null 2>&1; then
  echo "WARNING: Server still running"
else
  echo "Server stopped"
fi
```
