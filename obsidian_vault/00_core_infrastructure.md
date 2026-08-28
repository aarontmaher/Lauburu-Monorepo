---
title: "00_core_infrastructure — Core Mesh Infrastructure & Containerization"
updated: "2026-08-27"
tags: [infrastructure, seaweedfs, docker, tailscale, supabase, cloudflare, launchd, spec-00]
---

# 00_core_infrastructure — Core Mesh Infrastructure & Containerization

## 📋 Scope & Responsibility
Houses all clustering, distributed storage aggregation, network routing, container definitions, and background daemon services powering the 7-device Lauburu Mesh.

## 🏗️ Core Subsystems & Components
1. **SeaweedFS Distributed File System:**
   - Master (`:9333`), Filer (`:8888`), and Volume servers aggregating multi-device storage.
   - High-speed 10Gbps Thunderbolt 4 bridge (`bridge0`, `169.254.187.138`) binding for low-latency (<0.3ms) data transfer.
   - S3-compatible API gateway and POSIX FUSE mount integration.
2. **Docker Compose Infrastructure (`00_core_infrastructure/docker/`):**
   - Microservice container definitions, multi-node overlay networks, and isolated execution sandboxes.
3. **Tailscale & WireGuard Mesh Overlay:**
   - Layer 3 encrypted peer-to-peer mesh connecting all nodes (`100.119.199.76`, `100.103.212.21`, etc.) with DERP relay fallback.
4. **Cloudflare Workers & Supabase Edge Functions:**
   - Global ingress routing, telemetry ingestion endpoints, and authentication verification (`cloudflare_worker/`, `supabase/`).
5. **Self-Healing Sentinel & LaunchDaemons:**
   - Automated health monitoring daemons (Port 18802) for continuous storage, network, and process revival.

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-00-core-infrastructure`
- **Focus Areas:** SeaweedFS clustering, Docker container lifecycle, Tailscale mesh routing, launchd/systemd management.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Storage Governance:** [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- **Deep Architecture:** [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Connected Modules:** [[01_apps]], [[06_scripts_and_tooling]], [[11_security_and_governance]]
