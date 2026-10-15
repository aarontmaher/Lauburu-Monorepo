#!/usr/bin/env python3
"""
================================================================================
Lauburu Mesh Exclusive Model Switcher & 5GB RAM Sanctuary Governor
================================================================================
Governs single-model exclusive execution on the Mac Mini M4 Pro host (24 GB RAM)
so that 16.0 GB frontier models (Qwen 3.8 Max Standard & Abliterated) can run
independently on the Metal GPU without memory exhaustion or Metal buffer panics.
"""

import os
import sys
import time
import json
import signal
import subprocess
import urllib.request
import psutil
from pathlib import Path

MODEL_VAULT = Path('/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf')

MODELS = {
    'standard': {
        'name': 'Qwen 3.8 Max Standard',
        'path': MODEL_VAULT / 'Qwen3.8-27B-UD-Q4_K_XL.gguf',
        'port': 8081,
        'ctx': 2048,
        'batch': 256,
        'ngl': 99
    },
    'abliterated': {
        'name': 'Qwen 3.8 Max 27B Abliterated',
        'path': MODEL_VAULT / 'Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf',
        'port': 8083,
        'ctx': 2048,
        'batch': 256,
        'ngl': 99
    },
    'coder': {
        'name': 'Qwen 2.5 Coder 7B',
        'path': MODEL_VAULT / 'qwen2.5-coder-7b-instruct-q4_k_m.gguf',
        'port': 8081,
        'ctx': 4096,
        'batch': 512,
        'ngl': 99
    }
}

def kill_existing_llama_servers():
    print('Terminating any existing local llama-server processes on Mac Mini...')
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'llama-server' in p.info['name'] or any('llama-server' in arg for arg in (p.info['cmdline'] or [])):
                print(f'Killing PID {p.info["pid"]} ({p.info["name"]})')
                p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(1.5)

def check_ram_headroom():
    vm = psutil.virtual_memory()
    avail_gb = vm.available / (1024**3)
    print(f'Mac Mini Available RAM: {avail_gb:.2f} GB (Total: {vm.total / (1024**3):.2f} GB)')
    return avail_gb

def switch_model(target_key):
    if target_key not in MODELS:
        print(f'Error: Unknown target {target_key}. Choose from: {list(MODELS.keys())}')
        sys.exit(1)
        
    cfg = MODELS[target_key]
    if not cfg['path'].exists():
        print(f'Error: Model file does not exist at {cfg["path"]}')
        sys.exit(1)
        
    print(f'=== Switching Exclusive Local Model to: {cfg["name"]} ===')
    print(f'File: {cfg["path"]} ({cfg["path"].stat().st_size / (1024**3):.2f} GB)')
    
    # 1. Kill any existing instances to guarantee mutual exclusivity
    kill_existing_llama_servers()
    
    # 2. Check RAM
    avail = check_ram_headroom()
    
    # 3. Formulate launch command
    cmd = [
        '/Users/aaron/.local/bin/llama-server',
        '-m', str(cfg['path']),
        '--host', '0.0.0.0',
        '--port', str(cfg['port']),
        '-c', str(cfg['ctx']),
        '-b', str(cfg['batch']),
        '-ngl', str(cfg['ngl']),
        '--no-mmap'
    ]
    
    log_path = f'/tmp/llama_server_{target_key}.log'
    print(f'Launching: {" ".join(cmd)}')
    print(f'Logging to: {log_path}')
    
    log_f = open(log_path, 'w')
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT)
    
    print('Waiting for model to initialize into Metal GPU...')
    for i in range(60):
        time.sleep(1)
        if proc.poll() is not None:
            print(f'Server failed to start! Return code: {proc.returncode}')
            with open(log_path, 'r') as f:
                print('--- Server Log ---')
                print(f.read())
            sys.exit(1)
            
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{cfg["port"]}/health', timeout=1) as resp:
                data = json.loads(resp.read().decode())
                if data.get('status') in ['ok', 'no slot available']:
                    print(f'
Model {cfg["name"]} is ONLINE and HEALTHY on port {cfg["port"]}!')
                    check_ram_headroom()
                    return proc
        except Exception:
            print('.', end='', flush=True)
            
    print('
Timeout waiting for model startup.')
    proc.kill()
    sys.exit(1)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'standard'
    switch_model(target)
