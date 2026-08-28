#!/usr/bin/env bash
# ==============================================================================
# LAUBURU SEAWEEDFS 3-NODE RAFT HA CLUSTER VALIDATOR
# Subsystem: 00_core_infrastructure/scripts
# Description: Programmatically audits Raft quorum, leader convergence,
#              derived gRPC companion ports (:19333), and volume availability.
# ==============================================================================
set -u

# --- Color Formatting ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

MASTER_PEERS="${1:-100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333}"
TIMEOUT=2

IFS=',' read -ra PEER_ARRAY <<< "$MASTER_PEERS"
TOTAL_PEERS=${#PEER_ARRAY[@]}
QUORUM_REQUIRED=$(( (TOTAL_PEERS / 2) + 1 ))

ONLINE_COUNT=0
LEADERS_FOUND=()
TOPOLOGY_IDS=()
TOTAL_FREE_VOLUMES=0
TOTAL_MAX_VOLUMES=0

echo -e "${BOLD}${BLUE}================================================================${NC}"
echo -e "${BOLD}${BLUE}       SEAWEEDFS 3-NODE RAFT CONSENSUS AUDIT REPORT             ${NC}"
echo -e "${BOLD}${BLUE}================================================================${NC}"
echo -e "Target Masters:    ${CYAN}$MASTER_PEERS${NC}"
echo -e "Total Configured:  ${BOLD}$TOTAL_PEERS${NC}"
echo -e "Quorum Threshold:  ${BOLD}$QUORUM_REQUIRED${NC} nodes required for 2/3 majority"
echo "----------------------------------------------------------------"

for peer in "${PEER_ARRAY[@]}"; do
    HOST=$(echo "$peer" | cut -d: -f1)
    PORT=$(echo "$peer" | cut -d: -f2)
    GRPC_PORT=$((PORT + 10000))

    echo -e "\n${BOLD}[Node: $peer]${NC}"
    
    # 1. Check Derived Companion gRPC Socket (:19333)
    GRPC_STATUS="CLOSED"
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w "$TIMEOUT" "$HOST" "$GRPC_PORT" 2>/dev/null; then
            GRPC_STATUS="OPEN"
        fi
    elif timeout "$TIMEOUT" bash -c "</dev/tcp/$HOST/$GRPC_PORT" 2>/dev/null; then
        GRPC_STATUS="OPEN"
    fi

    if [ "$GRPC_STATUS" = "OPEN" ]; then
        echo -e "  • gRPC Companion Socket (:$GRPC_PORT): ${GREEN}OPEN / REACHABLE${NC}"
    else
        echo -e "  • gRPC Companion Socket (:$GRPC_PORT): ${YELLOW}UNREACHABLE / OFF-MESH${NC}"
    fi

    # 2. Query /cluster/status
    CLUSTER_RESP=$(curl -s --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" "http://$peer/cluster/status" 2>/dev/null || echo "")

    if [ -z "$CLUSTER_RESP" ]; then
        echo -e "  • HTTP REST API Status:              ${RED}OFFLINE / UNRESPONSIVE${NC}"
        continue
    fi

    ONLINE_COUNT=$((ONLINE_COUNT + 1))
    IS_LEADER=$(echo "$CLUSTER_RESP" | jq -r '.IsLeader // false' 2>/dev/null || echo "false")
    REPORTED_LEADER=$(echo "$CLUSTER_RESP" | jq -r '.Leader // "NONE"' 2>/dev/null || echo "NONE")
    PEER_LIST=$(echo "$CLUSTER_RESP" | jq -r '.Peers | join(", ")' 2>/dev/null || echo "")

    if [ "$IS_LEADER" = "true" ]; then
        echo -e "  • Raft Role:                         ${GREEN}${BOLD}★ ACTIVE RAFT LEADER ★${NC}"
    else
        echo -e "  • Raft Role:                         ${CYAN}FOLLOWER${NC}"
    fi
    echo -e "  • Reported Leader:                   ${BOLD}$REPORTED_LEADER${NC}"
    echo -e "  • Active Raft Peers:                 $PEER_LIST"

    if [ "$REPORTED_LEADER" != "NONE" ] && [ "$REPORTED_LEADER" != "null" ] && [ -n "$REPORTED_LEADER" ]; then
        LEADERS_FOUND+=("$REPORTED_LEADER")
    fi

    # 3. Query /dir/status
    DIR_RESP=$(curl -s --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" "http://$peer/dir/status" 2>/dev/null || echo "")
    if [ -n "$DIR_RESP" ]; then
        TOPOLOGY_ID=$(echo "$DIR_RESP" | jq -r '.TopologyId // "UNKNOWN"' 2>/dev/null || echo "UNKNOWN")
        FREE_VOLS=$(echo "$DIR_RESP" | jq -r '.Topology.Free // 0' 2>/dev/null || echo "0")
        MAX_VOLS=$(echo "$DIR_RESP" | jq -r '.Topology.Max // 0' 2>/dev/null || echo "0")
        TOPOLOGY_IDS+=("$TOPOLOGY_ID")
        
        echo -e "  • Cluster Topology ID:               $TOPOLOGY_ID"
        echo -e "  • Volume Storage Slots:              Free: ${BOLD}$FREE_VOLS${NC} / Max: ${BOLD}$MAX_VOLS${NC}"

        if [ "$IS_LEADER" = "true" ]; then
            TOTAL_FREE_VOLUMES=$FREE_VOLS
            TOTAL_MAX_VOLUMES=$MAX_VOLS
        fi
    fi
done

echo "----------------------------------------------------------------"
echo -e "${BOLD}${BLUE}=================== CONSENSUS ASSESSMENT ======================${NC}"

# Quorum Evaluation
echo -e "Online Master Nodes:           $ONLINE_COUNT / $TOTAL_PEERS"

QUORUM_OK=0
if [ "$ONLINE_COUNT" -ge "$QUORUM_REQUIRED" ]; then
    echo -e "Quorum Health Status:          ${GREEN}${BOLD}✔ QUORUM HEALTHY ($ONLINE_COUNT >= $QUORUM_REQUIRED)${NC}"
    QUORUM_OK=1
else
    echo -e "Quorum Health Status:          ${RED}${BOLD}✘ CRITICAL: QUORUM LOST ($ONLINE_COUNT < $QUORUM_REQUIRED)${NC}"
fi

# Split-Brain Evaluation
UNIQUE_LEADERS=()
if [ ${#LEADERS_FOUND[@]} -gt 0 ]; then
    while IFS= read -r line; do
        [ -n "$line" ] && UNIQUE_LEADERS+=("$line")
    done < <(printf "%s\n" "${LEADERS_FOUND[@]}" | sort -u)
fi

SPLIT_BRAIN_OK=0
if [ ${#UNIQUE_LEADERS[@]} -eq 1 ]; then
    echo -e "Consensus Leader:              ${GREEN}${BOLD}${UNIQUE_LEADERS[0]}${NC}"
    echo -e "Split-Brain Guard:             ${GREEN}PASSED (Unified Single Leader)${NC}"
    SPLIT_BRAIN_OK=1
elif [ ${#UNIQUE_LEADERS[@]} -gt 1 ]; then
    echo -e "Split-Brain Guard:             ${RED}${BOLD}CRITICAL ERROR: SPLIT BRAIN DETECTED! (${UNIQUE_LEADERS[*]:-})${NC}"
else
    echo -e "Consensus Leader:              ${YELLOW}NONE (Leader election pending, offline, or stalled)${NC}"
fi

# Topology ID Alignment
UNIQUE_TOPOLOGIES=()
if [ ${#TOPOLOGY_IDS[@]} -gt 0 ]; then
    while IFS= read -r line; do
        [ -n "$line" ] && UNIQUE_TOPOLOGIES+=("$line")
    done < <(printf "%s\n" "${TOPOLOGY_IDS[@]}" | sort -u)
fi

if [ ${#UNIQUE_TOPOLOGIES[@]} -eq 1 ]; then
    echo -e "Topology ID Consistency:       ${GREEN}ALIGNED (${UNIQUE_TOPOLOGIES[0]})${NC}"
elif [ ${#UNIQUE_TOPOLOGIES[@]} -gt 1 ]; then
    echo -e "Topology ID Consistency:       ${RED}MISMATCH DETECTED: Stale Raft metadata present across nodes${NC}"
fi

# Live Volume Allocation Smoke Test
ASSIGN_OK=1
if [ "$SPLIT_BRAIN_OK" -eq 1 ] && [ "$QUORUM_OK" -eq 1 ]; then
    LEADER_HOST=$(echo "${UNIQUE_LEADERS[0]}" | cut -d: -f1)
    LEADER_PORT=$(echo "${UNIQUE_LEADERS[0]}" | cut -d: -f2 | cut -d. -f1)
    echo -e "\n${BOLD}[Live Write Allocation Smoke Test]${NC}"
    ASSIGN_RESP=$(curl -s --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" "http://$LEADER_HOST:$LEADER_PORT/dir/assign" 2>/dev/null || echo "")
    ASSIGN_FID=$(echo "$ASSIGN_RESP" | jq -r '.fid // "FAIL"' 2>/dev/null || echo "FAIL")
    ASSIGN_URL=$(echo "$ASSIGN_RESP" | jq -r '.url // "NONE"' 2>/dev/null || echo "NONE")
    
    if [ "$ASSIGN_FID" != "FAIL" ] && [ "$ASSIGN_FID" != "null" ]; then
        echo -e "  • File ID Allocation (/dir/assign): ${GREEN}${BOLD}SUCCESS (FID: $ASSIGN_FID at $ASSIGN_URL)${NC}"
    else
        echo -e "  • File ID Allocation (/dir/assign): ${YELLOW}SKIPPED / NO ACTIVE VOLUMES ($ASSIGN_RESP)${NC}"
        ASSIGN_OK=0
    fi
fi

echo -e "${BOLD}${BLUE}================================================================${NC}"

# Structured Exit Codes:
# 0 = Quorum Healthy & Consensus Established
# 1 = Quorum Lost
# 2 = Split Brain Detected
# 3 = Write Allocation Failed with Quorum Active
if [ "$QUORUM_OK" -ne 1 ]; then
    exit 1
elif [ "$SPLIT_BRAIN_OK" -ne 1 ]; then
    exit 2
elif [ "$ASSIGN_OK" -ne 1 ]; then
    exit 3
else
    exit 0
fi
