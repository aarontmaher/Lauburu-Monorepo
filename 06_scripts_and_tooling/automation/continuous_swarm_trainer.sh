#!/bin/bash
echo "Starting 24/7 Continuous IDE, MoE, Swarm Topology, LoRA Trainer & Dynamic Tool Generator..."
while true; do
    date >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    
    echo "--- 1. Running Custom MoE Gating Router Training ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/moe_router_trainer.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1

    echo "--- 2. Running IDE Routing Evaluator (Generates Failures) ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/ide_routing_evaluator.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1
    
    echo "--- 3. Running Full Network Auto-Discovery & Swarm Generation ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/full_network_local_swarm_developer.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1
    
    echo "--- 4. Running Frontier Hybrid Swarm Collaboration Benchmark ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/benchmarks/frontier_hybrid_swarm_evaluator.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1
    
    echo "--- 5. 🛠️ EXECUTING LEVEL 5 AUTONOMY: DYNAMIC TOOL GENERATOR 🛠️ ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/dynamic_tool_generator.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1
    
    echo "--- 6. ⚡ EXECUTING INTRA-DAY HIGH-FREQUENCY LORA DISTILLATION ⚡ ---" >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log
    python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/high_frequency_lora_trainer.py >> /Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_training.log 2>&1
    
    sleep 300 # Run every 5 minutes
done
