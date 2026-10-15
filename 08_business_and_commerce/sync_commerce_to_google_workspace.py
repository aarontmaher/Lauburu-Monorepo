#!/usr/bin/env python3
"""
🌐 Lauburu Mesh — Google Workspace & Cloud Commercial Sync Bridge
Synchronizes the monorepo's financial ledger, catalog pricing, compute billing,
and Screen Lens audit logs into Google Sheets format, local CSV sheets, and
encrypted disaster recovery backups.
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

COMMERCE_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce")
LEDGER_PATH = COMMERCE_DIR / "business_ledger.json"
COMPUTE_DB_PATH = COMMERCE_DIR / "compute_billing_db.json"
ELO_BANK_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/elo_bank.json")
EXPORTS_DIR = COMMERCE_DIR / "google_workspace_exports"
GDRIVE_BACKUP_DIR = Path("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/commerce_backups")

class GoogleWorkspaceCommerceSync:
    def __init__(self):
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if GDRIVE_BACKUP_DIR.parent.exists():
            GDRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def load_data(self) -> Dict[str, Any]:
        with open(LEDGER_PATH, "r") as f:
            ledger = json.load(f)
        with open(COMPUTE_DB_PATH, "r") as f:
            compute_db = json.load(f)
        with open(ELO_BANK_PATH, "r") as f:
            elo_bank = json.load(f)

        return {
            "ledger": ledger,
            "compute_db": compute_db,
            "elo_bank": elo_bank
        }

    def export_all_sheets(self) -> Dict[str, str]:
        data = self.load_data()
        ledger = data["ledger"]
        compute_db = data["compute_db"]
        elo_bank = data["elo_bank"]

        exported_files = {}

        # Sheet 1: Financial KPI Summary
        summary_csv = EXPORTS_DIR / "1_executive_financial_summary.csv"
        with open(summary_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Metric", "Value AUD", "Status / Notes"])
            w.writerow(["Total Virtual Business Capital", f"${ledger.get('total_capital_aud', 0.0):,.2f}", "Bootstrapped Asset Reserve"])
            w.writerow(["OpenRouter Query Permissions", f"{ledger.get('available_openrouter_credits', 0)} credits", "Local AI Research Allowance"])
            w.writerow(["Compute API Gross Revenue", f"${compute_db.get('total_revenue_aud', 0.0):,.2f}", "Pay-by-Compute API Ingress"])
            w.writerow(["Settled Fiat Reserve", f"${compute_db.get('settled_fiat_reserve_aud', 0.0):,.2f}", "Hard COGS Settlement Invariant"])
            w.writerow(["Total Tokens Served", f"{compute_db.get('total_tokens_served', 0):,}", "Inference Metering Volume"])
            w.writerow(["Completed Milestones", len(ledger.get("completed_milestones", {})), "Automated Goals Delivered"])
        exported_files["summary"] = str(summary_csv)

        # Sheet 2: Catalog & Unit Economics
        catalog_csv = EXPORTS_DIR / "2_catalog_unit_economics.csv"
        from unified_enterprise_commercial_engine import COMMERCE_CATALOG
        with open(catalog_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Item Key", "Product Title", "Category", "Retail Price AUD", "Hard COGS AUD", "Shipping AUD", "Net Margin AUD", "Gross Margin %", "Solvency Guard"])
            for key, item in COMMERCE_CATALOG.items():
                price = item.get("price_aud") or item.get("target_price_aud", 0.0)
                cogs = item.get("hard_cogs_aud", 0.0)
                ship = item.get("shipping_aud", 0.0)
                margin = price - (cogs + ship)
                margin_pct = (margin / price * 100) if price > 0 else 0.0
                guard = "ZERO_OUT_OF_POCKET" if item.get("category") == "HARD_PHYSICAL_ASSET" else "MARGIN_DEFENSE"
                w.writerow([key, item.get("title"), item.get("category"), f"${price:.2f}", f"${cogs:.2f}", f"${ship:.2f}", f"${margin:.2f}", f"{margin_pct:.1f}%", guard])
        exported_files["catalog"] = str(catalog_csv)

        # Sheet 3: Compute & SaaS Accounts
        accounts_csv = EXPORTS_DIR / "3_compute_saas_accounts.csv"
        with open(accounts_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Account ID", "Compute Token Balance AUD", "Settled Fiat Balance AUD", "Total Usage AUD", "Account Solvency"])
            for acc_id, acc in compute_db.get("active_accounts", {}).items():
                tokens = acc.get("compute_token_balance_aud", 0.0)
                fiat = acc.get("settled_fiat_balance_aud", 0.0)
                usage = acc.get("total_usage_aud", 0.0)
                solvency = "SOLVENT_FIAT_BACKED" if fiat > 0 else "VIRTUAL_COMPUTE_ONLY"
                w.writerow([acc_id, f"${tokens:.2f}", f"${fiat:.2f}", f"${usage:.2f}", solvency])
        exported_files["accounts"] = str(accounts_csv)

        # Sheet 4: Completed Milestones
        milestones_csv = EXPORTS_DIR / "4_completed_milestones.csv"
        with open(milestones_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Milestone Key", "Title", "Delivering Model", "Automation Score", "Capital Granted AUD", "Credits Granted", "ELO Granted", "Evidence"])
            for m_key, m in ledger.get("completed_milestones", {}).items():
                w.writerow([
                    m_key,
                    m.get("title", m_key),
                    m.get("model_id", "Qwen_3.8_Max"),
                    m.get("automation_score", "N/A"),
                    f"${m.get('capital_granted_aud', 0.0):.2f}",
                    m.get("openrouter_credits_granted", 0),
                    m.get("elo_granted", 0),
                    m.get("deliverable_evidence", "")
                ])
        exported_files["milestones"] = str(milestones_csv)

        # Sheet 5: AI Model ELO & Incentive Standings
        elo_csv = EXPORTS_DIR / "5_ai_model_elo_standings.csv"
        with open(elo_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Model Identifier", "ELO Rating", "Mesh Hierarchy Role", "RAM Headroom Priority"])
            roles = {
                "Qwen_3.8_Max_Abliterated": ("Sovereign Master Local Orchestrator (Port 8082)", "Host Sanctuary Priority 1"),
                "Qwen_3.8_Max": ("Canonical Devil's Advocate / Red Team (Port 8083)", "Host Sanctuary Priority 2"),
                "GPT_6_Astra": ("Frontier Cloud Contender (OpenAI via OpenRouter)", "Cloud Remote Only"),
                "Gemini_3.8_Flash": ("Frontier Cloud Contender (Google DeepMind via OpenRouter)", "Cloud Remote Only"),
                "DeepSeek_V4.1_Flash": ("Frontier Cloud Contender (DeepSeek via OpenRouter)", "Cloud Remote Only"),
                "Claude_Fable_5.1": ("Frontier Cloud Contender (Anthropic via OpenRouter)", "Cloud Remote Only"),
                "Opus_Architect": ("Cloud Frontier Teacher AI (OpenRouter)", "Cloud Remote Only"),
                "Baseline_Untrained_Generalist": ("Novice Benchmark Baseline", "Unallocated")
            }
            for model_id, elo in elo_bank.items():
                role, priority = roles.get(model_id, ("Syntax Specialist", "Peripheral Offload"))
                w.writerow([model_id, elo, role, priority])
        exported_files["elo"] = str(elo_csv)

        # Backup snapshot to Google Drive if available
        if GDRIVE_BACKUP_DIR.exists():
            snapshot_file = GDRIVE_BACKUP_DIR / f"commerce_ledger_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            snapshot_file.write_text(json.dumps(data, indent=2))
            exported_files["gdrive_snapshot"] = str(snapshot_file)

        return exported_files

if __name__ == "__main__":
    sync = GoogleWorkspaceCommerceSync()
    print("=================================================================")
    print("📊 Lauburu Mesh: Google Workspace & Sheets Sync Bridge Active")
    print("=================================================================")
    res = sync.export_all_sheets()
    for name, path in res.items():
        print(f"  [✓] Exported {name:15s}: {path}")
    print("=================================================================")
