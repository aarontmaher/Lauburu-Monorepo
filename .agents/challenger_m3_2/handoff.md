# Milestone 3 Adversarial Verification & Challenge Report (challenger_m3_2)

**Evaluator**: challenger_m3_2 (Empirical Challenger: Critic / Specialist)  
**Target Device**: Google Pixel 10 Pro XL (`100.73.38.87:8022`, Android 15/17 aarch64)  
**Objective**: Adversarially challenge logging throughput, `svlogd -tt` log rotation, boot script idempotency (`~/.termux/boot/01-mesh-boot.sh`), wake-lock persistence, and resource throttling (`OMP_NUM_THREADS=2`, `nice -n 10`).  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

All data and evidence below were obtained directly through live, zero-mock empirical testing:

### 1.1 Network Reachability & Socket Probing
1. **Tailscale Mesh Ping**:
   - Command: `ping -c 3 100.73.38.87`
   - Output:
     ```
     PING 100.73.38.87 (100.73.38.87): 56 data bytes
     64 bytes from 100.73.38.87: icmp_seq=0 ttl=64 time=1034.225 ms
     64 bytes from 100.73.38.87: icmp_seq=1 ttl=64 time=216.523 ms
     64 bytes from 100.73.38.87: icmp_seq=2 ttl=64 time=211.992 ms
     --- 100.73.38.87 ping statistics ---
     3 packets transmitted, 3 packets received, 0.0% packet loss
     ```
2. **Port Scan across Target Ports on Pixel 10 Pro XL (`100.73.38.87`)**:
   - Python socket scan across ports `[22, 5555, 8022, 31330, 31331, 50051, 50052]`:
     ```
     Port 22: CLOSED (61)
     Port 5555: CLOSED (61)
     Port 8022: CLOSED (61)
     Port 31330: OPEN
     Port 31331: CLOSED (61)
     Port 50051: CLOSED (61)
     Port 50052: OPEN
     ```
   - Direct SSH attempt:
     - Command: `ssh -p 8022 -o StrictHostKeyChecking=no -o ConnectTimeout=5 100.73.38.87 "uname -a"`
     - Output (Exit code 255):
       ```
       ssh: connect to host 100.73.38.87 port 8022: Connection refused
       ```

### 1.2 Automated Pytest Suite Execution
- **Command**:
  `/Users/aaron/.local/bin/uv run --with pytest pytest -v -k "TestTier1Feature5PersistentRunitService or TestTier1Feature6CoexistenceRPC" tests/test_petals_mesh_e2e.py`
- **Output**:
  ```
  tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_01_runit_service_directory_and_run_script FAILED [ 10%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_02_runit_service_active_status FAILED [ 20%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_03_svlogd_logger_and_current_log FAILED [ 30%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_04_guardian_cli_status FAILED [ 40%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_05_boot_script_contains_mesh_services FAILED [ 50%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_01_rpc_server_process_active FAILED [ 60%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_02_rpc_server_port_open PASSED [ 70%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_03_rpc_server_handshake PASSED [ 80%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_04_sshd_service_uninterrupted FAILED [ 90%]
  tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_05_cpu_nice_priority_differential FAILED [100%]

  =================================== FAILURES ===================================
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_01_runit_service_directory_and_run_script
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_02_runit_service_active_status
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_03_svlogd_logger_and_current_log
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_04_guardian_cli_status
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature5PersistentRunitService::test_f5_05_boot_script_contains_mesh_services
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_01_rpc_server_process_active
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_04_sshd_service_uninterrupted
  FAILED tests/test_petals_mesh_e2e.py::TestTier1Feature6CoexistenceRPC::test_f6_05_cpu_nice_priority_differential
  ================== 8 failed, 2 passed, 73 deselected in 2.15s ==================
  ```

### 1.3 Audit of Proposed Scripts (`deploy_m3.py`)
1. **Boot Script (`01-mesh-boot.sh`)**:
   - Lines 48–51:
     ```sh
     if ! pgrep -x sshd >/dev/null 2>&1 && ! pgrep -f "/data/data/com.termux/files/usr/bin/sshd" >/dev/null 2>&1; then
         $PREFIX/bin/sshd 2>/dev/null || true
     fi
     ```
   - Vulnerability: `sshd` is invoked as a loose, un-supervised daemon without integration into `termux-services` (runit) or a permanent foreground notification/wake-lock holder. When Termux background activity pauses or when the terminal session ends, Android OS terminates `sshd`, leading to the `Connection refused` state observed above.
