# Phase 0 Survey & Technical Specification Report — Scope 3
**Author**: explorer_2 (Role: Ecosystem & Verification Explorer)  
**Date**: 2026-08-27  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/.agents/explorer_2`  
**Authoritative Reference**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/router_ai_daemon/ORIGINAL_REQUEST.md`

---

## 1. Executive Summary

This specification document formalizes the architecture, interfaces, and end-to-end verification harness for:
1. **Requirement R6: Autonomous Download & Model Routing**: Secure Hugging Face Hub discovery, authentication, safe streaming acquisition, and zero-downtime atomic model swapping in `llama.cpp` for ultra-compact GGUF models running within the GL.iNet router's strict **$\le 300\text{ MB}$ RAM budget**.
2. **Requirement R7: Decentralized Asset Monetization (Business Swarm)**: Autonomous discovery, structured packaging, cryptographic signing, and transmission of newly synthesized skills, CLIs, MCP servers, SDKs, and surplus mesh compute cycles to the Business AI Swarm marketplace.
3. **E2E Acceptance Criteria & Verification Architecture**: Multi-tiered opaque-box test harness (pytest) covering container compilation, RAM profiling under load, Dual-Core micro-debate consensus resolution, Economic Realignment Penalty (Waste Tax) calculations, and Business Swarm marketplace payload schemas.

---

## 2. Requirement R6: Autonomous Download & Model Routing

### 2.1 Hugging Face Hub Authentication & Credential Isolation

The GL.iNet MT3600BE travel router operates on an ARM64 Cortex-A53 processor with $1.0\text{ GB}$ system RAM and $330\text{ MB}$ SPI NAND writable flash (`/overlay`).

#### 2.1.1 Security & Storage Invariants
- **Zero-Flash-Wear Invariant**: Secrets and tokens must **never** be written to persistent NAND flash (`/overlay` or `/etc/config/`) to eliminate write amplification and premature flash exhaustion.
- **Volatile In-Memory Token Injection**: Tokens are supplied via:
  1. Environment variable `HF_TOKEN` / `HUGGINGFACE_HUB_TOKEN`.
  2. Transient RAM-backed secret mount: `/tmp/secrets/hf_token` (mounted as `tmpfs`, mode `0600`).
  3. Dynamic API injection via secure local loopback IPC (`POST http://127.0.0.1:8080/api/v1/auth/hf_token`).
- **Authorization Header**: All Hugging Face REST requests transmit `Authorization: Bearer <token>`.
- **Public Model Graceful Fallback**: If no token is provided, the agent falls back to unauthenticated public GET requests for unrestricted model repositories.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               HUGGING FACE AUTHENTICATION & DISCOVERY FLOW                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Token Source Check: ENV (HF_TOKEN) -> /tmp/secrets/hf_token -> Anonymous │
│ 2. Discovery API: GET https://huggingface.co/api/models?search=...          │
│ 3. Tree Metadata API: GET https://huggingface.co/api/models/{id}/tree/main  │
│ 4. LFS Header Check: HEAD https://huggingface.co/api/.../resolve/main/{file}│
│    Extracts: Content-Length, X-Linked-Size, X-Linked-ETag (SHA-256)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Model Discovery Engine for Sub-1B Quantized GGUF Models

To adhere strictly to the **$\le 300\text{ MB}$ RAM budget**, the router agent must discover models where the combined resident memory footprint satisfies:

$$\text{RAM}_{\text{total}} = \text{RAM}_{\text{weights}} + \text{RAM}_{\text{kv\_cache}}(\text{context\_len}) + \text{RSS}_{\text{llama\_server}} + \text{RSS}_{\text{daemon}} \le 300.0\text{ MB}$$

#### 2.2.1 Memory Allocation Budget Matrix

