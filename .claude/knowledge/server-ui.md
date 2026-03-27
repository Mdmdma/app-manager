# server-ui Knowledge
<!-- source: jam/html_page.py -->
<!-- hash: 9beff8cf6df1 -->
<!-- updated: 2026-03-27 -->

## Public API

| Constant | Type | Purpose |
|---|---|---|
| `HTML_PAGE` | `str` | Complete HTML document with inline CSS and JS |

## Key Components

### Layout
- Header: app title + two connection indicators (jam + kb), click title to return to dashboard
- Dashboard view (`#dashboard-view`): stats row + actions bar + applications container
- Settings view (`#settings-view`): sidebar nav + content panels
- Detail view (`#detail-view`): sidebar with application info + step navigation + step panels
- Max-width: 1200px for dashboard, 912px card pattern for settings content

### Tabs / Views
- Dashboard: stats row (Total, Active, Interviews, Offers) + actions bar + applications grid
- Settings: General, Connection, AI Models sections via sidebar
- Detail: multi-step navigation (App Details, CV & Cover Letters, Extra Questions, Interview rounds, Offer)

### Actions Bar (`div.actions-bar`)
- URL import form: `#import-url` input, `#import-btn` button, `#import-status` span
- "New Application" button (`.btn.btn-primary`, calls `openNewApplicationModal()`)

### Connection Status (Header)
Two side-by-side indicators in `.header-actions`:
- `#jam-status` / `#jam-dot` / `#jam-status-text` — jam server status
- `#kb-status` / `#kb-dot` / `#kb-status-text` — kb knowledge base status

### Connection Settings Section (`#section-connection`)
Three rows:
- "jam Server": `#jam-settings-dot`, `#jam-settings-display`
- "Knowledge Base": `#kb-settings-dot`, `#kb-settings-display`
- "KB API URL": `#kb-url-display` (read-only)

### CV & Cover Letters Step (`#step-cv-cover`)
Full tri-split LaTeX editor with two document types (CV, Cover Letter):
- Tab bar (`.tab-bar`) with `.tab-btn-doc` buttons switching between `doc-panel-cv` and `doc-panel-cover_letter`
- Each panel has:
  - `.doc-list-bar`: document selector (`<select>`), New/Save/Compile/Delete buttons, status span
  - `.trisplit-container` with three panes:
    - Pane 0 (25%): Instructions panel (`#<type>-instructions-panel`) — structured per-section instruction fields with debounced auto-save
    - Pane 1 (37.5%): LaTeX source — CodeMirror 5 editor (`#<type>-latex-editor` textarea, upgraded via `_initCmEditors()`)
    - Pane 2 (37.5%): PDF preview div (`#<type>-preview-frame`) — canvas-based PDF.js viewer (no iframe)
  - `.doc-version-bar`: version history buttons

### CodeMirror Editor (Pane 1)
The LaTeX textareas are upgraded to CodeMirror 5 at init time via `_initCmEditors()`.
- CDN scripts loaded in `<head>`: `codemirror.min.js`, `mode/stex/stex.min.js`, `addon/edit/closebrackets.min.js`, `codemirror.min.css` — all version 5.65.16 from cdnjs
- Mode: `stex` (LaTeX/TeX) — `%` comments rendered in a distinct color
- `autoCloseBrackets: true` — `{`, `[`, `(`, `"`, `'` auto-close on type
- `extraKeys`: `Ctrl-Enter` / `Cmd-Enter` → `_compileDoc(docType)`
- Editor instances stored in `_cmEditors = { cv: null, cover_letter: null }`
- All reads use `_cmEditors[docType].getValue()`, all writes use `_cmEditors[docType].setValue(...)`
- CSS: `.trisplit-pane-body .CodeMirror` has `flex:1; height:100%; min-height:0` to fill the flex pane

### Instructions Panel (`#<type>-instructions-panel`)
Scrollable `.instructions-panel` div inside pane 0. Built dynamically by `_buildInstructionsFromLatex()`.
- Always has a global field (`data-section-key="__global__"`, `.global` class, no toggle)
- For CV: one `.instruction-field` per unique `\section{Name}` in LaTeX source
- For cover letters: one field per paragraph block (>10 chars, separated by blank lines), keyed `__para_N__`
- Each non-global field has a "restrict edits" toggle (checkbox)
- State serialised to JSON via `_getInstructionsAsJson()` and stored in `prompt_text` field

