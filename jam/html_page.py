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
  }

  /* -- Layout -- */
  .app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  /* -- Header -- */
  header {
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  header .title-section {
    flex: 1;
  }

  header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #16213e;
    letter-spacing: -0.02em;
    margin: 0;
  }

  header p {
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 4px;
    margin-bottom: 0;
  }

  header .header-actions {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  /* -- Connection indicator -- */
  .connection-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: #6b7280;
  }

  .connection-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #d1d5db;
  }

  .connection-dot.connected {
    background: #10b981;
  }

  .connection-dot.disconnected {
    background: #dc2626;
  }

  .settings-btn {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    color: #6b7280;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s;
  }

  .settings-btn:hover {
    color: #4f46e5;
  }

  /* -- Main content -- */
  main {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 24px 16px 48px;
  }

  main.dashboard-view {
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  main.settings-view {
    display: flex;
    width: 100%;
  }

  /* -- Settings layout -- */
  .settings-container {
    display: flex;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    gap: 24px;
  }

  .settings-sidebar {
    flex-shrink: 0;
    width: 200px;
  }

  .settings-sidebar-menu {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .settings-sidebar-menu li {
    margin: 0;
  }

  .settings-sidebar-menu button {
    width: 100%;
    padding: 12px 16px;
    background: none;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    font-size: 0.875rem;
    font-weight: 600;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.15s;
  }

  .settings-sidebar-menu button:hover {
    background: #f3f4f6;
    color: #4f46e5;
  }

  .settings-sidebar-menu button.active {
    background: #f0f2f5;
    color: #4f46e5;
    border-left-color: #4f46e5;
  }

  .settings-content {
    flex: 1;
    background: #ffffff;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06);
  }

  .settings-section {
    display: none;
  }

  .settings-section.active {
    display: block;
  }

  .settings-section h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #16213e;
    margin-bottom: 16px;
    margin-top: 0;
  }

  .setting-group {
    margin-bottom: 24px;
  }

  .setting-group-label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }

  .setting-value {
    font-size: 0.875rem;
    color: #1a1a2e;
    padding: 8px 12px;
    background: #f9fafb;
    border-radius: 8px;
    word-break: break-all;
  }

  /* -- Dashboard stats -- */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }

  .stat-card .stat-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #1a1a2e;
  }

  .stat-card .stat-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
  }

  /* -- Actions bar -- */
  .actions-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }

  /* -- Buttons -- */
  .btn {
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-sm {
    font-size: 0.8rem;
    padding: 5px 14px;
  }

  .btn-primary {
    background: #4f46e5;
    color: #fff;
  }

  .btn-primary:hover {
    background: #4338ca;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
  }

  .btn-secondary:hover {
    background: #e5e7eb;
  }

  .btn-danger {
    background: #dc2626;
    color: #fff;
  }

  .btn-danger:hover {
    background: #b91c1c;
  }

  .btn-generate {
    background: #7c3aed;
    color: #fff;
    border: none;
  }

  .btn-generate:hover {
    background: #6d28d9;
  }

  .btn-critique {
    background: transparent;
    color: #7c3aed;
    border: 1.5px solid #7c3aed;
  }

  .btn-critique:hover {
    background: #f5f3ff;
  }

  .btn:disabled {
    opacity: 0.55;
    cursor: default;
  }

  /* -- Badges -- */
  .badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .badge-applied {
    background: #dbeafe;
    color: #1e40af;
  }

  .badge-screening {
    background: #fef3c7;
    color: #92400e;
  }

  .badge-interviewing {
    background: #fce7f3;
    color: #831843;
  }

  .badge-offered {
    background: #dcfce7;
    color: #166534;
  }

  .badge-rejected {
    background: #fee2e2;
    color: #991b1b;
  }

  .badge-accepted {
    background: #d1fae5;
    color: #065f46;
  }

  .badge-withdrawn {
    background: #f3f4f6;
    color: #4b5563;
  }

  .badge-not_applied_yet {
    background: #d1d5db;
    color: #ffffff;
  }

  .badge-scheduled { background: #dbeafe; color: #2563eb; }
  .badge-completed { background: #dcfce7; color: #16a34a; }
  .badge-cancelled { background: #f1f5f9; color: #64748b; }
  .badge-pending { background: #fef3c7; color: #d97706; }
  .badge-negotiating { background: #dbeafe; color: #2563eb; }
  .badge-declined { background: #fee2e2; color: #dc2626; }
  .badge-expired { background: #f1f5f9; color: #64748b; }

  /* -- Applications grid -- */
  .applications-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .app-tile {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .app-tile:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-color: #4f46e5;
  }

  .app-tile-company {
    font-size: 1.1rem;
    font-weight: 700;
    color: #16213e;
    margin-bottom: 8px;
  }

  .app-tile-position {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 12px;
  }

  .app-tile-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .app-tile-date {
    font-size: 0.75rem;
    color: #9ca3af;
  }

  .app-tile-status {
    display: block;
  }

  /* -- Empty state -- */
  .empty-state {
    text-align: center;
    color: #9ca3af;
    padding: 60px 20px;
  }

  .empty-state .icon {
    font-size: 2.5rem;
    margin-bottom: 12px;
  }

  .empty-state h3 {
    font-size: 1rem;
    font-weight: 600;
    color: #6b7280;
    margin-bottom: 6px;
  }

  .empty-state p {
    font-size: 0.875rem;
  }

  /* -- Modal -- */
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1000;
    align-items: center;
    justify-content: center;
  }

  .modal-overlay.open {
    display: flex;
  }

  /* ── Crop modal ─────────────────────────────────────────────────────────── */
  .crop-modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 2000;
    align-items: center;
    justify-content: center;
  }
  .crop-modal-overlay.open {
    display: flex;
  }
  .crop-modal {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px;
    max-width: 580px;
    width: 95%;
    box-shadow: 0 20px 25px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .crop-modal-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1a1a2e;
    margin: 0;
  }
  .crop-container {
    position: relative;
    overflow: hidden;
    background: #1a1a2e;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
  }
  .crop-container img {
    display: block;
    max-width: 100%;
    max-height: 460px;
    pointer-events: none;
    user-select: none;
  }
  .crop-overlay-canvas {
    position: absolute;
    top: 0; left: 0;
    pointer-events: none;
  }
  .crop-modal-hint {
    font-size: 0.8rem;
    color: #6b7280;
    margin: 0;
  }
  .crop-modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  /* ── Rectangle crop modal ───────────────────────────────────────────────── */
  .rect-crop-modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 2000;
    align-items: center;
    justify-content: center;
  }
  .rect-crop-modal-overlay.open {
    display: flex;
  }
  .rect-crop-modal {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px;
    max-width: 680px;
    width: 95%;
    box-shadow: 0 20px 25px rgba(0,0,0,0.25);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .rect-crop-modal-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1a1a2e;
    margin: 0;
  }
  .rect-crop-container {
    position: relative;
    overflow: hidden;
    background: #1a1a2e;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
  }
  .rect-crop-container img {
    display: block;
    max-width: 100%;
    max-height: 400px;
    pointer-events: none;
    user-select: none;
  }
  .rect-crop-overlay-canvas {
    position: absolute;
    top: 0; left: 0;
    pointer-events: none;
  }
  .rect-crop-modal-hint {
    font-size: 0.8rem;
    color: #6b7280;
    margin: 0;
  }
  .rect-crop-modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .modal {
    background: #ffffff;
    border-radius: 16px;
    padding: 24px;
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px rgba(0,0,0,0.15);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 12px;
  }

  .modal-header h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #16213e;
    margin: 0;
  }

  .modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6b7280;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-close:hover {
    color: #1a1a2e;
  }

  .modal-body {
    margin-bottom: 20px;
  }

  .modal-footer {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    border-top: 1px solid #e5e7eb;
    padding-top: 12px;
  }

  /* -- Form fields -- */
  .form-group {
    margin-bottom: 16px;
  }

  .field-label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }

  textarea.field-input,
  input.field-input,
  select.field-input {
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 0.875rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
    color: #1a1a2e;
    background: #ffffff;
  }

  textarea.field-input:focus,
  input.field-input:focus,
  select.field-input:focus {
    border-color: #4f46e5;
  }

  textarea.field-input {
    resize: vertical;
    min-height: 80px;
  }

  /* -- Status messages -- */
  .status-msg {
    font-size: 0.85rem;
    color: #6b7280;
  }

  .status-msg.success {
    color: #059669;
  }

  .status-msg.error {
    color: #dc2626;
  }

  .setting-group input[type="password"] {
    padding-right: 50px;
  }

  /* -- Responsive -- */
  @media (max-width: 768px) {
    header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    header .header-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .settings-container {
      flex-direction: column;
    }

    .settings-sidebar {
      width: 100%;
    }

    .settings-sidebar-menu {
      display: flex;
      gap: 8px;
      overflow-x: auto;
    }

    .settings-sidebar-menu li {
      flex-shrink: 0;
    }

    .settings-sidebar-menu button {
      border-left: none;
      border-bottom: 3px solid transparent;
    }

    .settings-sidebar-menu button.active {
      border-left: none;
      border-bottom-color: #4f46e5;
    }

    .applications-grid {
      grid-template-columns: 1fr;
    }

    .stats-row {
      grid-template-columns: repeat(2, 1fr);
    }

    .detail-container {
      flex-direction: column;
    }

    .detail-sidebar {
      width: 100%;
    }

    .detail-sidebar-menu {
      flex-direction: row;
      overflow-x: auto;
    }

    .detail-step-btn {
      border-left: none;
      border-bottom: 3px solid transparent;
    }

    .detail-step-btn.active {
      border-left: none;
      border-left-color: transparent;
      border-bottom: 3px solid #4f46e5;
    }

    .detail-form-grid {
      grid-template-columns: 1fr;
    }

    .detail-form-grid .form-group.full-width {
      grid-column: span 1;
    }
  }

  /* -- Detail view -- */
  .detail-view {
    display: flex;
    padding: 24px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .detail-container {
    display: flex;
    flex-direction: row;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    gap: 24px;
    height: 100%;
    align-items: stretch;
  }

  .detail-sidebar {
    flex-shrink: 0;
    width: 240px;
  }

  .detail-back {
    margin-bottom: 16px;
  }

  .detail-app-header {
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .detail-app-header h3 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #16213e;
    margin: 0;
  }

  .detail-app-header p {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 4px;
    margin-bottom: 0;
  }

  .detail-sidebar-menu {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .detail-step-btn {
    width: 100%;
    padding: 10px 16px;
    background: none;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    cursor: pointer;
    font-size: 0.9rem;
    color: #4b5563;
    border-radius: 0 6px 6px 0;
    transition: all 0.15s;
  }

  .detail-step-btn:hover {
    background: #f3f4f6;
  }

  .detail-step-btn.active {
    border-left-color: #4f46e5;
    background: #eef2ff;
    color: #4f46e5;
    font-weight: 600;
  }

  .detail-content {
    flex: 1;
    min-height: 0;
    background: #fff;
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .detail-content.no-outer-scroll {
    overflow-y: hidden;
  }

  .detail-step {
    display: none;
  }

  .detail-step.active {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .detail-step h2 {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: #16213e;
    margin-top: 0;
  }

  .placeholder-text {
    color: #9ca3af;
    font-size: 0.95rem;
    padding: 60px 0;
    text-align: center;
  }

  .detail-form-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .detail-form-grid .form-group.full-width {
    grid-column: span 2;
  }

  .detail-form-actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #e5e7eb;
  }

  .detail-form-actions .btn-danger {
    margin-right: auto;
  }

  /* ── Tabs (from shared design system) ── */
  .tab-bar {
    display: flex;
    border-bottom: 1px solid #e5e7eb;
    background: #fafafa;
  }
  .tab-btn-doc {
    flex: 1;
    padding: 10px 16px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6b7280;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    text-align: center;
  }
  .tab-btn-doc:hover { color: #4f46e5; }
  .tab-btn-doc.active { color: #4f46e5; border-bottom-color: #4f46e5; background: #fff; }
  .doc-tab-panel { display: none; }
  .doc-tab-panel.active { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }

  /* ── Tri-split reusable pattern ── */
  .trisplit-container {
    display: flex;
    flex: 1;
    height: 0;
    min-height: 250px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
    background: #fff;
  }
  .trisplit-pane {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex: 1 1 0;
    min-width: 0;
  }
  .trisplit-pane.collapsed {
    flex: 0 0 30px !important;
    min-width: 30px;
    overflow: hidden;
  }
  .trisplit-pane.collapsed .trisplit-pane-body { display: none; }
  .trisplit-pane.collapsed .trisplit-pane-header {
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
    padding: 8px 0;
    height: 100%;
    border-bottom: none;
    border-right: 1px solid #e5e7eb;
    gap: 8px;
  }
  .trisplit-pane.collapsed .trisplit-pane-header span {
    display: block;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-height: 120px;
  }
  .trisplit-pane.collapsed .trisplit-pane-header button {
    transform: rotate(-90deg);
  }
  .trisplit-pane-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
    min-height: 30px;
  }
  .trisplit-pane-header button {
    background: none;
    border: none;
    cursor: pointer;
    color: #9ca3af;
    font-size: 0.85rem;
    padding: 2px 4px;
    border-radius: 4px;
    line-height: 1;
  }
  .trisplit-pane-header button:hover { color: #4f46e5; background: #eef2ff; }
  .trisplit-pane-body {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .trisplit-pane textarea {
    flex: 1;
    width: 100%;
    border: none;
    padding: 12px;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.82rem;
    resize: none;
    outline: none;
    line-height: 1.6;
    background: #fff;
    color: #1a1a2e;
    tab-size: 2;
  }
  .trisplit-pane textarea.prompt-editor {
    font-family: inherit;
    font-size: 0.85rem;
  }
  .trisplit-pane-body .CodeMirror {
    flex: 1;
    height: 100%;
    min-height: 0;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.82rem;
    line-height: 1.6;
    background: #fff;
    color: #1a1a2e;
    border: none;
  }

  /* ── Instructions panel ── */
  .instructions-panel {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: #f9fafb;
  }
  .instruction-field {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .instruction-field.global {
    border-color: #a5b4fc;
    background: #eef2ff;
  }
  .instruction-field-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .instruction-field-title {
    font-size: 0.78rem;
    font-weight: 600;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .instruction-field.global .instruction-field-title {
    color: #4f46e5;
  }
  .instruction-toggle-wrap {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
  }
  .instruction-toggle-label {
    font-size: 0.7rem;
    color: #6b7280;
    user-select: none;
  }
  .instruction-toggle {
    position: relative;
    width: 30px;
    height: 16px;
    flex-shrink: 0;
  }
  .instruction-toggle input {
    opacity: 0;
    width: 0;
    height: 0;
    position: absolute;
  }
  .instruction-toggle-slider {
    position: absolute;
    inset: 0;
    background: #d1d5db;
    border-radius: 16px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .instruction-toggle-slider::before {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    left: 2px;
    top: 2px;
    background: #fff;
    border-radius: 50%;
    transition: transform 0.2s;
  }
  .instruction-toggle input:checked + .instruction-toggle-slider { background: #4f46e5; }
  .instruction-toggle input:checked + .instruction-toggle-slider::before { transform: translateX(14px); }
  .instruction-textarea {
    width: 100%;
    box-sizing: border-box;
    resize: vertical;
    min-height: 52px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 6px 8px;
    font-family: inherit;
    font-size: 0.82rem;
    line-height: 1.45;
    color: #1a1a2e;
    background: #fff;
    outline: none;
    transition: border-color 0.15s;
  }
  .instruction-textarea:focus { border-color: #a5b4fc; }
  .instruction-field.global .instruction-textarea { min-height: 64px; }

  /* ── Extra questions ── */
  .eq-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .eq-header h2 { margin: 0; }
  #eq-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .eq-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
  }
  .eq-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    cursor: pointer;
    user-select: none;
    background: #f9fafb;
    border-bottom: 1px solid transparent;
  }
  .eq-card.expanded .eq-card-header {
    border-bottom-color: #e5e7eb;
  }
  .eq-chevron {
    font-size: 0.7rem;
    color: #6b7280;
    transition: transform 0.15s;
    flex-shrink: 0;
  }
  .eq-card.expanded .eq-chevron {
    transform: rotate(90deg);
  }
  .eq-question-preview {
    flex: 1;
    font-size: 0.88rem;
    font-weight: 500;
    color: #1a1a2e;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .eq-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .eq-word-cap-wrap {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    color: #6b7280;
  }
  .eq-word-cap-wrap input {
    width: 56px;
    padding: 2px 6px;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    font-size: 0.78rem;
    text-align: center;
  }
  .eq-btn-delete {
    background: none;
    border: none;
    color: #9ca3af;
    cursor: pointer;
    font-size: 0.9rem;
    padding: 2px 4px;
    border-radius: 4px;
    line-height: 1;
  }
  .eq-btn-delete:hover { color: #dc2626; background: #fef2f2; }
  .eq-card-body {
    padding: 12px;
    display: none;
  }
  .eq-card.expanded .eq-card-body {
    display: block;
  }
  .eq-card-body .form-group { margin-bottom: 10px; }
  .eq-card-body .form-group:last-child { margin-bottom: 0; }
  .eq-card-body textarea {
    width: 100%;
    box-sizing: border-box;
    min-height: 60px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 10px;
    font-family: inherit;
    font-size: 0.85rem;
    line-height: 1.5;
    color: #1a1a2e;
    background: #fff;
    outline: none;
    overflow: hidden;
    resize: none;
    transition: border-color 0.15s;
  }
  .eq-card-body textarea:focus { border-color: #a5b4fc; }

  /* ── Document editor specific ── */
  .doc-list-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 0;
    flex-wrap: wrap;
  }
  .doc-list-bar select {
    flex: 1;
    min-width: 120px;
    max-width: 250px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.82rem;
    font-family: inherit;
    color: #1a1a2e;
    outline: none;
  }
  .doc-list-bar select:focus { border-color: #4f46e5; }
  .doc-preview-frame {
    flex: 1;
    width: 100%;
    overflow-y: auto;
    background: #f3f4f6;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .pdf-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #9ca3af;
    font-family: sans-serif;
    font-size: 0.9rem;
  }
  .pdf-canvas-page {
    display: block;
    margin: 8px auto;
    box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    background: #fff;
    max-width: 100%;
  }
  .doc-version-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    font-size: 0.8rem;
    color: #6b7280;
    flex-wrap: wrap;
  }
  .doc-version-bar button {
    background: #f3f4f6;
    border: none;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #374151;
    cursor: pointer;
  }
  .doc-version-bar button:hover { background: #e5e7eb; }
  .agent-feedback-panel {
    padding: 8px 12px;
    background: #f9fafb;
    border-top: 1px solid #e5e7eb;
    font-size: 0.8rem;
    max-height: 40vh;
    overflow-y: auto;
    flex-shrink: 1;
  }
  .agent-feedback-panel details { margin-bottom: 6px; }
  .agent-feedback-panel summary {
    font-weight: 600;
    cursor: pointer;
    color: #374151;
    user-select: none;
  }
  .feedback-text {
    white-space: pre-wrap;
    color: #4b5563;
    margin: 4px 0 0 0;
    font-family: inherit;
    font-size: 0.78rem;
    max-height: 200px;
    overflow-y: auto;
    padding: 4px 8px;
    border: 1px solid #e5e7eb;
    background: #ffffff;
  }
  .help-tip {
    display: inline-block;
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background: #e5e7eb;
    color: #6b7280;
    font-size: 0.6rem;
    font-weight: 700;
    text-align: center;
    line-height: 15px;
    cursor: help;
    margin-left: 4px;
    vertical-align: middle;
  }
  .doc-compile-status {
    font-size: 0.8rem;
    color: #6b7280;
    margin-left: auto;
  }
  .doc-compile-status.error { color: #dc2626; }
  .doc-compile-status.success { color: #059669; }

  .compile-overlay {
    position: absolute;
    inset: 0;
    background: rgba(255,255,255,0.8);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    z-index: 10;
    font-size: 0.85rem;
    color: #6b7280;
    font-weight: 500;
  }
  .compile-spinner {
    width: 28px;
    height: 28px;
    border: 3px solid #e5e7eb;
    border-top-color: #4f46e5;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Generation progress tracker */
  .gen-progress-tracker {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
    font-size: 0.75rem;
    overflow-x: auto;
  }
  .gen-progress-step {
    display: flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
    color: #9ca3af;
  }
  .gen-progress-step .step-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .gen-progress-step .step-icon::before {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #d1d5db;
    display: block;
  }
  .gen-progress-step.completed {
    color: #059669;
  }
  .gen-progress-step.completed .step-icon::before {
    content: "\\2713";
    width: auto;
    height: auto;
    background: none;
    font-size: 12px;
    font-weight: bold;
    border-radius: 0;
    line-height: 16px;
  }
  .gen-progress-step.active {
    color: #1a1a2e;
    font-weight: 500;
  }
  .gen-progress-step.active .step-icon::before {
    content: "";
    width: 12px;
    height: 12px;
    border: 2px solid #e5e7eb;
    border-top-color: #4f46e5;
    background: none;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .gen-progress-step.error {
    color: #dc2626;
  }
  .gen-progress-step.error .step-icon::before {
    content: "\\2717";
    width: auto;
    height: auto;
    background: none;
    font-size: 12px;
    font-weight: bold;
    border-radius: 0;
    line-height: 16px;
  }
  .gen-progress-sep {
    color: #d1d5db;
    font-size: 10px;
    flex-shrink: 0;
    user-select: none;
  }

  /* Override detail-content layout for cv-cover step */
  #step-cv-cover.active { display: flex; flex-direction: column; flex: 1; min-height: 0; }

  /* Fullscreen overlay for trisplit */
  #step-cv-cover.trisplit-fullscreen {
    position: fixed;
    inset: 0;
    z-index: 1000;
    background: #fff;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
  }
  #step-cv-cover.trisplit-fullscreen .trisplit-container {
    flex: 1;
    height: auto;
  }
  .trisplit-fs-btn {
    margin-left: auto;
    padding: 6px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    cursor: pointer;
    color: #374151;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .trisplit-fs-btn:hover { background: #e5e7eb; }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/stex/stex.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/closebrackets.min.js"></script>
</head>
<body>

<div class="app-container">
  <header>
    <div class="title-section">
      <h1>Job Application Manager</h1>
      <p>Track and manage your job applications</p>
    </div>
    <div class="header-actions">
      <div class="connection-status" id="jam-status">
        <span class="connection-dot" id="jam-dot"></span>
        <span id="jam-status-text">jam</span>
      </div>
      <div class="connection-status" id="kb-status">
        <span class="connection-dot" id="kb-dot"></span>
        <span id="kb-status-text">kb</span>
      </div>
      <button class="settings-btn" onclick="switchToSettings()" id="settings-btn" title="Settings">⚙️</button>
    </div>
  </header>

  <!-- Dashboard View -->
  <main id="dashboard-view" class="dashboard-view">
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
        <div class="stat-value" id="stat-interviewing">0</div>
        <div class="stat-label">Interviewing</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-offers">0</div>
        <div class="stat-label">Offers</div>
      </div>
    </div>

    <div class="actions-bar">
      <div style="display:flex;gap:8px;align-items:center;flex:1;max-width:600px">
        <input type="url" id="import-url" placeholder="Paste job posting URL..."
               style="flex:1;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px">
        <button onclick="importFromUrl()" id="import-btn"
                style="padding:8px 16px;background:#4f46e5;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;white-space:nowrap">
          Import
        </button>
        <span id="import-status" style="font-size:13px;white-space:nowrap"></span>
      </div>
      <button class="btn btn-primary" onclick="openNewApplicationModal()">+ New Application</button>
    </div>

    <div id="applications-container"></div>
  </main>

  <!-- Settings View -->
  <main id="settings-view" class="settings-view" style="display: none;">
    <div class="settings-container">
      <div class="settings-sidebar">
        <ul class="settings-sidebar-menu">
          <li>
            <button class="sidebar-menu-btn active" data-section="personal-info" onclick="switchSettingsSection('personal-info')">
              Personal Info
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="general" onclick="switchSettingsSection('general')">
              General
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="connection" onclick="switchSettingsSection('connection')">
              Connection
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="knowledge-base" onclick="switchSettingsSection('knowledge-base')">
              Knowledge Base
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="ai-models" onclick="switchSettingsSection('ai-models')">
              AI Models
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="templates" onclick="switchSettingsSection('templates')">
              Templates
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="prompts" onclick="switchSettingsSection('prompts')">
              System Prompts
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="gmail" onclick="switchSettingsSection('gmail')">
              Email / Gmail
            </button>
          </li>
        </ul>
      </div>

      <div class="settings-content">
        <!-- Personal Info Settings Section -->
        <div id="section-personal-info" class="settings-section active">
          <h2>Personal Information</h2>
          <p class="setting-description" style="color: var(--text-secondary, #6b7280); margin-bottom: 20px;">
            This information is embedded into your PDF document metadata.
          </p>
          <div class="setting-group">
            <label class="setting-group-label" for="personal-full-name">Full Name</label>
            <input type="text" id="personal-full-name" class="field-input" placeholder="e.g. Jane Doe" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label" for="personal-email">Email</label>
            <input type="email" id="personal-email" class="field-input" placeholder="e.g. jane@example.com" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label" for="personal-phone">Phone</label>
            <input type="tel" id="personal-phone" class="field-input" placeholder="e.g. +1 555 123 4567" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label" for="personal-website">Website / Portfolio</label>
            <input type="url" id="personal-website" class="field-input" placeholder="e.g. https://janedoe.dev" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label" for="personal-address">Address / Location</label>
            <input type="text" id="personal-address" class="field-input" placeholder="e.g. San Francisco, CA" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label">Profile Photo</label>
            <p style="color: var(--text-secondary, #6b7280); font-size: 0.85rem; margin: 0 0 8px 0;">Used on your CV</p>
            <input type="file" id="personal-photo-input" accept="image/*" style="display:none" onchange="handleImageUpload(this, 'personal-photo-preview', 'personal_photo')" />
            <div style="display: flex; align-items: center; gap: 12px;">
              <button type="button" class="btn btn-secondary" onclick="document.getElementById('personal-photo-input').click()">Choose file</button>
              <button type="button" class="btn btn-secondary" id="personal-photo-remove" style="display:none" onclick="removeImage('personal-photo-preview', 'personal_photo')">Remove</button>
            </div>
            <img id="personal-photo-preview" style="display:none; margin-top: 10px; width: 120px; height: 120px; border-radius: 50%; border: 2px solid var(--border-primary, #e5e7eb); object-fit: cover;" alt="Profile photo preview" />
          </div>
          <div class="setting-group">
            <label class="setting-group-label">Signature</label>
            <p style="color: var(--text-secondary, #6b7280); font-size: 0.85rem; margin: 0 0 8px 0;">Used on your cover letter</p>
            <input type="file" id="personal-signature-input" accept="image/*" style="display:none" onchange="handleImageUpload(this, 'personal-signature-preview', 'personal_signature')" />
            <div style="display: flex; align-items: center; gap: 12px;">
              <button type="button" class="btn btn-secondary" onclick="document.getElementById('personal-signature-input').click()">Choose file</button>
              <button type="button" class="btn btn-secondary" id="personal-signature-remove" style="display:none" onclick="removeImage('personal-signature-preview', 'personal_signature')">Remove</button>
            </div>
            <img id="personal-signature-preview" style="display:none; margin-top: 10px; max-width: 250px; max-height: 80px; border-radius: 4px; border: 1px solid var(--border-primary, #e5e7eb);" alt="Signature preview" />
          </div>
          <div style="margin-top: 20px;">
            <button class="btn btn-primary" onclick="savePersonalInfo()">Save</button>
            <span id="personal-info-msg" class="status-msg" style="margin-left: 12px;"></span>
          </div>
        </div>

        <!-- General Settings Section -->
        <div id="section-general" class="settings-section">
          <h2>General</h2>
          <div class="setting-group">
            <label class="setting-group-label">Application Title</label>
            <div class="setting-value">Job Application Manager</div>
          </div>
          <div class="setting-group">
            <label class="setting-group-label">Version</label>
            <div class="setting-value">0.1.0</div>
          </div>
        </div>

        <!-- Connection Settings Section -->
        <div id="section-connection" class="settings-section">
          <h2>Connection</h2>
          <div class="setting-group">
            <label class="setting-group-label">jam Server</label>
            <div class="setting-value">
              <span class="connection-dot" id="jam-settings-dot" style="display: inline-block;"></span>
              <span id="jam-settings-display">Checking...</span>
            </div>
          </div>
          <div class="setting-group">
            <label class="setting-group-label">Knowledge Base</label>
            <div class="setting-value">
              <span class="connection-dot" id="kb-settings-dot" style="display: inline-block;"></span>
              <span id="kb-settings-display">Checking...</span>
            </div>
          </div>
          <div class="setting-group">
            <label class="setting-group-label">KB API URL</label>
            <div class="setting-value" id="kb-url-display">http://localhost:8000/api/v1</div>
          </div>
        </div>

        <!-- Knowledge Base Settings Section -->
        <div id="section-knowledge-base" class="settings-section">
          <h2>Knowledge Base</h2>
          <p style="color:#6b7280; margin-bottom:16px;">Configure which knowledge base content is used when generating CVs and cover letters.</p>

          <div class="setting-group">
            <label class="setting-group-label">Search Namespaces</label>
            <p style="color:#9ca3af; font-size:0.8rem; margin-bottom:8px;">Select namespaces to search for relevant chunks during generation.</p>
            <div id="kb-search-namespaces" style="display:flex; flex-direction:column; gap:6px;">
              <span style="color:#9ca3af; font-size:0.85rem;">Loading namespaces&hellip;</span>
            </div>
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Retrieved Chunks</label>
            <p style="color:#9ca3af; font-size:0.8rem; margin-bottom:8px;">Number of relevant chunks to retrieve per search query.</p>
            <input type="number" id="kb-n-results" class="field-input" min="1" max="50" value="5" style="max-width:120px;">
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Padding</label>
            <p style="color:#9ca3af; font-size:0.8rem; margin-bottom:8px;">Number of surrounding chunks to include around each result for additional context.</p>
            <input type="number" id="kb-padding" class="field-input" min="0" max="10" value="0" style="max-width:120px;">
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Include Entire Namespaces</label>
            <p style="color:#9ca3af; font-size:0.8rem; margin-bottom:8px;">Select namespaces whose full content will be included in every generation (not just search results).</p>
            <div id="kb-include-namespaces" style="display:flex; flex-direction:column; gap:6px;">
              <span style="color:#9ca3af; font-size:0.85rem;">Loading namespaces&hellip;</span>
            </div>
          </div>

          <div id="kb-settings-msg" class="status-msg" style="margin-top:16px; display:none;"></div>
          <div style="display:flex; gap:8px; margin-top:16px;">
            <button class="btn btn-primary" onclick="saveKbSettings()">Save Knowledge Base Settings</button>
            <button class="btn" style="background:#6b7280;" onclick="testKbRetrieval()">Test Retrieval</button>
          </div>
        </div>

        <!-- AI Models Settings Section -->
        <div id="section-ai-models" class="settings-section">
          <h2>AI Models</h2>

          <div class="setting-group">
            <label class="setting-group-label">LLM Provider</label>
            <select id="ai-provider" class="field-input" onchange="onProviderChange()"></select>
            <div id="ai-key-warning" class="status-msg error" style="display:none; margin-top:8px;"></div>
          </div>

          <div class="setting-group">
            <label class="setting-group-label">LLM Model</label>
            <select id="ai-model" class="field-input" onchange="_autoSaveProviderModel()"></select>
          </div>

          <div id="ai-credentials"></div>

          <details class="step-models-details" style="margin-top:var(--space-4)">
            <summary style="cursor:pointer; font-weight:600; color:var(--text-secondary); font-size:0.92em; user-select:none; padding:4px 0;">
              Per-Step Model Overrides
            </summary>
            <div id="step-model-overrides" style="margin-top:var(--space-3);"></div>
          </details>

          <div id="ai-settings-msg" class="status-msg" style="margin-top:16px; display:none;"></div>
          <button class="btn btn-primary" style="margin-top:16px;" onclick="saveAiSettings()">Save AI Settings</button>
        </div>

        <!-- Templates Settings Section -->
        <div id="section-templates" class="settings-section">
          <h2>LaTeX Templates</h2>
          <p style="color:#6b7280; margin-bottom:16px;">Default LaTeX templates used as starting point when creating new documents.</p>

          <div class="setting-group">
            <label class="setting-group-label">CV Template</label>
            <textarea id="template-cv" class="field-input" rows="18" style="font-family:monospace; font-size:0.8rem; white-space:pre; overflow-x:auto;" placeholder="LaTeX template for CV documents..."></textarea>
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Cover Letter Template</label>
            <textarea id="template-cover-letter" class="field-input" rows="18" style="font-family:monospace; font-size:0.8rem; white-space:pre; overflow-x:auto;" placeholder="LaTeX template for cover letter documents..."></textarea>
          </div>

          <div id="template-settings-msg" class="status-msg" style="margin-top:16px; display:none;"></div>
          <button class="btn btn-primary" style="margin-top:16px;" onclick="saveTemplateSettings()">Save Templates</button>
        </div>

        <!-- System Prompts Settings Section -->
        <div id="section-prompts" class="settings-section">
          <h2>System Prompts</h2>
          <p style="color:#6b7280; margin-bottom:16px;">
            Customize the system prompts used by the AI agents during document generation.
            Available placeholders: <code>{locked_sections_notice}</code> (auto-inserted lock info),
            <code>{page_count}</code> (current page count, reduce_size only).
          </p>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Generate (First)</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_generate_first')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Used when populating a template for the first time.</p>
            <textarea id="prompt-generate-first" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Generate (Revise)</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_generate_revise')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Used when revising an existing document based on user feedback.</p>
            <textarea id="prompt-generate-revise" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Analyze Fit</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_analyze_fit')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Assesses how well the document matches the job requirements.</p>
            <textarea id="prompt-analyze-fit" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Analyze Quality</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_analyze_quality')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Reviews document for AI-sounding language, vague claims, grammar issues.</p>
            <textarea id="prompt-analyze-quality" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Apply Suggestions</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_apply_suggestions')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Applies fit and quality feedback to improve the document.</p>
            <textarea id="prompt-apply-suggestions" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div class="setting-group">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <label class="setting-group-label" style="margin-bottom:0;">Reduce Size</label>
              <button class="btn btn-secondary" style="font-size:0.75rem; padding:2px 8px;" onclick="resetPrompt('prompt_reduce_size')">Reset to default</button>
            </div>
            <p style="color:#6b7280; font-size:0.8rem; margin:4px 0 8px 0;">Shortens document to fit on one page when too long after compilation.</p>
            <textarea id="prompt-reduce-size" class="field-input" rows="6" style="font-family:monospace; font-size:0.8rem; white-space:pre-wrap;"></textarea>
          </div>

          <div id="prompt-settings-msg" class="status-msg" style="margin-top:16px; display:none;"></div>
          <button class="btn btn-primary" style="margin-top:16px;" onclick="savePromptSettings()">Save Prompts</button>
        </div>

        <!-- Email / Gmail Settings Section -->
        <div id="section-gmail" class="settings-section">
          <h2>Email / Gmail</h2>
          <p style="color:#6b7280; margin-bottom:16px;">Connect your Gmail account to read and compose emails for job applications.</p>

          <div class="setting-group">
            <label class="setting-group-label">Status</label>
            <div class="setting-value">
              <span class="connection-dot disconnected" id="gmail-status-dot" style="display:inline-block;"></span>
              <span id="gmail-status-text">Not connected</span>
            </div>
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Client ID</label>
            <input type="text" id="gmail-client-id" class="field-input" placeholder="123456789-abc.apps.googleusercontent.com">
          </div>

          <div class="setting-group">
            <label class="setting-group-label">Client Secret</label>
            <div style="position:relative;">
              <input type="password" id="gmail-client-secret" class="field-input" placeholder="GOCSPX-...">
              <button type="button" style="position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:#6b7280;cursor:pointer;font-size:0.75rem;" onclick="toggleGmailSecret(this)">show</button>
            </div>
          </div>

          <p style="color:#6b7280; margin-bottom:16px; font-size:0.875rem;">Permissions requested: read emails, compose and send emails. Create a project in Google Cloud Console, enable the Gmail API, and create OAuth 2.0 credentials (Web application type) with redirect URI: <code>http://localhost:8001/gmail/callback</code></p>

          <div id="gmail-settings-msg" class="status-msg" style="margin-top:16px; display:none;"></div>
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:16px;">
            <button class="btn btn-primary" onclick="saveGmailCredentials()">Save Credentials</button>
            <button class="btn btn-primary" onclick="connectGmail()">Connect Gmail</button>
            <button id="gmail-disconnect-btn" class="btn btn-secondary" onclick="disconnectGmail()" style="display:none;">Disconnect</button>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Detail View -->
  <main id="detail-view" class="detail-view" style="display: none;">
    <div class="detail-container">
      <div class="detail-sidebar">
        <div class="detail-back">
          <button class="btn btn-secondary" onclick="switchToDashboard()" style="font-size:0.85rem;padding:6px 14px;">← Back</button>
        </div>
        <div class="detail-app-header">
          <h3 id="detail-company"></h3>
          <p id="detail-position"></p>
          <span id="detail-status-badge" class="badge" style="margin-top:8px;display:inline-block;"></span>
        </div>
        <ul class="detail-sidebar-menu">
          <li><button class="detail-step-btn active" data-step="app-details" onclick="switchDetailStep('app-details')">Application Details</button></li>
          <li><button class="detail-step-btn" data-step="cv-cover" onclick="switchDetailStep('cv-cover')">CV &amp; Cover Letters</button></li>
          <li><button class="detail-step-btn" data-step="extra-questions" onclick="switchDetailStep('extra-questions')">Extra Questions</button></li>
          <li><button class="detail-step-btn" data-step="interviews" onclick="switchDetailStep('interviews')">Interviews</button></li>
          <li><button class="detail-step-btn" data-step="offers" onclick="switchDetailStep('offers')">Offers</button></li>
        </ul>
      </div>
      <div class="detail-content">
        <!-- Step: Application Details -->
        <div id="step-app-details" class="detail-step active">
          <h2>Application Details</h2>
          <div id="detail-form-msg" class="status-msg" style="display:none;margin-bottom:16px;"></div>
          <div class="detail-form-grid">
            <div class="form-group">
              <label class="field-label">Company Name *</label>
              <input type="text" id="detail-company-input" class="field-input" required />
            </div>
            <div class="form-group">
              <label class="field-label">Position *</label>
              <input type="text" id="detail-position-input" class="field-input" required />
            </div>
            <div class="form-group">
              <label class="field-label">Status</label>
              <select id="detail-status" class="field-input">
              <option value="not_applied_yet">Not Applied Yet</option>
                <option value="applied">Applied</option>
                <option value="screening">Screening</option>
                <option value="interviewing">Interviewing</option>
                <option value="offered">Offered</option>
                <option value="rejected">Rejected</option>
                <option value="accepted">Accepted</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </div>
            <div class="form-group">
              <label class="field-label">Date Applied</label>
              <input type="date" id="detail-applied-date" class="field-input" />
            </div>
            <div class="form-group">
              <label class="field-label">Salary Range</label>
              <input type="text" id="detail-salary-range" class="field-input" placeholder="e.g. $120k - $150k" />
            </div>
            <div class="form-group">
              <label class="field-label">Location</label>
              <input type="text" id="detail-location" class="field-input" placeholder="e.g. New York, NY" />
            </div>
            <div class="form-group">
              <label class="field-label">Work Mode</label>
              <select id="detail-work-mode" class="field-input">
                <option value="">— Select —</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </div>
            <div class="form-group">
              <label class="field-label">Contact Person</label>
              <input type="text" id="detail-contact-person" class="field-input" placeholder="e.g. Jane Smith, Recruiter" />
            </div>
            <div class="form-group">
              <label class="field-label">Opening Date</label>
              <input type="date" id="detail-opening-date" class="field-input" />
            </div>
            <div class="form-group">
              <label class="field-label">Closing Date</label>
              <input type="date" id="detail-closing-date" class="field-input" />
            </div>
            <div class="form-group full-width">
              <label class="field-label">URL</label>
              <input type="url" id="detail-url" class="field-input" placeholder="https://..." />
            </div>
            <div class="form-group full-width">
              <label class="field-label">Description</label>
              <textarea id="detail-description" class="field-input" rows="3" placeholder="Role description..."></textarea>
            </div>
            <div class="form-group full-width">
              <label class="field-label">Notes</label>
              <textarea id="detail-notes" class="field-input" rows="4" placeholder="Additional notes..."></textarea>
            </div>
          </div>
          <div class="detail-form-actions">
            <button class="btn btn-danger" onclick="deleteFromDetail()">Delete</button>
            <button class="btn btn-primary" onclick="saveDetailForm()">Save Changes</button>
          </div>
          <div id="detail-full-text-section" style="display:none;margin-top:32px;border-top:1px solid #e5e7eb;padding-top:24px;">
            <h3 style="font-size:1rem;font-weight:700;color:#16213e;margin-bottom:12px;">Full Extracted Text</h3>
            <pre id="detail-full-text" style="white-space:pre-wrap;word-break:break-word;font-size:0.8rem;color:#4b5563;background:#f9fafb;padding:16px;border-radius:10px;border:1px solid #e5e7eb;max-height:400px;overflow-y:auto;font-family:inherit;margin:0;"></pre>
          </div>
        </div>

        <!-- Step: CV & Cover Letters -->
        <div id="step-cv-cover" class="detail-step">
          <h2>CV &amp; Cover Letters</h2>

          <!-- Document type tabs -->
          <div class="tab-bar" style="border-radius:8px 8px 0 0; margin-bottom:0;">
            <button class="tab-btn-doc active" data-doctab="cv" onclick="_switchDocTab('cv')">CVs</button>
            <button class="tab-btn-doc" data-doctab="cover_letter" onclick="_switchDocTab('cover_letter')">Cover Letters</button>
            <button id="trisplit-fs-btn" class="trisplit-fs-btn" onclick="_toggleTrisplitFullscreen()" title="Toggle fullscreen">&#x26F6; Fullscreen</button>
          </div>

          <!-- CV tab -->
          <div id="doc-panel-cv" class="doc-tab-panel active">
            <div class="doc-list-bar">
              <select id="cv-doc-select" onchange="_onDocSelect('cv')"><option value="">-- no documents --</option></select>
              <button class="btn btn-sm btn-primary" onclick="_createDoc('cv')">+ New</button>
              <button class="btn btn-sm btn-green" onclick="_saveCurrentDoc('cv')">Save</button>
              <button class="btn btn-sm btn-primary" onclick="_compileDoc('cv')">Compile</button>
              <button class="btn btn-sm btn-generate" onclick="_generateDoc('cv')">Generate</button>
              <button class="btn btn-sm btn-critique" onclick="_critiqueDoc('cv')">Critique</button>
              <button class="btn btn-sm" id="cv-download-btn" onclick="_downloadPdf('cv')" style="display:none">Download PDF</button>
              <button class="btn btn-sm btn-danger" onclick="_deleteCurrentDoc('cv')">Delete</button>
              <button class="btn btn-sm" onclick="_renameCurrentDoc('cv')">Rename</button>
              <span id="cv-save-status" class="doc-compile-status"></span>
              <span id="cv-gen-status" class="doc-compile-status"></span>
            </div>
            <div id="cv-gen-progress" class="gen-progress-tracker" style="display:none" aria-live="polite" aria-label="CV generation progress"></div>
            <div id="cv-trisplit" class="trisplit-container">
              <div class="trisplit-pane" data-pane="0">
                <div class="trisplit-pane-header">
                  <span>Instructions</span>
                  <button class="btn btn-sm" onclick="_clearInstructions('cv')" title="Clear all instructions" style="font-size:0.65rem; padding:1px 6px; margin-left:auto;">Clear</button>
                  <button onclick="_togglePane('cv-trisplit',0)" title="Collapse/Expand">&#x25C0;</button>
                </div>
                <div class="trisplit-pane-body">
                  <div id="cv-instructions-panel" class="instructions-panel"></div>
                </div>
              </div>
              <div class="trisplit-pane" data-pane="1">
                <div class="trisplit-pane-header"><span>LaTeX Source <span class="help-tip" title="Add % [COMMENT: your note] anywhere in the source to guide the AI">?</span></span><button onclick="_togglePane('cv-trisplit',1)" title="Collapse/Expand">&#x25C0;&#x25B6;</button></div>
                <div class="trisplit-pane-body"><textarea id="cv-latex-editor" placeholder="\\documentclass{article}&#10;\\begin{document}&#10;Your content here.&#10;\\end{document}" spellcheck="false"></textarea></div>
              </div>
              <div class="trisplit-pane" data-pane="2">
                <div class="trisplit-pane-header"><span>PDF Preview</span><button onclick="_togglePane('cv-trisplit',2)" title="Collapse/Expand">&#x25B6;</button></div>
                <div class="trisplit-pane-body" style="position:relative;"><div id="cv-preview-frame" class="doc-preview-frame"><div class="pdf-placeholder">No document selected</div></div><div id="cv-compile-overlay" class="compile-overlay" style="display:none;"><div class="compile-spinner"></div><span>Compiling...</span></div></div>
              </div>
            </div>
            <div id="cv-version-bar" class="doc-version-bar">
              <span>Versions:</span>
              <span id="cv-version-list">--</span>
            </div>
            <div id="cv-agent-feedback" class="agent-feedback-panel" style="display:none">
              <details open><summary>Fit Analysis</summary><pre id="cv-fit-feedback" class="feedback-text"></pre></details>
              <details open><summary>Quality Analysis</summary><pre id="cv-quality-feedback" class="feedback-text"></pre></details>
              <details><summary>Generation Prompt (System)</summary><pre id="cv-generation-system-prompt" class="feedback-text"></pre></details>
              <details><summary>Generation Prompt (User Context)</summary><pre id="cv-generation-user-prompt" class="feedback-text"></pre></details>
            </div>
          </div>

          <!-- Cover Letter tab -->
          <div id="doc-panel-cover_letter" class="doc-tab-panel">
            <div class="doc-list-bar">
              <select id="cover_letter-doc-select" onchange="_onDocSelect('cover_letter')"><option value="">-- no documents --</option></select>
              <button class="btn btn-sm btn-primary" onclick="_createDoc('cover_letter')">+ New</button>
              <button class="btn btn-sm btn-green" onclick="_saveCurrentDoc('cover_letter')">Save</button>
              <button class="btn btn-sm btn-primary" onclick="_compileDoc('cover_letter')">Compile</button>
              <button class="btn btn-sm btn-generate" onclick="_generateDoc('cover_letter')">Generate</button>
              <button class="btn btn-sm btn-critique" onclick="_critiqueDoc('cover_letter')">Critique</button>
              <button class="btn btn-sm" id="cover_letter-download-btn" onclick="_downloadPdf('cover_letter')" style="display:none">Download PDF</button>
              <button class="btn btn-sm btn-danger" onclick="_deleteCurrentDoc('cover_letter')">Delete</button>
              <button class="btn btn-sm" onclick="_renameCurrentDoc('cover_letter')">Rename</button>
              <span id="cover_letter-save-status" class="doc-compile-status"></span>
              <span id="cover_letter-gen-status" class="doc-compile-status"></span>
            </div>
            <div id="cover_letter-gen-progress" class="gen-progress-tracker" style="display:none" aria-live="polite" aria-label="Cover letter generation progress"></div>
            <div id="cover_letter-trisplit" class="trisplit-container">
              <div class="trisplit-pane" data-pane="0">
                <div class="trisplit-pane-header">
                  <span>Instructions</span>
                  <button class="btn btn-sm" onclick="_clearInstructions('cover_letter')" title="Clear all instructions" style="font-size:0.65rem; padding:1px 6px; margin-left:auto;">Clear</button>
                  <button onclick="_togglePane('cover_letter-trisplit',0)" title="Collapse/Expand">&#x25C0;</button>
                </div>
                <div class="trisplit-pane-body">
                  <div id="cover_letter-instructions-panel" class="instructions-panel"></div>
                </div>
              </div>
              <div class="trisplit-pane" data-pane="1">
                <div class="trisplit-pane-header"><span>LaTeX Source <span class="help-tip" title="Add % [COMMENT: your note] anywhere in the source to guide the AI">?</span></span><button onclick="_togglePane('cover_letter-trisplit',1)" title="Collapse/Expand">&#x25C0;&#x25B6;</button></div>
                <div class="trisplit-pane-body"><textarea id="cover_letter-latex-editor" placeholder="\\documentclass{article}&#10;\\begin{document}&#10;Your content here.&#10;\\end{document}" spellcheck="false"></textarea></div>
              </div>
              <div class="trisplit-pane" data-pane="2">
                <div class="trisplit-pane-header"><span>PDF Preview</span><button onclick="_togglePane('cover_letter-trisplit',2)" title="Collapse/Expand">&#x25B6;</button></div>
                <div class="trisplit-pane-body" style="position:relative;"><div id="cover_letter-preview-frame" class="doc-preview-frame"><div class="pdf-placeholder">No document selected</div></div><div id="cover_letter-compile-overlay" class="compile-overlay" style="display:none;"><div class="compile-spinner"></div><span>Compiling...</span></div></div>
              </div>
            </div>
            <div id="cover_letter-version-bar" class="doc-version-bar">
              <span>Versions:</span>
              <span id="cover_letter-version-list">--</span>
            </div>
            <div id="cover_letter-agent-feedback" class="agent-feedback-panel" style="display:none">
              <details open><summary>Fit Analysis</summary><pre id="cover_letter-fit-feedback" class="feedback-text"></pre></details>
              <details open><summary>Quality Analysis</summary><pre id="cover_letter-quality-feedback" class="feedback-text"></pre></details>
              <details><summary>Generation Prompt (System)</summary><pre id="cover_letter-generation-system-prompt" class="feedback-text"></pre></details>
              <details><summary>Generation Prompt (User Context)</summary><pre id="cover_letter-generation-user-prompt" class="feedback-text"></pre></details>
            </div>
          </div>
        </div>

        <!-- Step: Extra Questions -->
        <div id="step-extra-questions" class="detail-step">
          <div class="eq-header">
            <h2>Extra Questions</h2>
            <button class="btn btn-sm btn-primary" onclick="_eqAdd()">+ Add Question</button>
          </div>
          <div id="eq-list"></div>
          <p id="eq-empty" class="placeholder-text">No questions yet. Click "+ Add Question" to get started.</p>
        </div>

        <!-- Step: Interviews -->
        <div id="step-interviews" class="detail-step">
          <div class="section-header-row" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
            <h2 style="margin:0;">Interviews</h2>
            <button class="btn btn-primary btn-sm" onclick="_ivAdd()">+ Add Round</button>
          </div>
          <p id="iv-empty" class="placeholder-text">No interview rounds yet</p>
          <div id="iv-list"></div>
        </div>

        <!-- Step: Offers -->
        <div id="step-offers" class="detail-step">
          <div class="section-header-row" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
            <h2 style="margin:0;">Offers</h2>
            <button class="btn btn-primary btn-sm" onclick="_ofAdd()">+ Add Offer</button>
          </div>
          <p id="of-empty" class="placeholder-text">No offers yet</p>
          <div id="of-list"></div>
        </div>
      </div>
    </div>
  </main>
</div>

<!-- Modal for creating/editing applications -->
<div id="app-modal" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h2 id="modal-title">New Application</h2>
      <button class="modal-close" onclick="closeApplicationModal()">&times;</button>
    </div>

    <form id="app-form" onsubmit="handleApplicationFormSubmit(event)">
      <div class="modal-body">
        <div class="form-group">
          <label class="field-label">Company Name *</label>
          <input type="text" id="form-company" class="field-input" required />
        </div>

        <div class="form-group">
          <label class="field-label">Position *</label>
          <input type="text" id="form-position" class="field-input" required />
        </div>

        <div class="form-group">
          <label class="field-label">Status</label>
          <select id="form-status" class="field-input">
            <option value="not_applied_yet">Not Applied Yet</option>
            <option value="applied">Applied</option>
            <option value="screening">Screening</option>
            <option value="interviewing">Interviewing</option>
            <option value="offered">Offered</option>
            <option value="rejected">Rejected</option>
            <option value="accepted">Accepted</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
        </div>

        <div class="form-group">
          <label class="field-label">Date Applied</label>
          <input type="date" id="form-applied-date" class="field-input" />
        </div>

        <div class="form-group">
          <label class="field-label">URL</label>
          <input type="url" id="form-url" class="field-input" placeholder="https://..." />
        </div>

        <div class="form-group">
          <label class="field-label">Notes</label>
          <textarea id="form-notes" class="field-input" placeholder="Additional notes about this application..."></textarea>
        </div>

        <div id="form-message" style="display: none;" class="status-msg"></div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" onclick="closeApplicationModal()">Cancel</button>
        <button type="button" id="delete-btn" class="btn btn-danger" onclick="handleDelete()" style="display: none; margin-right: auto;">Delete</button>
        <button type="submit" class="btn btn-primary" id="submit-btn">Save</button>
      </div>
    </form>
  </div>
</div>

<script>
const API_BASE = "/api/v1";
if (typeof pdfjsLib !== "undefined") {
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}
let currentEditingId = null;
let allApplications = [];
let currentDetailId = null;

// API Helper
async function apiFetch(method, url, body) {
  const opts = { method, cache: "no-store" };
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
  if (resp.status === 204) {
    return resp;
  }
  return resp;
}

// Load and render applications
async function loadApplications() {
  try {
    const resp = await apiFetch("GET", "/applications");
    const data = await resp.json();
    allApplications = data;
    renderApplications();
    updateStats();
  } catch (e) {
    console.error("Failed to load applications:", e);
  }
}

function renderApplications() {
  const container = document.getElementById("applications-container");
  
  if (allApplications.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="icon">📋</div>
        <h3>No applications yet</h3>
        <p>Click "New Application" to get started tracking your job applications.</p>
      </div>
    `;
    return;
  }

  const html = allApplications.map(app => {
    const appliedDate = new Date(app.applied_date);
    const dateStr = appliedDate.toLocaleDateString();
    const statusBadgeClass = "badge-" + app.status;
    const statusLabel = app.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    
    return `
      <div class="app-tile" onclick="openDetailPage('${app.id}')">
        <div class="app-tile-company">${escapeHtml(app.company)}</div>
        <div class="app-tile-position">${escapeHtml(app.position)}</div>
        <div class="app-tile-meta">
          <span class="app-tile-date">${dateStr}</span>
          <span class="badge ${statusBadgeClass} app-tile-status">${statusLabel}</span>
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = `<div class="applications-grid">${html}</div>`;
}

function updateStats() {
  const total = allApplications.length;
  const active = allApplications.filter(a => 
    a.status === "not_applied_yet" || a.status === "applied" || a.status === "screening" || a.status === "interviewing"
  ).length;
  const interviewing = allApplications.filter(a => a.status === "interviewing").length;
  const offers = allApplications.filter(a => a.status === "offered").length;

  document.getElementById("stat-total").textContent = total;
  document.getElementById("stat-active").textContent = active;
  document.getElementById("stat-interviewing").textContent = interviewing;
  document.getElementById("stat-offers").textContent = offers;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Modal functions
function openNewApplicationModal() {
  currentEditingId = null;
  document.getElementById("modal-title").textContent = "New Application";
  document.getElementById("app-form").reset();
  document.getElementById("delete-btn").style.display = "none";
  document.getElementById("form-applied-date").valueAsDate = new Date();
  document.getElementById("form-message").style.display = "none";
  document.getElementById("app-modal").classList.add("open");
}

async function openDetailPage(appId) {
  try {
    const resp = await apiFetch("GET", "/applications/" + appId);
    const app = await resp.json();

    currentDetailId = appId;
    _docTabLoaded = { cv: false, cover_letter: false };
    _currentDocId = { cv: null, cover_letter: null };
    _eqLoaded = false;
    _ivLoaded = false;
    _ofLoaded = false;

    // Update sidebar header
    document.getElementById("detail-company").textContent = app.company;
    document.getElementById("detail-position").textContent = app.position;
    const badge = document.getElementById("detail-status-badge");
    badge.textContent = app.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    badge.className = "badge badge-" + app.status;

    // Populate form
    document.getElementById("detail-company-input").value = app.company;
    document.getElementById("detail-position-input").value = app.position;
    document.getElementById("detail-status").value = app.status;
    document.getElementById("detail-applied-date").value = app.applied_date;
    document.getElementById("detail-url").value = app.url || "";
    document.getElementById("detail-notes").value = app.notes || "";
    document.getElementById("detail-salary-range").value = app.salary_range || "";
    document.getElementById("detail-location").value = app.location || "";
    document.getElementById("detail-work-mode").value = app.work_mode || "";
    document.getElementById("detail-contact-person").value = app.contact_person || "";
    document.getElementById("detail-opening-date").value = app.opening_date || "";
    document.getElementById("detail-closing-date").value = app.closing_date || "";
    document.getElementById("detail-description").value = app.description || "";

    // Full extracted text
    const fullTextSection = document.getElementById("detail-full-text-section");
    if (app.full_text) {
      document.getElementById("detail-full-text").textContent = app.full_text;
      fullTextSection.style.display = "block";
    } else {
      fullTextSection.style.display = "none";
    }

    // Hide form message
    document.getElementById("detail-form-msg").style.display = "none";

    // Reset to first step
    switchDetailStep("app-details");

    // Show detail view, hide others
    document.getElementById("dashboard-view").style.display = "none";
    document.getElementById("settings-view").style.display = "none";
    document.getElementById("detail-view").style.display = "flex";
  } catch (e) {
    console.error("Failed to load application:", e);
    alert("Failed to load application details");
  }
}

function closeApplicationModal() {
  document.getElementById("app-modal").classList.remove("open");
  currentEditingId = null;
}

async function handleApplicationFormSubmit(event) {
  event.preventDefault();
  
  const company = document.getElementById("form-company").value;
  const position = document.getElementById("form-position").value;
  const status = document.getElementById("form-status").value;
  const appliedDate = document.getElementById("form-applied-date").value;
  const url = document.getElementById("form-url").value;
  const notes = document.getElementById("form-notes").value;

  const body = {
    company,
    position,
    status,
    applied_date: appliedDate,
    url: url || null,
    notes: notes || null,
  };

  try {
    const msgEl = document.getElementById("form-message");
    if (currentEditingId) {
      // Update
      await apiFetch("PUT", "/applications/" + currentEditingId, body);
      msgEl.textContent = "Application updated successfully";
      msgEl.className = "status-msg success";
      msgEl.style.display = "block";
      setTimeout(() => {
        closeApplicationModal();
        loadApplications();
      }, 800);
    } else {
      // Create
      await apiFetch("POST", "/applications", body);
      msgEl.textContent = "Application created successfully";
      msgEl.className = "status-msg success";
      msgEl.style.display = "block";
      setTimeout(() => {
        closeApplicationModal();
        loadApplications();
      }, 800);
    }
  } catch (e) {
    const msgEl = document.getElementById("form-message");
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
    msgEl.style.display = "block";
  }
}

async function handleDelete() {
  if (!currentEditingId) return;
  if (!confirm("Are you sure you want to delete this application?")) return;

  try {
    await apiFetch("DELETE", "/applications/" + currentEditingId);
    closeApplicationModal();
    loadApplications();
  } catch (e) {
    alert("Failed to delete application: " + e.message);
  }
}

// Detail view navigation
function switchDetailStep(step) {
  document.querySelectorAll(".detail-step").forEach(function(el) { el.classList.remove("active"); });
  document.querySelectorAll(".detail-step-btn").forEach(function(el) { el.classList.remove("active"); });
  document.getElementById("step-" + step).classList.add("active");
  document.querySelector('.detail-step-btn[data-step="' + step + '"]').classList.add("active");
  if (step === "cv-cover" && currentDetailId) {
    if (!_docTabLoaded.cv) {
      _loadDocuments("cv");
      _docTabLoaded.cv = true;
    }
  }
  if (step === "extra-questions" && currentDetailId && !_eqLoaded) {
    _eqLoad();
    _eqLoaded = true;
  }
  if (step === "interviews" && currentDetailId && !_ivLoaded) { _ivLoaded = true; _ivLoad(); }
  if (step === "offers" && currentDetailId && !_ofLoaded) { _ofLoaded = true; _ofLoad(); }
  var dc = document.querySelector(".detail-content");
  if (dc) {
    if (step === "cv-cover") {
      dc.classList.add("no-outer-scroll");
    } else {
      dc.classList.remove("no-outer-scroll");
    }
  }
}

async function saveDetailForm() {
  if (!currentDetailId) return;
  const msgEl = document.getElementById("detail-form-msg");

  const body = {
    company: document.getElementById("detail-company-input").value,
    position: document.getElementById("detail-position-input").value,
    status: document.getElementById("detail-status").value,
    applied_date: document.getElementById("detail-applied-date").value,
    url: document.getElementById("detail-url").value || null,
    notes: document.getElementById("detail-notes").value || null,
    salary_range: document.getElementById("detail-salary-range").value || null,
    location: document.getElementById("detail-location").value || null,
    work_mode: document.getElementById("detail-work-mode").value || null,
    contact_person: document.getElementById("detail-contact-person").value || null,
    opening_date: document.getElementById("detail-opening-date").value || null,
    closing_date: document.getElementById("detail-closing-date").value || null,
    description: document.getElementById("detail-description").value || null,
  };

  try {
    const resp = await apiFetch("PUT", "/applications/" + currentDetailId, body);
    const app = await resp.json();

    // Update sidebar header
    document.getElementById("detail-company").textContent = app.company;
    document.getElementById("detail-position").textContent = app.position;
    const badge = document.getElementById("detail-status-badge");
    badge.textContent = app.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    badge.className = "badge badge-" + app.status;

    msgEl.textContent = "Changes saved successfully";
    msgEl.className = "status-msg success";
    msgEl.style.display = "block";
    setTimeout(function() { msgEl.style.display = "none"; }, 3000);
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
    msgEl.style.display = "block";
  }
}

async function deleteFromDetail() {
  if (!currentDetailId) return;
  if (!confirm("Are you sure you want to delete this application?")) return;

  try {
    await apiFetch("DELETE", "/applications/" + currentDetailId);
    currentDetailId = null;
    switchToDashboard();
  } catch (e) {
    alert("Failed to delete: " + e.message);
  }
}

// ── Personal Info settings ──────────────────────────────────────────────────

function handleImageUpload(input, previewId, settingKey) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    const dataUri = e.target.result;
    if (settingKey === "personal_photo") {
      // Route through circular crop modal for profile photo
      openCropModal(dataUri, previewId, settingKey);
    } else if (settingKey === "personal_signature") {
      // Route through rectangle crop modal for signature
      openRectCropModal(dataUri, previewId, settingKey);
    } else {
      // Direct preview for other images
      const preview = document.getElementById(previewId);
      preview.src = dataUri;
      preview.style.display = "block";
      document.getElementById(previewId.replace("preview", "remove")).style.display = "";
      _stored[settingKey] = dataUri;
    }
  };
  reader.readAsDataURL(file);
}

// ── Crop modal ───────────────────────────────────────────────────────────────

(function() {
  // Internal state for the active crop session
  let _cropImg = null;       // HTMLImageElement displayed in the modal
  let _cropCanvas = null;    // overlay canvas
  let _cropCtx = null;
  let _cropPreviewId = null;
  let _cropSettingKey = null;

  // Circle state (in image-display coordinates, not natural coordinates)
  let _circle = { x: 0, y: 0, r: 0 };

  // Interaction state
  let _drag = null; // null | { type: "move"|"resize", startX, startY, startCircle }

  // Expose public functions on window
  window.openCropModal = function(dataUri, previewId, settingKey) {
    _cropPreviewId = previewId;
    _cropSettingKey = settingKey;

    // Build modal if it doesn't exist yet
    let overlay = document.getElementById("crop-modal-overlay");
    if (!overlay) {
      overlay = _buildCropModal();
      document.body.appendChild(overlay);
    }

    const container = document.getElementById("crop-container");
    // Remove old image and canvas
    container.innerHTML = "";

    _cropImg = new Image();
    _cropImg.alt = "Image to crop";
    _cropImg.style.cssText = "display:block; max-width:100%; max-height:460px; pointer-events:none; user-select:none;";

    _cropImg.onload = function() {
      // Now that the image is rendered we can set up the canvas
      const dispW = _cropImg.offsetWidth;
      const dispH = _cropImg.offsetHeight;

      _cropCanvas = document.createElement("canvas");
      _cropCanvas.className = "crop-overlay-canvas";
      _cropCanvas.width = dispW;
      _cropCanvas.height = dispH;
      _cropCanvas.style.cssText = "position:absolute; top:0; left:0; pointer-events:none;";
      container.appendChild(_cropCanvas);
      _cropCtx = _cropCanvas.getContext("2d");

      // Initial circle: largest possible circle centred in the image
      const r = Math.floor(Math.min(dispW, dispH) / 2) - 4;
      _circle = { x: Math.floor(dispW / 2), y: Math.floor(dispH / 2), r: Math.max(25, r) };

      _drawCropOverlay();

      // Sync canvas size if window resizes
      const ro = new ResizeObserver(() => _onCropResize());
      ro.observe(container);
      container._cropRO = ro;
    };

    _cropImg.src = dataUri;
    container.appendChild(_cropImg);

    // Pointer events on container
    container.addEventListener("mousedown", _onCropMouseDown);
    container.addEventListener("mousemove", _onCropMouseMove);
    container.addEventListener("mouseup", _onCropMouseUp);
    container.addEventListener("mouseleave", _onCropMouseUp);
    container.addEventListener("wheel", _onCropWheel, { passive: false });

    overlay.classList.add("open");
  };

  window.closeCropModal = function() {
    const overlay = document.getElementById("crop-modal-overlay");
    if (!overlay) return;
    overlay.classList.remove("open");

    // Clean up event listeners and observer
    const container = document.getElementById("crop-container");
    if (container) {
      container.removeEventListener("mousedown", _onCropMouseDown);
      container.removeEventListener("mousemove", _onCropMouseMove);
      container.removeEventListener("mouseup", _onCropMouseUp);
      container.removeEventListener("mouseleave", _onCropMouseUp);
      container.removeEventListener("wheel", _onCropWheel);
      if (container._cropRO) {
        container._cropRO.disconnect();
        container._cropRO = null;
      }
    }
    _drag = null;
    // Reset the file input so the same file can be re-selected
    const inputId = _cropPreviewId ? _cropPreviewId.replace("preview", "input") : null;
    if (inputId) {
      const el = document.getElementById(inputId);
      if (el) el.value = "";
    }
  };

  window.applyCrop = function() {
    if (!_cropImg || !_cropCanvas) return;

    const dispW = _cropCanvas.width;
    const dispH = _cropCanvas.height;
    const natW = _cropImg.naturalWidth;
    const natH = _cropImg.naturalHeight;

    // Scale factors from display coords to natural image coords
    const scaleX = natW / dispW;
    const scaleY = natH / dispH;

    const natCx = _circle.x * scaleX;
    const natCy = _circle.y * scaleY;
    const natR  = _circle.r * Math.min(scaleX, scaleY);

    const size = Math.ceil(natR * 2);
    const offscreen = document.createElement("canvas");
    offscreen.width = size;
    offscreen.height = size;
    const ctx = offscreen.getContext("2d");

    // Clip to circle
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();

    // Draw the relevant region of the natural image
    ctx.drawImage(
      _cropImg,
      natCx - natR, natCy - natR, natR * 2, natR * 2,
      0, 0, size, size
    );

    const resultUri = offscreen.toDataURL("image/png");

    // Update preview
    const preview = document.getElementById(_cropPreviewId);
    preview.src = resultUri;
    preview.style.display = "block";
    document.getElementById(_cropPreviewId.replace("preview", "remove")).style.display = "";
    _stored[_cropSettingKey] = resultUri;

    closeCropModal();
  };

  // ── Build DOM ──────────────────────────────────────────────────────────────

  function _buildCropModal() {
    const overlay = document.createElement("div");
    overlay.id = "crop-modal-overlay";
    overlay.className = "crop-modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "crop-modal-title");

    overlay.innerHTML = `
      <div class="crop-modal">
        <p class="crop-modal-title" id="crop-modal-title">Crop Profile Photo</p>
        <p class="crop-modal-hint">Drag the circle to reposition. Scroll to resize.</p>
        <div id="crop-container" class="crop-container" style="cursor:move;"></div>
        <div class="crop-modal-footer">
          <button type="button" class="btn btn-secondary" onclick="closeCropModal()">Cancel</button>
          <button type="button" class="btn btn-primary" onclick="applyCrop()">Crop</button>
        </div>
      </div>
    `;

    // Close on overlay click (outside modal)
    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) closeCropModal();
    });

    return overlay;
  }

  // ── Drawing ────────────────────────────────────────────────────────────────

  function _drawCropOverlay() {
    if (!_cropCtx || !_cropCanvas) return;
    const w = _cropCanvas.width;
    const h = _cropCanvas.height;
    const { x, y, r } = _circle;

    _cropCtx.clearRect(0, 0, w, h);

    // Dark overlay outside circle using composite ops
    _cropCtx.save();
    _cropCtx.fillStyle = "rgba(0,0,0,0.55)";
    _cropCtx.fillRect(0, 0, w, h);
    _cropCtx.globalCompositeOperation = "destination-out";
    _cropCtx.beginPath();
    _cropCtx.arc(x, y, r, 0, Math.PI * 2);
    _cropCtx.fill();
    _cropCtx.restore();

    // Circle border
    _cropCtx.save();
    _cropCtx.strokeStyle = "#4f46e5";
    _cropCtx.lineWidth = 2;
    _cropCtx.beginPath();
    _cropCtx.arc(x, y, r, 0, Math.PI * 2);
    _cropCtx.stroke();
    _cropCtx.restore();

    // Resize handle — small square at bottom-right of circle
    const hx = x + r * Math.cos(Math.PI / 4);
    const hy = y + r * Math.sin(Math.PI / 4);
    _cropCtx.save();
    _cropCtx.fillStyle = "#4f46e5";
    _cropCtx.fillRect(hx - 5, hy - 5, 10, 10);
    _cropCtx.restore();
  }

  // ── Resize observer ────────────────────────────────────────────────────────

  function _onCropResize() {
    if (!_cropImg || !_cropCanvas) return;
    const newW = _cropImg.offsetWidth;
    const newH = _cropImg.offsetHeight;
    if (newW === _cropCanvas.width && newH === _cropCanvas.height) return;
    // Scale circle proportionally
    const sx = newW / _cropCanvas.width;
    const sy = newH / _cropCanvas.height;
    _circle.x = Math.round(_circle.x * sx);
    _circle.y = Math.round(_circle.y * sy);
    _circle.r = Math.round(_circle.r * Math.min(sx, sy));
    _cropCanvas.width = newW;
    _cropCanvas.height = newH;
    _cropCanvas.style.width = newW + "px";
    _cropCanvas.style.height = newH + "px";
    _clampCircle();
    _drawCropOverlay();
  }

  // ── Pointer helpers ────────────────────────────────────────────────────────

  function _containerXY(e) {
    const rect = _cropCanvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function _distToHandle(px, py) {
    const hx = _circle.x + _circle.r * Math.cos(Math.PI / 4);
    const hy = _circle.y + _circle.r * Math.sin(Math.PI / 4);
    return Math.sqrt((px - hx) ** 2 + (py - hy) ** 2);
  }

  function _clampCircle() {
    const w = _cropCanvas.width;
    const h = _cropCanvas.height;
    const minR = 25;
    _circle.r = Math.max(minR, Math.min(_circle.r, Math.floor(Math.min(w, h) / 2)));
    _circle.x = Math.max(_circle.r, Math.min(_circle.x, w - _circle.r));
    _circle.y = Math.max(_circle.r, Math.min(_circle.y, h - _circle.r));
  }

  function _onCropMouseDown(e) {
    if (!_cropCanvas) return;
    e.preventDefault();
    const { x, y } = _containerXY(e);
    if (_distToHandle(x, y) <= 12) {
      _drag = { type: "resize", startX: x, startY: y, startCircle: { ..._circle } };
    } else {
      const dx = x - _circle.x, dy = y - _circle.y;
      if (Math.sqrt(dx * dx + dy * dy) <= _circle.r) {
        _drag = { type: "move", startX: x, startY: y, startCircle: { ..._circle } };
      }
    }
  }

  function _onCropMouseMove(e) {
    if (!_drag || !_cropCanvas) return;
    e.preventDefault();
    const { x, y } = _containerXY(e);
    const dx = x - _drag.startX;
    const dy = y - _drag.startY;

    if (_drag.type === "move") {
      _circle.x = _drag.startCircle.x + dx;
      _circle.y = _drag.startCircle.y + dy;
    } else {
      // resize: distance from centre to current pointer
      const newR = Math.round(Math.sqrt(
        (x - _drag.startCircle.x) ** 2 + (y - _drag.startCircle.y) ** 2
      ));
      _circle.r = newR;
    }
    _clampCircle();
    _drawCropOverlay();
  }

  function _onCropMouseUp(e) {
    _drag = null;
  }

  function _onCropWheel(e) {
    if (!_cropCanvas) return;
    e.preventDefault();
    const delta = e.deltaY > 0 ? -8 : 8;
    _circle.r += delta;
    _clampCircle();
    _drawCropOverlay();
  }
})();

// ── Rectangle crop modal ─────────────────────────────────────────────────────

(function() {
  // Internal state for the active rect crop session
  let _rImg = null;          // HTMLImageElement displayed in the modal
  let _rCanvas = null;       // overlay canvas
  let _rCtx = null;
  let _rPreviewId = null;
  let _rSettingKey = null;

  // Rectangle state in image-display coordinates: { x, y, w, h }
  // (x, y) is the top-left corner
  let _rect = { x: 0, y: 0, w: 0, h: 0 };

  // Interaction state
  // type: "move" | "resize-n" | "resize-s" | "resize-e" | "resize-w"
  //       | "resize-nw" | "resize-ne" | "resize-sw" | "resize-se"
  let _drag = null;

  const HANDLE_SIZE = 8;  // half-size of corner/edge handles
  const MIN_W = 50;
  const MIN_H = 20;

  // ── Public API ─────────────────────────────────────────────────────────────

  window.openRectCropModal = function(dataUri, previewId, settingKey) {
    _rPreviewId = previewId;
    _rSettingKey = settingKey;

    // Build modal if it doesn't exist yet
    let overlay = document.getElementById("rect-crop-modal-overlay");
    if (!overlay) {
      overlay = _buildRectCropModal();
      document.body.appendChild(overlay);
    }

    const container = document.getElementById("rect-crop-container");
    container.innerHTML = "";

    _rImg = new Image();
    _rImg.alt = "Signature image to crop";
    _rImg.style.cssText = "display:block; max-width:100%; max-height:400px; pointer-events:none; user-select:none;";

    _rImg.onload = function() {
      const dispW = _rImg.offsetWidth;
      const dispH = _rImg.offsetHeight;

      _rCanvas = document.createElement("canvas");
      _rCanvas.className = "rect-crop-overlay-canvas";
      _rCanvas.width = dispW;
      _rCanvas.height = dispH;
      _rCanvas.style.cssText = "position:absolute; top:0; left:0; pointer-events:none;";
      container.appendChild(_rCanvas);
      _rCtx = _rCanvas.getContext("2d");

      // Initial rectangle: wide signature-like aspect ratio (3:1), centred
      const initW = Math.max(MIN_W, Math.min(Math.round(dispW * 0.8), dispW));
      const initH = Math.max(MIN_H, Math.min(Math.round(initW / 3), dispH));
      _rect = {
        x: Math.round((dispW - initW) / 2),
        y: Math.round((dispH - initH) / 2),
        w: initW,
        h: initH
      };

      _drawRectOverlay();

      const ro = new ResizeObserver(() => _onRectResize());
      ro.observe(container);
      container._rectRO = ro;
    };

    _rImg.src = dataUri;
    container.appendChild(_rImg);

    container.addEventListener("mousedown", _onRectMouseDown);
    container.addEventListener("mousemove", _onRectMouseMove);
    container.addEventListener("mouseup", _onRectMouseUp);
    container.addEventListener("mouseleave", _onRectMouseUp);

    overlay.classList.add("open");
  };

  window.closeRectCropModal = function() {
    const overlay = document.getElementById("rect-crop-modal-overlay");
    if (!overlay) return;
    overlay.classList.remove("open");

    const container = document.getElementById("rect-crop-container");
    if (container) {
      container.removeEventListener("mousedown", _onRectMouseDown);
      container.removeEventListener("mousemove", _onRectMouseMove);
      container.removeEventListener("mouseup", _onRectMouseUp);
      container.removeEventListener("mouseleave", _onRectMouseUp);
      if (container._rectRO) {
        container._rectRO.disconnect();
        container._rectRO = null;
      }
    }
    _drag = null;
    // Reset file input so the same file can be re-selected
    const inputId = _rPreviewId ? _rPreviewId.replace("preview", "input") : null;
    if (inputId) {
      const el = document.getElementById(inputId);
      if (el) el.value = "";
    }
  };

  window.applyRectCrop = function() {
    if (!_rImg || !_rCanvas) return;

    const dispW = _rCanvas.width;
    const dispH = _rCanvas.height;
    const natW = _rImg.naturalWidth;
    const natH = _rImg.naturalHeight;

    // Scale factors from display coords to natural image coords
    const scaleX = natW / dispW;
    const scaleY = natH / dispH;

    const natX = Math.round(_rect.x * scaleX);
    const natY = Math.round(_rect.y * scaleY);
    const natW2 = Math.round(_rect.w * scaleX);
    const natH2 = Math.round(_rect.h * scaleY);

    const offscreen = document.createElement("canvas");
    offscreen.width = natW2;
    offscreen.height = natH2;
    const ctx = offscreen.getContext("2d");

    ctx.drawImage(_rImg, natX, natY, natW2, natH2, 0, 0, natW2, natH2);

    const resultUri = offscreen.toDataURL("image/png");

    // Update preview and stored value
    const preview = document.getElementById(_rPreviewId);
    preview.src = resultUri;
    preview.style.display = "block";
    document.getElementById(_rPreviewId.replace("preview", "remove")).style.display = "";
    _stored[_rSettingKey] = resultUri;

    closeRectCropModal();
  };

  // ── Build DOM ──────────────────────────────────────────────────────────────

  function _buildRectCropModal() {
    const overlay = document.createElement("div");
    overlay.id = "rect-crop-modal-overlay";
    overlay.className = "rect-crop-modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-labelledby", "rect-crop-modal-title");

    overlay.innerHTML = `
      <div class="rect-crop-modal">
        <p class="rect-crop-modal-title" id="rect-crop-modal-title">Crop Signature</p>
        <p class="rect-crop-modal-hint">Drag to reposition. Drag edges or corners to resize.</p>
        <div id="rect-crop-container" class="rect-crop-container" style="cursor:move;"></div>
        <div class="rect-crop-modal-footer">
          <button type="button" class="btn btn-secondary" onclick="closeRectCropModal()">Cancel</button>
          <button type="button" class="btn btn-primary" onclick="applyRectCrop()">Crop</button>
        </div>
      </div>
    `;

    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) closeRectCropModal();
    });

    return overlay;
  }

  // ── Drawing ────────────────────────────────────────────────────────────────

  function _drawRectOverlay() {
    if (!_rCtx || !_rCanvas) return;
    const w = _rCanvas.width;
    const h = _rCanvas.height;
    const { x, y, w: rw, h: rh } = _rect;

    _rCtx.clearRect(0, 0, w, h);

    // Dark overlay outside rectangle
    _rCtx.save();
    _rCtx.fillStyle = "rgba(0,0,0,0.55)";
    _rCtx.fillRect(0, 0, w, h);
    _rCtx.globalCompositeOperation = "destination-out";
    _rCtx.fillRect(x, y, rw, rh);
    _rCtx.restore();

    // Rectangle border
    _rCtx.save();
    _rCtx.strokeStyle = "#4f46e5";
    _rCtx.lineWidth = 2;
    _rCtx.strokeRect(x, y, rw, rh);
    _rCtx.restore();

    // Corner and edge handles
    _rCtx.save();
    _rCtx.fillStyle = "#4f46e5";
    const hs = HANDLE_SIZE;
    const cx = x + rw / 2;
    const cy = y + rh / 2;
    // Corners
    _rCtx.fillRect(x - hs,       y - hs,       hs * 2, hs * 2); // nw
    _rCtx.fillRect(x + rw - hs,  y - hs,       hs * 2, hs * 2); // ne
    _rCtx.fillRect(x - hs,       y + rh - hs,  hs * 2, hs * 2); // sw
    _rCtx.fillRect(x + rw - hs,  y + rh - hs,  hs * 2, hs * 2); // se
    // Edge midpoints
    _rCtx.fillRect(cx - hs,      y - hs,       hs * 2, hs * 2); // n
    _rCtx.fillRect(cx - hs,      y + rh - hs,  hs * 2, hs * 2); // s
    _rCtx.fillRect(x - hs,       cy - hs,      hs * 2, hs * 2); // w
    _rCtx.fillRect(x + rw - hs,  cy - hs,      hs * 2, hs * 2); // e
    _rCtx.restore();
  }

  // ── Resize observer ────────────────────────────────────────────────────────

  function _onRectResize() {
    if (!_rImg || !_rCanvas) return;
    const newW = _rImg.offsetWidth;
    const newH = _rImg.offsetHeight;
    if (newW === _rCanvas.width && newH === _rCanvas.height) return;
    const sx = newW / _rCanvas.width;
    const sy = newH / _rCanvas.height;
    _rect.x = Math.round(_rect.x * sx);
    _rect.y = Math.round(_rect.y * sy);
    _rect.w = Math.round(_rect.w * sx);
    _rect.h = Math.round(_rect.h * sy);
    _rCanvas.width = newW;
    _rCanvas.height = newH;
    _clampRect();
    _drawRectOverlay();
  }

  // ── Pointer helpers ────────────────────────────────────────────────────────

  function _canvasXY(e) {
    const rect = _rCanvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  // Returns the resize/move type for a given pointer position, or null
  function _hitTest(px, py) {
    const { x, y, w: rw, h: rh } = _rect;
    const hs = HANDLE_SIZE + 2; // slightly larger hit area
    const cx = x + rw / 2;
    const cy = y + rh / 2;

    // Corners (checked first — they take priority over edges)
    if (Math.abs(px - x)      <= hs && Math.abs(py - y)      <= hs) return "resize-nw";
    if (Math.abs(px - (x+rw)) <= hs && Math.abs(py - y)      <= hs) return "resize-ne";
    if (Math.abs(px - x)      <= hs && Math.abs(py - (y+rh)) <= hs) return "resize-sw";
    if (Math.abs(px - (x+rw)) <= hs && Math.abs(py - (y+rh)) <= hs) return "resize-se";
    // Edges
    if (Math.abs(py - y)      <= hs && px >= x && px <= x + rw) return "resize-n";
    if (Math.abs(py - (y+rh)) <= hs && px >= x && px <= x + rw) return "resize-s";
    if (Math.abs(px - x)      <= hs && py >= y && py <= y + rh) return "resize-w";
    if (Math.abs(px - (x+rw)) <= hs && py >= y && py <= y + rh) return "resize-e";
    // Interior
    if (px >= x && px <= x + rw && py >= y && py <= y + rh) return "move";
    return null;
  }

  function _clampRect() {
    const cw = _rCanvas.width;
    const ch = _rCanvas.height;
    _rect.w = Math.max(MIN_W, Math.min(_rect.w, cw));
    _rect.h = Math.max(MIN_H, Math.min(_rect.h, ch));
    _rect.x = Math.max(0, Math.min(_rect.x, cw - _rect.w));
    _rect.y = Math.max(0, Math.min(_rect.y, ch - _rect.h));
  }

  function _onRectMouseDown(e) {
    if (!_rCanvas) return;
    e.preventDefault();
    const { x, y } = _canvasXY(e);
    const type = _hitTest(x, y);
    if (!type) return;
    _drag = { type, startX: x, startY: y, startRect: { ..._rect } };
  }

  function _onRectMouseMove(e) {
    if (!_rCanvas) return;

    // Update cursor
    if (!_drag) {
      const { x, y } = _canvasXY(e);
      const type = _hitTest(x, y);
      const cursorMap = {
        "move": "move",
        "resize-n": "n-resize", "resize-s": "s-resize",
        "resize-e": "e-resize", "resize-w": "w-resize",
        "resize-nw": "nw-resize", "resize-ne": "ne-resize",
        "resize-sw": "sw-resize", "resize-se": "se-resize"
      };
      const container = document.getElementById("rect-crop-container");
      if (container) container.style.cursor = type ? (cursorMap[type] || "default") : "default";
      return;
    }

    e.preventDefault();
    const { x, y } = _canvasXY(e);
    const dx = x - _drag.startX;
    const dy = y - _drag.startY;
    const sr = _drag.startRect;

    if (_drag.type === "move") {
      _rect.x = sr.x + dx;
      _rect.y = sr.y + dy;
    } else {
      // Resize: compute new rect from start rect + delta
      let nx = sr.x, ny = sr.y, nw = sr.w, nh = sr.h;
      const t = _drag.type;
      if (t.includes("n")) { ny = sr.y + dy; nh = sr.h - dy; }
      if (t.includes("s")) { nh = sr.h + dy; }
      if (t.includes("w")) { nx = sr.x + dx; nw = sr.w - dx; }
      if (t.includes("e")) { nw = sr.w + dx; }
      // Enforce minimums (prevent inversion)
      if (nw < MIN_W) { if (t.includes("w")) { nx = sr.x + sr.w - MIN_W; } nw = MIN_W; }
      if (nh < MIN_H) { if (t.includes("n")) { ny = sr.y + sr.h - MIN_H; } nh = MIN_H; }
      _rect = { x: nx, y: ny, w: nw, h: nh };
    }
    _clampRect();
    _drawRectOverlay();
  }

  function _onRectMouseUp(e) {
    _drag = null;
  }
})();

function removeImage(previewId, settingKey) {
  const preview = document.getElementById(previewId);
  preview.src = "";
  preview.style.display = "none";
  document.getElementById(previewId.replace("preview", "remove")).style.display = "none";
  _stored[settingKey] = "";
  // Also clear the file input
  const inputId = previewId.replace("preview", "input");
  document.getElementById(inputId).value = "";
}

function loadPersonalInfo() {
  document.getElementById("personal-full-name").value = _stored.personal_full_name || "";
  document.getElementById("personal-email").value = _stored.personal_email || "";
  document.getElementById("personal-phone").value = _stored.personal_phone || "";
  document.getElementById("personal-website").value = _stored.personal_website || "";
  document.getElementById("personal-address").value = _stored.personal_address || "";
  // Load photo
  if (_stored.personal_photo) {
    document.getElementById("personal-photo-preview").src = _stored.personal_photo;
    document.getElementById("personal-photo-preview").style.display = "block";
    document.getElementById("personal-photo-remove").style.display = "";
  } else {
    document.getElementById("personal-photo-preview").style.display = "none";
    document.getElementById("personal-photo-remove").style.display = "none";
  }
  // Load signature
  if (_stored.personal_signature) {
    document.getElementById("personal-signature-preview").src = _stored.personal_signature;
    document.getElementById("personal-signature-preview").style.display = "block";
    document.getElementById("personal-signature-remove").style.display = "";
  } else {
    document.getElementById("personal-signature-preview").style.display = "none";
    document.getElementById("personal-signature-remove").style.display = "none";
  }
}

async function savePersonalInfo() {
  const msg = document.getElementById("personal-info-msg");
  msg.textContent = "";
  msg.className = "status-msg";
  const body = {
    personal_full_name: document.getElementById("personal-full-name").value.trim(),
    personal_email: document.getElementById("personal-email").value.trim(),
    personal_phone: document.getElementById("personal-phone").value.trim(),
    personal_website: document.getElementById("personal-website").value.trim(),
    personal_address: document.getElementById("personal-address").value.trim(),
    personal_photo: _stored.personal_photo || "",
    personal_signature: _stored.personal_signature || "",
  };
  try {
    await apiFetch("POST", "/settings", body);
    Object.assign(_stored, body);
    msg.textContent = "Saved";
    msg.className = "status-msg success";
    setTimeout(() => { msg.textContent = ""; }, 3000);
  } catch (e) {
    msg.textContent = "Failed to save";
    msg.className = "status-msg error";
  }
}

// Settings navigation
async function switchToSettings() {
  document.getElementById("dashboard-view").style.display = "none";
  document.getElementById("detail-view").style.display = "none";
  document.getElementById("settings-view").style.display = "flex";
  await loadAiSettings();
  loadPersonalInfo();
  await loadKbSettings();
  loadGmailSettings();
  await loadPromptSettings();
}

function switchToDashboard() {
  document.getElementById("settings-view").style.display = "none";
  document.getElementById("detail-view").style.display = "none";
  document.getElementById("dashboard-view").style.display = "block";
  currentDetailId = null;
  loadApplications();
}

function switchSettingsSection(section) {
  // Hide all sections
  document.querySelectorAll(".settings-section").forEach(el => {
    el.classList.remove("active");
  });
  // Hide all menu buttons
  document.querySelectorAll(".sidebar-menu-btn").forEach(el => {
    el.classList.remove("active");
  });
  
  // Show selected section and highlight button
  document.getElementById("section-" + section).classList.add("active");
  document.querySelector('[data-section="' + section + '"]').classList.add("active");
}

// Header back to dashboard
document.addEventListener("DOMContentLoaded", function() {
  const titleSection = document.querySelector("header .title-section");
  titleSection.style.cursor = "pointer";
  titleSection.onclick = switchToDashboard;
  
  // Handle URL parameters for OAuth callback
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  const section = params.get("section");
  if (view === "settings" && section === "gmail") {
    switchToSettings();
    switchSettingsSection("gmail");
  }
});

// Health check
async function checkKbConnection() {
  const jamDot = document.getElementById("jam-dot");
  const jamText = document.getElementById("jam-status-text");
  const jamSettingsDot = document.getElementById("jam-settings-dot");
  const jamSettingsDisplay = document.getElementById("jam-settings-display");
  const kbDot = document.getElementById("kb-dot");
  const kbText = document.getElementById("kb-status-text");
  const kbSettingsDot = document.getElementById("kb-settings-dot");
  const kbSettingsDisplay = document.getElementById("kb-settings-display");

  try {
    const resp = await apiFetch("GET", "/health");
    const data = await resp.json();

    // jam is always ok if we get a response
    jamDot.className = "connection-dot connected";
    jamText.textContent = "jam";
    if (jamSettingsDot) jamSettingsDot.className = "connection-dot connected";
    if (jamSettingsDisplay) jamSettingsDisplay.textContent = "Connected";

    // kb status from response
    if (data.kb_status === "ok") {
      kbDot.className = "connection-dot connected";
      kbText.textContent = "kb";
      if (kbSettingsDot) kbSettingsDot.className = "connection-dot connected";
      if (kbSettingsDisplay) kbSettingsDisplay.textContent = "Connected";
    } else {
      kbDot.className = "connection-dot disconnected";
      kbText.textContent = "kb";
      if (kbSettingsDot) kbSettingsDot.className = "connection-dot disconnected";
      if (kbSettingsDisplay) kbSettingsDisplay.textContent = "Unreachable";
    }
  } catch (e) {
    // jam itself is down
    jamDot.className = "connection-dot disconnected";
    jamText.textContent = "jam";
    if (jamSettingsDot) jamSettingsDot.className = "connection-dot disconnected";
    if (jamSettingsDisplay) jamSettingsDisplay.textContent = "Disconnected";

    kbDot.className = "connection-dot disconnected";
    kbText.textContent = "kb";
    if (kbSettingsDot) kbSettingsDot.className = "connection-dot disconnected";
    if (kbSettingsDisplay) kbSettingsDisplay.textContent = "Unknown";
  }
}

// ── AI Models settings ──────────────────────────────────────────────────────
let _catalog = null;
let _stored = {};

async function loadAiSettings() {
  try {
    const [catResp, setResp] = await Promise.all([
      apiFetch("GET", "/catalog"),
      apiFetch("GET", "/settings"),
    ]);
    _catalog = await catResp.json();
    _stored = await setResp.json();
    renderProviderDropdown();
    renderStepModelOverrides();
    await loadTemplateSettings();
  } catch (e) {
    console.error("Failed to load AI settings:", e);
  }
}

var _suppressAutoSave = false;

function renderProviderDropdown() {
  const sel = document.getElementById("ai-provider");
  sel.innerHTML = "";
  if (!_catalog) return;
  const current = _stored.llm_provider || (_catalog.providers[0] && _catalog.providers[0].id) || "openai";
  _catalog.providers.forEach(function(p) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.label;
    if (p.id === current) opt.selected = true;
    sel.appendChild(opt);
  });
  _suppressAutoSave = true;
  onProviderChange();
  _suppressAutoSave = false;
}

function _providerById(id) {
  if (!_catalog) return null;
  return _catalog.providers.find(function(p) { return p.id === id; }) || null;
}

// ── Per-step model overrides ────────────────────────────────────────────────

const _STEP_MODEL_META = [
  {key: "generate_or_revise", label: "Generate / Revise"},
  {key: "analyze_fit",        label: "Analyze Fit"},
  {key: "analyze_quality",    label: "Analyze Quality"},
  {key: "apply_suggestions",  label: "Apply Suggestions"},
  {key: "reduce_size",        label: "Reduce Size"},
];

function renderStepModelOverrides() {
  const container = document.getElementById("step-model-overrides");
  if (!container) return;
  container.innerHTML = "";
  if (!_catalog) return;

  _STEP_MODEL_META.forEach(function(step) {
    const settingKey = "step_model_" + step.key;

    const row = document.createElement("div");
    row.style.cssText = "display:flex; align-items:center; gap:12px; margin-bottom:10px;";

    const lbl = document.createElement("span");
    lbl.textContent = step.label;
    lbl.style.cssText = "flex:0 0 160px; font-size:0.85rem; color:var(--text-secondary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;";
    row.appendChild(lbl);

    const sel = document.createElement("select");
    sel.className = "field-input";
    sel.style.cssText = "flex:1; font-size:0.85rem; padding:5px 10px;";
    sel.setAttribute("aria-label", step.label + " model override");

    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = "Use global default";
    sel.appendChild(defaultOpt);

    _catalog.providers.forEach(function(prov) {
      if (!prov.llm_models || prov.llm_models.length === 0) return;
      const grp = document.createElement("optgroup");
      grp.label = prov.label;
      prov.llm_models.forEach(function(m) {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = m.label;
        grp.appendChild(opt);
      });
      sel.appendChild(grp);
    });

    sel.value = _stored[settingKey] || "";

    sel.onchange = async function() {
      const val = sel.value;
      try {
        await apiFetch("POST", "/settings", {[settingKey]: val});
        _stored[settingKey] = val;
        const msgEl = document.getElementById("ai-settings-msg");
        msgEl.textContent = step.label + " model saved";
        msgEl.className = "status-msg success";
        msgEl.style.display = "block";
        setTimeout(function() {
          if (msgEl.textContent === step.label + " model saved") msgEl.style.display = "none";
        }, 2000);
      } catch (e) {
        const msgEl = document.getElementById("ai-settings-msg");
        msgEl.textContent = "Save failed: " + e.message;
        msgEl.className = "status-msg error";
        msgEl.style.display = "block";
      }
    };

    row.appendChild(sel);
    container.appendChild(row);
  });
}

function _providerHasKey(id) {
  if (id === "ollama") return true;
  return !!_stored[id + "_api_key_set"];
}

var _autoSaveTimer = null;

function _autoSaveProviderModel() {
  if (_suppressAutoSave) return;
  // Debounce: wait 400ms after last change before saving
  if (_autoSaveTimer) clearTimeout(_autoSaveTimer);
  _autoSaveTimer = setTimeout(async function() {
    var pid = document.getElementById("ai-provider").value;
    var model = document.getElementById("ai-model").value;
    if (!pid || !model) return;
    try {
      await apiFetch("POST", "/settings", { llm_provider: pid, llm_model: model });
      _stored.llm_provider = pid;
      _stored.llm_model = model;
      var msgEl = document.getElementById("ai-settings-msg");
      msgEl.textContent = "Provider & model saved";
      msgEl.className = "status-msg success";
      msgEl.style.display = "block";
      setTimeout(function() { if (msgEl.textContent === "Provider & model saved") msgEl.style.display = "none"; }, 2000);
    } catch (e) {
      var msgEl = document.getElementById("ai-settings-msg");
      msgEl.textContent = "Auto-save failed: " + e.message;
      msgEl.className = "status-msg error";
      msgEl.style.display = "block";
    }
  }, 400);
}

function onProviderChange() {
  const pid = document.getElementById("ai-provider").value;
  const prov = _providerById(pid);
  if (!prov) return;

  // Warning
  const warn = document.getElementById("ai-key-warning");
  if (!_providerHasKey(pid)) {
    warn.textContent = "No API key configured for " + prov.label;
    warn.style.display = "block";
  } else {
    warn.style.display = "none";
  }

  // Models
  const modelSel = document.getElementById("ai-model");
  modelSel.innerHTML = "";
  const currentModel = _stored.llm_model || "";
  prov.llm_models.forEach(function(m) {
    const opt = document.createElement("option");
    opt.value = m.model_id;
    opt.textContent = m.label;
    if (m.model_id === currentModel) opt.selected = true;
    modelSel.appendChild(opt);
  });

  // Credential fields
  renderCredentialFields(prov);

  // Auto-save provider+model when user changes provider
  _autoSaveProviderModel();
}

function renderCredentialFields(prov) {
  const container = document.getElementById("ai-credentials");
  container.innerHTML = "";
  prov.fields.forEach(function(f) {
    const group = document.createElement("div");
    group.className = "setting-group";

    const label = document.createElement("label");
    label.className = "setting-group-label";
    label.textContent = f.label;
    group.appendChild(label);

    const wrapper = document.createElement("div");
    wrapper.style.position = "relative";

    const input = document.createElement("input");
    input.type = f.input_type === "password" ? "password" : f.input_type;
    input.className = "field-input";
    input.id = "cred-" + f.key;
    input.placeholder = f.placeholder || "";
    if (f.input_type === "password" && _stored[prov.id + "_api_key_set"]) {
      input.placeholder = "saved — leave blank to keep";
    }
    wrapper.appendChild(input);

    if (f.input_type === "password") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.textContent = "show";
      toggle.style.cssText = "position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;color:#6b7280;cursor:pointer;font-size:0.75rem;";
      toggle.onclick = function() {
        if (input.type === "password") { input.type = "text"; toggle.textContent = "hide"; }
        else { input.type = "password"; toggle.textContent = "show"; }
      };
      wrapper.appendChild(toggle);
    }

    group.appendChild(wrapper);
    container.appendChild(group);
  });
}

async function saveAiSettings() {
  const msgEl = document.getElementById("ai-settings-msg");
  msgEl.textContent = "Saving...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";

  const pid = document.getElementById("ai-provider").value;
  const model = document.getElementById("ai-model").value;
  const prov = _providerById(pid);

  const body = { llm_provider: pid, llm_model: model };

  if (prov) {
    prov.fields.forEach(function(f) {
      const input = document.getElementById("cred-" + f.key);
      if (input && input.value.trim()) {
        body[f.key] = input.value.trim();
      }
    });
  }

  try {
    await apiFetch("POST", "/settings", body);
    msgEl.textContent = "Settings saved successfully";
    msgEl.className = "status-msg success";
    await loadAiSettings();
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

// ── Template settings ──────────────────────────────────────────────────────

async function loadTemplateSettings() {
  if (Object.keys(_stored).length === 0) return;
  var cvEl = document.getElementById("template-cv");
  var clEl = document.getElementById("template-cover-letter");
  var cvVal = _stored.cv_latex_template ? _stored.cv_latex_template : "";
  var clVal = _stored.cover_letter_latex_template ? _stored.cover_letter_latex_template : "";
  if (!cvVal || !clVal) {
    try {
      var tplResp = await apiFetch("GET", "/templates/defaults");
      var defaults = await tplResp.json();
      if (!cvVal) cvVal = defaults.cv || "";
      if (!clVal) clVal = defaults.cover_letter || "";
    } catch (e) {
      console.error("Failed to load default templates:", e);
    }
  }
  cvEl.value = cvVal;
  clEl.value = clVal;
}

async function saveTemplateSettings() {
  var msgEl = document.getElementById("template-settings-msg");
  msgEl.textContent = "Saving...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";

  var cvRaw = document.getElementById("template-cv").value.trim();
  var clRaw = document.getElementById("template-cover-letter").value.trim();
  if (!cvRaw && !clRaw) {
    msgEl.textContent = "Nothing to save — both templates are empty.";
    msgEl.className = "status-msg error";
    return;
  }

  var body = {};
  if (cvRaw) body.cv_latex_template = cvRaw;
  if (clRaw) body.cover_letter_latex_template = clRaw;

  try {
    await apiFetch("POST", "/settings", body);
    msgEl.textContent = "Templates saved successfully";
    msgEl.className = "status-msg success";
    if (cvRaw) _stored.cv_latex_template = cvRaw;
    if (clRaw) _stored.cover_letter_latex_template = clRaw;
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

// ── System Prompt settings ──────────────────────────────────────────────────
let _promptDefaults = null;

const _promptKeys = [
  "prompt_generate_first", "prompt_generate_revise",
  "prompt_analyze_fit", "prompt_analyze_quality",
  "prompt_apply_suggestions", "prompt_reduce_size"
];

function _promptElId(key) {
  return key.replace(/_/g, "-");  // prompt_generate_first -> prompt-generate-first
}

async function loadPromptDefaults() {
  if (_promptDefaults) return _promptDefaults;
  try {
    var resp = await apiFetch("GET", "/prompts/defaults");
    _promptDefaults = await resp.json();
  } catch (e) {
    console.error("Failed to load prompt defaults:", e);
    _promptDefaults = {};
  }
  return _promptDefaults;
}

async function loadPromptSettings() {
  var defaults = await loadPromptDefaults();
  for (var key of _promptKeys) {
    var el = document.getElementById(_promptElId(key));
    if (!el) continue;
    // Use stored value if set, otherwise use default
    el.value = _stored[key] || defaults[key] || "";
  }
}

async function savePromptSettings() {
  var msgEl = document.getElementById("prompt-settings-msg");
  msgEl.textContent = "Saving...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";

  var body = {};
  var defaults = await loadPromptDefaults();
  for (var key of _promptKeys) {
    var el = document.getElementById(_promptElId(key));
    if (!el) continue;
    var val = el.value.trim();
    // Only save if different from default (save empty string to clear custom prompt)
    if (val && val !== (defaults[key] || "").trim()) {
      body[key] = val;
    }
  }

  if (Object.keys(body).length === 0) {
    msgEl.textContent = "No changes to save \u2014 all prompts match defaults.";
    msgEl.className = "status-msg";
    return;
  }

  try {
    await apiFetch("POST", "/settings", body);
    msgEl.textContent = "Prompts saved successfully";
    msgEl.className = "status-msg success";
    for (var k in body) _stored[k] = body[k];
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

async function resetPrompt(key) {
  var defaults = await loadPromptDefaults();
  var el = document.getElementById(_promptElId(key));
  if (el && defaults[key]) {
    el.value = defaults[key];
  }
}

// ── Knowledge Base settings ──────────────────────────────────────────────────

let _kbNamespaces = [];

async function loadKbSettings() {
  // Get saved settings and populate numeric fields immediately (synchronous, no await)
  var saved = _stored || {};
  var searchNs = [];
  var includeNs = [];
  try { searchNs = JSON.parse(saved.kb_retrieval_namespaces || "[]"); } catch(e) {}
  try { includeNs = JSON.parse(saved.kb_include_namespaces || "[]"); } catch(e) {}

  var nResults = saved.kb_retrieval_n_results != null ? parseInt(saved.kb_retrieval_n_results) : 5;
  if (isNaN(nResults)) nResults = 5;
  var padding = saved.kb_retrieval_padding != null ? parseInt(saved.kb_retrieval_padding) : 0;
  if (isNaN(padding)) padding = 0;
  document.getElementById("kb-n-results").value = nResults;
  document.getElementById("kb-padding").value = padding;

  // Fetch namespaces from KB (may be slow or fail, independent of numeric fields)
  try {
    var nsResp = await apiFetch("GET", "/kb/namespaces");
    _kbNamespaces = await nsResp.json();
  } catch (e) {
    _kbNamespaces = [];
  }

  // Populate search namespaces checkboxes
  var searchDiv = document.getElementById("kb-search-namespaces");
  searchDiv.innerHTML = "";
  if (_kbNamespaces.length === 0) {
    searchDiv.innerHTML = '<span style="color:#9ca3af; font-size:0.85rem;">No namespaces found \u2014 is the knowledge base running?</span>';
  } else {
    _kbNamespaces.forEach(function(ns) {
      var id = ns.id || ns;
      var label = ns.label || ns.id || ns;
      var checked = searchNs.indexOf(id) !== -1;
      var row = document.createElement("label");
      row.style.cssText = "display:flex; align-items:center; gap:8px; cursor:pointer; font-size:0.9rem; color:#1a1a2e;";
      row.innerHTML = '<input type="checkbox" value="' + escapeHtml(id) + '"' + (checked ? ' checked' : '') + ' style="accent-color:#4f46e5;"> ' + escapeHtml(label);
      searchDiv.appendChild(row);
    });
  }

  // Populate include namespaces checkboxes
  var includeDiv = document.getElementById("kb-include-namespaces");
  includeDiv.innerHTML = "";
  if (_kbNamespaces.length === 0) {
    includeDiv.innerHTML = '<span style="color:#9ca3af; font-size:0.85rem;">No namespaces found \u2014 is the knowledge base running?</span>';
  } else {
    _kbNamespaces.forEach(function(ns) {
      var id = ns.id || ns;
      var label = ns.label || ns.id || ns;
      var checked = includeNs.indexOf(id) !== -1;
      var row = document.createElement("label");
      row.style.cssText = "display:flex; align-items:center; gap:8px; cursor:pointer; font-size:0.9rem; color:#1a1a2e;";
      row.innerHTML = '<input type="checkbox" value="' + escapeHtml(id) + '"' + (checked ? ' checked' : '') + ' style="accent-color:#4f46e5;"> ' + escapeHtml(label);
      includeDiv.appendChild(row);
    });
  }
}

async function saveKbSettings() {
  var msgEl = document.getElementById("kb-settings-msg");
  msgEl.textContent = "Saving...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";

  // Collect checked search namespaces
  var searchNs = [];
  document.querySelectorAll("#kb-search-namespaces input[type=checkbox]:checked").forEach(function(cb) {
    searchNs.push(cb.value);
  });

  // Collect checked include namespaces
  var includeNs = [];
  document.querySelectorAll("#kb-include-namespaces input[type=checkbox]:checked").forEach(function(cb) {
    includeNs.push(cb.value);
  });

  var nResults = parseInt(document.getElementById("kb-n-results").value);
  if (isNaN(nResults)) nResults = 5;
  var padding = parseInt(document.getElementById("kb-padding").value);
  if (isNaN(padding)) padding = 0;

  var body = {
    kb_retrieval_namespaces: JSON.stringify(searchNs),
    kb_retrieval_n_results: nResults,
    kb_retrieval_padding: padding,
    kb_include_namespaces: JSON.stringify(includeNs)
  };

  try {
    await apiFetch("POST", "/settings", body);
    msgEl.textContent = "Knowledge Base settings saved successfully";
    msgEl.className = "status-msg success";
    // Update local cache
    _stored.kb_retrieval_namespaces = body.kb_retrieval_namespaces;
    _stored.kb_retrieval_n_results = String(nResults);
    _stored.kb_retrieval_padding = String(padding);
    _stored.kb_include_namespaces = body.kb_include_namespaces;
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

async function testKbRetrieval() {
  var msgEl = document.getElementById("kb-settings-msg");
  msgEl.textContent = "Testing KB retrieval...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";

  // Collect checked include namespaces
  var includeNs = [];
  var checkboxes = document.querySelectorAll("#kb-include-namespaces input[type='checkbox']:checked");
  checkboxes.forEach(function(cb) {
    includeNs.push(cb.value);
  });

  if (includeNs.length === 0) {
    msgEl.textContent = "Error: No include namespaces selected. Select at least one.";
    msgEl.className = "status-msg error";
    return;
  }

  try {
    const resp = await apiFetch("POST", "/kb/test-retrieval", {
      namespace_ids: includeNs,
      query: "test"
    });
    const result = await resp.json();

    var lines = ["=== Test Results ==="];
    var hasError = false;

    if (result.search_error) {
      lines.push("Semantic Search: ERROR - " + result.search_error);
      hasError = true;
    } else if (result.search_results) {
      lines.push("Semantic Search: OK - " + result.search_results.length + " chunks matched");
    }

    if (result.namespace_summaries) {
      lines.push("");
      lines.push("=== Full-include Namespaces ===");
      result.namespace_summaries.forEach(function(ns) {
        var docs = ns.documents || [];
        var totalChunks = docs.reduce(function(sum, d) { return sum + d.chunks; }, 0);
        lines.push("");
        lines.push("[" + ns.namespace_id + "] " + docs.length + " document" + (docs.length !== 1 ? "s" : "") + ", " + totalChunks + " chunk" + (totalChunks !== 1 ? "s" : ""));
        if (ns.error) {
          lines.push("  ERROR: " + ns.error);
          hasError = true;
        } else if (docs.length === 0) {
          lines.push("  WARNING: Namespace is empty. Import content to the KB first.");
          hasError = true;
        } else {
          docs.forEach(function(d) {
            lines.push("  - " + d.file_name + " (" + d.chunks + " chunk" + (d.chunks !== 1 ? "s" : "") + ")");
          });
        }
      });
    }

    var msg = lines.join(String.fromCharCode(10));

    msgEl.textContent = msg;
    msgEl.className = hasError ? "status-msg error" : "status-msg success";
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

async function loadGmailSettings() {
  try {
    // Load status
    const statusResp = await apiFetch("GET", "/gmail/status");
    const status = await statusResp.json();

    // Update status display
    const dotEl = document.getElementById("gmail-status-dot");
    const textEl = document.getElementById("gmail-status-text");
    const disconnectBtn = document.getElementById("gmail-disconnect-btn");

    if (status.connected) {
      dotEl.className = "connection-dot connected";
      textEl.textContent = "Connected as " + status.email;
      disconnectBtn.style.display = "inline-block";
    } else {
      dotEl.className = "connection-dot disconnected";
      textEl.textContent = "Not connected";
      disconnectBtn.style.display = "none";
    }

    // Load stored settings
    const settingsResp = await apiFetch("GET", "/settings");
    const settings = await settingsResp.json();
    document.getElementById("gmail-client-id").value = settings.gmail_client_id || "";
    // client_secret never returned, just show placeholder
    document.getElementById("gmail-client-secret").value = "";
  } catch (e) {
    console.error("Failed to load Gmail settings:", e);
  }
}

async function saveGmailCredentials() {
  const clientId = document.getElementById("gmail-client-id").value.trim();
  const clientSecret = document.getElementById("gmail-client-secret").value.trim();
  const msgEl = document.getElementById("gmail-settings-msg");
  
  if (!clientId) {
    msgEl.textContent = "Client ID is required";
    msgEl.className = "status-msg error";
    msgEl.style.display = "block";
    return;
  }
  
  msgEl.textContent = "Saving...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";
  
  try {
    const body = { gmail_client_id: clientId };
    if (clientSecret) body.gmail_client_secret = clientSecret;
    await apiFetch("POST", "/settings", body);
    msgEl.textContent = "Credentials saved successfully";
    msgEl.className = "status-msg success";
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

async function connectGmail() {
  const msgEl = document.getElementById("gmail-settings-msg");
  msgEl.textContent = "Opening authorization window...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";
  
  try {
    const resp = await apiFetch("GET", "/gmail/auth-url");
    const data = await resp.json();
    
    msgEl.textContent = "Complete authorization in the new tab, then return here.";
    msgEl.className = "status-msg";
    
    // Open auth URL in new tab
    window.open(data.url, "_blank", "width=500,height=600");
    
    // Poll for connection status
    let pollCount = 0;
    const maxPolls = 40; // 2 minutes with 3-second intervals
    const pollInterval = setInterval(async function() {
      pollCount++;
      try {
        const statusResp = await apiFetch("GET", "/gmail/status");
        const status = await statusResp.json();
        if (status.connected) {
          clearInterval(pollInterval);
          msgEl.textContent = "Gmail connected successfully!";
          msgEl.className = "status-msg success";
          await loadGmailSettings();
        }
      } catch (e) {
        // Polling continues
      }
      
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval);
        msgEl.textContent = "Authorization timeout. Please try again.";
        msgEl.className = "status-msg error";
      }
    }, 3000);
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}

function toggleGmailSecret(btn) {
  const input = document.getElementById("gmail-client-secret");
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "hide";
  } else {
    input.type = "password";
    btn.textContent = "show";
  }
}

async function disconnectGmail() {
  const msgEl = document.getElementById("gmail-settings-msg");
  msgEl.textContent = "Disconnecting...";
  msgEl.className = "status-msg";
  msgEl.style.display = "block";
  
  try {
    await apiFetch("POST", "/gmail/disconnect", {});
    msgEl.textContent = "Gmail disconnected";
    msgEl.className = "status-msg success";
    await loadGmailSettings();
  } catch (e) {
    msgEl.textContent = "Error: " + e.message;
    msgEl.className = "status-msg error";
  }
}


// Import from URL
async function importFromUrl() {
  const input = document.getElementById('import-url');
  const btn = document.getElementById('import-btn');
  const status = document.getElementById('import-status');
  const url = input.value.trim();
  if (!url) { status.textContent = 'Please enter a URL'; status.style.color = '#ef4444'; return; }

  btn.disabled = true;
  btn.textContent = 'Importing...';
  status.textContent = 'Fetching and analyzing...';
  status.style.color = '#6b7280';

  try {
    const res = await apiFetch('POST', '/applications/from-url', { url });
    const data = await res.json();
    status.style.color = '#10b981';
    status.textContent = data.kb_ingested ? 'Imported + added to KB' : 'Imported (KB offline)';
    input.value = '';
    await loadApplications();
  } catch (e) {
    status.style.color = '#ef4444';
    status.textContent = e.message || 'Import failed';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Import';
  }
}

// Close modal when clicking overlay
document.getElementById("app-modal").addEventListener("click", function(e) {
  if (e.target === this) {
    closeApplicationModal();
  }
});

function _togglePane(containerId, paneIndex) {
  var container = document.getElementById(containerId);
  var panes = Array.from(container.querySelectorAll(".trisplit-pane"));
  var pane = panes[paneIndex];
  pane.classList.toggle("collapsed");

  var btn = pane.querySelector(".trisplit-pane-header button");
  if (btn) {
    var idx = parseInt(pane.dataset.pane);
    if (pane.classList.contains("collapsed")) {
      btn.innerHTML = "&#x25B6;";
    } else {
      if (idx === 0)      btn.innerHTML = "&#x25C0;";
      else if (idx === 2) btn.innerHTML = "&#x25B6;";
      else                btn.innerHTML = "&#x25C0;&#x25B6;";
    }
  }
}

function _toggleTrisplitFullscreen() {
  var el = document.getElementById("step-cv-cover");
  var btn = document.getElementById("trisplit-fs-btn");
  if (!el || !btn) return;
  var isFullscreen = el.classList.toggle("trisplit-fullscreen");
  if (isFullscreen) {
    btn.innerHTML = "&#x2715; Exit Fullscreen";
    btn.title = "Exit fullscreen (Esc)";
  } else {
    btn.innerHTML = "&#x26F6; Fullscreen";
    btn.title = "Toggle fullscreen";
  }
}

// ── Document editor logic ────────────────────────────────────────────────────

var _docLists = { cv: [], cover_letter: [] };
var _currentDocId = { cv: null, cover_letter: null };
var _saveTimers = { cv: null, cover_letter: null };
var _saveRetries = { cv: 0, cover_letter: 0 };
var _docTabLoaded = { cv: false, cover_letter: false };
var _currentPdfUrl = { cv: null, cover_letter: null };
var _cmEditors = { cv: null, cover_letter: null };
var _eqLoaded = false;
var _eqSaveTimers = {};
var _ivLoaded = false;
var _ivSaveTimers = {};
var _ofLoaded = false;
var _ofSaveTimers = {};

function _downloadPdf(docType) {
  var url = _currentPdfUrl[docType];
  if (!url) return;
  var a = document.createElement("a");
  a.href = url;
  var sanitize = function(s) { return (s || "").replace(/[^\w\-]/g, "_").replace(/^_+|_+$/g, ""); };
  var fname;
  if (docType === "cv") {
    var author = sanitize(_stored.personal_full_name);
    fname = author ? "CV_" + author + ".pdf" : "CV.pdf";
  } else {
    var pos = sanitize((document.getElementById("detail-position") || {}).textContent);
    fname = pos ? "CoverLetter_" + pos + ".pdf" : "CoverLetter.pdf";
  }
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function _renderPdf(docType, url) {
  var container = document.getElementById(docType + "-preview-frame");
  container.innerHTML = '<div class="pdf-placeholder">Loading PDF\u2026</div>';
  try {
    var pdf = await pdfjsLib.getDocument(url).promise;
    container.innerHTML = "";
    for (var i = 1; i <= pdf.numPages; i++) {
      var page = await pdf.getPage(i);
      var viewport = page.getViewport({ scale: 1.5 });
      var canvas = document.createElement("canvas");
      canvas.className = "pdf-canvas-page";
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      container.appendChild(canvas);
      await page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise;
    }
  } catch (e) {
    container.innerHTML = '<div class="pdf-placeholder">Failed to load PDF</div>';
  }
}

function _showCompileOverlay(docType, show) {
  var el = document.getElementById(docType + "-compile-overlay");
  if (el) el.style.display = show ? "flex" : "none";
}

function _switchDocTab(docType) {
  document.querySelectorAll(".tab-btn-doc").forEach(function(btn) { btn.classList.remove("active"); });
  document.querySelectorAll(".doc-tab-panel").forEach(function(p) { p.classList.remove("active"); });
  document.querySelector('.tab-btn-doc[data-doctab="' + docType + '"]').classList.add("active");
  document.getElementById("doc-panel-" + docType).classList.add("active");
  if (!_docTabLoaded[docType] && currentDetailId) {
    _loadDocuments(docType);
    _docTabLoaded[docType] = true;
  }
}

async function _loadDocuments(docType) {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("GET", "/applications/" + currentDetailId + "/documents?doc_type=" + docType);
    var docs = await resp.json();
    _docLists[docType] = docs;
    var sel = document.getElementById(docType + "-doc-select");
    sel.innerHTML = "";
    if (docs.length === 0) {
      sel.innerHTML = '<option value="">-- no documents --</option>';
      _currentDocId[docType] = null;
      _clearEditor(docType);
      return;
    }
    docs.forEach(function(doc) {
      var opt = document.createElement("option");
      opt.value = doc.id;
      opt.textContent = doc.title;
      sel.appendChild(opt);
    });
    sel.value = docs[0].id;
    _currentDocId[docType] = docs[0].id;
    _loadDocIntoEditor(docType, docs[0]);
  } catch (e) {
    console.warn("Failed to load documents:", e);
  }
}

function _clearEditor(docType) {
  _buildInstructionsFromLatex(docType, "");
  _cmEditors[docType].setValue("");
  var frame = document.getElementById(docType + "-preview-frame");
  frame.innerHTML = '<div class="pdf-placeholder">No document selected</div>';
  document.getElementById(docType + "-version-list").textContent = "--";
}

function _loadDocIntoEditor(docType, doc) {
  _buildInstructionsFromLatex(docType, doc.latex_source || "");
  _setInstructionsFromJson(docType, doc.prompt_text || "");
  _cmEditors[docType].setValue(doc.latex_source || "");
  _currentDocId[docType] = doc.id;
  // Try loading cached PDF; fall back to placeholder
  var pdfUrl = API_BASE + "/documents/" + doc.id + "/pdf";
  fetch(pdfUrl, { method: "HEAD" }).then(function(r) {
    if (r.ok) {
      _currentPdfUrl[docType] = pdfUrl;
      _renderPdf(docType, pdfUrl + "?t=" + Date.now());
      document.getElementById(docType + "-download-btn").style.display = "";
    } else {
      var frame = document.getElementById(docType + "-preview-frame");
      var msg = (doc.latex_source && doc.latex_source.trim())
        ? "Click Compile to see preview"
        : "Write LaTeX to see preview";
      frame.innerHTML = '<div class="pdf-placeholder">' + msg + '</div>';
      document.getElementById(docType + "-download-btn").style.display = "none";
    }
  }).catch(function() {
    var frame = document.getElementById(docType + "-preview-frame");
    frame.innerHTML = '<div class="pdf-placeholder">Click Compile to see preview</div>';
  });
  _loadVersions(docType);
}

function _onDocSelect(docType) {
  var sel = document.getElementById(docType + "-doc-select");
  var docId = sel.value;
  if (!docId) return;
  var doc = _docLists[docType].find(function(d) { return d.id === docId; });
  if (doc) _loadDocIntoEditor(docType, doc);
}

async function _createDoc(docType) {
  if (!currentDetailId) return;
  var defaultTitle = docType === "cv" ? "New CV" : "New Cover Letter";
  var title = prompt("Name for this " + (docType === "cv" ? "CV" : "Cover Letter") + ":", defaultTitle);
  if (!title) return;
  var defaultLatex = docType === "cv" ? _stored.cv_latex_template : _stored.cover_letter_latex_template;
  if (!defaultLatex) {
    try {
      var tplResp = await apiFetch("GET", "/templates/defaults");
      var tpls = await tplResp.json();
      defaultLatex = tpls[docType] || "";
    } catch (e) {
      defaultLatex = "";
    }
  }
  try {
    var resp = await apiFetch("POST", "/applications/" + currentDetailId + "/documents", {
      doc_type: docType,
      title: title,
      latex_source: defaultLatex,
    });
    var doc = await resp.json();
    _docLists[docType].unshift(doc);
    var sel = document.getElementById(docType + "-doc-select");
    var opt = document.createElement("option");
    opt.value = doc.id;
    opt.textContent = doc.title;
    sel.insertBefore(opt, sel.firstChild);
    sel.value = doc.id;
    _loadDocIntoEditor(docType, doc);
    _setDocStatus(docType, "Created", "success");
    // Reset other tab's cache so switching reloads fresh data
    var other = docType === "cv" ? "cover_letter" : "cv";
    _docTabLoaded[other] = false;
  } catch (e) {
    _setDocStatus(docType, "Failed to create", "error");
  }
}

async function _saveCurrentDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;
  var body = {
    latex_source: _cmEditors[docType].getValue(),
    prompt_text: _getInstructionsAsJson(docType),
  };
  try {
    var resp = await apiFetch("PUT", "/documents/" + docId, body);
    var updated = await resp.json();
    // Update cache
    var idx = _docLists[docType].findIndex(function(d) { return d.id === docId; });
    if (idx >= 0) _docLists[docType][idx] = updated;
    _saveRetries[docType] = 0;
    _setDocStatus(docType, "Saved", "success");
  } catch (e) {
    if (_saveRetries[docType] < 1) {
      _saveRetries[docType]++;
      _setDocStatus(docType, "Save failed, retrying...", "");
      _saveTimers[docType] = setTimeout(function() { _saveCurrentDoc(docType); }, 5000);
    } else {
      _saveRetries[docType] = 0;
      _setDocStatus(docType, "Save failed", "error");
    }
  }
}

async function _deleteCurrentDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;
  if (!confirm("Delete this document?")) return;
  try {
    await apiFetch("DELETE", "/documents/" + docId);
    _docLists[docType] = _docLists[docType].filter(function(d) { return d.id !== docId; });
    _currentDocId[docType] = null;
    _docTabLoaded[docType] = false;
    _loadDocuments(docType);
    _setDocStatus(docType, "Deleted", "success");
  } catch (e) {
    _setDocStatus(docType, "Delete failed", "error");
  }
}

async function _renameCurrentDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;
  var current = _docLists[docType].find(function(d) { return d.id === docId; });
  var newTitle = prompt("Rename document:", current ? current.title : "");
  if (!newTitle || newTitle === (current && current.title)) return;
  try {
    var resp = await apiFetch("PUT", "/documents/" + docId, { title: newTitle });
    var updated = await resp.json();
    var idx = _docLists[docType].findIndex(function(d) { return d.id === docId; });
    if (idx >= 0) _docLists[docType][idx] = updated;
    var sel = document.getElementById(docType + "-doc-select");
    var opt = sel.querySelector('option[value="' + docId + '"]');
    if (opt) opt.textContent = updated.title;
    _setDocStatus(docType, "Renamed", "success");
  } catch (e) {
    _setDocStatus(docType, "Rename failed", "error");
  }
}

function _onLatexInput(docType) {
  if (_saveTimers[docType]) clearTimeout(_saveTimers[docType]);
  _saveTimers[docType] = setTimeout(function() { _saveCurrentDoc(docType); }, 2000);
}

function _initCmEditors() {
  ['cv', 'cover_letter'].forEach(function(docType) {
    var ta = document.getElementById(docType + '-latex-editor');
    var cm = CodeMirror.fromTextArea(ta, {
      mode: 'stex',
      lineNumbers: false,
      autoCloseBrackets: true,
      lineWrapping: true,
      extraKeys: {
        "Ctrl-Enter": function() { _compileDoc(docType); },
        "Cmd-Enter": function() { _compileDoc(docType); },
      },
    });
    cm.on('change', function() { _onLatexInput(docType); });
    _cmEditors[docType] = cm;
  });
}

function _scheduleInstructionSave(docType) {
  if (_saveTimers[docType]) clearTimeout(_saveTimers[docType]);
  _saveTimers[docType] = setTimeout(function() { _saveCurrentDoc(docType); }, 2000);
}

function _makeInstructionField(docType, key, label, isGlobal) {
  var field = document.createElement("div");
  field.className = "instruction-field" + (isGlobal ? " global" : "");
  field.dataset.sectionKey = key;

  var header = document.createElement("div");
  header.className = "instruction-field-header";

  var title = document.createElement("span");
  title.className = "instruction-field-title";
  title.textContent = label;
  header.appendChild(title);

  if (!isGlobal) {
    var toggleWrap = document.createElement("label");
    toggleWrap.className = "instruction-toggle-wrap";
    var toggleLabel = document.createElement("span");
    toggleLabel.className = "instruction-toggle-label";
    toggleLabel.textContent = "restrict edits";
    var toggleOuter = document.createElement("label");
    toggleOuter.className = "instruction-toggle";
    toggleOuter.setAttribute("aria-label", "Restrict edits for " + label);
    var checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.setAttribute("onchange", "_scheduleInstructionSave('" + docType + "')");
    var slider = document.createElement("span");
    slider.className = "instruction-toggle-slider";
    toggleOuter.appendChild(checkbox);
    toggleOuter.appendChild(slider);
    toggleWrap.appendChild(toggleLabel);
    toggleWrap.appendChild(toggleOuter);
    header.appendChild(toggleWrap);
  }

  field.appendChild(header);

  var textarea = document.createElement("textarea");
  textarea.className = "instruction-textarea";
  textarea.placeholder = isGlobal
    ? "General instructions for the entire document\u2026"
    : "Instructions for this section\u2026";
  textarea.setAttribute("oninput", "_scheduleInstructionSave('" + docType + "')");
  field.appendChild(textarea);

  return field;
}

function _clearInstructions(docType) {
  var panel = document.getElementById(docType + "-instructions-panel");
  if (!panel) return;
  var textareas = panel.querySelectorAll(".instruction-textarea");
  for (var i = 0; i < textareas.length; i++) {
    textareas[i].value = "";
  }
  _scheduleInstructionSave(docType);
}

function _buildInstructionsFromLatex(docType, latex) {
  var panel = document.getElementById(docType + "-instructions-panel");
  if (!panel) return;

  // Capture existing state before rebuilding
  var oldData = {};
  Array.from(panel.querySelectorAll(".instruction-field")).forEach(function(f) {
    var k = f.dataset.sectionKey;
    var ta = f.querySelector(".instruction-textarea");
    var cb = f.querySelector("input[type=checkbox]");
    oldData[k] = {
      text: ta ? ta.value : "",
      checked: cb ? cb.checked : false,
    };
  });

  panel.innerHTML = "";

  // Always add global field first
  var globalField = _makeInstructionField(docType, "__global__", "General", true);
  panel.appendChild(globalField);
  if (oldData["__global__"]) {
    globalField.querySelector(".instruction-textarea").value = oldData["__global__"].text;
  }

  var sections = [];
  if (docType === "cv") {
    var re = /\\\\section\{([^}]+)\}/g;
    var match;
    var seen = {};
    while ((match = re.exec(latex)) !== null) {
      var name = match[1];
      if (!seen[name]) {
        seen[name] = true;
        sections.push({ key: name, label: name });
      }
    }
  } else {
    // Primary: detect sections from <<NAME-PARAGRAPH: ...>> template markers
    var re = /<<([A-Z][A-Z-]*)-PARAGRAPH:/g;
    var match;
    var seen = {};
    while ((match = re.exec(latex)) !== null) {
      var name = match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase();
      if (!seen[name]) {
        seen[name] = true;
        sections.push({ key: name, label: name });
      }
    }
    // Fallback: detect from \paragraph{Name} (markers replaced after generation)
    if (sections.length === 0) {
      re = /\\\\paragraph\{([^}]+)\}/g;
      while ((match = re.exec(latex)) !== null) {
        var name = match[1];
        if (!seen[name]) {
          seen[name] = true;
          sections.push({ key: name, label: name });
        }
      }
    }
  }

  sections.forEach(function(s) {
    var f = _makeInstructionField(docType, s.key, s.label, false);
    panel.appendChild(f);
    if (oldData[s.key]) {
      f.querySelector(".instruction-textarea").value = oldData[s.key].text;
      var cb = f.querySelector("input[type=checkbox]");
      if (cb) cb.checked = oldData[s.key].checked;
    }
  });
}

function _getInstructionsAsJson(docType) {
  var panel = document.getElementById(docType + "-instructions-panel");
  if (!panel) return "";
  var fields = Array.from(panel.querySelectorAll(".instruction-field"));
  if (fields.length === 0) return "";

  var generalText = "";
  var sections = [];

  fields.forEach(function(f) {
    var k = f.dataset.sectionKey;
    var ta = f.querySelector(".instruction-textarea");
    var cb = f.querySelector("input[type=checkbox]");
    var text = ta ? ta.value : "";
    if (k === "__global__") {
      generalText = text;
    } else {
      var label = (f.querySelector(".instruction-field-title") || {}).textContent || k;
      sections.push({
        key: k,
        label: label,
        text: text,
        enabled: cb ? !cb.checked : true,
      });
    }
  });

  return JSON.stringify({ general: generalText, sections: sections });
}

function _setInstructionsFromJson(docType, jsonStr) {
  if (!jsonStr) return;
  var data;
  try {
    data = JSON.parse(jsonStr);
  } catch (e) {
    return; // treat invalid JSON as empty; no crash
  }
  if (!data || typeof data !== "object") return;

  var panel = document.getElementById(docType + "-instructions-panel");
  if (!panel) return;

  if (data.general != null) {
    var globalField = panel.querySelector('.instruction-field[data-section-key="__global__"]');
    if (!globalField) globalField = panel.querySelector(".instruction-field.global");
    if (globalField) {
      var gta = globalField.querySelector(".instruction-textarea");
      if (gta) gta.value = data.general;
    }
  }

  if (Array.isArray(data.sections)) {
    data.sections.forEach(function(s) {
      var f = panel.querySelector('.instruction-field[data-section-key="' + CSS.escape(s.key) + '"]');
      if (!f) return;
      var ta = f.querySelector(".instruction-textarea");
      var cb = f.querySelector("input[type=checkbox]");
      if (ta && s.text != null) ta.value = s.text;
      if (cb && s.enabled != null) cb.checked = !s.enabled;
    });
  }
}

// ── Extra questions ─────────────────────────────────────────────────────────

async function _eqLoad() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("GET", "/applications/" + currentDetailId + "/questions");
    var questions = await resp.json();
    _eqRender(questions);
  } catch (e) {
    console.error("Failed to load extra questions:", e);
  }
}

function _eqRender(questions) {
  var list = document.getElementById("eq-list");
  var empty = document.getElementById("eq-empty");
  list.innerHTML = "";
  empty.style.display = questions.length ? "none" : "block";

  questions.forEach(function(q) {
    list.appendChild(_eqMakeCard(q));
  });
}

function _eqMakeCard(q) {
  var card = document.createElement("div");
  card.className = "eq-card";
  card.dataset.eqId = q.id;

  // Header
  var header = document.createElement("div");
  header.className = "eq-card-header";
  header.addEventListener("click", function(e) {
    if (e.target.closest(".eq-actions")) return;
    _eqToggle(card);
  });

  var chevron = document.createElement("span");
  chevron.className = "eq-chevron";
  chevron.innerHTML = "&#x25B6;";

  var preview = document.createElement("span");
  preview.className = "eq-question-preview";
  preview.textContent = q.question || "New Question";

  var actions = document.createElement("span");
  actions.className = "eq-actions";

  var wcWrap = document.createElement("span");
  wcWrap.className = "eq-word-cap-wrap";
  wcWrap.innerHTML = "Word cap: ";
  var wcInput = document.createElement("input");
  wcInput.type = "number";
  wcInput.min = "0";
  wcInput.value = q.word_cap != null ? q.word_cap : "";
  wcInput.placeholder = "-";
  wcInput.addEventListener("input", function() { _eqScheduleSave(q.id); });
  wcInput.dataset.field = "word_cap";
  wcWrap.appendChild(wcInput);

  var delBtn = document.createElement("button");
  delBtn.className = "eq-btn-delete";
  delBtn.title = "Delete question";
  delBtn.innerHTML = "&#x2715;";
  delBtn.addEventListener("click", function(e) {
    e.stopPropagation();
    _eqDelete(q.id);
  });

  actions.appendChild(wcWrap);
  actions.appendChild(delBtn);
  header.appendChild(chevron);
  header.appendChild(preview);
  header.appendChild(actions);

  // Body
  var body = document.createElement("div");
  body.className = "eq-card-body";

  var qGroup = document.createElement("div");
  qGroup.className = "form-group";
  var qLabel = document.createElement("label");
  qLabel.className = "field-label";
  qLabel.textContent = "Question";
  var qInput = document.createElement("input");
  qInput.className = "field-input";
  qInput.type = "text";
  qInput.value = q.question || "";
  qInput.placeholder = "Enter question\u2026";
  qInput.dataset.field = "question";
  qInput.addEventListener("input", function() {
    preview.textContent = qInput.value || "New Question";
    _eqScheduleSave(q.id);
  });
  qGroup.appendChild(qLabel);
  qGroup.appendChild(qInput);

  var aGroup = document.createElement("div");
  aGroup.className = "form-group";
  var aLabel = document.createElement("label");
  aLabel.className = "field-label";
  aLabel.textContent = "Answer";
  var aTextarea = document.createElement("textarea");
  aTextarea.value = q.answer || "";
  aTextarea.placeholder = "Enter answer\u2026";
  aTextarea.dataset.field = "answer";
  aTextarea.addEventListener("input", function() {
    _eqAutoResize(aTextarea);
    _eqScheduleSave(q.id);
  });
  aGroup.appendChild(aLabel);
  aGroup.appendChild(aTextarea);

  body.appendChild(qGroup);
  body.appendChild(aGroup);

  card.appendChild(header);
  card.appendChild(body);

  // Auto-resize textarea once visible
  requestAnimationFrame(function() { _eqAutoResize(aTextarea); });

  return card;
}

function _eqToggle(card) {
  card.classList.toggle("expanded");
  // Resize textareas when expanding
  if (card.classList.contains("expanded")) {
    card.querySelectorAll("textarea").forEach(function(ta) {
      _eqAutoResize(ta);
    });
  }
}

function _eqAutoResize(ta) {
  ta.style.height = "auto";
  ta.style.height = ta.scrollHeight + "px";
}

async function _eqAdd() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("POST", "/applications/" + currentDetailId + "/questions", {});
    var q = await resp.json();
    var list = document.getElementById("eq-list");
    var card = _eqMakeCard(q);
    list.appendChild(card);
    card.classList.add("expanded");
    document.getElementById("eq-empty").style.display = "none";
    // Focus the question input
    var qInput = card.querySelector('input[data-field="question"]');
    if (qInput) qInput.focus();
  } catch (e) {
    console.error("Failed to add question:", e);
  }
}

function _eqScheduleSave(questionId) {
  if (_eqSaveTimers[questionId]) clearTimeout(_eqSaveTimers[questionId]);
  _eqSaveTimers[questionId] = setTimeout(function() { _eqSave(questionId); }, 2000);
}

async function _eqSave(questionId) {
  var card = document.querySelector('.eq-card[data-eq-id="' + questionId + '"]');
  if (!card) return;
  var qInput = card.querySelector('input[data-field="question"]');
  var aTextarea = card.querySelector('textarea[data-field="answer"]');
  var wcInput = card.querySelector('input[data-field="word_cap"]');
  var body = {
    question: qInput ? qInput.value : "",
    answer: aTextarea ? aTextarea.value : "",
  };
  var wc = wcInput ? wcInput.value.trim() : "";
  body.word_cap = wc !== "" ? parseInt(wc, 10) : null;
  try {
    await apiFetch("PUT", "/questions/" + questionId, body);
  } catch (e) {
    console.error("Failed to save question:", e);
  }
}

async function _eqDelete(questionId) {
  if (!confirm("Delete this question?")) return;
  try {
    await apiFetch("DELETE", "/questions/" + questionId);
    var card = document.querySelector('.eq-card[data-eq-id="' + questionId + '"]');
    if (card) card.remove();
    var list = document.getElementById("eq-list");
    if (list && !list.children.length) {
      document.getElementById("eq-empty").style.display = "block";
    }
  } catch (e) {
    console.error("Failed to delete question:", e);
  }
}

// ── HTML escape helpers ─────────────────────────────────────────────────

function _escHtml(s) {
  var d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

function _escAttr(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── Interview rounds ────────────────────────────────────────────────────

async function _ivLoad() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("GET", "/applications/" + currentDetailId + "/interviews");
    var data = await resp.json();
    _ivRender(data);
  } catch (e) {
    console.error("Failed to load interview rounds:", e);
  }
}

function _ivRender(items) {
  var list = document.getElementById("iv-list");
  var empty = document.getElementById("iv-empty");
  list.innerHTML = "";
  empty.style.display = items.length ? "none" : "";
  items.forEach(function(item) { list.appendChild(_ivMakeCard(item)); });
}

function _ivMakeCard(item) {
  var card = document.createElement("div");
  card.className = "eq-card";
  card.dataset.ivId = item.id;

  var roundTypes = [
    {v:"phone_screen",l:"Phone Screen"},{v:"technical",l:"Technical"},
    {v:"behavioral",l:"Behavioral"},{v:"hiring_manager",l:"Hiring Manager"},
    {v:"panel",l:"Panel"},{v:"other",l:"Other"}
  ];
  var statuses = [
    {v:"scheduled",l:"Scheduled"},{v:"completed",l:"Completed"},{v:"cancelled",l:"Cancelled"}
  ];

  var typeLabel = roundTypes.find(function(t){ return t.v === item.round_type; });
  typeLabel = typeLabel ? typeLabel.l : item.round_type;

  var dateStr = item.scheduled_at ? " \u00b7 " + item.scheduled_at : "";
  var interviewerStr = item.interviewer_names ? " \u00b7 " + item.interviewer_names : "";

  // Header (DOM construction, like extra questions)
  var header = document.createElement("div");
  header.className = "eq-card-header";
  header.addEventListener("click", function(e) {
    if (e.target.closest(".eq-actions")) return;
    _ivToggle(card);
  });

  var chevron = document.createElement("span");
  chevron.className = "eq-chevron";
  chevron.innerHTML = "&#x25B6;";

  var preview = document.createElement("span");
  preview.className = "eq-question-preview";
  preview.innerHTML = "<strong>" + _escHtml(typeLabel) + "</strong>" + dateStr + interviewerStr;

  var actions = document.createElement("span");
  actions.className = "eq-actions";

  var statusBadge = document.createElement("span");
  statusBadge.className = "badge badge-" + item.status;
  statusBadge.textContent = item.status;

  var delBtn = document.createElement("button");
  delBtn.className = "eq-btn-delete";
  delBtn.title = "Delete round";
  delBtn.innerHTML = "&#x2715;";
  delBtn.addEventListener("click", function(e) {
    e.stopPropagation();
    _ivDelete(item.id);
  });

  actions.appendChild(statusBadge);
  actions.appendChild(delBtn);
  header.appendChild(chevron);
  header.appendChild(preview);
  header.appendChild(actions);
  card.appendChild(header);

  // Body
  var body = document.createElement("div");
  body.className = "eq-card-body";

  var typeOpts = roundTypes.map(function(t){ return "<option value=\\"" + t.v + "\\"" + (t.v === item.round_type ? " selected" : "") + ">" + t.l + "</option>"; }).join("");
  var statusOpts = statuses.map(function(s){ return "<option value=\\"" + s.v + "\\"" + (s.v === item.status ? " selected" : "") + ">" + s.l + "</option>"; }).join("");

  var confidenceOpts = "<option value=\\"\\">—</option>";
  for (var i = 1; i <= 5; i++) {
    confidenceOpts += "<option value=\\"" + i + "\\"" + (item.confidence === i ? " selected" : "") + ">" + i + "</option>";
  }

  body.innerHTML =
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Type</label><select class=\\"field-input iv-round_type\\" onchange=\\"_ivScheduleSave(this)\\">" + typeOpts + "</select></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Status</label><select class=\\"field-input iv-status\\" onchange=\\"_ivScheduleSave(this)\\">" + statusOpts + "</select></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Scheduled</label><input type=\\"date\\" class=\\"field-input iv-scheduled_at\\" value=\\"" + _escAttr(item.scheduled_at) + "\\" onchange=\\"_ivScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Interviewer(s)</label><input type=\\"text\\" class=\\"field-input iv-interviewer_names\\" value=\\"" + _escAttr(item.interviewer_names) + "\\" oninput=\\"_ivScheduleSave(this)\\"></div>" +
    "</div>" +
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Location / Link</label><input type=\\"text\\" class=\\"field-input iv-location\\" value=\\"" + _escAttr(item.location) + "\\" oninput=\\"_ivScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Confidence (1-5)</label><select class=\\"field-input iv-confidence\\" onchange=\\"_ivScheduleSave(this)\\">" + confidenceOpts + "</select></div>" +
    "</div>" +
    "<label class=\\"field-label\\" style=\\"margin-top:16px;\\">Preparation</label>" +
    "<div class=\\"form-group\\"><label class=\\"field-label\\">Prep Notes</label><textarea class=\\"field-input iv-prep_notes\\" oninput=\\"_ivScheduleSave(this)\\">" + _escHtml(item.prep_notes) + "</textarea></div>" +
    "<label class=\\"field-label\\" style=\\"margin-top:16px;\\">Debrief</label>" +
    "<div class=\\"form-group\\"><label class=\\"field-label\\">Questions Asked</label><textarea class=\\"field-input iv-questions_asked\\" oninput=\\"_ivScheduleSave(this)\\">" + _escHtml(item.questions_asked) + "</textarea></div>" +
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr;gap:12px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">What Went Well</label><textarea class=\\"field-input iv-went_well\\" oninput=\\"_ivScheduleSave(this)\\">" + _escHtml(item.went_well) + "</textarea></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">What To Improve</label><textarea class=\\"field-input iv-to_improve\\" oninput=\\"_ivScheduleSave(this)\\">" + _escHtml(item.to_improve) + "</textarea></div>" +
    "</div>" +
    "<div class=\\"form-group\\" style=\\"margin-top:12px;\\"><label class=\\"field-label\\">General Notes</label><textarea class=\\"field-input iv-debrief_notes\\" oninput=\\"_ivScheduleSave(this)\\">" + _escHtml(item.debrief_notes) + "</textarea></div>";
  card.appendChild(body);
  return card;
}

function _ivToggle(cardOrChild) {
  var card = cardOrChild.classList.contains("eq-card") ? cardOrChild : cardOrChild.closest(".eq-card");
  card.classList.toggle("expanded");
  if (card.classList.contains("expanded")) {
    card.querySelectorAll("textarea").forEach(function(ta) {
      ta.style.height = "auto";
      ta.style.height = ta.scrollHeight + "px";
    });
  }
}

async function _ivAdd() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("POST", "/applications/" + currentDetailId + "/interviews", {});
    var item = await resp.json();
    document.getElementById("iv-empty").style.display = "none";
    var card = _ivMakeCard(item);
    document.getElementById("iv-list").appendChild(card);
    var chevron = card.querySelector(".eq-chevron");
    _ivToggle(chevron);
  } catch (e) {
    console.error("Failed to add interview round:", e);
  }
}

function _ivScheduleSave(el) {
  var card = el.closest(".eq-card");
  var id = card.dataset.ivId;
  clearTimeout(_ivSaveTimers[id]);
  _ivSaveTimers[id] = setTimeout(function() { _ivSave(card, id); }, 2000);
}

async function _ivSave(card, id) {
  var conf = card.querySelector(".iv-confidence").value;
  var body = {
    round_type: card.querySelector(".iv-round_type").value,
    status: card.querySelector(".iv-status").value,
    scheduled_at: card.querySelector(".iv-scheduled_at").value || null,
    interviewer_names: card.querySelector(".iv-interviewer_names").value,
    location: card.querySelector(".iv-location").value,
    confidence: conf ? parseInt(conf) : null,
    prep_notes: card.querySelector(".iv-prep_notes").value,
    questions_asked: card.querySelector(".iv-questions_asked").value,
    went_well: card.querySelector(".iv-went_well").value,
    to_improve: card.querySelector(".iv-to_improve").value,
    debrief_notes: card.querySelector(".iv-debrief_notes").value,
  };
  try {
    await apiFetch("PUT", "/interviews/" + id, body);
    var roundTypes = {phone_screen:"Phone Screen",technical:"Technical",behavioral:"Behavioral",hiring_manager:"Hiring Manager",panel:"Panel",other:"Other"};
    var preview = card.querySelector(".eq-question-preview");
    var label = roundTypes[body.round_type] || body.round_type;
    var dateStr = body.scheduled_at ? " \u00b7 " + body.scheduled_at : "";
    var intStr = body.interviewer_names ? " \u00b7 " + body.interviewer_names : "";
    preview.innerHTML = "<strong>" + label + "</strong>" + dateStr + intStr;
    card.querySelectorAll(".badge").forEach(function(b) { b.className = "badge badge-" + body.status; b.textContent = body.status; });
  } catch (e) {
    console.error("Failed to save interview round", id, e);
  }
}

async function _ivDelete(id) {
  if (!confirm("Delete this interview round?")) return;
  try {
    await apiFetch("DELETE", "/interviews/" + id);
    var card = document.querySelector('.eq-card[data-iv-id="' + id + '"]');
    card.parentNode.removeChild(card);
    if (!document.getElementById("iv-list").children.length) {
      document.getElementById("iv-empty").style.display = "";
    }
  } catch (e) {
    console.error("Failed to delete interview round:", e);
  }
}

// ── Offers ──────────────────────────────────────────────────────────────

async function _ofLoad() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("GET", "/applications/" + currentDetailId + "/offers");
    var data = await resp.json();
    _ofRender(data);
  } catch (e) {
    console.error("Failed to load offers:", e);
  }
}

function _ofRender(items) {
  var list = document.getElementById("of-list");
  var empty = document.getElementById("of-empty");
  list.innerHTML = "";
  empty.style.display = items.length ? "none" : "";
  items.forEach(function(item) { list.appendChild(_ofMakeCard(item)); });
}

function _ofMakeCard(item) {
  var card = document.createElement("div");
  card.className = "eq-card";
  card.dataset.ofId = item.id;

  var ofStatuses = [
    {v:"pending",l:"Pending"},{v:"negotiating",l:"Negotiating"},
    {v:"accepted",l:"Accepted"},{v:"declined",l:"Declined"},{v:"expired",l:"Expired"}
  ];
  var remotePolicies = [
    {v:"",l:"—"},{v:"remote",l:"Remote"},{v:"hybrid",l:"Hybrid"},{v:"onsite",l:"On-site"}
  ];
  var currencies = ["EUR","USD","GBP","CHF","CAD","AUD","JPY","SEK","NOK","DKK"];

  var statusLabel = ofStatuses.find(function(s){ return s.v === item.status; });
  statusLabel = statusLabel ? statusLabel.l : item.status;
  var salaryStr = item.base_salary ? (item.currency + " " + Number(item.base_salary).toLocaleString()) : "No salary set";

  // Header (DOM construction, like extra questions)
  var header = document.createElement("div");
  header.className = "eq-card-header";
  header.addEventListener("click", function(e) {
    if (e.target.closest(".eq-actions")) return;
    _ofToggle(card);
  });

  var chevron = document.createElement("span");
  chevron.className = "eq-chevron";
  chevron.innerHTML = "&#x25B6;";

  var preview = document.createElement("span");
  preview.className = "eq-question-preview";
  preview.innerHTML = "<strong>" + _escHtml(salaryStr) + "</strong>";

  var actions = document.createElement("span");
  actions.className = "eq-actions";

  var statusBadge = document.createElement("span");
  statusBadge.className = "badge badge-" + item.status;
  statusBadge.textContent = statusLabel;

  var delBtn = document.createElement("button");
  delBtn.className = "eq-btn-delete";
  delBtn.title = "Delete offer";
  delBtn.innerHTML = "&#x2715;";
  delBtn.addEventListener("click", function(e) {
    e.stopPropagation();
    _ofDelete(item.id);
  });

  actions.appendChild(statusBadge);
  actions.appendChild(delBtn);
  header.appendChild(chevron);
  header.appendChild(preview);
  header.appendChild(actions);
  card.appendChild(header);

  // Body
  var body = document.createElement("div");
  body.className = "eq-card-body";

  var statusOpts = ofStatuses.map(function(s){ return "<option value=\\"" + s.v + "\\"" + (s.v === item.status ? " selected" : "") + ">" + s.l + "</option>"; }).join("");
  var currencyOpts = currencies.map(function(c){ return "<option value=\\"" + c + "\\"" + (c === item.currency ? " selected" : "") + ">" + c + "</option>"; }).join("");
  var remoteOpts = remotePolicies.map(function(r){ return "<option value=\\"" + r.v + "\\"" + (r.v === item.remote_policy ? " selected" : "") + ">" + r.l + "</option>"; }).join("");

  body.innerHTML =
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Status</label><select class=\\"field-input of-status\\" onchange=\\"_ofScheduleSave(this)\\">" + statusOpts + "</select></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Base Salary</label><input type=\\"number\\" class=\\"field-input of-base_salary\\" value=\\"" + _escAttr(item.base_salary) + "\\" oninput=\\"_ofScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Currency</label><select class=\\"field-input of-currency\\" onchange=\\"_ofScheduleSave(this)\\">" + currencyOpts + "</select></div>" +
    "</div>" +
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Bonus</label><input type=\\"text\\" class=\\"field-input of-bonus\\" value=\\"" + _escAttr(item.bonus) + "\\" oninput=\\"_ofScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Equity</label><input type=\\"text\\" class=\\"field-input of-equity\\" value=\\"" + _escAttr(item.equity) + "\\" oninput=\\"_ofScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Signing Bonus</label><input type=\\"text\\" class=\\"field-input of-signing_bonus\\" value=\\"" + _escAttr(item.signing_bonus) + "\\" oninput=\\"_ofScheduleSave(this)\\"></div>" +
    "</div>" +
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Benefits</label><textarea class=\\"field-input of-benefits\\" oninput=\\"_ofScheduleSave(this)\\">" + _escHtml(item.benefits) + "</textarea></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">PTO (days)</label><input type=\\"number\\" class=\\"field-input of-pto_days\\" value=\\"" + _escAttr(item.pto_days) + "\\" oninput=\\"_ofScheduleSave(this)\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Remote Policy</label><select class=\\"field-input of-remote_policy\\" onchange=\\"_ofScheduleSave(this)\\">" + remoteOpts + "</select></div>" +
    "</div>" +
    "<div style=\\"display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;\\">" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Start Date</label><input type=\\"date\\" class=\\"field-input of-start_date\\" onchange=\\"_ofScheduleSave(this)\\" value=\\"" + _escAttr(item.start_date) + "\\"></div>" +
      "<div class=\\"form-group\\"><label class=\\"field-label\\">Expiry Date</label><input type=\\"date\\" class=\\"field-input of-expiry_date\\" onchange=\\"_ofScheduleSave(this)\\" value=\\"" + _escAttr(item.expiry_date) + "\\"></div>" +
    "</div>" +
    "<div class=\\"form-group\\"><label class=\\"field-label\\">Notes</label><textarea class=\\"field-input of-notes\\" oninput=\\"_ofScheduleSave(this)\\">" + _escHtml(item.notes) + "</textarea></div>";
  card.appendChild(body);
  return card;
}

function _ofToggle(cardOrChild) {
  var card = cardOrChild.classList.contains("eq-card") ? cardOrChild : cardOrChild.closest(".eq-card");
  card.classList.toggle("expanded");
  if (card.classList.contains("expanded")) {
    card.querySelectorAll("textarea").forEach(function(ta) {
      ta.style.height = "auto";
      ta.style.height = ta.scrollHeight + "px";
    });
  }
}

async function _ofAdd() {
  if (!currentDetailId) return;
  try {
    var resp = await apiFetch("POST", "/applications/" + currentDetailId + "/offers", {});
    var item = await resp.json();
    document.getElementById("of-empty").style.display = "none";
    var card = _ofMakeCard(item);
    document.getElementById("of-list").appendChild(card);
    var chevron = card.querySelector(".eq-chevron");
    _ofToggle(chevron);
  } catch (e) {
    console.error("Failed to add offer:", e);
  }
}

function _ofScheduleSave(el) {
  var card = el.closest(".eq-card");
  var id = card.dataset.ofId;
  clearTimeout(_ofSaveTimers[id]);
  _ofSaveTimers[id] = setTimeout(function() { _ofSave(card, id); }, 2000);
}

async function _ofSave(card, id) {
  var sal = card.querySelector(".of-base_salary").value;
  var pto = card.querySelector(".of-pto_days").value;
  var body = {
    status: card.querySelector(".of-status").value,
    base_salary: sal ? parseFloat(sal) : null,
    currency: card.querySelector(".of-currency").value,
    bonus: card.querySelector(".of-bonus").value,
    equity: card.querySelector(".of-equity").value,
    signing_bonus: card.querySelector(".of-signing_bonus").value,
    benefits: card.querySelector(".of-benefits").value,
    pto_days: pto ? parseInt(pto) : null,
    remote_policy: card.querySelector(".of-remote_policy").value,
    start_date: card.querySelector(".of-start_date").value || null,
    expiry_date: card.querySelector(".of-expiry_date").value || null,
    notes: card.querySelector(".of-notes").value,
  };
  try {
    await apiFetch("PUT", "/offers/" + id, body);
    var preview = card.querySelector(".eq-question-preview");
    var salaryStr = body.base_salary ? (body.currency + " " + Number(body.base_salary).toLocaleString()) : "No salary set";
    preview.innerHTML = "<strong>" + salaryStr + "</strong>";
    var ofStatuses = {pending:"Pending",negotiating:"Negotiating",accepted:"Accepted",declined:"Declined",expired:"Expired"};
    card.querySelectorAll(".badge").forEach(function(b) { b.className = "badge badge-" + body.status; b.textContent = ofStatuses[body.status] || body.status; });
  } catch (e) {
    console.error("Failed to save offer", id, e);
  }
}

async function _ofDelete(id) {
  if (!confirm("Delete this offer?")) return;
  try {
    await apiFetch("DELETE", "/offers/" + id);
    var card = document.querySelector('.eq-card[data-of-id="' + id + '"]');
    card.parentNode.removeChild(card);
    if (!document.getElementById("of-list").children.length) {
      document.getElementById("of-empty").style.display = "";
    }
  } catch (e) {
    console.error("Failed to delete offer:", e);
  }
}

async function _compileDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;
  // Save first
  var body = {
    latex_source: _cmEditors[docType].getValue(),
    prompt_text: _getInstructionsAsJson(docType),
  };
  try {
    await apiFetch("PUT", "/documents/" + docId, body);
  } catch (e) {
    _setDocStatus(docType, "Save failed, compile aborted", "error");
    return;
  }
  _setDocStatus(docType, "Compiling...", "");
  _showCompileOverlay(docType, true);
  try {
    var resp = await fetch(API_BASE + "/documents/" + docId + "/compile", { method: "POST" });
    if (!resp.ok) {
      var err = await resp.json().catch(function() { return { detail: "Compilation error" }; });
      _setDocStatus(docType, err.detail || "Compilation failed", "error");
      _showCompileOverlay(docType, false);
      return;
    }
    _currentPdfUrl[docType] = "/api/v1/documents/" + docId + "/pdf";
    _renderPdf(docType, _currentPdfUrl[docType] + "?t=" + Date.now());
    _buildInstructionsFromLatex(docType, _cmEditors[docType].getValue());

    _showCompileOverlay(docType, false);
    _setDocStatus(docType, "Compiled", "success");
    document.getElementById(docType + "-download-btn").style.display = "";
  } catch (e) {
    _setDocStatus(docType, "Compile error: " + e.message, "error");
    _showCompileOverlay(docType, false);
  }
}

async function _loadVersions(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;
  try {
    var resp = await apiFetch("GET", "/documents/" + docId + "/versions");
    var versions = await resp.json();
    var el = document.getElementById(docType + "-version-list");
    if (versions.length === 0) {
      el.textContent = "No versions yet";
      return;
    }
    el.innerHTML = "";
    versions.slice(0, 10).forEach(function(v) {
      var btn = document.createElement("button");
      btn.textContent = "v" + v.version_number;
      btn.title = "Compiled " + v.compiled_at;
      btn.onclick = function() { _restoreVersion(docType, v); };
      el.appendChild(btn);
    });
  } catch (e) {
    // silent
  }
}

function _restoreVersion(docType, version) {
  if (!confirm("Restore version " + version.version_number + "? Current edits will be replaced.")) return;
  _cmEditors[docType].setValue(version.latex_source);
  _buildInstructionsFromLatex(docType, version.latex_source || "");
  _setInstructionsFromJson(docType, version.prompt_text || "");
  _saveCurrentDoc(docType);
}

function _setDocStatus(docType, msg, cls) {
  var el = document.getElementById(docType + "-save-status");
  el.textContent = msg;
  el.className = "doc-compile-status" + (cls ? " " + cls : "");
  if (cls === "success") {
    setTimeout(function() { if (el.textContent === msg) el.textContent = ""; }, 3000);
  }
}

function _setGenStatus(docType, msg, cls) {
  var el = document.getElementById(docType + "-gen-status");
  if (!el) return;
  el.textContent = msg;
  el.className = "doc-compile-status" + (cls ? " " + cls : "");
  if (cls === "success") {
    setTimeout(function() { if (el.textContent === msg) el.textContent = ""; }, 4000);
  }
}

var _GEN_NODE_LABELS = {
  "retrieve_kb_docs":   "Retrieving knowledge base...",
  "generate_or_revise": "Generating document...",
  "analyze_fit":        "Analysing job fit...",
  "analyze_quality":    "Checking quality...",
  "apply_suggestions":  "Applying improvements...",
  "compile_and_check":  "Compiling...",
  "reduce_size":        "Reducing to 1 page...",
  "finalize":           "Finalising...",
  "done":               "Done",
  "error":              "Error"
};

var _GEN_STEP_ORDER = [
  {key: "retrieve_kb_docs",   label: "Retrieve KB"},
  {key: "generate_or_revise", label: "Generate"},
  {key: "analyze_fit",        label: "Analyze fit"},
  {key: "analyze_quality",    label: "Check quality"},
  {key: "apply_suggestions",  label: "Apply improvements"},
  {key: "compile_and_check",  label: "Compile"},
  {key: "reduce_size",        label: "Reduce size"},
  {key: "finalize",           label: "Finalize"}
];

function _initGenProgress(docType) {
  var container = document.getElementById(docType + "-gen-progress");
  if (!container) return;
  container.innerHTML = "";
  _GEN_STEP_ORDER.forEach(function(step, i) {
    if (i > 0) {
      var sep = document.createElement("span");
      sep.className = "gen-progress-sep";
      sep.textContent = "\\u203a";
      container.appendChild(sep);
    }
    var el = document.createElement("span");
    el.className = "gen-progress-step";
    el.setAttribute("data-step-key", step.key);
    var icon = document.createElement("span");
    icon.className = "step-icon";
    el.appendChild(icon);
    el.appendChild(document.createTextNode(step.label));
    container.appendChild(el);
  });
  container.style.display = "";
}

function _updateGenProgress(docType, activeNode) {
  var container = document.getElementById(docType + "-gen-progress");
  if (!container) return;
  // Mark previously active step as completed
  var prev = container.querySelector(".gen-progress-step.active");
  if (prev) prev.className = "gen-progress-step completed";
  // Mark new node as active (skip unknown nodes)
  var step = container.querySelector(".gen-progress-step[data-step-key=\\"" + activeNode + "\\"]");
  if (step) step.className = "gen-progress-step active";
}

function _completeGenProgress(docType) {
  var container = document.getElementById(docType + "-gen-progress");
  if (!container) return;
  var steps = container.querySelectorAll(".gen-progress-step");
  for (var i = 0; i < steps.length; i++) {
    // Only mark steps that were seen (active or completed); leave pure-pending steps alone
    // unless they precede the last completed step — mark all as completed for a clean done state
    steps[i].className = "gen-progress-step completed";
  }
}

function _errorGenProgress(docType) {
  var container = document.getElementById(docType + "-gen-progress");
  if (!container) return;
  var active = container.querySelector(".gen-progress-step.active");
  if (active) active.className = "gen-progress-step error";
}

function _hideGenProgress(docType) {
  var container = document.getElementById(docType + "-gen-progress");
  if (container) {
    container.style.display = "none";
    container.innerHTML = "";
  }
}

async function _generateDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;

  // Save current editor state first
  var saveBody = {
    latex_source: _cmEditors[docType].getValue(),
    prompt_text: _getInstructionsAsJson(docType)
  };
  try {
    await apiFetch("PUT", "/documents/" + docId, saveBody);
  } catch (e) {
    _setGenStatus(docType, "Save failed: " + e.message, "error");
    return;
  }

  // Heuristic: if template placeholders like <<KEY: ...>> are still present,
  // treat this as a first generation.
  var currentLatex = _cmEditors[docType].getValue();
  var isFirst = /<<[A-Z\-]+:/.test(currentLatex);

  _initGenProgress(docType);
  _showCompileOverlay(docType, true);

  var resp;
  try {
    resp = await fetch(API_BASE + "/documents/" + docId + "/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_first_generation: isFirst })
    });
  } catch (e) {
    _hideGenProgress(docType);
    _setGenStatus(docType, "Network error: " + e.message, "error");
    _showCompileOverlay(docType, false);
    return;
  }

  if (!resp.ok) {
    var errData = await resp.json().catch(function() { return { detail: "Request failed" }; });
    _hideGenProgress(docType);
    _setGenStatus(docType, errData.detail || "Generate failed", "error");
    _showCompileOverlay(docType, false);
    return;
  }

  // Read SSE stream
  var reader = resp.body.getReader();
  var decoder = new TextDecoder();
  var buffer = "";

  while (true) {
    var chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    var lines = buffer.split("\\n");
    buffer = lines.pop();

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (!line.startsWith("data: ")) continue;
      var raw = line.slice(6).trim();
      if (!raw) continue;
      var evt;
      try { evt = JSON.parse(raw); } catch (e) { continue; }

      if (evt.node && evt.node !== "done" && evt.node !== "error") {
        _updateGenProgress(docType, evt.node);
      }

      if (evt.node === "done") {
        _showCompileOverlay(docType, false);
        _completeGenProgress(docType);
        if (evt.latex) {
          _cmEditors[docType].setValue(evt.latex);
          _buildInstructionsFromLatex(docType, evt.latex);
          // Refresh PDF preview from the cache the server just populated
          var previewEl = document.getElementById(docType + "-preview-frame");
          if (previewEl) {
            var pdfUrl = API_BASE + "/documents/" + docId + "/pdf?t=" + Date.now();
            _currentPdfUrl[docType] = API_BASE + "/documents/" + docId + "/pdf";
            _renderPdf(docType, pdfUrl);
          }
          document.getElementById(docType + "-download-btn").style.display = "";
          _loadVersions(docType);
        }
        // Show agent feedback panel
        var panel = document.getElementById(docType + "-agent-feedback");
        if (panel && (evt.fit_feedback || evt.quality_feedback || evt.generation_system_prompt || evt.generation_user_prompt)) {
          panel.style.display = "";
          var fitEl = document.getElementById(docType + "-fit-feedback");
          var qualEl = document.getElementById(docType + "-quality-feedback");
          var sysPromptEl = document.getElementById(docType + "-generation-system-prompt");
          var userPromptEl = document.getElementById(docType + "-generation-user-prompt");
          if (fitEl) fitEl.textContent = evt.fit_feedback || "";
          if (qualEl) qualEl.textContent = evt.quality_feedback || "";
          if (sysPromptEl) sysPromptEl.textContent = evt.generation_system_prompt || "";
          if (userPromptEl) userPromptEl.textContent = evt.generation_user_prompt || "";
        }
        var pageLabel = evt.page_count ? " (" + evt.page_count + " page)" : "";
        _setGenStatus(docType, "Generated" + pageLabel, "success");
      }

      if (evt.node === "error") {
        _showCompileOverlay(docType, false);
        _errorGenProgress(docType);
        _setGenStatus(docType, "Error: " + (evt.detail || "unknown"), "error");
      }
    }
  }
}

async function _critiqueDoc(docType) {
  var docId = _currentDocId[docType];
  if (!docId) return;

  // Save current editor state first
  var saveBody = {
    latex_source: _cmEditors[docType].getValue(),
    prompt_text: _getInstructionsAsJson(docType)
  };
  try {
    await apiFetch("PUT", "/documents/" + docId, saveBody);
  } catch (e) {
    _setGenStatus(docType, "Save failed: " + e.message, "error");
    return;
  }

  _setGenStatus(docType, "Starting critique...", "");

  var resp;
  try {
    resp = await fetch(API_BASE + "/documents/" + docId + "/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ critique_only: true })
    });
  } catch (e) {
    _setGenStatus(docType, "Network error: " + e.message, "error");
    return;
  }

  if (!resp.ok) {
    var errData = await resp.json().catch(function() { return { detail: "Request failed" }; });
    _setGenStatus(docType, errData.detail || "Critique failed", "error");
    return;
  }

  // Read SSE stream
  var reader = resp.body.getReader();
  var decoder = new TextDecoder();
  var buffer = "";

  while (true) {
    var chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    var lines = buffer.split("\\n");
    buffer = lines.pop();

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (!line.startsWith("data: ")) continue;
      var raw = line.slice(6).trim();
      if (!raw) continue;
      var evt;
      try { evt = JSON.parse(raw); } catch (e) { continue; }

      if (evt.node && evt.node !== "done" && evt.node !== "error") {
        var label = _GEN_NODE_LABELS[evt.node] || evt.node;
        _setGenStatus(docType, label, "");
      }

      if (evt.node === "done") {
        // Show agent feedback panel (don't update editor or PDF)
        var panel = document.getElementById(docType + "-agent-feedback");
        if (panel && (evt.fit_feedback || evt.quality_feedback)) {
          panel.style.display = "";
          var fitEl = document.getElementById(docType + "-fit-feedback");
          var qualEl = document.getElementById(docType + "-quality-feedback");
          var sysPromptEl = document.getElementById(docType + "-generation-system-prompt");
          var userPromptEl = document.getElementById(docType + "-generation-user-prompt");
          if (fitEl) fitEl.textContent = evt.fit_feedback || "";
          if (qualEl) qualEl.textContent = evt.quality_feedback || "";
          if (sysPromptEl) sysPromptEl.textContent = evt.generation_system_prompt || "";
          if (userPromptEl) userPromptEl.textContent = evt.generation_user_prompt || "";
        }
        _setGenStatus(docType, "Critique complete", "success");
      }

      if (evt.node === "error") {
        _setGenStatus(docType, "Error: " + (evt.detail || "unknown"), "error");
      }
    }
  }
}

document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    var step = document.getElementById("step-cv-cover");
    if (step && step.classList.contains("trisplit-fullscreen")) {
      _toggleTrisplitFullscreen();
    }
  }
});

// Init
_initCmEditors();
checkKbConnection();
loadApplications();
loadAiSettings();
</script>

</body>
</html>
"""
