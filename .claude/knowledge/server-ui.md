# server-ui Knowledge
<!-- source: jam/html_page.py -->
<!-- hash: 0b48950813bc -->
<!-- updated: 2026-03-20 -->

## Public API

| Constant | Type | Purpose |
|---|---|---|
| `HTML_PAGE` | `str` | Complete HTML document with inline CSS and JS |

## Key Components

### Layout
- Header: app title + kb connection indicator
- Card with tab bar: Dashboard, Applications, Settings
- Max-width: 912px (matches kb design system)

### Tabs
- Dashboard: stats row (Total, Active, Interviews, Offers) + empty state
- Applications: placeholder empty state
- Settings: placeholder empty state

### CSS Classes (from shared design system)
- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-green`, `.btn-danger`, `.btn-sm`
- Badges: `.badge`, `.badge-indigo`, `.badge-green`, `.badge-gray`, `.badge-amber`
- Forms: `.field-label`, `.field-input`
- Layout: `.card`, `.tab-bar`, `.tab-btn`, `.tab-panel`
- Status: `.status-msg`, `.status-msg.success`, `.status-msg.error`
- Custom: `.stats-row`, `.stat-card`, `.connection-status`, `.connection-dot`

### JS Helpers
- `apiFetch(method, url, body)` — central API wrapper
- `switchTab(name)` — tab switching
- `checkKbConnection()` — checks `/health` on load

### Design Tokens Used
- Primary: `#4f46e5` (indigo)
- Success: `#10b981` (green)
- Error: `#dc2626` (red)
- Background: `#f0f2f5`
- Card: `#ffffff`, radius `16px`
- Text: `#1a1a2e` primary, `#6b7280` secondary, `#9ca3af` muted

## Dependencies
- Imports from: (none — standalone constant)
- Imported by: `jam/server.py`

## Testing
- Tested indirectly via `test_server.py` (checks HTML content in response)

## Known Limitations
- All tabs except Dashboard are placeholder empty states
- No actual data fetching yet — stats are hardcoded to 0
