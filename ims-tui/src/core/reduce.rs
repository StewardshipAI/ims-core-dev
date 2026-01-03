use crate::app::AppState;
use super::events::{Event, Signal};

/// Central reducer: applies events to state
pub fn reduce(state: &mut AppState, event: Event) {
    match event {
        Event::AgentToken { token, usage } => {
            state.thinking_log.push(format!("Token: {}", token));
            state.total_tokens_used += usage as u64;
        }
        
        Event::FileSelected(index) => {
            state.selected_file_index = index;
        }
        
        Event::MetricsUpdated(metrics) => {
            if let Some(total) = metrics.total_models_registered {
                state.add_debug_log(format!("Models registered: {}", total));
            }
        }
        
        Event::HealthStatusChanged(status) => {
            state.api_connected = status == "healthy";
            state.add_debug_log(format!("Health: {}", status));
        }
        
        Event::StateMutationRequested(mutation) => {
            mutation(state);
        }
        
        Event::SignalReceived(Signal::Interrupt) => {
            state.add_debug_log("Signal Interrupt received".to_string());
            // Logic to cancel agent or exit would go here
        }
        
        _ => {
            // Unhandled events
        }
    }
}
