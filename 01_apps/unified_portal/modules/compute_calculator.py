"""
Lauburu Mesh - Real-Time Compute Token & Cost Savings Calculator
Compares Local 82.8GB Mesh VRAM Generation vs. OpenAI GPT-4o, Claude 3.5 Sonnet, and Gemini Pro.
"""

from typing import Dict, Any

CLOUD_API_PRICING = {
    "GPT_4O": {"input_per_million": 2.50, "output_per_million": 10.00, "blended_per_million": 5.00},
    "CLAUDE_35_SONNET": {"input_per_million": 3.00, "output_per_million": 15.00, "blended_per_million": 6.00},
    "GEMINI_15_PRO": {"input_per_million": 1.25, "output_per_million": 5.00, "blended_per_million": 2.50}
}

ELECTRICITY_COST_PER_KWH_AUD = 0.32  # Typical Melbourne peak/off-peak blended
AVERAGE_MESH_WATTAGE = 45.0          # Pooled Mac Mini + MacBook + S20 + Linux idle/inference avg

class ComputeCalculator:
    @staticmethod
    def calculate_mesh_savings(local_tokens_generated: int = 1420500) -> Dict[str, Any]:
        # Cost if run on Cloud APIs
        gpt4o_cost_usd = (local_tokens_generated / 1_000_000) * CLOUD_API_PRICING["GPT_4O"]["blended_per_million"]
        claude_cost_usd = (local_tokens_generated / 1_000_000) * CLOUD_API_PRICING["CLAUDE_35_SONNET"]["blended_per_million"]
        gemini_cost_usd = (local_tokens_generated / 1_000_000) * CLOUD_API_PRICING["GEMINI_15_PRO"]["blended_per_million"]
        
        avg_cloud_cost_usd = (gpt4o_cost_usd + claude_cost_usd + gemini_cost_usd) / 3.0
        avg_cloud_cost_aud = avg_cloud_cost_usd * 1.55  # USD to AUD rate

        # Mesh electricity cost (Assuming ~50 tokens/sec throughput)
        hours_run = (local_tokens_generated / 50.0) / 3600.0
        kwh_consumed = (AVERAGE_MESH_WATTAGE * hours_run) / 1000.0
        local_electricity_aud = kwh_consumed * ELECTRICITY_COST_PER_KWH_AUD

        net_savings_aud = max(0.0, avg_cloud_cost_aud - local_electricity_aud)

        return {
            "local_tokens_generated": local_tokens_generated,
            "cloud_costs_avoided_usd": {
                "openai_gpt4o": round(gpt4o_cost_usd, 2),
                "anthropic_claude_35": round(claude_cost_usd, 2),
                "google_gemini_pro": round(gemini_cost_usd, 2)
            },
            "average_cloud_cost_aud": round(avg_cloud_cost_aud, 2),
            "local_mesh_electricity_aud": round(local_electricity_aud, 4),
            "net_savings_aud": round(net_savings_aud, 2),
            "roi_multiplier": round(avg_cloud_cost_aud / max(0.001, local_electricity_aud), 1),
            "pooled_vram_gb": 82.8,
            "carbon_offset_kg": round(kwh_consumed * 0.75, 3)
        }
