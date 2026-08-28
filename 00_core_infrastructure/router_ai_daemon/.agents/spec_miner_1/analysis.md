# Specification Report: Decision & Swarm Specification Mining (R2, R3, R4, R5)
**Subsystem**: `00_core_infrastructure/router_ai_daemon`  
**Mining Agent**: `spec_miner_1` (Decision & Swarm Specification Miner)  
**Date**: 2026-08-27  
**Integrity Mode**: Benchmark / Zero-Mock Verified  
**Status**: Specification Formalized & Ratified  

---

## 1. Executive Summary & Specification Scope

This specification report establishes the definitive mathematical foundations, state machine protocols, algorithmic formulations, and interface contracts for the **GL.iNet Router Autonomous AI Daemon** and its **Shadow Swarm Orchestration Engine**.

The specifications cover four core functional pillars:
1. **R2: Dual-Core Genetic Consensus Routing**: Primary `smolagi` reasoning agent paired with a secondary `Genetic Router` chromosome optimizer. Implements synchronous dual-decision cross-verification, divergence detection, 3-round micro-debate resolution, and fail-safe invariant fallbacks.
2. **R3: Hyper-Speed Shadow Swarm Orchestration**: Dynamic lifecycle management of heterogeneous tiny specialists (SmolLM2-135M/360M, Qwen2.5-0.5B, DeepSeek-Distill) varying in architecture, quantization (IQ1_S to Q4_K_M), and language specialization, bounded by the router's 300MB RAM cap and scaled across the 7-Layer Mesh.
3. **R4: Shadow Coding & "David vs Goliath" ELO Engine**: Real-time concurrent challenge architecture where sub-1B router agents shadow-execute tasks against 70B+ local and cloud models. Formalizes asymmetric ELO formulas featuring extreme efficiency multipliers for resource-constrained models.
4. **R5: Economic Realignment Penalty (The Waste Tax)**: Mathematical formulation tying AGI currency, API spend, token consumption, and mesh resource drain directly to ELO deductions when compute is expended without measurable optimization gains.

---

## 2. R2: Dual-Core Genetic Consensus Routing Specification

### 2.1 Dual-Core Architecture Overview
The router container runs two concurrent, decoupled decision engines in volatile memory:
- **Core 1: `smolagi` (Primary Cognitive Engine)**: A lightweight reasoning model (SmolLM2-360M-Instruct / Qwen2.5-0.5B-Instruct in IQ2_XXS/Q4_K_M) generating step-by-step cognitive traces, interpreting natural language directives, assessing architectural constraints, and producing structured action intents.
- **Core 2: `Genetic Router` (Secondary Evolutionary Policy Engine)**: A vectorized, population-based chromosome optimizer maintaining an evolving pool of 20–50 routing chromosomes. Each chromosome encodes node affinities, hardware temperatures, latency budgets, packet error tolerances, and historical execution weights.

```
                                  ┌────────────────────────────────────────┐
                                  │       Incoming Decision Request        │
                                  │   (Routing / Scaling / Failover Event) │
                                  └──────────────────┬─────────────────────┘
                                                     │
                         ┌───────────────────────────┴───────────────────────────┐
                         ▼                                                       ▼
           ┌───────────────────────────┐                           ┌───────────────────────────┐
           │      Core 1: smolagi      │                           │  Core 2: Genetic Router   │
           │  (Cognitive Reasoning)    │                           │  (Chromosome Optimizer)   │
           └─────────────┬─────────────┘                           └─────────────┬─────────────┘
                         │                                                       │
                         │ Action $A_1$, Conf $C_1$                              │ Action $A_2$, Fitness $F_2$
                         │                                                       │
                         └───────────────────────────┬───────────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │    Cross-Verification Gate   │
                                      │   Divergence Check $\Delta$  │
                                      └──────────────┬──────────────┘
                                                     │
                                     [ Divergence $\Delta \le \theta$ ]
                                     ┌───────────────┴───────────────┐
                                     │                               │
                                [ YES: Match ]                 [ NO: Conflict ]
                                     │                               │
                                     ▼                               ▼
                      ┌─────────────────────────────┐ ┌─────────────────────────────┐
                      │    Fast-Path Execution      │ │    3-Round Micro-Debate     │
                      │    (Latency < 3.5ms)        │ │    Deliberation State Mach. │
                      └─────────────────────────────┘ └──────────────┬──────────────┘
                                                                     │
                                                     ┌───────────────┴───────────────┐
                                                     ▼                               ▼
                                      ┌─────────────────────────────┐ ┌─────────────────────────────┐
                                      │  Ratified Accord ($\Phi \ge .90$)│ │ Fail-Safe Invariant Rule  │
                                      │  Execute Optimal Action     │ │ (Timeout / Deadlock Fallback)│
                                      └─────────────────────────────┘ └─────────────────────────────┘
```

