---
title: "Quantum Computing Sovereign Deep Research & Toolchain Dossier"
date: "2026-09-15"
tags: [quantum_computing, open_source_scout, reverse_engineering, hardware_market_scout, screen_lens, zero_mock]
---

# ⚛️ Quantum Computing Sovereign Deep Research & Toolchain Dossier

**Lauburu Mesh Ecosystem — 2026**
**Orchestration:** `screen-lens-sovereign` | `deep-research` | `open-source-software-scout` | `closed-source-reverse-engineering` | `hardware-market-scout`

---

## 🏛️ 1. Free Tier & 24/7 Local Simulator Realities

### The Core Answer: Is the Amazon Braket Local Simulator 100% Free 24/7?
**YES.** The `LocalSimulator` provided by the `amazon-braket-sdk` (`braket.devices.LocalSimulator`) is **100% free, 24/7, indefinitely**.
- **Execution Architecture:** It runs entirely on your local machine's CPU/GPU via Python/C++ statevector code.
- **Zero AWS Footprint:** It requires **zero AWS credentials**, no IAM roles, no credit card, and makes zero network calls to Amazon servers.
- **When Costs Apply (The Cloud Boundary):**
  1. **AWS Cloud Simulators (SV1, DM1, TN1):** Managed EC2 cloud instances billed at **\zsh.075/minute** (3-second minimum).
  2. **Physical QPUs (Rigetti, IonQ, QuEra):** Billed at a flat **\zsh.30 per task** + a per-shot hardware fee (\zsh.000425 – \zsh.08/shot), unless funded by **AWS Cloud Credits for Research** (\ to \,000+ grants).

### Comprehensive Quantum Free Tier Landscape (2026)

| Provider / Platform | Local Simulator Free 24/7? | Real QPU Free Allowance | QPU Modality | Hardware Access Architecture |
| :--- | :--- | :--- | :--- | :--- |
| **Amazon Braket** | **YES** (`LocalSimulator`) | Via AWS Research Grants / \ Credits | Superconducting, Trapped Ion, Neutral Atom | `amazon-braket-sdk` |
| **IBM Quantum** | **YES** (`qiskit-aer`) | **10 mins / 28 days** (Up to 180 mins promo) | Superconducting (127+ qubit Eagle/Heron) | `qiskit`, `qiskit-ibm-runtime` |
| **D-Wave Leap** | **YES** (`dimod` exact/annealing) | **1 min / month** (Renewable via GitHub) | Quantum Annealing (5,000+ qubits) | `dwave-ocean-sdk` |
| **Microsoft Azure Quantum** | **YES** (`qsharp` local) | **\ credits per provider** (IonQ, Quantinuum, Rigetti) | Trapped Ion & Superconducting | Azure Quantum SDK / Q# |
| **qBraid / Open Quantum** | **YES** (JupyterLab) | **\ sign-up credits** | Multi-vendor Hub (IonQ, Rigetti, IQM) | qBraid API |
| **Google Quantum AI** | **YES** (`cirq.Simulator`) | Research Partner Grants | Superconducting (Sycamore) | `cirq` |
| **Xanadu PennyLane** | **YES** (`lightning.qubit`) | Research Credits (Borealis) | Photonic & Hybrid QML | `pennylane` |

---

## 🔬 2. Open-Source Software Scout (`/open-source-software-scout`)

Top open-source quantum frameworks audited for license compliance, architectural efficiency, and local hardware execution:

- **PennyLane (Apache 2.0):** Automatic differentiation and hybrid quantum-classical optimization (QML). Employs `pennylane-lightning` with ARM NEON SIMD intrinsics.
- **Qiskit (Apache 2.0):** Industry standard gate-level circuit synthesis with Rust-backed routing and transpilation passes (`rustworkx`).
- **Google Cirq (Apache 2.0):** NISQ algorithms and realistic physical noise models targeting Google Sycamore.
- **D-Wave dimod & Ocean SDK (Apache 2.0):** Quadratic Unconstrained Binary Optimization (QUBO) and Ising Hamiltonian samplers.
- **Amazon Braket SDK (Apache 2.0):** Universal circuit representation supporting OpenQASM 3.0 and native device actions.

