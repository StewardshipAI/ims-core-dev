use crate::app::FocusPane;
use super::effects::TelemetryEvent;

/// Events are facts that have occurred
#[derive(Debug, Clone)]
pub enum Event {
    // Agent Events
    AgentToken {
        token: String,
        usage: u32,
    },
    AgentCompleted {
        result: String,
    },
    AgentFailed {
        error: String,
    },
    
    // API Events
    MetricsUpdated(crate::app::api::MetricsResponse),
    HealthStatusChanged(String),
    
    // UI Events
    FileSelected(usize),
    PaneFocused(FocusPane),
    
    // File Events
    FileContentLoaded {
        content: String,
    },
    FileLoadFailed {
        error: String,
    },
    
    // Clipboard Events
    ClipboardUpdated {
        action: String,
    },
    ClipboardContentPasted {
        text: String,
    },
    ClipboardError {
        error: String,
    },
    
    // Signal Events
    SignalReceived(Signal),
    
    // Internal
    StateMutationRequested(Box<dyn FnOnce(&mut crate::app::AppState) + Send>),
    NotificationShown {
        level: super::effects::NotificationLevel,
        message: String,
    },
}

// Manual Debug implementation because FnOnce is not Debug
impl std::fmt::Debug for Event {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Event::AgentToken { token, usage } => f.debug_struct("AgentToken").field("token", token).field("usage", usage).finish(),
            Event::AgentCompleted { result } => f.debug_struct("AgentCompleted").field("result", result).finish(),
            Event::AgentFailed { error } => f.debug_struct("AgentFailed").field("error", error).finish(),
            Event::MetricsUpdated(m) => f.debug_tuple("MetricsUpdated").field(m).finish(),
            Event::HealthStatusChanged(s) => f.debug_tuple("HealthStatusChanged").field(s).finish(),
            Event::FileSelected(i) => f.debug_tuple("FileSelected").field(i).finish(),
            Event::PaneFocused(p) => f.debug_tuple("PaneFocused").field(p).finish(),
            Event::FileContentLoaded { content } => f.debug_struct("FileContentLoaded").field("content", content).finish(),
            Event::FileLoadFailed { error } => f.debug_struct("FileLoadFailed").field("error", error).finish(),
            Event::ClipboardUpdated { action } => f.debug_struct("ClipboardUpdated").field("action", action).finish(),
            Event::ClipboardContentPasted { text } => f.debug_struct("ClipboardContentPasted").field("text", text).finish(),
            Event::ClipboardError { error } => f.debug_struct("ClipboardError").field("error", error).finish(),
            Event::SignalReceived(s) => f.debug_tuple("SignalReceived").field(s).finish(),
            Event::StateMutationRequested(_) => f.debug_tuple("StateMutationRequested").finish(),
            Event::NotificationShown { level, message } => f.debug_struct("NotificationShown").field("level", level).field("message", message).finish(),
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub enum Signal {
    Interrupt,
    Terminate,
    Quit,
}