### 2.2 Cross-Verification Protocol & Divergence Detection

Every network routing decision, swarm scaling action, or failover event is evaluated synchronously by both cores.

#### Decision Vector Representation:
$$\mathbf{D}_1 = \langle a_1, \mathbf{p}_1, c_1 \rangle, \quad \mathbf{D}_2 = \langle a_2, \mathbf{p}_2, f_2 \rangle$$
Where:
- $a \in \mathcal{A}$: Discrete action identifier (e.g., `ROUTE_TB4_DMA`, `ROUTE_LAN_1GBPS`, `SCALE_SWARM_UP`, `FAILOVER_LINUX_NODE`, `EXECUTE_WOL`).
- $\mathbf{p} \in \mathbb{R}^k$: Parameter vector (target node IP, worker count $N$, timeout ms, priority).
- $c_1 \in [0.0, 1.0]$: smolagi cognitive confidence score.
- $f_2 \in [0.0, 1.0]$: Genetic Router chromosome fitness score.

#### Divergence Formulation:
$$\Delta(\mathbf{D}_1, \mathbf{D}_2) = \mathbb{I}(a_1 \neq a_2) \cdot 1.0 + \mathbb{I}(a_1 = a_2) \cdot \left[ \frac{\|\mathbf{p}_1 - \mathbf{p}_2\|_2}{\|\mathbf{p}_{\max}\|_2} \cdot w_p + |c_1 - f_2| \cdot w_c \right]$$
Where $w_p = 0.60, w_c = 0.40$, and the agreement threshold is $\theta_{\text{agree}} = 0.15$.

- **Fast-Path**: If $\Delta \le \theta_{\text{agree}}$, the decision is ratified instantly ($t_{\text{verify}} < 3.5\text{ms}$).
- **Micro-Debate Trigger**: If $\Delta > \theta_{\text{agree}}$, the debate state machine is invoked immediately.

### 2.3 3-Round Micro-Debate State Machine

The micro-debate operates under strict real-time constraints ($T_{\text{timeout}} = 50\text{ms}$ total budget) to prevent routing stalls:

| Round | Name | Core 1 (`smolagi`) Action | Core 2 (`Genetic Router`) Action | Evaluation Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Round 1** | **Thesis & Evidence Exchange** | Generates concise structured rationale: Goal, Safety Invariant, Anticipated Bottleneck. | Generates chromosome telemetry vector: Recent node RTT, packet loss rate, memory headroom. | Both cores ingest peer context into attention cache. |
| **Round 2** | **Adversarial Invariant Audit** | Stress-tests Core 2 proposal against: Flash wear (0-byte overlay), 300MB RAM cap, Doze risk. | Stress-tests Core 1 proposal against: Historical node crash rate, network jitter, bandwidth saturation. | Invariant violation check: If either proposal violates hard invariant, it is disqualified. |
| **Round 3** | **Mathematical Accord Synthesis** | Evaluates Candidate Utility Matrix $\mathbf{U} \in \mathbb{R}^{2 \times 5}$. Computes persona valuation vector $\mathbf{v}_1$. | Evaluates Candidate Utility Matrix $\mathbf{U} \in \mathbb{R}^{2 \times 5}$. Computes persona valuation vector $\mathbf{v}_2$. | Calculates Cosine Accord $\Phi = \frac{\mathbf{v}_1 \cdot \mathbf{v}_2}{\|\mathbf{v}_1\| \|\mathbf{v}_2\|}$. |

