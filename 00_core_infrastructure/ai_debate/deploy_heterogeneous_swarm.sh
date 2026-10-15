#!/bin/bash
# 00_core_infrastructure/ai_debate/deploy_heterogeneous_swarm.sh
# Deploys the Heterogeneous Debate Swarm concurrently across the Lauburu Mesh
# according to the updated hardware matrix capacities.

echo "Deploying Heterogeneous Debate Swarm..."

# 1. Sovereign Master Orchestrator -> L1 Mac Mini M4 Pro (Port 8082)
echo "Configuring Node: L1 Mac Mini M4 Pro (127.0.0.1:8082)"
cat << 'EOF' > /Volumes/Lauburu-Monorepo/00_core_infrastructure/ai_debate/config_qwen_l1.json
{
  "model": "Qwen-3.8-Max-27B.gguf",
  "engine": "prima.cpp",
  "port": 8082,
  "role": "Sovereign Master Orchestrator",
  "backend": "Metal",
  "max_vram_gb": 16.0
}
EOF
echo "[OK] L1 Qwen 3.8 Configured."

# 2. Devil's Advocate -> L3 Linux Mini (Port 8083)
# Uses the massive 32GB RAM entirely for Gemma 4 31B (CPU/AVX2).
echo "Configuring Node: L3 Linux Mini (100.101.39.98:8083)"
cat << 'EOF' > /Volumes/Lauburu-Monorepo/00_core_infrastructure/ai_debate/config_gemma_l3.json
{
  "model": "Gemma-4-31B-Abliterated.gguf",
  "engine": "llama.cpp",
  "port": 8083,
  "role": "Devil's Advocate",
  "backend": "CPU-AVX2",
  "max_ram_gb": 22.0
}
EOF
echo "[OK] L3 Gemma 4 Configured."

# 3. Syntax / Code Specialist -> L1b M2 Pro / L5 Air (Port 8084)
echo "Configuring Node: L1b Mac Mini M2 Pro (169.254.122.75:8084)"
cat << 'EOF' > /Volumes/Lauburu-Monorepo/00_core_infrastructure/ai_debate/config_deepseek_l1b.json
{
  "model": "DeepSeek-30B-Coder.gguf",
  "engine": "mlx_lm",
  "port": 8084,
  "role": "Syntax/Code Specialist",
  "backend": "Metal",
  "max_vram_gb": 16.0
}
EOF
echo "[OK] L1b DeepSeek Configured."

echo ""
echo "Deployment manifest generated successfully in 00_core_infrastructure/ai_debate/"
echo "Ready to launch heterogeneous swarm."
