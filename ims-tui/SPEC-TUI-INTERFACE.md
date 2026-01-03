# SPEC-TUI: Smart Scroll & Virtual Cursor

## 1. Smart Scroll Logic
- **Condition:** If `AppState.global_auto_scroll` is `true`:
  - New lines appended to `thinking_log` or `generated_code` will automatically increment `scroll_offset`.
  - **Manual Override:** If a `KeyEvent::Up` is detected while a pane is focused, set `ActiveSession.[pane].auto_scroll = false`.
  - **Reset:** Auto-scroll for both panes resets to `true` when a new file is opened or a new agent task begins.

## 2. Vendor Cursor
- The "cursor" is not the system cursor. It is a character (from `vendor_logo`) rendered at the end of the `generated_code` string.
- If `theme_cursor` is toggled off in Settings, fall back to a standard block `█`.