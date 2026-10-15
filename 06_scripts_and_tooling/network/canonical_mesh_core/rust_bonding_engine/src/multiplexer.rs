use futures::{future::poll_fn, io::{AsyncRead, AsyncWrite}};
use tokio::sync::{mpsc, oneshot};
use tracing::{debug, error, info};
use yamux::{Config, Connection, ConnectionError, Mode, Stream};

pub struct MuxHandle {
    outbound_tx: mpsc::Sender<oneshot::Sender<Result<Stream, ConnectionError>>>,
    inbound_rx: mpsc::Receiver<Stream>,
}

impl MuxHandle {
    pub async fn open_stream(&self) -> anyhow::Result<Stream> {
        let (tx, rx) = oneshot::channel();
        self.outbound_tx
            .send(tx)
            .await
            .map_err(|_| anyhow::anyhow!("Multiplexer driver task has shut down"))?;
        let stream = rx
            .await
            .map_err(|_| anyhow::anyhow!("Multiplexer dropped response channel"))??;
        Ok(stream)
    }

    pub async fn next_inbound_stream(&mut self) -> Option<Stream> {
        self.inbound_rx.recv().await
    }
}

pub fn spawn_multiplexer<T>(io: T, mode: Mode) -> MuxHandle
where
    T: AsyncRead + AsyncWrite + Unpin + Send + 'static,
{
    let (outbound_tx, mut outbound_rx) = mpsc::channel::<oneshot::Sender<Result<Stream, ConnectionError>>>(64);
    let (inbound_tx, inbound_rx) = mpsc::channel::<Stream>(64);

    tokio::spawn(async move {
        let mut config = Config::default();
        config.set_max_num_streams(1024);

        let mut conn = Connection::new(io, config, mode);

        loop {
            tokio::select! {
                Some(sender) = outbound_rx.recv() => {
                    let res = poll_fn(|cx| conn.poll_new_outbound(cx)).await;
                    let _ = sender.send(res);
                }

                res = poll_fn(|cx| conn.poll_next_inbound(cx)) => {
                    match res {
                        Some(Ok(stream)) => {
                            debug!("New inbound Yamux stream received");
                            if inbound_tx.send(stream).await.is_err() {
                                debug!("Inbound stream consumer closed; terminating multiplexer");
                                break;
                            }
                        }
                        Some(Err(err)) => {
                            error!("Yamux multiplexer error: {}", err);
                            break;
                        }
                        None => {
                            info!("Yamux connection closed cleanly by remote peer");
                            break;
                        }
                    }
                }
            }
        }
        let _ = poll_fn(|cx| conn.poll_close(cx)).await;
    });

    MuxHandle {
        outbound_tx,
        inbound_rx,
    }
}
