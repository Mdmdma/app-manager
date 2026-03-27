# chrome-extension Knowledge
<!-- source: extensions/chrome/ -->
<!-- hash: a3f1c9d2e847 -->
<!-- updated: 2026-03-27 -->

## What it is

A Manifest V3 Chrome extension that ingests the currently open browser tab into
jam as a job application with one click. It calls the existing jam server API —
no new backend code is required.

## File structure

```
extensions/chrome/
├── manifest.json          MV3 manifest
├── popup.html             Extension popup — all state panels pre-rendered
├── popup.js               State machine, API calls, tab query
├── popup.css              Styles (320 px wide popup, all states)
└── icons/
    ├── icon16.png         Toolbar icon — solid indigo #4f46e5, 16×16 px
    ├── icon32.png         32×32 px
    └── icon48.png         48×48 px
```

No build step, no bundler, no external dependencies.

## Manifest permissions

| Permission | Why |
|---|---|
| `activeTab` | Read the current tab's URL and title from an action popup |
| `host_permissions: http://localhost:8001/*` | Required in MV3 for `fetch()` to localhost — CORS alone is not sufficient |

## API contract

| | |
|---|---|
| Ingest endpoint | `POST http://localhost:8001/api/v1/applications/from-url` |
| Request body | `{"url": "string"}` |
| Success (201) | `{application: {company, position, …}, extraction: {…}, kb_ingested: bool}` |
| Error 422 | URL fetch failed or page content too short |
| Error 502 | LLM extraction failed |
| Health endpoint | `GET http://localhost:8001/api/v1/health` → `{status: "ok", kb_status: "ok"\|"unreachable"}` |

`kb_ingested: false` in a success response means the jam server is up but the kb
server (port 8000) is unreachable — the application is still saved in jam's SQLite
database.

## UI state machine

```
open popup
    │
    ▼
  idle ─────── page title + URL, [Save job] button
               header shows jam dot (green/red) + kb dot (green/red/gray)
    │ click
    ▼
 loading ────── spinner + "Ingesting…" + "10–30 s" hint (LLM is slow)
    │
    ├─ 201 ──────► success ─────── company, position, KB badge, "Open jam UI ↗" link
    ├─ TypeError ► error-server ── server unreachable — shows start command
    ├─ 422 ──────► error-fetch ─── could not fetch/parse page
    ├─ 502 ──────► error-llm ───── LLM failed — check API key
    └─ other ────► error-generic ─ HTTP {status}: {detail}

  All non-idle states have "Try again / Save another page" → back to idle
```

## Key implementation details

- **State panels are pre-rendered** in `popup.html`; `setState(name, payload)` in
  `popup.js` shows/hides them. No `innerHTML` mutations with user-controlled data
  (XSS-safe, MV3 CSP compliant).
- **Health probe** fires on popup open with `AbortSignal.timeout(3000)`. It is
  non-blocking — the popup shows immediately regardless of probe outcome.
- **Ingest call has no timeout** — LLM extraction can legitimately take 30+ seconds.
- **Error classification**: `err instanceof TypeError` reliably detects connection
  refused in Chromium (server offline). HTTP 422 → fetch error, 502 → LLM error.
- **Non-http(s) pages** (`chrome://`, `about:`, new tab) disable the Save button
  with a tooltip rather than sending a doomed request.

## How to install / reload

**First install:**
1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select `extensions/chrome/`
3. Pin the icon via the puzzle-piece menu

**After modifying any file:**
- Go to `chrome://extensions` and click the **refresh icon** on the jam card
- No re-install needed

**Icons missing / corrupted:** regenerate with:
```bash
cd /home/mathis/Documents/app-manager && python3 -c "
import struct, zlib, os
def make_png(size, r, g, b):
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    raw = b''.join(b'\x00' + bytes([r, g, b] * size) for _ in range(size))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
os.makedirs('extensions/chrome/icons', exist_ok=True)
[open(f'extensions/chrome/icons/icon{sz}.png','wb').write(make_png(sz,79,70,229)) for sz in [16,32,48]]
"
```

## Known limitations

- Only `http://` and `https://` pages can be ingested. The button is disabled on
  other URL schemes.
- The extension talks to `http://localhost:8001` hard-coded. If `JAM_PORT` is
  changed from the default 8001, `popup.js` (`JAM_BASE` constant) must also be
  updated.
- There is no background service worker — the extension has no persistent state
  between popup opens.
