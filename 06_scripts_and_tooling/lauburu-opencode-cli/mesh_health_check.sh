#!/bin/bash
echo "🔍 Lauburu Distributed Mesh AI Health Check (Rule 8 & 10)..."

check_node() {
  local IP=$1
  local PORT=$2
  local ROLE=$3
  if nc -z -w 1 $IP $PORT 2>/dev/null; then
    echo "✅ [$IP:$PORT] $ROLE -> ONLINE"
  else
    echo "❌ [$IP:$PORT] $ROLE -> OFFLINE"
  fi
}

echo "--- Mac Mini Host (L1) ---"
check_node 127.0.0.1 8082 "Master Local Orchestrator (Qwen 3.8 Max)"

echo "--- Linux Mini (L3 - 100.101.39.98) ---"
check_node 100.101.39.98 8081 "Subordinate Syntax Worker (Qwen 2.5 Coder)"
check_node 100.101.39.98 8083 "Adversarial Red Team (Qwen 3.8 Abliterated)"

echo ""
echo "⚙️ Config Verification: ~/.lauburu/config.yaml"
cat ~/.lauburu/config.yaml | grep "port_"

echo ""
echo "--- ⚡ Thunderbolt 4 Cable Telemetry ---"
# Check physical link presence
if system_profiler SPThunderboltDataType | grep -q "lauburu"; then
    echo "✅ Physical Cable: L8 (lauburu) LINKED"
else
    echo "❌ Physical Cable: L8 (lauburu) UNLINKED"
fi

if system_profiler SPThunderboltDataType | grep -q "Mac14,12"; then
    echo "✅ Physical Cable: L1b (Mac Mini M2 Pro) LINKED"
else
    echo "❌ Physical Cable: L1b (Mac Mini M2 Pro) UNLINKED"
fi

if system_profiler SPThunderboltDataType | grep -q "MacBookPro16,1"; then
    echo "✅ Physical Cable: L2 (MacBook Pro) LINKED"
else
    echo "❌ Physical Cable: L2 (MacBook Pro) UNLINKED"
fi

echo ""
echo "--- ⚡ Thunderbolt IP Bridge Latency ---"
check_ping() {
  local IP=$1
  local ROLE=$2
  if ping -c 1 -W 1 $IP >/dev/null 2>&1; then
    local RTT=$(ping -c 1 $IP | tail -1 | awk -F '/' '{print $5}')
    echo "✅ [$IP] $ROLE -> ONLINE (RTT: ${RTT} ms)"
  else
    echo "❌ [$IP] $ROLE -> OFFLINE"
  fi
}
check_ping 10.0.0.8 "L8 (lauburu) TB4 Bridge"
check_ping 10.0.0.3 "L1b (Mac Mini M2 Pro) TB4 Bridge"
