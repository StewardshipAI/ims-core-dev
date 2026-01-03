//! UI Rendering Module
//!
//! Implements VS Code-inspired 3-column layout:
//! [Sidebar (20%) | Center Workspace (60%) | Inspector (20%)]

pub mod editor;
pub mod inspector;
pub mod settings;
pub mod sidebar;
pub mod command_palette;

use crate::app::{AppState, FocusPane, InputMode};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph},
    Frame,
};

/// Main render function - called every frame
pub fn render(f: &mut Frame, state: &AppState) {
    let size = f.area();

    // Create 3-column layout
    let main_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(20), // Sidebar
            Constraint::Percentage(60), // Center Workspace
            Constraint::Percentage(20), // Inspector
        ])
        .split(size);

    // Render each column
    sidebar::render(f, state, main_layout[0]);
    render_center_workspace(f, state, main_layout[1]);
    inspector::render(f, state, main_layout[2]);

    // Render overlays
    if state.show_settings {
        settings::render(f, state, size);
    }
    
    if state.command_palette_visible {
        command_palette::render(f, state, size);
    }
}

/// Render center workspace (thinking + generation + prompt)
fn render_center_workspace(f: &mut Frame, state: &AppState, area: Rect) {
    // Split center into Content (Top) and Prompt (Bottom)
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Min(0),    // Content (Thinking/Generation or Welcome)
            Constraint::Length(3), // Prompt (Fixed height)
        ])
        .split(area);

    let content_area = layout[0];
    let prompt_area = layout[1];

    // Render Content Area
    if state.session.is_none() {
        render_welcome_screen(f, content_area);
    } else {
        // Split content into Thinking and Generation
        let workspace_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Percentage(50),
                Constraint::Percentage(50),
            ])
            .split(content_area);

        editor::render_thinking_pane(f, state, workspace_layout[0]);
        editor::render_generation_pane(f, state, workspace_layout[1]);
    }

    // Always render Prompt Box
    editor::render_prompt_box(f, state, prompt_area);
}

/// Welcome screen (shown when no file is open)
fn render_welcome_screen(f: &mut Frame, area: Rect) {
    let logo = vec![
        "██╗███╗   ███╗███████╗",
        "██║████╗ ████║██╔════╝",
        "██║██╔████╔██║███████╗",
        "██║██║╚██╔╝██║╚════██║",
        "██║██║ ╚═╝ ██║███████║",
        "╚═╝╚═╝     ╚═╝╚══════╝",
        "",
        "INTELLIGENT MODEL SWITCHING",
        "MULTI-VENDOR FRAMEWORK: GOOGLE • ANTHROPIC • OPENAI",
        "",
        "Press ↑/↓ to navigate files, Enter to open",
        "Press S for settings, Q to quit",
    ];

    let lines: Vec<Line> = logo
        .iter()
        .map(|&line| {
            Line::from(Span::styled(
                line,
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ))
        })
        .collect();

    let welcome = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Welcome to IMS-TUI")
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .alignment(ratatui::layout::Alignment::Center);

    f.render_widget(welcome, area);
}

/// Render status bar at bottom
pub fn render_status_bar(f: &mut Frame, state: &AppState, area: Rect) {
    let status_text = if state.api_connected {
        format!(
            "🟢 API Connected | Files: {} | Tokens: {} | Cost: ${:.4} | Focus: {:?}",
            state.file_tree.len(),
            state.total_tokens_used,
            state.total_cost,
            state.focus
        )
    } else {
        "🔴 API Disconnected - Waiting for backend...".to_string()
    };

    let status_bar = Paragraph::new(status_text)
        .style(
            Style::default()
                .bg(Color::DarkGray)
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )
        .block(Block::default());

    f.render_widget(status_bar, area);
}

/// Render keybinding hints
pub fn render_keybindings(area: Rect) -> Paragraph<'static> {
    let hints = vec![
        "↑/↓: Navigate",
        "Enter: Open",
        "Tab: Cycle Focus",
        "S: Settings",
        "Q: Quit",
    ];

    let text: Vec<Line> = hints
        .iter()
        .map(|&hint| {
            Line::from(Span::styled(
                hint,
                Style::default()
                    .fg(Color::Gray)
                    .add_modifier(Modifier::ITALIC),
            ))
        })
        .collect();

    Paragraph::new(text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Keybindings")
                .border_style(Style::default().fg(Color::DarkGray)),
        )
}

/// Get focus border style
pub fn focus_border_style(is_focused: bool) -> Style {
    if is_focused {
        Style::default()
            .fg(Color::Cyan)
            .add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::DarkGray)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_focus_border_style() {
        let focused = focus_border_style(true);
        let unfocused = focus_border_style(false);

        assert_eq!(focused.fg, Some(Color::Cyan));
        assert_eq!(unfocused.fg, Some(Color::DarkGray));
    }
}