| Component | Target Allocation | Notes & Constraints |
| :--- | :--- | :--- |
| **Model Weights (GGUF)** | $60\text{ MB} - 190\text{ MB}$ | Quantization: `IQ2_XXS`, `IQ3_S`, `Q4_K_M` |
| **KV Cache ($2048 - 4096\text{ ctx}$)** | $15\text{ MB} - 35\text{ MB}$ | Quantized KV: `--cache-type-k q4_0 --cache-type-v q4_0` |
| **`llama-server` RSS** | $30\text{ MB} - 45\text{ MB}$ | Statically linked C++ binary (`musl`), zero overhead |
| **Router Daemon RSS** | $15\text{ MB} - 25\text{ MB}$ | Minimal async event loop / POSIX worker |
| **Operating Headroom / Buffer** | $\ge 20\text{ MB}$ | Safety margin against kernel OOM kill |
| **Total Resident Footprint** | **$\le 295.0\text{ MB}$** | **STRICTLY PASSES $< 300.0\text{ MB}$ ACCEPTANCE GATE** |

#### 2.2.2 Qualified Sub-1B Model Candidate Matrix

| Model Identifier | Parameter Count | Quantization | Weight Size | Context | Projected Total RAM | Suitability Tier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SmolLM2-135M-Instruct** | $135\text{M}$ | `Q4_K_M` | $92\text{ MB}$ | $4096$ | $\approx 155\text{ MB}$ | 🟢 **Primary Ultra-Fast** |
| **SmolLM2-135M-Instruct** | $135\text{M}$ | `IQ2_XXS` | $58\text{ MB}$ | $4096$ | $\approx 115\text{ MB}$ | 🟢 **Minimal Footprint** |
| **SmolLM2-360M-Instruct** | $360\text{M}$ | `IQ2_XXS` | $138\text{ MB}$ | $2048$ | $\approx 215\text{ MB}$ | 🟢 **High Reasoning** |
| **SmolLM2-360M-Instruct** | $360\text{M}$ | `Q4_K_M` | $235\text{ MB}$ | $2048$ | $\approx 290\text{ MB}$ | 🟡 **Max Budget Headroom** |
| **Qwen2.5-0.5B-Instruct** | $490\text{M}$ | `IQ2_XXS` | $185\text{ MB}$ | $2048$ | $\approx 265\text{ MB}$ | 🟢 **Code & Tool Use** |
| **Danube3-500M-Chat** | $500\text{M}$ | `IQ2_XXS` | $175\text{ MB}$ | $2048$ | $\approx 255\text{ MB}$ | 🟢 **Conversation** |
| **TinyLlama-1.1B-Chat** | $1.1\text{B}$ | `IQ1_S` | $275\text{ MB}$ | $1024$ | $\approx 335\text{ MB}$ | 🔴 **Exceeds Budget** |

#### 2.2.3 Model Discovery REST Filter Query
```python
# HF Discovery Endpoint Filter
DISCOVERY_URL = "https://huggingface.co/api/models"
PARAMS = {
    "search": "gguf",
    "filter": "text-generation",
    "sort": "downloads",
    "direction": -1,
    "limit": 20
}
# Target filename heuristics: [ "135M", "360M", "0.5B", "500M" ] and [ "Q4_K_M", "IQ2_XXS", "IQ3_S" ]
```

---

### 2.3 Safe Streaming Download Pipeline with Rollback

