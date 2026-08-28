# Progress — Worker M1 & M2 (Native SeaweedFS & TB4 Ingress)

- **Status**: Complete
- **Last visited**: 2026-08-23T22:24:00+10:00

## Completed Tasks
1. [x] Audit and install signed ARM64 `weed` binary via Homebrew (`/Users/aaron/.local/opt/seaweedfs/bin/weed` / `/Users/aaron/.local/bin/weed`).
2. [x] Create NVMe storage directories (`/Users/aaron/.local/var/seaweedfs/` on APFS container `/dev/disk3s5`).
3. [x] Author, lint, and install LaunchAgent plist (`~/Library/LaunchAgents/ai.lauburu.seaweedfs.plist`).
4. [x] Bootstrap service via launchd (`launchctl bootstrap gui/501 ...`).
5. [x] Verify Master, Volume, Filer, and S3 HTTP and gRPC endpoints on Thunderbolt 4 interface (`169.254.80.69`).
6. [x] Verify file upload and download via Filer HTTP API with SHA256 parity and NVMe volume chunk verification.
7. [x] Complete 64MB throughput and cryptographic integrity benchmark.
