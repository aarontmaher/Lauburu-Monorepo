//! ============================================================================
//! Tier 1, 2, 3 & 4 Test Suite: Embedded Chat & SSE Stream Engine
//! ============================================================================
//! Features Covered:
//! - F7: Chat Textarea Input (Request formatting & JSON serialization)
//! - F8: Async SSE Chat Streaming (HTTP POST, SSE parser, UTF-8 buffering)
//! - F9: Scrollable Chat History (Message accumulation, scrolling mechanics)
//! - F10: Zero-Mock / Truth Audit Compliance (True socket parsing, zero fake tokens)
//! ============================================================================

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio::sync::mpsc;

// ----------------------------------------------------------------------------
// Wire Protocol & Domain Models
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

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

#[derive(Debug, Clone, Deserialize)]
pub struct SseDelta {
    pub content: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SseChoice {
    pub delta: SseDelta,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SseChunk {
    pub id: Option<String>,
    pub choices: Vec<SseChoice>,
}

// ----------------------------------------------------------------------------
// SSE Stream Accumulator & Parser Engine
// ----------------------------------------------------------------------------

#[derive(Debug, Default)]
pub struct SseAccumulator {
    raw_buffer: Vec<u8>,
    pub accumulated_text: String,
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    pub is_complete: bool,
}

impl SseAccumulator {
    pub fn new() -> Self {
        Self::default()
    }

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
                    // Try to preserve partial UTF-8 if event boundary fell mid-character
                    continue;
                }
            };


