# server-ui Knowledge
<!-- source: jam/html_page.py -->
<!-- hash: a542aaf2ee04 -->
<!-- updated: 2026-04-21 -->

## Public API

| Constant | Type | Purpose |
|---|---|---|
| `HTML_PAGE` | `str` | Complete HTML document with inline CSS and JS |

## Key Components

### Layout
- Header: app title + three connection indicators (jam + kb + proxy), click title to return to dashboard
- Dashboard view (`#dashboard-view`): stats row + actions bar + applications container
- Settings view (`#settings-view`): sidebar nav + content panels
- Detail view (`#detail-view`): sidebar with application info + step navigation + step panels
- Detail step layout: base `.detail-step.active` is `display: block` so the parent `.detail-content` (`overflow-y: auto`) handles scrolling for long-form steps (App Details, Extra Questions, Interviews, Offers)
- cv-cover override: `#step-cv-cover.active` uses `display: flex; flex-direction: column; flex: 1; min-height: 0` to maintain the flex height chain needed by the trisplit editor; JS toggles `.detail-content.no-outer-scroll` only for this step so inner panels own their scroll
- Flex height chain (cv-cover only, viewport-constrained): `.detail-view` (`height: calc(100vh - 64px)`) → `.detail-container` (`height: 100%`) → `.detail-content.no-outer-scroll` (`flex: 1; min-height: 0; overflow-y: hidden`) → `#step-cv-cover.active` (flex column, `min-height: 0`) → `.doc-tab-panel.active` (`overflow: hidden`) → `.trisplit-container` (`flex: 1`) → `.trisplit-pane` → `.trisplit-pane-body` (`min-height: 0`). Each element has `overflow: hidden` or `min-height: 0` to prevent content from pushing the layout taller than the viewport.
- `.detail-content.no-outer-scroll`: modifier class (applied via JS on cv-cover step) sets `overflow-y: hidden` so inner panels own their scroll
- Max-width: 1200px for dashboard, 912px card pattern for settings content

### Tabs / Views
- Dashboard: stats row (Total, Active, Interviews, Offers) + actions bar + applications grid
- Settings: Personal Info (default active), General, Connection, Knowledge Base, AI Models, Templates, System Prompts, Email / Gmail, Outlook Calendar sections via sidebar
- Detail: multi-step navigation (App Details, CV & Cover Letters, Extra Questions, Interviews, Offers)

### Actions Bar (`div.actions-bar`)
- URL import form: `#import-url` input, `#import-btn` button, `#import-status` span
- "New Application" button (`.btn.btn-primary`, calls `openNewApplicationModal()`)

### New Application Modal — paste-JD top field
- `#form-jd-group` is the first child of `.modal-body` (above Company Name)
- Contains `<label for="form-jd-text">Paste Job Description</label>`, a helper hint, and `<textarea id="form-jd-text" rows="6">` (resize vertical)
- On submit: if textarea is non-empty **and** `currentEditingId` is null, the form calls `POST /applications/from-text` instead of the manual create path; the LLM populates all extracted fields and the modal closes on success. If the textarea is empty, the existing manual create/update flow runs unchanged
- `openNewApplicationModal()` clears `#form-jd-text` and restores the submit button's `disabled = false` / `textContent = "Save"` (guards against abandoned in-flight from-text requests)
- `_syncJdRequiredFields()` — wired to `#form-jd-text` via `oninput`, also called from `openNewApplicationModal()` and `closeApplicationModal()`. When JD textarea is non-empty AND `currentEditingId` is null, strips the `required` attribute from `#form-company` and `#form-position` so the browser doesn't block the LLM-populate submit; otherwise restores `required`

### Connection Status (Header)
Three side-by-side indicators in `.header-actions`:
- `#jam-status` / `#jam-dot` / `#jam-status-text` — jam server status
- `#kb-status` / `#kb-dot` / `#kb-status-text` — kb knowledge base status
- `#proxy-status` / `#proxy-dot` / `#proxy-status-text` — CLIProxy status

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

