# Project: OpenClaw & Cloudflare Network Mesh Stabilization

## Architecture
The OpenClaw environment hosts a local gateway service (`openclaw gateway`), a multi-transport network mesh (Tailscale Serve), an HTTP/WebSocket proxy (`scripts/openclaw_proxy.py`), and a Cloudflare Tunnel edge endpoint (`cloudflared`).

Data and control flow:
1. **Local Gateway**: Node.js OpenClaw gateway service running on port 18789 (`~/.openclaw/openclaw.json`).
2. **Tailscale Serve Mesh**: Exposes local port 18789 securely to Tailscale mesh devices via `--tailscale serve` CLI flag.
3. **OpenClaw Proxy**: Python reverse-proxy (`scripts/openclaw_proxy.py`) running on port 8181, proxying LLM requests to local `llama.cpp` or Gemini fallback, and forwarding Gateway traffic.
4. **Cloudflare Tunnel**: `cloudflared` daemon establishing free quick tunnel (`trycloudflare.com`) or named tunnel to edge, routing to proxy/gateway.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | OpenClaw Config Audit | Audit and fix `~/.openclaw/openclaw.json` and `~/.openclaw/config.json` syntax & schema errors | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Gateway Bind Config | Set `gateway.bind` to `"lan"` in `~/.openclaw/openclaw.json` | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Secure Bootstrap Token | Configure `gateway.auth.token` to `mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400` | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Tailscale Serve Integration | Update `start_standalone.sh` and launchd plist to run gateway with `--tailscale serve` and `--port 18789` | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Tailscale Mesh Status Verification | Verify active Tailscale Serve status programmatically via CLI / logs | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Cloudflare Tunnel Audit | Audit `cloudflared` installation and daemon startup in `start_standalone.sh` | M3 | ORIGINAL_REQUEST §R3 |
| 7 | WebSocket Proxy Handler | Add WebSocket proxying support for Gateway (port 18789) in `openclaw_proxy.py` | M3 | Survey Findings |
| 8 | Cloudflare $0 Mandate Compliance | Ensure tunnel setup relies exclusively on free Cloudflare Tunnels | M3 | ORIGINAL_REQUEST §R3 |
| 9 | E2E Acceptance Verification | Run config validation, Tailscale serve status, Cloudflare tunnel status, and test suites | M4 | ORIGINAL_REQUEST §Acceptance Criteria |
| 10| Forensic Integrity Audit | Perform independent audit for zero fake data, genuine implementation, and zero violations | M4 | Global Rules |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | OpenClaw Configuration Audit & Fix | Fix `~/.openclaw/openclaw.json` (`gateway.mode = "local"`, `gateway.bind = "lan"`, `gateway.auth.token`), clean invalid keys in `config.json`, validate schema | None | DONE |
| M2 | Tailscale Serve & Mesh Setup | Update launch scripts (`start_standalone.sh`) and plist to include `--tailscale serve` `--port 18789`, restart gateway, verify serve status | M1 | DONE |
| M3 | Cloudflare Tunnel & Proxy Integration | Add WebSocket proxying to `scripts/openclaw_proxy.py`, ensure `cloudflared` tunnel startup complies with $0 spend mandate | M2 | DONE |
| M4 | E2E Verification & Forensic Audit | Run end-to-end verification, test suites (`test_e2e_cloudflare_tunnel.py`), and teamwork_preview_auditor integrity audit | M1, M2, M3 | DONE |

## Interface Contracts
### Gateway ↔ Tailscale
- Binary: `/Applications/Tailscale.app/Contents/MacOS/Tailscale` or `tailscale`
- Port: 18789 (HTTPS/WebSocket)
- Flag: `--tailscale serve --port 18789`

### Gateway ↔ Proxy ↔ Cloudflare Tunnel
- Proxy port: 8181 (`http://127.0.0.1:8181`)
- Gateway port: 18789 (`ws://127.0.0.1:18789`)
- Bootstrap token: `mGe5qpmFqnVWbnf1v1y72hWOv0JnQBjoTjo_229F400`
- Tunnel: `cloudflared tunnel --url http://127.0.0.1:8181` (Free trycloudflare)

## Code Layout
- Main config: `~/.openclaw/openclaw.json`
- Secondary config: `~/.openclaw/config.json`
- Startup script: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/Standalone_Services/OpenClaw_Environment/start_standalone.sh`
- Proxy script: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/Standalone_Services/OpenClaw_Environment/scripts/openclaw_proxy.py`
- Launchd plist: `~/Library/LaunchAgents/ai.openclaw.gateway.plist`
- Test suite: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/Standalone_Services/OpenClaw_Environment/test_e2e_cloudflare_tunnel.py`
