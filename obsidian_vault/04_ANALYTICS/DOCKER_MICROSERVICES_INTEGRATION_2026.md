---
title: "Docker Microservices & Container Orchestration Architecture"
date: 2026-09-02
tags: [docker, microservices, qdrant, seaweedfs, netbird, portainer, portal]
---

# 🐳 Docker Microservices Architecture & Container Integration

## 🏛️ 1. Architecture Overview
To avoid running isolated host services and enable reproducible 1-click deployments across the 7-layer mesh (Mac Mini M4 Pro, Linux Head Node, Cloud instances):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU DOCKER MICROSERVICES TOPOLOGY                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. MASTER COMPOSE STACK (00_core_infrastructure/docker-compose.master.yml)  │
│    • Qdrant Vector DB (Port 6333 / gRPC 6334) - High-throughput vectors    │
│    • SeaweedFS DFS (Port 9333 / Filer 8888) - Distributed dataset storage   │
│    • NetBird Dashboard & Management (Port 8087, 33073) - Open-source VPN    │
│    • Portainer CE (Port 9000, 9443) - Web GUI container manager            │
│    • Unified Portal Hub (Port 4000) - Production container image            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. UNIFIED PORTAL INTEGRATION (01_apps/unified_portal)                      │
│    • Dedicated "Docker Microservices" Tab in Web Portal                     │
│    • APIs: /api/v1/docker/status, /containers, /compose                     │
│    • Production Dockerfile: python:3.11-slim packaged bundle                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. CLI & SELF-HEALING TOOLING (06_scripts_and_tooling/lauburu_docker.py)    │
│    • Commands: status, start-daemon, up, down, ps                           │
│    • Automatic Colima detection & memory governance (4 CPUs, 8GB RAM)       │
└─────────────────────────────────────────────────────────────────────────────┘
```
