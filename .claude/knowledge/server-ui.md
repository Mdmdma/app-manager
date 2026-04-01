# server-ui Knowledge
<!-- source: jam/html_page.py -->
<!-- hash: 38107b4a7e00 -->
<!-- updated: 2026-04-01 -->

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
- Detail step layout: `.detail-step.active` uses `display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden` to maintain flex chain from `.detail-content` through to inner panels
- Flex height chain (viewport-constrained): `.detail-view` (`height: calc(100vh - 64px)`) → `.detail-container` (`height: 100%`) → `.detail-content` (`flex: 1; min-height: 0`) → `.detail-step.active` (`overflow: hidden`) → `.doc-tab-panel.active` (`overflow: hidden`) → `.trisplit-container` (`flex: 1`) → `.trisplit-pane` → `.trisplit-pane-body` (`min-height: 0`). Each element has `overflow: hidden` or `min-height: 0` to prevent content from pushing the layout taller than the viewport.
- `.detail-content.no-outer-scroll`: modifier class (applied via JS on cv-cover step) sets `overflow-y: hidden` so inner panels own their scroll
- Max-width: 1200px for dashboard, 912px card pattern for settings content

### Tabs / Views
- Dashboard: stats row (Total, Active, Interviews, Offers) + actions bar + applications grid
- Settings: Personal Info (default active), General, Connection, Knowledge Base, AI Models, Templates, System Prompts, Email / Gmail sections via sidebar
- Detail: multi-step navigation (App Details, CV & Cover Letters, Extra Questions, Interviews, Offers)

### Actions Bar (`div.actions-bar`)
- URL import form: `#import-url` input, `#import-btn` button, `#import-status` span
- "New Application" button (`.btn.btn-primary`, calls `openNewApplicationModal()`)

### Connection Status (Header)
Two side-by-side indicators in `.header-actions`:
- `#jam-status` / `#jam-dot` / `#jam-status-text` — jam server status
- `#kb-status` / `#kb-dot` / `#kb-status-text` — kb knowledge base status

### Personal Info Settings Section (`#section-personal-info`)
Default active settings tab. Five input fields for PDF metadata:
- `#personal-full-name` (text) — user's full name (used as PDF author)
- `#personal-email` (email)
- `#personal-phone` (tel)
- `#personal-website` (url)
- `#personal-address` (text)
- Profile Photo: file input → opens circular crop modal → stores cropped PNG data URI in `_stored.personal_photo`; preview displays as 120×120 circle (`border-radius: 50%`)
- Signature: file input → opens rectangle crop modal → stores cropped PNG data URI in `_stored.personal_signature`; preview max 250×80
- Save button calls `savePersonalInfo()`
- Status: `#personal-info-msg`

