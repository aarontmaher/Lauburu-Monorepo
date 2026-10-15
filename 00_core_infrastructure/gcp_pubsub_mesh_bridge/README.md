# GCP Pub/Sub Mesh Bridge

## Architecture Consensus (via AI Debate Protocol)
The AI Debate swarm (Cloud Shadow Orchestrator, Local AI, and Devil's Advocate) convened to evaluate replacing fragile SSH/Tailscale tunnels for Google Chat with a "Pub/Sub Mesh Bridge".

### Verdict: Approved (with Hardware Governance Warning)
- **Robustness (Approved):** By utilizing Google Cloud Run as the webhook receiver and Pub/Sub as the queue, inbound NAT/Tailscale fragility is bypassed. If the local network drops, messages simply queue in Pub/Sub until the subscriber reconnects.
- **Google Workspace Integration:** The architecture successfully integrates Google Sheets for telemetry logging and Google Drive for payload backups.
- **Rule #3 & #10 Violation Warning (Devil's Advocate Catch):** The original proposal suggested running the local subscriber daemon on the Mac Mini. This violates the **Mac Mini Host Physical Sanctuary Headroom** and the **Linux Mini First-Offload Invariant**. The Mac Mini must be preserved exclusively for the Master Orchestrator (Qwen 3.8 Max Duo). Therefore, while the code is named/designed as requested, it is **strongly recommended to deploy `local_subscriber` onto the L3 Linux Head Node** (`100.101.39.98`).

## Components
1. **`cloud_run_publisher/`**: A FastAPI service intended to be deployed on Google Cloud Run. It receives incoming webhooks from Google Chat and publishes the raw payload to a Pub/Sub topic (`google-chat-inbound`).
2. **`local_subscriber/`**: A Python daemon (to be run on the Linux Mini) that subscribes to `google-chat-outbound` (or `google-chat-inbound`), processes the messages, logs telemetry to a Google Sheet, and backs up the payload to Google Drive.

## Deployment
### 1. Cloud Run Publisher
```bash
cd cloud_run_publisher
gcloud run deploy google-chat-bridge \
  --source . \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=lauburu-project,PUBSUB_TOPIC_ID=google-chat-inbound
```

### 2. Local Subscriber
```bash
cd local_subscriber
pip install -r requirements.txt
# Set environment variables for Sheet ID, Drive Folder ID, etc.
python3 subscriber.py
```