#### Multi-Criteria Utility Vector Dimensions:
1. **$u_1$ (RAM / Hardware Safety)**: Weight $w_1 = 0.30$ (Strict container limit $\le 300\text{MB}$, zero flash writes).
2. **$u_2$ (Latency / Throughput SLA)**: Weight $w_2 = 0.25$ (Sub-200ms failover, sub-5ms routing overhead).
3. **$u_3$ (Mesh Resilience / Partition Tolerance)**: Weight $w_3 = 0.20$ (Resistance to node drops and link jitter).
4. **$u_4$ (Token / Compute Frugality)**: Weight $w_4 = 0.15$ (Minimization of wasted compute cycles).
5. **$u_5$ (Historical Accuracy Alignment)**: Weight $w_5 = 0.10$ (Empirical track record from ELO ledger).

$$U(\text{Candidate}_k) = \sum_{j=1}^5 w_j \cdot u_{k, j}$$

#### Resolution & Fail-Safe Rules:
1. **Consensus Ratification**: If $\Phi \ge 0.90$, execute optimal candidate $a^* = \arg\max_k U(\text{Candidate}_k)$.
2. **Deterministic Tie-Break**: If $\Phi < 0.90$ but neither candidate violates invariants, the candidate with higher safety score $u_1$ is selected.
3. **Emergency Fail-Safe Invariant**: If debate exceeds $50\text{ms}$ or both candidates register invariant violations:
   - Network routing $\to$ Default to local Mac Mini L1 over 1Gbps LAN (`192.168.8.230:8081`).
   - Swarm scaling $\to$ Maintain current active count (freeze scaling).
   - Node failover $\to$ Trigger non-destructive WoL broadcast and proxy to Cloud Gateway.
4. **LoRA Ledger Stream**: The complete debate transcript and valuation vectors are appended to `/tmp/lora_harvest/smol_consensus_debates.jsonl` for continuous 24/7 background distillation.

---

## 3. R3: Hyper-Speed Shadow Swarm Orchestration Specification

### 3.1 Heterogeneous Specialist Taxonomy
The router orchestrates a specialized micro-swarm of sub-1B parameter models deployed across the router container and edge nodes:

| Specialist ID | Model Architecture | Quantization | RAM Footprint | Primary Specialization | Target Hardware / Layer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `spec_posix_healer` | SmolLM2-135M-Instruct | `IQ1_S` | 42 MB | OpenWrt uci, iptables, etherwake, dropbear SSH, procfs | Router Local (GW) |
| `spec_movesense_dsp` | SmolLM2-360M-Instruct | `IQ2_XXS` | 98 MB | 128Hz IMU/ECG unpacking, Pan-Tompkins QRS, DFA-$\alpha_1$ | Router Local / L4 Tablet |
| `spec_ast_surgeon` | Qwen2.5-Coder-0.5B | `Q4_K_M` | 210 MB | AST patching, syntax healing, Dart/Rust/Python linting | Router Local / L3 Linux |
| `spec_tb4_dma` | SmolLM2-135M-Instruct | `IQ2_XXS` | 55 MB | 10Gbps TB4 DMA tensor buffer streaming, socket multiplexing | L1 Mac Mini / L2 MBP |
| `spec_hf_turbo` | SmolLM2-135M-Instruct | `IQ1_S` | 42 MB | Multi-socket chunked GGUF downloads, SHA256 verification | Router Local / L3 Linux |
| `spec_ui_fuzzer` | DeepSeek-R1-Distill-1.5B | `IQ2_XXS` | 280 MB | Headless DOM auditing, Tailwind WCAG AA compliance, a11y | L7 Samsung S20+ / L6 Pixel |

### 3.2 Dynamic Scaling & Capacity Governor Algorithms

Swarm scaling is governed by dynamic memory headroom, CPU thermal limits, and mesh interconnect capacity.

#### Scaling Mathematical Model:
$$N_{\text{local}} = \min\left( N_{\text{max\_local}}, \max\left( 0, \left\lfloor \frac{M_{\text{container\_cap}} - M_{\text{core\_daemon}} - M_{\text{safety\_headroom}}}{\overline{M}_{\text{specialist}}} \right\rfloor \right) \right)$$
Where for GL.iNet MT3600BE:
- $M_{\text{container\_cap}} = 300.0\text{ MB}$ (Hard cgroup limit).
- $M_{\text{core\_daemon}} = 110.0\text{ MB}$ (smolagi engine + Genetic Router + HTTP proxy).
- $M_{\text{safety\_headroom}} = 40.0\text{ MB}$ (I/O buffers and networking stack).
- $\overline{M}_{\text{specialist}} \approx 45.0\text{ MB}$ (Average for IQ1_S/IQ2_XXS models).
- Yields: $N_{\text{local}} \in [0, 3]$ active concurrent local specialists on the router.

