// network.rs — Async HTTP polling + benchmark runner + SSE token streaming

use anyhow::Result;
use chrono::Local;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use tokio::time::sleep;

use crate::config::{ClusterConfig, FrameworkConfig, NodeSpec};
use crate::BenchmarkResult;

// ─── Poll Events sent to main loop ────────────────────────────────────────────

#[derive(Debug)]
pub enum PollEvent {
    NodeHealth {
        rank: usize,
        status: bool,
        ttft_ms: Option<f64>,
        tps: Option<f64>,
        ram_pct: Option<f64>,
    },
    BenchmarkResult(BenchmarkResult),
    LogLine(String),
    TokenChunk(String),
    StreamDone,
    HaldaAssignment {
        rank: usize,
        layer_window: String,
        gpu_layers: u32,
    },
}

#[derive(Debug, Deserialize)]
struct HealthResponse {
    status: Option<String>,
}

#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    max_tokens: u32,
    stream: bool,
    temperature: f32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

// ─── Background Poller ────────────────────────────────────────────────────────

pub struct Poller {
    config: ClusterConfig,
    tx: tokio::sync::mpsc::UnboundedSender<PollEvent>,
    client: Client,
}

impl Poller {
    pub fn new(
        config: ClusterConfig,
        tx: tokio::sync::mpsc::UnboundedSender<PollEvent>,
    ) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .expect("HTTP client build failed");
        Self { config, tx, client }
    }

    pub async fn run(self) {
        let mut tick = 0u64;
        loop {
            // Poll each node's health every 3 seconds
            for node in &self.config.nodes {
                if let Some(health_url) = node.health_url() {
                    let rank = node.rank;
                    match self.poll_health(&health_url, rank).await {
                        Ok(ev) => { let _ = self.tx.send(ev); }
                        Err(_) => {
                            let _ = self.tx.send(PollEvent::NodeHealth {
                                rank,
                                status: false,
                                ttft_ms: None,
                                tps: None,
                                ram_pct: None,
                            });
                        }
                    }
                } else {
                    // Worker node — check via quick TCP probe
                    let up = self.tcp_probe(&node.host, 22).await;
                    let _ = self.tx.send(PollEvent::NodeHealth {
                        rank: node.rank,
                        status: up,
                        ttft_ms: None,
                        tps: None,
                        ram_pct: None,
                    });
                }
            }

            // Every 30 ticks (~90s), auto-run a lightweight benchmark
            if tick % 30 == 0 && tick > 0 {
                let _ = self.tx.send(PollEvent::LogLine(
                    format!("[{}] 🔄 Auto-polling all frameworks...", Local::now().format("%H:%M:%S"))
                ));
                for fw in &self.config.frameworks {
                    if let Some(r) = self.probe_framework(fw).await {
                        let _ = self.tx.send(PollEvent::BenchmarkResult(r));
                    }
                }
            }

            tick += 1;
            sleep(Duration::from_secs(3)).await;
        }
    }

    async fn poll_health(&self, url: &str, rank: usize) -> Result<PollEvent> {
        let t0 = Instant::now();
        let resp = self.client.get(url).send().await?;
        let elapsed = t0.elapsed().as_millis() as f64;

        let _body: serde_json::Value = resp.json().await.unwrap_or_default();
        Ok(PollEvent::NodeHealth {
            rank,
            status: true,
            ttft_ms: Some(elapsed),
            tps: None,
            ram_pct: None,
        })
    }

    async fn tcp_probe(&self, host: &str, port: u16) -> bool {
        let addr = format!("{}:{}", host, port);
        tokio::net::TcpStream::connect(&addr)
            .await
            .map(|_| true)
            .unwrap_or(false)
    }

    async fn probe_framework(&self, fw: &FrameworkConfig) -> Option<BenchmarkResult> {
        let t0 = Instant::now();
        let req = ChatRequest {
            model: "local".to_string(),
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: "Describe your role as an AgentWorld agent in one sentence.".to_string(),
            }],
            max_tokens: 40,
            stream: false,
            temperature: 0.1,
        };

        let url = format!("{}/v1/chat/completions", fw.url);
        let resp = self.client
            .post(&url)
            .json(&req)
            .timeout(Duration::from_secs(30))
            .send()
            .await
            .ok()?;

        let elapsed = t0.elapsed().as_millis() as f64;
        let body: serde_json::Value = resp.json().await.ok()?;
        let completion_tokens = body["usage"]["completion_tokens"].as_f64().unwrap_or(10.0);
        let tps = if elapsed > 0.0 { completion_tokens / (elapsed / 1000.0) } else { 0.0 };

        Some(BenchmarkResult {
            framework: fw.name.clone(),
            ttft_ms: elapsed,
            tps,
            transport: fw.transport.clone(),
            nodes: vec![],
            timestamp: Local::now(),
        })
    }
}

