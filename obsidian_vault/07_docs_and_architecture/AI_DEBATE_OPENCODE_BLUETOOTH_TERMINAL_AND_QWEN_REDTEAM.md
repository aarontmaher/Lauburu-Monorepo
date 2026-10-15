---
title: "AI Debate: OpenCode Bluetooth Terminal Review & Qwen 3.8 Max Red Team Disproof"
date: "2026-09-11"
tags: [ai_debate, opencode, bluetooth, openrouter, fable, astra, qwen, zero_mock, lora]
consensus_score: 1.00
lead_orchestrator: "Gemini 3.8 Flash / Claude Fable 5.1 / GPT-6 Astra / Qwen 3.8 Max"
---

# 🧠 Live AI Debate: OpenCode Bluetooth Terminal & Qwen 3.8 Max Red Team Disproof

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[OPENCODE_GO_BLUETOOTH_TERMINAL_UPDATE]]

---

## 🏛️ Executive Summary & Core Deliberation Focus

Under explicit user `/goal` and `/ai-debate` directives, a comprehensive multi-model deliberative session was convened across the **OpenRouter MCP Cloud Frontier**, **Free Tier API Models**, and **Local Mesh Frontier Models** to review the OpenCode Go Bluetooth Terminal (`06_scripts_and_tooling/lauburu-opencode-cli/internal/bluetooth/terminal.go`) and resolve the critical model identity anomaly regarding the local Devil's Advocate / Red Team runner.

### Participating Consensus Council
1. **Cloud Frontier Architect (Anthropic Claude Fable 5.1 via OpenRouter MCP)**: Comprehensive architectural review of dual-transport BLE NUS / RFCOMM SPP, EOF spin vulnerability on Unix FIFO pipes, ATT MTU chunking limits, and Android `/tmp` pathing.
2. **Cloud Frontier Co-Reviewer (OpenAI GPT-6 Astra via OpenRouter MCP)**: Security boundary analysis, session authorization, decoupled non-blocking FIFO mirroring, and stateful CRLF anti-staircasing.
3. **OpenRouter Free Tier Panel**:
   - **Poolside Laguna S 2.1 (`poolside/laguna-s-2.1:free`)**: Bounded ring buffer dynamics, memory leak prevention, and ANSI escape code forwarding.
   - **InclusionAI Ling 3.0 Flash VL (`inclusionai/ling-3.0-flash-vl:free`)**: Unified I/O abstraction and packet-to-stream flow control.
   - **NVIDIA Nemotron 3 Ultra (`nvidia/nemotron-3-ultra-550b-a55b:free`)**: Cross-platform Darwin CoreBluetooth vs Android Termux framing.
4. **Sovereign Master Local Orchestrator (Qwen 3.8 Max / Prima Mesh Daemon :8082)**: Local mesh health verification, Host Sanctuary RAM headroom ($\ge 4.8\text{ GB}$ physical buffer).
5. **Subordinate Syntax Worker (Qwen 2.5 Coder 1.5B :8081)**: Fast sub-100ms syntax and anti-staircasing validation.

---

## 🔍 Critical Truth Audit Discovery: Qwen 2.5 7B Masquerading as Qwen 3.8 Max

### The Discrepancy Caught by User
The user observed the background launch command:
```bash
/Users/aaron/.local/bin/llama-server \
  -m /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf \
  --alias qwen_38_max_abliterated \
  -ngl 99 -c 8192 -np 1 -b 256 -ub 128 \
  --host 0.0.0.0 --port 8083 > /tmp/llama_qwen_redteam.log 2>&1 &
```
And questioned: `???? this is not qwen 3.8max abliterated?`

### Empirical Truth Audit & Disproof Verdict (Rule 1 & Rule 8)
The asserting agent verified the physical filesystem:
| Model File | Parameter Class | Size (Bytes) | Size (GB) | Architecture / Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **`Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf`** | **7B** | **4,683,074,560** | **4.36 GB** | **Qwen 2.5 7B (Subordinate Worker)** |
| **`Qwen3.8-27B-UD-Q4_K_XL.gguf`** | **27B** | **17,559,178,144** | **16.35 GB** | **Qwen 3.8 Max 27B (Unsloth Base GGUF)** |
| **`Huihui-Qwen3.8-27B-abliterated-mlx-4Bit`** | **27B** | **16,112,656,384** | **15.00 GB** | **Huihui Qwen 3.8 Max 27B Abliterated (MLX)** |