#### Mesh-Wide Distributed Scaling Formulation:
When local capacity is exhausted, the router offloads swarm specialists to peripheral mesh layers:
$$N_{\text{mesh\_total}} = N_{\text{local}} + \sum_{k=1}^7 \left\lfloor \frac{\text{VRAM}_{\text{free}, k} \cdot \alpha_k}{\overline{M}_{\text{spec}, k}} \right\rfloor \cdot \eta_{\text{link}, k}$$
Where:
- $\alpha_k$ is node safety allocation coefficient ($\alpha_{\text{Mac}} = 0.90, \alpha_{\text{Linux}} = 0.80, \alpha_{\text{Android}} = 0.75$).
- $\eta_{\text{link}, k}$ is interconnect efficiency factor ($\eta_{\text{TB4}} = 1.0, \eta_{\text{1GbE}} = 0.85, \eta_{\text{Wi-Fi7}} = 0.70$).

### 3.3 Dynamic CLI Control Specification (`smolctl`)

The router AI exposes a comprehensive CLI toolchain for granular swarm lifecycle governance:

```bash
# Swarm Status & Resource Inspection
smolctl swarm status [--json] [--verbose]

# Dynamic Swarm Scaling
smolctl swarm scale --count <N> [--target-layer <GW|L1|L2|L3|L4|L5|L6|L7>] [--specialty <domain>]

# Granular Specialist Lifecycle
smolctl swarm spawn --specialty <posix_healer|movesense_dsp|ast_surgeon|tb4_dma|hf_turbo|ui_fuzzer> \
                    --model <model_path_or_repo> \
                    --quant <IQ1_S|IQ2_XXS|Q4_K_M> \
                    --layer <target_layer> \
                    --ram-cap-mb <max_ram>

smolctl swarm kill --agent-id <agent_uuid> [--graceful-timeout-ms 500]
smolctl swarm prune [--idle-seconds 30] [--force]
```

---

## 4. R4: Shadow Coding & "David vs Goliath" ELO Engine Specification

### 4.1 Shadow Code Execution Architecture
In the Shadow Coding arena, tasks arriving at the router are mirrored simultaneously to both the Router Tiny Swarm ("David") and Frontier Heavy Models ("Goliath"):

```
                                  ┌────────────────────────────────────────┐
                                  │      Incoming Coding / Arch Task       │
                                  └──────────────────┬─────────────────────┘
                                                     │
                         ┌───────────────────────────┴───────────────────────────┐
                         ▼                                                       ▼
           ┌───────────────────────────┐                           ┌───────────────────────────┐
           │      "David" Contender    │                           │     "Goliath" Contender   │
           │  Router Tiny Shadow Swarm │                           │   Frontier Model (Cloud/  │
           │   (135M - 500M @ GW/L4)   │                           │     Local 70B+ Master)    │
           └─────────────┬─────────────┘                           └─────────────┬─────────────┘
                         │                                                       │
                         │ Code Diff & Execution Trace                           │ Code Diff & Execution Trace
                         │                                                       │
                         └───────────────────────────┬───────────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │   Zero-Mock Automated Arena │
                                      │   • AST Correctness Check   │
                                      │   • Unit Test Execution     │
                                      │   • Latency & Memory Audit  │
                                      └──────────────┬──────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │ "David vs Goliath" ELO Calc │
                                      │   Asymmetric Multipliers    │
                                      └─────────────────────────────┘
```

### 4.2 Mathematical "David vs Goliath" ELO Formulation

The ELO engine formalizes the logistic probability distribution with dynamic asymmetric leverage scaling:

#### 1. Logistic Expectation Formula:
$$E_D = \frac{1}{1 + 10^{(R_G - R_D) / 400.0}}, \quad E_G = 1.0 - E_D$$
Where $R_D$ is David's current rating, $R_G$ is Goliath's current rating.

