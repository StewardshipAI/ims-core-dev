pub mod scroll;

use crate::app::{api::{ApiEvent, ExecuteRequest}, AppState, FocusPane, InputMode, FileNode};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers, MouseEvent, MouseEventKind};
use ratatui::layout::Rect;
use tokio::sync::mpsc;
use tui_tree_widget::TreeItem;

/// Handle mouse input
pub fn handle_mouse_event(state: &mut AppState, mouse: MouseEvent, terminal_size: Rect) -> bool {
    let col = mouse.column;
    let row = mouse.row;
    
    let sidebar_width = (terminal_size.width as f32 * 0.2) as u16;
    let inspector_start = (terminal_size.width as f32 * 0.8) as u16;
    
    // Check click-to-focus
    if mouse.kind == MouseEventKind::Down(crossterm::event::MouseButton::Left) {
        if col < sidebar_width {
            state.focus = FocusPane::Sidebar;
        } else if col >= inspector_start {
            state.focus = FocusPane::Inspector;
        } else {
            let prompt_start_y = terminal_size.height.saturating_sub(3);
            
            if row >= prompt_start_y {
                state.focus = FocusPane::Prompt;
                state.input_mode = InputMode::Editing;
            } else {
                let workspace_height = prompt_start_y;
                let mid_point = workspace_height / 2;
                
                if row < mid_point {
                    state.focus = FocusPane::Thinking;
                } else {
                    state.focus = FocusPane::Generation;
                }
            }
        }
    }

    match mouse.kind {
        MouseEventKind::ScrollDown => {
            match state.focus {
                FocusPane::Sidebar => {
                    state.tree_state.borrow_mut().key_down();
                }
                FocusPane::Thinking => {
                    if let Some(session) = &mut state.session {
                        session.thinking.manual_scroll(1);
                    }
                }
                FocusPane::Generation => {
                    if let Some(session) = &mut state.session {
                        session.generation.manual_scroll(1);
                    }
                }
                _ => {}
            }
        }
        MouseEventKind::ScrollUp => {
            match state.focus {
                FocusPane::Sidebar => {
                    state.tree_state.borrow_mut().key_up();
                }
                FocusPane::Thinking => {
                    if let Some(session) = &mut state.session {
                        session.thinking.manual_scroll(-1);
                    }
                }
                FocusPane::Generation => {
                    if let Some(session) = &mut state.session {
                        session.generation.manual_scroll(-1);
                    }
                }
                _ => {}
            }
        }
        _ => {}
    }
    true
}

/// Handle keyboard input
pub fn handle_key_event(
    state: &mut AppState, 
    key: KeyEvent,
    api_tx: &mpsc::UnboundedSender<ApiEvent>
) -> bool {
    if state.show_settings {
        return handle_settings_input(state, key);
    }
    
    if state.command_palette_visible {
        return handle_command_palette_input(state, key);
    }

    if state.input_mode == InputMode::Editing {
        match key.code {
            KeyCode::Esc => {
                state.input_mode = InputMode::Normal;
            }
            KeyCode::Enter => {
                let prompt = state.input_buffer.clone();
                if !prompt.trim().is_empty() {
                    state.prompt_history.push(prompt.clone());
                    state.add_thinking(format!("> User: {}", prompt));
                    state.add_thinking("Dispatching to IMS Core...".to_string());
                    
                    // Dispatch API call
                    if let Some(client) = state.api_client.clone() {
                        let tx = api_tx.clone();
                        let prompt_text = prompt.clone();
                        let model = state.session.as_ref().map(|s| s.model_id.clone()).unwrap_or("gpt-4o".to_string());
                        
                        tokio::spawn(async move {
                            let req = ExecuteRequest {
                                prompt: prompt_text,
                                model_id: model, // Should come from selection
                                max_tokens: Some(1024),
                                temperature: 0.7,
                                system_instruction: None,
                                user_id: Some("ims-tui-user".to_string()),
                                bypass_policies: false,
                            };
                            
                            match client.execute_prompt(req).await {
                                Ok(response) => {
                                    let _ = tx.send(ApiEvent::GenerationComplete(response));
                                }
                                Err(e) => {
                                    let _ = tx.send(ApiEvent::Error(format!("Prompt failed: {}", e)));
                                }
                            }
                        });
                    } else {
                        state.add_debug_log("Error: API Client not initialized".to_string());
                    }
                    
                    state.input_buffer.clear();
                }
                state.input_mode = InputMode::Normal;
            }
            KeyCode::Backspace => {
                state.input_buffer.pop();
            }
            KeyCode::Char(c) => {
                state.input_buffer.push(c);
            }
            _ => {}
        }
        return true;
    }

    match key.code {
        KeyCode::Char('q') | KeyCode::Char('Q') => {
            return false;
        }

        KeyCode::Char('s') | KeyCode::Char('S') => {
            state.show_settings = !state.show_settings;
        }
        
        KeyCode::Char('p') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            state.command_palette_visible = !state.command_palette_visible;
            state.command_input.clear();
            state.command_index = 0;
        }

        KeyCode::Tab => {
            state.cycle_focus();
        }

        KeyCode::Up => {
            handle_up(state);
        }

        KeyCode::Down => {
            handle_down(state);
        }
        
        KeyCode::Left => {
            if state.focus == FocusPane::Sidebar {
                state.tree_state.borrow_mut().key_left();
            }
        }
        
        KeyCode::Right => {
            if state.focus == FocusPane::Sidebar {
                state.tree_state.borrow_mut().key_right();
            }
        }

        KeyCode::Enter => {
            match state.focus {
                FocusPane::Sidebar => state.open_selected_file(),
                FocusPane::Prompt => state.input_mode = InputMode::Editing,
                _ => {}
            }
        }
        
        // File Management Shortcuts
        KeyCode::Char('n') => {
            if state.focus == FocusPane::Sidebar {
                state.add_debug_log("Creating new file...".to_string());
                let new_path = std::path::PathBuf::from(format!("new_file_{}.rs", state.file_tree.len() + 1));
                state.add_file(new_path);
            }
        }
        
        KeyCode::Delete => {
             if state.focus == FocusPane::Sidebar {
                 // Mock delete logic
                 state.add_debug_log("Mock: Deleted selected file".to_string());
             }
        }

        KeyCode::Char('a') | KeyCode::Char('A') => {
            state.global_auto_scroll = !state.global_auto_scroll;
            if let Some(session) = &mut state.session {
                if state.global_auto_scroll {
                    session.thinking.enable_auto_scroll();
                    session.generation.enable_auto_scroll();
                }
            }
        }

        KeyCode::Char('r') | KeyCode::Char('R') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            if let Some(session) = &mut state.session {
                session.reset_scroll();
                state.add_debug_log("Reset scroll states".to_string());
            }
        }

        _ => {}
    }

    true
}