### AI Models — Web Search Enrichment toggle
- `#search-enrichment-toggle` — checkbox inside the AI Models section, below `#ai-credentials` and above the per-step model overrides `<details>`
- Label: "Enrich ingestion with web search (Claude only)"; helper text explains it only activates when provider is Anthropic or CLIProxy
- Loaded from `_stored.search_enrichment_enabled` (JSON bool, defaults to `true` when key missing) in `loadAiSettings()`
- Saved via `saveAiSettings()` which includes `search_enrichment_enabled` in the POST `/settings` body and updates `_stored.search_enrichment_enabled` on success

### Connection Settings Section (`#section-connection`)
Four rows:
- "jam Server": `#jam-settings-dot`, `#jam-settings-display`
- "Knowledge Base": `#kb-settings-dot`, `#kb-settings-display`
- "CLIProxy": `#proxy-settings-dot`, `#proxy-settings-display`
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
- Built dynamically by `_initGenProgress()` from `_GEN_STEP_ORDER` (6 steps: Retrieve KB → Generate → Compile → Analyze fit → Check quality → Finalize; `analyze_compress` removed — internal to compact loop)
- Each step has a fixed 16×16px `.step-icon` container to prevent layout shift; states: pending (gray dot), active (indigo spinner reusing `@keyframes spin`), completed (green ✓), error (red ✗)
- Steps separated by `›` characters (`.gen-progress-sep`)
- `_updateGenProgress` handles compact-loop re-activation: when a previously-completed step becomes active again, resets it and all following steps to pending
- Unknown nodes (e.g. `analyze_compress` from backend) are silently skipped by `_updateGenProgress`
- `_generateDoc` and `_reviseDoc` both use shared `_handleGenSSE(docType, resp)` for SSE processing
- `_critiqueDoc` still uses `_setGenStatus` text-only approach (no tracker)

### Per-Step Model Overrides (inside AI Models section)
Collapsible `<details>` section below global provider/model dropdowns.
- Container: `#step-model-overrides` inside `<details class="step-models-details">`
- JS constant: `_STEP_MODEL_META` — array of `{key, label}` for 4 generation steps
- Each row: flex layout with step label + `<select class="field-input">` dropdown
- Options: "Use global default" (value="") + `<optgroup>` per provider with models from `_catalog`
- Values use catalog model ID format: `"provider:model_id"` (e.g. `"openai:gpt-4o"`)
- Auto-saves on change, updates `_stored`, shows success toast via `#ai-settings-msg`

### System Prompts Settings Section (`#section-prompts`)
8 textareas across 5 prompt groups, with doc-type tabbed UI for 3 of them:

**Tabbed groups** (generate_first, generate_revise, analyze_quality):
- Each has a `.prompt-tab-bar` with 2 tabs: CV | Cover Letter (no shared tab)
- Each tab has its own `.prompt-tab-pane` with textarea + "Reset to default" button
- CV tab/pane active by default; Cover Letter pane hidden
- Tab switching via `switchPromptTab(btn, baseKey, docType)`

**Single-textarea groups** (analyze_fit, analyze_compress):
- Same layout as before — one textarea + reset button, no tabs

Key IDs: `#prompt-generate-first--cv`, `#prompt-generate-first--cover-letter`, etc. (colons in keys mapped to `--` in element IDs via `_promptElId()`)

- `_promptKeys` array: 8 keys (2 shared + 6 doc-type-specific with colon format)
- Defaults loaded via `GET /prompts/defaults` (returns all 8 keys) and cached in `_promptDefaults`
- Save button calls `savePromptSettings()` — only saves values differing from defaults
- `resetPrompt(key)` works for both shared and typed keys
- Status: `#prompt-settings-msg`

### Interviews Step (`#step-interviews`)

Section header row contains two buttons:
- `+ From Email` (`.btn.btn-secondary.btn-sm`, calls `openEmailIngestModal()`)
- `+ Add Round` (`.btn.btn-primary.btn-sm`, calls `_ivAdd()`)

Interview card body (`_ivMakeCard`) includes a new **Links** section between the
Location/Confidence row and the Preparation heading:
- `.iv-links-preview` — div of clickable `<a target="_blank" rel="noopener">` anchors (rebuilt on input)
- `.iv-links` — textarea, one URL per line; `oninput` calls both `_ivScheduleSave(this)` and `_ivUpdateLinksPreview(this)`
- `_ivSave` includes `links: ...` in the PUT body

