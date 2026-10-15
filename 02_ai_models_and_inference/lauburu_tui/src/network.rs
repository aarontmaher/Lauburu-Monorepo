use crate::events::AppEvent;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tokio::sync::mpsc::{Receiver, UnboundedSender};
use tokio::task::JoinHandle;

/// Chat message representation for conversation history and OpenAI payload.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

/// OpenAI-compatible chat completion request payload for prima.cpp / llama.cpp.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatCompletionRequest {
    pub model: String,
    pub messages: Vec<ChatMessage>,
    pub stream: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<usize>,
}

/// SSE chunk delta representation.
#[derive(Debug, Clone, Deserialize)]
pub struct SseDelta {
    pub content: Option<String>,
    pub role: Option<String>,
}

/// SSE chunk choice representation.
#[derive(Debug, Clone, Deserialize)]
pub struct SseChoice {
    pub delta: SseDelta,
    pub finish_reason: Option<String>,
}

/// SSE chunk root payload.
#[derive(Debug, Clone, Deserialize)]
pub struct SseChunk {
    pub id: Option<String>,
    pub choices: Vec<SseChoice>,
}

/// Byte-level Server-Sent Events (SSE) accumulator and tokenizer.
#[derive(Debug, Default, Clone)]
pub struct SseAccumulator {
    raw_buffer: Vec<u8>,
    pub accumulated_text: String,
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    pub is_complete: bool,
}

impl SseAccumulator {
    /// Create a new, empty SSE accumulator.
    pub fn new() -> Self {
        Self::default()
    }

    /// Push incoming byte chunk into the buffer and extract any complete SSE tokens.
    pub fn push_bytes(&mut self, bytes: &[u8]) -> Result<Vec<String>, String> {
        self.raw_buffer.extend_from_slice(bytes);
        let mut tokens = Vec::new();

        loop {
            let (pos, delim_len) = if let Some(p4) = self.raw_buffer.windows(4).position(|w| w == b"\r\n\r\n") {
                if let Some(p2) = self.raw_buffer.windows(2).position(|w| w == b"\n\n") {
                    if p2 < p4 {
                        (p2, 2)
                    } else {
                        (p4, 4)
                    }
                } else {
                    (p4, 4)
                }
            } else if let Some(p2) = self.raw_buffer.windows(2).position(|w| w == b"\n\n") {
                (p2, 2)
            } else {
                break;
            };

            let event_bytes: Vec<u8> = self.raw_buffer.drain(..pos + delim_len).collect();
            let event_str = match std::str::from_utf8(&event_bytes) {
                Ok(s) => s,
                Err(_) => {
                    // Incomplete UTF-8 sequence across boundary
                    continue;
                }
            };


            for line in event_str.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() || trimmed.starts_with(':') {
                    // SSE comments or empty keepalive lines
                    continue;
                }

                if let Some(data_part) = trimmed.strip_prefix("data:") {
                    let json_payload = data_part.trim();
                    if json_payload == "[DONE]" {
                        self.is_complete = true;
                        continue;
                    }

                    if let Ok(chunk) = serde_json::from_str::<SseChunk>(json_payload) {
                        for choice in chunk.choices {
                            if let Some(content) = choice.delta.content {
                                if !content.is_empty() {
                                    self.accumulated_text.push_str(&content);
                                    self.completion_tokens += 1;
                                    tokens.push(content);
                                }
                            }
                            if choice.finish_reason.is_some() {
                                self.is_complete = true;
                            }
                        }
                    }
                }
            }
        }

        Ok(tokens)
    }

    /// Reset internal accumulator state for a new conversation turn.
    pub fn reset(&mut self) {
        self.raw_buffer.clear();
        self.accumulated_text.clear();
        self.prompt_tokens = 0;
        self.completion_tokens = 0;
        self.is_complete = false;
    }
}

/// Commands sent from the UI/App to the background NetworkWorker.
#[derive(Debug, Clone, PartialEq)]
pub enum NetworkCommand {
    /// Send a prompt message to the prima.cpp inference master.
    SendPrompt {
        prompt: String,
        model: String,
    },
    /// Abort an active streaming response.
    CancelStream,
}

/// Asynchronous network worker handling non-blocking HTTP streaming requests.
pub struct NetworkWorker;

