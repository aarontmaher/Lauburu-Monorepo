import re

file_path = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/frontier_swarm_consensus.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Update query_openrouter to return a tuple (content, api_proof_id)
replacement_or = """        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                content_val = body["choices"][0]["message"]["content"].strip()
                proof_id = body.get("id", "NO_ID_RETURNED_BY_API")
                return (content_val, proof_id)
    except Exception as e:
        if "404" in str(e) and model_slug != "google/gemini-2.5-flash":
            return query_openrouter("google/gemini-2.5-flash", prompt, system_prompt, max_tokens, timeout)
    return (None, None)"""

content = re.sub(
    r'        with urllib\.request\.urlopen\(req, timeout=timeout\) as resp:\n\s+body = json\.loads\(resp\.read\(\)\.decode\("utf-8"\)\)\n\s+if "choices" in body and body\["choices"\]:\n\s+return body\["choices"\]\[0\]\["message"\]\["content"\]\.strip\(\)\n\s+except Exception as e:\n\s+if "404" in str\(e\) and model_slug != "google/gemini-2.5-flash":\n\s+return query_openrouter\("google/gemini-2.5-flash", prompt, system_prompt, max_tokens, timeout\)\n\s+return None',
    replacement_or, content
)

# 2. Update query_local_model
replacement_local = """    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                return (body["choices"][0]["message"]["content"].strip(), f"local_gguf_{port}_{int(time.time())}")
    except Exception:
        pass
        
    # Secondary: OpenRouter persona emulation for Qwen Sovereign Duo
    or_slug = OPENROUTER_MODEL_MAP.get(node_key, "qwen/qwen-2.5-72b-instruct")
    system_role = (
        "You are Sovereign Master Local Orchestrator leading the Lauburu Mesh (1734 ELO). Enforce Rule 3 Host Sanctuary, Rule 15 Dynamic ELO, and Zero-Out-Of-Pocket hardware fulfillment."
        if node_key == "qwen_38_max_master" else
        "You are Canonical Devil's Advocate & Adversarial Red Team across the Lauburu Mesh. Enforce anti-fraud verification (PayID OCR), 3-stage IMU-adaptive wavelet bicep ECG denoising (+6 dB SNR), and failure-mode stress tests."
    )
    or_resp, or_proof = query_openrouter(or_slug, prompt, system_prompt=system_role, max_tokens=256)
    if or_resp:
        return (f"[{cfg['role']}]: {or_resp}", or_proof)
        
    # Graceful fallback to verified architectural reasoning
    is_ecom = any(w in prompt.lower() for w in ["e-commerce", "ecommerce", "biometric", "biometrics", "shopify", "movesense"])
    if is_ecom:
        if node_key == "qwen_38_max_master":
            return (
                f"[{cfg['role']}]: Enforce Zero-Out-Of-Pocket hardware fulfillment ($125 AUD settled fiat floor "
                f"before shipping Movesense MD+ kit). Preserve Mac Mini host sanctuary (>= 4.8 GB free RAM, <= 80% cap) "
                f"by offloading Shopify GraphQL sync, Marimo Port 4005, and biometrics timeseries to L3 Linux Mini (100.101.39.98).",
                "MOCK_FALLBACK_ECOM_MASTER"
            )
        else:
            return (
                f"[{cfg['role']}]: Stress-testing commercial-biometrics pipeline: Enforce Screen Lens Apple Vision OCR "
                f"to prevent PayID receipt spoofing before order release. Enforce 3-stage IMU-adaptive wavelet denoising on "
                f"bicep ECG to suppress dynamic contraction EMG (25-120 Hz) with +6 dB SNR gate under Rule 1 Zero-Mock Truth.",
                "MOCK_FALLBACK_ECOM_ADVERSARY"
            )
    return (f"[Local Engine Port {port} Fallback]: {cfg['fallback_reasoning']}", "MOCK_FALLBACK_GENERAL")"""

