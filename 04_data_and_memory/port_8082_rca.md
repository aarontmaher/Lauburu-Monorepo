# Root Cause Analysis: Port 8082 `HTTP 503 Service Unavailable`

## 1. The Incident
During the AI Debate on backend TUIs, the Sovereign Master Local Orchestrator (`qwen_38_max`) on Port 8082 timed out and returned an `HTTP 503 Service Unavailable` error.

## 2. Root Cause Discovery
Investigation into the local mesh state revealed a cascading failure:

1. **Runaway Inference Process (RAM & CPU Starvation):** A `llama-server` process running an incorrect 1.5B model (`qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`) on Port 8081 was stuck in a runaway loop, consuming **488% CPU for over 12 hours**. This maxed out the Mac Mini's unified memory, forcing the macOS memory compressor to consume over 10 GB of RAM. This severely breached the 9.6 GB physical RAM sanctuary (Rule #3).
2. **Missing Sovereign Master & Red Team:** Neither the Red Team (Port 8083) nor the Sovereign Master `qwen_38_max` (Port 8085) were actually running!
3. **Flawed Proxy Fallback Logic:** The `decentralized_prima_daemon.py` listening on Port 8082 acts as a reverse proxy. When it couldn't find the models on 8085 or 8083, it fell back to Port 8081 (the 1.5B model).
4. **Hardcoded Timeout Drop:** The proxy daemon has a hardcoded `timeout=15.0` for upstream inference. The 1.5B model, bogged down by the huge debate context and system resource starvation, failed to process the prompt within 15 seconds. The proxy dropped the connection and correctly returned the `503 Service Unavailable`. (Ironically, the Red Team's response during the debate was hallucinated by the fallback 1.5B model just before the timeout!)

## 3. Autonomous Remediation Actions Taken
- **Killed Runaway Process:** Executed `kill -9 97041` to terminate the stuck 1.5B model. This instantly restored ~12.2 GB of effective free physical RAM (compressor dropped from 671k to 143k pages).
- **Enforced Rule 8 Invariants:**
  - Booted the correct subordinate worker **Qwen 2.5 Coder 7B** on Port 8081.
  - Booted the correct Red Team **Qwen 3.8 Max 27B Abliterated** on Port 8083.

## 4. Next Steps for Full Healing
To fully restore the Sovereign Master Orchestrator, we must:
1. Increase the `timeout=15.0` limit in `decentralized_prima_daemon.py` to `120.0` seconds to accommodate deep reasoning and large contexts.
2. Launch the true `Qwen 3.8 Max` engine on Port 8085 via the `tb4_prp_sharding_coordinator.py` Pipelined-Ring over the Thunderbolt 4 bridge.
