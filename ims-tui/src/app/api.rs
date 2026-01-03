//! Backend API Integration
//!
//! Handles communication with IMS Core FastAPI backend:
//! - Model Registry (Swagger UI endpoints)
//! - Metrics API (Grafana data source)
//! - Telemetry Bus (RabbitMQ streams)

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// API Client for IMS Core Backend

#[derive(Clone)]

pub struct ImsApiClient {

    client: reqwest::Client,

    base_url: String,

    admin_api_key: Option<String>,

    mock_mode: bool,

}



impl ImsApiClient {

    pub fn new(base_url: String, admin_api_key: Option<String>, mock_mode: bool) -> Result<Self> {

        let client = reqwest::Client::builder()

            .timeout(Duration::from_secs(30))

            .build()

            .context("Failed to create HTTP client")?;



        Ok(Self {

            client,

            base_url,

            admin_api_key,

            mock_mode,

        })

    }



    /// Health check endpoint

    pub async fn health_check(&self) -> Result<HealthResponse> {

        if self.mock_mode {

            return Ok(HealthResponse {

                status: "healthy (mock)".to_string(),

                database: "connected".to_string(),

                cache: "connected".to_string(),

                rabbitmq: Some("connected".to_string()),

            });

        }

        let url = format!("{}/health", self.base_url);

        let response = self.client.get(&url).send().await?;



        if response.status().is_success() {

            Ok(response.json().await?)

        } else {

            Err(anyhow::anyhow!("Health check failed: {}", response.status()))

        }

    }



    /// Get system metrics

    pub async fn get_metrics(&self) -> Result<MetricsResponse> {

        if self.mock_mode {

            return Ok(MetricsResponse {

                total_models_registered: Some(10),

                total_model_queries: Some(1234),

                total_filter_queries: Some(56),

            });

        }

        let url = format!("{}/metrics", self.base_url);

        

        let mut request = self.client.get(&url);

        

        if let Some(key) = &self.admin_api_key {

            request = request.header("X-Admin-Key", key);

        }



        let response = request.send().await?;



        if response.status().is_success() {

            Ok(response.json().await?)

        } else {

            Err(anyhow::anyhow!("Metrics fetch failed: {}", response.status()))

        }

    }



    // ... filter_models, get_model, get_recommendations (keep as is or mock if needed) ...



    /// Execute prompt via Action Gateway

    pub async fn execute_prompt(&self, req: ExecuteRequest) -> Result<ExecuteResponse> {

        if self.mock_mode {

            // Simulate network delay

            tokio::time::sleep(Duration::from_millis(800)).await;

            

            return Ok(ExecuteResponse {

                content: format!("(Mock Response) I received your prompt: \"{}\"\n\nHere is a simulated Python function:\n\n```python\ndef hello_world():\n    print(\"Hello from IMS Mock Mode!\")\n```", req.prompt),

                model_id: req.model_id,

                tokens: TokenUsage { input: 10, output: 20, total: 30 },

                cost: CostUsage { input: 0.0001, output: 0.0002, total: 0.0003 },

                latency_ms: 800.0,

            });

        }



        let url = format!("{}/api/v1/execute", self.base_url);

        

        let mut request = self.client.post(&url).json(&req);

        

        if let Some(key) = &self.admin_api_key {

            request = request.header("X-Admin-Key", key);

        }



        let response = request.send().await?;



        if response.status().is_success() {

            Ok(response.json().await?)

        } else {

            Err(anyhow::anyhow!("Execution failed: {}", response.status()))

        }

    }

}

// ============================================================================
// Response Types (Mirror backend schemas)
// ============================================================================

#[derive(Debug, Clone, Serialize)]
pub struct ExecuteRequest {
    pub prompt: String,
    pub model_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    pub temperature: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub system_instruction: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_id: Option<String>,
    pub bypass_policies: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ExecuteResponse {
    pub content: String,
    pub model_id: String,
    pub tokens: TokenUsage,
    pub cost: CostUsage,
    pub latency_ms: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TokenUsage {
    pub input: u32,
    pub output: u32,
    pub total: u32,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CostUsage {
    pub input: f64,
    pub output: f64,
    pub total: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub database: String,
    pub cache: String,
    pub rabbitmq: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct MetricsResponse {
    pub total_models_registered: Option<u64>,
    pub total_model_queries: Option<u64>,
    pub total_filter_queries: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct FilterParams {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability_tier: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub vendor_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub function_call_support: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub min_context: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_cost_in: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub include_inactive: Option<bool>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ModelResponse {
    pub model_id: String,
    pub vendor_id: String,
    pub capability_tier: String,
    pub context_window: u32,
    pub cost_in_per_mil: f64,
    pub cost_out_per_mil: f64,
    pub function_call_support: bool,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct RecommendationRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub min_capability_tier: Option<String>,
    pub min_context_window: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_cost_per_mil: Option<f64>,
    pub strategy: String, // "cost" | "performance"
}

// ============================================================================
// Background Tasks
// ============================================================================

use tokio::sync::mpsc;

/// Event sent from background polling to UI
#[derive(Debug, Clone)]
pub enum ApiEvent {
    MetricsUpdate(MetricsResponse),
    HealthUpdate(HealthResponse),
    GenerationComplete(ExecuteResponse),
    Error(String),
}

/// Background metrics poller
pub async fn metrics_poller(
    client: ImsApiClient,
    tx: mpsc::UnboundedSender<ApiEvent>,
    mut shutdown: tokio::sync::watch::Receiver<bool>,
) {
    let mut interval = tokio::time::interval(Duration::from_secs(5));

    loop {
        tokio::select! {
            _ = interval.tick() => {
                match client.get_metrics().await {
                    Ok(metrics) => {
                        let _ = tx.send(ApiEvent::MetricsUpdate(metrics));
                    }
                    Err(e) => {
                        let _ = tx.send(ApiEvent::Error(format!("Metrics error: {}", e)));
                    }
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

/// Background health checker
pub async fn health_checker(
    client: ImsApiClient,
    tx: mpsc::UnboundedSender<ApiEvent>,
    mut shutdown: tokio::sync::watch::Receiver<bool>,
) {
    let mut interval = tokio::time::interval(Duration::from_secs(30));

    loop {
        tokio::select! {
            _ = interval.tick() => {
                match client.health_check().await {
                    Ok(health) => {
                        let _ = tx.send(ApiEvent::HealthUpdate(health));
                    }
                    Err(e) => {
                        let _ = tx.send(ApiEvent::Error(format!("Health check error: {}", e)));
                    }
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_client_creation() {
        let client = ImsApiClient::new(
            "http://localhost:8000".to_string(),
            None,
        );
        assert!(client.is_ok());
    }

    #[test]
    fn test_filter_params_serialization() {
        let params = FilterParams {
            capability_tier: Some("Tier_1".to_string()),
            vendor_id: Some("OpenAI".to_string()),
            function_call_support: None,
            min_context: Some(100000),
            max_cost_in: None,
            include_inactive: Some(false),
        };

        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("Tier_1"));
        assert!(json.contains("OpenAI"));
    }
}