2. **Process Coexistence vs Management**:
   - While `ggml-rpc-server` (port `50052`) and `p2pd` / Petals (port `31330`) remain running in the background, remote administrative ingress (`sshd` port `8022`) has collapsed, preventing `01-mesh-boot.sh` idempotency loops, `svlogd` timestamp verification, and `/proc/<pid>/stat` priority validation from executing over SSH.

---

## 2. Logic Chain

1. **Empirical Status vs. Worker Claims**:
   - `worker_m3_gen2/handoff.md` claimed a 100% pass rate (10/10 passed) on Milestone 3 features with `sshd` actively running under PID 23391.
   - Independent empirical execution of the exact test suite command yielded **8 FAILED, 2 PASSED**, with all SSH-dependent tests failing due to `Connection refused` on port `8022`.
2. **Root Cause Analysis**:
   - On Android 15/17 (Pixel 10 Pro XL), process lifecycle rules aggressively reclaim background processes lacking persistent foreground service registration or wake-lock anchors.
   - The boot script (`01-mesh-boot.sh`) and supervision structure must ensure that `sshd` itself is either supervised under runit (`sv up sshd` via `$PREFIX/var/service/sshd`) or launched with an enduring wake-lock guarantee before interactive sessions disconnect.
3. **Adversarial Assessment**:
   - **Boot Script Idempotency**: Cannot be verified on-device until SSH connectivity is restored.
   - **Log Rotation & Timestamps (`svlogd -tt`)**: Unreachable via SSH.
   - **Resource Throttling (`nice -n 10`, `OMP_NUM_THREADS=2`)**: Unreachable via SSH.
   - **Coexistence**: Partial pass (`ggml-rpc-server` on 50052 and Petals DHT on 31330 are responding to raw TCP sockets, but remote telemetry is unreachable).

---

## 3. Caveats

- Direct TCP socket probes confirm that `ggml-rpc-server` (`50052`) and `p2pd` (`31330`) survived and are operational on `100.73.38.87`.
- Once `sshd` is brought up on the device in Termux, `deploy_m3.py` or the runit `sshd` service can be started to allow remote verification.

---

## 4. Conclusion

- **Verdict**: **`REQUEST_CHANGES`**
- **Action Items for Implementer**:
  1. Restore `sshd` on Google Pixel 10 Pro XL (`100.73.38.87:8022`).
  2. Ensure `sshd` is registered as a supervised runit service (`sv-enable sshd` / `$PREFIX/var/service/sshd`) and guaranteed by `termux-wake-lock` so it does not terminate upon backgrounding.
  3. Re-run deployment and verify all 10 tests in `TestTier1Feature5PersistentRunitService` and `TestTier1Feature6CoexistenceRPC` pass 100%.

---

## 5. Verification Method

1. **Verify SSH Port 8022**:
   ```bash
   ssh -p 8022 -o StrictHostKeyChecking=no -o ConnectTimeout=5 100.73.38.87 "uname -a"
   ```
2. **Verify Live Pytest Suite**:
   ```bash
   /Users/aaron/.local/bin/uv run --with pytest pytest -v -k "TestTier1Feature5PersistentRunitService or TestTier1Feature6CoexistenceRPC" tests/test_petals_mesh_e2e.py
   ```
3. **Verify Boot Script Idempotency (5x run)**:
   ```bash
   ssh -p 8022 100.73.38.87 'for i in $(seq 1 5); do ~/.termux/boot/01-mesh-boot.sh; done && echo "IDEMPOTENCY_PASS"'
   ```
4. **Verify `svlogd -tt` Monotonicity & Log Rotation**:
   ```bash
   ssh -p 8022 100.73.38.87 'tail -n 20 $PREFIX/var/log/sv/petals/current'
   ```
5. **Verify Process Niceness & Environment**:
   ```bash
   ssh -p 8022 100.73.38.87 'ps -o pid,nice,args -C python3,ggml-rpc-server'
   ```
