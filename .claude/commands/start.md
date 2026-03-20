# Start jam Server

Start the job application manager server.

## Steps

### 1. Check if already running
```bash
curl -s --max-time 2 http://localhost:8001/api/v1/health
```
If the server responds, print "Server already running on port 8001" and stop.

### 2. Start the server
```bash
cd /home/mathis/Documents/app-manager && uv run scripts/serve.py --reload &
```

### 3. Wait for startup
```bash
for i in 1 2 3 4 5; do
  sleep 1
  if curl -s --max-time 2 http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "Server started on http://localhost:8001"
    exit 0
  fi
done
echo "Server failed to start within 5 seconds"
```

### 4. Report
Print the health check response if available.
