#!/usr/bin/env python3
"""
Lauburu Evolutionary Trainer (HF SFTTrainer + PEFT)
Runs as a weekend cron job to bake successful smolagents fixes into a new LoRA adapter.
"""

import os
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

DATASET_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_dataset.jsonl")
MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_DIR = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/mesh_lora_checkpoints")

def run_hourly_training():
    if not os.path.exists(DATASET_PATH):
        print("No telemetry harvested yet. Skipping training.")
        return

    print("Loading Mesh Telemetry Dataset...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    print(f"Loading Base Model ({MODEL_ID}) in 4-bit...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, device_map="auto", load_in_4bit=True)
    
    # PEFT / LoRA Configuration (Targeting Qwen2.5 attention layers)
    peft_config = LoraConfig(
        r=8,  # Optimized for Hourly Rapid Training
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        max_seq_length=1024,
        dataset_text_field="completion",
        save_strategy="epoch"
    )
    
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        args=training_args,
    )
    
    print("Initiating Supervised Fine-Tuning (SFT)...")
    trainer.train()
    
    # Save the final LoRA adapter
    final_path = os.path.join(OUTPUT_DIR, "mesh_healer_lora_final")
    trainer.model.save_pretrained(final_path)
    print(f"Evolution Complete! New LoRA saved to {final_path}. The Mesh is now smarter.")

if __name__ == "__main__":
    run_weekend_training()