fn handle_up(state: &mut AppState) {
    match state.focus {
        FocusPane::Sidebar => {
            state.tree_state.borrow_mut().key_up();
        }
        FocusPane::Thinking => {
            if let Some(session) = &mut state.session {
                session.thinking.manual_scroll(-1);
            }
        }
        FocusPane::Generation => {
            if let Some(session) = &mut state.session {
                session.generation.manual_scroll(-1);
            }
        }
        FocusPane::Inspector | FocusPane::Prompt => {}
    }
}

fn handle_down(state: &mut AppState) {
    match state.focus {
        FocusPane::Sidebar => {
            state.tree_state.borrow_mut().key_down();
        }
        FocusPane::Thinking => {
            if let Some(session) = &mut state.session {
                session.thinking.manual_scroll(1);
            }
        }
        FocusPane::Generation => {
            if let Some(session) = &mut state.session {
                session.generation.manual_scroll(1);
            }
        }
        FocusPane::Inspector | FocusPane::Prompt => {}
    }
}

fn handle_settings_input(state: &mut AppState, key: KeyEvent) -> bool {
    let option_count = 6; 

    match key.code {
        KeyCode::Esc => {
            state.show_settings = false;
        }
        KeyCode::Char('q') | KeyCode::Char('Q') => {
            return false; 
        }
        KeyCode::Up => {
            if state.settings_index > 0 {
                state.settings_index -= 1;
            } else {
                state.settings_index = option_count - 1;
            }
        }
        KeyCode::Down => {
            state.settings_index = (state.settings_index + 1) % option_count;
        }
        KeyCode::Enter => {
            match state.settings_index {
                0 => { // Auto-scroll
                    state.global_auto_scroll = !state.global_auto_scroll;
                    if let Some(session) = &mut state.session {
                        if state.global_auto_scroll {
                            session.thinking.enable_auto_scroll();
                            session.generation.enable_auto_scroll();
                        }
                    }
                }
                2 => { // API Status (Reconnect)
                    state.api_connected = false;
                }
                _ => {}
            }
        }
        _ => {}
    }

    true
}

fn handle_command_palette_input(state: &mut AppState, key: KeyEvent) -> bool {
    match key.code {
        KeyCode::Esc => {
            state.command_palette_visible = false;
        }
        KeyCode::Up => {
            if state.command_index > 0 {
                state.command_index -= 1;
            }
        }
        KeyCode::Down => {
            state.command_index += 1; // Simplified bounds check
        }
        KeyCode::Enter => {
            // Execute selected command (Mock)
            state.command_palette_visible = false;
            state.add_debug_log(format!("Executed command index: {}", state.command_index));
            // Actual dispatch logic would go here
        }
        KeyCode::Backspace => {
            state.command_input.pop();
        }
        KeyCode::Char(c) => {
            state.command_input.push(c);
        }
        _ => {}
    }
    true
}