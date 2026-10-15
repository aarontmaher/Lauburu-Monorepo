
## Architectural FAQs
* **Engine Type:** This CLI does not use basic RAG. It routes explicitly to the **Genetic MoE Swarm**, utilizing 3 parallel 7B/8B parameter models (~23B active parameters total) to synthesize medical and reasoning contexts concurrently.
* **Network Setup:** It relies on an absolute IP-less Layer 0 foundation (BLE GATT 0x180D) for biometrics. The model mesh relies strictly on Tailscale (Kernel-mode on Host, Userspace on Android) combined with `prima.cpp` Pipelined-Ring Parallelism to shard memory across devices.
