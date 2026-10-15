use crossterm::event::{Event as CrosstermEvent, EventStream, KeyEvent, KeyEventKind};
use futures_util::{FutureExt, StreamExt};
use std::time::Duration;
use tokio::sync::mpsc::{self, UnboundedReceiver, UnboundedSender};
use tokio::task::JoinHandle;
use tokio::time::interval;

/// Application events delivered to the central event loop.
#[derive(Debug, Clone, PartialEq)]
pub enum AppEvent {
    /// Terminal keyboard event
    Key(KeyEvent),
    /// Periodic 60 FPS tick event
    Tick,
    /// Terminal window resize event (width, height)
    Resize(u16, u16),
    /// Streaming token delta from prima.cpp chat endpoint
    TokenChunk(String),
    /// Notification that the chat stream has finished
    StreamComplete {
        prompt_tokens: usize,
        completion_tokens: usize,
    },
    /// Stream or network error notification
    StreamError(String),
    /// General status or info notification message
    StatusMessage(String),
    /// General application error message
    Error(String),
}

/// Asynchronous event handler wrapping Crossterm event stream and Tokio interval tick.
pub struct EventHandler {
    rx: UnboundedReceiver<AppEvent>,
    tx: UnboundedSender<AppEvent>,
    _task: JoinHandle<()>,
}

impl EventHandler {
    /// Create a new EventHandler with the specified tick duration (e.g. 16ms for ~60 FPS).
    pub fn new(tick_rate: Duration) -> Self {
        let (tx, rx) = mpsc::unbounded_channel();
        let event_tx = tx.clone();

        let task = tokio::spawn(async move {
            let mut reader = EventStream::new();
            let mut tick_interval = interval(tick_rate);

            loop {
                let tick_delay = tick_interval.tick();
                let crossterm_event = reader.next().fuse();

                tokio::select! {
                    _ = tick_delay => {
                        if event_tx.send(AppEvent::Tick).is_err() {
                            break;
                        }
                    }
                    maybe_event = crossterm_event => {
                        match maybe_event {
                            Some(Ok(evt)) => match evt {
                                CrosstermEvent::Key(key) => {
                                    if key.kind == KeyEventKind::Press || key.kind == KeyEventKind::Repeat {
                                        if event_tx.send(AppEvent::Key(key)).is_err() {
                                            break;
                                        }
                                    }
                                }
                                CrosstermEvent::Resize(w, h) => {
                                    if event_tx.send(AppEvent::Resize(w, h)).is_err() {
                                        break;
                                    }
                                }
                                _ => {}
                            },
                            Some(Err(err)) => {
                                if event_tx.send(AppEvent::Error(err.to_string())).is_err() {
                                    break;
                                }
                            }
                            None => break,
                        }
                    }
                }
            }
        });

        Self {
            rx,
            tx,
            _task: task,
        }
    }

    /// Return a clone of the event channel sender.
    pub fn sender(&self) -> UnboundedSender<AppEvent> {
        self.tx.clone()
    }

    /// Receive the next asynchronous event.
    pub async fn next(&mut self) -> Option<AppEvent> {
        self.rx.recv().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_event_handler_channel_message_passing() {
        let handler = EventHandler::new(Duration::from_millis(50));
        let tx = handler.sender();

        assert!(tx.send(AppEvent::TokenChunk("test_token".to_string())).is_ok());
        assert!(tx.send(AppEvent::StreamComplete { prompt_tokens: 10, completion_tokens: 20 }).is_ok());

        let mut handler = handler;
        let mut received_chunk = false;
        let mut received_complete = false;

        // Poll up to 5 events
        for _ in 0..5 {
            if let Some(event) = handler.next().await {
                match event {
                    AppEvent::TokenChunk(chunk) if chunk == "test_token" => {
                        received_chunk = true;
                    }
                    AppEvent::StreamComplete { prompt_tokens, completion_tokens }
                        if prompt_tokens == 10 && completion_tokens == 20 =>
                    {
                        received_complete = true;
                    }
                    _ => {}
                }
                if received_chunk && received_complete {
                    break;
                }
            }
        }

        assert!(received_chunk, "Should have received TokenChunk event");
        assert!(received_complete, "Should have received StreamComplete event");
    }
}
