use std::net::{Ipv4Addr, Ipv6Addr, SocketAddr};
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};
use anyhow::{anyhow, Result};

#[derive(Debug, Clone)]
pub enum TargetAddr {
    Ip(SocketAddr),
    Domain(String, u16),
}

impl std::fmt::Display for TargetAddr {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TargetAddr::Ip(addr) => write!(f, "{}", addr),
            TargetAddr::Domain(host, port) => write!(f, "{}:{}", host, port),
        }
    }
}

/// Handles initial SOCKS5 handshake and returns the requested destination.
pub async fn handle_socks5_handshake<S>(stream: &mut S) -> Result<TargetAddr>
where
    S: AsyncRead + AsyncWrite + Unpin,
{
    // 1. Version identifier / method selection message
    let mut ver_methods = [0u8; 2];
    stream.read_exact(&mut ver_methods).await?;
    if ver_methods[0] != 0x05 {
        return Err(anyhow!("Unsupported SOCKS version: {}", ver_methods[0]));
    }
    let nmethods = ver_methods[1] as usize;
    let mut methods = vec![0u8; nmethods];
    stream.read_exact(&mut methods).await?;

    // Respond with Method: No Authentication (0x00)
    stream.write_all(&[0x05, 0x00]).await?;
    stream.flush().await?;

    // 2. SOCKS request details
    let mut req_header = [0u8; 4];
    stream.read_exact(&mut req_header).await?;
    if req_header[0] != 0x05 {
        return Err(anyhow!("Invalid request SOCKS version: {}", req_header[0]));
    }
    if req_header[1] != 0x01 {
        stream.write_all(&[0x05, 0x07, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await?;
        return Err(anyhow!("Unsupported command: {}", req_header[1]));
    }

    let target = match req_header[3] {
        0x01 => {
            // IPv4
            let mut ip_bytes = [0u8; 4];
            stream.read_exact(&mut ip_bytes).await?;
            let mut port_bytes = [0u8; 2];
            stream.read_exact(&mut port_bytes).await?;
            let port = u16::from_be_bytes(port_bytes);
            TargetAddr::Ip(SocketAddr::new(Ipv4Addr::from(ip_bytes).into(), port))
        }
        0x03 => {
            // Domain name
            let mut len_byte = [0u8; 1];
            stream.read_exact(&mut len_byte).await?;
            let len = len_byte[0] as usize;
            let mut domain_bytes = vec![0u8; len];
            stream.read_exact(&mut domain_bytes).await?;
            let domain = String::from_utf8(domain_bytes)?;
            let mut port_bytes = [0u8; 2];
            stream.read_exact(&mut port_bytes).await?;
            let port = u16::from_be_bytes(port_bytes);
            TargetAddr::Domain(domain, port)
        }
        0x04 => {
            // IPv6
            let mut ip_bytes = [0u8; 16];
            stream.read_exact(&mut ip_bytes).await?;
            let mut port_bytes = [0u8; 2];
            stream.read_exact(&mut port_bytes).await?;
            let port = u16::from_be_bytes(port_bytes);
            TargetAddr::Ip(SocketAddr::new(Ipv6Addr::from(ip_bytes).into(), port))
        }
        atyp => {
            stream.write_all(&[0x05, 0x08, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await?;
            return Err(anyhow!("Unsupported address type: {}", atyp));
        }
    };

    Ok(target)
}

/// Send SOCKS5 success response to client
pub async fn send_socks5_success<S>(stream: &mut S) -> Result<()>
where
    S: AsyncWrite + Unpin,
{
    stream.write_all(&[0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await?;
    stream.flush().await?;
    Ok(())
}

/// Send SOCKS5 failure response
pub async fn send_socks5_failure<S>(stream: &mut S, err_code: u8) -> Result<()>
where
    S: AsyncWrite + Unpin,
{
    stream.write_all(&[0x05, err_code, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await?;
    stream.flush().await?;
    Ok(())
}

/// Serializes target destination into bytes for sending across the Yamux tunnel
pub fn serialize_target(target: &TargetAddr) -> Vec<u8> {
    let mut buf = Vec::new();
    match target {
        TargetAddr::Ip(SocketAddr::V4(v4)) => {
            buf.push(0x01);
            buf.extend_from_slice(&v4.ip().octets());
            buf.extend_from_slice(&v4.port().to_be_bytes());
        }
        TargetAddr::Ip(SocketAddr::V6(v6)) => {
            buf.push(0x04);
            buf.extend_from_slice(&v6.ip().octets());
            buf.extend_from_slice(&v6.port().to_be_bytes());
        }
        TargetAddr::Domain(domain, port) => {
            buf.push(0x03);
            let bytes = domain.as_bytes();
            buf.push(bytes.len() as u8);
            buf.extend_from_slice(bytes);
            buf.extend_from_slice(&port.to_be_bytes());
        }
    }
    buf
}

/// Deserializes target destination from bytes received across the Yamux tunnel
pub async fn read_target_from_stream<S>(stream: &mut S) -> Result<TargetAddr>
where
    S: AsyncRead + Unpin,
{
    let mut atyp = [0u8; 1];
    stream.read_exact(&mut atyp).await?;
    match atyp[0] {
        0x01 => {
            let mut ip = [0u8; 4];
            stream.read_exact(&mut ip).await?;
            let mut port = [0u8; 2];
            stream.read_exact(&mut port).await?;
            Ok(TargetAddr::Ip(SocketAddr::new(
                Ipv4Addr::from(ip).into(),
                u16::from_be_bytes(port),
            )))
        }
        0x04 => {
            let mut ip = [0u8; 16];
            stream.read_exact(&mut ip).await?;
            let mut port = [0u8; 2];
            stream.read_exact(&mut port).await?;
            Ok(TargetAddr::Ip(SocketAddr::new(
                Ipv6Addr::from(ip).into(),
                u16::from_be_bytes(port),
            )))
        }
        0x03 => {
            let mut len = [0u8; 1];
            stream.read_exact(&mut len).await?;
            let mut domain = vec![0u8; len[0] as usize];
            stream.read_exact(&mut domain).await?;
            let mut port = [0u8; 2];
            stream.read_exact(&mut port).await?;
            Ok(TargetAddr::Domain(
                String::from_utf8(domain)?,
                u16::from_be_bytes(port),
            ))
        }
        other => Err(anyhow!("Unknown target address type: {}", other)),
    }
}