// ─── On-demand benchmark (triggered by [b] key) ───────────────────────────────

pub async fn run_benchmark(
    _master_url: &str,
    _nodes: &[NodeSpec],
    tx: &tokio::sync::mpsc::UnboundedSender<PollEvent>,
) {
    let config = crate::config::load_cluster_config();
    let client = Client::builder()
        .timeout(Duration::from_secs(60))
        .build()
        .expect("client");

    let prompt = "You are an AgentWorld agent. Explain your planning strategy for complex multi-step reasoning tasks.";

    for fw in &config.frameworks {
        let _ = tx.send(PollEvent::LogLine(
            format!("[{}] ⚡ Benchmarking {}...", Local::now().format("%H:%M:%S"), fw.name)
        ));

        let t0 = Instant::now();
        let req = ChatRequest {
            model: "local".to_string(),
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            max_tokens: 100,
            stream: false,
            temperature: 0.1,
        };

        let url = format!("{}/v1/chat/completions", fw.url);
        match client.post(&url).json(&req).send().await {
            Ok(resp) => {
                let elapsed = t0.elapsed().as_millis() as f64;
                if let Ok(body) = resp.json::<serde_json::Value>().await {
                    let toks = body["usage"]["completion_tokens"].as_f64().unwrap_or(10.0);
                    let tps = if elapsed > 0.0 { toks / (elapsed / 1000.0) } else { 0.0 };
                    let content = body["choices"][0]["message"]["content"]
                        .as_str().unwrap_or("").chars().take(60).collect::<String>();

                    let _ = tx.send(PollEvent::BenchmarkResult(BenchmarkResult {
                        framework: fw.name.clone(),
                        ttft_ms: elapsed,
                        tps,
                        transport: fw.transport.clone(),
                        nodes: vec![],
                        timestamp: Local::now(),
                    }));
                    let _ = tx.send(PollEvent::LogLine(
                        format!("  ✅ {} → {:.0}ms TTFT | {:.1} t/s | \"{}...\"",
                            fw.name, elapsed, tps, content)
                    ));
                }
            }
            Err(e) => {
                let _ = tx.send(PollEvent::LogLine(
                    format!("  ❌ {} → OFFLINE: {}", fw.name, e)
                ));
            }
        }
    }
    let _ = tx.send(PollEvent::LogLine("✅ Benchmark complete. Press [3] to view results.".to_string()));
}

// ─── Streaming chat via SSE ────────────────────────────────────────────────────

pub async fn stream_chat(
    master_url: &str,
    history: &[(String, String)],
    tx: &tokio::sync::mpsc::UnboundedSender<PollEvent>,
) {
    let client = Client::builder()
        .timeout(Duration::from_secs(120))
        .build()
        .expect("client");

    let messages: Vec<ChatMessage> = history
        .iter()
        .map(|(role, content)| ChatMessage {
            role: role.clone(),
            content: content.clone(),
        })
        .collect();

    let req = ChatRequest {
        model: "local".to_string(),
        messages,
        max_tokens: 512,
        stream: true,
        temperature: 0.7,
    };

    let url = format!("{}/v1/chat/completions", master_url);
    match client.post(&url).json(&req).send().await {
        Ok(mut resp) => {
            use futures::StreamExt;
            let mut stream = resp.bytes_stream();

            while let Some(chunk) = stream.next().await {
                if let Ok(bytes) = chunk {
                    let text = String::from_utf8_lossy(&bytes);
                    for line in text.lines() {
                        if line.starts_with("data: ") {
                            let data = &line[6..];
                            if data == "[DONE]" {
                                let _ = tx.send(PollEvent::StreamDone);
                                return;
                            }
                            if let Ok(val) = serde_json::from_str::<serde_json::Value>(data) {
                                if let Some(delta) = val["choices"][0]["delta"]["content"].as_str() {
                                    let _ = tx.send(PollEvent::TokenChunk(delta.to_string()));
                                }
                            }
                        }
                    }
                }
            }
        }
        Err(e) => {
            let _ = tx.send(PollEvent::TokenChunk(
                format!("[ERROR: {} — is prima.cpp master running on {}?]", e, master_url)
            ));
        }
    }
    let _ = tx.send(PollEvent::StreamDone);
}
