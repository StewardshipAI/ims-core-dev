//! Smart Scroll Logic Implementation
//!
//! CRITICAL REQUIREMENTS:
//! 1. Default: auto_scroll = true (follow text stream)
//! 2. Manual Override: Up/Down disables auto_scroll for that pane
//! 3. Persistence: Other pane remains in auto_scroll if not interacted with
//! 4. Reset: Opening new file resets both panes to auto_scroll = true

use crate::app::{ActiveSession, ScrollState};

/// Scroll logic manager
pub struct ScrollManager;

impl ScrollManager {
    /// Handle scroll up event
    pub fn scroll_up(scroll_state: &mut ScrollState, lines: usize) {
        // Disable auto-scroll on manual interaction
        scroll_state.auto_scroll = false;

        // Scroll up (decrease offset)
        if scroll_state.scroll_offset > 0 {
            scroll_state.scroll_offset = scroll_state.scroll_offset.saturating_sub(lines as u16);
        }
    }

    /// Handle scroll down event
    pub fn scroll_down(scroll_state: &mut ScrollState, lines: usize, max_lines: usize) {
        // Disable auto-scroll on manual interaction
        scroll_state.auto_scroll = false;

        // Scroll down (increase offset)
        let max_offset = max_lines.saturating_sub(1);
        scroll_state.scroll_offset = (scroll_state.scroll_offset + lines as u16).min(max_offset as u16);
    }

    /// Check if at bottom (for auto-scroll re-enable detection)
    pub fn is_at_bottom(scroll_state: &ScrollState, content_lines: usize, visible_lines: usize) -> bool {
        let offset = scroll_state.scroll_offset as usize;
        let max_offset = content_lines.saturating_sub(visible_lines);
        
        offset >= max_offset
    }

    /// Auto-re-enable scroll if user scrolls to bottom
    pub fn maybe_re_enable_auto_scroll(scroll_state: &mut ScrollState, content_lines: usize, visible_lines: usize) {
        if Self::is_at_bottom(scroll_state, content_lines, visible_lines) {
            scroll_state.enable_auto_scroll();
        }
    }

    /// Calculate visible range for rendering
    pub fn calculate_visible_range(
        scroll_state: &ScrollState,
        content_lines: usize,
        visible_lines: usize,
    ) -> (usize, usize) {
        if scroll_state.auto_scroll {
            // Auto-scroll: show last N lines
            let start = content_lines.saturating_sub(visible_lines);
            let end = content_lines;
            (start, end)
        } else {
            // Manual: use stored offset
            let start = scroll_state.scroll_offset as usize;
            let end = (start + visible_lines).min(content_lines);
            (start, end)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scroll_up() {
        let mut scroll = ScrollState::default();
        scroll.scroll_offset = 10;
        scroll.auto_scroll = true;

        ScrollManager::scroll_up(&mut scroll, 3);

        assert!(!scroll.auto_scroll); // Disabled on manual scroll
        assert_eq!(scroll.scroll_offset, 7);
    }

    #[test]
    fn test_scroll_down() {
        let mut scroll = ScrollState::default();
        scroll.auto_scroll = true;

        ScrollManager::scroll_down(&mut scroll, 5, 100);

        assert!(!scroll.auto_scroll);
        assert_eq!(scroll.scroll_offset, 5);
    }

    #[test]
    fn test_at_bottom_detection() {
        let scroll = ScrollState {
            auto_scroll: false,
            scroll_offset: 50,
        };

        let content_lines = 100;
        let visible_lines = 50;

        let at_bottom = ScrollManager::is_at_bottom(&scroll, content_lines, visible_lines);
        assert!(at_bottom);
    }

    #[test]
    fn test_auto_re_enable() {
        let mut scroll = ScrollState {
            auto_scroll: false,
            scroll_offset: 50,
        };

        ScrollManager::maybe_re_enable_auto_scroll(&mut scroll, 100, 50);

        assert!(scroll.auto_scroll); // Re-enabled at bottom
    }

    #[test]
    fn test_visible_range_auto_scroll() {
        let scroll = ScrollState {
            auto_scroll: true,
            scroll_offset: 0,
        };

        let (start, end) = ScrollManager::calculate_visible_range(&scroll, 100, 20);

        assert_eq!(start, 80); // Last 20 lines
        assert_eq!(end, 100);
    }

    #[test]
    fn test_visible_range_manual_scroll() {
        let scroll = ScrollState {
            auto_scroll: false,
            scroll_offset: 10,
        };

        let (start, end) = ScrollManager::calculate_visible_range(&scroll, 100, 20);

        assert_eq!(start, 10);
        assert_eq!(end, 30);
    }

    #[test]
    fn test_scroll_independence() {
        // Simulate two panes with independent scroll states
        let mut thinking = ScrollState::default();
        let mut generation = ScrollState::default();

        // User scrolls thinking pane
        ScrollManager::scroll_up(&mut thinking, 5);

        // Thinking should be manual, generation still auto
        assert!(!thinking.auto_scroll);
        assert!(generation.auto_scroll);
    }
}
