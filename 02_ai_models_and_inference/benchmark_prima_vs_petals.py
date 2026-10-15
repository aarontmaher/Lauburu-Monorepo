import time
import httpx
import json
import subprocess

def measure_rtt(ip):
    try:
        out = subprocess.check_output(f"ping -c 3 {ip}", shell=True).decode()
        avg = [line for line in out.split('\n') if 'avg' in line][0].split('/')[4]
        return float(avg)
    except:
        return float('inf')

def run_inference_test(name, url, payload, timeout=10.0):
    start = time.time()
    try:
        r = httpx.post(url, json=payload, timeout=timeout)
        duration = time.time() - start
        if r.status_code == 200:
            data = r.json()
            tokens = data.get("usage", {}).get("completion_tokens", 0)
            if tokens == 0 and "choices" in data:
                tokens = len(data["choices"][0]["message"]["content"].split()) * 1.3
            return duration, tokens
        else:
            return "--", "--"
    except Exception as e:
        return "--", "--"

def main():
    print("=======================================================================")
    print(" 🚀 SIDE-BY-SIDE BENCHMARK: prima.cpp vs. Petals DHT Transport ")
    print("=======================================================================")
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a speed test bot."},
            {"role": "user", "content": "Write a 50 word summary of quantum mechanics."}
        ],
        "max_tokens": 50,
        "temperature": 0.0
    }

    # 1. prima.cpp (Local TB4 Ring)
    print("\n[1] Testing prima.cpp (Local Thunderbolt 4 Ring / Port 8082)...")
    prima_url = "http://127.0.0.1:8082/v1/chat/completions"
    prima_dur, prima_tok = run_inference_test("prima.cpp", prima_url, payload)
    
    # Measure RTT to TB4 L2 Node (169.254.187.138 from Rule 2)
    tb4_rtt = measure_rtt("169.254.187.138")
    
    if prima_dur != "--":
        prima_tps = float(prima_tok) / prima_dur
        print(f"  -> Hardware Link Latency (TB4): {tb4_rtt} ms RTT")
        print(f"  -> Inference Latency: {prima_dur:.3f} s")
        print(f"  -> Throughput: {prima_tps:.1f} Tokens/s")
    else:
        print("  -> Status: UNREACHABLE / TIMEOUT")

    # 2. Petals DHT (Linux Head Node / Tailscale)
    print("\n[2] Testing Petals DHT (Linux Head Node / 100.101.39.98:8080)...")
    petals_url = "http://100.101.39.98:8080/v1/chat/completions"
    petals_dur, petals_tok = run_inference_test("Petals DHT", petals_url, payload, timeout=3.0)
    
    ts_rtt = measure_rtt("100.101.39.98")
    
    if petals_dur != "--":
        petals_tps = float(petals_tok) / petals_dur
        print(f"  -> Hardware Link Latency (1GbE/TS): {ts_rtt} ms RTT")
        print(f"  -> Inference Latency: {petals_dur:.3f} s")
        print(f"  -> Throughput: {petals_tps:.1f} Tokens/s")
    else:
        print(f"  -> Hardware Link Latency (1GbE/TS): {ts_rtt} ms RTT")
        print("  -> Inference Latency: --")
        print("  -> Throughput: -- (Waiting for DHT Bootstrap or Target Down)")

    print("\n=======================================================================")

if __name__ == "__main__":
    main()
