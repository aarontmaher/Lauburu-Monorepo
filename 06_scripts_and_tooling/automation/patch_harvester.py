import re

FILE_PATH = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/cloud_quota_harvester_daemon.py"

with open(FILE_PATH, "r") as f:
    content = f.read()

# We need to insert BigQuery logic right after writing to continuous_lora_dataset.jsonl
target_str = """                with open(LORA_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\\n")"""

bq_patch = """                with open(LORA_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\\n")
                
                # --- GCP FREE TIER REPLENISHABLE INTEGRATION ---
                # Mirroring the dataset directly to BigQuery
                try:
                    from google.cloud import bigquery
                    bq_client = bigquery.Client(project="acoustic-welder-508220-n7")
                    table_ref = "acoustic-welder-508220-n7.lauburu_mesh.continuous_lora_dataset"
                    errors = bq_client.insert_rows_json(table_ref, [record])
                    if errors:
                        log.warning(f"Failed BigQuery push (table might not exist yet): {errors}")
                    else:
                        log.info(f"✅ Replicated LoRA row to BigQuery {table_ref} (Free Tier 1TB/mo)")
                except ImportError:
                    pass
                except Exception as e:
                    # Catch authentication/permissions errors transparently without crashing the daemon
                    log.warning(f"BigQuery ADC Auth pending. Error: {str(e)[:100]}")
                # -----------------------------------------------"""

if target_str in content:
    content = content.replace(target_str, bq_patch)
    with open(FILE_PATH, "w") as f:
        f.write(content)
    print("Patched harvester with BigQuery integration.")
else:
    print("Could not find target string in harvester.")
