//! Application State Management
//!
//! This module defines the core data structures for IMS-TUI.
//! It maintains strict separation between UI state and business logic.

pub mod api;

use std::collections::HashMap;
use std::path::PathBuf;
use std::cell::RefCell;
use serde::{Deserialize, Serialize};
use ratatui::layout::Rect;
use tui_tree_widget::TreeState;

/// Agent execution status
#[derive(Clone, Copy, PartialEq, Eq, Debug, Serialize, Deserialize)]
pub enum AgentStatus {
    Working,
    Idle,
    Error,
    Paused,
}

impl AgentStatus {
    pub fn emoji(&self) -> &'static str {
        match self {
            AgentStatus::Working => "🟢",
            AgentStatus::Idle => "⚪",
            AgentStatus::Error => "🔴",
            AgentStatus::Paused => "🟡",
        }
    }

    pub fn color(&self) -> ratatui::style::Color {
        use ratatui::style::Color;
        match self {
            AgentStatus::Working => Color::Green,
            AgentStatus::Idle => Color::Gray,
            AgentStatus::Error => Color::Red,
            AgentStatus::Paused => Color::Yellow,
        }
    }
}

/// File System Node (File or Directory)
#[derive(Clone, Debug)]
pub struct FileNode {
    pub id: String,
    pub name: String,
    pub path: PathBuf,
    pub is_dir: bool,
    pub children: Vec<FileNode>,
    pub status: AgentStatus,
    pub tokens: u32,
    pub model: String,
}

impl FileNode {
    pub fn new_file(path: PathBuf) -> Self {
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("unknown").to_string();
        Self {
            id: path.to_string_lossy().to_string(),
            name,
            path,
            is_dir: false,
            children: Vec::new(),
            status: AgentStatus::Idle,
            tokens: 0,
            model: "gpt-4o".to_string(),
        }
    }

    pub fn new_dir(path: PathBuf) -> Self {
        let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("unknown").to_string();
        Self {
            id: path.to_string_lossy().to_string(),
            name,
            path,
            is_dir: true,
            children: Vec::new(),
            status: AgentStatus::Idle,
            tokens: 0,
            model: "".to_string(),
        }
    }
}

/// Scroll behavior for a pane
#[derive(Clone, Debug)]
pub struct ScrollState {
    pub auto_scroll: bool,
    pub scroll_offset: u16,
}

impl Default for ScrollState {
    fn default() -> Self {
        Self {
            auto_scroll: true,
            scroll_offset: 0,
        }
    }
}

impl ScrollState {
    pub fn manual_scroll(&mut self, delta: i16) {
        self.auto_scroll = false;
        if delta > 0 {
            self.scroll_offset = self.scroll_offset.saturating_add(delta as u16);
        } else {
            self.scroll_offset = self.scroll_offset.saturating_sub(delta.abs() as u16);
        }
    }

    pub fn enable_auto_scroll(&mut self) {
        self.auto_scroll = true;
        self.scroll_offset = 0;
    }
}

/// Active agent session
#[derive(Clone, Debug)]
pub struct ActiveSession {
    /// Path to file being processed
    pub file_path: PathBuf,
    /// Vendor name (e.g., "Google Gemini", "Anthropic Claude")
    pub vendor_name: String,
    /// Vendor logo character (e.g., "▲" for Anthropic, "●" for OpenAI)
    pub vendor_logo: String,
    /// Model ID
    pub model_id: String,
    /// Scroll state for thinking pane
    pub thinking: ScrollState,
    /// Scroll state for generation pane
    pub generation: ScrollState,
}

impl ActiveSession {
    pub fn new(file_path: PathBuf, vendor_name: String, vendor_logo: String, model_id: String) -> Self {
        Self {
            file_path,
            vendor_name,
            vendor_logo,
            model_id,
            thinking: ScrollState::default(),
            generation: ScrollState::default(),
        }
    }

    pub fn reset_scroll(&mut self) {
        self.thinking.enable_auto_scroll();
        self.generation.enable_auto_scroll();
    }
}

/// Focus target for keyboard navigation
#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
pub enum FocusPane {
    Sidebar,
    Thinking,
    Generation,
    Inspector,
    Prompt,
}

/// Input mode for the prompt box
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum InputMode {
    Normal,
    Editing,
}

use crate::app::api::ImsApiClient;

/// Main application state
pub struct AppState {
    // File Management (Tree)
    pub file_tree: Vec<FileNode>,
    pub tree_state: RefCell<TreeState<String>>,

    // Active Session
    pub session: Option<ActiveSession>,

    // Content Buffers
    pub thinking_log: Vec<String>,
    pub generated_code: String,
    pub meta_prompt: String,

