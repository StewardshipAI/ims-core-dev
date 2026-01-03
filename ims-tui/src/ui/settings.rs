//! Settings Overlay Modal

use crate::app::AppState;
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph},
    Frame,
};

pub fn render(f: &mut Frame, state: &AppState, area: Rect) {
    // Create centered popup
    let popup_area = centered_rect(60, 70, area);

    // Clear background
    f.render_widget(Clear, popup_area);

    // Split into sections
    let sections = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // Title
            Constraint::Min(0),     // Options
            Constraint::Length(3),  // Footer
        ])
        .split(popup_area);

    render_title(f, sections[0]);
    render_options(f, state, sections[1]);
    render_footer(f, sections[2]);
}

fn render_title(f: &mut Frame, area: Rect) {
    let title = Paragraph::new("⚙️  IMS-TUI Settings")
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .style(
            Style::default()
                .fg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );

    f.render_widget(title, area);
}

fn render_options(f: &mut Frame, state: &AppState, area: Rect) {
    let token_usage = format!("{} tokens", state.total_tokens_used);
    let total_cost = format!("${:.4}", state.total_cost);
    let debug_logs = format!("{} entries", state.debug_logs.len());

    let options = vec![
        ("Auto-scroll", if state.global_auto_scroll { "Enabled" } else { "Disabled" }),
        ("API Endpoint", state.api_base_url.as_str()),
        ("API Status", if state.api_connected { "🟢 Connected" } else { "🔴 Disconnected" }),
        ("Token Usage", token_usage.as_str()),
        ("Total Cost", total_cost.as_str()),
        ("Debug Logs", debug_logs.as_str()),
    ];

    let items: Vec<ListItem> = options
        .iter()
        .enumerate()
        .map(|(i, (label, value))| {
            let style = if i == state.settings_index {
                Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::Yellow)
            };

            ListItem::new(Line::from(vec![
                Span::styled(
                    format!("{:<20}", label),
                    style,
                ),
                Span::styled(
                    *value,
                    if i == state.settings_index { style } else { Style::default().fg(Color::White) },
                ),
            ]))
        })
        .collect();

    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Configuration")
                .border_style(Style::default().fg(Color::White)),
        );

    f.render_widget(list, area);
}

fn render_footer(f: &mut Frame, area: Rect) {
    let footer = Paragraph::new("Press Esc to close | Press R to refresh API connection")
        .alignment(Alignment::Center)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::DarkGray)),
        )
        .style(Style::default().fg(Color::Gray));

    f.render_widget(footer, area);
}

/// Helper to create a centered rect
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_centered_rect() {
        let screen = Rect::new(0, 0, 100, 50);
        let centered = centered_rect(60, 70, screen);

        assert_eq!(centered.width, 60);
        assert_eq!(centered.height, 35); // 70% of 50
    }
}