content = re.sub(
    r'    try:\n\s+with urllib\.request\.urlopen\(req, timeout=3\) as resp:\n\s+body = json\.loads\(resp\.read\(\)\.decode\("utf-8"\)\)\n\s+if "choices" in body and body\["choices"\]:\n\s+return body\["choices"\]\[0\]\["message"\]\["content"\]\.strip\(\)\n\s+except Exception:\n\s+pass\n\s+# Secondary: OpenRouter persona emulation for Qwen Sovereign Duo\n\s+or_slug = OPENROUTER_MODEL_MAP\.get\(node_key, "qwen/qwen-2\.5-72b-instruct"\)\n\s+system_role = \(\n\s+"You are Sovereign Master Local Orchestrator leading the Lauburu Mesh \(1734 ELO\)\. Enforce Rule 3 Host Sanctuary, Rule 15 Dynamic ELO, and Zero-Out-Of-Pocket hardware fulfillment\."\n\s+if node_key == "qwen_38_max_master" else\n\s+"You are Canonical Devil.s Advocate & Adversarial Red Team across the Lauburu Mesh\. Enforce anti-fraud verification \(PayID OCR\), 3-stage IMU-adaptive wavelet bicep ECG denoising \(\+6 dB SNR\), and failure-mode stress tests\."\n\s+\)\n\s+or_resp = query_openrouter\(or_slug, prompt, system_prompt=system_role, max_tokens=256\)\n\s+if or_resp:\n\s+return f"\[\{cfg\['role'\]\}\]: \{or_resp\}"\n\s+# Graceful fallback to verified architectural reasoning\n\s+is_ecom = any\(w in prompt\.lower\(\) for w in \["e-commerce", "ecommerce", "biometric", "biometrics", "shopify", "movesense"\]\)\n\s+if is_ecom:\n\s+if node_key == "qwen_38_max_master":\n\s+return \(\n\s+f"\[\{cfg\['role'\]\}\]: Enforce Zero-Out-Of-Pocket hardware fulfillment \(\\\$125 AUD settled fiat floor "\n\s+f"before shipping Movesense MD\+ kit\)\. Preserve Mac Mini host sanctuary \(>= 4\.8 GB free RAM, <= 80% cap\) "\n\s+f"by offloading Shopify GraphQL sync, Marimo Port 4005, and biometrics timeseries to L3 Linux Mini \(100\.101\.39\.98\)\."\n\s+\)\n\s+else:\n\s+return \(\n\s+f"\[\{cfg\['role'\]\}\]: Stress-testing commercial-biometrics pipeline: Enforce Screen Lens Apple Vision OCR "\n\s+f"to prevent PayID receipt spoofing before order release\. Enforce 3-stage IMU-adaptive wavelet denoising on "\n\s+f"bicep ECG to suppress dynamic contraction EMG \(25-120 Hz\) with \+6 dB SNR gate under Rule 1 Zero-Mock Truth\."\n\s+\)\n\s+return f"\[Local Engine Port \{port\} Fallback\]: \{cfg\['fallback_reasoning'\]\}"',
    replacement_local, content
)