### CSS Classes (from shared design system)
- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-sm`, `.btn-green`
- Badges: `.badge`, `.badge-applied`, `.badge-screening`, `.badge-interviewing`, `.badge-offered`, `.badge-rejected`, `.badge-accepted`, `.badge-withdrawn`
- Forms: `.field-label`, `.field-input`
- Layout: `.card`, `.modal`, `.modal-overlay`, `.modal-header`, `.modal-body`, `.modal-footer`
- Status: `.status-msg`, `.status-msg.success`, `.status-msg.error`
- Custom: `.stats-row`, `.stat-card`, `.connection-status`, `.connection-dot`, `.actions-bar`, `.applications-grid`, `.app-tile`, `.empty-state`
- Settings: `.settings-container`, `.settings-sidebar`, `.settings-sidebar-menu`, `.settings-content`, `.settings-section`
- Document editor: `.tab-bar`, `.tab-btn-doc`, `.doc-tab-panel`, `.trisplit-container`, `.trisplit-pane`, `.trisplit-pane-header`, `.trisplit-pane-body`, `.doc-list-bar`, `.doc-preview-frame`, `.doc-version-bar`, `.doc-compile-status`
- Instructions panel: `.instructions-panel`, `.instruction-field`, `.instruction-field.global`, `.instruction-field-header`, `.instruction-field-title`, `.instruction-toggle-wrap`, `.instruction-toggle-label`, `.instruction-toggle`, `.instruction-toggle-slider`, `.instruction-textarea`
- PDF viewer: `.pdf-placeholder` (centered message div), `.pdf-canvas-page` (per-page canvas element)

### JS Helpers
- `apiFetch(method, url, body)` — central API wrapper (prepends `/api/v1`)
- `loadApplications()` — fetches `GET /applications`, calls `renderApplications()` + `updateStats()`
- `renderApplications()` — populates `#applications-container` with grid or empty state
- `updateStats()` — updates `#stat-total/active/interviewing/offers`
- `escapeHtml(text)` — XSS-safe text escaping
- `openNewApplicationModal()` — opens modal for creating a new application
- `openEditApplicationModal(appId)` — fetches and opens edit modal
- `closeApplicationModal()` — closes modal, clears `currentEditingId`
- `handleApplicationFormSubmit(event)` — POST or PUT to `/applications[/:id]`
- `handleDelete()` — DELETE `/applications/:id` with confirmation
- `importFromUrl()` — POST `/applications/from-url` with `{url}`, updates status span, reloads list
- `switchToSettings()` / `switchToDashboard()` — toggle main views
- `switchSettingsSection(section)` — activate settings sidebar section
- `checkKbConnection()` — GET `/health`, updates both jam and kb header/settings indicators
- `loadAiSettings()` — GET `/catalog` + GET `/settings`, populates AI settings
- `renderProviderDropdown()` — fills `#ai-provider` select
- `onProviderChange()` — updates model dropdown and credential fields on provider change
- `renderCredentialFields(prov)` — builds credential input fields with show/hide toggle
- `saveAiSettings()` — POST `/settings` with current AI config
- `openDetailPage(appId)` — loads application, resets doc state, shows detail view
- `switchDetailStep(step)` — activates detail step panel; lazy-loads CV docs on first visit
- `_switchDocTab(docType)` — switches between cv/cover_letter document tabs
- `_loadDocuments(docType)` — GET `/applications/:id/documents?doc_type=<type>`, populates selector
- `_clearEditor(docType)` — calls `_buildInstructionsFromLatex(docType, '')`, clears latex editor (`setValue("")`) and sets preview div to "No document selected" placeholder
- `_loadDocIntoEditor(docType, doc)` — calls `_buildInstructionsFromLatex` + `_setInstructionsFromJson`, fills latex editor via `setValue(doc.latex_source)`, sets preview div placeholder (no auto-compile)
- `_onDocSelect(docType)` — handles select change, loads selected doc into editor
- `_createDoc(docType)` — POST `/applications/:id/documents`, inserts into list
- `_saveCurrentDoc(docType)` — PUT `/documents/:id` with current editor content; reads latex via `_cmEditors[docType].getValue()`; reads `prompt_text` via `_getInstructionsAsJson(docType)`
- `_deleteCurrentDoc(docType)` — DELETE `/documents/:id` with confirmation
- `_onLatexInput(docType)` — debounces `_saveCurrentDoc` on CodeMirror change (2000ms auto-save); wired via `cm.on('change', ...)`
- `_scheduleInstructionSave(docType)` — debounces `_saveCurrentDoc` on instruction field changes (2000ms auto-save); called from `oninput` on instruction textareas and `onchange` on toggle checkboxes
- `_initCmEditors()` — initialises CodeMirror 5 on both latex textareas; stores instances in `_cmEditors`; called at page init
- `_makeInstructionField(docType, key, label, isGlobal)` — builds and returns one `.instruction-field` DOM element; `isGlobal=true` adds `.global` class and omits toggle; sets `data-section-key` attribute
- `_buildInstructionsFromLatex(docType, latex)` — (re)builds `#${docType}-instructions-panel`; always starts with global field; for CV parses `\section{Name}` occurrences; for cover_letter splits by blank lines; preserves existing textarea values and toggle states for matching keys
- `_getInstructionsAsJson(docType)` — serialises panel state to JSON string `{general, sections:[{key,label,text,enabled}]}`; returns `""` if panel is empty
- `_setInstructionsFromJson(docType, jsonStr)` — populates existing fields from JSON string; handles invalid JSON gracefully (no crash)
- `_renderPdf(docType, url)` — async; renders PDF via PDF.js into `#<type>-preview-frame` div, one canvas per page; shows "Loading PDF…" then replaces with canvases or "Failed to load PDF" on error
- `_compileDoc(docType)` — saves doc (reads latex via `getValue()`, instructions via `_getInstructionsAsJson`), POST `/documents/:id/compile`, calls `_renderPdf` with cache-busting URL
- `_loadVersions(docType)` — GET `/documents/:id/versions`, renders version buttons
- `_restoreVersion(docType, version)` — restores latex source via `setValue(version.latex_source)`, rebuilds instruction panel from latex, populates from version prompt_text JSON, and saves (no auto-compile)
- `_setDocStatus(docType, msg, cls)` — updates status span; clears after 3s on success
- `_togglePane(containerId, paneIndex)` — collapses/expands a trisplit pane

