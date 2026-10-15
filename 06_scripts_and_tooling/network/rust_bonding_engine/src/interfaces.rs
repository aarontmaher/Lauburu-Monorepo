use network_interface::{NetworkInterface, NetworkInterfaceConfig, Addr};
use anyhow::Result;

pub fn list_interfaces() -> Result<Vec<InterfaceInfo>> {
    let ifaces = NetworkInterface::show()
        .map_err(|e| anyhow::anyhow!("Failed to list network interfaces: {}", e))?;

    let mut result = Vec::new();
    for iface in ifaces {
        let mut ips = Vec::new();
        for addr in &iface.addr {
            match addr {
                Addr::V4(v4) => ips.push(format!("IPv4: {} (mask: {:?})", v4.ip, v4.netmask)),
                Addr::V6(v6) => ips.push(format!("IPv6: {}", v6.ip)),
            }
        }
        let is_loopback = iface.name.starts_with("lo");
        let is_virtual = iface.name.starts_with("utun") 
            || iface.name.starts_with("bridge") 
            || iface.name.starts_with("gif") 
            || iface.name.starts_with("stf")
            || iface.name.starts_with("awdl")
            || iface.name.starts_with("llw")
            || iface.name.starts_with("anpi");

        result.push(InterfaceInfo {
            name: iface.name,
            ips,
            is_loopback,
            is_virtual,
        });
    }
    Ok(result)
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct InterfaceInfo {
    pub name: String,
    pub ips: Vec<String>,
    pub is_loopback: bool,
    pub is_virtual: bool,
}
