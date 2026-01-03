//! Inspector Panel - Metrics & Stats

use crate::app::{AppState, FocusPane};
use crate::ui::focus_border_style;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph},
    Frame,
};

pub fn render(f: &mut Frame, state: &AppState, area: Rect) {
    let is_focused = state.focus == FocusPane::Inspector;

    // Split inspector into sections
    let sections = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(6),  // Session info
            Constraint::Length(8),  // Metrics
            Constraint::Length(6),  // Active models
            Constraint::Min(0),     // Debug logs
        ])
        .split(area);

    render_session_info(f, state, sections[0], is_focused);
    render_metrics(f, state, sections[1], is_focused);
    render_active_models(f, state, sections[2], is_focused);
    render_debug_logs(f, state, sections[3], is_focused);
}

/// Session information
fn render_session_info(f: &mut Frame, state: &AppState, area: Rect, is_focused: bool) {
    let info = if let Some(session) = &state.session {
        vec![
            Line::from(vec![
                Span::raw("Vendor: "),
                Span::styled(
                    format!("{} {}", session.vendor_logo, session.vendor_name),
                    Style::default().fg(Color::Cyan),
                ),
            ]),
            Line::from(vec![
                Span::raw("File: "),
                Span::styled(
                    session
                        .file_path
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("unknown"),
                    Style::default().fg(Color::Yellow),
                ),
            ]),
            Line::from(vec![
                Span::raw("Status: "),
                Span::styled(
                    if state.api_connected {
                        "🟢 Connected"
                    } else {
                        "🔴 Disconnected"
                    },
                    Style::default().fg(if state.api_connected {
                        Color::Green
                    } else {
                        Color::Red
                    }),
                ),
            ]),
        ]
    } else {
        vec![
            Line::from(Span::styled(
                "No active session",
                Style::default().fg(Color::DarkGray),
            )),
            Line::from(""),
            Line::from(Span::styled(
                "Press Enter to open a file",
                Style::default().fg(Color::Gray),
            )),
        ]
    };

    let paragraph = Paragraph::new(info).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Session")
            .border_style(focus_border_style(is_focused)),
    );

    f.render_widget(paragraph, area);
}

/// Metrics panel
fn render_metrics(f: &mut Frame, state: &AppState, area: Rect, is_focused: bool) {
    let metrics_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2), // Tokens
            Constraint::Length(2), // Cost
            Constraint::Length(2), // Requests
        ])
        .split(area);

    // Token usage gauge
    let token_percent = ((state.total_tokens_used as f64 / 1_000_000.0) * 100.0).min(100.0);
    let token_gauge = Gauge::default()
        .block(Block::default().title("Tokens"))
        .gauge_style(Style::default().fg(Color::Cyan))
        .percent(token_percent as u16)
        .label(format!(
            "{:.2}M / 1M",
            state.total_tokens_used as f64 / 1_000_000.0
        ));

    // Cost display
    let cost_text = format!(
        "Total Cost: ${:.4}",
        state.total_cost
    );
    let cost_para = Paragraph::new(cost_text)
        .block(Block::default())
        .style(Style::default().fg(if state.total_cost > 1.0 {
            Color::Red
        } else {
            Color::Green
        }));

    // Request count
    let req_text = format!(
        "Requests: {} (Limit: 1500/day)",
        state.request_count
    );
    let req_para = Paragraph::new(req_text)
        .block(Block::default())
        .style(Style::default().fg(Color::Yellow));

    let metrics_block = Block::default()
        .borders(Borders::ALL)
        .title("Metrics")
        .border_style(focus_border_style(is_focused));

    f.render_widget(metrics_block, area);
    f.render_widget(token_gauge, metrics_layout[0]);
    f.render_widget(cost_para, metrics_layout[1]);
    f.render_widget(req_para, metrics_layout[2]);
}

/// Active models list
fn render_active_models(f: &mut Frame, state: &AppState, area: Rect, is_focused: bool) {
    let items: Vec<ListItem> = if state.active_models.is_empty() {
        vec![ListItem::new(Line::from(Span::styled(
            "No active models",
            Style::default().fg(Color::DarkGray),
        )))]
    } else {
        state
            .active_models
            .iter()
            .map(|model| {
                ListItem::new(Line::from(Span::styled(
                    format!("• {}", model),
                    Style::default().fg(Color::Green),
                )))
            })
            .collect()
    };

    let list = List::new(items).block(
        Block::default()
            .borders(Borders::ALL)
            .title("Active Models")
            .border_style(focus_border_style(is_focused)),
    );

    f.render_widget(list, area);
}

/// Debug logs (last 10 entries)
fn render_debug_logs(f: &mut Frame, state: &AppState, area: Rect, is_focused: bool) {
    let log_count = state.debug_logs.len();
    let visible_logs = area.height.saturating_sub(2) as usize;

    let logs: Vec<Line> = state
        .debug_logs
        .iter()
        .rev()
        .take(visible_logs)
        .rev()
        .map(|log| {
            Line::from(Span::styled(
                log.clone(),
                Style::default().fg(Color::Gray),
            ))
        })
        .collect();

    let paragraph = Paragraph::new(logs).block(
        Block::default()
            .borders(Borders::ALL)
            .title(format!("Debug Logs ({})", log_count))
            .border_style(focus_border_style(is_focused)),
    );

    f.render_widget(paragraph, area);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_token_percentage_calculation() {
        let tokens: u64 = 500_000;
        let percent = ((tokens as f64 / 1_000_000.0) * 100.0).min(100.0);
        assert_eq!(percent, 50.0);
    }

    #[test]
    fn test_cost_color() {
        let low_cost = 0.5;
        let high_cost = 1.5;

        let low_color = if low_cost > 1.0 { Color::Red } else { Color::Green };
        let high_color = if high_cost > 1.0 { Color::Red } else { Color::Green };

        assert_eq!(low_color, Color::Green);
        assert_eq!(high_color, Color::Red);
    }
}
