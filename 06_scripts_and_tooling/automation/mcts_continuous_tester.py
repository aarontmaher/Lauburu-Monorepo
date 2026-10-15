import time
import random
from mesh_mcts_orchestrator_v2 import mcts_reasoning_loop

PROMPTS = [
    "Prove that the square root of 2 is irrational.",
    "Solve the equation: x^2 - 5x + 6 = 0 step by step.",
    "Explain the concept of quantum entanglement using an analogy.",
    "Design a distributed system architecture for a high-throughput chat application.",
    "Write a Python function to solve the traveling salesperson problem using dynamic programming.",
    "Explain the mechanism of action of CRISPR-Cas9.",
    "What is the mathematical relationship between the Fibonacci sequence and the Golden Ratio?",
    "Evaluate the time complexity of the quicksort algorithm in its best, worst, and average cases."
]

def daemon_loop():
    print("Starting Continuous MCTS Tester Daemon...")
    while True:
        try:
            prompt = random.choice(PROMPTS)
            print(f"\n[TESTER] Initiating MCTS for prompt: '{prompt}'")
            result = mcts_reasoning_loop(prompt)
            print(f"\n[TESTER] Final Result:\n{result}\n")
            time.sleep(30) # Wait 30 seconds before next prompt
        except KeyboardInterrupt:
            print("Shutting down tester daemon.")
            break
        except Exception as e:
            print(f"Error in tester: {e}")
            time.sleep(30)

if __name__ == "__main__":
    daemon_loop()
