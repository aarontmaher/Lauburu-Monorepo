# Gemini Lens Integration — Agent Instructions

## 1. Project Purpose
Bidirectional zero-mock sync between Screen Lens Sovereign, Gemini Spark/Notebook APIs, and PyCharm 2026.2. Dual-account (`aaron.t.maher@gmail.com` + `lauburu@lauburugrappling.com`), hourly sidecar automation.

## 2. Key Files
- `sync_engine.py` — CLI entrypoint (`--dry-run`, `--once`, `--account`)
- `auth_manager.py` — DualAccountManager, ADC + OAuth2 isolation
- `lens_client.py` — Screen Lens harvester (ports 3037/3035/4003 + SQLite fallback)
- `notebook_sync.py` — PyCharm workspace detector, atomic notebook cell injector
- `resilience.py` — 429 backoff, circuit-breaker, offline JSONL queue
- `config/sync_config.json` — canonical endpoints, accounts, rate limits

## 3. Running
```bash
cd 06_scripts_and_tooling/gemini_lens_integration
python3 sync_engine.py --dry-run      # validate, no credits burned
python3 sync_engine.py --once         # single sync
python3 sync_engine.py --account aaron.t.maher@gmail.com --once
```

## 4. Credentials
- Personal Admin: ADC at `~/.config/gcloud/legacy_credentials/aaron.t.maher@gmail.com/adc.json`, fallback `GEMINI_API_KEY`
- Workspace: OAuth2 token at `automation/workspace_token.json`, fallback `GEMINI_API_KEY_WORKSPACE`

## 5. Rate Limits
- 14 RPM / 1400 RPD per account
- 429 exponential backoff 1s–32s, 60s cooldown

## 6. Testing
```bash
python3 -m pytest tests/ -v
```
All tiers must pass before merge (M5 invariant).
