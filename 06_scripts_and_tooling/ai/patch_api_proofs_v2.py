import re

file_path = "frontier_swarm_consensus.py"
with open(file_path, "r") as f:
    content = f.read()

# Instead of complex regex, let's use exact string replacement
old_or_try = '''        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                return body["choices"][0]["message"]["content"].strip()'''

new_or_try = '''        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                return (body["choices"][0]["message"]["content"].strip(), body.get("id", "NO_ID"))'''

content = content.replace(old_or_try, new_or_try)

old_or_except = '''        if "404" in str(e) and model_slug != "google/gemini-2.5-flash":
            return query_openrouter("google/gemini-2.5-flash", prompt, system_prompt, max_tokens, timeout)
    return None'''

new_or_except = '''        if "404" in str(e) and model_slug != "google/gemini-2.5-flash":
            return query_openrouter("google/gemini-2.5-flash", prompt, system_prompt, max_tokens, timeout)
    return (None, "ERROR")'''

content = content.replace(old_or_except, new_or_except)

old_cloud = '''    or_slug = OPENROUTER_MODEL_MAP.get(shorthand)
    if or_slug:
        or_resp = query_openrouter(or_slug, prompt, max_tokens=max_tokens, timeout=12)
        if or_resp:
            return or_resp'''

new_cloud = '''    or_slug = OPENROUTER_MODEL_MAP.get(shorthand)
    if or_slug:
        or_resp, or_id = query_openrouter(or_slug, prompt, max_tokens=max_tokens, timeout=12)
        if or_resp:
            return (or_resp, or_id)'''

content = content.replace(old_cloud, new_cloud)

old_agy = '''        parsed = extract_json(res.stdout)
        if parsed and "response" in parsed and parsed["response"]:
            return parsed["response"].strip()
        if res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass'''

new_agy = '''        parsed = extract_json(res.stdout)
        if parsed and "response" in parsed and parsed["response"]:
            return (parsed["response"].strip(), "AGY_LOCAL_EXECUTION_STDOUT")
        if res.stdout.strip():
            return (res.stdout.strip(), "AGY_LOCAL_EXECUTION_STDOUT")
    except Exception:
        pass'''

content = content.replace(old_agy, new_agy)

old_cloud_fb = '''    if is_ecom:
        ecom_fallbacks = {
            "gemini_flash": "Hardware fulfillment gate passed ($125 AUD floor).",
            "gemini_pro": "Shopify GraphQL mutations must be routed via local L3 Linux node.",
            "opus": "3-stage IMU adaptive wavelet filter prevents dynamic ECG noise.",
            "sonnet": "DFA-alpha1 Zone 2 threshold bound mathematically verified.",
            "gpt_6_astra": "Apple Vision OCR receipt validation guarantees 0% spoofing.",
            "gpt_oss": "Zero-Mock truth enforced across biometrics pipeline."
        }
        return ecom_fallbacks.get(shorthand, "E-Commerce consensus recommendation ratified.")'''

new_cloud_fb = '''    if is_ecom:
        ecom_fallbacks = {
            "gemini_flash": "Hardware fulfillment gate passed ($125 AUD floor).",
            "gemini_pro": "Shopify GraphQL mutations must be routed via local L3 Linux node.",
            "opus": "3-stage IMU adaptive wavelet filter prevents dynamic ECG noise.",
            "sonnet": "DFA-alpha1 Zone 2 threshold bound mathematically verified.",
            "gpt_6_astra": "Apple Vision OCR receipt validation guarantees 0% spoofing.",
            "gpt_oss": "Zero-Mock truth enforced across biometrics pipeline."
        }
        return (ecom_fallbacks.get(shorthand, "E-Commerce consensus recommendation ratified."), "MOCK_FALLBACK_ECOM_CLOUD")'''

content = content.replace(old_cloud_fb, new_cloud_fb)

old_cloud_fb_end = '''    }
    return fallbacks.get(shorthand, "Architectural consensus recommendation ratified.")'''

new_cloud_fb_end = '''    }
    return (fallbacks.get(shorthand, "Architectural consensus recommendation ratified."), "MOCK_FALLBACK_GENERAL_CLOUD")'''

content = content.replace(old_cloud_fb_end, new_cloud_fb_end)

# Local model updates
old_local_try = '''        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                return body["choices"][0]["message"]["content"].strip()'''

new_local_try = '''        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if "choices" in body and body["choices"]:
                return (body["choices"][0]["message"]["content"].strip(), f"local_gguf_{port}")'''

content = content.replace(old_local_try, new_local_try)

old_local_fb1 = '''    or_resp = query_openrouter(or_slug, prompt, system_prompt=system_role, max_tokens=256)
    if or_resp:
        return f"[{cfg['role']}]: {or_resp}"'''

new_local_fb1 = '''    or_resp, or_id = query_openrouter(or_slug, prompt, system_prompt=system_role, max_tokens=256)
    if or_resp:
        return (f"[{cfg['role']}]: {or_resp}", or_id)'''

content = content.replace(old_local_fb1, new_local_fb1)

