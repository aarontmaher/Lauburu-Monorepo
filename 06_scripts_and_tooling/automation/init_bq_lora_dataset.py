#!/usr/bin/env python3
import os
import sys

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
except ImportError:
    print("google-cloud-bigquery not installed. Run: pip install --break-system-packages google-cloud-bigquery")
    sys.exit(1)

PROJECT_ID = "acoustic-welder-508220-n7"
DATASET_ID = "lauburu_mesh"
TABLE_ID = "continuous_lora_dataset"

client = bigquery.Client(project=PROJECT_ID)

# Create Dataset
dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
try:
    client.get_dataset(dataset_ref)
    print(f"Dataset {dataset_ref} already exists.")
except NotFound:
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    dataset = client.create_dataset(dataset, timeout=30)
    print(f"Created dataset {dataset.project}.{dataset.dataset_id}")

# Create Table
table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
schema = [
    bigquery.SchemaField("interaction_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
    bigquery.SchemaField("provider", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("prompt", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("reasoning_trace", "STRING", mode="NULLABLE")
]

try:
    client.get_table(table_ref)
    print(f"Table {table_ref} already exists.")
except NotFound:
    table = bigquery.Table(table_ref, schema=schema)
    # Partitioning by day helps analytics and saves money/quota
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp" 
    )
    table = client.create_table(table)
    print(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