Because router flash storage is volatile or capacity-limited, downloads must be staged safely:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SAFE MODEL DOWNLOAD STATE MACHINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. PRE-FLIGHT CHECK:                                                        │
│    • Verify mount target: /mnt/usb_storage/models/ or /tmp/models/ (tmpfs)  │
│    • Inode & free space check: statvfs.f_bavail * f_frsize >= size * 1.25   │
│ 2. RESUME-CAPABLE STREAMING DOWNLOAD:                                       │
│    • Stream to staging file: /path/to/{model_name}.download.tmp             │
│    • Chunk size: 64 KB (protects socket buffer from memory bloat)           │
│    • HTTP Header: Range: bytes={offset}- for crash resumption               │
│ 3. CRYPTOGRAPHIC CHECKSUM VERIFICATION:                                     │
│    • Compute streaming SHA-256 hash during download                         │
│    • Compare against Hugging Face LFS OID / ETag                            │
│ 4. ATOMIC COMMIT OR ROLLBACK:                                               │
│    • Success: os.replace(staged_tmp_path, target_gguf_path)                 │
│    • Failure: unlink(staged_tmp_path), retain existing active model         │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.3.1 Download Pipeline Specification
```python
import os
import hashlib
import urllib.request
from pathlib import Path

class SafeModelDownloader:
    def __init__(self, target_dir: Path):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def download_model(self, url: str, filename: str, expected_sha256: str, token: str = None) -> bool:
        target_path = self.target_dir / filename
        temp_path = self.target_dir / f"{filename}.download.tmp"

        # 1. Pre-flight disk space check
        req = urllib.request.Request(url, headers={"User-Agent": "SmolAGI-Router/1.0"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        
        with urllib.request.urlopen(req) as resp:
            content_len = int(resp.headers.get("Content-Length", 0))
            stat = os.statvfs(self.target_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
            if free_bytes < (content_len + 10 * 1024 * 1024):
                raise IOError(f"Insufficient disk space: {free_bytes} bytes free, {content_len} needed")

            # 2. Stream and compute hash
            hasher = hashlib.sha256()
            with open(temp_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)

        # 3. Checksum verification
        calculated_hash = hasher.hexdigest()
        if expected_sha256 and calculated_hash.lower() != expected_sha256.lower():
            temp_path.unlink(missing_ok=True)
            raise ValueError(f"Checksum mismatch: expected {expected_sha256}, got {calculated_hash}")

        # 4. Atomic rename
        temp_path.replace(target_path)
        return True
```

---

### 2.4 Atomic Dynamic Model Swapping in `llama.cpp`

The router must upgrade or downgrade its active model without dropping network connections or returning `502 Bad Gateway` errors.

#### 2.4.1 Two-Tier Zero-Downtime Swap Architecture

```
                                  ┌─────────────────────────────┐
                                  │      Incoming Requests      │
                                  │  http://192.168.8.1:8080/   │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │  Router Ingress Proxy Queue │
                                  └──────────────┬──────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   │                 SWAP TRIGGER (RAM Governor)               │
                   ▼                                                           ▼
      [ Request Queueing State ]                                  [ Process Lifecycle ]
 1. Hold new requests in memory queue                       1. SIGUSR1 / SIGTERM to current server
    (buffer timeout: 5.0 seconds)                           2. Release old model weights from RAM
 2. Flush queue as soon as new model                        3. Exec new llama-server with target GGUF
    passes /health endpoint                                 4. Poll /health until HTTP 200 (sub-500ms)
```

#### 2.4.2 Swap Timing & SLA Guarantees
- **Unload Old Model**: Sub-50ms (memory unmapped via `munmap`).
- **Load New Sub-1B Model**: $250\text{ ms} - 450\text{ ms}$ (direct `mmap` of local GGUF file).
- **Health Verification**: $< 50\text{ ms}$ (`GET http://127.0.0.1:8081/health`).
- **Total Swap Interruption**: **$< 600\text{ ms}$**.
- **Client Perception**: HTTP requests during the swap experience a $\approx 500\text{ ms}$ latency bump, with **0 dropped connections and 0 HTTP 5xx errors**.

---

## 3. Requirement R7: Decentralized Asset Monetization (Business Swarm)

### 3.1 Autonomous Asset Packaging Specification

When the Shadow Swarm discovers an optimized software component, CLI tool, MCP server, SDK, or detects surplus mesh compute (idle NPU/RAM cycles), it packages the asset into a structured, signed JSON payload.

