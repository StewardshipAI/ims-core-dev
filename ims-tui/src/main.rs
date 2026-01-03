//! IMS-TUI: Terminal User Interface for Intelligent Model Switching
//!
//! A high-performance, VS Code-inspired TUI for managing AI model selection,
//! monitoring metrics, and orchestrating multi-agent workflows.

mod app;
mod handlers;
mod ui;

use anyhow::{Context, Result};
use app::{api::ImsApiClient, AppState};
use crossterm::{
    event::{self, Event, MouseEvent},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, layout::Rect, Terminal};
use std::{
    io,
    path::PathBuf,
    time::{Duration, Instant},
};
use tokio::sync::mpsc;
use tracing::{error, info, warn};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("ims_tui=debug")
        .with_target(false)
        .with_thread_ids(false)
        .with_file(true)
        .with_line_number(true)
        .init();

    info!("Starting IMS-TUI v1.0.0");

    // Load configuration
    dotenv::dotenv().ok();
    let api_base_url = std::env::var("IMS_API_URL").unwrap_or_else(|_| "http://localhost:8000".to_string());
    let admin_api_key = std::env::var("ADMIN_API_KEY").ok();

    info!("API URL: {}", api_base_url);

    // Setup terminal
    enable_raw_mode().context("Failed to enable raw mode")?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, event::EnableMouseCapture).context("Failed to enter alternate screen")?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend).context("Failed to create terminal")?;

    // Initialize application state
    let mut app_state = AppState::new(api_base_url.clone());

    // Add demo files for testing
    app_state.add_file(PathBuf::from("/workspace/src/main.rs"));
    app_state.add_file(PathBuf::from("/workspace/src/app.rs"));
    app_state.add_file(PathBuf::from("/workspace/README.md"));

    // Initialize API client (Mock Mode = true)
    let api_client = ImsApiClient::new(api_base_url.clone(), admin_api_key.clone(), true)
        .context("Failed to create API client")?;
    
    app_state.api_client = Some(api_client.clone());

    // Test API connection
    match api_client.health_check().await {
        Ok(health) => {
            info!("API Health: {:?}", health);
            app_state.api_connected = true;
            app_state.add_debug_log("API connected successfully (Mock)".to_string());
        }
        Err(e) => {
            warn!("API connection failed: {}", e);
            app_state.add_debug_log(format!("API connection failed: {}", e));
        }
    }

    // Setup background tasks
    let (api_tx, mut api_rx) = mpsc::unbounded_channel();
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // Spawn metrics poller
    if app_state.api_connected {
        let client_clone = ImsApiClient::new(api_base_url.clone(), admin_api_key.clone(), true)?;
        let tx_clone = api_tx.clone();
        let rx_clone = shutdown_rx.clone();
        
        tokio::spawn(async move {
            app::api::metrics_poller(client_clone, tx_clone, rx_clone).await;
        });

        info!("Started metrics poller");
    }

    // Main event loop
    let result = run_event_loop(&mut terminal, &mut app_state, &mut api_rx, api_tx.clone()).await;

    // Cleanup
    info!("Shutting down...");
    let _ = shutdown_tx.send(true);
    
    disable_raw_mode().context("Failed to disable raw mode")?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen, event::DisableMouseCapture)
        .context("Failed to leave alternate screen")?;
    terminal.show_cursor().context("Failed to show cursor")?;

    info!("IMS-TUI exited");
    
    result
}

/// Main event loop
async fn run_event_loop(
    terminal: &mut Terminal<CrosstermBackend<io::Stdout>>,
    state: &mut AppState,
    api_rx: &mut mpsc::UnboundedReceiver<app::api::ApiEvent>,
    api_tx: mpsc::UnboundedSender<app::api::ApiEvent>,
) -> Result<()> {
    let tick_rate = Duration::from_millis(100);
    let mut last_tick = Instant::now();

    loop {
        // Render UI
        terminal.draw(|f| {
            ui::render(f, state);
        })?;

        // Handle events
        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if event::poll(timeout)? {
            match event::read()? {
                Event::Key(key) => {
                    if !handlers::handle_key_event(state, key, &api_tx) {
                        break; // User quit
                    }
                }
                Event::Mouse(mouse) => {
                    if let Ok(size) = terminal.size() {
                        let rect = Rect {
                            x: 0,
                            y: 0,
                            width: size.width,
                            height: size.height,
                        };
                        handlers::handle_mouse_event(state, mouse, rect);
                    }
                }
                _ => {}
            }
        }

        // Handle API events
        while let Ok(api_event) = api_rx.try_recv() {
            match api_event {
                app::api::ApiEvent::MetricsUpdate(metrics) => {
                    if let Some(total) = metrics.total_models_registered {
                        state.add_debug_log(format!("Models registered: {}", total));
                    }
                }
                app::api::ApiEvent::HealthUpdate(health) => {
                    state.api_connected = health.status.contains("healthy");
                    state.add_debug_log(format!("Health: {}", health.status));
                }
                app::api::ApiEvent::GenerationComplete(response) => {
                    state.append_generation(&response.content);
                    state.add_thinking(format!("Finished in {:.2}ms. Tokens: {} (Cost: ${:.6})", 
                        response.latency_ms, 
                        response.tokens.total, 
                        response.cost.total
                    ));
                    state.total_tokens_used += response.tokens.total as u64;
                    state.total_cost += response.cost.total;
                }
                app::api::ApiEvent::Error(err) => {
                    error!("API Error: {}", err);
                    state.add_debug_log(format!("API Error: {}", err));
                }
            }
        }

        // Periodic tick
        if last_tick.elapsed() >= tick_rate {
            // Update state (e.g., simulate agent activity)
            // simulate_agent_activity(state); // Disabled to stop spam
            last_tick = Instant::now();
        }
    }

    Ok(())
}

/// Simulate agent activity for demo purposes (Disabled)
fn simulate_agent_activity(state: &mut AppState) {
    if let Some(session) = &mut state.session {
        // Simulate thinking logs
        if state.thinking_log.len() < 50 {
            let timestamp = chrono::Local::now().format("%H:%M:%S");
            state.add_thinking(format!("[{}] Analyzing code structure...", timestamp));
        }

        // Simulate code generation
        if state.generated_code.len() < 1000 {
            state.append_generation("// Generated code\n");
            state.append_generation("fn example() {\n");
            state.append_generation("    println!(\"Hello, IMS!\");\n");
            state.append_generation("}\n");
        }

        // Update token usage
        state.total_tokens_used += 10;
        state.total_cost = state.total_tokens_used as f64 * 0.000001;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api_url_default() {
        std::env::remove_var("IMS_API_URL");
        let url = std::env::var("IMS_API_URL").unwrap_or_else(|_| "http://localhost:8000".to_string());
        assert_eq!(url, "http://localhost:8000");
    }

    #[test]
    fn test_simulation() {
        let mut state = AppState::default();
        state.open_selected_file(); // No files, should be safe

        simulate_agent_activity(&mut state);
        
        // Should not crash
    }
}
