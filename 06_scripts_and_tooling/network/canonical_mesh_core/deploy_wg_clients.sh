#!/usr/bin/env bash
# Canonical WireGuard Client Config Deployer — Lauburu Mesh
# Pulls peer configs from GL-BE14000 router via SSH, deploys to devices via ADB
set -euo pipefail

ROUTER="root@192.168.8.1"
SSH_OPTS="-o ConnectTimeout=5 -o StrictHostKeyChecking=no"

ssh_router() { ssh $SSH_OPTS "$ROUTER" "$@"; }

SRV_PUBKEY=$(ssh_router "wg show wgserver public-key" 2>/dev/null)
echo "Server public key: $SRV_PUBKEY"

gen_conf() {
  local peer_uci="$1"
  local priv addr
  priv=$(ssh_router "uci get wireguard.${peer_uci}.private_key" 2>/dev/null)
  addr=$(ssh_router "uci get wireguard.${peer_uci}.address_v4" 2>/dev/null)
  cat <<EOF
[Interface]
PrivateKey = $priv
Address = $addr
DNS = 10.1.0.1

[Peer]
PublicKey = $SRV_PUBKEY
AllowedIPs = 10.1.0.0/24, 192.168.8.0/24
Endpoint = 192.168.8.1:51820
PersistentKeepalive = 25
EOF
}

deploy_android() {
  local adb_target="$1" peer_uci="$2" label="$3"
  echo "=== Deploying to $label ($adb_target) ==="
  gen_conf "$peer_uci" > /tmp/${label}_wg.conf
  adb -s "$adb_target" push /tmp/${label}_wg.conf /sdcard/lauburu_wg.conf
  # Import via WireGuard app intent
  adb -s "$adb_target" shell "am start -a android.intent.action.VIEW \
    -d 'file:///sdcard/lauburu_wg.conf' \
    -t 'application/x-wireguard-profile' 2>&1 | head -3"
  echo "Config pushed to $label. Open WireGuard app to activate."
}

deploy_mac() {
  local ssh_target="$1" peer_uci="$2" label="$3"
  echo "=== Deploying to $label ($ssh_target) ==="
  gen_conf "$peer_uci" > /tmp/${label}_wg.conf
  scp $SSH_OPTS /tmp/${label}_wg.conf "${ssh_target}:/tmp/lauburu_wg.conf"
  ssh $SSH_OPTS "$ssh_target" "
    mkdir -p ~/.config/wireguard
    cp /tmp/lauburu_wg.conf ~/.config/wireguard/lauburu.conf
    echo 'Config at ~/.config/wireguard/lauburu.conf — activate via WireGuard app or wg-quick'
  "
}

case "${1:-all}" in
  s20)    deploy_android "192.168.8.131:5555" "peer_2006" "L7_SamsungS20" ;;
  pixel)
    ssh_router "adb connect 10.76.201.252:5555 2>/dev/null; sleep 1; adb -s 10.76.201.252:5555 push /tmp/pixel10_wg.conf /sdcard/lauburu_wg.conf" 2>/dev/null
    echo "Pixel WG conf pushed via router ADB. Open WireGuard app on Pixel to import."
    ;;
  macair) deploy_mac "aaron@192.168.8.221" "peer_2004" "L5_MacBookAir" ;;
  all)
    deploy_android "192.168.8.131:5555" "peer_2006" "L7_SamsungS20" || true
    echo "---"
    deploy_mac "aaron@192.168.8.221" "peer_2004" "L5_MacBookAir" || true
    ;;
  *)
    echo "Usage: $0 [s20|pixel|macair|all]"
    ;;
esac