#### 3.1.1 The 5 Canonical Monetizable Asset Classes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MONETIZABLE ASSET CLASSIFICATION                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. code_component : Optimized AST snippets, SIMD kernels, DSP algorithms     │
│ 2. cli_tool       : Standalone compiled binaries, shell/Python utilities    │
│ 3. mcp_server     : Model Context Protocol servers & JSON-RPC tools         │
│ 4. sdk_package    : Polyglot client libraries (Dart, Rust, Kotlin, Python)   │
│ 5. surplus_compute: Tokenized idle NPU / GPU / VRAM time-slices              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Canonical JSON Payload Schema for Marketplace Listing

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LauburuMarketplaceAssetPayload",
  "type": "object",
  "required": [
    "schema_version",
    "asset_id",
    "asset_type",
    "title",
    "description",
    "version",
    "tags",
    "technical_spec",
    "monetization",
    "provenance",
    "payload_manifest",
    "consensus_signature"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "asset_id": {
      "type": "string",
      "pattern": "^urn:lauburu:asset:(code|cli|mcp|sdk|compute):[a-f0-9]{12,64}$"
    },
    "asset_type": {
      "type": "string",
      "enum": ["code_component", "cli_tool", "mcp_server", "sdk_package", "surplus_compute"]
    },
    "title": {
      "type": "string",
      "minLength": 5,
      "maxLength": 120
    },
    "description": {
      "type": "string",
      "minLength": 20,
      "maxLength": 2000
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1
    },
    "technical_spec": {
      "type": "object",
      "required": ["target_architecture", "runtime_environment", "ram_footprint_mb"],
      "properties": {
        "target_architecture": {
          "type": "array",
          "items": { "type": "string", "enum": ["arm64", "x86_64", "mips", "wasm", "agnostic"] }
        },
        "runtime_environment": { "type": "string" },
        "ram_footprint_mb": { "type": "number", "minimum": 0.1 },
        "benchmark_metrics": {
          "type": "object",
          "properties": {
            "speedup_multiplier": { "type": "number" },
            "latency_reduction_pct": { "type": "number" },
            "test_pass_rate_pct": { "type": "number", "minimum": 0.0, "maximum": 100.0 }
          }
        },
        "compute_specs": {
          "type": "object",
          "properties": {
            "node_identifier": { "type": "string" },
            "npu_tops_available": { "type": "number" },
            "vram_headroom_gb": { "type": "number" },
            "max_lease_duration_sec": { "type": "integer" }
          }
        }
      }
    },
    "monetization": {
      "type": "object",
      "required": ["pricing_model", "floor_price_lct", "suggested_price_lct", "currency"],
      "properties": {
        "pricing_model": {
          "type": "string",
          "enum": ["one_time_purchase", "pay_per_execution", "hourly_lease", "subscription_tier"]
        },
        "floor_price_lct": { "type": "number", "minimum": 0.0 },
        "suggested_price_lct": { "type": "number", "minimum": 0.0 },
        "fiat_equivalent_estimate_aud": { "type": "number" },
        "currency": { "type": "string", "enum": ["LCT", "AUD", "USD", "CREDITS"] }
      }
    },
    "provenance": {
      "type": "object",
      "required": ["discovering_agent_id", "timestamp_utc", "verification_run_id", "merkle_state_root"],
      "properties": {
        "discovering_agent_id": { "type": "string" },
        "timestamp_utc": { "type": "string", "format": "date-time" },
        "verification_run_id": { "type": "string" },
        "merkle_state_root": { "type": "string", "pattern": "^[a-f0-9]{64}$" }
      }
    },
    "payload_manifest": {
      "type": "object",
      "required": ["content_encoding", "payload_sha256", "payload_data_or_uri"],
      "properties": {
        "content_encoding": { "type": "string", "enum": ["base64_tar_gz", "raw_text_json", "uri_reference"] },
        "payload_sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
        "payload_data_or_uri": { "type": "string" }
      }
    },
    "consensus_signature": {
      "type": "object",
      "required": ["dual_core_ratified", "smolagi_vote", "genetic_router_vote", "hmac_sha256"],
      "properties": {
        "dual_core_ratified": { "type": "boolean" },
        "smolagi_vote": { "type": "string", "enum": ["RATIFIED", "REJECTED"] },
        "genetic_router_vote": { "type": "string", "enum": ["RATIFIED", "REJECTED"] },
        "hmac_sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" }
      }
    }
  }
}
```

---

### 3.3 Business Swarm Transmission Protocol & Endpoints

The router transmits ratified packages to the Business AI Swarm via multi-tier ingress:

```
                                  ┌─────────────────────────────┐
                                  │   Dual-Core Router Engine   │
                                  │   (Asset Ratified & Signed) │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │  Volatile tmpfs Outbox      │
                                  │  /tmp/business_queue/       │
                                  └──────────────┬──────────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   ▼ (Primary LAN)               ▼ (Overlay / Cloud)           ▼ (Headless Shopify)
    ┌─────────────────────────────┐┌─────────────────────────────┐┌─────────────────────────────┐
    │ Self-Healing Hub Ingress    ││ Cloudflare Worker Edge Ingress││ Shopify Storefront Proxy   │
    │ Host: 100.101.39.98:18802   ││ api.lauburu.mesh/mcp/v2/admin││ Port 4000 App Gateway       │
    │ Endpoint:                   ││ Endpoint:                   ││ Endpoint:                   │
    │ POST /api/v1/marketplace/   ││ POST /mcp/marketplace/inbound││ POST /api/storefront/listing│
    │ publish                     ││                             ││                             │
    └─────────────────────────────┘└─────────────────────────────┘└─────────────────────────────┘
