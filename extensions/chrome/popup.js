"use strict";

const JAM_BASE = "http://localhost:8001";
const API_URL  = JAM_BASE + "/api/v1/applications/from-url";
const HEALTH_URL = JAM_BASE + "/api/v1/health";

const STATES = [
  "idle", "loading", "success",
  "error-server", "error-fetch", "error-llm", "error-generic",
];

let _currentTabUrl = "";

// ── State machine ────────────────────────────────────────────────────────────

function setState(name, payload = {}) {
  for (const s of STATES) {
    const el = document.getElementById("state-" + s);
    if (el) el.style.display = "none";
  }
  const target = document.getElementById("state-" + name);
  if (target) target.style.display = "";

  if (name === "success" && payload.data) {
    const d = payload.data;
    document.getElementById("result-company").textContent =
      d.application.company || "Unknown company";
    document.getElementById("result-position").textContent =
      d.application.position || "Unknown position";

    const kbBadge = document.getElementById("kb-badge");
    if (d.kb_ingested) {
      kbBadge.textContent = "KB ingested";
      kbBadge.className = "badge badge-kb-on";
    } else {
      kbBadge.textContent = "KB offline";
      kbBadge.className = "badge badge-kb-off";
    }
  }

  if (name === "error-fetch" && payload.detail) {
    document.getElementById("error-fetch-detail").textContent = payload.detail;
  }
  if (name === "error-llm" && payload.detail) {
    document.getElementById("error-llm-detail").textContent = payload.detail;
  }
  if (name === "error-generic" && payload.detail) {
    document.getElementById("error-generic-detail").textContent = payload.detail;
  }
}

// ── Health probe ─────────────────────────────────────────────────────────────

async function probeHealth() {
  const dotJam = document.getElementById("dot-jam");
  const dotKb  = document.getElementById("dot-kb");
  try {
    const resp = await fetch(HEALTH_URL, {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    });
    if (resp.ok) {
      const data = await resp.json();
      dotJam.classList.add("online");
      dotKb.classList.add(data.kb_status === "ok" ? "online" : "offline");
    } else {
      dotJam.classList.add("offline");
      dotKb.classList.add("offline");
    }
  } catch (_) {
    dotJam.classList.add("offline");
    // kb status unknown when jam is unreachable — leave dot gray
  }
}

// ── Tab info ─────────────────────────────────────────────────────────────────

async function loadTabInfo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;

    _currentTabUrl = tab.url || "";

    const titleEl = document.getElementById("page-title");
    const urlEl   = document.getElementById("page-url");
    const saveBtn = document.getElementById("save-btn");

    titleEl.textContent = tab.title || _currentTabUrl || "Unknown page";
    urlEl.textContent   = _currentTabUrl;

    if (
      !_currentTabUrl.startsWith("http://") &&
      !_currentTabUrl.startsWith("https://")
    ) {
      saveBtn.disabled = true;
      saveBtn.title    = "Only http/https pages can be ingested";
      titleEl.textContent = "This page cannot be ingested";
    }
  } catch (_) {
    document.getElementById("page-title").textContent = "Could not read tab info";
  }
}

// ── Save ─────────────────────────────────────────────────────────────────────

async function onSave() {
  if (!_currentTabUrl) return;

  setState("loading");

  try {
    const resp = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: _currentTabUrl }),
      // No AbortSignal — LLM extraction can legitimately take 30+ seconds
    });

    if (resp.ok) {
      const data = await resp.json();
      setState("success", { data });
      return;
    }

    let detail = "";
    try {
      const body = await resp.json();
      detail = body.detail || "";
    } catch (_) {
      detail = resp.statusText;
    }

    if (resp.status === 422) {
      setState("error-fetch", { detail });
    } else if (resp.status === 502) {
      setState("error-llm", { detail });
    } else {
      setState("error-generic", { detail: `HTTP ${resp.status}: ${detail}` });
    }
  } catch (err) {
    // TypeError: Failed to fetch → server unreachable (connection refused)
    if (err instanceof TypeError) {
      setState("error-server");
    } else {
      setState("error-generic", { detail: String(err) });
    }
  }
}

// ── Reset ─────────────────────────────────────────────────────────────────────

function onReset() {
  setState("idle");
  loadTabInfo();
}

// ── Init ──────────────────────────────────────────────────────────────────────

// Wire up event listeners — inline onclick is blocked by MV3 CSP
document.getElementById("save-btn").addEventListener("click", onSave);
document.getElementById("reset-success").addEventListener("click", onReset);
document.getElementById("reset-server").addEventListener("click", onReset);
document.getElementById("reset-fetch").addEventListener("click", onReset);
document.getElementById("reset-llm").addEventListener("click", onReset);
document.getElementById("reset-generic").addEventListener("click", onReset);

probeHealth();
loadTabInfo();
