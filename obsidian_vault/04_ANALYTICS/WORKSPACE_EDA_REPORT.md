# Exploratory Data Analysis (EDA) Report — Lauburu Workspace & `gbos-vm` Build

- **Generated Timestamp (UTC):** `2026-10-14T11:03:33Z`
- **Workspace Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test`
- **Obsidian Mirror:** `[[04_ANALYTICS/WORKSPACE_EDA_REPORT]]` (`[[Index]]`)
- **Compliance Mandate:** Rule #0 / Rule #1 Zero-Mock Empirical Verification (100% live filesystem & dataset telemetry)

---

## 1. Executive Summary & Corpus Overview

| Dataset / Source | File Size (Bytes) | File SHA256 Checksum | Total Trajectories | Valid JSON | 64-Char SHA256 Present | Zero-Mock Verified / Tagged |
|:--|:--|--:|:--|--:|--:|--:|
| `continuous_lora_dataset.jsonl` | **139,690,421** | `99cb619c8d80a761f105a9a26259d510887078c1fcc7459a64aca011929679b8` | **88,845** | 88,845 | 7,470 (8.41%) | 35,964 (40.48%) |
| `frontier_consensus_dataset.jsonl` | **4,475,099** | `eca30b5003d921663bb13fea056d8f8a7ed8aa473ae49a9878ed3b6e0b927232` | **4,800** | 4,800 | 871 (18.15%) | 887 (18.48%) |
| **Combined Corpus Total** | **144,165,520** | *Dual-File Aggregate* | **93,645** | **93,645** | **8,341 (8.91%)** | **36,851 (39.35%)** |

### Key Analytical Takeaways
1. **Total Empirical Trajectories:** **93,645** JSONL records across `continuous_lora_dataset.jsonl` (88,845 records, 133.22 MB) and `frontier_consensus_dataset.jsonl` (4,800 records, 4.27 MB).
2. **Cryptographic Provenance Rate:**
   - Across `continuous_lora_dataset.jsonl`, **7,470** records (**8.41%**) embed 64-character hexadecimal SHA256 digests (`sha256` / `document_sha256` / inline Tri-Proof hashes), with **5,949** (**6.70%**) carrying dedicated top-level or metadata `sha256` fields.
   - Across `frontier_consensus_dataset.jsonl`, **871** records (**18.15%**) embed 64-character SHA256 digests (`sha256` / `document_sha256`), and **100%** of the recent v4 consensus synthesis entries include cryptographic proof hashes.
3. **Byte & Token Length Distributions:**
   - Combined mean record size is **1,538.49 bytes** (median **1,441.00 B**, p95 **1,889.00 B**, max **899,900 B**).
   - Combined estimated token length per trajectory has a mean of **233.29 tokens** (median **257.00**, min **10**, p95 **300.00**, max **9,196 tokens**), totaling **21,846,869 tokens** (~21.85M tokens).

---

## 2. Byte & Token Length Distributions

| Metric | Raw Record Bytes (`continuous`) | Raw Record Bytes (`frontier`) | Raw Record Bytes (`Combined`) | Est. Tokens (`continuous`) | Est. Tokens (`frontier`) | Est. Tokens (`Combined`) |
|:--|--:|--:|--:|--:|--:|--:|
| **Count (N)** | 88,845 | 4,800 | **93,645** | 88,845 | 4,800 | **93,645** |
| **Mean** | 1,571.29 | 931.31 | **1,538.49** | 239.21 | 123.83 | **233.29** |
| **Median (p50)** | 1,444.00 | 529.00 | **1,441.00** | 257.00 | 96.00 | **257.00** |
| **Min** | 223 | 299 | **223** | 15 | 10 | **10** |
| **p95** | 1,892.00 | 1,441.00 | **1,889.00** | 300.00 | 288.00 | **300.00** |
| **p99** | 4,343.00 | 3,207.00 | **4,311.80** | 319.00 | 295.00 | **319.00** |
| **Max** | 899,900 | 21,463 | **899,900** | 9,196 | 973 | **9,196** |
| **Total Sum** | 139,601,576 | 4,470,299 | **144,071,875** | 21,252,505 | 594,364 | **21,846,869** |

---

## 3. Domain & Category Breakdown (Top 15 Domains)

| Rank | Domain / Category Identifier | `continuous_lora` | `frontier_consensus` | Combined Count | Share (%) |
|--:|:--|--:|--:|--:|--:|
| 1 | `zero_mock_and_functionality` | 24,207 | 0 | **24,207** | 25.85% |
| 2 | `ui_ux_and_sellability` | 24,206 | 0 | **24,206** | 25.85% |
| 3 | `lens_ctf_cybergym` | 11,759 | 0 | **11,759** | 12.56% |
| 4 | `unclassified_general` | 8,843 | 829 | **9,672** | 10.33% |
| 5 | `autonomous_tool_self_optimizer` | 4,811 | 0 | **4,811** | 5.14% |
| 6 | `frontier_swarm_consensus` | 800 | 3,918 | **4,718** | 5.04% |
| 7 | `stitch_2.0_ui_optimizer` | 2,778 | 0 | **2,778** | 2.97% |
| 8 | `ai_debate_consensus` | 2,322 | 0 | **2,322** | 2.48% |
| 9 | `tb4_40gbps_hardware_telemetry` | 2,318 | 0 | **2,318** | 2.48% |
| 10 | `prod_testing_sovereign_console` | 1,030 | 0 | **1,030** | 1.10% |
| 11 | `1b_context_loop` | 962 | 0 | **962** | 1.03% |
| 12 | `prod_adversarial_sovereign_console` | 553 | 0 | **553** | 0.59% |
| 13 | `stress_test_locking` | 505 | 0 | **505** | 0.54% |
| 14 | `prod_edge_keepalive_sovereign_console` | 449 | 0 | **449** | 0.48% |
| 15 | `00_core_infrastructure` | 265 | 0 | **265** | 0.28% |

---

## 4. Model ELO vs. Token Cost Efficiency (`$ / 1M Tokens`)

Highlighting **Gemini 4 Argon (High)** at **$0.075 / 1M tokens** (verified `1.0x` Argon-to-Flash token parity via `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/argon_swarm_telemetry_state.json`) alongside **$0.00 / 1M Local Sovereign** endpoints (`L1` Mac Mini M4 Pro & `L8` Ubuntu Thunderbolt 4 Hub) and Free-Tier Cloud endpoints:

| Model Identifier | Tournament ELO | Cost / 1M Tokens (USD) | Governance Tier | Mesh Layer / Endpoint | Avg TPS | Empirical Notes |
|:--|--:|--:|:--|:--|--:|:--|
| `Gemini 4 Argon (High)` | **1525.0** | **$0.075** | `Cloud Flash-Parity Frontier (1.0x Ratio)` | `AGY Cloud / G1 Credits` | 142.0 | 1.0x Flash Token Parity ($0.075/1M input); Multi-Tier ELO 2614.0 |
| `Gemini 3.8 Flash (High)` | **1510.0** | **$0.075** | `Cloud Flash Reference` | `Google AI Studio / Vertex` | 155.0 | Baseline Flash pricing reference ($0.075/1M input) |
| `meta/llama-3.2-11b-vision-instruct` | **1457.8** | **$0.000** | `Cloud Free-Tier ($0/1M Quota)` | `Cloud (NVIDIA NIM)` | 41.4 | Cloud Frontier Vision | Factual Acc: 83.3% |
| `qwen/qwen3.8-27b` | **1397.8** | **$0.000** | `Cloud Free-Tier ($0/1M Quota)` | `Cloud (Groq)` | 497.5 | Cloud Fast LPU | Factual Acc: 50.0% |
| `qwen2.5-0.5b-instruct-q4_k_m.gguf` | **1372.7** | **$0.000** | `Local Sovereign ($0/1M)` | `L1 (mac-mini-m4:8089)` | 84.1 | Edge AI (0.5B) | Factual Acc: 100.0% |
| `Huihui-Qwen3.8-27B-abliterated` | **1345.7** | **$0.000** | `Local Sovereign ($0/1M)` | `L8 (Ubuntu-TB4:8083)` | 1.4 | Sovereign Swarm (>8B) | Factual Acc: 50.0% |
| `smollm2-135m-instruct-q4_k_m.gguf` | **1140.1** | **$0.000** | `Local Sovereign ($0/1M)` | `L8 (Ubuntu:9096)` | 102.6 | MiniLM (>20M) | Factual Acc: 33.3% |
| `TinyStories-LLaMA2-20M-256h-4l-GQA.Q4_K_M.gguf` | **965.9** | **$0.000** | `Local Sovereign ($0/1M)` | `L8 (Ubuntu:9095)` | 577.0 | TinyLM (<=20M) | Factual Acc: 0.0% |
| `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` | **1385.0** | **$0.000** | `Local Sovereign ($0/1M)` | `L1 (mac-mini-m4:8090 / :8082)` | 46.2 | Active local Metal orchestrator runtime on :8090 (proxied by :8082) |
| `Frontier Pro Reference (Standard Cloud API)` | **1530.0** | **$1.250** | `Paid Cloud Frontier` | `Upstream Paid Cloud API` | 65.0 | 16.7x more expensive than Gemini 4 Argon ($1.25 vs $0.075/1M) |

---

## 5. `gbos-vm` Built Guest & Host Tool Artifacts (6 Canonical Targets)

All 6 required build outputs defined in `test_build_podman.sh` inside `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test/gbos-vm/work/` are physically verified on disk (`Total Canonical Size = 3,988,600 bytes` / `3.80 MB`):

| # | Artifact Relative Path | Exact Byte Size | Size (KB) | Cryptographic SHA256 Checksum | Status |
|--:|:--|--:|--:|:--|:--|
| 1 | `gbos-vm/work/guest/mesa-runtime/libEGL_virgl.so` | **324,064** | 316.47 KB | `8306aafeec5ae3936c6b38259ea2945e356ec1fe0828a7c3f694a1e0867380d9` | VERIFIED |
| 2 | `gbos-vm/work/guest/mesa-runtime/libGLESv2_virgl.so` | **60,792** | 59.37 KB | `45b2afc226e7f24e5a7a79dc6e10d85d31ee690524167bcfa3861ba5adfe4d10` | VERIFIED |
| 3 | `gbos-vm/work/guest/libvulkan_virtio.so` | **3,302,952** | 3,225.54 KB | `92380729e96b84bc4b7d579fb74fc06ade65388e583936019e9b5d10ec58a681` | VERIFIED |
| 4 | `gbos-vm/work/guest/vm-input.jar` | **7,600** | 7.42 KB | `acbbf20483cf8290375dec9f23fa4e2aa7a7529d6548b9412601e57575d70173` | VERIFIED |
| 5 | `gbos-vm/work/guest/guest-vulkan-probe` | **27,912** | 27.26 KB | `e86148933b4c91515697cb0c0ce5d5dff054fe8bf77af20a20539a4f0a6160d9` | VERIFIED |
| 6 | `gbos-vm/work/tools/guest_graphics_memfd_policy` | **265,280** | 259.06 KB | `37a8aa964c8c6ceeba94f18357c4285d3a17ddb108011401381296937d7c00e0` | VERIFIED |

### Supplementary `gbos-vm/work/` Runtime Libraries & Cross Config

| # | Supplementary Artifact Path | Exact Byte Size | Size (KB) | Cryptographic SHA256 Checksum | Status |
|--:|:--|--:|--:|:--|:--|
| 1 | `gbos-vm/work/guest/mesa-runtime/libgallium_dri.so` | **18,110,792** | 17,686.32 KB | `3e27686cd5a38a1aa54d6a8a5ae720287a248edca1e4acf9d7371d37a575eaef` | VERIFIED |
| 2 | `gbos-vm/work/guest/mesa-runtime/libdrm.so` | **94,904** | 92.68 KB | `e7ff06bbbac3e492e221ecaa0fa593eb9387db5dc932d99c17ad8645704bb087` | VERIFIED |
| 3 | `gbos-vm/work/guest/mesa-runtime/libGLESv1_CM_virgl.so` | **25,800** | 25.20 KB | `fa14d225da805db4d93e20a0d820b72cc7005fdd3db6cbe6c63aea5a7706e077` | VERIFIED |
| 4 | `gbos-vm/work/android-aarch64.cross` | **661** | 0.65 KB | `2b0b30ceb8026cde2d59356ce4983b73444085503a2b6b4c1e5dd39153904a3e` | VERIFIED |

---

## 6. Generated Visual EDA Plots (`eda_plots/`)

| Plot Filename | Absolute Path | Exact Byte Size | SHA256 Checksum |
|:--|:--|--:|:--|
| `eda_domain_distribution.png` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test/eda_plots/eda_domain_distribution.png` | **139,225** | `9687947289d9a9e77b04db8df75fded20d14662131cf233c7606674952cdbfc0` |
| `eda_artifact_sizes.png` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test/eda_plots/eda_artifact_sizes.png` | **134,137** | `6fa5f9b10e39b6ddf6a4d6dc43a4aa03389c3ff6361c11675b03e524f108cdf8` |
| `eda_model_elo_vs_cost.png` | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test/eda_plots/eda_model_elo_vs_cost.png` | **200,003** | `62f2aaa842a7ef2a384b150c777881ae1696cbc9af6f48643bd7a4ebee6ce53c` |
