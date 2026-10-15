#!/usr/bin/env bash
# ==============================================================================
# ROUTER SEAWEEDFS MESH CLUSTER BRIDGE
# Subsystem: 00_core_infrastructure/seaweedfs
# Connects node storage volume servers with GL-BE14000 Sovereign Gateway Master
# ==============================================================================
set -euo pipefail

ROUTER_IP="${ROUTER_MASTER_IP:-192.168.8.1}"
MASTER_PORT="9333"
FILER_PORT="8888"
S3_PORT="8333"
WEBDAV_PORT="7333"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}[*] Probing Router SeaweedFS Cluster Endpoints (${ROUTER_IP})...${NC}"

# Check Master
if curl -s -I "http://${ROUTER_IP}:${MASTER_PORT}/dir/status" | grep -q "200 OK"; then
    echo -e "${GREEN}[+] Master Server Online at http://${ROUTER_IP}:${MASTER_PORT}${NC}"
else
    echo -e "${RED}[-] Master Server not reachable.${NC}"
fi

# Check Filer
if curl -s -I "http://${ROUTER_IP}:${FILER_PORT}/" | grep -q "200 OK"; then
    echo -e "${GREEN}[+] Filer Server Online at http://${ROUTER_IP}:${FILER_PORT}${NC}"
else
    echo -e "${RED}[-] Filer Server not reachable.${NC}"
fi

# Check S3 Gateway
if curl -s "http://${ROUTER_IP}:${S3_PORT}/" | grep -q "ListAllMyBucketsResult"; then
    echo -e "${GREEN}[+] S3 Gateway Online at http://${ROUTER_IP}:${S3_PORT}${NC}"
else
    echo -e "${RED}[-] S3 Gateway not reachable.${NC}"
fi

# Check WebDAV
if curl -s -I "http://${ROUTER_IP}:${WEBDAV_PORT}/" 2>/dev/null | grep -q -E "200|405"; then
    echo -e "${GREEN}[+] WebDAV Gateway Online at http://${ROUTER_IP}:${WEBDAV_PORT}${NC}"
else
    echo -e "${RED}[-] WebDAV Gateway not reachable.${NC}"
fi

echo -e "${CYAN}[*] Cluster Status Summary:${NC}"
curl -s "http://${ROUTER_IP}:${MASTER_PORT}/dir/status" | python3 -m json.tool || true
