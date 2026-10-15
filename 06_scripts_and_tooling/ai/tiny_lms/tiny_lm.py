# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mlx",
# ]
# ///
import mlx.core as mx
import mlx.nn as nn
import math

# Tiny LM built from scratch in Python using Apple's MLX framework
# Minimal implementation of an efficient Apple Silicon transformer

class TinyConfig:
    vocab_size: int = 32000
    hidden_dim: int = 256
    num_layers: int = 2
    num_heads: int = 8

class Attention(nn.Module):
    def __init__(self, config: TinyConfig):
        super().__init__()
        self.q_proj = nn.Linear(config.hidden_dim, config.hidden_dim, bias=False)
        self.k_proj = nn.Linear(config.hidden_dim, config.hidden_dim, bias=False)
        self.v_proj = nn.Linear(config.hidden_dim, config.hidden_dim, bias=False)
        self.o_proj = nn.Linear(config.hidden_dim, config.hidden_dim, bias=False)
        self.num_heads = config.num_heads
        self.head_dim = config.hidden_dim // config.num_heads

    def __call__(self, x, mask=None):
        B, L, D = x.shape
        q, k, v = self.q_proj(x), self.k_proj(x), self.v_proj(x)
        
        # Reshape for multi-head attention: (B, L, heads, head_dim) -> (B, heads, L, head_dim)
        q = q.reshape(B, L, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        k = k.reshape(B, L, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        v = v.reshape(B, L, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        
        # mlx provides scaled_dot_product_attention or we can do it manually
        scale = math.sqrt(self.head_dim)
        scores = (q @ k.transpose(0, 1, 3, 2)) / scale
        
        if mask is not None:
            scores = scores + mask

        probs = mx.softmax(scores, axis=-1)
        out = probs @ v
        
        # Reshape back to (B, L, D)
        out = out.transpose(0, 2, 1, 3).reshape(B, L, D)
        return self.o_proj(out)

class TransformerBlock(nn.Module):
    def __init__(self, config: TinyConfig):
        super().__init__()
        self.attention = Attention(config)
        self.ln1 = nn.LayerNorm(config.hidden_dim)
        self.mlp = nn.Sequential(
            nn.Linear(config.hidden_dim, 4 * config.hidden_dim),
            nn.GELU(),
            nn.Linear(4 * config.hidden_dim, config.hidden_dim)
        )
        self.ln2 = nn.LayerNorm(config.hidden_dim)

    def __call__(self, x, mask=None):
        x = x + self.attention(self.ln1(x), mask)
        x = x + self.mlp(self.ln2(x))
        return x

class TinyLM(nn.Module):
    def __init__(self, config: TinyConfig):
        super().__init__()
        self.embed = nn.Embedding(config.vocab_size, config.hidden_dim)
        self.layers = [TransformerBlock(config) for _ in range(config.num_layers)]
        self.norm = nn.LayerNorm(config.hidden_dim)
        self.lm_head = nn.Linear(config.hidden_dim, config.vocab_size, bias=False)

    def __call__(self, x):
        x = self.embed(x)
        # Create causal mask
        B, L, D = x.shape
        mask = nn.MultiHeadAttention.create_additive_causal_mask(L)
        
        for layer in self.layers:
            x = layer(x, mask)
        x = self.norm(x)
        return self.lm_head(x)

if __name__ == "__main__":
    print("Tiny LM in MLX - Minimal implementation initialized.")
    config = TinyConfig()
    model = TinyLM(config)
    
    # Generate random tokens and test forward pass
    x = mx.random.randint(0, config.vocab_size, (1, 10))
    logits = model(x)
    print(f"Logits shape: {logits.shape}")
