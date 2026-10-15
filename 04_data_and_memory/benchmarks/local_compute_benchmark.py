import time
import argparse
import platform

def benchmark_pytorch(size=4096, iterations=50):
    try:
        import torch
    except ImportError:
        return "PyTorch not installed"

    device = torch.device('cpu')
    if torch.backends.mps.is_available():
        device = torch.device('mps')
    elif torch.cuda.is_available():
        device = torch.device('cuda')

    print(f"Testing PyTorch on {device}...")
    
    # Warmup
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    for _ in range(5):
        _ = torch.matmul(a, b)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    elif device.type == 'mps':
        torch.mps.synchronize()

    start_time = time.time()
    for _ in range(iterations):
        _ = torch.matmul(a, b)
    
    if device.type == 'cuda':
        torch.cuda.synchronize()
    elif device.type == 'mps':
        torch.mps.synchronize()
        
    end_time = time.time()
    
    total_time = end_time - start_time
    tflops = (2 * (size ** 3) * iterations) / (total_time * 1e12)
    return f"{tflops:.2f} TFLOPs (Time: {total_time:.2f}s)"

def benchmark_mlx(size=4096, iterations=50):
    try:
        import mlx.core as mx
    except ImportError:
        return "MLX not installed/supported"
    
    print("Testing MLX (Metal GPU)...")
    
    # Warmup
    a = mx.random.normal((size, size))
    b = mx.random.normal((size, size))
    mx.eval(mx.matmul(a, b))

    start_time = time.time()
    for _ in range(iterations):
        c = mx.matmul(a, b)
    mx.eval(c)
    end_time = time.time()

    total_time = end_time - start_time
    tflops = (2 * (size ** 3) * iterations) / (total_time * 1e12)
    return f"{tflops:.2f} TFLOPs (Time: {total_time:.2f}s)"

if __name__ == "__main__":
    print(f"=== Single Device Local Benchmark ===")
    print(f"Node: {platform.node()} | OS: {platform.system()} {platform.machine()}")
    print("-" * 40)
    
    pt_result = benchmark_pytorch()
    print(f"PyTorch Result: {pt_result}\n")
    
    mlx_result = benchmark_mlx()
    print(f"MLX Result:     {mlx_result}\n")
