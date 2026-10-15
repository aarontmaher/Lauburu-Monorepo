use anyhow::Result;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_util::compat::FuturesAsyncReadCompatExt;
use tracing::{error, info, warn};
use tun::Configuration;

pub async fn run_tun_client(
    mux: &crate::multiplexer::MuxHandle,
    tun_ip: [u8; 4],
    tun_netmask: [u8; 4],
) -> Result<()> {
    info!("Initializing TUN Interface (L3 Packet Tunnel)...");

    let mut config = Configuration::default();
    config
        .address((tun_ip[0], tun_ip[1], tun_ip[2], tun_ip[3]))
        .netmask((tun_netmask[0], tun_netmask[1], tun_netmask[2], tun_netmask[3]))
        .up();

    #[cfg(target_os = "macos")]
    config.name("utun8");

    let dev = match tun::create_as_async(&config) {
        Ok(d) => d,
        Err(e) => {
            warn!("Could not create TUN interface (requires root / sudo): {}", e);
            warn!("Proceeding in userspace SOCKS5 proxy mode.");
            return Ok(());
        }
    };

    info!("Created TUN interface successfully. IP: {:?}", tun_ip);

    // Open dedicated Yamux sub-stream for TUN traffic
    let mut stream = mux.open_stream().await?.compat();
    // Send Stream Type: TUN_STREAM_ID (0x01)
    stream.write_all(&[crate::protocol::TUN_STREAM_ID]).await?;
    stream.flush().await?;

    let (mut tun_reader, mut tun_writer) = tokio::io::split(dev);
    let (mut stream_reader, mut stream_writer) = tokio::io::split(stream);

    // TUN -> Yamux stream loop
    let tun_to_stream = async move {
        let mut buf = [0u8; 4096];
        loop {
            match tun_reader.read(&mut buf).await {
                Ok(0) => break,
                Ok(n) => {
                    let len = (n as u16).to_be_bytes();
                    if stream_writer.write_all(&len).await.is_err() {
                        break;
                    }
                    if stream_writer.write_all(&buf[..n]).await.is_err() {
                        break;
                    }
                    let _ = stream_writer.flush().await;
                }
                Err(e) => {
                    error!("TUN read error: {}", e);
                    break;
                }
            }
        }
    };

    // Yamux stream -> TUN loop
    let stream_to_tun = async move {
        let mut len_buf = [0u8; 2];
        let mut buf = [0u8; 4096];
        loop {
            if stream_reader.read_exact(&mut len_buf).await.is_err() {
                break;
            }
            let len = u16::from_be_bytes(len_buf) as usize;
            if len > buf.len() {
                error!("Received oversized TUN frame: {} bytes", len);
                break;
            }
            if stream_reader.read_exact(&mut buf[..len]).await.is_err() {
                break;
            }
            if let Err(e) = tun_writer.write_all(&buf[..len]).await {
                error!("TUN write error: {}", e);
                break;
            }
            let _ = tun_writer.flush().await;
        }
    };

    info!("L3 TUN packet forwarding active!");
    tokio::select! {
        _ = tun_to_stream => {},
        _ = stream_to_tun => {},
    }

    Ok(())
}