### Auto-save / Compile behaviour
- **Auto-save**: CodeMirror `change` event triggers `_onLatexInput` → debounces `_saveCurrentDoc` (2000ms). Instruction textarea and toggle changes trigger `_saveCurrentDoc` via `_scheduleInstructionSave` (same 2-second debounce, shared `_saveTimers`). This persists edits to the DB without compilation.
- **Compile**: Explicit action via the "Compile" button or `Ctrl-Enter` inside the CodeMirror editor. Saves first (reads instructions via `_getInstructionsAsJson`), then compiles via backend, creates a version checkpoint. No auto-compile on load or typing.
- **Version restore**: Rebuilds instruction panel from version LaTeX, populates from version prompt_text, saves.
- **prompt_text storage format**: JSON string `{"general":"...","sections":[{"key":"...","label":"...","text":"...","enabled":true},...]}`. Old plain-text values fail JSON parse and are treated as empty (backward-compatible).

### PDF preview (PDF.js canvas)
- After compilation, `_renderPdf(docType, url)` is called with `/api/v1/documents/{doc_id}/pdf?t={timestamp}`
- PDF.js (`pdf.min.js` from cdnjs, version 3.11.174) renders each page as a `<canvas class="pdf-canvas-page">` inside the preview div
- Worker configured via `pdfjsLib.GlobalWorkerOptions.workerSrc` pointing to `pdf.worker.min.js` on cdnjs
- `_currentPdfUrl[docType]` stores the base URL without query param for download
- No iframe or blob URLs; avoids Vivaldi/Chromium sandbox blocking
- 404 returned if document has not yet been compiled

### Design Tokens Used
- Primary: `#4f46e5` (indigo)
- Primary hover: `#4338ca`
- Success: `#10b981` (green), `#059669` (compiled success)
- Error: `#dc2626` (red), `#ef4444` (validation red)
- Background: `#f0f2f5`
- Card: `#ffffff`, radius `16px`
- Border: `#e5e7eb`, border-dark `#d1d5db`
- Text: `#1a1a2e` primary, `#6b7280` secondary, `#9ca3af` muted, `#16213e` heading
- Instructions panel global: `#a5b4fc` border, `#eef2ff` background, `#4f46e5` title
- Instructions panel surface: `#f9fafb` panel background, `#fff` field background

## Dependencies
- Imports from: (none — standalone constant)
- Imported by: `jam/server.py`
- External scripts (loaded at runtime in `<head>`):
  - PDF.js 3.11.174 via cdnjs
  - CodeMirror 5.65.16 (core + stex mode + closebrackets addon) via cdnjs

## Testing
- Tested indirectly via `test_server.py` (checks HTML content in response)

## Known Limitations
- Settings view sections (General, Connection) are read-only displays
- Stats are computed client-side from the full applications list
- Import status message persists until next import attempt (not auto-cleared)
- LaTeX compilation requires backend `/documents/:id/compile` endpoint
- LLM generation via instruction panel is marked "coming soon"
- PDF cache is server-side in-memory; PDFs lost on server restart
- CodeMirror and PDF.js are loaded from cdnjs CDN; requires network access at runtime
- Instruction panel rebuild only happens on document load / version restore, not on live LaTeX edits
- CodeMirror placeholder not shown (textarea placeholder attribute hidden once CM wraps the element)