### Crop Modal (Profile Photo)
Lazy-built modal (`#crop-modal-overlay`, `.crop-modal-overlay`) for circular cropping of the profile photo. IIFE-scoped; exposes three window functions:
- `openCropModal(dataUri, previewId, settingKey)` — builds modal DOM on first call, loads image into `#crop-container`, creates overlay canvas sized to displayed image, initialises circle to largest inscribed circle
- `closeCropModal()` — hides modal, removes listeners, disconnects ResizeObserver, resets file input
- `applyCrop()` — scales circle from display to natural image coords, draws circular-clipped region to offscreen canvas, exports as PNG data URI with transparency outside circle, updates `_stored` and preview
Interaction:
- Drag inside circle → move; drag handle (indigo square at 45° on perimeter) → resize; scroll wheel → resize
- Circle clamped to image bounds, minimum radius 25px
- Dark semi-transparent overlay outside circle; indigo (#4f46e5) circle border
CSS classes: `.crop-modal-overlay`, `.crop-modal`, `.crop-container`, `.crop-overlay-canvas`, `.crop-modal-title`, `.crop-modal-hint`, `.crop-modal-footer`

### Rectangle Crop Modal (Signature)
Lazy-built modal (`#rect-crop-modal-overlay`, `.rect-crop-modal-overlay`) for rectangular cropping of the signature. IIFE-scoped; exposes three window functions:
- `openRectCropModal(dataUri, previewId, settingKey)` — builds modal DOM on first call, loads image, creates overlay canvas, initialises rectangle to 3:1 wide aspect ratio centred on image
- `closeRectCropModal()` — hides modal, removes listeners, disconnects ResizeObserver, resets file input
- `applyRectCrop()` — scales rectangle from display to natural image coords, draws region to offscreen canvas, exports as PNG data URI, updates `_stored` and preview
Interaction:
- Drag inside rectangle → move; drag any of 8 corner/edge handles → resize
- Rectangle clamped to image bounds, minimum 50px wide / 20px tall
- Dark semi-transparent overlay outside rectangle; indigo (#4f46e5) rectangle border
CSS classes: `.rect-crop-modal-overlay`, `.rect-crop-modal`, `.rect-crop-container`, `.rect-crop-overlay-canvas`, `.rect-crop-modal-title`, `.rect-crop-modal-hint`, `.rect-crop-modal-footer`

### Connection Settings Section (`#section-connection`)
Three rows:
- "jam Server": `#jam-settings-dot`, `#jam-settings-display`
- "Knowledge Base": `#kb-settings-dot`, `#kb-settings-display`
- "KB API URL": `#kb-url-display` (read-only)

### Knowledge Base Settings Section (`#section-knowledge-base`)
Four setting groups:
- "Search Namespaces": `#kb-search-namespaces` div — dynamic checkboxes loaded from `GET /kb/namespaces`
- "Retrieved Chunks": `#kb-n-results` number input (1–50, default 5)
- "Padding": `#kb-padding` number input (0–10, default 0)
- "Include Entire Namespaces": `#kb-include-namespaces` div — dynamic checkboxes loaded from `GET /kb/namespaces`
- Status: `#kb-settings-msg`
- Save button calls `saveKbSettings()`

### CV & Cover Letters Step (`#step-cv-cover`)
Full tri-split LaTeX editor with two document types (CV, Cover Letter):
- Tab bar (`.tab-bar`) with `.tab-btn-doc` buttons switching between `doc-panel-cv` and `doc-panel-cover_letter`
- Each panel has:
  - `.doc-list-bar`: document selector (`<select>`), New/Save/Compile/Generate/Delete/Rename buttons, status span
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
- Pane header has a "Clear" button (`_clearInstructions(docType)`) that empties all textareas and triggers debounced auto-save

### Generation Progress Tracker
Horizontal multi-step progress bar shown during document generation. One tracker per doc type: `#cv-gen-progress`, `#cover_letter-gen-progress` (placed between doc-list-bar and trisplit-container, `aria-live="polite"`).
- Built dynamically by `_initGenProgress()` from `_GEN_STEP_ORDER` (8 steps: Retrieve KB → Generate → Analyze fit → Check quality → Apply improvements → Compile → Reduce size → Finalize)
- Each step has a fixed 16×16px `.step-icon` container to prevent layout shift; states: pending (gray dot), active (indigo spinner reusing `@keyframes spin`), completed (green ✓), error (red ✗)
- Steps separated by `›` characters (`.gen-progress-sep`)
- `_generateDoc` uses `_initGenProgress` → `_updateGenProgress` per SSE node → `_completeGenProgress` on done / `_errorGenProgress` on error
- `_critiqueDoc` still uses `_setGenStatus` text-only approach (no tracker)
- Conditional steps (e.g. `reduce_size`) stay pending-gray if skipped; all marked green on done

### Per-Step Model Overrides (inside AI Models section)
Collapsible `<details>` section below global provider/model dropdowns.
- Container: `#step-model-overrides` inside `<details class="step-models-details">`
- JS constant: `_STEP_MODEL_META` — array of `{key, label}` for 5 generation steps
- Each row: flex layout with step label + `<select class="field-input">` dropdown
- Options: "Use global default" (value="") + `<optgroup>` per provider with models from `_catalog`
- Values use catalog model ID format: `"provider:model_id"` (e.g. `"openai:gpt-4o"`)
- Auto-saves on change, updates `_stored`, shows success toast via `#ai-settings-msg`

### System Prompts Settings Section (`#section-prompts`)
Six textareas for editing the system prompts used by the agentic generation pipeline:
- `#prompt-generate-first` — first-time generation prompt
- `#prompt-generate-revise` — revision prompt
- `#prompt-analyze-fit` — fit analysis prompt
- `#prompt-analyze-quality` — quality review prompt
- `#prompt-apply-suggestions` — apply suggestions prompt
- `#prompt-reduce-size` — reduce size prompt
Each has a "Reset to default" button calling `resetPrompt(key)`.
- Defaults loaded via `GET /prompts/defaults` and cached in `_promptDefaults`
- Save button calls `savePromptSettings()` — only saves values differing from defaults
- Status: `#prompt-settings-msg`

### CSS Classes (from shared design system)
- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-sm`, `.btn-green`
- Badges: `.badge`, `.badge-applied`, `.badge-screening`, `.badge-interviewing`, `.badge-offered`, `.badge-rejected`, `.badge-accepted`, `.badge-withdrawn`
- Forms: `.field-label`, `.field-input`
- Layout: `.card`, `.modal`, `.modal-overlay`, `.modal-header`, `.modal-body`, `.modal-footer`
- Status: `.status-msg`, `.status-msg.success`, `.status-msg.error`
- Custom: `.stats-row`, `.stat-card`, `.connection-status`, `.connection-dot`, `.actions-bar`, `.applications-grid`, `.app-tile`, `.empty-state`
- Settings: `.settings-container`, `.settings-sidebar`, `.settings-sidebar-menu`, `.settings-content`, `.settings-section`
- Document editor: `.tab-bar`, `.tab-btn-doc`, `.doc-tab-panel`, `.trisplit-container`, `.trisplit-pane`, `.trisplit-pane-header`, `.trisplit-pane-body`, `.doc-list-bar`, `.doc-preview-frame`, `.doc-version-bar`, `.doc-compile-status`, `.agent-feedback-panel` (max-height: 40vh, overflow-y: auto, flex-shrink: 1), `.feedback-text` (max-height: 200px, overflow-y: auto)
- Generation progress: `.gen-progress-tracker` (flex row below doc-list-bar), `.gen-progress-step` (`.completed` green ✓, `.active` spinner, `.error` red ✗), `.gen-progress-sep` (› separator), `.step-icon` (fixed 16×16px to prevent layout shift)
- Instructions panel: `.instructions-panel`, `.instruction-field`, `.instruction-field.global`, `.instruction-field-header`, `.instruction-field-title`, `.instruction-toggle-wrap`, `.instruction-toggle-label`, `.instruction-toggle`, `.instruction-toggle-slider`, `.instruction-textarea`
- PDF viewer: `.pdf-placeholder` (centered message div), `.pdf-canvas-page` (per-page canvas element)
- Crop modal (circle): `.crop-modal-overlay`, `.crop-modal`, `.crop-container`, `.crop-overlay-canvas`, `.crop-modal-title`, `.crop-modal-hint`, `.crop-modal-footer`
- Crop modal (rect): `.rect-crop-modal-overlay`, `.rect-crop-modal`, `.rect-crop-container`, `.rect-crop-overlay-canvas`, `.rect-crop-modal-title`, `.rect-crop-modal-hint`, `.rect-crop-modal-footer`

### JS Helpers
- `apiFetch(method, url, body)` — central API wrapper (prepends `/api/v1`); always sets `cache: "no-store"` to prevent stale browser caching
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
- `loadAiSettings()` — GET `/catalog` + GET `/settings`, populates AI settings, then calls `renderStepModelOverrides()`
- `renderProviderDropdown()` — fills `#ai-provider` select
- `renderStepModelOverrides()` — builds per-step model override dropdowns in `#step-model-overrides` container; each dropdown has "Use global default" + grouped `<optgroup>` per provider from catalog; auto-saves on change via `POST /settings` with `step_model_*` key
- `onProviderChange()` — updates model dropdown and credential fields on provider change
- `renderCredentialFields(prov)` — builds credential input fields with show/hide toggle
- `saveAiSettings()` — POST `/settings` with current AI config
- `loadKbSettings()` — reads `_stored` and sets numeric fields (`#kb-n-results`, `#kb-padding`) synchronously first, then fetches GET `/kb/namespaces` and renders namespace checkboxes; `parseInt(x) || default` replaced with null-check + isNaN guard to handle value `0` correctly
- `saveKbSettings()` — collects checked namespaces and numeric values, POST `/settings`
- `loadTemplateSettings()` — populates template textareas from `_stored` or defaults
- `saveTemplateSettings()` — POST `/settings` with template values
- `loadPromptDefaults()` — GET `/prompts/defaults`, caches in `_promptDefaults`
- `loadPromptSettings()` — populates 6 prompt textareas from `_stored` or defaults
- `savePromptSettings()` — POST `/settings` with prompt values (only saves values that differ from defaults)
- `resetPrompt(key)` — resets a single prompt textarea to its default value
- `loadPersonalInfo()` — reads from `_stored` to populate personal info fields (called after `loadAiSettings` in `switchToSettings`)
- `savePersonalInfo()` — POST `/settings` with 5 personal info fields, updates `_stored` via `Object.assign`
- `loadGmailSettings()` — GET `/gmail/status` + GET `/settings`, populates Gmail fields
- `saveGmailCredentials()` — POST `/settings` with Gmail OAuth credentials
- `connectGmail()` — GET `/gmail/auth-url`, opens auth URL in new window
- `disconnectGmail()` — POST `/gmail/disconnect`
- `openDetailPage(appId)` — loads application, resets doc state, shows detail view
- `switchDetailStep(step)` — activates detail step panel; lazy-loads CV docs on first visit; toggles `.no-outer-scroll` on `.detail-content` (added for cv-cover, removed for other steps)
- `_switchDocTab(docType)` — switches between cv/cover_letter document tabs
- `_loadDocuments(docType)` — GET `/applications/:id/documents?doc_type=<type>`, populates selector
- `_clearEditor(docType)` — calls `_buildInstructionsFromLatex(docType, '')`, clears latex editor (`setValue("")`) and sets preview div to "No document selected" placeholder
- `_loadDocIntoEditor(docType, doc)` — calls `_buildInstructionsFromLatex` + `_setInstructionsFromJson`, fills latex editor via `setValue(doc.latex_source)`, tries to load cached PDF via `HEAD /documents/:id/pdf` (shows preview if available, falls back to placeholder)
- `_onDocSelect(docType)` — handles select change, loads selected doc into editor
- `_createDoc(docType)` — prompts user for document name, POST `/applications/:id/documents`, inserts into list
- `_saveCurrentDoc(docType)` — PUT `/documents/:id` with current editor content; reads latex via `_cmEditors[docType].getValue()`; reads `prompt_text` via `_getInstructionsAsJson(docType)`
- `_deleteCurrentDoc(docType)` — DELETE `/documents/:id` with confirmation
- `_renameCurrentDoc(docType)` — prompts user for new name, PUT `/documents/:id` with `{title}`, updates dropdown option text
- `_onLatexInput(docType)` — debounces `_saveCurrentDoc` on CodeMirror change (2000ms auto-save); wired via `cm.on('change', ...)`
- `_scheduleInstructionSave(docType)` — debounces `_saveCurrentDoc` on instruction field changes (2000ms auto-save); called from `oninput` on instruction textareas and `onchange` on toggle checkboxes
- `_initCmEditors()` — initialises CodeMirror 5 on both latex textareas; stores instances in `_cmEditors`; called at page init
- `_makeInstructionField(docType, key, label, isGlobal)` — builds and returns one `.instruction-field` DOM element; `isGlobal=true` adds `.global` class and omits toggle; sets `data-section-key` attribute
- `_clearInstructions(docType)` — empties all `.instruction-textarea` values in the panel and triggers `_scheduleInstructionSave`
- `_buildInstructionsFromLatex(docType, latex)` — (re)builds `#${docType}-instructions-panel`; always starts with global field; for CV parses `\section{Name}` occurrences; for cover_letter splits by blank lines; preserves existing textarea values and toggle states for matching keys
- `_getInstructionsAsJson(docType)` — serialises panel state to JSON string `{general, sections:[{key,label,text,enabled}]}`; returns `""` if panel is empty
- `_setInstructionsFromJson(docType, jsonStr)` — populates existing fields from JSON string; handles invalid JSON gracefully (no crash)
- `_renderPdf(docType, url)` — async; renders PDF via PDF.js into `#<type>-preview-frame` div, one canvas per page; shows "Loading PDF…" then replaces with canvases or "Failed to load PDF" on error
- `_compileDoc(docType)` — saves doc (reads latex via `getValue()`, instructions via `_getInstructionsAsJson`), POST `/documents/:id/compile`, calls `_renderPdf` with cache-busting URL (does not create a version)
- `_loadVersions(docType)` — GET `/documents/:id/versions`, renders version buttons
- `_restoreVersion(docType, version)` — restores latex source via `setValue(version.latex_source)`, rebuilds instruction panel from latex, populates from version prompt_text JSON, and saves (no auto-compile)
- `_initGenProgress(docType)` — builds step tracker from `_GEN_STEP_ORDER`, shows `#<type>-gen-progress` container
- `_updateGenProgress(docType, activeNode)` — promotes previous active step to completed, marks new node active
- `_completeGenProgress(docType)` — marks all steps completed (green) on generation done
- `_errorGenProgress(docType)` — marks current active step as error (red)
- `_hideGenProgress(docType)` — hides and clears the tracker
- `_setDocStatus(docType, msg, cls)` — updates status span; clears after 3s on success
- `_togglePane(containerId, paneIndex)` — collapses/expands a trisplit pane
- `openCropModal(dataUri, previewId, settingKey)` — opens circular crop modal for profile photo
- `closeCropModal()` — closes crop modal, cleans up listeners
- `applyCrop()` — exports circular-cropped PNG and updates preview/stored
- `openRectCropModal(dataUri, previewId, settingKey)` — opens rectangle crop modal for signature
- `closeRectCropModal()` — closes rectangle crop modal, cleans up listeners
- `applyRectCrop()` — exports rectangular-cropped PNG and updates preview/stored

### Auto-save / Compile behaviour
- **Auto-save**: CodeMirror `change` event triggers `_onLatexInput` → debounces `_saveCurrentDoc` (2000ms). Instruction textarea and toggle changes trigger `_saveCurrentDoc` via `_scheduleInstructionSave` (same 2-second debounce, shared `_saveTimers`). This persists edits to the DB without compilation.
- **Compile**: Explicit action via the "Compile" button or `Ctrl-Enter` inside the CodeMirror editor. Saves first (reads instructions via `_getInstructionsAsJson`), then compiles via backend. Does NOT create a version — versions are only created on Generate. No auto-compile on load or typing.
- **Document switching**: When switching documents via the dropdown, `_loadDocIntoEditor` tries a `HEAD` request to the PDF endpoint. If a cached PDF exists, it renders immediately; otherwise shows a placeholder.
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
- Settings view sections (General, Connection) are read-only displays; Personal Info is editable
- Stats are computed client-side from the full applications list
- Import status message persists until next import attempt (not auto-cleared)
- LaTeX compilation requires backend `/documents/:id/compile` endpoint
- LLM generation via instruction panel is marked "coming soon"
- PDF cache is server-side in-memory; PDFs lost on server restart
- CodeMirror and PDF.js are loaded from cdnjs CDN; requires network access at runtime
- Instruction panel rebuild only happens on document load / version restore, not on live LaTeX edits
- CodeMirror placeholder not shown (textarea placeholder attribute hidden once CM wraps the element)
- KB namespace checkboxes require knowledge base to be running; shows fallback message if unavailable