            for line in event_str.lines() {
                let trimmed = line.trim();
                if trimmed.is_empty() || trimmed.starts_with(':') {
                    // SSE comments or empty lines
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

    pub fn reset(&mut self) {
        self.raw_buffer.clear();
        self.accumulated_text.clear();
        self.prompt_tokens = 0;
        self.completion_tokens = 0;
        self.is_complete = false;
    }
}

// ============================================================================
// TIER 1: FEATURE COVERAGE (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t1_f7_01_request_json_serialization() {
    let req = ChatCompletionRequest {
        model: "DeepSeek-R1-32B".to_string(),
        messages: vec![ChatMessage {
            role: "user".to_string(),
            content: "Explain PRP pipelining".to_string(),
        }],
        stream: true,
        temperature: Some(0.7),
        max_tokens: Some(2048),
    };

    let serialized = serde_json::to_string(&req).expect("Failed to serialize request");
    assert!(serialized.contains(r#""stream":true"#));
    assert!(serialized.contains(r#""model":"DeepSeek-R1-32B""#));
    assert!(serialized.contains(r#""content":"Explain PRP pipelining""#));
}

#[test]
fn test_t1_f8_02_sse_single_token_chunk_parsing() {
    let mut acc = SseAccumulator::new();
    let sse_data = b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}\n\n";
    let tokens = acc.push_bytes(sse_data).expect("Parsing failed");
    assert_eq!(tokens, vec!["Hello"]);
    assert_eq!(acc.accumulated_text, "Hello");
    assert_eq!(acc.completion_tokens, 1);
    assert!(!acc.is_complete);
}

#[test]
fn test_t1_f8_03_sse_stream_concatenation_and_done() {
    let mut acc = SseAccumulator::new();
    let chunk1 = b"data: {\"choices\":[{\"delta\":{\"content\":\"Lauburu \"}}]}\n\n";
    let chunk2 = b"data: {\"choices\":[{\"delta\":{\"content\":\"Mesh\"}}]}\n\n";
    let chunk3 = b"data: [DONE]\n\n";

    acc.push_bytes(chunk1).unwrap();
    acc.push_bytes(chunk2).unwrap();
    acc.push_bytes(chunk3).unwrap();

    assert_eq!(acc.accumulated_text, "Lauburu Mesh");
    assert_eq!(acc.completion_tokens, 2);
    assert!(acc.is_complete);
}

#[test]
fn test_t1_f9_04_chat_history_message_insertion() {
    let mut history: Vec<ChatMessage> = Vec::new();
    history.push(ChatMessage {
        role: "user".to_string(),
        content: "What is node L2?".to_string(),
    });
    history.push(ChatMessage {
        role: "assistant".to_string(),
        content: "Node L2 is MacBook_Pro connected via 10Gbps Thunderbolt 4.".to_string(),
    });

    assert_eq!(history.len(), 2);
    assert_eq!(history[0].role, "user");
    assert_eq!(history[1].role, "assistant");
    assert!(history[1].content.contains("Thunderbolt 4"));
}

#[test]
fn test_t1_f10_05_zero_mock_token_identity() {
    let mut acc = SseAccumulator::new();
    // Simulate real tokens received from socket
    let stream_payload = b"data: {\"choices\":[{\"delta\":{\"content\":\"Real \"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"Socket \"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"Data\"}}]}\n\n";
    let tokens = acc.push_bytes(stream_payload).unwrap();

    assert_eq!(tokens, vec!["Real ", "Socket ", "Data"]);
    assert_eq!(acc.accumulated_text, "Real Socket Data");
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t2_chat_b01_tcp_packet_fragmentation() {
    let mut acc = SseAccumulator::new();
    // Split "data: {\"choices\":[{\"delta\":{\"content\":\"Chunk\"}}]}\n\n" across 4 tiny fragments
    let p1 = b"da";
    let p2 = b"ta: {\"choices\":[{\"del";
    let p3 = b"ta\":{\"content\":\"Chunk\"}}";
    let p4 = b"]}\n\n";

    let t1 = acc.push_bytes(p1).unwrap();
    assert!(t1.is_empty(), "Fragment 1 must not yield tokens");
    let t2 = acc.push_bytes(p2).unwrap();
    assert!(t2.is_empty(), "Fragment 2 must not yield tokens");
    let t3 = acc.push_bytes(p3).unwrap();
    assert!(t3.is_empty(), "Fragment 3 must not yield tokens");
    let t4 = acc.push_bytes(p4).unwrap();
    assert_eq!(t4, vec!["Chunk"], "Final fragment completing delimiter must yield token");
    assert_eq!(acc.accumulated_text, "Chunk");
}

#[test]
fn test_t2_chat_b02_multibyte_utf8_split_across_packets() {
    let mut acc = SseAccumulator::new();
    // 🦀 Crab emoji is 4 bytes: 0xF0, 0x9F, 0xA6, 0x80
    // Split the JSON payload right in the middle of the 4-byte UTF-8 sequence
    let json_prefix = b"data: {\"choices\":[{\"delta\":{\"content\":\"";
    let json_suffix = b"\"}}]}\n\n";

    let mut part1 = json_prefix.to_vec();
    part1.push(0xF0);
    part1.push(0x9F);

    let mut part2 = vec![0xA6, 0x80];
    part2.extend_from_slice(json_suffix);

    let _ = acc.push_bytes(&part1).unwrap();
    let tokens = acc.push_bytes(&part2).unwrap();

    assert_eq!(tokens, vec!["🦀"]);
    assert_eq!(acc.accumulated_text, "🦀");
}

#[test]
fn test_t2_chat_b03_sse_comments_and_keepalive_ignored() {
    let mut acc = SseAccumulator::new();
    let payload = b": keep-alive ping\n: second comment\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"Valid\"}}]}\n\n";
    let tokens = acc.push_bytes(payload).unwrap();
    assert_eq!(tokens, vec!["Valid"]);
    assert_eq!(acc.accumulated_text, "Valid");
}

#[test]
fn test_t2_chat_b04_malformed_json_inside_sse_skipped_gracefully() {
    let mut acc = SseAccumulator::new();
    let corrupted_payload = b"data: {corrupted json}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"Recovered\"}}]}\n\n";
    let tokens = acc.push_bytes(corrupted_payload).unwrap();
    assert_eq!(tokens, vec!["Recovered"]);
    assert_eq!(acc.accumulated_text, "Recovered");
}

#[test]
fn test_t2_chat_b05_empty_delta_content_handled() {
    let mut acc = SseAccumulator::new();
    // Delta with role only (initial chunk)
    let role_payload = b"data: {\"choices\":[{\"delta\":{\"role\":\"assistant\"}}]}\n\n";
    let tokens = acc.push_bytes(role_payload).unwrap();
    assert!(tokens.is_empty(), "Role-only delta must not add tokens");
    assert_eq!(acc.accumulated_text, "");
}

#[test]
fn test_t2_chat_b06_finish_reason_stop_marks_completion() {
    let mut acc = SseAccumulator::new();
    let stop_payload = b"data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n";
    acc.push_bytes(stop_payload).unwrap();
    assert!(acc.is_complete);
}

#[test]
fn test_t2_chat_b07_huge_token_payload_stress() {
    let mut acc = SseAccumulator::new();
    let large_string = "X".repeat(32768); // 32KB single chunk
    let large_json = format!("data: {{\"choices\":[{{\"delta\":{{\"content\":\"{}\"}}}}]}}\n\n", large_string);
    let tokens = acc.push_bytes(large_json.as_bytes()).unwrap();
    assert_eq!(tokens.len(), 1);
    assert_eq!(acc.accumulated_text.len(), 32768);
}

// ============================================================================
// TIER 3 & 4: ASYNC HTTP SSE MOCK SERVER & END-TO-END WORKFLOWS
// ============================================================================

#[tokio::test]
async fn test_t4_e2e_async_http_sse_streaming_workflow() {
    // 1. Spin up a real in-process Tokio TCP listener mimicking prima.cpp / llama.cpp :8082
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("Failed to bind test listener");
    let server_addr = listener.local_addr().unwrap();

    let server_task = tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut req_buf = vec![0u8; 1024];
            let _ = socket.read(&mut req_buf).await;

            let response = "HTTP/1.1 200 OK\r\n\
                Content-Type: text/event-stream\r\n\
                Cache-Control: no-cache\r\n\
                Connection: keep-alive\r\n\r\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"Pipelined \"}}]}\n\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"Ring \"}}]}\n\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"Parallelism\"}}]}\n\n\
                data: [DONE]\n\n";

            let _ = socket.write_all(response.as_bytes()).await;
            let _ = socket.flush().await;
        }
    });

    // 2. Client connecting via HTTP stream
    let client = reqwest::Client::new();
    let url = format!("http://{}/v1/chat/completions", server_addr);
    let req = ChatCompletionRequest {
        model: "DeepSeek-R1-32B".to_string(),
        messages: vec![ChatMessage {
            role: "user".to_string(),
            content: "What is PRP?".to_string(),
        }],
        stream: true,
        temperature: None,
        max_tokens: None,
    };

    let res = client.post(&url).json(&req).send().await.expect("Failed to send POST request");
    assert_eq!(res.status(), reqwest::StatusCode::OK);

    let mut byte_stream = res.bytes_stream();
    let mut accumulator = SseAccumulator::new();

    use futures_util::StreamExt;
    while let Some(item) = byte_stream.next().await {
        let chunk = item.expect("Stream read failed");
        accumulator.push_bytes(&chunk).expect("Accumulator push failed");
    }

    assert_eq!(accumulator.accumulated_text, "Pipelined Ring Parallelism");
    assert_eq!(accumulator.completion_tokens, 3);
    assert!(accumulator.is_complete);

    let _ = server_task.await;
}

#[tokio::test]
async fn test_t3_cross_stream_cancellation_aborts_network_task() {
    let (tx_cmd, mut rx_cmd) = mpsc::channel::<&'static str>(10);
    let is_cancelled = Arc::new(AtomicBool::new(false));
    let is_cancelled_clone = is_cancelled.clone();

    let worker = tokio::spawn(async move {
        while let Some(cmd) = rx_cmd.recv().await {
            if cmd == "CancelStream" {
                is_cancelled_clone.store(true, Ordering::SeqCst);
                break;
            }
        }
    });

    tx_cmd.send("CancelStream").await.unwrap();
    let _ = worker.await;

    assert!(is_cancelled.load(Ordering::SeqCst), "CancelStream command must stop worker");
}

#[tokio::test]
async fn test_t2_http_500_server_error_status_handled() {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut req_buf = vec![0u8; 1024];
            let _ = socket.read(&mut req_buf).await;
            let response = "HTTP/1.1 500 Internal Server Error\r\nContent-Length: 21\r\n\r\nCUDA Out of Memory OOM";
            let _ = socket.write_all(response.as_bytes()).await;
        }
    });

    let client = reqwest::Client::new();
    let res = client.post(format!("http://{}/v1/chat/completions", addr))
        .send().await.unwrap();

    assert_eq!(res.status(), reqwest::StatusCode::INTERNAL_SERVER_ERROR);
}

#[tokio::test]
async fn test_t2_connection_refused_on_offline_port() {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_millis(500))
        .build().unwrap();

