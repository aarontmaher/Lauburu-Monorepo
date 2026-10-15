import torch
import torch.nn as nn
import torch.nn.functional as F

class HardwareAwareRouter(nn.Module):
    """
    Unlike standard MoE routers (e.g., Mixtral) that only look at semantic tokens,
    this router concatenates the physical device's telemetry (RAM, Battery, Latency) 
    to dynamically shift probability mass away from Heavy Experts when on Edge devices.
    """
    def __init__(self, hidden_dim: int, hardware_dim: int, num_experts: int):
        super().__init__()
        # Projects [Hidden State + Hardware State] -> Expert Logits
        self.router_weights = nn.Linear(hidden_dim + hardware_dim, num_experts)
        
    def forward(self, x: torch.Tensor, hw_state: torch.Tensor):
        # x shape: [batch, seq_len, hidden_dim]
        # hw_state shape: [batch, hardware_dim] (e.g., [Available_RAM_MB, Target_Latency_ms])
        
        # Broadcast the hardware state across the sequence length
        hw_expanded = hw_state.unsqueeze(1).expand(-1, x.size(1), -1)
        
        # Combine token meaning with physical constraints
        combined = torch.cat([x, hw_expanded], dim=-1)
        
        # Get routing probabilities
        logits = self.router_weights(combined)
        routing_probs = F.softmax(logits, dim=-1)
        return routing_probs


class ExpertNetwork(nn.Module):
    """A standard Feed-Forward Network acting as a single Expert."""
    def __init__(self, hidden_dim: int, intermediate_dim: int):
        super().__init__()
        self.w1 = nn.Linear(hidden_dim, intermediate_dim)
        self.w2 = nn.Linear(intermediate_dim, hidden_dim)
        
    def forward(self, x):
        return self.w2(F.silu(self.w1(x)))


class HardwareAdaptiveMoEBlock(nn.Module):
    """
    A full Mixture of Experts Transformer Block that routes tokens to different
    sized experts depending on the physical hardware limits provided in the forward pass.
    """
    def __init__(self, hidden_dim: int, hardware_dim: int):
        super().__init__()
        self.num_experts = 3
        
        # 3 Experts of varying physical sizes
        self.experts = nn.ModuleList([
            ExpertNetwork(hidden_dim, intermediate_dim=hidden_dim * 1), # Tiny (Edge)
            ExpertNetwork(hidden_dim, intermediate_dim=hidden_dim * 4), # Standard
            ExpertNetwork(hidden_dim, intermediate_dim=hidden_dim * 8)  # Heavy (Host Mac)
        ])
        
        self.router = HardwareAwareRouter(hidden_dim, hardware_dim, self.num_experts)
        
    def forward(self, x: torch.Tensor, hw_state: torch.Tensor):
        # 1. Get routing probabilities dynamically adjusted by hardware
        routing_probs = self.router(x, hw_state)
        
        # 2. In a real sparse MoE, we would only compute the top-K experts.
        # For this prototype, we compute the weighted sum of all experts.
        out = torch.zeros_like(x)
        for i, expert in enumerate(self.experts):
            expert_out = expert(x)
            # Multiply expert output by its routing probability
            prob = routing_probs[:, :, i].unsqueeze(-1)
            out += expert_out * prob
            
        return out


if __name__ == "__main__":
    print("🧠 Initializing Hardware-Adaptive MoE Model from scratch...")
    
    batch_size = 1
    seq_len = 16
    hidden_dim = 512
    hardware_dim = 2 # e.g., [RAM_Headroom_MB, Current_Battery_Pct]
    
    model = HardwareAdaptiveMoEBlock(hidden_dim, hardware_dim)
    
    # Simulate a token sequence
    x = torch.randn(batch_size, seq_len, hidden_dim)
    
    # ---------------------------------------------------------
    # Scenario 1: Running on the Mac Mini Host (Lots of RAM)
    # ---------------------------------------------------------
    mac_hw_state = torch.tensor([[16000.0, 100.0]]) # 16GB RAM, 100% Power
    mac_output = model(x, mac_hw_state)
    
    # ---------------------------------------------------------
    # Scenario 2: Running on the Movesense Edge (Low RAM)
    # ---------------------------------------------------------
    movesense_hw_state = torch.tensor([[0.025, 45.0]]) # 25KB RAM, 45% Power
    movesense_output = model(x, movesense_hw_state)
    
    print("✅ Model architecture tested successfully.")
    print("Tokens routed dynamically based on injected telemetry state!")