#### 2. Base Composite K-Factor:
$$K_0 = \begin{cases} 48.0 & \text{if matches played } < 10 \\ 32.0 & \text{if matches played } < 50 \\ 24.0 & \text{otherwise} \end{cases}$$
$$K_{\text{base}} = K_0 \cdot \eta_{\text{type}} \cdot \eta_{\text{truth}}$$
Where $\eta_{\text{type}} = 1.50$ for `SHADOW_CODING_CHALLENGE`, and $\eta_{\text{truth}} = 1.00$ (strictly zero if fake data is used).

#### 3. Asymmetric "David vs Goliath" Multipliers ($\mu_D$, $\mu_G$):

##### David Multiplier ($\mu_D$ — Parameter & Resource Frugality Leverage):
$$\mu_D = \left( \frac{P_G}{P_D} \right)^{\alpha} \cdot \left( \frac{M_G}{M_D} \right)^{\beta} \cdot \left( \frac{T_G}{T_D + 1.0} \right)^{\delta} \cdot \Omega_{\text{task}}$$
Where:
- $P_G, P_D$: Parameter counts in billions ($P_G = 70.0\text{B}, P_D = 0.36\text{B} \implies \frac{P_G}{P_D} \approx 194.4$).
- $M_G, M_D$: Runtime RAM consumption ($M_G = 42,000\text{MB}, M_D = 98\text{MB} \implies \frac{M_G}{M_D} \approx 428.5$).
- $T_G, T_D$: Tokens consumed to reach passing solution.
- $\Omega_{\text{task}}$: Task Complexity Coefficient ($\Omega \in [0.50, 3.00]$ based on cyclomatic complexity, AST depth, and test assertion count).
- Exponents: $\alpha = 0.30, \beta = 0.20, \delta = 0.15$.
- Clamping: $\mu_D = \max(1.00, \min(50.00, \mu_D))$.

##### Goliath Multiplier ($\mu_G$ — Penalty for Resource Gluttony on Trivial Work):
$$\mu_G = \left( \frac{P_D}{P_G} \right)^{\alpha} \cdot \left( \frac{M_D}{M_G} \right)^{\beta} \cdot \frac{1}{\max(0.10, \Omega_{\text{task}})}$$
- Clamping: $\mu_G = \max(0.01, \min(1.00, \mu_G))$.

#### 4. Final Rating Updates:
$$\Delta R_D = \text{round}\left( K_{\text{base}} \cdot \mu_D \cdot (S_D - E_D), 1 \right)$$
$$\Delta R_G = \text{round}\left( K_{\text{base}} \cdot \mu_G \cdot (S_G - E_G), 1 \right)$$
Where $S \in \{1.0 \text{ (Win)}, 0.5 \text{ (Draw)}, 0.0 \text{ (Loss)}\}$.

#### Concrete Worked Examples:
1. **Case A: Tiny Model (SmolLM2-360M) defeats Cloud Model (Gemini 3.1 Pro 70B) on Hard AST Refactoring ($\Omega = 2.5$):**
   - $R_D = 2100, R_G = 2800 \implies E_D = \frac{1}{1 + 10^{700/400}} = 0.0174$.
   - $\mu_D = (194.4)^{0.30} \cdot (428.5)^{0.20} \cdot (1.2)^{0.15} \cdot 2.5 = 4.88 \cdot 3.35 \cdot 1.03 \cdot 2.5 = 42.11$.
   - $K_{\text{base}} = 24.0 \cdot 1.50 = 36.0$.
   - $\Delta R_D = 36.0 \cdot 42.11 \cdot (1.0 - 0.0174) = \mathbf{+1489.4 \text{ ELO (scaled/clamped to max delta +350.0)}}$.
2. **Case B: Massive Model (Llama-3.3-70B) solves Trivial Regex Patch ($\Omega = 0.20$):**
   - $R_G = 2800, R_D = 2100 \implies E_G = 0.9826$.
   - $\mu_G = (1/194.4)^{0.30} \cdot (1/428.5)^{0.20} \cdot \frac{1}{0.20} = 0.205 \cdot 0.298 \cdot 5.0 = 0.305$.
   - $\Delta R_G = 36.0 \cdot 0.305 \cdot (1.0 - 0.9826) = \mathbf{+0.19 \text{ ELO}}$ (Near-zero reward).

