#!/usr/bin/env python3
"""
Lauburu AgentWorld Training Pipeline
=====================================
Fine-tunes Qwen3.8-27B (abliterated + base) on AgentWorld next-state-prediction format
using existing Lauburu JSONL datasets across 7 agent domains.

Domains covered by our data:
  MCP / Tool-calling  → nomad_autonomous_actions.jsonl, cron_governor_decisions.jsonl
  Terminal / SSH/bash → nomad_autonomous_actions.jsonl, network_decisions.jsonl
  SWE / Code          → ui_ux_improvements.jsonl, truth_audit_decisions.jsonl
  Android / ADB       → shizuku_healing_actions.jsonl
  OS / System Admin   → nomad_autonomous_actions.jsonl, network_decisions.jsonl
  Search              → truth_audit_debate.jsonl, truth_audit_decisions.jsonl
  Web                 → ui_ux_improvements.jsonl

Training stages (matching AgentWorld CPT → SFT → RL):
  Stage 1: SFT on Terminal + MCP domains (most data)
  Stage 2: SFT on SWE + Android domains
  Stage 3: RL warm-up via TRL GRPO on mesh governor reward signal

Usage:
  python3 agentworld_train.py --model abliterated --stage 1 --dry-run
  python3 agentworld_train.py --model abliterated --stage 1
  python3 agentworld_train.py --model base --stage 2
  python3 agentworld_train.py --list-data
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from datetime import datetime, timezone

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
VAULT = REPO / "02_ai_models_and_inference/model_vault_gguf"
LORA_OUT = REPO / "02_ai_models_and_inference/lora_adapters"
DATA = REPO / "data/lora_datasets"
GDRIVE = REPO / "data/gdrive_cache/Lauburu_AI_Memory/lora_datasets"
LOGS = REPO / "logs"
TRAIN_LOG = DATA / "agentworld_training_runs.jsonl"

LORA_OUT.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

# ── Model Registry ─────────────────────────────────────────────────────────────
MODELS = {
    "abliterated": {
        "name": "Huihui-Qwen3.8-27B-abliterated",
        "gguf": VAULT / "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf",
        "hf_id": "huihui-ai/Huihui-Qwen3.8-27B-abliterated",
        "server_port": 8085,
        "description": "Qwen3.8-27B abliterated — no safety filters, best for mesh/terminal training",
    },
    "base": {
        "name": "Qwen2.5-7B-abliterated",
        "gguf": VAULT / "Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf",
        "hf_id": "Qwen/Qwen2.5-7B-Instruct",
        "server_port": 8086,
        "description": "Qwen2.5-7B abliterated — smaller, faster iteration for SFT experiments",
    },
}

# ── Domain → Dataset Mapping ──────────────────────────────────────────────────
DOMAIN_DATASETS = {
    # Stage 1 domains (most training data)
    "stage_1": {
        "MCP_tool_calling": [
            DATA / "nomad_autonomous_actions.jsonl",
            DATA / "cron_governor_decisions.jsonl",
        ],
        "Terminal_bash_ssh": [
            DATA / "nomad_autonomous_actions.jsonl",
            DATA / "network_decisions.jsonl",
        ],
    },
    # Stage 2 domains
    "stage_2": {
        "SWE_code_patches": [
            DATA / "ui_ux_improvements.jsonl",
            DATA / "truth_audit_decisions.jsonl",
        ],
        "Android_ADB": [
            DATA / "shizuku_healing_actions.jsonl",
        ],
        "Search": [
            DATA / "truth_audit_debate.jsonl",
            DATA / "truth_audit_decisions.jsonl",
        ],
    },
    # Stage 3: RL warm-up
    "stage_3": {
        "OS_system_admin": [
            DATA / "nomad_autonomous_actions.jsonl",
            DATA / "network_decisions.jsonl",
            DATA / "cron_governor_decisions.jsonl",
        ],
    },
}

# ── AgentWorld Format Converter ────────────────────────────────────────────────

def lauburu_to_agentworld(record: Dict, domain: str) -> Optional[Dict]:
    """
    Convert a Lauburu JSONL record to AgentWorld next-state-prediction format.
    Handles all field schemas across Lauburu datasets:
      nomad_autonomous_actions: {action, result, timestamp_utc, nomad_agent}
      cron_governor_decisions:  {instruction, completion, action, ...}
      truth_audit_decisions:    {instruction, input, output, completion, ...}
      ui_ux_improvements:       {instruction, input, output, ...}
      network_decisions:        {action, result, context, ...}
      shizuku_healing_actions:  {instruction, completion, actions_taken, ...}
    """
    # ── Extract action/instruction ──────────────────────────────────────────
    instruction = (
        record.get("instruction") or
        record.get("action") or
        record.get("input") or
        record.get("prompt") or
        record.get("query") or ""
    )

    # ── Extract observation/context ─────────────────────────────────────────
    observation = (
        record.get("observation") or
        record.get("context") or
        record.get("input") or
        record.get("state") or
        record.get("nomad_agent", "") + " @ " + record.get("timestamp_utc", "")
    )

    # ── Extract completion/result ───────────────────────────────────────────
    completion = (
        record.get("completion") or
        record.get("result") or
        record.get("output") or
        record.get("response") or ""
    )

    # Skip records without both an action and a result
    if not instruction or not completion:
        return None

    # Skip trivially short records
    if len(str(completion)) < 3:
        return None

    # ── Extract action list ─────────────────────────────────────────────────
    actions = record.get("actions_taken", record.get("action", instruction))
    if isinstance(actions, list):
        action_str = "; ".join(str(a) for a in actions[:5]) if actions else instruction
    else:
        action_str = str(actions)[:300]

    history_str = str(observation)[:400] if observation else "No prior state."

    system = (
        f"You are a language world model simulating the {domain} environment. "
        f"Given an agent's action and interaction history, predict the next environment state "
        f"using chain-of-thought reasoning."
    )

    user = (
        f"<action>\n{action_str}\n</action>\n\n"
        f"<history>\n{history_str}\n</history>\n\n"
        f"Predict the next environment state:"
    )

    assistant = f"<next_state>\n{completion}\n</next_state>"

    return {
        "messages": [
            {"role": "system",    "content": system},
            {"role": "user",      "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "domain":    domain,
        "source":    "lauburu_mesh_telemetry",
        "timestamp": record.get("timestamp", record.get("timestamp_utc", "")),
    }


def load_domain_datasets(stage: int) -> List[Dict]:
    """Load and convert all datasets for a training stage."""
    stage_key = f"stage_{stage}"
    stage_domains = DOMAIN_DATASETS.get(stage_key, {})
    all_samples = []
    seen = set()

    for domain, paths in stage_domains.items():
        domain_samples = 0
        for p in paths:
            if not p.exists():
                print(f"  ⚠️  Missing: {p.name}")
                continue
            with open(p, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        converted = lauburu_to_agentworld(rec, domain)
                        if converted:
                            # Dedup by full action + completion signature
                            user_content = converted["messages"][1]["content"]
                            asst_content = converted["messages"][2]["content"]
                            sig = hash((user_content[:200], asst_content[:200]))
                            if sig in seen:
                                continue
                            seen.add(sig)
                            all_samples.append(converted)
                            domain_samples += 1
                    except Exception:
                        continue
        print(f"  {domain}: {domain_samples} samples")

    return all_samples


def save_training_dataset(samples: List[Dict], stage: int) -> Path:
    """Save converted dataset as JSONL for TRL."""
    out_path = DATA / f"agentworld_stage{stage}_training.jsonl"
    with open(out_path, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
    print(f"  ✅ Saved {len(samples)} samples → {out_path}")
    return out_path


# ── LoRA Training via TRL SFT ─────────────────────────────────────────────────

def run_sft_training(model_key: str, dataset_path: Path, stage: int, dry_run: bool = False):
    """Run LoRA SFT via TRL SFTTrainer on Apple MPS (Metal)."""
    model_cfg = MODELS[model_key]
    adapter_out = LORA_OUT / f"agentworld_{model_key}_stage{stage}"
    adapter_out.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"AgentWorld LoRA Training")
    print(f"  Model:    {model_cfg['name']}")
    print(f"  Stage:    {stage}")
    print(f"  Data:     {dataset_path} ({sum(1 for _ in open(dataset_path))} samples)")
    print(f"  Output:   {adapter_out}")
    print(f"  Dry-run:  {dry_run}")
    print(f"{'='*60}\n")

    if dry_run:
        print("DRY RUN — training plan only, no weights modified.")
        print(f"\nWould run:\n"
              f"  from trl import SFTTrainer, SFTConfig\n"
              f"  from peft import LoraConfig\n"
              f"  model = AutoModelForCausalLM.from_pretrained('{model_cfg['hf_id']}')\n"
              f"  lora = LoraConfig(r=64, lora_alpha=128, target_modules='all-linear')\n"
              f"  trainer = SFTTrainer(model, train_dataset, lora_cfg=lora)\n"
              f"  trainer.train()\n"
              f"  trainer.save_model('{adapter_out}')")
        return

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model
        from trl import SFTTrainer, SFTConfig
        from datasets import Dataset

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"  Device: {device} (Apple Metal: {device == 'mps'})")

        # Load dataset
        records = []
        with open(dataset_path) as f:
            for line in f:
                rec = json.loads(line.strip())
                # Format as plain text for SFT
                messages = rec.get("messages", [])
                text = ""
                for m in messages:
                    role = m["role"]
                    content = m["content"]
                    if role == "system":
                        text += f"<|system|>\n{content}\n"
                    elif role == "user":
                        text += f"<|user|>\n{content}\n"
                    elif role == "assistant":
                        text += f"<|assistant|>\n{content}\n"
                records.append({"text": text})
        dataset = Dataset.from_list(records)

        print(f"  Loading tokenizer: {model_cfg['hf_id']}")
        tokenizer = AutoTokenizer.from_pretrained(model_cfg["hf_id"], trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        print(f"  Loading model: {model_cfg['hf_id']}")
        model = AutoModelForCausalLM.from_pretrained(
            model_cfg["hf_id"],
            torch_dtype=torch.float16,
            device_map=device,
            trust_remote_code=True,
        )

        # LoRA config — AgentWorld uses r=64 based on their paper
        lora_cfg = LoraConfig(
            r=64,
            lora_alpha=128,
            target_modules="all-linear",
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()

        # SFT training config
        sft_cfg = SFTConfig(
            output_dir=str(adapter_out),
            num_train_epochs=3,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            logging_steps=10,
            save_steps=100,
            save_total_limit=2,
            bf16=False,
            fp16=True,
            dataloader_num_workers=0,   # Required for MPS
            report_to="none",
            max_seq_length=2048,
        )

        trainer = SFTTrainer(
            model=model,
            args=sft_cfg,
            train_dataset=dataset,
            tokenizer=tokenizer,
            dataset_text_field="text",
        )

        print(f"\n🚀 Starting training... ({len(dataset)} samples, 3 epochs)")
        trainer.train()
        trainer.save_model(str(adapter_out))
        tokenizer.save_pretrained(str(adapter_out))
        print(f"\n✅ Adapter saved → {adapter_out}")

        # Log to LoRA dataset
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instruction": f"AgentWorld SFT training stage {stage} on {model_cfg['name']}",
            "observation": f"samples={len(dataset)} device={device}",
            "completion": f"Adapter saved to {adapter_out}",
            "actions_taken": [f"SFT_STAGE_{stage}_{model_key.upper()}"],
        }
        with open(TRAIN_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    except ImportError as e:
        print(f"\n❌ Missing training dependency: {e}")
        print("   Install with: uv pip install torch transformers peft trl datasets --system")
        print("   OR use llama.cpp server + proxy for inference-time adaptation")


# ── Qwen Math Decision ─────────────────────────────────────────────────────────

def print_qwen_math_analysis():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         Qwen2.5-Math — Should You Download It?                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Model options:                                                      ║
║    Qwen2.5-Math-7B-Instruct     Q4_K_M ≈ 4.5 GB   ← RECOMMENDED    ║
║    Qwen2.5-Math-72B-Instruct    Q4_K_M ≈ 40 GB    (needs RPC)       ║
║                                                                      ║
║  Use cases in YOUR stack:                                            ║
║   ✅ Trend analysis on ECG/biometrics data (DFA-α1, HRV stats)      ║
║   ✅ Loss curve analysis during training (perplexity, grad norms)   ║
║   ✅ Mesh ROI scoring (VRAM headroom equations, latency models)      ║
║   ✅ PySpark aggregation query planning                              ║
║   ✅ Shopify CAC/LTV/margin calculations                             ║
║   ✅ Nomad governor cost/ROI decision math                           ║
║                                                                      ║
║  VERDICT: YES — download Qwen2.5-Math-7B-Instruct (4.5 GB).        ║
║  It's tiny, fits alongside Qwen3.8 with room to spare.              ║
║  Load it on :8086. Route /model math in the TUI proxy.              ║
║                                                                      ║
║  Download:                                                           ║
║   huggingface-cli download Qwen/Qwen2.5-Math-7B-Instruct \\         ║
║     --include "*.gguf" --local-dir model_vault_gguf/                ║
║   OR: https://huggingface.co/bartowski/Qwen2.5-Math-7B-Instruct-GGUF║
╚══════════════════════════════════════════════════════════════════════╝
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lauburu AgentWorld Training Pipeline")
    parser.add_argument("--model",    choices=["abliterated", "base"], default="abliterated",
                        help="Which Qwen model to fine-tune")
    parser.add_argument("--stage",   type=int, choices=[1, 2, 3], default=1,
                        help="Training stage (1=MCP+Terminal, 2=SWE+Android, 3=RL/OS)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print training plan without executing")
    parser.add_argument("--list-data", action="store_true",
                        help="Show dataset inventory and exit")
    parser.add_argument("--qwen-math", action="store_true",
                        help="Print Qwen Math analysis and exit")
    parser.add_argument("--both",    action="store_true",
                        help="Run both abliterated and base models sequentially")
    args = parser.parse_args()

    print(f"\n🤖 Lauburu AgentWorld Training Pipeline")
    print(f"   Based on: Qwen-AgentWorld-35B-A3B (CPT→SFT→RL)\n")

    if args.qwen_math:
        print_qwen_math_analysis()
        return

    if args.list_data:
        print("📊 Dataset Inventory:\n")
        total = 0
        for stage_key, domains in DOMAIN_DATASETS.items():
            print(f"  [{stage_key.upper()}]")
            for domain, paths in domains.items():
                for p in paths:
                    if p.exists():
                        lines = sum(1 for _ in open(p, "rb"))
                        size_kb = p.stat().st_size // 1024
                        print(f"    ✅ {domain}: {lines:>6,} samples  {size_kb:>5} KB  {p.name}")
                        total += lines
                    else:
                        print(f"    🔴 {domain}: MISSING  {p.name}")
        print(f"\n  TOTAL: {total:,} training samples across all stages")
        return

    # Load and convert dataset
    print(f"📦 Loading Stage {args.stage} datasets...")
    samples = load_domain_datasets(args.stage)
    print(f"  Total unique samples: {len(samples)}")

    if not samples:
        print("❌ No samples found. Check dataset paths.")
        sys.exit(1)

    dataset_path = save_training_dataset(samples, args.stage)

    # Run training
    models_to_train = (["abliterated", "base"] if args.both
                       else [args.model])

    for model_key in models_to_train:
        run_sft_training(model_key, dataset_path, args.stage, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print("📊 Qwen Math recommendation:")
    print_qwen_math_analysis()


if __name__ == "__main__":
    main()
