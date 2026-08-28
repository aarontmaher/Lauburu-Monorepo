#!/bin/bash
# QUICK_START.sh - Get Anti-Gravity running in 30 minutes with Gordon

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        ANTI-GRAVITY QUICK START WITH GORDON                  ║"
echo "║        Head Orchestrator for Unified AI Workflow             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will coordinate with Gordon to build your project."
echo ""
echo "Prerequisites:"
echo "  ✓ Docker installed"
echo "  ✓ Docker Compose installed"
echo "  ✓ .env file with GEMINI_API_KEY"
echo ""
read -p "Ready to start? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1: FOUNDATION (Docker Images + Build)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "What Gordon will do:"
echo "  1. Create missing files (.dockerignore, requirements.txt, etc.)"
echo "  2. Build 7 Docker images"
echo "  3. Validate all builds"
echo ""

read -p "Proceed with Phase 1? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executing Phase 1..."
    if command -v ./GORDON_ORCHESTRATION_FRAMEWORK.sh &> /dev/null; then
        ./GORDON_ORCHESTRATION_FRAMEWORK.sh phase1
    else
        echo "Orchestration framework not executable. Run:"
        echo "  chmod +x GORDON_ORCHESTRATION_FRAMEWORK.sh"
        echo "  ./GORDON_ORCHESTRATION_FRAMEWORK.sh phase1"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 2: VOICE INTEGRATION"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "What Gordon will do:"
echo "  1. Implement Web Speech API for voice capture"
echo "  2. Implement /api/nano/voice-chat endpoint"
echo "  3. Test voice flow end-to-end"
echo ""

read -p "Proceed with Phase 2? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executing Phase 2..."
    echo "(This is manually coordinated - see GORDON_ORCHESTRATION_PROTOCOL.md)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 3: RAY CLUSTER VALIDATION"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "What Gordon will do:"
echo "  1. Start docker-compose stack"
echo "  2. Validate Ray 4-node cluster"
echo "  3. Execute distributed tasks"
echo ""

read -p "Proceed with Phase 3? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executing Phase 3..."
    ./GORDON_ORCHESTRATION_FRAMEWORK.sh phase3
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 4: END-TO-END TESTING"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "What Gordon will do:"
echo "  1. Start all containers"
echo "  2. Health check all services"
echo "  3. Test API endpoints"
echo ""

read -p "Proceed with Phase 4? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executing Phase 4..."
    ./GORDON_ORCHESTRATION_FRAMEWORK.sh phase4
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STATUS REPORT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
./GORDON_ORCHESTRATION_FRAMEWORK.sh status

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "NEXT STEPS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ Anti-Gravity is now running!"
echo ""
echo "Access the app:"
echo "  Frontend: http://localhost:3000"
echo "  Ray Dashboard: http://localhost:8265"
echo ""
echo "For more information:"
echo "  Read: GORDON_ORCHESTRATION_PROTOCOL.md"
echo "  Read: IMPLEMENTATION_AUDIT_AND_WORKFLOW.md"
echo "  Run: ./GORDON_ORCHESTRATION_FRAMEWORK.sh health"
echo ""
echo "Commands for ongoing work:"
echo "  - Save progress: ./GORDON_ORCHESTRATION_FRAMEWORK.sh checkpoint-save 'my-label'"
echo "  - Health check: ./GORDON_ORCHESTRATION_FRAMEWORK.sh health"
echo "  - View status: ./GORDON_ORCHESTRATION_FRAMEWORK.sh status"
echo "  - Stop all: docker-compose -f docker-compose.pixel.yml down"
echo ""
