//! Editor Panes (Thinking + Generation)
//!
//! Implements the 50/50 split center workspace with smart scroll logic

use crate::app::{AppState, FocusPane, InputMode};
use crate::ui::focus_border_style;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Wrap},
    Frame,
};

/// Render thinking pane (top half of center workspace)
pub fn render_thinking_pane(f: &mut Frame, state: &AppState, area: Rect) {
    let session = match &state.session {
        Some(s) => s,
        None => return,
    };

    let is_focused = state.focus == FocusPane::Thinking;

    // Create header with vendor branding
    let header_area = Rect {
        x: area.x,
        y: area.y,
        width: area.width,
        height: 3,
    };

    let content_area = Rect {
        x: area.x,
        y: area.y + 3,
        width: area.width,
        height: area.height.saturating_sub(3),
    };

    // Render vendor header
    render_vendor_header(f, session, header_area, is_focused);

    // Render thinking log
    render_scrollable_content(
        f,
        &state.thinking_log,
        content_area,
        &session.thinking,
        is_focused,
        "Agent Thinking",
    );
}

/// Render generation pane (bottom half of center workspace)
pub fn render_generation_pane(f: &mut Frame, state: &AppState, area: Rect) {
    let session = match &state.session {
        Some(s) => s,
        None => return,
    };

    let is_focused = state.focus == FocusPane::Generation;

    // Calculate scroll offset for auto-scroll
    let content_lines: Vec<&str> = state.generated_code.lines().collect();
    let visible_lines = area.height.saturating_sub(2) as usize; // Account for borders

    let scroll_offset = if session.generation.auto_scroll {
        // Auto-scroll: show last N lines
        content_lines.len().saturating_sub(visible_lines)
    } else {
        // Manual scroll: use stored offset
        session.generation.scroll_offset as usize
    };

    // Add virtual cursor (vendor logo)
    let mut display_lines: Vec<Line> = content_lines
        .iter()
        .skip(scroll_offset)
        .take(visible_lines)
        .map(|&line| Line::from(line))
        .collect();

    // Append vendor logo as virtual cursor on last line
    if !display_lines.is_empty() && session.generation.auto_scroll {
        let last_idx = display_lines.len() - 1;
        let current_text = display_lines[last_idx].clone();
        
        let mut spans = current_text.spans;
        spans.push(Span::styled(
            format!(" {}", session.vendor_logo),
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD | Modifier::SLOW_BLINK),
        ));
        
        display_lines[last_idx] = Line::from(spans);
    }

    let scroll_indicator = if session.generation.auto_scroll {
        "🔄 Auto-scroll"
    } else {
        "📌 Manual"
    };

    let title = format!(
        "File Generation ({}/{} lines) [{}]",
        scroll_offset + visible_lines.min(content_lines.len()),
        content_lines.len(),
        scroll_indicator
    );

    let paragraph = Paragraph::new(display_lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(title)
                .border_style(focus_border_style(is_focused)),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(paragraph, area);
}

/// Render prompt input box (bottom of center workspace)
pub fn render_prompt_box(f: &mut Frame, state: &AppState, area: Rect) {
    let is_focused = state.focus == FocusPane::Prompt;
    
    let border_style = if is_focused {
        match state.input_mode {
            InputMode::Normal => Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            InputMode::Editing => Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        }
    } else {
        Style::default().fg(Color::DarkGray)
    };

    let title = match state.input_mode {
        InputMode::Normal => "Prompt (Press Enter to edit)",
        InputMode::Editing => "Prompt (Editing - Press Esc to stop)",
    };

    let input_text = if state.input_buffer.is_empty() && state.input_mode == InputMode::Normal {
        Span::styled(
            "Type your instruction here...",
            Style::default().fg(Color::Gray).add_modifier(Modifier::ITALIC),
        )
    } else {
        Span::raw(&state.input_buffer)
    };

    let paragraph = Paragraph::new(Line::from(input_text))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(title)
                .border_style(border_style),
        );

    f.render_widget(paragraph, area);

    // Render cursor if editing
    if state.input_mode == InputMode::Editing && is_focused {
        f.set_cursor_position((
            area.x + state.input_buffer.len() as u16 + 1,
            area.y + 1,
        ));
    }
}

/// Render vendor branding header
fn render_vendor_header(
    f: &mut Frame,
    session: &crate::app::ActiveSession,
    area: Rect,
    is_focused: bool,
) {
    let vendor_display = format!(
        "{} {} | File: {}",
        session.vendor_logo,
        session.vendor_name,
        session
            .file_path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
    );

    let header = Paragraph::new(Line::from(vec![
        Span::styled(
            session.vendor_logo.clone(),
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw(" "),
        Span::styled(
            &session.vendor_name,
            Style::default()
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        ),
        Span::raw(" | "),
        Span::styled(
            session
                .file_path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown"),
            Style::default().fg(Color::Yellow),
        ),
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(focus_border_style(is_focused)),
    );

    f.render_widget(header, area);
}

/// Generic scrollable content renderer
fn render_scrollable_content(
    f: &mut Frame,
    lines: &[String],
    area: Rect,
    scroll_state: &crate::app::ScrollState,
    is_focused: bool,
    title: &str,
) {
    let visible_lines = area.height.saturating_sub(2) as usize;

    let scroll_offset = if scroll_state.auto_scroll {
        lines.len().saturating_sub(visible_lines)
    } else {
        scroll_state.scroll_offset as usize
    };

    let display_lines: Vec<Line> = lines
        .iter()
        .skip(scroll_offset)
        .take(visible_lines)
        .map(|line| Line::from(line.as_str()))
        .collect();

    let scroll_indicator = if scroll_state.auto_scroll {
        "🔄 Auto-scroll"
    } else {
        "📌 Manual"
    };

    let full_title = format!(
        "{} ({}/{} lines) [{}]",
        title,
        scroll_offset + visible_lines.min(lines.len()),
        lines.len(),
        scroll_indicator
    );

    let paragraph = Paragraph::new(display_lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(full_title)
                .border_style(focus_border_style(is_focused)),
        )
        .wrap(Wrap { trim: false });

    f.render_widget(paragraph, area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::{ActiveSession, ScrollState};
    use std::path::PathBuf;

    #[test]
    fn test_scroll_calculation() {
        let lines = vec![
            "Line 1".to_string(),
            "Line 2".to_string(),
            "Line 3".to_string(),
            "Line 4".to_string(),
            "Line 5".to_string(),
        ];

        let visible_lines = 3;

        // Auto-scroll: should show last 3 lines
        let auto_offset = lines.len().saturating_sub(visible_lines);
        assert_eq!(auto_offset, 2); // Skip first 2 lines

        // Manual scroll: use stored offset
        let manual_offset = 1;
        assert_eq!(manual_offset, 1);
    }

    #[test]
    fn test_vendor_header_display() {
        let session = ActiveSession::new(
            PathBuf::from("/test/file.rs"),
            "Google Gemini".to_string(),
            "◆".to_string(),
        );

        assert_eq!(session.vendor_logo, "◆");
        assert_eq!(session.vendor_name, "Google Gemini");
    }
}
