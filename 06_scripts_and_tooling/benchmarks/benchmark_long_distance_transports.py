import subprocess
import time
import json
import statistics

def ping_test(host, count=10):
    try:
        output = subprocess.check_output(
            ["ping", "-c", str(count), "-W", "1000", host],
            stderr=subprocess.STDOUT,
            text=True
        )
        times = []
        for line in output.split('\n'):
            if "time=" in line:
                try:
                    t = float(line.split("time=")[1].split()[0])
                    times.append(t)
                except:
                    pass
        if times:
            return {
                "min_ms": min(times),
                "avg_ms": statistics.mean(times),
                "max_ms": max(times),
                "packet_loss": "0%" if len(times) == count else f"{(count - len(times))/count * 100}%"
            }
    except Exception as e:
        pass
    return None

def test_transports():
    nodes = {
        "L8_TB4": "10.0.0.8",
        "L8_Tailscale": "100.121.247.8",
        "L3_LAN": "192.168.8.225",
        "L3_Tailscale": "100.101.39.98",
        "L4_Tailscale": "100.99.210.89",
        "L6_Tailscale": "100.114.215.68",
        "L7_Tailscale": "100.78.206.96"
    }
    
    results = {}
    for name, ip in nodes.items():
        print(f"Pinging {name} ({ip})...")
        res = ping_test(ip)
        if res:
            results[name] = res
        else:
            results[name] = {"status": "Unreachable"}
            
    with open("/Volumes/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/TRANSPORT_BENCHMARK.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_transports()
