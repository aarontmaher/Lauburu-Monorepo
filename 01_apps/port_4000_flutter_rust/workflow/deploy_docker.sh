#!/usr/bin/env bash
# ==============================================================================
# Lauburu Port 4000 Console: Containerized Docker Deployment Script
# Managed via Docker MCP & Container-First Orchestration Protocol
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "======================================================================"
echo "🐳 LAUBURU PORT 4000: DOCKER CONTAINERIZED DEPLOYMENT"
echo "======================================================================"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker CLI not found. Please ensure Docker is running."
    exit 1
fi

cd "$ROOT_DIR"

echo "📦 1/3 Building and launching containers via docker-compose.port4000.yml..."
docker compose -f docker-compose.port4000.yml up -d --build

echo ""
echo "⏳ 2/3 Waiting for container health checks..."
sleep 5

docker ps --filter "name=lauburu-port4000" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🔍 3/3 Testing containerized endpoints..."
if curl -s http://127.0.0.1:4000/health >/dev/null 2>&1; then
    echo "   ✅ Containerized Port 4000 Backend is HEALTHY!"
else
    echo "   ⚠️  Container starting up, check logs: docker logs lauburu-port4000-backend"
fi

echo ""
echo "======================================================================"
echo "🎉 DOCKER DEPLOYMENT COMPLETE!"
echo "   • Containerized Backend: http://localhost:4000/health"
echo "   • Containerized UI Web:  http://localhost:4001"
echo "======================================================================"