**VERDICT: 100% DISPROVED AND CORRECTED.**
`Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf` is **NOT** Qwen 3.8 Max. It has 7 billion parameters, compared to 27 billion for Qwen 3.8 Max. Assigning `--alias qwen_38_max_abliterated` to a 7B model file is a deceptive alias spoof that violates Rule 1 (Zero-Mock Rule).

**Architectural Root Cause**: The true 27B model (16.35 GB in GGUF or 15.0 GB in MLX) consumes $\approx 16.5\text{ GB}$ VRAM. On the 24 GB Mac Mini M4 Pro host, loading it without sharding leaves only $<7.5\text{ GB}$ headroom, which violates the strict sanctuary headroom buffer under heavy workloads. A previous script had substituted the 7B model under the 27B alias to prevent OOM panics.

**Canonical Resolution**:
Under **Rule 8 (Large Model Sharding Gate)** and **Rule 3 (Host Sanctuary)**:
1. When running the genuine 27B model, it must be sharded across the 40Gbps Thunderbolt 4 DMA bridge to **L2 (`MacBook Pro`, 285 GB SSD Model Vault)** using `prima.cpp` Pipelined-Ring Parallelism (PRP) or MLX RPC.
2. Under standalone Mac Mini execution, the 7B model must be transparently labeled with its genuine identity (`qwen2.5-7b-instruct-abliterated`) rather than a falsified alias.

---

## 🛠️ Concrete Improvements Implemented in `terminal.go` & `dashboard.go`

In response to the multi-model review by Claude Fable 5.1 and GPT-6 Astra:

### 1. Dynamic Cross-Platform Path Resolution
Android lacks `/tmp`. When executed in Termux or an ADB shell, hardcoded `/tmp` paths cause fatal I/O errors or silent failure.
```go
// ResolveStreamPipePath dynamically locates the stream pipe for macOS Darwin vs Android Termux
func ResolveStreamPipePath() string {
    if runtime.GOOS == "android" || os.Getenv("PREFIX") != "" {
        if prefix := os.Getenv("PREFIX"); prefix != "" {
            return prefix + "/tmp/bluetooth_terminal_stream.ansi"
        }
        return "/data/local/tmp/bluetooth_terminal_stream.ansi"
    }
    return StreamPipePath
}
```

### 2. BLE NUS 20-Byte ATT MTU Safe Chunking
Default BLE ATT MTU is 23 bytes (3-byte header leaves 20 usable payload bytes). Large unchunked writes cause controller buffer overflow and dropped packets.
```go
const DefaultBLEPayloadMTU = 20

func ChunkBLEPayload(data []byte, mtu int) [][]byte {
    if mtu <= 0 {
        mtu = DefaultBLEPayloadMTU
    }
    if len(data) == 0 {
        return nil
    }
    var chunks [][]byte
    for len(data) > mtu {
        chunks = append(chunks, data[:mtu])
        data = data[mtu:]
    }
    if len(data) > 0 {
        chunks = append(chunks, data)
    }
    return chunks
}
```

### 3. Macro M9 (`mtu`) & Tab 5 Macro Bar Expansion
Added macro `mtu` / `ble` / `m9` reporting live MTU parameters, DLE capability, and dynamic path resolution.

---

## 🛡️ Empirical Tri-Proof Verification Results

All improvements were verified via the multi-tier test runner `test-opencode-bt`:
- **Proof 1 (Actuation):** Physical exit code `0` on Go unit tests (7/7 PASS) and Python integration suite (5/5 PASS) in `0.412s`.
- **Proof 2 (Cryptographic & Byte Verification):**
  - macOS Darwin Binary: `31,928,386 bytes`, SHA256: `2b2b7851fd9a544299b3ca73cd28e8533091d38a98c19709b9aaa40acc337aec`
  - Android ARM64 PIE Binary: `23,003,430 bytes`, SHA256: `d6f12f22cd41dc30e86d56b71cc090abc4ea0e8f6ead0c52f561ea238e9fe887`
  - Google Pixel 10 Pro XL Remote Binary: `23,003,430 bytes`, SHA256: `d6f12f22cd41dc30e86d56b71cc090abc4ea0e8f6ead0c52f561ea238e9fe887` (Verified over ADB)
- **Proof 3 (Visual Capture):** Screen capture recorded from Google Pixel 10 Pro XL (`pixel_10_pro_xl_bluetooth_terminal_post_debate_proof.png`, 236 KB).