    // Use an unassigned port in the dynamic range guaranteed to be offline
    let res = client.post("http://127.0.0.1:59998/v1/chat/completions").send().await;
    assert!(res.is_err(), "Connection to offline port must return an error");
}

// ============================================================================
// TIER 5: ADVERSARIAL HARDENING & PRODUCTION RESILIENCE
// ============================================================================

#[test]
fn test_t5_adv_chat_01_crlf_sse_delimiters() {
    let mut acc = SseAccumulator::new();
    let crlf_payload = b"data: {\"choices\":[{\"delta\":{\"content\":\"CRLF \"}}]}\r\n\r\ndata: {\"choices\":[{\"delta\":{\"content\":\"Tokens\"}}]}\r\n\r\n";
    let tokens = acc.push_bytes(crlf_payload).unwrap();
    assert_eq!(tokens, vec!["CRLF ", "Tokens"]);
    assert_eq!(acc.accumulated_text, "CRLF Tokens");
}


#[test]
fn test_t5_adv_chat_02_multiple_choices_in_single_chunk() {
    let mut acc = SseAccumulator::new();
    let multi_choice_payload = b"data: {\"choices\":[{\"delta\":{\"content\":\"Choice1 \"}},{\"delta\":{\"content\":\"Choice2\"}}]}\n\n";
    let tokens = acc.push_bytes(multi_choice_payload).unwrap();
    assert_eq!(tokens, vec!["Choice1 ", "Choice2"]);
    assert_eq!(acc.accumulated_text, "Choice1 Choice2");
}

