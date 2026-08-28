# Handoff Report: Reviewer 1 — Milestone 2 (FUSE Mount Zombie Watchdog Daemon)

## 1. Observation

Direct empirical observations across the codebase and verification execution:

1. **Syntax & CLI Option Verification**:
   - `bash -n 00_core_infrastructure/scripts/fuse_watchdog.sh` returned exit code 0 (`SYNTAX_OK`).
   - `./00_core_infrastructure/scripts/fuse_watchdog.sh --help` printed full usage, options (`-m/--mount-point`, `-f/--filers`, `-i/--interval`, `-t/--timeout`, `--max-failures`, `-1/--once`, `--test`, `-v/--verbose`, `-h/--help`), and exit code 0.
   - `./00_core_infrastructure/scripts/fuse_watchdog.sh --unknown-flag` returned exit code 1 with error `Unknown option: --unknown-flag`.
   - Positional parsing (`fuse_watchdog.sh / 127.0.0.1:8888 --once --verbose`) correctly mapped mount point to `/` and filer list to `127.0.0.1:8888`.

2. **Self-Test Diagnostics Mode (`--test`)**:
   - `./00_core_infrastructure/scripts/fuse_watchdog.sh --test` completed with exit code 0:
     - Found tools: `stat` (`/usr/bin/stat`), `curl` (`/usr/bin/curl`), `pkill` (`/usr/bin/pkill`).
     - Selected probe engine: POSIX subshell timer fallback on macOS (or `timeout`/`gtimeout` if installed).
     - Verified canary probe on `/tmp` with exit code 0.
     - Verified SeaweedFS `weed` binary discovery at `/Users/aaron/.local/bin/weed`.

3. **Concurrency Control & Stale Lock Reclamation**:
   - Spawning concurrent instances against the same mount point resulted in the second instance detecting the active PID and exiting cleanly with:
     `2026-08-26T05:53:10Z [FUSE_WATCHDOG] [WARN] Another watchdog instance is actively running (PID: 48077) for mount point /. Exiting.`
   - Creating a simulated stale lock directory (`/tmp/fuse_watchdog_<hash>.lock.d`) with a dead PID (999999) resulted in:
     `2026-08-26T05:53:21Z [FUSE_WATCHDOG] [WARN] Stale lock directory detected (...). Re-acquiring lock...` and successful execution.

4. **Lazy Unmount & Eviction Mechanics**:
   - Script inspects host OS via `uname -s`.
   - On Linux (`Linux`): executes `pkill -9 -f "weed mount.*$MOUNT_POINT"`, `umount -l -f "$MOUNT_POINT"`, `fusermount3 -u -z "$MOUNT_POINT"`, `fusermount -u -z "$MOUNT_POINT"`, and writes `1` to `/sys/fs/fuse/connections/*/abort`.
   - On macOS (`Darwin`): executes `pkill -9 -f "weed mount.*$MOUNT_POINT"`, `diskutil unmount force "$MOUNT_POINT"`, and fallback `umount -f "$MOUNT_POINT"`.

5. **Pre-Flight HA Filer Reachability**:
   - Iterates over comma-separated endpoints with `curl -s --connect-timeout 2 --max-time 3 -I "$check_url"`.
   - When tested against an active ephemeral HTTP server, correctly reported `Reachable Filer found: 127.0.0.1:<port>`.
   - When tested against unreachable endpoints (`192.0.2.1:8888, 192.0.2.2:8888`), gracefully timed out after 2s connect timeout per endpoint and logged `No Filers currently reachable at (...). Offline mode operational.`.

6. **Systemd Service Unit Inspection**:
   - `00_core_infrastructure/systemd/dfs-fuse-watchdog.service` contains valid systemd unit configuration:
     - `Type=simple`, `User=root`, `Group=root`, `LimitNOFILE=65536`, `KillMode=process`.
     - `Restart=always`, `RestartSec=3`, `TimeoutSec=15`.
     - `After=network-online.target tailscaled.service docker.service dfs-fuse-mount.service`.
     - `PartOf=dfs-fuse-mount.service`.

7. **Symlink Integrity**:
   - `00_core_infrastructure/seaweedfs/fuse_watchdog.sh` -> `../scripts/fuse_watchdog.sh` (executable, symlink valid).

8. **Automated Test Suite Results**:
   - `pytest tests/test_seaweed_ha_watchdog.py -v`: **70 passed in 1.95s (100% PASS)**.
   - `pytest tests/test_adversarial_seaweed_raft_m1.py -v`: **36 passed in 3.06s (100% PASS)**.

---

## 2. Logic Chain

1. **Kernel Hang Prevention**: Direct, blocking VFS operations (`stat`, `ls`, `df`) on a deadlocked FUSE mount cause calling threads to block in uninterruptible kernel sleep (`D`/`U` state). The watchdog eliminates this by wrapping the canary probe in `timeout -k 1s -s KILL ${PROBE_TIMEOUT}s stat -t "$MOUNT_POINT"` (or a 100ms ticking subshell timer), ensuring the watchdog loop never locks up.
2. **Platform Portability**: macOS Darwin BSD kernel does not support Linux `umount -l` (lazy detachment) and will error out. By branching on `uname -s` to `diskutil unmount force` on Darwin and `umount -l -f` / `fusermount3 -u -z` on Linux, the daemon operates portably across all nodes of the 7-node Tailscale mesh.
3. **Flap Prevention**: Setting `MAX_FAILURES=2` prevents flapping or spurious unmounts during transient network blips (e.g. 1-second Wi-Fi re-keying or TCP retransmissions).
4. **Crash Loop Prevention**: `check_filer_reachability` validates that at least one SeaweedFS Filer node in the HA cluster is responding before executing `weed mount`, avoiding continuous failed spawn loops when the network mesh is offline.
5. **Concurrency Safety**: Dual-locking (`flock` on Linux, atomic directory with PID verification on macOS) prevents race conditions and ensures only one watchdog instance manages a specific mount point.

---

## 3. Caveats

- On macOS nodes, background service management uses launchd or standalone execution (`./fuse_watchdog.sh &`), as systemd is specific to Linux nodes.
- In production systemd deployment on Linux nodes, `fuse_watchdog.sh` should be placed or symlinked at `/usr/local/bin/fuse_watchdog.sh` as declared in `ExecStart`.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone 2 implementation strictly conforms to `PROJECT.md` and `ORIGINAL_REQUEST.md` specifications. The daemon script `fuse_watchdog.sh` is robust, handles kernel timeouts and unmount mechanics cleanly across both Linux and macOS platforms, enforces process locking, includes self-test diagnostics, and passes all 70 test suite cases with zero integrity violations or mock shortcuts.

---

## 5. Verification Method

To independently verify this review:

```bash
# 1. Verify shell syntax
bash -n 00_core_infrastructure/scripts/fuse_watchdog.sh

# 2. Run diagnostic self-test
./00_core_infrastructure/scripts/fuse_watchdog.sh --test

# 3. Test single-cycle probe
./00_core_infrastructure/scripts/fuse_watchdog.sh --once --mount-point / --verbose

# 4. Run full 4-tier test suite
pytest tests/test_seaweed_ha_watchdog.py -v

# 5. Run M1 regression suite
pytest tests/test_adversarial_seaweed_raft_m1.py -v
```
