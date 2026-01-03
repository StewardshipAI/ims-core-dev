//! Sidebar - File Explorer

use crate::app::{AppState, FileNode, FocusPane};
use crate::ui::focus_border_style;
use ratatui::{
    layout::Rect,
    style::{Color, Modifier, Style},
    text::Span,
    widgets::{Block, Borders},
    Frame,
};
use tui_tree_widget::{Tree, TreeItem};

pub fn render(f: &mut Frame, state: &AppState, area: Rect) {
    let is_focused = state.focus == FocusPane::Sidebar;

    // recursive helper to build tree items
    fn build_tree_items(nodes: &[FileNode]) -> Vec<TreeItem<String>> {
        nodes.iter().map(|node| {
            let label = Span::styled(
                if node.is_dir {
                    format!("📁 {}", node.name)
                } else {
                    format!("📄 {}", node.name)
                },
                if node.is_dir {
                    Style::default().fg(Color::Blue)
                } else {
                    Style::default().fg(Color::White)
                }
            );
            
            let children = build_tree_items(&node.children);
            TreeItem::new(node.id.clone(), label, children)
                .expect("Duplicate tree item ID")
        }).collect()
    }

    let items = build_tree_items(&state.file_tree);

    let tree = Tree::new(&items)
        .expect("Duplicate tree item ID")
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Explorer")
                .border_style(focus_border_style(is_focused)),
        )
        .highlight_style(
            Style::default()
                .bg(Color::DarkGray)
                .add_modifier(Modifier::BOLD),
        )
        .experimental_scrollbar(Some(
            ratatui::widgets::Scrollbar::default()
                .thumb_symbol("║")
                .track_symbol(None)
                .begin_symbol(None)
                .end_symbol(None),
        ));

    // Borrow mutable state from RefCell for rendering
    let mut tree_state = state.tree_state.borrow_mut();
    
    f.render_stateful_widget(tree, area, &mut *tree_state);
}