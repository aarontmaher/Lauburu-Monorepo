# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "torch",
# ]
# ///
import torch
import torch.nn as nn

class AITrainingAnalysisTinyML(nn.Module):
    """
    Specialized TinyML architecture designed for 'AI Training Analysis' and Genetic MoE integration.
    
    Inputs (Features):
      - Loss curves (e.g., current loss, delta loss over last N steps)
      - Iteration speed (tokens/sec or ms/step)
      - Gradient norms (L2 norm of gradients)
      
    Outputs:
      - Fitness Score: Scalar indicating the health and stability of the training branch.
      - Mutation Vector: Dynamic hyperparameter adjustments (e.g., LR scaling, weight decay shift).
    """
    def __init__(self, input_dim=3, hidden_dim=16, mutation_dim=2):
        super(AITrainingAnalysisTinyML, self).__init__()
        # Tiny MLP designed for extreme low-latency execution (sub-ms)
        # to monitor and adjust frontier models during training loops
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # 1. Output a "Fitness Score" based on the loss curves and gradient stability
        self.fitness_head = nn.Sequential(
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid() # Scale [0, 1] for fitness
        )
        
        # 2. Output a "Mutation Vector" (e.g., LR scaling or weight decay shifts)
        self.mutation_head = nn.Sequential(
            nn.Linear(hidden_dim, mutation_dim),
            nn.Tanh() # Scale [-1, 1] for relative shifts
        )

    def forward(self, x):
        """
        x: tensor of shape (batch, input_dim)
           [loss_delta, iter_speed_ms, grad_norm]
        Returns:
           fitness_score: dynamically evaluated fitness of the training branch
           mutation_vector: [lr_shift, wd_shift]
        """
        features = self.network(x)
        fitness_score = self.fitness_head(features)
        mutation_vector = self.mutation_head(features)
        return fitness_score, mutation_vector

# 3. Small integration wrapper showing how the Genetic MoE router will ingest these outputs
class GeneticMoERouterIntegration:
    """
    Integration wrapper for the Genetic MoE Router. 
    Ingests AI Training Analyst outputs to kill failing branches, apply mutations, and spawn next generation.
    """
    def __init__(self, fitness_threshold=0.4):
        self.fitness_threshold = fitness_threshold
        self.analyst_model = AITrainingAnalysisTinyML()
        self.analyst_model.eval()

    def evaluate_and_route(self, branch_id, loss_delta, iter_speed_ms, grad_norm, current_lr, current_wd):
        # Prepare input features
        metrics_tensor = torch.tensor([[loss_delta, iter_speed_ms, grad_norm]], dtype=torch.float32)
        
        # Guard against NaN/Inf in inputs
        if torch.isnan(metrics_tensor).any() or torch.isinf(metrics_tensor).any():
            print(f"[Branch {branch_id}] Warning: Extreme tensor values (NaN/Inf) detected in metrics.")
            fitness_score = 0.0
            lr_mutation = 0.0
            wd_mutation = 0.0
        else:
            with torch.no_grad():
                fitness, mutation_vector = self.analyst_model(metrics_tensor)
                
            fitness_score = fitness.item()
            lr_mutation = mutation_vector[0][0].item()
            wd_mutation = mutation_vector[0][1].item()
        
        print(f"[Branch {branch_id}] Fitness Score: {fitness_score:.4f}")
        
        # Automatically kill failing training branches
        if fitness_score < self.fitness_threshold:
            print(f" -> ❌ KILLING failing training branch '{branch_id}' (Fitness {fitness_score:.4f} < {self.fitness_threshold})")
            return None
        else:
            # Apply the mutations
            # E.g., scaling LR and WD by up to +/- 10% based on the mutation vector
            new_lr = current_lr * (1.0 + (lr_mutation * 0.1))
            new_wd = current_wd * (1.0 + (wd_mutation * 0.1))
            
            # Spawn the next generation
            print(f" -> ✅ SPAWNING next generation for branch '{branch_id}'")
            print(f"    Mutated LR: {current_lr:.6f} -> {new_lr:.6f}")
            print(f"    Mutated WD: {current_wd:.6f} -> {new_wd:.6f}")
            
            return {
                "branch_id": f"{branch_id}_gen_next",
                "learning_rate": new_lr,
                "weight_decay": new_wd
            }

if __name__ == "__main__":
    torch.manual_seed(42) # Make deterministic for testing
    print("Initializing AI Training Analysis TinyML Template with Genetic MoE Integration...\n")
    
    router = GeneticMoERouterIntegration(fitness_threshold=0.4)
    
    print("--- Evaluating Branch A ---")
    # Good loss delta, good speed, stable grad norm
    router.evaluate_and_route("Branch_A", loss_delta=-0.05, iter_speed_ms=12.5, grad_norm=0.8, current_lr=3e-4, current_wd=0.01)
    
    print("\n--- Evaluating Branch B ---")
    # Simulate a branch evaluating (Note: with random init, we might have to force weights or just demonstrate the hook)
    # We pass some dummy metrics.
    router.evaluate_and_route("Branch_B", loss_delta=0.5, iter_speed_ms=45.0, grad_norm=10.5, current_lr=3e-4, current_wd=0.01)
    
    # Save the architecture state
    torch.save(router.analyst_model.state_dict(), "ai_training_analysis_tinyml.pt")
    print("\nModel template saved to ai_training_analysis_tinyml.pt")
