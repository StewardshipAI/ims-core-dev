use crate::app::AppState;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph},
    Frame,
};

pub fn render(f: &mut Frame, state: &AppState, area: Rect) {
    let area = centered_rect(60, 40, area);
    f.render_widget(Clear, area);

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Input box
            Constraint::Min(0),    // List of commands
        ])
        .split(area);

    // Input Box
    let input = Paragraph::new(state.command_input.as_str())
        .style(Style::default().fg(Color::Yellow))
        .block(Block::default().borders(Borders::ALL).title("Command Palette"));
    f.render_widget(input, chunks[0]);
    
    // Commands List
    // For now, hardcode list. Later, use a registry.
    let commands = vec![
        "File: New File",
        "File: Open...",
        "File: Save",
        "View: Toggle Sidebar",
        "View: Toggle Inspector",
        "Agent: Reset Session",
        "System: Quit",
    ];

    let filtered_commands: Vec<&str> = commands
        .into_iter()
        .filter(|cmd| cmd.to_lowercase().contains(&state.command_input.to_lowercase()))
        .collect();

    let items: Vec<ListItem> = filtered_commands
        .iter()
        .enumerate()
        .map(|(i, cmd)| {
            let style = if i == state.command_index {
                Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };
            ListItem::new(Line::from(vec![Span::styled(*cmd, style)]))
        })
        .collect();

    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL));
    
    f.render_widget(list, chunks[1]);
}

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
