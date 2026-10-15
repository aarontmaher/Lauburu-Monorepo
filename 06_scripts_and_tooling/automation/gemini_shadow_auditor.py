import time
import os
import shutil
import ast
from datetime import datetime

WATCH_DIR = "/Volumes/Lauburu-Monorepo/01_apps/canonical_port/tui"
BACKUP_DIR = "/tmp/gemini_shadow_backups"
TELEMETRY_LOG = "/Volumes/Lauburu-Monorepo/04_data_and_memory/lens_daemon_telemetry.log"

def log_telemetry(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    with open(TELEMETRY_LOG, "a") as f:
        f.write(f"{timestamp} - {msg}\n")

def init_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    file_hashes = {}
    for root, _, files in os.walk(WATCH_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, WATCH_DIR)
                backup_path = os.path.join(BACKUP_DIR, rel_path.replace("/", "_"))
                shutil.copy2(file_path, backup_path)
                file_hashes[file_path] = os.path.getmtime(file_path)
    return file_hashes

def verify_ast(file_path):
    try:
        with open(file_path, "r") as f:
            source = f.read()
        ast.parse(source)
        return True
    except SyntaxError as e:
        return False
    except Exception:
        return False

def run_auditor():
    print("🛡️ Gemini 3.8 Flash Shadow Auditor Online. Monitoring AST integrity...")
    log_telemetry("🛡️ Gemini 3.8 Flash Shadow Auditor Online. Project corruption blocked.")
    
    file_states = init_backups()
    
    while True:
        time.sleep(2)
        for root, _, files in os.walk(WATCH_DIR):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    current_mtime = os.path.getmtime(file_path)
                    
                    if file_path not in file_states or current_mtime > file_states[file_path]:
                        # File was modified! Shadow Auditor steps in.
                        is_valid = verify_ast(file_path)
                        rel_path = os.path.relpath(file_path, WATCH_DIR)
                        backup_path = os.path.join(BACKUP_DIR, rel_path.replace("/", "_"))
                        
                        if is_valid:
                            # Update backup since it's a valid mutation
                            shutil.copy2(file_path, backup_path)
                            file_states[file_path] = current_mtime
                            log_telemetry(f"🛡️ Gemini 3.8 Flash: Verified safe AST mutation in {file}")
                        else:
                            # Revert or Delete!
                            if os.path.exists(backup_path):
                                shutil.copy2(backup_path, file_path)
                                file_states[file_path] = os.path.getmtime(file_path)
                                log_telemetry(f"🚨 Gemini 3.8 Flash VETO: Intercepted fatal syntax corruption in {file}. Change REVERTED.")
                            else:
                                os.remove(file_path)
                                if file_path in file_states:
                                    del file_states[file_path]
                                log_telemetry(f"🚨 Gemini 3.8 Flash VETO: Intercepted fatal syntax corruption in NEW file {file}. File DELETED.")

if __name__ == "__main__":
    run_auditor()
