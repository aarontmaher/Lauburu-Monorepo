# Google Colab + PyCharm Integration Guide

## Overview

This guide explains how to integrate Google Colab with PyCharm for the Lauburu Monorepo, enabling you to use Colab's free GPU resources (T4, V100, A100) directly within PyCharm's IDE while maintaining full IDE features like code navigation, refactoring, and inline outputs.

## Prerequisites

1. **PyCharm 2025.3.2+** (Professional or Community with Jupyter support)
   - Google Colab support is a core feature available for free
   - Check your version: `PyCharm` → `About` (macOS) or `Help` → `About` (Windows/Linux)

2. **Google Account** with access to Google Colab
   - Free tier provides T4 GPU (16 GB VRAM)
   - Pro/Pro+ provides V100/A100 GPUs with longer runtime

3. **Lauburu Monorepo** cloned locally with Jupyter dependencies:
   ```bash
   cd /Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo
   pip install ipykernel jupyterlab
   ```

## Step-by-Step Integration

### 1. Open a Jupyter Notebook in PyCharm

1. Open PyCharm and load the Lauburu Monorepo project
2. Navigate to any `.ipynb` file, e.g.:
   - `04_data_and_memory/colab_t4_five_domain_lora_distillation.ipynb`
   - `lens_global_orchestrator.ipynb`
   - Any notebook in `01_apps/notebooks/`

### 2. Connect to Google Colab Server

1. In the notebook editor, look at the **top-right corner** where the Jupyter server selector is located
2. Click the server dropdown menu
3. Select **Google Colab** from the list
4. **Sign in** with your Google account when prompted
5. Click **New Colab Server**
6. Choose the server type:
   - **GPU** (recommended for LoRA training, model inference)
   - **TPU** (for TensorFlow-specific workloads)
   - **CPU** (for lightweight tasks)
7. **Double-click** the connection to load it
8. The notebook is now connected to Colab's runtime

### 3. Verify GPU Access

Run this cell to confirm GPU availability:

```python
import torch
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
if torch.cuda.is_available():
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
```

Expected output for T4:
```
GPU: Tesla T4
VRAM: 15.79 GB
```

### 4. Working with Local Files

When your notebook references local files:

1. **Upload files directly**: If a file is missing on Colab, PyCharm will prompt you to upload it from your local environment
2. **Browse remote files**: The Project tool window shows the Colab file structure
3. **Sync datasets**: For large datasets, use Google Drive mounting:

```python
from google.colab import drive
drive.mount('/content/drive')
# Access files at /content/drive/MyDrive/
```

### 5. Running Existing Colab Notebooks

The monorepo has pre-configured Colab notebooks:

#### LoRA Distillation on Colab T4
- **Notebook**: `04_data_and_memory/colab_t4_five_domain_lora_distillation.ipynb`
- **Script**: `04_data_and_memory/colab_t4_unsloth_trainer.py`
- **Bridge**: `06_scripts_and_tooling/automation/colab_t4_ephemeral_bridge.py`

These are designed to offload heavy GPU work to Colab while preserving local RAM (Rule #3 Host Sanctuary).

## Integration with Screen Lens Ecosystem

The Screen Lens VLA ecosystem (ports 3035-3037, 4003-4006) can be accessed from Colab notebooks via the Lauburu mesh:

### Tailscale Mesh Connection (Optional)

For direct access to local services from Colab:

```python
# Install and configure Tailscale on Colab
!curl -fsSL https://tailscale.com/install.sh | sh
!sudo tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &

# Authenticate with your Tailscale auth key
!tailscale up --authkey=YOUR_AUTH_KEY
```

### Accessing Screen Lens APIs from Colab

```python
import requests

# Screen Lens Global Orchestrator state
response = requests.get("http://100.119.199.76:3037/api/orchestrator/state")
print(response.json())

# Health check
health = requests.get("http://100.119.199.76:3037/health")
print(health.json())
```

## Workflow Patterns

### Pattern 1: Local Development → Colab Training

1. Develop and test code locally in PyCharm with small datasets
2. Connect to Colab for full-scale training
3. Download trained models back to local storage

```python
# Save model on Colab
model.save_pretrained("/content/trained_model")

# Download to local (in PyCharm)
from google.colab import files
files.download("/content/trained_model/pytorch_model.bin")
```

### Pattern 2: Colab as GPU Accelerator

Use the ephemeral bridge script to automatically offload when local RAM is low:

```bash
python 06_scripts_and_tooling/automation/colab_t4_ephemeral_bridge.py --offload
```

This checks local memory (Rule #3: >= 4.8 GB buffer) and generates Colab-ready notebooks.

### Pattern 3: Hybrid Inference

Run lightweight inference locally, heavy inference on Colab:

```python
import psutil

def should_offload_to_colab(min_ram_gb=4.8):
    available_gb = psutil.virtual_memory().available / (1024**3)
    return available_gb < min_ram_gb

if should_offload_to_colab():
    # Switch to Colab runtime
    print("Offloading to Colab T4...")
else:
    # Run locally
    print("Running on local GPU/CPU...")
```

## PyCharm Run Configurations for Colab

Create run configurations for seamless execution:

### 1. Notebook Run Configuration
- Go to `Run` → `Edit Configurations`
- Add `Python` configuration
- Script path: point to your notebook or Python script
- Working directory: `/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo`
- Environment variables:
  ```
  PYTHONPATH=/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo
  ```

### 2. Colab Bridge Script
- Script: `06_scripts_and_tooling/automation/colab_t4_ephemeral_bridge.py`
- Arguments: `--offload --domain screen-lens-sovereign`

## Troubleshooting

### Connection Issues
- **Problem**: Cannot connect to Colab
- **Solution**: Ensure PyCharm is updated to 2025.3.2+ and you're signed into Google

### GPU Not Available
- **Problem**: `torch.cuda.is_available()` returns False
- **Solution**: In Colab, go to `Runtime` → `Change runtime type` → Select GPU

### File Sync Issues
- **Problem**: Local files not visible in Colab
- **Solution**: Use the upload prompt in PyCharm or mount Google Drive

### Session Timeout
- **Problem**: Colab session disconnects
- **Solution**: 
  - Free tier: ~12 hours max, 90 minutes idle timeout
  - Keep notebook active with periodic cell execution
  - Save checkpoints frequently

## Best Practices

1. **Always save checkpoints** during long training runs
2. **Use 4-bit quantization** (Unsloth) to maximize VRAM efficiency
3. **Monitor local RAM** before offloading (Rule #3 Host Sanctuary)
4. **Use Tailscale** for secure mesh access to local services
5. **Version control** your notebooks with git
6. **Document dependencies** in `pyproject.toml` or `requirements.txt`

## Related Resources

- **PyCharm Blog**: [Google Colab Support in PyCharm](https://blog.jetbrains.com/pycharm/2026/01/google-colab-support-is-now-available-in-pycharm-2025-3-2)
- **Colab Telemetry**: `obsidian_vault/05_TRAINING/COLAB_T4_OFFLOAD_TELEMETRY.md`
- **Screen Lens Skill**: Ports 3035-3037, 4003-4006 for VLA orchestration
