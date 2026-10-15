#!/bin/sh

# Set LAN VLAN to exclude port 0
uci set network.vlan_lan.ports='1 2 3 4 5t'

# Create WAN VLAN for port 0
uci set network.vlan_wan=switch_vlan
uci set network.vlan_wan.device='switch0'
uci set network.vlan_wan.vlan='3'
uci set network.vlan_wan.ports='0 5t'

# Reassign WAN interface to eth1.3 (Port 0)
uci set network.wan.device='eth1.3'

# Ensure other potential WAN sources are disabled
uci set network.secondwan.disabled='1'
uci set network.tethering.disabled='1'
uci set network.wwan.disabled='1'

# Disable their ipv6 counterparts just in case
uci set network.secondwan6.disabled='1'
uci set network.wan6.disabled='1'
uci set network.tethering6.disabled='1'
uci set network.wwan6.disabled='1'

uci commit network

# Restart network in background so script completes
(/etc/init.d/network restart >/dev/null 2>&1) &