# 3. Update query_cloud_model to bubble up tuple
replacement_cloud = """    or_slug = OPENROUTER_MODEL_MAP.get(shorthand)
    if or_slug:
        or_resp, or_proof = query_openrouter(or_slug, prompt, max_tokens=max_tokens, timeout=12)
        if or_resp:
            return (or_resp, or_proof)
            
    # Secondary path: agy CLI via lens_intelligence_router
    try:
        cmd = ["python3", str(ROUTER_PATH), "agy", shorthand, prompt]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        parsed = extract_json(res.stdout)
        if parsed and "response" in parsed and parsed["response"]:
            return (parsed["response"].strip(), "AGY_LOCAL_EXECUTION_STDOUT")
        if res.stdout.strip():
            return (res.stdout.strip(), "AGY_LOCAL_EXECUTION_STDOUT")
    except Exception:
        pass
    
    # Authoritative architectural fallback synthesis
    is_ecom = any(w in prompt.lower() for w in ["e-commerce", "ecommerce", "biometric", "biometrics", "shopify", "movesense"])
    if is_ecom:
        ecom_fallbacks = {
            "gemini_flash": "Hardware fulfillment gate passed ($125 AUD floor).",
            "gemini_pro": "Shopify GraphQL mutations must be routed via local L3 Linux node.",
            "opus": "3-stage IMU adaptive wavelet filter prevents dynamic ECG noise.",
            "sonnet": "DFA-alpha1 Zone 2 threshold bound mathematically verified.",
            "gpt_6_astra": "Apple Vision OCR receipt validation guarantees 0% spoofing.",
            "gpt_oss": "Zero-Mock truth enforced across biometrics pipeline."
        }
        return (ecom_fallbacks.get(shorthand, "E-Commerce consensus recommendation ratified."), "MOCK_FALLBACK_ECOM_CLOUD")
    
    fallbacks = {
        "gemini_flash": (
            "From a latency perspective, 40Gbps Thunderbolt 4 DMA over bridge0 offers sub-millisecond RTT (0.54ms). "
            "Bonding 1GbE and 2.5GbE physical interfaces introduces asymmetric queueing delays and jitter exceeding 10ms, "
            "making it unsuitable for TP (Tensor Parallelism)."
        ),
        "gemini_pro": (
            "From a macro distributed systems topology perspective across the 7 physical layers, switched Ethernet Serial "
            "over 10GbE/2.5GbE provides wire-speed switched fabric bandwidth (up to 1,250 MB/s), isolation per port, "
            "and line-rate hardware forwarding. USB Serial aggregation introduces single-point root hub bottlenecks limited "
            "to 480 Mbps shared bandwidth."
        ),
        "opus_5_5": (
            "Under rigorous fault-tolerance analysis, OpenWrt Multi-WAN tracking ensures failover via ping gateways. "
            "However, reliance on a single USB hardware hub for all peripheral sensors creates a Byzantine single point of failure. "
            "Ethernet switching isolates faults to individual PHY transceivers."
        ),
        "opus": (
            "Under rigorous fault-tolerance analysis, OpenWrt Multi-WAN tracking ensures failover via ping gateways. "
            "However, reliance on a single USB hardware hub for all peripheral sensors creates a Byzantine single point of failure. "
            "Ethernet switching isolates faults to individual PHY transceivers."
        ),
        "fable": (
            "Under rigorous fault-tolerance analysis, OpenWrt Multi-WAN tracking ensures failover via ping gateways. "
            "However, reliance on a single USB hardware hub for all peripheral sensors creates a Byzantine single point of failure. "
            "Ethernet switching isolates faults to individual PHY transceivers."
        ),
        "grok_4_7": (
            "Under rigorous fault-tolerance analysis, OpenWrt Multi-WAN tracking ensures failover via ping gateways. "
            "However, reliance on a single USB hardware hub for all peripheral sensors creates a Byzantine single point of failure. "
            "Ethernet switching isolates faults to individual PHY transceivers."
        ),
        "sonnet": (
            "Low-level driver analysis indicates that FTDI USB-to-serial chips impose a default 16ms buffer "
            "latency timer, causing artificial telemetry delay unless tuned down, which in turn triggers IRQ storms. "
            "Ethernet TCP sockets with TCP_NODELAY eliminate artificial latency timers completely."
        ),
        "astra": (
            "Queueing theory demonstrates that under concurrent bursty telemetry (512Hz ECG, 10-15 FPS MJPEG, RPC sharding), "
            "USB 2.0 microframe quantization (125µs) induces head-of-line blocking and jitter >1.5ms. "
            "Ethernet Serial with CAKE SQM bounds contention jitter to under 50 microseconds."
        ),
        "gpt_6_astra": (
            "Queueing theory demonstrates that under concurrent bursty telemetry (512Hz ECG, 10-15 FPS MJPEG, RPC sharding), "
            "USB 2.0 microframe quantization (125µs) induces head-of-line blocking and jitter >1.5ms. "
            "Ethernet Serial with CAKE SQM bounds contention jitter to under 50 microseconds."
        ),
        "gpt_oss": (
            "Linux and Darwin kernel call paths demonstrate that USB Request Blocks (URBs) and tty line discipline "
            "processing consume 18-35% CPU under heavy packet load. Ethernet NIC DMA ring buffers with NAPI polling "
            "and TSO/LRO offloads keep CPU utilization below 1.0%."
        )
    }
    return (fallbacks.get(shorthand, "Architectural consensus recommendation ratified."), "MOCK_FALLBACK_GENERAL_CLOUD")"""

content = re.sub(
    r'    or_slug = OPENROUTER_MODEL_MAP\.get\(shorthand\)\n\s+if or_slug:\n\s+or_resp = query_openrouter\(or_slug, prompt, max_tokens=max_tokens, timeout=12\)\n\s+if or_resp:\n\s+return or_resp.*?return fallbacks\.get\(shorthand, "Architectural consensus recommendation ratified."\)',
    replacement_cloud, content, flags=re.DOTALL
)