    // Prompt Input
    pub input_mode: InputMode,
    pub input_buffer: String,
    pub prompt_history: Vec<String>,

    // UI State
    pub global_auto_scroll: bool,
    pub show_settings: bool,
    pub settings_index: usize,
    pub command_palette_visible: bool,
    pub command_input: String,
    pub command_index: usize,
    pub focus: FocusPane,
    pub pane_areas: HashMap<FocusPane, Rect>,

    // Metrics & Stats
    pub total_tokens_used: u64,
    pub total_cost: f64,
    pub active_models: Vec<String>,
    pub request_count: u32,

    // Debug & Logs
    pub debug_logs: Vec<String>,

    // Backend Connection
    pub api_base_url: String,
    pub api_connected: bool,
    pub api_client: Option<ImsApiClient>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            file_tree: Vec::new(),
            tree_state: RefCell::new(TreeState::default()),
            session: None,
            thinking_log: Vec::new(),
            generated_code: String::new(),
            meta_prompt: String::new(),
            input_mode: InputMode::Normal,
            input_buffer: String::new(),
            prompt_history: Vec::new(),
            global_auto_scroll: true,
            show_settings: false,
            settings_index: 0,
            command_palette_visible: false,
            command_input: String::new(),
            command_index: 0,
            focus: FocusPane::Sidebar,
            pane_areas: HashMap::new(),
            total_tokens_used: 0,
            total_cost: 0.0,
            active_models: Vec::new(),
            request_count: 0,
            debug_logs: Vec::new(),
            api_base_url: "http://localhost:8000".to_string(),
            api_connected: false,
            api_client: None,
        }
    }
}

impl AppState {
    pub fn new(api_base_url: String) -> Self {
        Self {
            api_base_url,
            ..Default::default()
        }
    }

    fn find_node_recursive<'a>(nodes: &'a [FileNode], id: &str) -> Option<&'a FileNode> {
        for node in nodes {
            if node.id == id {
                return Some(node);
            }
            if let Some(found) = Self::find_node_recursive(&node.children, id) {
                return Some(found);
            }
        }
        None
    }

    pub fn get_selected_node(&self) -> Option<&FileNode> {
        if let Some(selected_ids) = self.tree_state.borrow().selected().last() {
            return Self::find_node_recursive(&self.file_tree, selected_ids);
        }
        None
    }
    
    pub fn open_selected_file(&mut self) {
        let selected_id = self.tree_state.borrow().selected().last().cloned();
        
        if let Some(id) = selected_id {
            if let Some(node) = Self::find_node_recursive(&self.file_tree, &id) {
                if !node.is_dir {
                    let path = node.path.clone();
                    let name = node.name.clone();
                    let model = node.model.clone();

                    let vendor = if model.contains("gemini") {
                        ("Google Gemini".to_string(), "◆".to_string())
                    } else if model.contains("claude") {
                        ("Anthropic Claude".to_string(), "▲".to_string())
                    } else if model.contains("gpt") {
                        ("OpenAI GPT".to_string(), "●".to_string())
                    } else {
                        ("Unknown Vendor".to_string(), "?".to_string())
                    };

                    let mut session = ActiveSession::new(path, vendor.0, vendor.1, model);
                    session.reset_scroll();
                    self.session = Some(session);
                    self.thinking_log.clear();
                    self.generated_code.clear();
                    self.add_debug_log(format!("Opened file: {}", name));
                } else {
                     self.tree_state.borrow_mut().toggle(vec![id.clone()]);
                }
            }
        }
    }

    // Stub for old method signature
    pub fn add_file(&mut self, path: PathBuf) {
        self.file_tree.push(FileNode::new_file(path));
    }

    pub fn cycle_focus(&mut self) {
        self.focus = match self.focus {
            FocusPane::Sidebar => FocusPane::Thinking,
            FocusPane::Thinking => FocusPane::Generation,
            FocusPane::Generation => FocusPane::Prompt,
            FocusPane::Prompt => FocusPane::Inspector,
            FocusPane::Inspector => FocusPane::Sidebar,
        };
    }
    
    pub fn add_debug_log(&mut self, message: String) {
        let timestamp = chrono::Local::now().format("%H:%M:%S");
        self.debug_logs.push(format!("[{}] {}", timestamp, message));
        if self.debug_logs.len() > 100 {
            self.debug_logs.drain(0..10);
        }
    }

    pub fn add_thinking(&mut self, line: String) {
        self.thinking_log.push(line);
        if self.thinking_log.len() > 1000 {
            self.thinking_log.drain(0..100);
        }
    }

    pub fn append_generation(&mut self, text: &str) {
        self.generated_code.push_str(text);
    }
}