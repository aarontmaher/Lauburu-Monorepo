import json

path = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json'
with open(path, 'r') as f:
    data = json.load(f)

# Update Astra to be OpenAI
astra = {
    "id": "openai_astra",
    "name": "ChatGPT Astra (OpenAI)",
    "exact_model_id": "gpt-astra-omni",
    "short_name": "ChatGPT Astra",
    "type": "Omnimodal Reasoning Agent",
    "tier": "CLOUD_FRONTIER_PRO",
    "archetype": "Universal Agent & Deep CoT Synthesizer",
    "deployment": "OpenAI API",
    "hardware": "Azure OpenAI Supercompute",
    "color": "#10a37f",
    "bg_color": "rgba(16, 163, 127, 0.15)",
    "badge": "🌌 OpenAI Frontier",
    "params_b": 150.0,
    "base_elo": 3150.0,
    "default_wins": 540,
    "default_losses": 4,
    "overall_benchmark_score": 99.6,
    "tokens_per_sec": 120.0,
    "context_window_tokens": 1048576,
    "multimodal_support": ["text", "code", "image", "video", "audio", "realtime"],
    "elo": 3150.0,
    "wins": 540,
    "losses": 4,
    "draws": 0,
    "total_duels": 544,
    "win_rate_pct": 99.2,
    "canonical_score": 99.8,
    "project_contribution_elo": 2700.0,
    "truth_audit_compliance_pct": 100.0,
    "rank": 1
}

# Update Fable to be Anthropic
fable = {
    "id": "anthropic_fable",
    "name": "Claude Fable (Anthropic)",
    "exact_model_id": "claude-fable-latest",
    "short_name": "Claude Fable",
    "type": "Advanced Reasoning & Simulation Architect",
    "tier": "CLOUD_FRONTIER_PRO",
    "archetype": "Complex Logic & Coding Mastermind",
    "deployment": "Anthropic API",
    "hardware": "AWS Trainium/Inferentia",
    "color": "#d97757",
    "bg_color": "rgba(217, 119, 87, 0.15)",
    "badge": "📚 Anthropic Elite",
    "params_b": 120.0,
    "base_elo": 3110.0,
    "default_wins": 490,
    "default_losses": 10,
    "overall_benchmark_score": 98.9,
    "tokens_per_sec": 85.0,
    "context_window_tokens": 1048576,
    "multimodal_support": ["text", "code", "image", "video"],
    "elo": 3110.0,
    "wins": 490,
    "losses": 10,
    "draws": 0,
    "total_duels": 500,
    "win_rate_pct": 98.0,
    "canonical_score": 99.1,
    "project_contribution_elo": 2650.0,
    "truth_audit_compliance_pct": 99.5,
    "rank": 2
}

for list_key in ["fighters", "leaderboard"]:
    if list_key in data:
        # Remove old placeholder ones
        data[list_key] = [m for m in data[list_key] if m['id'] not in ['google_astra', 'fable_model', 'openai_astra', 'anthropic_fable']]
        data[list_key].extend([astra, fable])
        data[list_key] = sorted(data[list_key], key=lambda x: x.get('elo', 0), reverse=True)
        for idx, model in enumerate(data[list_key]):
            model['rank'] = idx + 1

with open(path, 'w') as f:
    json.dump(data, f, indent=2)

print("Fixed to OpenAI and Anthropic!")
