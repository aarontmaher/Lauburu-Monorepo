#!/bin/bash
# DEPLOY_FULL_SYSTEM.sh
# Anti-Gravity AI Swarm - Full Autonomy Mode
# Deploy everything and let Gordon manage the swarm

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ANTI-GRAVITY AI SWARM - FULL AUTONOMY DEPLOYMENT      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "[CHECK] Prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not installed"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose not installed"; exit 1; }
echo "✓ Docker installed"
echo "✓ Docker Compose installed"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo "[SETUP] Creating .env file..."
    cat > .env << 'EOF'
GEMINI_API_KEY=your_key_here
RAY_HEAD=ray-head:6379
QDRANT_URL=http://qdrant:6333
LOG_TELEMETRY=true
NODE_ENV=production
MOVESENSE_SCAN_INTERVAL=5
EOF
    echo "⚠️  .env created. Update GEMINI_API_KEY if needed."
else
    echo "✓ .env file exists"
fi
echo ""

# Start services
echo "[DEPLOY] Starting all services..."
docker-compose -f docker-compose.separated.yml up -d

# Wait for services to be healthy
echo ""
echo "[WAIT] Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "[HEALTH] Checking service health..."

services=(
    "ray-head:Ray Head"
    "qdrant-db:Qdrant Database"
    "gordon-orchestrator:Gordon Orchestrator"
    "voice-coding:Voice-Only Coding"
    "local-ai-training:Local AI Training"
    "movesense-streaming:Movesense Streaming"
    "monitoring-dashboard:Monitoring Dashboard"
    "api-gateway:API Gateway"
)

for service in "${services[@]}"; do
    IFS=':' read -r container name <<< "$service"
    if docker ps | grep -q $container; then
        echo "✓ $name (running)"
    else
        echo "✗ $name (not running)"
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           DEPLOYMENT COMPLETE - FULL AUTONOMY              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "ACCESS POINTS:"
echo "  📊 Monitoring Dashboard: http://localhost:3003/dashboard"
echo "  🔌 API Gateway:          http://localhost:3000"
echo "  🎤 Voice Coding:         http://localhost:8002"
echo "  🤖 Local AI Training:    http://localhost:8003"
echo "  ❤️  Movesense Stream:     http://localhost:8004"
echo "  🧠 Ray Dashboard:        http://localhost:8265"
echo ""

echo "WHAT GORDON IS DOING:"
echo "  ✓ Monitoring all agents continuously"
echo "  ✓ Management cycle every 5 minutes (no human input needed)"
echo "  ✓ Removing underperformers automatically"
echo "  ✓ Deploying new agents based on workload"
echo "  ✓ Facilitating collective skill learning"
echo "  ✓ Optimizing swarm composition autonomously"
echo "  ✓ Logging all autonomous decisions"
echo ""

echo "WHAT YOU CAN DO:"
echo "  1. Monitor: Open dashboard at http://localhost:3003/dashboard"
echo "  2. Command: Give voice commands (optional)"
echo "  3. Watch: See Gordon manage everything automatically"
echo ""

echo "USEFUL COMMANDS:"
echo "  docker-compose -f docker-compose.separated.yml logs -f gordon-orchestrator"
echo "  docker-compose -f docker-compose.separated.yml logs -f voice-coding"
echo "  docker-compose -f docker-compose.separated.yml logs -f local-ai-training"
echo "  docker-compose -f docker-compose.separated.yml logs -f movesense-streaming"
echo ""

echo "🚀 SYSTEM READY - Gordon is now managing your AI swarm autonomously!"
echo ""
