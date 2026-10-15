use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;
use aggligator::transport::Connector;
use aggligator_transport_tcp::TcpConnector;
use anyhow::{anyhow, Result};
use tokio::net::TcpListener;
use tokio_util::compat::{FuturesAsyncReadCompatExt, TokioAsyncReadCompatExt};
use tracing::{error, info, warn};
use yamux::Mode;

use crate::multiplexer::spawn_multiplexer;
use crate::protocol::SOCKS5_STREAM_ID;
use crate::socks5::{
    handle_socks5_handshake, send_socks5_failure, send_socks5_success, serialize_target,
};

pub struct ClientConfig {
    pub targets: Vec<String>,
    pub default_port: u16,
    pub socks5_bind: SocketAddr,
    pub enable_tun: bool,
}

pub async fn run_client(config: ClientConfig) -> Result<()> {
    info!("Starting Lauburu Multipath Bonding Client");
    info!("Target servers: {:?}", config.targets);
    info!("SOCKS5 local proxy will listen on: {}", config.socks5_bind);

    // 1. Setup Aggligator multi-interface connector
    let mut connector = Connector::new();
    let mut tcp_conn = TcpConnector::new(config.targets.iter().map(|s| s.as_str()), config.default_port).await?;

    // Enable multi-interface bonding across all active physical interfaces
    tcp_conn.set_multi_interface(true);
    tcp_conn.set_resolve_interval(Duration::from_secs(10));
    connector.add(tcp_conn);

    let control = connector.control();

    info!("Connecting aggregated channels across available physical interfaces...");
    let channel = connector
        .channel()
        .ok_or_else(|| anyhow!("Failed to initialize connector channel"))?
        .await?;

    info!("Bonded connection established! Session ID: {}", channel.id());

    let stream = channel.into_stream();
    let mux_handle = Arc::new(spawn_multiplexer(stream.compat(), Mode::Client));

    // 2. Spawn Live Link Telemetry Task
    let ctrl = control.clone();
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(3)).await;
            if ctrl.is_terminated() {
                warn!("Bonded connection terminated");
                break;
            }
            let links = ctrl.links();
            let active_count = links.iter().filter(|l| l.is_working()).count();

            info!(
                "=== [Bonded Network Status] Active Links: {} / {} ===",
                active_count,
                links.len()
            );
            for (idx, link) in links.iter().enumerate() {
                let st = link.stats();
                let rtt = st.roundtrip.as_secs_f64() * 1000.0;
                let (tx_speed, rx_speed) = if let Some(ts) = st.time_stats.first() {
                    (ts.send_speed(), ts.recv_speed())
                } else {
                    (0.0, 0.0)
                };
                let tx_kbps = (tx_speed * 8.0) / 1000.0;
                let rx_kbps = (rx_speed * 8.0) / 1000.0;
                let status = if link.is_working() { "ONLINE" } else { "OFFLINE/STALLED" };

                info!(
                    "  [Link #{}] Status: {:<14} | RTT: {:>6.2} ms | TX: {:>8.1} kbps | RX: {:>8.1} kbps | Sent: {} KB",
                    idx + 1,
                    status,
                    rtt,
                    tx_kbps,
                    rx_kbps,
                    st.total_sent / 1024
                );
            }
        }
    });

    // 3. Optional TUN interface if requested
    if config.enable_tun {
        let mux_clone = mux_handle.clone();
        tokio::spawn(async move {
            if let Err(e) = crate::tun_engine::run_tun_client(&mux_clone, [10, 88, 0, 2], [255, 255, 255, 0]).await {
                error!("TUN engine error: {}", e);
            }
        });
    }

    // 4. Start SOCKS5 Local Proxy Listener
    let socks_listener = TcpListener::bind(config.socks5_bind).await?;
    info!("Local SOCKS5 proxy active on {}", config.socks5_bind);
    info!("You can configure your browser, curl (-x socks5://{}), or system to use this proxy!", config.socks5_bind);

    loop {
        match socks_listener.accept().await {
            Ok((mut client_socket, client_addr)) => {
                let mux = mux_handle.clone();
                tokio::spawn(async move {
                    if let Err(e) = handle_socks5_client(&mut client_socket, mux).await {
                        warn!("SOCKS5 client [{}] error: {}", client_addr, e);
                    }
                });
            }
            Err(e) => {
                error!("Error accepting SOCKS5 connection: {}", e);
            }
        }
    }
}

async fn handle_socks5_client(
    client_socket: &mut tokio::net::TcpStream,
    mux: Arc<crate::multiplexer::MuxHandle>,
) -> Result<()> {
    // Perform SOCKS5 handshake
    let target = match handle_socks5_handshake(client_socket).await {
        Ok(t) => t,
        Err(e) => {
            let _ = send_socks5_failure(client_socket, 0x01).await;
            return Err(e);
        }
    };

    info!("SOCKS5 request for destination: {}", target);

    // Open a new multiplexed sub-stream over the bonded Aggligator tunnel
    let mut sub_stream = match mux.open_stream().await {
        Ok(s) => s.compat(),
        Err(e) => {
            let _ = send_socks5_failure(client_socket, 0x01).await;
            return Err(anyhow!("Failed to open bonded multiplexer stream: {}", e));
        }
    };

    // Send Stream Type: SOCKS5_STREAM_ID
    tokio::io::AsyncWriteExt::write_all(&mut sub_stream, &[SOCKS5_STREAM_ID]).await?;

    // Send serialized target
    let target_bytes = serialize_target(&target);
    tokio::io::AsyncWriteExt::write_all(&mut sub_stream, &target_bytes).await?;
    tokio::io::AsyncWriteExt::flush(&mut sub_stream).await?;

    // Wait for remote server connection confirmation (0x00 = success)
    let mut status_buf = [0u8; 1];
    tokio::io::AsyncReadExt::read_exact(&mut sub_stream, &mut status_buf).await?;
    if status_buf[0] != 0x00 {
        let _ = send_socks5_failure(client_socket, status_buf[0]).await;
        return Err(anyhow!("Remote server failed to connect to target"));
    }

    // Acknowledge success to the local SOCKS5 client
    send_socks5_success(client_socket).await?;

    // Bidirectional proxy
    let (mut cr, mut cw) = client_socket.split();
    let (mut sr, mut sw) = tokio::io::split(sub_stream);

    let c2s = tokio::io::copy(&mut cr, &mut sw);
    let s2c = tokio::io::copy(&mut sr, &mut cw);

    let _ = tokio::join!(c2s, s2c);
    Ok(())
}
