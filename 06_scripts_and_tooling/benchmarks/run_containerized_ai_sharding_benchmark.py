import subprocess
import time

def run_ollama_benchmark(runtime: str) -> dict:
    print(f"[{runtime}] Running Ollama AI inference benchmark...")
    
    # Start ollama server in background
    server_cmd = [runtime, "run", "-d", "--name", f"ollama_{runtime}", "ollama/ollama"]
    subprocess.run(server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(3) # Wait for server to boot
    
    t0 = time.time()
    try:
        # Run inference using qwen:0.5b
        run_cmd = [runtime, "exec", f"ollama_{runtime}", "ollama", "run", "qwen:0.5b", "Write a 50 word poem about space."]
        result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=60)
        t_elapsed = time.time() - t0
        
        # Calculate approximate TPS based on output length
        words = len(result.stdout.split())
        tps = words / t_elapsed if t_elapsed > 0 else 0
        
        return {
            "runtime": runtime,
            "status": "PASSED" if result.returncode == 0 else "FAILED",
            "approx_tps": round(tps, 2),
            "total_time_sec": round(t_elapsed, 2)
        }
    except Exception as e:
        return {
            "runtime": runtime,
            "status": "ERROR",
            "error": str(e)
        }
    finally:
        subprocess.run([runtime, "rm", "-f", f"ollama_{runtime}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("Starting Container AI Inference Benchmark (Ollama Qwen:0.5b)...")
    results = []
    
    # Pre-pull image
    subprocess.run(["docker", "pull", "ollama/ollama"], stdout=subprocess.DEVNULL)
    subprocess.run(["podman", "pull", "docker.io/ollama/ollama"], stdout=subprocess.DEVNULL)
    
    for rt in ["docker", "podman"]:
        res = run_ollama_benchmark(rt)
        results.append(res)
        print(f"Result for {rt}: {res}")
        
    print("\n--- Summary ---")
    for r in results:
        print(f"{r['runtime'].upper()}: TPS = ~{r.get('approx_tps', 0.0)} words/sec, TotalTime = {r.get('total_time_sec', 0.0)}s")

if __name__ == '__main__':
    main()