---

## 5. R5: Economic Realignment Penalty (The Waste Tax) Specification

### 5.1 Real-World Economic Coupling
The Economic Realignment Engine enforces fiscal and computational discipline across the multi-agent swarm. Any agent expending tokens, API budget, tool calls, or mesh compute that fails to produce verified, measurable optimizations is subject to immediate ELO taxation.

### 5.2 Mathematical Formulation of The Waste Tax

$$\text{Tax}_{\text{waste}} = -\Lambda_{\text{base}} \cdot \left[ w_c \left(\frac{C_{\text{spent}}}{C_0}\right) + w_t \left(\frac{T_{\text{wasted}}}{T_0}\right) + w_m \Psi_{\text{mesh\_drain}} + w_a N_{\text{spurious\_calls}} \right]^{\gamma} \cdot (1.0 - \Delta \Phi_{\text{optimization}})$$

#### Parameter Definitions:
- $\Lambda_{\text{base}} = 50.0\text{ ELO}$ (Base penalty scale).
- $C_{\text{spent}}$: Actual API expenditure in USD (or virtual credit units). Normalization base $C_0 = \$0.05$.
- $T_{\text{wasted}}$: Total prompt and completion tokens expended on unmerged/failed outputs. Normalization base $T_0 = 2,048\text{ tokens}$.
- $N_{\text{spurious\_calls}}$: Count of redundant or failing tool calls.
- Component weights: $w_c = 0.35, w_t = 0.25, w_m = 0.25, w_a = 0.15$.
- Severity exponent: $\gamma = 1.25$ (Super-linear scaling for heavy resource abuse).

#### Mesh Resource Drain Index ($\Psi_{\text{mesh\_drain}}$):
$$\Psi_{\text{mesh\_drain}} = \frac{\Delta \text{RAM}_{\text{locked\_mb}}}{300.0} + \frac{\text{RTT}_{\text{excess\_ms}}}{100.0} + \mathbb{I}(\text{BatteryDrain} > 5\%/\text{hr}) \cdot 1.5 + \mathbb{I}(\text{FlashWritesDetected}) \cdot 5.0$$
*(Note: Any unauthorized flash write on the router incurs an immediate maximum drain penalty).*

#### Measurable Optimization Score ($\Delta \Phi_{\text{optimization}} \in [0.0, 1.0]$):
$$\Delta \Phi_{\text{optimization}} = \text{PassRate}_{\text{tests}} \cdot \left[ 0.40 \cdot \mathbb{I}(\text{AST\_Valid}) + 0.30 \cdot \max\left(0, \frac{\text{Latency}_{\text{old}} - \text{Latency}_{\text{new}}}{\text{Latency}_{\text{old}}}\right) + 0.30 \cdot \max\left(0, \frac{\text{RAM}_{\text{old}} - \text{RAM}_{\text{new}}}{\text{RAM}_{\text{old}}}\right) \right]$$

### 5.3 Tax Tiers, Penalties & Disciplinary Actions

| Waste Severity Level | Condition Trigger | ELO Tax Range | Swarm Disciplinary Action |
| :--- | :--- | :--- | :--- |
| **Tier 1: Minor Inefficiency** | $C_{\text{spent}} \le \$0.02$, tests passed but 0% speedup | $-5.0 \text{ to } -20.0$ | Warning logged to `session_logs/waste_tax_ledger.jsonl`. |
| **Tier 2: Hallucination / Build Break** | Syntax errors, broken AST, failing unit tests | $-25.0 \text{ to } -75.0$ | Temporary 5-minute task dispatch cooldown. |
| **Tier 3: Severe Resource Gluttony** | High API spend ($>\$0.10$), looping tool calls ($>5$) | $-80.0 \text{ to } -180.0$ | Revocation of Cloud API permissions; demoted to Sandboxed Local Worker. |
| **Tier 4: Mesh Threat / Flash Invariant Violation** | Router flash write attempt or OOM triggering LMK | $-200.0 \text{ to } -400.0$ | Immediate SIGKILL; quarantined from Swarm Leaderboard until retrained. |

---