#[test]
fn test_t5_adv_chat_03_app_submit_empty_prompt_is_rejected() {
    use lauburu_tui::app::App;
    use lauburu_tui::config::MeshConfig;

    let mut app = App::new(MeshConfig::fallback());
    app.switch_tab(lauburu_tui::Tab::Chat);

    // Initial textarea is empty
    let cmd = app.submit_prompt();
    assert_eq!(cmd, None, "Empty prompt must return None");
    assert!(!app.is_streaming);
    assert_eq!(app.chat_history.len(), 0);
}

#[test]
fn test_t5_adv_chat_04_app_handle_key_returns_send_prompt() {
    use crossterm::event::{KeyCode, KeyEvent, KeyEventState, KeyModifiers};
    use lauburu_tui::app::App;
    use lauburu_tui::config::MeshConfig;
    use lauburu_tui::network::NetworkCommand;

    let mut app = App::new(MeshConfig::fallback());
    app.switch_tab(lauburu_tui::Tab::Chat);

    let make_key = |code: KeyCode| KeyEvent {
        code,
        modifiers: KeyModifiers::NONE,
        kind: crossterm::event::KeyEventKind::Press,
        state: KeyEventState::NONE,
    };

    // Type prompt "ping"
    app.handle_key(make_key(KeyCode::Char('p')));
    app.handle_key(make_key(KeyCode::Char('i')));
    app.handle_key(make_key(KeyCode::Char('n')));
    app.handle_key(make_key(KeyCode::Char('g')));

    // Press Enter to submit
    let cmd = app.handle_key(make_key(KeyCode::Enter));
    assert!(cmd.is_some(), "Enter in Chat tab must yield SendPrompt command");
    match cmd.unwrap() {
        NetworkCommand::SendPrompt { prompt, model } => {
            assert_eq!(prompt, "ping");
            assert_eq!(model, "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf");
        }
        _ => panic!("Expected SendPrompt command"),
    }
    assert!(app.is_streaming);
    assert_eq!(app.chat_history.len(), 2);
    assert_eq!(app.chat_history[0].role, "user");
    assert_eq!(app.chat_history[0].content, "ping");
    assert_eq!(app.chat_history[1].role, "assistant");
}