impl NetworkWorker {
    /// Spawn the Tokio background actor receiving NetworkCommands and emitting AppEvents.
    pub fn spawn(
        rx_cmd: Receiver<NetworkCommand>,
        tx_event: UnboundedSender<AppEvent>,
        endpoint: String,
    ) -> JoinHandle<()> {
        Self::spawn_with_fallback(rx_cmd, tx_event, endpoint, None)
    }

    /// Spawn the Tokio background actor with primary endpoint (prima.cpp) and automatic fallback (llama.cpp).
    pub fn spawn_with_fallback(
        mut rx_cmd: Receiver<NetworkCommand>,
        tx_event: UnboundedSender<AppEvent>,
        primary_endpoint: String,
        fallback_endpoint: Option<String>,
    ) -> JoinHandle<()> {
        tokio::spawn(async move {
            let client = reqwest::Client::builder()
                .connect_timeout(Duration::from_secs(4))
                .timeout(Duration::from_secs(120))
                .build()
                .unwrap_or_default();

            let primary_url = if primary_endpoint.contains("/v1/chat/completions") {
                primary_endpoint.clone()
            } else {
                format!("{}/v1/chat/completions", primary_endpoint.trim_end_matches('/'))
            };

            let fallback_url = fallback_endpoint.as_ref().map(|ep| {
                if ep.contains("/v1/chat/completions") {
                    ep.clone()
                } else {
                    format!("{}/v1/chat/completions", ep.trim_end_matches('/'))
                }
            });

            while let Some(cmd) = rx_cmd.recv().await {
                match cmd {
                    NetworkCommand::SendPrompt { prompt, model } => {
                        let request_payload = ChatCompletionRequest {
                            model: model.clone(),
                            messages: vec![ChatMessage {
                                role: "user".to_string(),
                                content: prompt.clone(),
                            }],
                            stream: true,
                            temperature: Some(0.7),
                            max_tokens: Some(2048),
                        };

                        // Out-of-band Bluetooth Terminal stream header
                        let bt_header = format!("\x1b[1;36m[RUST TUI BLUETOOTH GATEWAY -> {}]\x1b[0m\n> {}\n", model, prompt);
                        let _ = std::fs::write("/tmp/bluetooth_terminal_stream.ansi", bt_header);

                        // 1. Try Primary Endpoint (prima.cpp)
                        let mut response = client
                            .post(&primary_url)
                            .header("Content-Type", "application/json")
                            .json(&request_payload)
                            .send()
                            .await;

                        let mut active_url = primary_url.clone();

                        // 2. If Primary fails and Fallback is configured, seamlessly failover to llama.cpp
                        if (response.is_err() || response.as_ref().map_or(false, |r| !r.status().is_success()))
                            && fallback_url.is_some()
                        {
                            if let Some(ref fb_url) = fallback_url {
                                if fb_url != &primary_url {
                                    let _ = tx_event.send(AppEvent::StatusMessage(
                                        "⚡ Primary prima.cpp (8082) unavailable. Routed to llama.cpp (8083)...".to_string(),
                                    ));
                                    response = client
                                        .post(fb_url)
                                        .header("Content-Type", "application/json")
                                        .json(&request_payload)
                                        .send()
                                        .await;
                                    active_url = fb_url.clone();
                                }
                            }
                        }

                        let resp = match response {
                            Ok(r) => r,
                            Err(e) => {
                                let _ = tx_event.send(AppEvent::StreamError(format!(
                                    "Connection failed to {}: {}",
                                    active_url, e
                                )));
                                continue;
                            }
                        };

                        if !resp.status().is_success() {
                            let status = resp.status();
                            let body = resp.text().await.unwrap_or_else(|_| "Unknown error".to_string());
                            let _ = tx_event.send(AppEvent::StreamError(format!(
                                "HTTP {} {}: {}",
                                status.as_u16(),
                                status.canonical_reason().unwrap_or(""),
                                body
                            )));
                            continue;
                        }

                        let mut byte_stream = resp.bytes_stream();
                        let mut accumulator = SseAccumulator::new();
                        let mut cancelled = false;

                        while let Some(chunk_result) = tokio::select! {
                            item = byte_stream.next() => item,
                            cmd_opt = rx_cmd.recv() => {
                                match cmd_opt {
                                    Some(NetworkCommand::CancelStream) => {
                                        cancelled = true;
                                        None
                                    }
                                    _ => None,
                                }
                            }
                        } {
                            match chunk_result {
                                Ok(bytes) => {
                                    if let Ok(tokens) = accumulator.push_bytes(&bytes) {
                                        for token in tokens {
                                            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open("/tmp/bluetooth_terminal_stream.ansi") {
                                                use std::io::Write;
                                                let _ = f.write_all(token.as_bytes());
                                            }
                                            if tx_event.send(AppEvent::TokenChunk(token)).is_err() {
                                                break;
                                            }
                                        }
                                    }
                                    if accumulator.is_complete {
                                        break;
                                    }
                                }
                                Err(e) => {
                                    let _ = tx_event.send(AppEvent::StreamError(format!(
                                        "Stream read error: {}",
                                        e
                                    )));
                                    break;
                                }
                            }
                        }

                        if cancelled {
                            let _ = tx_event.send(AppEvent::StreamError("Stream cancelled by user".to_string()));
                        } else {
                            let _ = tx_event.send(AppEvent::StreamComplete {
                                prompt_tokens: accumulator.prompt_tokens,
                                completion_tokens: accumulator.completion_tokens,
                            });
                        }
                    }
                    NetworkCommand::CancelStream => {
                        // Already handled inside select loop
                    }
                }
            }
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::sync::mpsc;
    use tokio::net::TcpListener;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};


    #[test]
    fn test_sse_accumulator_basic_and_reset() {
        let mut acc = SseAccumulator::new();
        let chunk = b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello \"}}]}\n\n";
        let tokens = acc.push_bytes(chunk).unwrap();
        assert_eq!(tokens, vec!["Hello "]);
        assert_eq!(acc.accumulated_text, "Hello ");
        assert_eq!(acc.completion_tokens, 1);
        assert!(!acc.is_complete);

        acc.reset();
        assert_eq!(acc.accumulated_text, "");
        assert_eq!(acc.completion_tokens, 0);
        assert!(!acc.is_complete);
    }

    #[test]
    fn test_sse_accumulator_done_signal() {
        let mut acc = SseAccumulator::new();
        let chunk1 = b"data: {\"choices\":[{\"delta\":{\"content\":\"World\"}}]}\n\n";
        let chunk2 = b"data: [DONE]\n\n";

        acc.push_bytes(chunk1).unwrap();
        acc.push_bytes(chunk2).unwrap();

        assert_eq!(acc.accumulated_text, "World");
        assert!(acc.is_complete);
    }

    #[test]
    fn test_chat_completion_request_serialization() {
        let req = ChatCompletionRequest {
            model: "Qwen2.5-7B".to_string(),
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: "ping".to_string(),
            }],
            stream: true,
            temperature: Some(0.7),
            max_tokens: Some(1024),
        };

        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("\"stream\":true"));
        assert!(json.contains("\"model\":\"Qwen2.5-7B\""));
        assert!(json.contains("\"content\":\"ping\""));
    }

    #[tokio::test]
    async fn test_network_worker_spawn_and_stream() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();

        tokio::spawn(async move {
            if let Ok((mut socket, _)) = listener.accept().await {
                let mut buf = vec![0u8; 1024];
                let _ = socket.read(&mut buf).await;

                let resp = "HTTP/1.1 200 OK\r\n\
                    Content-Type: text/event-stream\r\n\r\n\
                    data: {\"choices\":[{\"delta\":{\"content\":\"Mesh \"}}]}\n\n\
                    data: {\"choices\":[{\"delta\":{\"content\":\"Online\"}}]}\n\n\
                    data: [DONE]\n\n";
                let _ = socket.write_all(resp.as_bytes()).await;
            }
        });

        let (tx_cmd, rx_cmd) = mpsc::channel(10);
        let (tx_event, mut rx_event) = mpsc::unbounded_channel();

        let _handle = NetworkWorker::spawn(
            rx_cmd,
            tx_event,
            format!("http://{}", addr),
        );

        tx_cmd
            .send(NetworkCommand::SendPrompt {
                prompt: "Status".to_string(),
                model: "Qwen".to_string(),
            })
            .await
            .unwrap();

        let mut received_tokens = Vec::new();
        let mut completed = false;

        while let Some(event) = rx_event.recv().await {
            match event {
                AppEvent::TokenChunk(t) => received_tokens.push(t),
                AppEvent::StreamComplete { .. } => {
                    completed = true;
                    break;
                }
                _ => {}
            }
        }

        assert_eq!(received_tokens, vec!["Mesh ", "Online"]);
        assert!(completed);
    }
}
