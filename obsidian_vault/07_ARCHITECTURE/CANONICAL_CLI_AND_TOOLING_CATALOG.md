---
title: "Canonical CLI Tooling Knowledge Base & Execution Catalog for Qwen MoE"
tags: [cli, github_cli, adb, tailscale, wrangler, jules, uv, docker, shopify, loop, qwen_moe]
created: 2026-09-02
subsystems: [00_core_infrastructure, 05_agents_and_swarms, 06_scripts_and_tooling]
---

# 🛠️ Canonical CLI Tooling Knowledge Base & Execution Catalog

**`Qwen MoE`** integrates direct programmatic execution and knowledge indexing across 10 frontier CLI suites:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                CANONICAL CLI TOOLING CATALOG & PATH MATRIX                             │
├───────────────────────┬──────────────────────────────────┬─────────────────────────────────────────────┤
│ CLI Suite             │ Absolute Path                    │ Core Capability & Swarm Role                │
├───────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤
│ **1. GitHub CLI**     │ `/Users/aaron/.local/bin/gh`     │ PRs, issue backlogs, repo sync, GHA secrets │
│ **2. Git Core**       │ `/usr/bin/git`                   │ Worktrees, sparse checkout, branch linages  │
│ **3. Android ADB**    │ `/Users/aaron/.local/bin/adb`    │ Port 5555 TCP, Termux keepalive, Doze bypass│
│ **4. Tailscale**      │ `/Users/aaron/.local/bin/tailscale`│ 7-Layer WireGuard mesh ping & peer topology │
│ **5. Wrangler**       │ `npx -y wrangler`                │ Cloudflare Workers, D1 SQLite, Vectorize, AI│
│ **6. Google Jules**   │ `/Users/aaron/.local/bin/jules`  │ Multi-file async GitHub repo refactor agent │
│ **7. Astral uv**      │ `/Users/aaron/.local/bin/uv`     │ Sub-10ms Python package sync & pytest runner│
│ **8. Shopify CLI**    │ `~/.nvm/.../bin/shopify`         │ Storefront GraphQL, theme & app dev servers │
│ **9. jq Streamer**    │ `/usr/bin/jq`                    │ High-speed JSONL dataset filtering & counts │
│ **10. Docker**        │ `/Users/aaron/.local/bin/docker` │ SeaweedFS DFS, Ray Cluster & Petals DHT     │
└───────────────────────┴──────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## ⚡ 1. GitHub CLI (`gh`) Integration

- **List Open PRs:** `gh pr list --state open`
- **Create Pull Request:** `gh pr create --title "..." --body "..."`
- **Sync Fork:** `gh repo sync`
- **Check Workflow Runs:** `gh run list --limit 5`

---

## 📱 2. Android Debug Bridge (`adb`) Integration

- **Inspect Hardware Nodes:** `adb devices -l`
- **Inject 24/7 Keepalive:** `adb shell termux-wake-lock`
- **Whitelist Doze Optimization:** `adb shell dumpsys deviceidle whitelist +com.termux`

---

## ☁️ 3. Cloudflare Wrangler (`wrangler`) Integration

- **Verify Account:** `npx wrangler whoami`
- **Deploy Agents SDK:** `npx wrangler deploy`
- **Execute SQLite Queries:** `npx wrangler d1 execute DB --command "SELECT count(*) FROM state;"`

---

## 🚀 4. Google Jules (`jules`) Integration

- **Dispatch Remote Refactor:** `jules remote new --repo aarontmaher/Lauburu-Monorepo --session "..."`
- **Apply Pull Patch:** `jules remote pull --session <ID> --apply`
