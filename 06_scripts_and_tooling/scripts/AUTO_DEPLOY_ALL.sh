#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                            ║"
echo "║  🤖 ANTIGRAVITY - Full Automated Deployment                               ║"
echo "║                                                                            ║"
echo "║  • Deploy integrated AI app via ADB                                       ║"
echo "║  • Setup Google Chat integration                                          ║"
echo "║  • No manual copy-paste needed                                            ║"
echo "║                                                                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

cd "/Volumes/antigravity/Grappling Movesense  AI"

echo "📋 Optional Configuration (press Enter to skip):"
echo ""

read -p "Mac IP address: " MAC_IP
read -p "Gemini API key: " GEMINI_KEY
read -p "Google Chat webhook URL: " CHAT_WEBHOOK

echo ""
echo "🚀 Starting automated deployment..."
echo ""

python3 antigravity_automated_deploy.py "$MAC_IP" "$GEMINI_KEY" "$CHAT_WEBHOOK"

