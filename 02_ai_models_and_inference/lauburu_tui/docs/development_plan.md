# Lauburu Mesh TUI — Development Plan

## 1. Vision
`lauburu-tui` is a native Rust terminal interface (using Ratatui) that serves as the zero-dependency control plane for the Lauburu heterogeneous hardware mesh.

## 2. Hybrid Architecture (PRP + RPC Fallback)
The defining feature of this orchestrator is its awareness of **storage constraints**. 
* **prima.cpp PRP (Pipelined Ring Parallelism):** Requires the full `.gguf` model file on *every* node to overlap disk `mmap` with network transfer (`--prefetch`).
* **llama.cpp RPC (Legacy):** Requires the model file *only* on the master node; workers receive tensors in-memory.

**The Orchestrator Logic:**
When a model is requested (e.g., `DeepSeek-R1-32B`):
1. The TUI checks available disk space on all mesh nodes.
2. If a node (e.g., MacBook Air) lacks the 37GB needed, the TUI dynamically drops it from the `prima.cpp` ring and spins up a `llama-server --port 50052` RPC listener on that node instead.
3. The master node routes layers to the Air via RPC, while maintaining the PRP ring with the Linux and MBP nodes.

## 3. Implementation Roadmap
- **Phase 1:** Core Rust scaffolding, `mesh.toml` parsing, and basic SSH execution commands.
- **Phase 2:** `rsync` integration to automatically distribute models (Option B) to nodes with sufficient storage.
- **Phase 3:** Ratatui UI components (Topology visualizer, embedded chat stream).
- **Phase 4:** KwaaiNet (rust-libp2p) integration for raw internet peer discovery (replacing/augmenting Tailscale).

## 4. Node Targets
- macOS (arm64, x86_64)
- Linux (x86_64 Head Node)
- Android / Termux (cross-compiled aarch64)
