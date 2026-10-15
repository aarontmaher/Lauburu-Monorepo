use std::net::SocketAddr;
use aggligator::transport::Acceptor;
use aggligator_transport_tcp::TcpAcceptor;
use anyhow::Result;
use tokio::net::TcpStream;
use tokio_util::compat::{FuturesAsyncReadCompatExt, TokioAsyncReadCompatExt};
use tracing::{error, info, warn};
use yamux::Mode;

use crate::multiplexer::spawn_multiplexer;
use crate::protocol::{SOCKS5_STREAM_ID, TUN_STREAM_ID};
use crate::socks5::read_target_from_stream;

pub async fn run_server(bind_addr: SocketAddr) -> Result<()> {
    info!("Starting Lauburu Multipath Bonding Server on {}", bind_addr);

    let acceptor = Acceptor::new();
    let tcp_acceptor = TcpAcceptor::new([bind_addr]).await?;
    acceptor.add(tcp_acceptor);

    info!("Server listening for bonded link connections on {}", bind_addr);

    loop {
        match acceptor.accept().await {
            Ok((channel, control)) => {
                let conn_id = channel.id();
                info!("Accepted new bonded multi-link connection [id={}]", conn_id);

                let stream = channel.into_stream();
                let mut mux_handle = spawn_multiplexer(stream.compat(), Mode::Server);

                // Spawn link telemetry monitor for this connection
                let ctrl = control.clone();
                tokio::spawn(async move {
                    loop {
                        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
                        if ctrl.is_terminated() {
                            break;
                        }
                        let links = ctrl.links();
                        let active = links.iter().filter(|l| l.is_working()).count();
                        let mut total_tx = 0.0;
                        let mut total_rx = 0.0;
                        for l in &links {
                            let st = l.stats();
                            if let Some(ts) = st.time_stats.first() {
                                total_tx += ts.send_speed();
                                total_rx += ts.recv_speed();
                            }
                        }
                        info!(
                            "Server Connection [{}]: {} active links | Aggregated TX: {:.1} KB/s | RX: {:.1} KB/s",
                            conn_id, active, total_tx / 1024.0, total_rx / 1024.0
                        );
                    }
                });

                // Spawn stream dispatcher for incoming multiplexed channels
                tokio::spawn(async move {
                    while let Some(mut stream) = mux_handle.next_inbound_stream().await {
                        tokio::spawn(async move {
                            if let Err(e) = handle_inbound_stream(&mut stream).await {
                                warn!("Error handling multiplexed stream: {}", e);
                            }
                        });
                    }
                    info!("Connection [{}] ended stream dispatch loop", conn_id);
                });
            }
            Err(e) => {
                error!("Error accepting bonded connection: {}", e);
            }
        }
    }
}

async fn handle_inbound_stream(stream: &mut yamux::Stream) -> Result<()> {
    let mut stream_compat = stream.compat();

    // Read stream type
    let mut type_buf = [0u8; 1];
    tokio::io::AsyncReadExt::read_exact(&mut stream_compat, &mut type_buf).await?;

    match type_buf[0] {
        SOCKS5_STREAM_ID => {
            let target = read_target_from_stream(&mut stream_compat).await?;
            info!("Relaying bonded connection to destination: {}", target);

            let target_str = match &target {
                crate::socks5::TargetAddr::Ip(addr) => addr.to_string(),
                crate::socks5::TargetAddr::Domain(host, port) => format!("{}:{}", host, port),
            };

            match TcpStream::connect(&target_str).await {
                Ok(mut remote) => {
                    // Send 0x00 = connection succeeded
                    tokio::io::AsyncWriteExt::write_all(&mut stream_compat, &[0x00]).await?;
                    tokio::io::AsyncWriteExt::flush(&mut stream_compat).await?;

                    // Proxy bidirectional traffic
                    let (mut cr, mut cw) = tokio::io::split(stream_compat);
                    let (mut rr, mut rw) = remote.split();

                    let c2r = tokio::io::copy(&mut cr, &mut rw);
                    let r2c = tokio::io::copy(&mut rr, &mut cw);

                    let (res1, res2) = tokio::join!(c2r, r2c);
                    if let Err(e) = res1 {
                        warn!("Client to remote relay error: {}", e);
                    }
                    if let Err(e) = res2 {
                        warn!("Remote to client relay error: {}", e);
                    }
                    info!("Relay closed for {}", target_str);
                }
                Err(e) => {
                    warn!("Failed to connect to target {}: {}", target_str, e);
                    // Send 0x05 = Connection refused / failed
                    let _ = tokio::io::AsyncWriteExt::write_all(&mut stream_compat, &[0x05]).await;
                    let _ = tokio::io::AsyncWriteExt::flush(&mut stream_compat).await;
                }
            }
        }
        TUN_STREAM_ID => {
            info!("Received incoming L3 TUN packet stream from client");
            let mut len_buf = [0u8; 2];
            let mut buf = [0u8; 4096];
            loop {
                if tokio::io::AsyncReadExt::read_exact(&mut stream_compat, &mut len_buf).await.is_err() {
                    break;
                }
                let len = u16::from_be_bytes(len_buf) as usize;
                if len > buf.len() {
                    break;
                }
                if tokio::io::AsyncReadExt::read_exact(&mut stream_compat, &mut buf[..len]).await.is_err() {
                    break;
                }
            }
        }
        unknown => {
            warn!("Received unknown stream type: {}", unknown);
        }
    }

    Ok(())
}
