
## Active Priorities (Injected by Live Debate)

- [Target Qwen 27B/7B for LoRA] Avoid 88B OOM panics and optimize for native MPS gradient descent.

## Active Priorities (Injected by Live Debate)
- [Dual Qwen Topology] Deploy Qwen 3.8 27B (Normal) and Qwen 3.8 27B (Abliterated) in isolated Docker containers.
- [Edge Qwen Pairing] Pair both Hub containers with dedicated Edge Qwen models (e.g., 7B/0.5B) on the Android/Tablet nodes for localized inference and LoRA telemetry harvesting.

## Active Priorities (Injected by Live Debate)
- [Smolagents Edge Roster] Implement a Hybrid 'Zero-Resident 7B' policy for Android nodes. Qwen 2.5 0.5B stays loaded 24/7 as the background router (<600MB RAM). Qwen 2.5 7B (Coder/VL) is treated as a transient worker, loaded only on-demand by the 0.5B model to evade the Android OOM killer, then immediately dumped.

## Active Priorities (Injected by Live Debate)
- [Qwen3.8 Benchmark & Training Games] Execute Red/Blue Tournament and Software Dev Game against Qwen3.8-Flash-Next on Port 8081 with lock-synchronized state transitions and AST-validated DPO pair logging.