```

#### 3.3.1 Transmission Headers & Handshake
- `Content-Type: application/json`
- `X-Lauburu-Signature: sha256={hmac}`
- `X-Lauburu-Node-ID: GL_INET_ROUTER_GW`
- `X-Lauburu-Consensus-Proof: {merkle_root}`

---

## 4. E2E Acceptance Criteria & Verification Architecture

### 4.1 Acceptance Criteria Traceability Matrix

| ID | Acceptance Criterion | Target Constraint | Empirical Verification Method |
| :--- | :--- | :--- | :--- |
| **AC-1** | Container Build Validation | ARM64 / MIPS target, stripped static binary | Build multi-arch container image with Docker Buildx / LXC; verify binary architecture with `file` / `readelf`. |
| **AC-2** | Total RAM Footprint Budget | Strictly $\le 300.0\text{ MB}$ RSS | Execute load tests; sample `/proc/{pid}/status` and cgroups `memory.current`; assert peak $\text{RSS} \le 300\text{ MB}$. |
| **AC-3** | Disagreement Micro-Debate | Dual-Core disagreement triggers debate | Inject synthetic conflict between `smolagi` and `Genetic Router`; verify debate loop triggers and converges within $\le 3$ rounds. |
| **AC-4** | Waste Tax ELO Penalty | Economic Realignment Penalty applied | Simulate wasted API spend ($Cost > 0$, $Gain = 0$); verify ELO deduction proportional to waste and mesh impact. |
| **AC-5** | Business Swarm Asset Packaging | Valid marketplace JSON generated | Package newly discovered skill/CLI; validate payload against JSON schema and transmit to mock endpoint with HTTP 200. |

---

### 4.2 Mathematical Formalism: Economic Realignment Penalty (The Waste Tax)

When an agent consumes resources (API credits, cloud compute, tool execution tokens), its ELO update is computed as:

$$\Delta \text{ELO} = \Delta \text{ELO}_{\text{performance}} - \text{Penalty}_{\text{waste}}$$

#### 4.2.1 The Waste Penalty Formulation
$$\text{Penalty}_{\text{waste}} = \begin{cases} 
0, & \text{if } \Delta \text{Opt} \ge \text{Threshold} \\
\left( \alpha \cdot \frac{\text{Spend}_{\text{consumed}}}{\text{Spend}_{\text{budget}}} + \beta \cdot \text{MeshImpactFactor} \right) \times (1.0 - \Delta \text{Opt}) \times K_{\text{base}}, & \text{if } \Delta \text{Opt} < \text{Threshold}
\end{cases}$$

Where:
- $\Delta \text{Opt} \in [0.0, 1.0]$: Measured optimization gain (e.g., test pass rate improvement, latency reduction, memory reduction).
- $\text{Spend}_{\text{consumed}} / \text{Spend}_{\text{budget}}$: Fraction of allocated budget burned.
- $\text{MeshImpactFactor} \in [1.0, 5.0]$: Severity weight reflecting mesh congestion or battery/RAM depletion caused by the action.
- $K_{\text{base}} = 100.0$: Scaling constant.
- $\alpha = 1.5, \beta = 0.8$: Governing coefficients.

#### 4.2.2 Test Scenarios & Edge Cases
1. **Zero Gain / Maximum Spend**: $\text{Spend} = 100\%$, $\Delta \text{Opt} = 0.0$, $\text{MeshImpact} = 2.0 \implies \text{Penalty} = (1.5 \times 1.0 + 0.8 \times 2.0) \times 1.0 \times 100 = \mathbf{-310\text{ ELO}}$. (Severely penalized).
2. **High Gain / Modest Spend**: $\text{Spend} = 20\%$, $\Delta \text{Opt} = 0.95 \implies \text{Penalty} = 0$, $\Delta \text{ELO} = \mathbf{+45\text{ ELO}}$.
3. **Zero Spend / Failed Task**: $\text{Spend} = 0 \implies \text{Waste Tax} = 0$, standard task-level ELO delta applies.

---

### 4.3 Dual-Core Consensus & Micro-Debate Simulation Logic

```python
class DualCoreRouterEngine:
    def __init__(self, smolagi_core, genetic_core, max_debate_rounds=3):
        self.smolagi = smolagi_core
        self.genetic = genetic_core
        self.max_debate_rounds = max_debate_rounds

    def evaluate_routing_decision(self, routing_request: dict) -> dict:
        # Phase 1: Independent evaluations
        decision_a = self.smolagi.propose_route(routing_request)
        decision_b = self.genetic.propose_route(routing_request)

        # Check for immediate consensus
        if decision_a["target"] == decision_b["target"] and decision_a["action"] == decision_b["action"]:
            return {
                "status": "IMMEDIATE_CONSENSUS",
                "consensus_decision": decision_a,
                "debate_triggered": False,
                "rounds": 0
            }

        # Phase 2: Micro-debate trigger
        debate_history = []
        for r in range(1, self.max_debate_rounds + 1):
            rebuttal_a = self.smolagi.rebut(decision_b, debate_history)
            rebuttal_b = self.genetic.rebut(decision_a, debate_history)
            debate_history.append({"round": r, "a": rebuttal_a, "b": rebuttal_b})

            # Check if synthetic compromise / consensus reached
            if rebuttal_a.get("conceded") or rebuttal_b.get("conceded") or rebuttal_a.get("compromise_target") == rebuttal_b.get("compromise_target"):
                final_target = rebuttal_a.get("compromise_target") or (decision_a["target"] if rebuttal_b.get("conceded") else decision_b["target"])
                return {
                    "status": "DEBATE_CONSENSUS_REACHED",
                    "consensus_decision": {"target": final_target, "action": "ROUTED_AFTER_DEBATE"},
                    "debate_triggered": True,
                    "rounds": r,
                    "debate_transcript": debate_history
                }

        # Fallback to deterministic conservative route if debate deadlocks
        return {
            "status": "FALLBACK_SAFETY_DEFAULT",
            "consensus_decision": {"target": "TIER1_SAFE_LOCAL_SHARD", "action": "FAILSAFE_ROUTE"},
            "debate_triggered": True,
            "rounds": self.max_debate_rounds,
            "debate_transcript": debate_history
        }
