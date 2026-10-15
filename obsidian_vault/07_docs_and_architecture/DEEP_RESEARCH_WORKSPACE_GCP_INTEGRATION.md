---
title: "Deep Research: Full Google Workspace & GCP Free Tier Integration"
tags: [lauburu, deep-research, gcp, workspace, architecture]
date: "2026-09-15"
---

# 🔬 Hybrid Local-Cloud Deep Research Report
**Subject:** Google Workspace & Google Cloud Platform (GCP) Free Tier Integration  
**Methodology:** Zero-Cost Architecture, Secure Pub/Sub Mesh Bridging, and Tri-Vault Sync

## 1. Executive Summary & Problem Statement
The recent system reboot and subsequent `localhost.run` tunnel timeout exposed the fragility of using public SSH reverse tunnels to bridge Google Chat with the local Lauburu 7-Layer Mesh. To achieve absolute stability with **$0 monthly cloud spend**, we must shift the inbound webhook listener off the local Mac Mini and onto Google Cloud's **Always Free Tier**.

By leveraging GCP Serverless (Cloud Run + Pub/Sub), we can create an indestructible, zero-trust bridge between Google Workspace and your local hardware, while simultaneously integrating Google Drive and Sheets for data retention.

---

## 2. The Free Tier Integration Matrix

### A. Google Cloud Platform (GCP) Free Tier Exploitation
We will utilize the following GCP Always Free quotas to build the bridge:
*   **Cloud Run (2 Million Requests/Month Free):** 
    *   *Usage:* Replaces the fragile Python `chat_app_listener.py` and Cloudflare/localtunnel setup. We deploy a tiny Python FastAPI container to Cloud Run. Google Chat posts to this highly available, auto-scaling endpoint.
*   **Cloud Pub/Sub (10 GB Messages/Month Free):** 
    *   *Usage:* The Cloud Run container validates the Chat message and publishes it to a Pub/Sub topic (e.g., `mesh-inbound`). Your local Mac Mini simply runs a background subscriber daemon. **This eliminates all need for reverse tunneling, port forwarding, or public IPs on your home network.**
*   **Compute Engine `e2-micro` (730 Hours/Month Free in us-west1):** 
    *   *Usage:* Provision a permanent Linux bastion node. Install Tailscale on it to join your 7-Layer Mesh. This acts as an always-on cloud exit node and external heartbeat monitor for your local hardware.

### B. Google Workspace App Integration
*   **Google Chat API (Two-Way Bot):** 
    *   *Usage:* Upgraded interactive bot (`@Lauburu Swarm`). Commands typed on your phone are instantly routed through Cloud Run -> Pub/Sub -> Mac Mini.
*   **Google Sheets API (Looker Studio Telemetry):**
    *   *Usage:* The Mac Mini aggregates telemetry across the 7 physical layers and streams it to a dedicated Google Sheet every 15 minutes. This Sheet powers a free Looker Studio dashboard for live visual mesh health.
*   **Google Drive API (Tri-Vault Sync):**
    *   *Usage:* Automated `rclone` cron jobs push nightly Parquet LoRA datasets and Obsidian Vault markdown backups to your Google Drive, utilizing your Workspace storage limits for disaster recovery.

---

## 3. The New "Pub/Sub Mesh Bridge" Architecture

```mermaid
graph TD
    A[Google Chat (Phone/Web)] -->|POST / webhook| B[GCP Cloud Run Endpoint]
    B -->|Authenticates & Parses| C[GCP Pub/Sub Topic: mesh-commands]
    
    subgraph Lauburu 7-Layer Mesh (Local)
    D[Mac Mini L1] -->|Polls/Subscribes| C
    D -->|Executes Local Script| E[Mesh Healing / Operations]
    E -->|Success Response| F[Google Chat API REST]
    F --> A
    end
    
    subgraph Tri-Vault Cloud Sync
    D -->|Telemetry Streams| G[Google Sheets API]
    D -->|Nightly Backup| H[Google Drive API]
    end
```

---

## 4. Implementation Blueprint (Next Steps)

1. **GCP Project Setup:** Enable Cloud Run, Pub/Sub, and Drive APIs on your `lauburu-net-cloud` project.
2. **Deploy Cloud Run Bridge:** Write a 50-line Flask app, containerize it, and deploy it to Cloud Run. Set the Cloud Run URL as the Google Chat App endpoint.
3. **Local Pub/Sub Subscriber:** Replace `chat_app_listener.py` with `pubsub_mesh_daemon.py` on the Mac Mini. It securely pulls messages using a Service Account Key (`.json`), requiring no open firewall ports.
4. **Drive & Sheets Daemon:** Write Python scripts using `google-api-python-client` with Domain-Wide Delegation to seamlessly sync the `obsidian_vault` and LoRA datasets to Drive.

## 5. LoRA Distillation Serialized
*An instruction pair for this architectural transition has been formatted for the `lora_datasets` to enforce future avoidance of SSH reverse tunnels in favor of Pub/Sub event buses.*
