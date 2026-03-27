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
    min-height: 100vh;
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
    height: calc(100vh - 64px);
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

  .detail-step {
    display: none;
  }

  .detail-step.active {
    display: block;
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
  .doc-tab-panel.active { display: flex; flex-direction: column; flex: 1; min-height: 0; }

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
            <button class="sidebar-menu-btn active" data-section="general" onclick="switchSettingsSection('general')">
              General
            </button>
          </li>
          <li>
            <button class="sidebar-menu-btn" data-section="connection" onclick="switchSettingsSection('connection')">
              Connection
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
        </ul>
      </div>

      <div class="settings-content">
        <!-- General Settings Section -->
        <div id="section-general" class="settings-section active">
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
            <select id="ai-model" class="field-input"></select>
          </div>

          <div id="ai-credentials"></div>

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
          <li><button class="detail-step-btn" data-step="interview-1" onclick="switchDetailStep('interview-1')">Interview Round 1</button></li>
          <li><button class="detail-step-btn" data-step="interview-2" onclick="switchDetailStep('interview-2')">Interview Round 2</button></li>
          <li><button class="detail-step-btn" data-step="interview-3" onclick="switchDetailStep('interview-3')">Interview Round 3</button></li>
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
              <button class="btn btn-sm" id="cv-download-btn" onclick="_downloadPdf('cv')" style="display:none">Download PDF</button>
              <button class="btn btn-sm btn-danger" onclick="_deleteCurrentDoc('cv')">Delete</button>
              <span id="cv-save-status" class="doc-compile-status"></span>
            </div>
            <div id="cv-trisplit" class="trisplit-container">
              <div class="trisplit-pane" data-pane="0">
                <div class="trisplit-pane-header">
                  <span>Instructions</span>
                  <button onclick="_togglePane('cv-trisplit',0)" title="Collapse/Expand">&#x25C0;</button>
                </div>
                <div class="trisplit-pane-body">
                  <div id="cv-instructions-panel" class="instructions-panel"></div>
                </div>
              </div>
              <div class="trisplit-pane" data-pane="1">
                <div class="trisplit-pane-header"><span>LaTeX Source</span><button onclick="_togglePane('cv-trisplit',1)" title="Collapse/Expand">&#x25C0;&#x25B6;</button></div>
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
          </div>

          <!-- Cover Letter tab -->
          <div id="doc-panel-cover_letter" class="doc-tab-panel">
            <div class="doc-list-bar">
              <select id="cover_letter-doc-select" onchange="_onDocSelect('cover_letter')"><option value="">-- no documents --</option></select>
              <button class="btn btn-sm btn-primary" onclick="_createDoc('cover_letter')">+ New</button>
              <button class="btn btn-sm btn-green" onclick="_saveCurrentDoc('cover_letter')">Save</button>
              <button class="btn btn-sm btn-primary" onclick="_compileDoc('cover_letter')">Compile</button>
              <button class="btn btn-sm" id="cover_letter-download-btn" onclick="_downloadPdf('cover_letter')" style="display:none">Download PDF</button>
              <button class="btn btn-sm btn-danger" onclick="_deleteCurrentDoc('cover_letter')">Delete</button>
              <span id="cover_letter-save-status" class="doc-compile-status"></span>
            </div>
            <div id="cover_letter-trisplit" class="trisplit-container">
              <div class="trisplit-pane" data-pane="0">
                <div class="trisplit-pane-header">
                  <span>Instructions</span>
                  <button onclick="_togglePane('cover_letter-trisplit',0)" title="Collapse/Expand">&#x25C0;</button>
                </div>
                <div class="trisplit-pane-body">
                  <div id="cover_letter-instructions-panel" class="instructions-panel"></div>
                </div>
              </div>
              <div class="trisplit-pane" data-pane="1">
                <div class="trisplit-pane-header"><span>LaTeX Source</span><button onclick="_togglePane('cover_letter-trisplit',1)" title="Collapse/Expand">&#x25C0;&#x25B6;</button></div>
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
          </div>
        </div>

        <!-- Step: Extra Questions -->
        <div id="step-extra-questions" class="detail-step">
          <h2>Extra Questions</h2>
          <p class="placeholder-text">Coming soon</p>
        </div>

        <!-- Step: Interview Round 1 -->
        <div id="step-interview-1" class="detail-step">
          <h2>Interview Round 1</h2>
          <p class="placeholder-text">Coming soon</p>
        </div>

        <!-- Step: Interview Round 2 -->
        <div id="step-interview-2" class="detail-step">
          <h2>Interview Round 2</h2>
          <p class="placeholder-text">Coming soon</p>
        </div>

        <!-- Step: Interview Round 3 -->
        <div id="step-interview-3" class="detail-step">
          <h2>Interview Round 3</h2>
          <p class="placeholder-text">Coming soon</p>
        </div>

        <!-- Step: Offers -->
        <div id="step-offers" class="detail-step">
          <h2>Offers</h2>
          <p class="placeholder-text">Coming soon</p>
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

// Settings navigation
function switchToSettings() {
  document.getElementById("dashboard-view").style.display = "none";
  document.getElementById("detail-view").style.display = "none";
  document.getElementById("settings-view").style.display = "flex";
  loadAiSettings();
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
    await loadTemplateSettings();
  } catch (e) {
    console.error("Failed to load AI settings:", e);
  }
}

function renderProviderDropdown() {
  const sel = document.getElementById("ai-provider");
  sel.innerHTML = "";
  if (!_catalog) return;
  const current = _stored.llm_provider || "openai";
  _catalog.providers.forEach(function(p) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.label;
    if (p.id === current) opt.selected = true;
    sel.appendChild(opt);
  });
  onProviderChange();
}

function _providerById(id) {
  if (!_catalog) return null;
  return _catalog.providers.find(function(p) { return p.id === id; }) || null;
}

function _providerHasKey(id) {
  if (id === "ollama") return true;
  return !!_stored[id + "_api_key_set"];
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

function _downloadPdf(docType) {
  var url = _currentPdfUrl[docType];
  if (!url) return;
  var a = document.createElement("a");
  a.href = url;
  var title = _currentDocId[docType] ? _currentDocId[docType].slice(0, 8) : "document";
  a.download = docType.replace("_", "-") + "-" + title + ".pdf";
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
  var frame = document.getElementById(docType + "-preview-frame");
  var msg = (doc.latex_source && doc.latex_source.trim())
    ? "Click Compile to see preview"
    : "Write LaTeX to see preview";
  frame.innerHTML = '<div class="pdf-placeholder">' + msg + '</div>';
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
  var title = docType === "cv" ? "New CV" : "New Cover Letter";
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
      enabled: cb ? cb.checked : true,
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
    var re = /\\\\paragraph\{([^}]+)\}/g;
    var match;
    var seen = {};
    while ((match = re.exec(latex)) !== null) {
      var name = match[1];
      if (!seen[name]) {
        seen[name] = true;
        sections.push({ key: name, label: name });
      }
    }
  }

  sections.forEach(function(s) {
    var f = _makeInstructionField(docType, s.key, s.label, false);
    panel.appendChild(f);
    if (oldData[s.key]) {
      f.querySelector(".instruction-textarea").value = oldData[s.key].text;
      var cb = f.querySelector("input[type=checkbox]");
      if (cb) cb.checked = oldData[s.key].enabled;
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
        enabled: cb ? cb.checked : true,
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
      if (cb && s.enabled != null) cb.checked = s.enabled;
    });
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
    _loadVersions(docType);
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
