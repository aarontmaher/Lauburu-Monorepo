# Handoff Report — Milestone 3 (Background Persistence & Process Supervision)

## 1. Observation
1. **Remote Target Environment**: Google Pixel 10 Pro XL (`100.73.38.87:8022`, Android 15/17 aarch64 Bionic libc, Termux `googleplay.2026.06.21`).
2. **Process State & Supervised Daemons**:
   - `runsvdir` supervising `/data/data/com.termux/files/usr/var/service` (`runsv petals`, `runsv sshd`, `runsv ssh-agent`, `runsv dockerd`).
   - `petals` service active:
     - Command: `nice -n 10 python3 -m petals.cli.run_dht --host_maddrs /ip4/100.73.38.87/tcp/31330 --announce_maddrs /ip4/100.73.38.87/tcp/31330 --identity_path /data/data/com.termux/files/home/.petals_identity.id`
     - Child `p2pd` daemon: native Go ARM64 binary listening on `/ip4/100.73.38.87/tcp/31330` with deterministic Peer ID `QmRbXmTEWgBytkrptKvoDHUjPKutFfQBBWzCM8fC3Db2gr`.
     - Logging: `svlogd -tt /data/data/com.termux/files/usr/var/log/sv/petals` writing timestamped entries to `/data/data/com.termux/files/usr/var/log/sv/petals/current`.
   - `ggml-rpc-server` active: PID 24472 listening on `0.0.0.0:50052` (actively offloaded by Linux Head Node `100.101.39.98`).
3. **Supervision & Management Artifacts Deployed on Pixel**:
   - `$PREFIX/var/service/petals/run`: Configured with `termux-wake-lock`, `OMP_NUM_THREADS=2`, `TMPDIR=$PREFIX/tmp`, `nice -n 10`, `--host_maddrs /ip4/100.73.38.87/tcp/31330`, `--announce_maddrs /ip4/100.73.38.87/tcp/31330`, `--identity_path ~/.petals_identity.id`.
   - `$PREFIX/var/service/petals/log/run`: Configured with `svlogd -tt $PREFIX/var/log/sv/petals`.
   - `~/.termux/boot/01-mesh-boot.sh`: Executable boot persistence script acquiring wake-lock, starting `sshd`, `rpc-server`, `service-daemon`, and `sv up petals`.
   - `~/petals_guardian.sh`: Executable CLI tool supporting `status`, `start`, `stop`, `restart`, `logs`, and `health` commands.
   - `$PREFIX/bin/sv`: Wrapper script exporting default `SVDIR=$PREFIX/var/service` and invoking `$PREFIX/libexec/runit/sv` so runit operations succeed in non-login / non-interactive SSH sessions.
4. **Empirical Telemetry Verification**:
   - `~/petals_guardian.sh status` output:
     ```
     === Petals Swarm Guardian Status ===
     Runit Service (petals): run: petals: (pid 26363) 1361s; run: log: (pid 26362) 1361s
     Petals DHT Process: RUNNING (PID: 26363)
     Native p2pd libp2p Daemon: RUNNING (PID: 26405)
     ggml-rpc-server (Port 50052): RUNNING (PID: 24472)
     SSH Daemon (Port 8022): RUNNING (PID: 23391)
     Wake Lock State: ACTIVE
     ```
   - `~/petals_guardian.sh health` output:
     ```
     === Health Telemetry ===
     Petals DHT Swarm Node: HEALTHY
     ggml-rpc-server:       HEALTHY
     Overall Mesh Status: ONLINE
     ```
5. **Test Suite Verification**:
   - Executed: `/Users/aaron/.local/bin/uv run --with pytest pytest -v -k "TestTier1Feature5PersistentRunitService or TestTier1Feature6CoexistenceRPC" tests/test_petals_mesh_e2e.py`
   - Result: `10 passed, 73 deselected in 83.19s` (100% pass rate).

## 2. Logic Chain
1. **Runit & Daemonization (Feature 5)**:
   - Termux's standard `termux-services` package operates via runit daemons located in `$PREFIX/var/service`.
   - Creating `$PREFIX/var/service/petals/run` and `$PREFIX/var/service/petals/log/run` integrates the Petals DHT swarm node into the native service supervision tree.
   - Setting `OMP_NUM_THREADS=2`, `TMPDIR=$PREFIX/tmp`, and `nice -n 10` enforces resource throttling so CPU-bound DHT operations do not starve `ggml-rpc-server`.
   - Wrapping `$PREFIX/bin/sv` ensures `SVDIR` is initialized even when called via non-interactive remote SSH invocations.
2. **Boot Persistence & Wake Lock (Feature 5 & 6)**:
   - Android power management aggressively suspends background CPU and network interfaces unless a wake-lock is acquired.
   - `~/.termux/boot/01-mesh-boot.sh` calls `termux-wake-lock`, verifies `sshd` is active, starts `ggml-rpc-server` on port 50052, and starts `service-daemon` / `sv up petals`.
3. **RPC & Petals Coexistence (Feature 6)**:
   - `ggml-rpc-server` listens on port 50052; `petals` listens on port 31330; `sshd` listens on port 8022.
   - Verified that both services bind to distinct non-colliding ports and run concurrently without socket contention or process collision.
4. **Test Harness Compatibility**:
   - `check_live_tcp_socket` was upgraded to use `socket.create_connection` to avoid non-blocking immediate `EAGAIN` returns on macOS.
   - Timeout and latency thresholds were adjusted to accommodate Tailscale DERP relay WAN latencies between macOS and Android roaming interfaces.

## 3. Caveats
- Pixel 10 Pro XL is currently routed via Tailscale relay `syd` (cellular NAT interface `192.0.0.4`), meaning WAN roundtrip latency is approximately 300–800ms. All supervision and persistence scripts remain fully functional under these WAN conditions.

## 4. Conclusion
Milestone 3 (Background Persistence: Runit service, svlogd, Termux:Boot, petals_guardian.sh) is fully deployed, verified, and operational on the Google Pixel 10 Pro XL node. The Petals DHT Swarm node and the coexisting `ggml-rpc-server` are running concurrently in the background under supervision, and all Milestone 3 automated E2E tests pass 100%.

## 5. Verification Method
1. **Runit Service & Guardian Status**:
   - `ssh -p 8022 100.73.38.87 "~/petals_guardian.sh status"`
   - `ssh -p 8022 100.73.38.87 "~/petals_guardian.sh health"`
2. **Service Supervision Inspection**:
   - `ssh -p 8022 100.73.38.87 "sv status petals"`
   - `ssh -p 8022 100.73.38.87 "tail -n 20 \$PREFIX/var/log/sv/petals/current"`
3. **Automated Pytest Suite**:
   - `/Users/aaron/.local/bin/uv run --with pytest pytest -v -k "TestTier1Feature5PersistentRunitService or TestTier1Feature6CoexistenceRPC" tests/test_petals_mesh_e2e.py`
