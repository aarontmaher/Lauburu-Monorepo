Based on your L1 (M4 Mac Mini, TB4) → L2 (Intel MBP, TB4 bridge) → L3 (AMD Ryzen, 1GbE) topology:

---

## SeaweedFS IOPS Tuning: TB4 Bridge + 1GbE Hybrid

### 1. `weed volume` — Tune Concurrent Writes via `-concurrentUploadLimitMB` + OS-level `mmap` pinning

**For L1/L2 (TB4 nodes):**
```bash
weed volume \
  -dir=/data/seaweedfs \
  -max=256 \
  -concurrentUploadLimitMB=512 \
  -dataCenter=dc1 -rack=tb4_ring \
  -readBufferSizeMB=64
```

**Why:** TB4's 40Gbps DMA bridge (~4.8 GB/s sustained) saturates with default 8MB upload caps. Setting `-concurrentUploadLimitMB=512` + `-readBufferSizeMB=64` aligns read buffers to Apple Unified Memory page boundaries (16KB), reducing mmap remapping overhead. Pair with:
```bash
sudo sysctl kern.maxvnodes=750000  # macOS — prevents vnode exhaustion under high file-handle churn
```

---

### 2. `weed master` — Raft heartbeat + lease tuning for cross-transport latency asymmetry

Your topology has a **latency asymmetry problem**: TB4 RTT ≈ 0.27ms vs 1GbE to L3 ≈ 1-3ms. Default Raft timeouts cause spurious re-elections.

```bash
weed master \
  -raftHashicorp=true \
  -heartbeatInterval=500ms \
  -electionTimeout=5000ms \
  -volumeSizeLimitMB=30000 \
  -defaultReplication=001
```

**Why:**
- `-raftHashicorp=true` uses the HashiCorp Raft implementation (more stable under mixed-latency clusters than the legacy impl)
- `heartbeatInterval=500ms` / `electionTimeout=5000ms` → 10:1 ratio prevents L3's 1GbE jitter from triggering leader flaps
- `-volumeSizeLimitMB=30000` (30GB per volume) reduces needle-map reload frequency, cutting IOPS spikes during volume sealing

---

### 3. `weed volume` — Direct I/O + index memory map for NVMe on L1/L2

```bash
weed volume \
  -dir=/data/seaweedfs \
  -index=leveldb \
  -diskType=ssd \
  -compactionMBps=400
```

**Why:**
- `-index=leveldb` replaces the default flat-file needle index with LevelDB's LSM tree — critical for your 3,100+ file AST crawl workload; reduces random-read amplification from O(n) scan to O(log n)
- `-diskType=ssd` enables SeaweedFS's internal SSD-aware write batching (coalesces small writes into 8MB sequential bursts, matching NVMe optimal transfer unit)
- `-compactionMBps=400` caps background compaction at 400 MB/s on the TB4 path — enough headroom to avoid starving foreground IOPS while the L2 MBP's 285GB SSD vault compacts large volumes

---

### Bonus: Android S3 client tuning (L4-L7)

For your Termux S3 clients writing over Tailscale:
```bash
# In your S3 client config (e.g. rclone or custom):
--s3-upload-concurrency=4
--s3-chunk-size=16M
--s3-disable-checksum=true   # saves CPU on Tensor G5/Exynos under Doze
```

The `--s3-disable-checksum` flag is safe here since Tailscale provides transport-layer integrity (WireGuard AEAD) — eliminates redundant SHA256 per-chunk on Android CPUs.
