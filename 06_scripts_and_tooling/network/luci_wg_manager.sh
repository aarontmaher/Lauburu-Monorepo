#!/usr/bin/env bash
# Canonical LuCI WireGuard Manager — GL-BE14000
# Usage: ./luci_wg_manager.sh [list|add|remove|status] [peer_name]
set -euo pipefail

ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
ROUTER_USER="${ROUTER_USER:-root}"
ROUTER_PASS="${ROUTER_PASS:-goldfighting1}"

ssh_router() { ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$ROUTER_USER@$ROUTER_IP" "$@"; }

cmd="${1:-status}"
peer="${2:-}"

case "$cmd" in
  status)
    echo "=== WireGuard Server Status ==="
    ssh_router "wg show wgserver"
    echo ""
    echo "=== WireGuard Peers (UCI) ==="
    ssh_router "uci show wireguard | grep -E '(name|address_v4|allowed_ips)' | grep -v provider | grep -v AzireVPN | grep -v Hideme" 2>/dev/null
    ;;

  list)
    echo "=== Lauburu WG Mesh Peer Table ==="
    printf "%-20s %-15s %-12s %s\n" "NAME" "WG_IP" "HANDSHAKE" "BYTES_TX"
    ssh_router "
      for p in \$(uci show wireguard | grep '=peers' | grep -v 'provider' | cut -d= -f1); do
        NAME=\$(uci get \$p.name 2>/dev/null || echo '?')
        ADDR=\$(uci get \$p.address_v4 2>/dev/null || echo '?')
        echo \"\$NAME \$ADDR\"
      done
    " 2>/dev/null | while read name addr; do
      printf "%-20s %-15s\n" "$name" "$addr"
    done
    echo ""
    echo "=== Active Handshakes ==="
    ssh_router "wg show wgserver latest-handshakes 2>/dev/null" 2>/dev/null
    ;;

  showconf)
    # Generate and display WG conf for a named peer
    [[ -z "$peer" ]] && { echo "Usage: $0 showconf <peer_name>"; exit 1; }
    echo "=== WG Config for $peer ==="
    ssh_router "
      for p in \$(uci show wireguard | grep '=peers' | cut -d= -f1); do
        NAME=\$(uci get \$p.name 2>/dev/null)
        if [ \"\$NAME\" = \"$peer\" ]; then
          PRIV=\$(uci get \$p.private_key 2>/dev/null)
          ADDR=\$(uci get \$p.address_v4 2>/dev/null)
          SRVPUB=\$(wg show wgserver public-key)
          printf '[Interface]\nPrivateKey = %s\nAddress = %s\nDNS = 10.1.0.1\n\n[Peer]\nPublicKey = %s\nAllowedIPs = 10.1.0.0/24, 192.168.8.0/24\nEndpoint = 192.168.8.1:51820\nPersistentKeepalive = 25\n' \"\$PRIV\" \"\$ADDR\" \"\$SRVPUB\"
          break
        fi
      done
    " 2>/dev/null
    ;;

  reload)
    echo "Reloading WireGuard server..."
    ssh_router "wg syncconf wgserver <(wg-quick strip wgserver 2>/dev/null) 2>/dev/null || /etc/init.d/wireguard restart"
    ;;

  luci-token)
    echo "=== LuCI Auth Token ==="
    TOKEN=$(ssh_router "ubus call session login '{\"username\":\"root\",\"password\":\"goldfighting1\"}' 2>/dev/null | grep -o '\"ubus_rpc_session\":\"[^\"]*\"' | cut -d'\"' -f4")
    echo "Token: $TOKEN"
    echo "$TOKEN" > /tmp/luci_token.txt
    echo "(saved to /tmp/luci_token.txt)"
    ;;

  *)
    echo "Usage: $0 [status|list|showconf <name>|reload|luci-token]"
    ;;
esac