### Interview Preparation Guide Section (inside expanded interview card)

Appended to `.eq-card-body` at the end of `_ivMakeCard` via `_pgMakeSection(item.id)`. Structure:
- **Header row** (`.prep-guide-header`) — title "Preparation guide", "Generate"/"Regenerate" button (`data-pg-btn-generate`), "Edit" toggle (`data-pg-btn-edit`), `.prep-guide-last-gen` timestamp span.
- **Inline error banner** (`.prep-guide-error`, hidden by default).
- **Progress tracker** (`.prep-guide-progress`) — reuses existing `.gen-progress-step` / `.gen-progress-sep` / `.step-icon` classes. Three steps: Load context → Research & reason → Save.
- **Body** (`.prep-guide-body`) — either `.prep-guide-empty` placeholder, `.prep-guide-markdown` rendered view, or `.prep-guide-textarea` edit mode.
- **Three `<details>` collapsibles** under `.prep-guide-collapsibles`: View prompts, Web searches used, Model reasoning.

**Provider gate**: generate button is disabled with a tooltip when `settings.llm_provider not in ("anthropic","cliproxy")`. `_pgCheckProvider()` fetches `GET /settings` once per page load, caches result in module-level `_PREP_GUIDE_PROVIDER_OK`, and updates all generate buttons via `_pgApplyProviderState`.

**SSE client** (`_pgGenerate`) POSTs `{}` to `/interviews/{id}/prep-guide/generate`, streams `data: <json>\n\n` frames, dispatches progress events to the tracker, and on the final `{node:"done"}` event refreshes state, re-renders the markdown view, and populates the collapsibles.

**Flashcard rendering** — inline markdown renderer (`_pgRenderMarkdown`) extracts ```flashcard fenced blocks with a regex, splits `Q:`/`A:` lines, and emits `.flashcard` flip-card components (CSS 3D transform, click to toggle `.flipped`). The remaining markdown is passed through `_pgRenderMd` (a ~50-line inline renderer supporting headings, bold/italic, inline code, fenced code, links, and lists).

**Edit mode** (`_pgToggleEdit`) swaps the rendered view for a textarea; on input, `_pgScheduleSave` debounces 800ms and calls `_pgSaveNow()` which PUTs `{markdown}` and flashes a `.prep-guide-saved-msg` indicator. The existing `prep_notes` textarea in the Preparation section is untouched; the prep guide is a separate, richer field.

**State cache**: per-interview state dict (`_pgState`) with `loaded`, `markdown`, `lastGeneratedAt`, `systemPrompt`, `userPrompt`, `searchLog` (parsed list), `thinking`, `isGenerating`, `editMode`, `debounceTimer`. Fetched once on first card expand via `_pgLoadOnce(card, ivId)`. Reset alongside other application-scoped state in `openDetailPage` (`_pgState = {}`, `_PREP_GUIDE_PROVIDER_OK = null`).

### Outlook Calendar Settings Section (`#section-ms-graph`)
Sibling to the Gmail settings section in the sidebar (new `<li>` nav entry after Gmail). Structure mirrors Gmail:
- Status dot (`#ms-graph-status-dot`, `.connection-dot.disconnected` by default) + status text (`#ms-graph-status-text`). When connected, the `user_email` is shown in muted text next to the label.
- Status message region (`#ms-graph-settings-msg`) for inline feedback.
- Three action buttons:
  - `#ms-graph-connect-btn` "Connect Outlook" — visible only when disconnected; calls `_msGraphConnect()` which hits `GET /api/v1/ms_graph/auth-url` and `window.location.href = data.url`.
  - `#ms-graph-disconnect-btn` "Disconnect" — visible only when connected; `confirm()` then `POST /api/v1/ms_graph/disconnect` → reload status.
  - `#ms-graph-sync-btn` "Sync all" — visible only when connected; `POST /api/v1/ms_graph/sync`; displays `"Synced N interviews (M errors)."` in the status region. Button disabled during the in-flight request.
- OAuth callback return handling: on `DOMContentLoaded`, if `?ms_graph_connected=1` is present in the URL, `history.replaceState` cleans it up, the settings view is activated, `switchSettingsSection('ms-graph')` is called, status is reloaded, and a 4-second success toast is shown.