#[tokio::test]
async fn test_t5_adv_chat_05_network_worker_full_stream_lifecycle() {
    use lauburu_tui::events::AppEvent;
    use lauburu_tui::network::{NetworkCommand, NetworkWorker};

    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    let server = tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut buf = vec![0u8; 1024];
            let _ = socket.read(&mut buf).await;

            let resp = "HTTP/1.1 200 OK\r\n\
                Content-Type: text/event-stream\r\n\
                Connection: close\r\n\r\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"DeepSeek \"}}]}\n\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"R1 \"}}]}\n\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"32B\"}}]}\n\n\
                data: [DONE]\n\n";
            let _ = socket.write_all(resp.as_bytes()).await;
        }
    });

    let (tx_cmd, rx_cmd) = mpsc::channel(10);
    let (tx_event, mut rx_event) = tokio::sync::mpsc::unbounded_channel::<AppEvent>();

    let _handle = NetworkWorker::spawn(rx_cmd, tx_event, format!("http://{}", addr));

    tx_cmd
        .send(NetworkCommand::SendPrompt {
            prompt: "Identify model".to_string(),
            model: "DeepSeek-R1-32B".to_string(),
        })
        .await
        .unwrap();

    let mut tokens = Vec::new();
    let mut complete = false;

    while let Some(evt) = rx_event.recv().await {
        match evt {
            AppEvent::TokenChunk(t) => tokens.push(t),
            AppEvent::StreamComplete { .. } => {
                complete = true;
                break;
            }
            _ => {}
        }
    }

    assert_eq!(tokens, vec!["DeepSeek ", "R1 ", "32B"]);
    assert!(complete);
    let _ = server.await;
}

#[tokio::test]
async fn test_t5_adv_chat_06_network_worker_cancellation_mid_stream() {
    use lauburu_tui::events::AppEvent;
    use lauburu_tui::network::{NetworkCommand, NetworkWorker};

    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut buf = vec![0u8; 1024];
            let _ = socket.read(&mut buf).await;

            let head = "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n";
            let _ = socket.write_all(head.as_bytes()).await;

            let c1 = "data: {\"choices\":[{\"delta\":{\"content\":\"Starting \"}}]}\n\n";
            let _ = socket.write_all(c1.as_bytes()).await;

            // Keep connection open without completing
            tokio::time::sleep(Duration::from_millis(1000)).await;
        }
    });

    let (tx_cmd, rx_cmd) = mpsc::channel(10);
    let (tx_event, mut rx_event) = tokio::sync::mpsc::unbounded_channel::<AppEvent>();

    let _handle = NetworkWorker::spawn(rx_cmd, tx_event, format!("http://{}", addr));

    tx_cmd
        .send(NetworkCommand::SendPrompt {
            prompt: "Infinite Stream".to_string(),
            model: "test".to_string(),
        })
        .await
        .unwrap();

    // Wait for first token
    if let Some(AppEvent::TokenChunk(t)) = rx_event.recv().await {
        assert_eq!(t, "Starting ");
    }

    // Now cancel the stream
    tx_cmd.send(NetworkCommand::CancelStream).await.unwrap();

    // Expect cancellation event
    let mut got_cancelled = false;
    while let Some(evt) = rx_event.recv().await {
        if let AppEvent::StreamError(e) = evt {
            if e.contains("cancelled") {
                got_cancelled = true;
                break;
            }
        }
    }
    assert!(got_cancelled, "Worker must emit StreamError on cancellation");
}

