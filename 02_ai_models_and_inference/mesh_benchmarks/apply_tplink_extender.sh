#!/bin/sh
# TP-LINK / GL.iNET HIGH-GAIN REPEATER BRIDGE CONFIGURATION
echo "📡 Configuring high-gain wireless antennas for 'absolute mesh'..."

# 1. Configure Radio 0 (2.4GHz High Penetration) & Radio 1 (5GHz High Throughput)
uci set wireless.radio0.disabled='0'
uci set wireless.radio0.txpower='23'
uci set wireless.radio0.htmode='HT40'
uci set wireless.radio0.country='AU'

uci set wireless.radio1.disabled='0'
uci set wireless.radio1.txpower='23'
uci set wireless.radio1.htmode='VHT80'
uci set wireless.radio1.country='AU'

# 2. Add STA (Client) Repeater Interface for 'absolute mesh'
uci set wireless.sta=wifi-iface
uci set wireless.sta.device='radio0'
uci set wireless.sta.network='wwan'
uci set wireless.sta.mode='sta'
uci set wireless.sta.ssid='absolute mesh'
uci set wireless.sta.encryption='psk2'
uci set wireless.sta.key='W0rshipDan'

# 3. Configure WWAN Network Interface with DHCP
uci set network.wwan=interface
uci set network.wwan.proto='dhcp'

# 4. Add WWAN to WAN Firewall Zone
uci add_list firewall.@zone[1].network='wwan'

# 5. Commit and Restart Wireless Subsystem
uci commit wireless
uci commit network
uci commit firewall
/etc/init.d/network restart
wifi reload
echo "✅ TP-Link Extender Bridge applied for 'absolute mesh'!"