### Interview round card — Outlook sync badge
Rendered inside `_ivMakeCard()` in the card action row (after `statusBadge`, before the delete button): when `item.graph_event_id` is a non-empty string, a `<span class="iv-sync-badge iv-sync-ok" title="Synced to Outlook">✓ Outlook</span>` pill is appended. Renders nothing when `graph_event_id` is null/empty. Binary state only — pending/error states are not exposed (backend BackgroundTasks are fire-and-forget; errors are logged server-side only).

CSS:
- `.iv-sync-badge` — inline-flex pill, `0.72rem` font, small padding, rounded.
- `.iv-sync-ok` — green from design-system tokens: `#d1fae5` background, `#065f46` text.

### Email Ingest Modal (`#email-ingest-modal`)

Lazy-opened modal (sibling to `#app-modal`) triggered from the Interviews tab.
Structure:
- Header: "Paste Email — Auto-Fill" + close X
- Body: short instruction + `#email-ingest-text` (monospace textarea, 200px min-height, resize:vertical) + `#email-ingest-status` (`.status-msg`, hidden by default)
- Footer: Cancel + `#email-ingest-submit` ("Extract & Save")

Submit flow (`submitEmailIngest`): POSTs to `/applications/{id}/email/ingest`.
Branches on response `kind`:
- `interview_invite` → close modal, `_ivLoad()`, auto-expand newest card
- `rejection` → close modal, `switchDetailStep("details")`, `_rjLoad()`, flash green outline
- HTTP 4xx → display `detail` (string or `{message, extraction}`) in `#email-ingest-status`; modal stays open

### Rejection Panel (`#rejection-panel`, inside `#step-app-details`)

Hidden by default (`display:none`); shown by `_rjRender()` when `_rjRecord` is
set. Placement: appended after `#detail-full-text-section`.

- Section header row: "Outcome — Rejection" (red `#dc2626`) + trash Delete button → `_rjDelete()`
- Fields (all debounced-save via `_rjScheduleSave(this)`):
  - `.rj-summary` (textarea)
  - `.rj-reasons` (textarea)
  - `.rj-links-preview` (anchor div) + `.rj-links` (textarea, one URL per line)
  - `.rj-received_at` (date input)
  - `.rj-followup_status` (select: `none` / `contacted` / `responded` / `closed`) — placeholder for future reach-back feature
  - `.rj-followup_notes` (textarea) — placeholder for future feature
  - `<details>` "Original Email" containing readonly `.rj-raw_email` textarea

Module state: `var _rjLoaded = false; var _rjSaveTimer = null; var _rjRecord = null;`
Reset in `openDetailPage()`. `switchDetailStep("app-details")` calls `_rjLoad()` once (guarded by `_rjLoaded`).