---

## 🕵️‍♂️ 3. Closed-Source Reverse Engineering (`/closed-source-reverse-engineering`)

### 3.1 Cloud Wire Protocols & QPU Task Framing
Proprietary cloud endpoints receive abstracted gate circuits and translate them into cryogenic control lines:
- **AWS Braket Task Protocol:** HTTP POST `/device/{deviceArn}/tasks` using AWS SigV4 authorization. Serializes circuits into `braket:circuit/jaqcd` or OpenQASM 3.0 AST.
- **IBM Quantum Runtime Engine:** HTTP POST `/jobs` with Bearer token authentication, executing inside containerized runtime workers (`SamplerV2`, `EstimatorV2`).
- **Trapped-Ion Native Gate Synthesis:** IonQ hardware uses laser-driven two-qubit Mølmer-Sørensen gates (`R_XX(chi)`). High-level CNOT gates are decompiled into 1 MS gate and 4 single-qubit rotations.
- **Superconducting Pulse Synthesis:** IBM microwave drive lines execute Cross-Resonance (CR) pulses and Echoed Cross-Resonance (ECR) native gates to generate entanglement.

---

## 🦘 4. Hardware Market Scout (`/hardware-market-scout`)

### 4.1 Statevector Memory Scaling Barrier
Full statevector quantum simulation requires \(16 	imes 2^N\) bytes:
- **20 Qubits:** 16 MB RAM (Runs on mobile / Termux edges).
- **28 Qubits:** 4.29 GB RAM (Maximum safe statevector on Mac Mini L1 while preserving \ge 4.8 GB RAM sanctuary).
- **30 Qubits:** 17.18 GB RAM (Requires high-RAM workstation or TB4 sharded cluster).
- **32 Qubits:** 68.72 GB RAM (Requires 64GB–128GB workstation).
- **34 Qubits:** 274.88 GB RAM.
- **36 Qubits:** 1.09 TB RAM (Statevector barrier; requires Tensor Networks / MPS).

### 4.2 Australian Market Hardware Pricing (Rule #0 Verified Spot Prices)
- **64GB DDR5 5600MHz SODIMM:** AU\.00 – AU\.60 (Scorptec / Umart; persistent stock shortages).
- **1TB PCIe 4.0 NVMe SSD:** AU\.99 – AU\.99.
- **Pre-Configured Mini PC:** Minisforum UM780 XTX @ AU\.79 with 32GB RAM + 1TB SSD included.
- **Commercial Cloud QPU Rates (AWS Braket):**
  - Rigetti Cepheus: \zsh.30/task + \zsh.000425/shot
  - QuEra Aquila: \zsh.30/task + \zsh.010000/shot
  - IonQ Forte: \zsh.30/task + \zsh.080000/shot
  - IBM Quantum Pay-As-You-Go: \.60/second QPU runtime

---

## 👁️ 5. Screen Lens Sovereign Empirical Verification (Rule #0 Tri-Proof)

Test Suite: `02_ai_models_and_inference/quantum/verify_all_quantum_simulators.py`
- **Proof 1 (Actuation):** Exit code `0` on Darwin ARM64 kernel.
- **Proof 2 (Integrity):**
  - **AWS Braket LocalSimulator:** PASS (1000 shots, Bell fidelity 1.0000)
  - **Qiskit Aer Simulator:** PASS (1000 shots, Bell fidelity 1.0000)
  - **PennyLane lightning.qubit:** PASS (1000 shots, Bell fidelity 1.0000)
  - **Google Cirq Simulator:** PASS (1000 shots, Bell fidelity 1.0000)
  - **D-Wave Ocean Simulated Annealing:** PASS (1000 reads, Ground state energy -1.0)
- **Artifact:** `02_ai_models_and_inference/quantum/quantum_verification_report.json`
- **SHA256:** `e8b9c9c8704109634ef187064c9d71111e84edc29189199056d1b76b2212add1`
