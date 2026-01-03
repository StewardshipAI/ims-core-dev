use crate::app::AppState;
use super::effects::CommandEffect;

pub struct CommandContext {
    pub selected_vendor: String,
}

impl Default for CommandContext {
    fn default() -> Self {
        Self {
            selected_vendor: "google".to_string(),
        }
    }
}

pub struct Command {
    pub id: &'static str,
    pub title: &'static str,
    
    /// Pure function: no side effects, no async
    pub handler: Box<dyn Fn(&AppState, CommandContext) -> Vec<CommandEffect> + Send + Sync>,
}

impl Command {
    /// Safe execution: returns effects, doesn't mutate
    pub fn execute(&self, state: &AppState, ctx: CommandContext) -> Vec<CommandEffect> {
        (self.handler)(state, ctx)
    }
}
