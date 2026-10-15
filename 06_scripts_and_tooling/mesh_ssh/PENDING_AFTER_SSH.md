# Pending Actions Once MacBook Pro SSH Is Established

## 1. Delete cold models from Mac Mini (approved)
```bash
rm -f "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/WebWorld-32B.Q4_K_M.gguf"
rm -f "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf"
```

## 2. Start Gemma 4 12B download (approved)
```bash
/Users/aaron/.venv/bin/python -m mlx_lm.convert \
  --hf-path google/gemma-4-12b-it \
  --mlx-path /Users/aaron/.cache/huggingface/hub/gemma-4-12b-4bit \
  --quantize --q-bits 4
```

## 3. Run training on Gemma 4 12B
Using 70K+ LoRA dataset priority batch (loop skill DPO pairs)
