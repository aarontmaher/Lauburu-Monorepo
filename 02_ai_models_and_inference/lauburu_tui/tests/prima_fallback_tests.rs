use lauburu_tui::config::MeshConfig;
use lauburu_tui::events::AppEvent;
use lauburu_tui::network::{NetworkCommand, NetworkWorker};
use std::time::Duration;
use tokio::net::TcpListener;
use tokio::sync::mpsc;

#[tokio::test]
async fn test_prima_to_llama_automatic_failover() {
    // 1. Create a dummy fallback server simulating llama.cpp on localhost
    let fallback_listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let fallback_addr = fallback_listener.local_addr().unwrap();

    tokio::spawn(async move {
        while let Ok((mut socket, _)) = fallback_listener.accept().await {
            use tokio::io::{AsyncReadExt, AsyncWriteExt};
            let mut buf = [0u8; 1024];
            let _ = socket.read(&mut buf).await;

            let response_body = "data: {\"choices\":[{\"delta\":{\"content\":\"Hello from llama.cpp fallback\"}}]}\n\ndata: [DONE]\n\n";
            let http_response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                response_body.len(),
                response_body
            );
            let _ = socket.write_all(http_response.as_bytes()).await;
        }
    });

    // 2. Spawn NetworkWorker with unreachable primary (prima.cpp) and active fallback (llama.cpp)
    let (tx_cmd, rx_cmd) = mpsc::channel(32);
    let (tx_event, mut rx_event) = mpsc::unbounded_channel();

    let unreachable_primary = "http://127.0.0.1:59999".to_string();
    let active_fallback = format!("http://{}", fallback_addr);

    let _handle = NetworkWorker::spawn_with_fallback(
        rx_cmd,
        tx_event,
        unreachable_primary,
        Some(active_fallback),
    );

    // 3. Send prompt command
    tx_cmd
        .send(NetworkCommand::SendPrompt {
            prompt: "Test prompt".to_string(),
            model: "test_model".to_string(),
        })
        .await
        .unwrap();

    // 4. Assert that tokens were received from fallback server
    let mut received_tokens = Vec::new();
    let mut got_status_message = false;
    let mut got_completion = false;

    let timeout = tokio::time::sleep(Duration::from_secs(5));
    tokio::pin!(timeout);

    loop {
        tokio::select! {
            _ = &mut timeout => break,
            event = rx_event.recv() => {
                match event {
                    Some(AppEvent::TokenChunk(tok)) => {
                        received_tokens.push(tok);
                    }
                    Some(AppEvent::StatusMessage(msg)) => {
                        if msg.contains("Routed to llama.cpp") {
                            got_status_message = true;
                        }
                    }
                    Some(AppEvent::StreamComplete { .. }) => {
                        got_completion = true;
                        break;
                    }
                    _ => {}
                }
            }
        }
    }

    assert!(got_status_message, "Expected status message indicating routing to llama.cpp fallback");
    assert!(!received_tokens.is_empty(), "Expected token chunks from fallback server");
    assert_eq!(received_tokens.join(""), "Hello from llama.cpp fallback");
    assert!(got_completion, "Expected StreamComplete event from fallback");
}

#[test]
fn test_mesh_config_fallback_endpoint_accessors() {
    let cfg = MeshConfig::fallback();
    assert_eq!(cfg.master_endpoint(), "http://127.0.0.1:8082/v1/chat/completions");
    assert_eq!(cfg.fallback_endpoint(), "http://127.0.0.1:8083/v1/chat/completions");
}
