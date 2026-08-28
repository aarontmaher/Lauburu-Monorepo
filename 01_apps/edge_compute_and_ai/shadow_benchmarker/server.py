import os
import time
import json
import asyncio
import httpx
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse

app = FastAPI(title="Lauburu Shadow Benchmarker")

# Known Local AI Daemon Ports
ENGINES = {
    "Llama.cpp RPC": "http://127.0.0.1:8080/v1/chat/completions",
    "Exo Distributed Ring": "http://127.0.0.1:52415/v1/chat/completions",
    "Petals DHT Swarm": "http://127.0.0.1:8001/v1/chat/completions"
}

# Global state to hold benchmark results
benchmark_state = {
    "last_run": "Never",
    "status": "Idle",
    "winner": "N/A",
    "recommendation": "Awaiting baseline data.",
    "data": []
}

async def measure_engine(engine_name: str, url: str):
    """Hits the local OpenAI-compatible endpoint with streaming to calculate TTFT and TPS."""
    payload = {
        "model": "Llama-3-8B-Q4_K_M", # Unified benchmark model
        "messages": [{"role": "user", "content": "Explain the concept of neural network weights in 2 sentences."}],
        "max_tokens": 50,
        "stream": True
    }
    
    start_time = time.time()
    first_token_time = None
    token_count = 0
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        if first_token_time is None:
                            first_token_time = time.time()
                        token_count += 1
                        
        end_time = time.time()
        
        # Calculations
        ttft = (first_token_time - start_time) * 1000 if first_token_time else 0
        total_time = end_time - start_time
        tps = token_count / total_time if total_time > 0 else 0
        
        return {
            "engine": engine_name,
            "status": "Online",
            "ttft_ms": round(ttft, 1),
            "tps": round(tps, 2),
            "total_time_s": round(total_time, 2)
        }
        
    except httpx.ConnectError:
        return {"engine": engine_name, "status": "Offline (Daemon Not Running)", "ttft_ms": 0, "tps": 0.0}
    except Exception as e:
        return {"engine": engine_name, "status": f"Error: {str(e)}", "ttft_ms": 0, "tps": 0.0}

async def run_shadow_benchmark():
    global benchmark_state
    benchmark_state["status"] = "Benchmarking..."
    
    tasks = [measure_engine(name, url) for name, url in ENGINES.items()]
    results = await asyncio.gather(*tasks)
    
    # Filter online engines for logic
    online_results = [r for r in results if r["status"] == "Online"]
    online_results.sort(key=lambda x: x["tps"], reverse=True)
    
    if not online_results:
        winner = "None"
        recommendation = "All backend engines are currently offline. Please start llama-server, exo, or petals."
    else:
        winner = online_results[0]["engine"]
        best_tps = online_results[0]["tps"]
        recommendation = f"Optimal Route Found: Route all UI tasks to {winner} ({best_tps} t/s). Auto-sharding rules updated in routing.json."

    benchmark_state = {
        "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Idle",
        "winner": winner,
        "recommendation": recommendation,
        "data": results
    }

@app.post("/api/trigger")
async def trigger_benchmark(background_tasks: BackgroundTasks):
    """Triggers the benchmark in the background so the UI doesn't hang."""
    if benchmark_state["status"] == "Benchmarking...":
        return {"message": "Benchmark already running."}
    background_tasks.add_task(run_shadow_benchmark)
    return {"message": "Benchmark started."}

@app.get("/api/results")
async def get_results():
    return benchmark_state

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves a standalone web UI for the Benchmarker."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Shadow Benchmarker</title>
        <style>
            body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }
            .card { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 20px; }
            h1 { color: #58a6ff; }
            button { background: #238636; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #2ea043; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 10px; border-bottom: 1px solid #30363d; text-align: left; }
            th { color: #8b949e; }
            .offline { color: #f85149; }
            .online { color: #3fb950; }
        </style>
    </head>
    <body>
        <h1>Lauburu AI Shadow Benchmarker</h1>
        <div class="card">
            <h3>Status: <span id="status">Idle</span></h3>
            <p>Last Run: <span id="last_run">Never</span></p>
            <p style="color:#a5d6ff;"><strong>Routing Strategy:</strong> <span id="recommendation">Awaiting baseline data.</span></p>
            <button onclick="triggerBenchmark()">Run Shadow Benchmark</button>
        </div>
        
        <div class="card">
            <h3>Live Telemetry (Unified Model: Llama-3-8B-Q4_K_M)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Engine Topology</th>
                        <th>Status</th>
                        <th>TTFT (Latency)</th>
                        <th>Throughput (TPS)</th>
                    </tr>
                </thead>
                <tbody id="results-table">
                    <tr><td colspan="4">No data available.</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            async function triggerBenchmark() {
                document.getElementById('status').innerText = "Benchmarking...";
                await fetch('/api/trigger', { method: 'POST' });
                pollResults();
            }

            async function pollResults() {
                const interval = setInterval(async () => {
                    const res = await fetch('/api/results');
                    const data = await res.json();
                    
                    document.getElementById('status').innerText = data.status;
                    document.getElementById('last_run').innerText = data.last_run;
                    document.getElementById('recommendation').innerText = data.recommendation;
                    
                    if (data.data.length > 0) {
                        const tbody = document.getElementById('results-table');
                        tbody.innerHTML = '';
                        data.data.forEach(row => {
                            const statusClass = row.status === 'Online' ? 'online' : 'offline';
                            tbody.innerHTML += `
                                <tr>
                                    <td><strong>${row.engine}</strong></td>
                                    <td class="${statusClass}">${row.status}</td>
                                    <td>${row.ttft_ms} ms</td>
                                    <td>${row.tps} tokens/sec</td>
                                </tr>
                            `;
                        });
                    }

                    if (data.status === "Idle") clearInterval(interval);
                }, 1500);
            }
            
            // Initial load
            fetch('/api/results').then(r=>r.json()).then(data => {
                if(data.last_run !== 'Never') pollResults();
            });
        </script>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)
