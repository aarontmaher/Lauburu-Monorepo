#!/usr/bin/env python3
"""
================================================================================
Google Colab + PyCharm Integration Setup Script
================================================================================
Location: /Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/setup_colab_pycharm.py

This script helps set up and verify the Google Colab + PyCharm integration
for the Lauburu Monorepo. It checks prerequisites, verifies dependencies,
and provides a quick-start notebook template.

Usage:
    python 06_scripts_and_tooling/automation/setup_colab_pycharm.py [--check] [--template]

Options:
    --check     Verify all prerequisites and dependencies
    --template  Generate a Colab-ready notebook template
================================================================================
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Project paths
REPO_ROOT = Path("/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo")
COLAB_NOTEBOOKS_DIR = REPO_ROOT / "04_data_and_memory"
NOTEBOOKS_DIR = REPO_ROOT / "01_apps" / "notebooks"
AUTOMATION_DIR = REPO_ROOT / "06_scripts_and_tooling" / "automation"

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        return False, f"Python 3.10+ required, found {version.major}.{version.minor}"
    return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"

def check_jupyter_dependencies() -> Dict[str, bool]:
    """Check if required Jupyter dependencies are installed."""
    dependencies = {
        "ipykernel": False,
        "jupyterlab": False,
        "torch": False,
        "datasets": False,
        "transformers": False,
        "psutil": False,
    }
    
    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            pass
    
    return dependencies

def check_pycharm_version() -> str:
    """Check if PyCharm is installed and suggest version."""
    # Check for PyCharm on macOS
    pycharm_paths = [
        Path("/Applications/PyCharm.app"),
        Path("/Applications/PyCharm CE.app"),
        Path("/Applications/PyCharm Community Edition.app"),
    ]
    
    for path in pycharm_paths:
        if path.exists():
            return f"PyCharm found at {path} ✓"
    
    return "PyCharm not found in /Applications. Install PyCharm 2025.3.2+ from https://www.jetbrains.com/pycharm/download/"

def list_colab_notebooks() -> List[Path]:
    """List all Colab-compatible notebooks in the project."""
    notebooks = []
    
    # Check main Colab notebook
    colab_notebook = COLAB_NOTEBOOKS_DIR / "colab_t4_five_domain_lora_distillation.ipynb"
    if colab_notebook.exists():
        notebooks.append(colab_notebook)
    
    # Check all notebooks in notebooks directory
    for nb in NOTEBOOKS_DIR.glob("*.ipynb"):
        notebooks.append(nb)
    
    # Check root notebooks
    for nb in REPO_ROOT.glob("*.ipynb"):
        notebooks.append(nb)
    
    return notebooks

def generate_colab_template() -> str:
    """Generate a Colab-ready notebook template."""
    template = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# 🚀 Lauburu Monorepo - Colab Notebook Template\n",
                    "**Purpose:** Template for running Lauburu notebooks on Google Colab\n",
                    "**GPU:** Tesla T4 (16 GB VRAM) or better\n",
                    "\n",
                    "This template is designed to work with PyCharm's native Colab integration.\n",
                    "Connect from PyCharm: Open notebook → Top-right server menu → Google Colab → New Colab Server"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# [1] Verify GPU Availability\n",
                    "import torch\n",
                    "import psutil\n",
                    "\n",
                    "print(\"=\" * 60)\n",
                    "print(\"🖥️  Colab Runtime Information\")\n",
                    "print(\"=\" * 60)\n",
                    "print(f\"Python: {sys.version}\")\n",
                    "print(f\"PyTorch: {torch.__version__}\")\n",
                    "print(f\"CUDA Available: {torch.cuda.is_available()}\")\n",
                    "if torch.cuda.is_available():\n",
                    "    print(f\"GPU: {torch.cuda.get_device_name(0)}\")\n",
                    "    print(f\"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB\")\n",
                    "print(f\"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB\")\n",
                    "print(\"=\" * 60)"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# [2] Install Required Dependencies\n",
                    "!pip install --quiet unsloth trl peft accelerate bitsandbytes datasets transformers"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# [3] Mount Google Drive (Optional)\n",
                    "# from google.colab import drive\n",
                    "# drive.mount('/content/drive')\n",
                    "# DATA_PATH = '/content/drive/MyDrive/Lauburu/data/'"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# [4] Connect to Screen Lens (Optional, via Tailscale)\n",
                    "# !curl -fsSL https://tailscale.com/install.sh | sh\n",
                    "# !sudo tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &\n",
                    "# !tailscale up --authkey=YOUR_AUTH_KEY\n",
                    "\n",
                    "import requests\n",
                    "\n",
                    "# Test Screen Lens connection\n",
                    "try:\n",
                    "    response = requests.get(\"http://100.119.199.76:3037/health\", timeout=5)\n",
                    "    print(f\"Screen Lens Health: {response.json()}\")\n",
                    "except Exception as e:\n",
                    "    print(f\"Screen Lens not reachable: {e}\")\n",
                    "    print(\"This is expected if Tailscale is not configured.\")"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# [5] Your Code Here\n",
                    "# Add your training, inference, or analysis code\n",
                    "\n",
                    "print(\"✅ Colab notebook ready for execution!\")"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0"
            },
            "accelerator": "GPU"
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    return json.dumps(template, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Google Colab + PyCharm Integration Setup")
    parser.add_argument("--check", action="store_true", help="Check prerequisites and dependencies")
    parser.add_argument("--template", action="store_true", help="Generate a Colab notebook template")
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔗 Google Colab + PyCharm Integration Setup")
    print("=" * 70)
    
    if args.check or not any([args.check, args.template]):
        print("\n📋 Prerequisites Check:")
        print("-" * 70)
        
        # Python version
        ok, msg = check_python_version()
        status = "✓" if ok else "✗"
        print(f"  [{status}] {msg}")
        
        # PyCharm
        pycharm_status = check_pycharm_version()
        if "✓" in pycharm_status:
            print(f"  [✓] {pycharm_status}")
        else:
            print(f"  [!] {pycharm_status}")
        
        # Dependencies
        print("\n📦 Dependencies:")
        print("-" * 70)
        deps = check_jupyter_dependencies()
        for dep, installed in deps.items():
            status = "✓" if installed else "✗"
            action = "installed" if installed else "NOT installed"
            print(f"  [{status}] {dep}: {action}")
        
        # Missing dependencies
        missing = [dep for dep, installed in deps.items() if not installed]
        if missing:
            print(f"\n💡 To install missing dependencies:")
            print(f"   pip install {' '.join(missing)}")
        
        # Notebooks
        print("\n📓 Available Notebooks:")
        print("-" * 70)
        notebooks = list_colab_notebooks()
        for nb in notebooks[:10]:  # Show first 10
            print(f"  • {nb.relative_to(REPO_ROOT)}")
        if len(notebooks) > 10:
            print(f"  ... and {len(notebooks) - 10} more")
    
    if args.template:
        print("\n📝 Generating Colab Notebook Template...")
        print("-" * 70)
        
        template = generate_colab_template()
        output_path = COLAB_NOTEBOOKS_DIR / "colab_template.ipynb"
        
        with open(output_path, 'w') as f:
            f.write(template)
        
        print(f"  ✓ Template saved to: {output_path.relative_to(REPO_ROOT)}")
        print(f"\n  To use this template in PyCharm:")
        print(f"  1. Open {output_path.relative_to(REPO_ROOT)} in PyCharm")
        print(f"  2. Click the server menu in the top-right corner")
        print(f"  3. Select Google Colab → New Colab Server → GPU")
        print(f"  4. Double-click to connect and run cells")
    
    print("\n" + "=" * 70)
    print("📖 For full documentation, see:")
    print(f"   {REPO_ROOT}/07_docs_and_architecture/GOOGLE_COLAB_PYCHARM_INTEGRATION.md")
    print("=" * 70)

if __name__ == "__main__":
    main()
