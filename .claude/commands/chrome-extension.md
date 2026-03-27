# Chrome Extension Setup

Guides the user through loading and verifying the jam Chrome extension.

## Steps

### 1. Verify extension files exist

Check that all required files are present:
```bash
ls extensions/chrome/manifest.json extensions/chrome/popup.html \
   extensions/chrome/popup.js extensions/chrome/popup.css \
   extensions/chrome/icons/icon16.png extensions/chrome/icons/icon32.png \
   extensions/chrome/icons/icon48.png
```

If any file is missing, tell the user which file is absent and stop. Do not
attempt to regenerate files — ask the user to re-run the implementation.

If the `icons/` directory is empty or missing PNGs, offer to regenerate them:
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
print('Icons regenerated.')
"
```

### 2. Ensure the jam server is running

```bash
curl -s --max-time 2 http://localhost:8001/api/v1/health
```

- If the server responds: note whether `kb_status` is `"ok"` or `"unreachable"` and
  inform the user. The extension will show this via the status dots in its header.
- If the server does not respond: tell the user to run `/start` first so they can
  test the extension end-to-end, then continue with the setup steps below.

### 3. Print installation instructions

Tell the user to follow these steps **in Chrome**:

---

**Step 1 — Open the extensions page**
Navigate to `chrome://extensions` in your address bar.

**Step 2 — Enable Developer mode**
Toggle **Developer mode** on (top-right corner of the page).

**Step 3 — Load the extension**
Click **Load unpacked** and select this directory:
```
/home/mathis/Documents/app-manager/extensions/chrome
```

**Step 4 — Pin the icon**
Click the **puzzle-piece icon** (🧩) in the Chrome toolbar, find
"jam — Job Application Manager", and click the **pin** icon so it always shows.

---

### 4. Verify the extension loads

Ask the user to confirm the extension appeared without errors. Common issues:

| Symptom | Fix |
|---|---|
| "Manifest file is missing or unreadable" | Wrong directory selected — re-select `extensions/chrome/` not `extensions/` |
| "Could not load icon" | Icons missing — regenerate them (see Step 1 above) |
| Extension loaded but popup is blank | Open DevTools on the popup (right-click icon → Inspect popup) and share the console error |
| "Could not establish connection" on first click | Normal on non-http pages — navigate to an `http://` or `https://` URL first |

### 5. Run a quick end-to-end test

Ask the user to:
1. Navigate to any public job posting URL (e.g. a LinkedIn or Greenhouse job page)
2. Click the jam icon
3. Confirm the idle state shows the page title and URL
4. Click **Save job** and wait for the result

Expected results:
- **Success**: company name and position appear, KB badge shows "KB ingested" or "KB offline"
- **Loading indicator visible**: if it disappears instantly, the server may have returned an error — check the popup DevTools console

### 6. After code changes

If any extension file is modified, Chrome requires a **manual reload**:
1. Go to `chrome://extensions`
2. Click the **refresh icon** on the jam extension card

Changes to `popup.html`, `popup.js`, or `popup.css` take effect immediately after
reload — no re-install needed.