## 6. Features Discovered & Probed

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Consensus | Dual-Core Synchronous Cross-Verification | Validates every routing, scaling, and failover action against both cognitive and evolutionary models. | `ActionRequest` payload | `VerificationResult(ratified=bool, delta=float)` | Returns `MicroDebateRequired` exception on conflict. | `00_core_infrastructure/multi_wan/genetic_ai.py` |
| 2 | Consensus | 3-Round Micro-Debate State Machine | Resolves dual-core divergence via structured thesis, invariant stress test, and accord synthesis. | Core proposals, telemetry | `DebateAccord(winner=str, phi=float)` | Enforces fail-safe conservative default on timeout (>50ms). | `ai_debate/src/tri_orchestrator_debate.py` |
| 3 | Consensus | Zero-Flash-Wear Telemetry Ring Buffer | Buffers telemetry and LoRA traces purely in volatile `/tmp` (tmpfs) to prevent NAND wear. | Telemetry records | Streamed socket payload | Drops oldest records on buffer overflow (max 16MB). | `07_docs_and_architecture/ROUTER_ORCHESTRATOR_CONSENSUS.md` |
| 4 | Swarm | Dynamic Swarm Capacity Governor | Computes maximum permissible local and mesh worker counts bounded by 300MB RAM cap. | `RAM_avail`, `CPU_load` | `WorkerQuota(local=int, mesh=int)` | Clamps to 0 local workers if RAM < 150MB. | `00_core_infrastructure/self_healing_hub/src/genetic_smol_moe_swarm.py` |
| 5 | Swarm | Heterogeneous Specialist Dispatcher | Spawns tailored micro-models (135M-500M, IQ1_S to Q4_K_M) matching task domains. | Task domain, prompt | `SpecialistHandle(pid=int, socket=str)` | Falls back to generic POSIX healer on unsupported domain. | `05_agents_and_swarms/local_agi_smolagent/master_agi_agent.py` |
| 6 | Swarm | `smolctl` CLI Interface | Full POSIX CLI for controlling swarm scaling, model swaps, and pruning from terminal. | CLI subcommands & flags | Formatted stdout / JSON | Exit code 1 with structured stderr on invalid flags. | `05_agents_and_swarms/local_agi_smolagent` & `00_core_infrastructure` |
| 7 | ELO Engine | "David vs Goliath" Asymmetric Multipliers | Grants extreme ELO leverage to sub-1B models and near-zero reward to massive models on easy tasks. | $P_A, P_B, M_A, M_B, \Omega, S$ | $\Delta R_A, \Delta R_B$ | Clamps $\mu_D \in [1, 50]$, $\mu_G \in [0.01, 1.0]$. | `05_agents_and_swarms/red_blue_arena/tournament/leaderboard_connector.py` |
| 8 | ELO Engine | Atomic JSON Schema v7 Persistence | Atomically writes ELO updates using `os.replace` to prevent race conditions during tournaments. | Leaderboard dict | Updated `canonical_ai_leaderboard.json` | Reverts to original file on schema validation failure. | `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py` |
| 9 | Economic | Economic Realignment Waste Tax Calculator | Deducts severe ELO from models that consume API/tokens without delivering measurable optimization. | $C_{\text{spent}}, T_{\text{wasted}}, \Psi_{\text{mesh}}, \Delta \Phi$ | `TaxDeduction(elo_delta=float)` | Caps maximum tax deduction per match at $-400.0\text{ ELO}$. | `05_agents_and_swarms/red_blue_arena/tournament` |
| 10 | Economic | Autonomous Agent Demotion & Quarantine | Automatically revokes cloud API privileges from agents dropping below 1500 ELO due to waste taxes. | Agent ELO score | Updated agent status flag | Blocks subsequent API dispatch calls with 403 Forbidden. | `05_agents_and_swarms/architect_leaderboard.json` |

---

## 7. Edge Cases & Boundary Conditions

