"""
GCP BigQuery & GCS Exporter Daemon

Consumes massive dataset dumps via ZMQ and uploads them to GCS as Parquet files,
then registers them as External Tables in BigQuery.
"""
import os
import json
import time
import tempfile
import zmq

try:
    import pandas as pd
    from google.cloud import storage
    from google.cloud import bigquery
except ImportError:
    print("Please install missing dependencies: pip install google-cloud-bigquery google-cloud-storage pandas pyarrow zmq")
    import sys
    sys.exit(1)

ZMQ_URL = "tcp://127.0.0.1:5555"
ZMQ_TOPIC = b"LORA.DATASET"
BUFFER_SIZE_LIMIT = 100
FLUSH_INTERVAL_SEC = 60

GCS_BUCKET = "lauburu-lora-datasets-free-tier"
BQ_DATASET = "lauburu_datasets"
BQ_TABLE = "lora_external"

def upload_to_gcs_and_register_bq(df):
    """Saves to parquet, uploads to GCS, and updates BigQuery External Table."""
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df.to_parquet(tmp_path, index=False)
        
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/token.json")
        storage_client = storage.Client(credentials=creds, project="acoustic-welder-508220-n7")
        bucket = storage_client.bucket(GCS_BUCKET)
        if not bucket.exists():
            bucket.create()
            
        blob_name = f"dataset_{int(time.time())}.parquet"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(tmp_path)
        
        print(f"Uploaded Parquet to gs://{GCS_BUCKET}/{blob_name}")
        
        bq_client = bigquery.Client(credentials=creds, project="acoustic-welder-508220-n7")
        dataset_ref = bq_client.dataset(BQ_DATASET)
        
        try:
            from google.api_core.exceptions import NotFound
            bq_client.get_dataset(dataset_ref)
        except NotFound:
            bq_client.create_dataset(bigquery.Dataset(dataset_ref))
            
        table_ref = dataset_ref.table(BQ_TABLE)
        
        external_config = bigquery.ExternalConfig("PARQUET")
        external_config.source_uris = [f"gs://{GCS_BUCKET}/*.parquet"]
        external_config.autodetect = True
        
        table = bigquery.Table(table_ref)
        table.external_data_configuration = external_config
        
        try:
            bq_client.get_table(table)
            bq_client.update_table(table, ["external_data_configuration"])
            print(f"Updated BQ External Table {BQ_DATASET}.{BQ_TABLE}")
        except NotFound:
            bq_client.create_table(table)
            print(f"Created BQ External Table {BQ_DATASET}.{BQ_TABLE}")
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(ZMQ_URL)
    socket.setsockopt(zmq.SUBSCRIBE, ZMQ_TOPIC)
    
    print(f"Listening on {ZMQ_URL} for topic {ZMQ_TOPIC}...")
    
    buffer = []
    last_flush_time = time.time()
    
    while True:
        try:
            topic, msg = socket.recv_multipart(flags=zmq.NOBLOCK)
            try:
                record = json.loads(msg.decode('utf-8'))
                buffer.append(record)
            except json.JSONDecodeError:
                pass
        except zmq.Again:
            time.sleep(0.1)
            
        now = time.time()
        if len(buffer) >= BUFFER_SIZE_LIMIT or (len(buffer) > 0 and now - last_flush_time >= FLUSH_INTERVAL_SEC):
            print(f"Flushing {len(buffer)} records to Parquet/GCS...")
            df = pd.DataFrame(buffer)
            try:
                upload_to_gcs_and_register_bq(df)
                buffer.clear()
                last_flush_time = time.time()
            except Exception as e:
                print(f"Failed to process batch: {e}")
                # Prevent infinite buffer growth on persistent failure
                if len(buffer) > 10000:
                    print("Buffer limit exceeded, dropping oldest data.")
                    buffer = buffer[-5000:]
                time.sleep(5)  # Backoff

if __name__ == "__main__":
    main()
