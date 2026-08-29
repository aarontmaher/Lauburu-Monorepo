# Original User Request

## Initial Request — 2026-08-29T06:34:00Z

Deploy, test, and continuously benchmark real multi-transport data routing (Thunderbolt 4 DMA, Custom WireGuard Mesh, Speedify Multi-WAN Channel Bonding, Local LAN) across the 7-node physical mesh with empirical statistical confidence algorithms, chaos latency injection, and a dedicated Qwen Math Algorithm Specialist AI.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo
Integrity mode: development

## Requirements

### R1. Custom WireGuard & Speedify Multipath Integration
- Configure and test real userspace/kernel WireGuard and 44-byte SPDF packet-striping Speedify multi-WAN bonding across physical network interfaces (`en0`, `bridge0`, `utunX`).
- Establish zero-mock data pipelines with sub-millisecond MTU 9000 jumbo frames over Thunderbolt 4 and authenticated WireGuard endpoints.

### R2. Continuous Multi-Device Server Rotation & Combinations Matrix
- Execute automated server rotation across the 7 physical nodes (Mac Mini Host, MacBook Pro M1 Max, Linux Head Node AMD 5700U, Android Termux / Pixel 10 Pro).
- Continuously compute Student-t / Gaussian 95% Confidence Intervals ($\bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$) until Margin of Error $< 3.0\%$.
- Inject progressive chaos network degradation (Mild $+25\text{ms}$, Heavy Jitter $+85\text{ms} \pm 15\text{ms}$, Severed Link $+350\text{ms}$) and evaluate real-time multi-path failover across transport combinations.

### R3. Qwen Math Algorithm Specialist AI & Continuous Training Protocol
- Host standard and abliterated Qwen Math local models on Port `:8086` to analyze real-time transport matrices, optimize packet striping weights, and discover high-speed network topologies.
- Format all debate verdicts, packet telemetry, and benchmark records into continuous 24/7 LoRA training datasets in `04_data_and_memory` and synchronize to Obsidian Vault.

## Acceptance Criteria

### Real Socket & Transport Verification (Rule #0 Compliance)
- [ ] Every transport probe connects to real physical sockets (`bridge0`, `utunX`, `en0`, `lo0`) with zero simulated data.
- [ ] Speedify bonding engine successfully packs, stripes, and reassembles 36/44-byte binary frames with CRC32 integrity checks across multi-path subflows.

### Statistical Confidence & Chaos Recovery
- [ ] Benchmarking daemon gathers $\ge 30$ continuous samples per link and reports 95% Confidence Intervals.
- [ ] Chaos fault injection automatically verifies sub-second failover from degraded links to backup transports without dropping active TUI sessions.

### Model Serving & Proxy Integration
- [ ] `Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf` serves on Port `:8086` and responds to mathematical/algorithmic optimization queries.
- [ ] Unified AI Proxy (`:8080`) includes `:8086` in its cascade routing matrix.
