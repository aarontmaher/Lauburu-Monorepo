## 2026-08-23T06:40:44Z

# Dispatch for Worker M3 (Milestone 3: Persistent Background Execution & Process Supervision)

Working directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3`
Project root: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
Authoritative request: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md`
Scope document: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/PROJECT.md`
Test infra: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/TEST_INFRA.md`

## Mission
Deploy and verify persistent background execution, supervision, and coexistence on Pixel 10 Pro XL (`100.73.38.87 -p 8022`) via Termux:

1. **Runit Service Setup (`petals`)**:
   - Create `$PREFIX/var/service/petals/run` with `nice -n 10`, `OMP_NUM_THREADS=2`, `TMPDIR=$PREFIX/tmp`, `termux-wake-lock`, and `--host_maddrs /ip4/100.73.38.87/tcp/31330 --announce_maddrs /ip4/100.73.38.87/tcp/31330 --identity_path /data/data/com.termux/files/home/.petals_identity.id`.
   - Create `$PREFIX/var/service/petals/log/run` with `svlogd -tt $PREFIX/var/log/sv/petals`.
   - Set permissions (`chmod +x` on both run scripts).
   - Verify service is picked up by `runsvdir` and status is `run: petals`.
2. **Termux:Boot Persistence**:
   - Create/Update `/data/data/com.termux/files/home/.termux/boot/01-mesh-boot.sh` (chmod +x) ensuring idempotent launch of:
     - `termux-wake-lock`
     - `sshd` (port 8022)
     - `rpc-server` on `0.0.0.0:50052` (check if already running)
     - `service-daemon start` (managing runit services including `petals`)
3. **Guardian Management CLI**:
   - Deploy `/data/data/com.termux/files/home/petals_guardian.sh` (chmod +x) with support for `status`, `start`, `stop`, `restart`, `logs`, `health` (monitoring both Petals DHT and `rpc-server`).
4. **Coexistence & Non-Interference**:
   - Verify `rpc-server` on PID 7605 (`0.0.0.0:50052`) is preserved and operational.
5. **E2E Test Execution**:
   - Run Tier 1 Feature 5 (`TestTier1Feature5PersistentRunitService`) and Feature 6 (`TestTier1Feature6CoexistenceRPC`) in `tests/test_petals_mesh_e2e.py`.
   - Run full regression suite (Tier 1 Features 1-6).
6. Write your completion report to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/worker_m3/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-08-23T06:55:40Z

**Context**: Milestone 3 Deployment & SSH Connectivity
**Content**: 
1. The user environment includes the Multi-Transport Device Connectivity Hub with ADB support.
2. Please check if `adb devices` sees the Pixel 10 Pro XL (over USB or wireless ADB), and if so, send an intent to bring Termux to the foreground or start `sshd`:
   - `adb shell "am start -n com.termux/.app.TermuxActivity"`
   - or `adb shell "/data/data/com.termux/files/usr/bin/sshd"`
3. Also perform an automated retry loop for SSH on `100.73.38.87:8022` with backoff in case Android battery optimization or a brief network blip paused the background socket.
**Action**: Probe ADB / retry SSH, complete deployment of Milestone 3 deliverables, and report findings.
