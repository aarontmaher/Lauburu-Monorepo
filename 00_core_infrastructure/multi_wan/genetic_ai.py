import time
import random
import threading
import uuid
import logging

logger = logging.getLogger("multi_wan.genetic_ai")

class Chromosome:
    def __init__(self, target_node, model_type, temperature, top_k, top_p, penalty):
        self.id = str(uuid.uuid4())[:8]
        self.target_node = target_node
        self.model_type = model_type
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.penalty = penalty
        
        # Fitness scores
        self.accuracy = 0.0
        self.coding = 0.0
        self.reasoning = 0.0
        self.overall = 0.0

class GeneticAIOptimizer:
    def __init__(self):
        self.population_size = 20
        self.generations = 0
        self.population = []
        self.training_logs = []
        self.is_training = False
        self.thread = None
        
        self.nodes = ["apple_m4", "linux_node", "google_pixel", "samsung_s20"]
        self.models = ["llama-3-8b", "qwen-2.5-coder", "mistral-nemo", "phi-3-mini"]
        
        self._initialize_population()
        
    def _initialize_population(self):
        self.population = []
        for _ in range(self.population_size):
            self.population.append(self._random_chromosome())
            
    def _random_chromosome(self):
        return Chromosome(
            target_node=random.choice(self.nodes),
            model_type=random.choice(self.models),
            temperature=round(random.uniform(0.1, 1.5), 2),
            top_k=random.randint(10, 100),
            top_p=round(random.uniform(0.5, 1.0), 2),
            penalty=round(random.uniform(1.0, 1.5), 2)
        )
        
    def _evaluate_fitness(self, chrom: Chromosome):
        # Base capability on model
        base_coding = 60 if "coder" in chrom.model_type else 40
        base_reasoning = 60 if "llama" in chrom.model_type else 50
        base_acc = 50
        
        # Node modifiers (simulate affinity to hardware)
        node_mod = 1.0
        if chrom.target_node == "linux_node":
            node_mod = 1.5 # 4090 GPU
        elif chrom.target_node == "apple_m4":
            node_mod = 1.3 # M4 NPU
        elif chrom.target_node == "google_pixel":
            node_mod = 0.8
            
        # Temperature modifier (lower temp = better coding, higher temp = better reasoning/creativity)
        temp_coding = max(0, 1.0 - (chrom.temperature - 0.2))
        temp_reasoning = min(1.0, chrom.temperature)
        
        chrom.coding = min(100.0, base_coding * node_mod * (0.5 + temp_coding))
        chrom.reasoning = min(100.0, base_reasoning * node_mod * (0.5 + temp_reasoning))
        chrom.accuracy = min(100.0, base_acc * node_mod)
        
        chrom.overall = (chrom.coding + chrom.reasoning + chrom.accuracy) / 3.0
        
    def _log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {msg}"
        self.training_logs.append(log_entry)
        if len(self.training_logs) > 50:
            self.training_logs = self.training_logs[-50:]

    def _crossover(self, parent1, parent2):
        child = Chromosome(
            target_node=parent1.target_node if random.random() > 0.5 else parent2.target_node,
            model_type=parent1.model_type if random.random() > 0.5 else parent2.model_type,
            temperature=(parent1.temperature + parent2.temperature) / 2.0,
            top_k=int((parent1.top_k + parent2.top_k) / 2),
            top_p=(parent1.top_p + parent2.top_p) / 2.0,
            penalty=(parent1.penalty + parent2.penalty) / 2.0
        )
        return child
        
    def _mutate(self, chrom):
        if random.random() < 0.2:
            chrom.target_node = random.choice(self.nodes)
            self._log(f"Mutation: Agent {chrom.id} switched to {chrom.target_node}")
        if random.random() < 0.2:
            chrom.temperature = round(random.uniform(0.1, 1.5), 2)
            self._log(f"Mutation: Agent {chrom.id} adjusted temperature to {chrom.temperature}")
            
    def _train_loop(self):
        self._log("Genetic AI Optimizer Initialized. Starting training stream...")
        while self.is_training:
            self.generations += 1
            self._log(f"--- Generation {self.generations} ---")
            
            # 1. Evaluate
            for chrom in self.population:
                self._evaluate_fitness(chrom)
            
            # Sort by overall fitness
            self.population.sort(key=lambda x: x.overall, reverse=True)
            
            best = self.population[0]
            self._log(f"Evaluated {len(self.population)} AI Configurations.")
            self._log(f"Best Agent: {best.id} ({best.model_type} on {best.target_node}) | Fitness: {best.overall:.1f}")
            
            # 2. Selection (Top 50%)
            survivors = self.population[:self.population_size // 2]
            
            # 3. Crossover & Mutation
            new_population = list(survivors)
            while len(new_population) < self.population_size:
                p1 = random.choice(survivors)
                p2 = random.choice(survivors)
                child = self._crossover(p1, p2)
                self._mutate(child)
                new_population.append(child)
                
            self.population = new_population
            self._log(f"Crossover & Mutation applied. Proceeding to next generation.")
            time.sleep(3.0) # Train step delay
            
    def start_training(self):
        if not self.is_training:
            self.is_training = True
            self.thread = threading.Thread(target=self._train_loop, daemon=True)
            self.thread.start()
            
    def stop_training(self):
        self.is_training = False
        
    def get_leaderboard(self):
        # Return sorted by different categories
        sorted_overall = sorted(self.population, key=lambda x: x.overall, reverse=True)
        sorted_coding = sorted(self.population, key=lambda x: x.coding, reverse=True)
        sorted_reasoning = sorted(self.population, key=lambda x: x.reasoning, reverse=True)
        sorted_accuracy = sorted(self.population, key=lambda x: x.accuracy, reverse=True)
        
        def _to_dict(chrom):
            return {
                "id": chrom.id,
                "target_node": chrom.target_node,
                "model_type": chrom.model_type,
                "temperature": chrom.temperature,
                "overall": round(chrom.overall, 1),
                "coding": round(chrom.coding, 1),
                "reasoning": round(chrom.reasoning, 1),
                "accuracy": round(chrom.accuracy, 1)
            }
            
        return {
            "overall": [_to_dict(c) for c in sorted_overall[:10]],
            "coding": [_to_dict(c) for c in sorted_coding[:10]],
            "reasoning": [_to_dict(c) for c in sorted_reasoning[:10]],
            "accuracy": [_to_dict(c) for c in sorted_accuracy[:10]]
        }
        
    def get_logs(self):
        return {
            "generation": self.generations,
            "logs": self.training_logs
        }