old_local_fb2 = '''    if is_ecom:
        if node_key == "qwen_38_max_master":
            return (
                f"[{cfg['role']}]: Enforce Zero-Out-Of-Pocket hardware fulfillment ($125 AUD settled fiat floor "
                f"before shipping Movesense MD+ kit). Preserve Mac Mini host sanctuary (>= 4.8 GB free RAM, <= 80% cap) "
                f"by offloading Shopify GraphQL sync, Marimo Port 4005, and biometrics timeseries to L3 Linux Mini (100.101.39.98)."
            )
        else:
            return (
                f"[{cfg['role']}]: Stress-testing commercial-biometrics pipeline: Enforce Screen Lens Apple Vision OCR "
                f"to prevent PayID receipt spoofing before order release. Enforce 3-stage IMU-adaptive wavelet denoising on "
                f"bicep ECG to suppress dynamic contraction EMG (25-120 Hz) with +6 dB SNR gate under Rule 1 Zero-Mock Truth."
            )
    return f"[Local Engine Port {port} Fallback]: {cfg['fallback_reasoning']}"'''

new_local_fb2 = '''    if is_ecom:
        if node_key == "qwen_38_max_master":
            return (
                f"[{cfg['role']}]: Enforce Zero-Out-Of-Pocket hardware fulfillment ($125 AUD settled fiat floor "
                f"before shipping Movesense MD+ kit). Preserve Mac Mini host sanctuary (>= 4.8 GB free RAM, <= 80% cap) "
                f"by offloading Shopify GraphQL sync, Marimo Port 4005, and biometrics timeseries to L3 Linux Mini (100.101.39.98).", "MOCK_FALLBACK_ECOM_LOCAL"
            )
        else:
            return (
                f"[{cfg['role']}]: Stress-testing commercial-biometrics pipeline: Enforce Screen Lens Apple Vision OCR "
                f"to prevent PayID receipt spoofing before order release. Enforce 3-stage IMU-adaptive wavelet denoising on "
                f"bicep ECG to suppress dynamic contraction EMG (25-120 Hz) with +6 dB SNR gate under Rule 1 Zero-Mock Truth.", "MOCK_FALLBACK_ECOM_LOCAL"
            )
    return (f"[Local Engine Port {port} Fallback]: {cfg['fallback_reasoning']}", "MOCK_FALLBACK_GENERAL_LOCAL")'''

content = content.replace(old_local_fb2, new_local_fb2)

# Update run_frontier_swarm loop
old_run1 = '''    print("\\n--- Phase 1: Querying Frontier Cloud Roster ---")
    cloud_roster = ["fable", "opus_5_5", "astra", "gemini_pro", "grok_4_7"]
    for shorthand in cloud_roster:
        prompt = f"As a frontier swarm pillar, evaluate and provide rigorous architectural recommendation for: {task}"
        resp = query_cloud_model(shorthand, prompt)
        responses[shorthand] = resp
        print(f"    [+] {shorthand.upper()} deliberation captured ({len(resp)} chars)")
        
    print("\\n--- Phase 2: Querying Local Sovereign Duo ---")
    local_roster = ["qwen_38_max_master", "qwen_38_max_abliterated"]
    for local_key in local_roster:
        prompt = f"As the Local Sovereign Duo, provide authoritative architectural verdict and failure-mode analysis for: {task}"
        resp = query_local_model(local_key, prompt)
        responses[local_key] = resp
        print(f"    [+] {local_key.upper()} deliberation captured ({len(resp)} chars)")'''

new_run1 = '''    proofs = {}
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
        print(f"    [+] {local_key.upper()} deliberation captured ({len(resp)} chars, PROOF: {proof_id})")'''

content = content.replace(old_run1, new_run1)

old_run2 = '''    consensus = query_cloud_model("gemini_pro", synthesis_prompt, max_tokens=600)
    if not consensus or len(consensus) < 50:'''

new_run2 = '''    consensus, cons_proof = query_cloud_model("gemini_pro", synthesis_prompt, max_tokens=600)
    if not consensus or len(consensus) < 50:'''

content = content.replace(old_run2, new_run2)

old_meta = '''        model_telemetry[model] = {
            "category": cat,
            "overall_rank": overall_rankings.get(model, 99),
            "category_rank": category_rankings.get(cat, {}).get(model, 99),
            "local_elo": 1000 + (2000 - overall_rankings.get(model, 99) * 10),  # Mock ELO math
            "elo_diff_this_eval": elo_diff,
            "external_elo_score": external_elos.get(model, 1000),
            "api_cost_usd": round(cost, 6)
        }'''

new_meta = '''        model_telemetry[model] = {
            "category": cat,
            "api_proof_id": proofs.get(model, "NO_PROOF_FOUND"),
            "overall_rank": overall_rankings.get(model, 99),
            "category_rank": category_rankings.get(cat, {}).get(model, 99),
            "local_elo": 1000 + (2000 - overall_rankings.get(model, 99) * 10),  # Mock ELO math
            "elo_diff_this_eval": elo_diff,
            "external_elo_score": external_elos.get(model, 1000),
            "api_cost_usd": round(cost, 6)
        }'''

content = content.replace(old_meta, new_meta)

with open(file_path, "w") as f:
    f.write(content)
print("Patched successfully")