### CSS Classes (from shared design system)
- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-sm`, `.btn-green`
- Badges: `.badge`, `.badge-applied`, `.badge-screening`, `.badge-interviewing`, `.badge-offered`, `.badge-rejected`, `.badge-accepted`, `.badge-withdrawn`
- Forms: `.field-label`, `.field-input`
- Layout: `.card`, `.modal`, `.modal-overlay`, `.modal-header`, `.modal-body`, `.modal-footer`
- Status: `.status-msg`, `.status-msg.success`, `.status-msg.error`
- Custom: `.stats-row`, `.stat-card`, `.connection-status`, `.connection-dot`, `.actions-bar`, `.applications-grid`, `.app-tile`, `.empty-state`
- Settings: `.settings-container`, `.settings-sidebar`, `.settings-sidebar-menu`, `.settings-content`, `.settings-section`
- Document editor: `.tab-bar`, `.tab-btn-doc`, `.doc-tab-panel`, `.trisplit-container`, `.trisplit-pane`, `.trisplit-pane-header`, `.trisplit-pane-body`, `.doc-list-bar`, `.doc-preview-frame`, `.doc-version-bar`, `.doc-compile-status`, `.agent-feedback-panel` (max-height: 40vh, overflow-y: auto, flex-shrink: 1), `.feedback-text` (max-height: 200px, overflow-y: auto, read-only `<pre>`), `.feedback-textarea` (max-height: 200px, editable `<textarea>`, resize: vertical, monospace)
- Prompt tabs: `.prompt-tab-bar` (flex row with border-bottom), `.prompt-tab` (inactive tab), `.prompt-tab.active` (indigo border-bottom + text), `.prompt-tab-pane` (tab content container)
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
- `handleApplicationFormSubmit(event)` — reads `#form-jd-text`; if non-empty **and** creating (not editing), POSTs `{text}` to `/applications/from-text` with submit button disabled + "Extracting…" label, then closes modal + `loadApplications()` on success or shows error in `#form-message`; otherwise falls through to the manual create/update path unchanged
- `switchToSettings()` / `switchToDashboard()` — toggle main views
- `switchSettingsSection(section)` — activate settings sidebar section
- `checkKbConnection()` — GET `/health`, updates jam, kb, and proxy header/settings indicators
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
- `switchPromptTab(btn, baseKey, docType)` — switches between Shared/CV/Cover Letter prompt tabs within a tabbed group
- `loadPromptSettings()` — populates 8 prompt textareas from `_stored` or defaults
- `savePromptSettings()` — POST `/settings` with prompt values (only saves values that differ from defaults)
- `resetPrompt(key)` — resets a single prompt textarea to its default value
- `loadPersonalInfo()` — reads from `_stored` to populate personal info fields (called after `loadAiSettings` in `switchToSettings`)
- `savePersonalInfo()` — POST `/settings` with 5 personal info fields, updates `_stored` via `Object.assign`
- `loadGmailSettings()` — GET `/gmail/status` + GET `/settings`, populates Gmail fields
- `saveGmailCredentials()` — POST `/settings` with Gmail OAuth credentials
- `connectGmail()` — GET `/gmail/auth-url`, opens auth URL in new window
- `disconnectGmail()` — POST `/gmail/disconnect`
- `_msGraphLoadStatus()` — GET `/ms_graph/status`; toggles `.connection-dot.disconnected` / `.connected`, writes status text with `user_email`, toggles visibility of Connect/Disconnect/Sync-all buttons
- `_msGraphConnect()` — GET `/ms_graph/auth-url` → same-tab `window.location.href = data.url` (confidential-client flow; callback lands at `/ms_graph/callback` then redirects to `/?ms_graph_connected=1`)
- `_msGraphDisconnect()` — `confirm()` dialog → POST `/ms_graph/disconnect` → reload status; the server clears every `interview_rounds.graph_event_id` and reports `rounds_cleared`
- `_msGraphSyncAll()` — POST `/ms_graph/sync`; reports `{synced, errors}` in `#ms-graph-settings-msg`; button disabled during flight
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
- `_handleGenSSE(docType, resp)` — shared SSE stream reader for both `_generateDoc` and `_reviseDoc`; updates progress, populates textareas (`.value =`), refreshes PDF, shows feedback panel
- `_reviseDoc(docType)` — reads edited fit/quality feedback from textareas, saves editor state, POSTs to generate with `{is_first_generation: false, fit_feedback, quality_feedback}`, delegates to `_handleGenSSE`
- `_initGenProgress(docType)` — builds step tracker from `_GEN_STEP_ORDER`, shows `#<type>-gen-progress` container
- `_updateGenProgress(docType, activeNode)` — handles loop re-activation (resets completed steps to pending if revisited), promotes previous active to completed, marks new node active; skips unknown nodes
- `_completeGenProgress(docType)` — marks all steps completed (green) on generation done
- `_errorGenProgress(docType)` — marks current active step as error (red)
- `_hideGenProgress(docType)` — hides and clears the tracker
- `_setDocStatus(docType, msg, cls)` — updates status span; clears after 3s on success
- `_togglePane(containerId, paneIndex)` — collapses/expands a trisplit pane
- `openEmailIngestModal()` — clears `#email-ingest-text` + `#email-ingest-status`, resets submit button, shows `#email-ingest-modal`; requires `currentDetailId`
- `closeEmailIngestModal()` — hides `#email-ingest-modal`
- `submitEmailIngest()` — POST `/applications/{currentDetailId}/email/ingest` with `{ email_text }`; button label toggles to "Extracting…" during flight. On `kind === "interview_invite"`: close modal, `_ivLoad()`, auto-expand newest card. On `kind === "rejection"`: close modal, `switchDetailStep("details")`, `await _rjLoad()`, flash success. On 4xx: parse JSON `detail` (string or `{message, extraction}`), show in `#email-ingest-status`, keep modal open.
- `_ivUpdateLinksPreview(el)` — rebuilds `.iv-links-preview` anchors from textarea value (newline-split, escaped). Called from interview card `.iv-links` `oninput` handler.
- `_rjLoad()` — GET `/applications/{id}/rejections`; stores first item in `_rjRecord`; calls `_rjRender()`
- `_rjRender()` — hides `#rejection-panel` if `_rjRecord` null; otherwise populates all `.rj-*` fields + rebuilds links-preview and shows panel
- `_rjUpdateLinksPreview(el)` — rebuilds `.rj-links-preview` anchors
- `_rjScheduleSave(el)` — 2 s debounce → `_rjSave`
- `_rjSave()` — PUT `/rejections/{_rjRecord.id}` with current field values; updates `_rjRecord` from response
- `_rjDelete()` — confirm → DELETE `/rejections/{id}` → clears `_rjRecord` → `_rjRender()`
- `_pgGetState(ivId)` / `_pgMakeSection(ivId)` / `_pgFindSection(ivId)` — build and locate the per-interview prep-guide DOM; lazy state object with `loaded`, `markdown`, `lastGeneratedAt`, `systemPrompt`, `userPrompt`, `searchLog`, `thinking`, `isGenerating`, `editMode`, `debounceTimer`
- `_pgLoadOnce(card, ivId)` — GET `/interviews/{id}/prep-guide` once per expand (guarded by `state.loaded`); applies response into state
- `_pgCheckProvider()` — GET `/settings` once per page; caches `_PREP_GUIDE_PROVIDER_OK` based on `llm_provider in ("anthropic","cliproxy")`; calls `_pgApplyProviderState` on every generate button
- `_pgApplyProviderState(btn)` — disables button + sets tooltip when provider not supported
- `_pgApplyResponse(ivId, data)` — stores a `PrepGuideResponse` dict into state, triggers `_pgRender`
- `_pgRender(ivId)` — full re-render of section: button labels (Generate vs Regenerate), last-gen timestamp, body shows empty / markdown / textarea per mode
- `_pgRenderCollapsibles(ivId, section, state)` — rebuilds the three `<details>` blocks (View prompts, Web searches used, Model reasoning)
- `_pgToggleEdit(ivId)` — swap between view and edit; PUTs on leaving edit if content changed
- `_pgScheduleSave(ivId)` / `_pgSaveNow(ivId)` — 800 ms debounce → PUT `/interviews/{id}/prep-guide` with `{markdown}`; flashes `.prep-guide-saved-msg.visible`
- `_pgSetError(ivId, msg)` — shows/hides `.prep-guide-error` banner
- `_pgInitProgress(ivId)` / `_pgUpdateProgress(ivId, node)` / `_pgCompleteProgress(ivId)` / `_pgErrorProgress(ivId)` / `_pgHideProgress(ivId)` — progress tracker management (mirrors `_initGenProgress` / `_updateGenProgress` ... for three steps: Load context → Research & reason → Save)
- `_pgGenerate(ivId)` — POST `{}` to `/interviews/{id}/prep-guide/generate`, reads SSE stream, dispatches progress events; on `{node:"done"}` event updates state (markdown, prompts, search log, thinking) and re-renders
- `_pgRenderMarkdown(md)` — extracts ```flashcard fenced blocks (regex), feeds rest through `_pgRenderMd`, stitches the flashcard flip-card components back in at the correct positions
- `_pgRenderFlashcard(text)` — parses `Q:`/`A:` lines and emits `.flashcard` DOM with click-to-flip behaviour
- `_pgRenderMd(text)` — ~50-line inline markdown renderer: headings (`#..######`), `**bold**`, `*italic*`, inline ``code``, fenced ```code```, `[text](url)`, `-` and `1.` lists, paragraphs; escapes HTML first
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
