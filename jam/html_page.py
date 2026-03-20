HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Job Application Manager</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 24px 16px 48px;
  }

  header {
    width: 100%;
    max-width: 912px;
    margin-bottom: 20px;
  }

  header h1 { font-size: 1.6rem; font-weight: 700; color: #16213e; letter-spacing: -0.02em; }
  header p  { font-size: 0.875rem; color: #6b7280; margin-top: 4px; }

  /* -- Card -- */
  .card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06);
    width: 100%;
    max-width: 912px;
    overflow: hidden;
  }

  /* -- Tabs -- */
  .tab-bar {
    display: flex;
    border-bottom: 1px solid #e5e7eb;
    background: #fafafa;
  }
  .tab-btn {
    flex: 1;
    padding: 12px 16px;
    font-size: 0.875rem;
    font-weight: 600;
    color: #6b7280;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .tab-btn:hover { color: #4f46e5; }
  .tab-btn.active { color: #4f46e5; border-bottom-color: #4f46e5; background: #fff; }

  .tab-panel { display: none; padding: 20px; }
  .tab-panel.active { display: block; }

  /* -- Buttons -- */
  .btn {
    border: none; border-radius: 8px; padding: 8px 16px;
    font-size: 0.85rem; font-weight: 600; cursor: pointer;
    transition: background 0.15s;
  }
  .btn-sm { font-size: 0.8rem; padding: 5px 14px; }
  .btn-primary { background: #4f46e5; color: #fff; }
  .btn-primary:hover { background: #4338ca; }
  .btn-secondary { background: #f3f4f6; color: #374151; }
  .btn-secondary:hover { background: #e5e7eb; }
  .btn-green { background: #10b981; color: #fff; }
  .btn-green:hover:not(:disabled) { background: #059669; }
  .btn-danger { background: #dc2626; color: #fff; }
  .btn-danger:hover { background: #b91c1c; }
  .btn:disabled { opacity: 0.55; cursor: default; }

  /* -- Badges -- */
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 6px;
    font-size: 0.75rem; font-weight: 600;
  }
  .badge-indigo { background: #e0e7ff; color: #3730a3; }
  .badge-green  { background: #d1fae5; color: #065f46; }
  .badge-gray   { background: #f3f4f6; color: #4b5563; }
  .badge-amber  { background: #fef3c7; color: #92400e; }

  /* -- Form fields -- */
  .field-label {
    display: block; font-size: 0.8rem; font-weight: 600; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
  }
  textarea.field-input, input.field-input {
    width: 100%; border: 1px solid #d1d5db; border-radius: 10px;
    padding: 10px 14px; font-size: 0.875rem; font-family: inherit;
    outline: none; transition: border-color 0.15s; color: #1a1a2e;
  }
  textarea.field-input:focus, input.field-input:focus { border-color: #4f46e5; }

  /* -- Status -- */
  .status-msg { font-size: 0.85rem; color: #6b7280; }
  .status-msg.success { color: #059669; }
  .status-msg.error   { color: #dc2626; }

  /* -- Empty state -- */
  .empty-state {
    text-align: center; color: #9ca3af; padding: 60px 20px;
  }
  .empty-state .icon { font-size: 2.5rem; margin-bottom: 12px; }
  .empty-state h3 { font-size: 1rem; font-weight: 600; color: #6b7280; margin-bottom: 6px; }
  .empty-state p { font-size: 0.875rem; }

  /* -- Dashboard stats -- */
  .stats-row {
    display: flex; gap: 12px; margin-bottom: 20px;
  }
  .stat-card {
    flex: 1; background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 10px; padding: 16px; text-align: center;
  }
  .stat-card .stat-value {
    font-size: 1.4rem; font-weight: 700; color: #1a1a2e;
  }
  .stat-card .stat-label {
    font-size: 0.75rem; font-weight: 600; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;
  }

  /* -- Connection indicator -- */
  .connection-status {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.8rem; color: #6b7280;
  }
  .connection-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #d1d5db;
  }
  .connection-dot.connected { background: #10b981; }
  .connection-dot.disconnected { background: #dc2626; }

  @media (max-width: 600px) {
    .stats-row { flex-direction: column; }
  }
</style>
</head>
<body>

<header>
  <div style="display:flex; align-items:center; justify-content:space-between;">
    <div>
      <h1>Job Application Manager</h1>
      <p>Track and manage your job applications</p>
    </div>
    <div class="connection-status" id="kb-status">
      <span class="connection-dot" id="kb-dot"></span>
      <span id="kb-status-text">Checking kb...</span>
    </div>
  </div>
</header>

<div class="card">
  <div class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('dashboard')">Dashboard</button>
    <button class="tab-btn" onclick="switchTab('applications')">Applications</button>
    <button class="tab-btn" onclick="switchTab('settings')">Settings</button>
  </div>

  <div id="tab-dashboard" class="tab-panel active">
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value" id="stat-total">0</div>
        <div class="stat-label">Total</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-active">0</div>
        <div class="stat-label">Active</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-interviews">0</div>
        <div class="stat-label">Interviews</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-offers">0</div>
        <div class="stat-label">Offers</div>
      </div>
    </div>

    <div class="empty-state">
      <div class="icon">&#128188;</div>
      <h3>No applications yet</h3>
      <p>Start tracking your job applications to see stats here.</p>
    </div>
  </div>

  <div id="tab-applications" class="tab-panel">
    <div class="empty-state">
      <div class="icon">&#128196;</div>
      <h3>Applications</h3>
      <p>Your job applications will appear here. Features coming soon.</p>
    </div>
  </div>

  <div id="tab-settings" class="tab-panel">
    <div class="empty-state">
      <div class="icon">&#9881;</div>
      <h3>Settings</h3>
      <p>Configuration options will appear here.</p>
    </div>
  </div>
</div>

<script>
const API_BASE = "/api/v1";

async function apiFetch(method, url, body) {
  const opts = { method };
  if (body) {
    opts.body = JSON.stringify(body);
    opts.headers = { "Content-Type": "application/json" };
  }
  const resp = await fetch(API_BASE + url, opts);
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    const msg = method + " " + url + " -> " + resp.status + " " + resp.statusText + (text ? ": " + text : "");
    throw new Error(msg);
  }
  return resp;
}

function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((btn, i) => {
    btn.classList.toggle("active", btn.textContent.toLowerCase().includes(name.toLowerCase()));
  });
  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === "tab-" + name);
  });
}

async function checkKbConnection() {
  const dot = document.getElementById("kb-dot");
  const text = document.getElementById("kb-status-text");
  try {
    const resp = await apiFetch("GET", "/health");
    const data = await resp.json();
    if (data.status === "ok") {
      dot.className = "connection-dot connected";
      text.textContent = "Connected";
    } else {
      dot.className = "connection-dot disconnected";
      text.textContent = "Degraded";
    }
  } catch (e) {
    dot.className = "connection-dot disconnected";
    text.textContent = "Disconnected";
  }
}

// Init
checkKbConnection();
</script>
</body>
</html>
"""
