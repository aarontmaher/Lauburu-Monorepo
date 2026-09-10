---
title: "Google Workspace & Gmail API Unified Mesh Integration"
date: "2026-09-08T12:30:00+00:00"
tags: [google_workspace, gmail_api, dwd_gateway, auth_sentinel, zero_mock, mesh_alerts, multi_account]
aliases: ["Google Workspace Integration", "Gmail API Sentinel"]
---

# 📬 Google Workspace & Gmail API Unified Mesh Integration

## 1. Architectural Overview & Topology
The Lauburu Monorepo integrates Google Workspace services to provide out-of-band telemetry alerts, automated inbound task ingestion, and continuous architectural documentation across the 7-layer physical mesh.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   LAUBURU GOOGLE WORKSPACE TOPOLOGY                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Enterprise Workspace Account: lauburu@lauburugrappling.com               │
│    • Domain: lauburugrappling.com (Google Workspace Business Plus)          │
│    • Role: Official organization bot, Google Chat Card v2, Drive Archival.  │
│    • Auth: Centralized Domain-Wide Delegation (DWD) Gateway on Port 18802.  │
│    • Transport: Gmail REST API v1 (via Bearer Token) / SMTP fallback.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Mesh Sovereign Admin Account: aaron.t.maher@gmail.com                    │
│    • Role: Developer admin, Google AI Ultra subscription anchor.            │
│    • Auth: Authenticated Google App Password (0600) + gcloud ADC.           │
│    • Transport: Google TLS SMTP (Port 587) & IMAP (Port 993).               │
│    • Zero-Mock Empirical Status: AUTHENTICATED (52,454+ emails, live probe).│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules & Subsystems

1. **Central DWD Auth Gateway (`00_core_infrastructure/auth/workspace_dwd_gateway.py`)**:
   - Manages Bearer token lifecycle, 300s TTL proactive caching, and multi-tier credential cascade:
     - Tier 1: Service Account Key (`service_account.json`) with Domain-Wide Delegation.
     - Tier 2: Dedicated Workspace Token (`~/.config/lauburu/workspace_token.json`).
     - Tier 3: Headless GDrive User Token (`token.json`).
     - Tier 4: Application Default Credentials (`~/.config/gcloud/legacy_credentials/.../adc.json`).
   - Private keys and credential files strictly restricted to `0600` permissions on L1 Mac Mini Host.

2. **Unified Configuration (`00_core_infrastructure/config/gmail_workspace_config.json`)**:
   - Stores account metadata, port routing, and environment variable overrides (`GMAIL_APP_PASSWORD`, `LAUBURU_GMAIL_APP_PASSWORD`).
   - File mode locked to `0600`.

3. **Gmail Workspace Client (`06_scripts_and_tooling/notifications/gmail_workspace_client.py`)**:
   - Implements dual-transport architecture:
     - REST Gmail API v1 over OAuth2 Bearer tokens.
     - Native Python TLS SMTP (587) and IMAP (993) with zero external dependency.
   - Core capabilities:
     - `send_email(to, subject, body, html, attachments, sender)`
     - `fetch_inbox(account, query, limit)`
     - `fetch_unread_directives(account)` (Subject: `[LAUBURU-COMMAND]`)
     - `check_account_health(account)` (Empirical round-trip latency and inbox counts)
     - `send_mesh_alert(title, details, severity)`

4. **Google Workspace Unified Manager (`06_scripts_and_tooling/notifications/google_workspace_unified_manager.py`)**:
   - Integrates all 5 pillars: Google Chat Card v2, Google Drive VFS, Gmail API Alert Bus, Google Sheets Telemetry, and DWD Auth Sentinel.
   - CLI flags: `--status`, `--probe-live`, `--gmail-status`, `--gmail-inbox`, `--gmail-send`.

5. **Self-Healing Hub REST API (`00_core_infrastructure/self_healing_hub/src/api_server.py`)**:
   - `GET /api/workspace/status`: Overview across all 5 Workspace pillars.
   - `GET /api/workspace/gmail/status`: Real-time empirical health check of configured accounts.
   - `GET /api/workspace/gmail/inbox`: Authenticated IMAP message extraction.
   - `POST /api/workspace/gmail/send`: Authenticated email dispatch.

---

## 3. Zero-Mock Verification Evidence (Rule #0 / #1)

Empirical execution verified on 2026-09-08:
- **IMAP Connection:** `imap.gmail.com:993` -> `52,454` total messages, `394` unread.
- **SMTP Connection:** `smtp.gmail.com:587` -> TLS login successful.
- **DWD Token Minting:** `ACTIVE` Bearer token resolution via gcloud ADC cascade.
- **Automated Test Suite:** `7/7 PASSED` in `06_scripts_and_tooling/tests/test_gmail_workspace_integration.py`.
- **E2E Suite:** `5/5 STAGES PASSED` in `06_scripts_and_tooling/notifications/test_e2e_google_workspace.py`.
- **Workspace Master Suite:** `5/5 PASSED` in `06_scripts_and_tooling/tests/test_google_workspace_suite.py`.

---

## 4. Wikilinks & Cross-References
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[AUTOMATED_E2E_WORKSPACE_SETUP_REPORT_2026]]
- [[DEBATE_GOOGLE_WORKSPACE_LENS_INTEGRATION_2026]]
- [[UNIFIED_TOOLING_AND_API_ECOSYSTEM_WHITEPAPER]]