```

---

## 5. Test Suite Architecture Design (Pytest Specification)

The test suite will be structured as follows:

```
00_core_infrastructure/router_ai_daemon/tests/
├── conftest.py                       # Shared test fixtures, mock servers, tmpfs allocators
├── test_container_build.py           # AC-1: Container multi-arch manifest & binary tests
├── test_ram_footprint.py             # AC-2: RAM sampling & 300MB budget enforcement tests
├── test_dual_core_micro_debate.py    # AC-3: Disagreement injection & consensus convergence tests
├── test_waste_tax_elo.py             # AC-4: Economic Realignment Penalty mathematical tests
├── test_hf_model_router.py           # R6: HF discovery, safe download & model swap tests
├── test_business_marketplace.py      # R7 & AC-5: Asset packaging, JSON schema & transmit tests
└── test_e2e_integration.py           # Full end-to-end integration lifecycle test
```

### 5.1 Test Modules and Invariants

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TEST HARNESS INVARIANT MATRIX                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. test_container_build.py:                                                 │
│    • Invariant: Executable elf header matches ARM64/x86_64 target.          │
│    • Invariant: Image stripped of dev dependencies (< 80MB image size).     │
│ 2. test_ram_footprint.py:                                                   │
│    • Invariant: max(RSS) <= 300.0 MB during 100 concurrent token inferences.│
│    • Invariant: tmpfs ring buffer <= 16.0 MB.                               │
│ 3. test_dual_core_micro_debate.py:                                          │
│    • Invariant: Injected disagreement MUST trigger debate_triggered=True.   │
│    • Invariant: Agreement MUST reach consensus in <= 3 turns with 0 deadlock│
│ 4. test_waste_tax_elo.py:                                                   │
│    • Invariant: Spend > 0 with Gain = 0 yields Delta ELO <= -150.           │
│    • Invariant: Zero mock compliance (rejects fabricated test reports).     │
│ 5. test_hf_model_router.py:                                                 │
│    • Invariant: Atomic rename ensures corrupted download never activates.  │
│    • Invariant: Swap latency pause <= 600ms, 0x 5xx HTTP response codes.    │
│ 6. test_business_marketplace.py:                                            │
│    • Invariant: 100% JSON Schema compliance on all 5 asset classes.          │
│    • Invariant: HMAC signature verifies over payload body.                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Monorepo Integration Audit Findings

1. **Business AI Swarm Endpoints**:
   - `00_core_infrastructure/self_healing_hub/src/api_server.py`: Port 18802 provides `/api/business_ai/status`, `/api/game_arena/purchase_perk`, `/api/roi_improvements`.
   - `08_business_and_commerce/` & `spec-08-business-commerce`: Governs Shopify Storefront GraphQL, membership tiers, and merchandise margin optimization.
2. **Hugging Face Hub Integration**:
   - `00_core_infrastructure/self_healing_hub/src/genetic_smol_moe_swarm.py`: Line 175 uses `unsloth/SmolLM2-360M-Instruct-GGUF` and `SmolLM2-360M-Instruct-Q4_K_M.gguf` under a $45\text{MB}$ C-runtime footprint.
   - `00_core_infrastructure/self_healing_hub/src/api_server.py`: Line 1856 defines `download_model_hf_cli` for dynamic model injection.
3. **Dual-Core & ELO Engines**:
   - `00_core_infrastructure/self_healing_hub/src/bidirectional_elo_calibrator.py`: Implements size efficiency multiplier $\eta_{\text{size}} = \log_2(71.0)/\log_2(\text{params\_b} + 1.0)$ and hardware compute multiplier.
   - `05_agents_and_swarms/red_blue_arena/tests/test_hardening_invariants.py`: Standardizes 5-tier E2E verification test patterns.
4. **Hardware Topology & Zero-Flash-Wear**:
   - `07_docs_and_architecture/ROUTER_ORCHESTRATOR_CONSENSUS.md`: Ratified Tier-0 GL.iNet MT3600BE Gateway architecture, $16\text{MB}$ volatile `tmpfs` ring buffer, and $0$-byte persistent flash write invariant.