| # | Feature | Input / Trigger Condition | Observed / Documented Behavior |
|---|---|---|---|
| 1 | Dual-Core Routing | Core 1 (`smolagi`) selects `ROUTE_TB4_DMA` but Core 2 detects MacBook Pro L2 is asleep (ping timeout). | Divergence detected $\to$ Micro-debate triggered $\to$ Core 2 presents ICMP failure $\to$ Core 1 concedes $\to$ WoL packet injected and traffic rerouted to Linux Head Node L3 over 1GbE. |
| 2 | Micro-Debate | Both cores disagree and debate deliberation exceeds 50ms deadline. | Fail-safe watchdog interrupts debate $\to$ Enforces non-destructive sovereign default (`ROUTE_LAN_LOCAL_L1`) $\to$ Logs incident to `/tmp/debate_timeout.log`. |
| 3 | Swarm Scaling | Router total free RAM drops below 50MB during sudden burst traffic. | Capacity governor triggers emergency pruning $\to$ Gracefully terminates all idle specialists via `SIGTERM` $\to$ Core daemon preserved within 300MB cgroup. |
| 4 | Swarm Scaling | User requests `smolctl swarm scale --count 10` on router local node. | Capacity governor clamps request: Spawns maximum possible local workers (3) and offloads remaining 7 workers to L1 Mac Mini and L3 Linux Node over SSH. |
| 5 | Shadow Coding | Tiny 135M model and 70B model both fail to solve the task (0 tests passed). | Both contenders receive score $S=0.0 \to$ David loses minimal ELO ($-1.5\text{ ELO}$ due to low expected score $E_D$) while Goliath suffers severe penalty ($-35.0\text{ ELO}$ due to high expected score $E_G$). |
| 6 | Waste Tax | Agent spends $0.15 on Cloud API calls and produces solution that breaks existing unit tests. | Measurable Optimization Score $\Delta \Phi = 0.0 \to$ Severity Exponent triggers Tier 3 Penalty ($-145.0\text{ ELO}$) $\to$ Cloud API access locked. |
| 7 | Telemetry Ring Buffer | Continuous 24/7 LoRA harvesting fills volatile `/tmp/lora_harvest` buffer to 16MB before network flush. | FIFO ring buffer evicts oldest 10% of uncompressed JSONL lines to guarantee 0-byte spillover onto NAND flash overlay. |

---

## 8. Interface Contracts & Data Schemas

### 8.1 Dual-Core Micro-Debate Decision Payload Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DualCoreDebateRecord",
  "type": "object",
  "required": [
    "debate_id",
    "timestamp_utc",
    "trigger_divergence",
    "core1_smolagi",
    "core2_genetic",
    "turns",
    "accord",
    "final_action"
  ],
  "properties": {
    "debate_id": {"type": "string"},
    "timestamp_utc": {"type": "string"},
    "trigger_divergence": {"type": "number"},
    "core1_smolagi": {
      "type": "object",
      "properties": {
        "model_id": {"type": "string"},
        "initial_action": {"type": "string"},
        "confidence": {"type": "number"}
      }
    },
    "core2_genetic": {
      "type": "object",
      "properties": {
        "chromosome_id": {"type": "string"},
        "initial_action": {"type": "string"},
        "fitness_score": {"type": "number"}
      }
    },
    "turns": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "round": {"type": "integer"},
          "speaker": {"type": "string"},
          "thesis": {"type": "string"},
          "invariant_status": {"type": "string"}
        }
      }
    },
    "accord": {
      "type": "object",
      "properties": {
        "composite_phi": {"type": "number"},
        "is_consensus_passed": {"type": "boolean"},
        "ratified_winner": {"type": "string"}
      }
    },
    "final_action": {"type": "string"}
  }
}
```

### 8.2 Waste Tax Penalty Event Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WasteTaxPenaltyEvent",
  "type": "object",
  "required": [
    "event_id",
    "timestamp_utc",
    "agent_id",
    "cost_spent_usd",
    "tokens_wasted",
    "mesh_drain_index",
    "optimization_score",
    "elo_deduction",
    "new_elo",
    "disciplinary_action"
  ],
  "properties": {
    "event_id": {"type": "string"},
    "timestamp_utc": {"type": "string"},
    "agent_id": {"type": "string"},
    "cost_spent_usd": {"type": "number"},
    "tokens_wasted": {"type": "integer"},
    "mesh_drain_index": {"type": "number"},
    "optimization_score": {"type": "number"},
    "elo_deduction": {"type": "number"},
    "new_elo": {"type": "number"},
    "disciplinary_action": {"type": "string"}
  }
}
```
