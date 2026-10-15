import asyncio
from micro_network_healer import MicroNetworkHealer
from genetic_sharding_optimizer import GeneticShardingOptimizer

async def main():
    print("=== Lauburu Network MicroLM & Genetic Sharding Pod ===")
    
    # 1. Initialize Network Healer MicroLM
    healer = MicroNetworkHealer(model_path="/home/linuxmini/model_vault_gguf/SmolLM2-360M-Instruct-Q8_0.gguf")
    
    # 2. Initialize Genetic Optimizer
    optimizer = GeneticShardingOptimizer(population_size=5, mutation_rate=0.15)
    
    # Run both loops concurrently
    await asyncio.gather(
        healer.continuous_healing_loop(),
        optimizer.evolution_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Pod terminated by user.")
