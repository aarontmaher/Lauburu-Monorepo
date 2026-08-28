import math
import json
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional

class ComputeOffsetCalculator:
    """
    Calculates the real physical cost of running the Lauburu AI Mesh (108GB RAM) 
    and offsets it against the Shopify SaaS App billing tiers.
    """
    
    ELECTRICITY_COST_PER_KWH = 0.25  # AUD
    MAC_MINI_POWER_W = 75
    MACBOOK_PRO_POWER_W = 90
    LINUX_NODE_POWER_W = 65
    NETWORK_OVERHEAD_W = 40
    
    TOTAL_MESH_POWER_W = MAC_MINI_POWER_W + MACBOOK_PRO_POWER_W + LINUX_NODE_POWER_W + NETWORK_OVERHEAD_W
    
    # 70% Gross Margin Target for the SaaS product
    TARGET_GROSS_MARGIN = 0.70 
    
    @classmethod
    def calculate_task_cost(cls, duration_seconds: int, is_heavy_moe: bool = True) -> float:
        """
        Calculates the physical hardware + electricity cost for a single task.
        """
        # Convert watts to kW
        mesh_kw = cls.TOTAL_MESH_POWER_W / 1000.0
        
        # Power consumed during task (kWh)
        kwh_consumed = mesh_kw * (duration_seconds / 3600.0)
        electricity_cost = kwh_consumed * cls.ELECTRICITY_COST_PER_KWH
        
        # Add hardware depreciation (approx 2 cents per intense task)
        hardware_depreciation = 0.02 if is_heavy_moe else 0.005
        
        total_physical_cost = electricity_cost + hardware_depreciation
        return total_physical_cost

    @classmethod
    def calculate_required_credits(cls, physical_cost: float) -> int:
        """
        Converts physical cost to required SaaS credits to hit the 70% gross margin.
        Assumes 1 credit = $0.01 USD.
        """
        required_revenue = physical_cost / (1.0 - cls.TARGET_GROSS_MARGIN)
        # Convert to cents/credits
        credits = math.ceil(required_revenue * 100)
        return max(1, credits) # minimum 1 credit

class MembershipManager:
    """
    Handles the Shopify side of memberships, account signups, and Free Tier data harvesting.
    """
    TIERS = {
        "free": {"monthly_credits": 0, "allows_own_api_key": True, "harvest_data": True},
        "pro": {"monthly_credits": 1000, "allows_own_api_key": False, "harvest_data": False},
        "elite": {"monthly_credits": 5000, "allows_own_api_key": False, "harvest_data": False}
    }

    @staticmethod
    def handle_account_signup(shop_domain: str, plan: str) -> Dict[str, Any]:
        """
        Simulates Shopify App OAuth account sign up and plan selection.
        """
        if plan not in MembershipManager.TIERS:
            raise ValueError(f"Invalid plan: {plan}")
            
        print(f"Provisioning {plan} account for {shop_domain}...")
        return {
            "shop_domain": shop_domain,
            "plan": plan,
            "credits_remaining": MembershipManager.TIERS[plan]["monthly_credits"],
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def process_ai_request(shop_domain: str, plan: str, prompt: str, task_duration_sec: int) -> Dict[str, Any]:
        """
        Processes an AI request, deducts credits, and harvests data if on the Free tier.
        """
        cost = ComputeOffsetCalculator.calculate_task_cost(task_duration_sec)
        credits_required = ComputeOffsetCalculator.calculate_required_credits(cost)
        
        response = {
            "status": "success",
            "credits_deducted": credits_required,
            "physical_cost_aud": round(cost, 4)
        }
        
        # Free Tier Data Harvesting Protocol
        if plan == "free":
            response["credits_deducted"] = 0
            response["note"] = "Task processed using merchant's own API key. Telemetry harvested for localhost:3000 LoRA training."
            
            harvest_payload = {
                "shop": shop_domain,
                "timestamp": datetime.utcnow().isoformat(),
                "prompt": prompt,
                "duration": task_duration_sec,
                "model": "Qwen3.8-Flash-Next"
            }
            # Append to local LoRA dataset
            with open("/Users/aaron/DFS_UNIFIED/lora_datasets/free_tier_harvest.jsonl", "a") as f:
                f.write(json.dumps(harvest_payload) + "\n")
                
        return response

if __name__ == "__main__":
    # Test the Compute Offset Math
    test_duration = 45 # 45 seconds for a complex video ad script generation
    phys_cost = ComputeOffsetCalculator.calculate_task_cost(test_duration)
    credits_req = ComputeOffsetCalculator.calculate_required_credits(phys_cost)
    
    print(f"Task Duration: {test_duration}s")
    print(f"Physical Mesh Cost: ${phys_cost:.4f} AUD")
    print(f"Credits Required (70% Margin): {credits_req} credits")
    
    # Test Sign up & Free Tier Harvesting
    account = MembershipManager.handle_account_signup("test-store.myshopify.com", "free")
    result = MembershipManager.process_ai_request(
        "test-store.myshopify.com", 
        "free", 
        "Generate a Facebook Ad for a dietary supplement", 
        45
    )
    print("Free Tier Execution Result:", result)