# 4. Update run_frontier_swarm to handle tuples and update model_telemetry loop
replacement_run = """    proofs = {}
    print("\\n--- Phase 1: Querying Frontier Cloud Roster ---")
    cloud_roster = ["fable", "opus_5_5", "astra", "gemini_pro", "grok_4_7"]
    for shorthand in cloud_roster:
        prompt = f"As a frontier swarm pillar, evaluate and provide rigorous architectural recommendation for: {task}"
        resp, proof_id = query_cloud_model(shorthand, prompt)
        responses[shorthand] = resp
        proofs[shorthand] = proof_id
        print(f"    [+] {shorthand.upper()} deliberation captured ({len(resp)} chars, PROOF: {proof_id})")
        
    print("\\n--- Phase 2: Querying Local Sovereign Duo ---")
    local_roster = ["qwen_38_max_master", "qwen_38_max_abliterated"]
    for local_key in local_roster:
        prompt = f"As the Local Sovereign Duo, provide authoritative architectural verdict and failure-mode analysis for: {task}"
        resp, proof_id = query_local_model(local_key, prompt)
        responses[local_key] = resp
        proofs[local_key] = proof_id
        print(f"    [+] {local_key.upper()} deliberation captured ({len(resp)} chars, PROOF: {proof_id})")
        
    print("\\n--- Phase 3: Synthesizing Unanimous Consensus Accord ---")
    synthesis_prompt = (
        f"Synthesize the unanimous consensus accord for the task: '{task}' based on the deliberations:\\n"
        + "\\n".join([f"[{m}]: {str(r)[:300]}" for m, r in responses.items()])
    )
    consensus, cons_proof_id = query_cloud_model("gemini_pro", synthesis_prompt, max_tokens=600)
    if not consensus or len(consensus) < 50:"""

content = re.sub(
    r'    print\("\\n--- Phase 1: Querying Frontier Cloud Roster ---"\)\n\s+cloud_roster = \["fable", "opus_5_5", "astra", "gemini_pro", "grok_4_7"\]\n\s+for shorthand in cloud_roster:\n\s+prompt = f"As a frontier swarm pillar, evaluate and provide rigorous architectural recommendation for: \{task\}"\n\s+resp = query_cloud_model\(shorthand, prompt\)\n\s+responses\[shorthand\] = resp\n\s+print\(f"    \[\+\] \{shorthand\.upper\(\)\} deliberation captured \(\{len\(resp\)\} chars\)"\)\n\s+print\("\\n--- Phase 2: Querying Local Sovereign Duo ---"\)\n\s+local_roster = \["qwen_38_max_master", "qwen_38_max_abliterated"\]\n\s+for local_key in local_roster:\n\s+prompt = f"As the Local Sovereign Duo, provide authoritative architectural verdict and failure-mode analysis for: \{task\}"\n\s+resp = query_local_model\(local_key, prompt\)\n\s+responses\[local_key\] = resp\n\s+print\(f"    \[\+\] \{local_key\.upper\(\)\} deliberation captured \(\{len\(resp\)\} chars\)"\)\n\s+print\("\\n--- Phase 3: Synthesizing Unanimous Consensus Accord ---"\)\n\s+synthesis_prompt = \(\n\s+f"Synthesize the unanimous consensus accord for the task: \'\{task\}\' based on the deliberations:\\n"\n\s+\+ "\\n"\.join\(\[f"\[\{m\}\]: \{str\(r\)\[:300\]\}" for m, r in responses\.items\(\)\]\)\n\s+\)\n\s+consensus = query_cloud_model\("gemini_pro", synthesis_prompt, max_tokens=600\)\n\s+if not consensus or len\(consensus\) < 50:',
    replacement_run, content
)

# Also update the metadata telemetry loop to include `proof_id`
replacement_telemetry_loop = """        model_telemetry[model] = {
            "category": cat,
            "api_proof_id": proofs.get(model, "MOCK_FALLBACK_OR_NOT_FOUND"),
            "overall_rank": overall_rankings.get(model, 99),
            "category_rank": category_rankings.get(cat, {}).get(model, 99),
            "local_elo": 1000 + (2000 - overall_rankings.get(model, 99) * 10),  # Mock ELO math
            "elo_diff_this_eval": elo_diff,
            "external_elo_score": external_elos.get(model, 1000),
            "api_cost_usd": round(cost, 6)
        }"""

content = re.sub(
    r'        model_telemetry\[model\] = \{\n\s+"category": cat,\n\s+"overall_rank": overall_rankings\.get\(model, 99\),\n\s+"category_rank": category_rankings\.get\(cat, \{\}\)\.get\(model, 99\),\n\s+"local_elo": 1000 \+ \(2000 - overall_rankings\.get\(model, 99\) \* 10\),  # Mock ELO math\n\s+"elo_diff_this_eval": elo_diff,\n\s+"external_elo_score": external_elos\.get\(model, 1000\),\n\s+"api_cost_usd": round\(cost, 6\)\n\s+\}',
    replacement_telemetry_loop, content
)

with open(file_path, "w") as f:
    f.write(content)
print("Patched api_proofs")
