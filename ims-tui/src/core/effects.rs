use crate::app::{AppState, FocusPane};
use super::events::Event;

/// Effects are declarative intents, not executions
pub enum CommandEffect {
    /// Immediate state mutation (pure function)
    StateMutation(Box<dyn FnOnce(&mut AppState) + Send>),
    
    /// Spawn background task
    SpawnTask {
        task: Task,
        on_success: Option<Box<dyn FnOnce(TaskResult) -> Event + Send>>,
        on_error: Option<Box<dyn FnOnce(String) -> Event + Send>>,
    },
    
    /// Emit telemetry
    EmitEvent(TelemetryEvent),
    
    /// Show notification
    ShowNotification {
        level: NotificationLevel,
        message: String,
    },
    
    /// Navigate to pane
    FocusPane(FocusPane),
}

#[derive(Debug, Clone)]
pub enum Task {
    GenerateCode {
        file_path: std::path::PathBuf,
        vendor: String,
    },
    FetchMetrics,
    HealthCheck,
    ReadFile {
        path: std::path::PathBuf,
    },
    CopyToClipboard {
        text: String,
    },
    PasteFromClipboard,
}

#[derive(Debug, Clone)]
pub enum TaskResult {
    CodeGenerated {
        file_path: std::path::PathBuf,
        code: String,
    },
    MetricsFetched(crate::app::api::MetricsResponse),
    HealthChecked(crate::app::api::HealthResponse),
    FileContentLoaded {
        content: String,
    },
    ClipboardContentPasted {
        text: String,
    },
    Success,
}

#[derive(Debug, Clone)]
pub enum TelemetryEvent {
    CommandExecuted {
        id: &'static str,
    },
    AgentToken {
        token: String,
        usage: u32,
    },
}

#[derive(Debug, Clone)]
pub enum NotificationLevel {
    Info,
    Warning,
    Error,
}
