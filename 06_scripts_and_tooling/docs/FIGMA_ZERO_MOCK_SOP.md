# Standard Operating Procedure (SOP): Figma Design-to-Code Zero-Mock Enforcement
- **Document ID**: `SOP-FIGMA-ZERO-MOCK-001`
- **Version**: `1.0.0`
- **Classification**: Mandatory Monorepo Engineering Standard
- **Enforcement Level**: Automated Pre-Merge Blocking Gate (Exit Code `1`)
- **Authority**: Lauburu Monorepo Rule #0 & Swarm Truth Audit Protocol

---

## 1. Purpose & Authority

This Standard Operating Procedure (SOP) governs the conversion of Figma design canvases, design tokens, and layer trees into production source code across the Lauburu Monorepo.

Under **Monorepo Rule #0 ("CRITICAL TRUTH & VERIFICATION RULES")**, all software components, UI views, and telemetry graphs must reflect 100% genuine data. AI agents, design-to-code pipelines, and human developers are **strictly prohibited** from embedding synthetic mock data (e.g. hardcoded sensor readings, static device arrays, synthetic delay loops, and fake API fixtures) in production code.

Every user interface metric must either:
1. Bind directly to physical hardware registers, live WebSocket streams, or authentic REST endpoints.
2. Render an explicit, clean uninitialized waiting state (`--`, `N/A`, `null`, or `<LoadingSkeleton />`) when data is unavailable.

---

## 2. The Zero-Mock Discrimination Axiom

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE ZERO-MOCK DISCRIMINATION AXIOM                                 │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Structure describes HOW data is presented; Mock data manufactures WHAT is presented.             │
│ • If a string or construct defines layout geometry, styling tokens, or static chrome field        │
│   labels ("Heart Rate", "Throughput"), it is PERMISSIBLE STRUCTURAL LAYOUT.                       │
│ • If a string or construct manufactures a metric value ("142 bpm", "0.28ms"), active device count, │
│   or synthetic delay loop (setTimeout) not bound to live hardware, it is FORBIDDEN MOCK DATA.     │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Structural Layout vs. Mock Data Discrimination Rubric

| Construct Category | Concrete Syntax Signature | Classification | Rule #0 Status | Remediation Required |
| :--- | :--- | :--- | :--- | :--- |
| **DOM Hierarchy** | `<div className="card"><section className="grid">` | **Structural Layout** | **PASS 🟢** | None. Preserves layout hierarchy. |
| **Flexbox / Grid Layout** | `display: 'flex', gap: '1rem', gridTemplateColumns: '1fr 1fr'` | **Structural Layout** | **PASS 🟢** | None. Preserves styling tokens. |
| **Design Tokens & Theme** | `color: 'var(--color-primary)', bg: '#0f172a', radius: 12` | **Structural Layout** | **PASS 🟢** | None. Preserves design tokens. |
| **Static Chrome Header** | `<h2>Hardware Telemetry</h2>`, `<th>Heart Rate (BPM)</th>` | **Structural Layout** | **PASS 🟢** | None. Recognized as static UI label. |
| **Dynamic State Binding** | `<span>{device?.vram ?? '--'}</span>`, `Text(val ?? '--')` | **Dynamic Value** | **PASS 🟢** | Standard zero-mock state binding. |
| **Uninitialized State** | `'--'`, `'N/A'`, `null`, `undefined`, `<LoadingSkeleton />` | **Waiting State** | **PASS 🟢** | Clean fallback indicator. |
| **Hardcoded Telemetry String** | `<span>142 bpm</span>`, `<div>0.28ms (DMA)</div>` | **Forbidden Mock Data** | **FAIL 🔴 (ZM-JSX-01)** | Replace with `{props.hr != null ? `${props.hr} bpm` : '--'}`. |
| **Hardcoded Numeric Metric** | `<MetricCard value={142} />`, `latency: 0.28` | **Forbidden Mock Data** | **FAIL 🔴 (ZM-JS-01)** | Replace with dynamic state variable. |
| **In-Source Mock Array** | `const mockNodes = [{ id: '1', status: 'ACTIVE' }];` | **Forbidden Mock Data** | **FAIL 🔴 (ZM-JS-03)** | Initialize empty `[]` and hydrate via REST/WS. |
| **Synthetic Timer Simulation** | `setTimeout(() => setDone(true), 1500)` | **Synthetic Logic** | **FAIL 🔴 (ZM-JS-05)** | Bind to WebSocket `onopen` or HTTP response. |
| **Synthetic Math Multiplier** | `const merged = single_tp * 2.0;`, `const load = raw * 5;` | **Synthetic Math** | **FAIL 🔴 (ZM-PY-02)** | Compute from empirical socket measurements. |
| **Unverified Randomization** | `Math.random() * 100`, `random.randint(60, 120)` | **Synthetic Math** | **FAIL 🔴 (ZM-JS-06)** | Remove random generator; bind to sensor. |
| **Mock Catch Fallback** | `catch (e) { return { status: 'ONLINE', count: 6 }; }` | **Forbidden Mock Data** | **FAIL 🔴 (ZM-PY-04)** | Return explicit `{ status: 'ERROR', data: null }`. |
| **Simulation Comment** | `// Simulating failover transition`, `/* Fake API */` | **Simulation Flag** | **FAIL 🔴 (ZM-COM-05)** | Remove simulation comment; bind real pipeline. |
| **Verified Canvas Animation** | `/* @verified-visual-animation */ Math.random() * 360` | **Visual FX** | **PASS 🟢 (Exempt)** | Allowed for purely decorative visual FX. |

---

## 4. Rule Catalog & Error Identifier Index

```
┌──────────────┬────────────────────────────────────────────────────────┬──────────┐
│ Error ID     │ Rule Name                                              │ Severity │
├──────────────┼────────────────────────────────────────────────────────┼──────────┤
│ ZM-JSX-01    │ Hardcoded Telemetry Literal in JSX / TSX Element       │ CRITICAL │
│ ZM-JS-01     │ Hardcoded Telemetry Property in JS/TS Object Literal   │ CRITICAL │
│ ZM-JS-03     │ Static Mock Array Pre-Marked Active in JavaScript      │ HIGH     │
│ ZM-JS-05     │ Synthetic Async State Transition (setTimeout)          │ CRITICAL │
│ ZM-JS-06     │ Unverified Math.random() in Telemetry / UI Pipeline   │ CRITICAL │
│ ZM-VUE-01    │ Hardcoded Telemetry in Vue Template / Script           │ CRITICAL │
│ ZM-HTML-01   │ Hardcoded Metric in HTML / Jinja Element               │ CRITICAL │
│ ZM-DART-01   │ Hardcoded Telemetry in Flutter Text() Widget           │ CRITICAL │
│ ZM-DART-03   │ Static Mock List of Model Objects in Flutter           │ HIGH     │
│ ZM-DART-05   │ Synthetic Future.delayed State Transition in Flutter   │ CRITICAL │
│ ZM-PY-01     │ Hardcoded Telemetry Literal in Python Dict             │ CRITICAL │
│ ZM-PY-02     │ Synthetic Scaling Multiplier on Telemetry Variable     │ CRITICAL │
│ ZM-PY-04     │ Mock Active Fallback in Python Exception Handler       │ CRITICAL │
│ ZM-PY-06     │ Unverified Random Telemetry Generation in Python       │ CRITICAL │
│ ZM-COM-05    │ Explicit Simulation Comment in Source Code             │ HIGH     │
│ ZM-LEX-04    │ Mock Variable Declaration (mock_data, dummy_devices)   │ CRITICAL │
└──────────────┴────────────────────────────────────────────────────────┴──────────┘
```

---

## 5. End-to-End Workflow: Figma Extraction to Zero-Mock Code

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. FIGMA REST AST EXTRACTION (get_file / get_file_nodes / get_image)        │
│    • Query Figma API via Figma MCP Client (`figma_mcp_client.py`).          │
│    • Extract layoutMode (HORIZONTAL/VERTICAL), padding, gap, typography.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. ZERO-MOCK AST CODE GENERATION                                            │
│    • Map AutoLayout to CSS Flexbox / Tailwind / Flutter Column/Row.         │
│    • Generate dynamic prop interface: `interface ComponentProps { val?: ...}`│
│    • Bind all metric fields to `{telemetry?.field ?? '--'}`.                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. RULE #0 PRE-MERGE AST LINTER GATE (figma_zero_mock_linter.py)            │
│    • Scan code AST: Verify zero hardcoded literals or mock arrays.          │
│    • Exit 0 -> Proceed to Visual Audit. Exit 1 -> Abort & Generate Patch.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. TRI-LENS VISUAL SWARM PARITY AUDIT (figma_tri_lens_auditor.py)           │
│    • Lens 1 (CDP) + Lens 2 (Firefox) + Lens 3 (Android Mobile).             │
│    • Compute 5-Frame MD5 Delta (asserts dynamic rendering).                 │
│    • Compute SSIM Parity >= 0.95 against Figma get_image reference render.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Multi-Language Code Generation Patterns

#### TypeScript / React (TSX):
```tsx
// ✅ CORRECT: Rule #0 Compliant Zero-Mock Component
import React from 'react';

export interface HeartRateCardProps {
  heartRate?: number | null;
  sensorStatus?: 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED';
}

export const HeartRateCard: React.FC<HeartRateCardProps> = ({ heartRate, sensorStatus }) => {
  return (
    <div className="flex flex-col p-4 bg-slate-900 border border-slate-800 rounded-xl">
      <span className="text-xs font-semibold text-slate-400">HEART RATE</span>
      <span className="text-2xl font-bold text-emerald-400">
        {heartRate != null ? `${heartRate} bpm` : '--'}
      </span>
      <span className="text-xs text-slate-500">
        Status: {sensorStatus ?? 'DISCONNECTED'}
      </span>
    </div>
  );
};
```

#### Flutter / Dart:
```dart
// ✅ CORRECT: Rule #0 Compliant Zero-Mock Flutter Widget
import 'package:flutter/material.dart';

class HeartRateCard extends StatelessWidget {
  final int? heartRate;
  final String status;

  const HeartRateCard({Key? key, this.heartRate, this.status = 'DISCONNECTED'}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('HEART RATE', style: TextStyle(color: Colors.grey, fontSize: 12)),
          Text(
            heartRate != null ? '$heartRate bpm' : '--',
            style: const TextStyle(color: Colors.greenAccent, fontSize: 24, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
```

---

## 6. Pre-Merge CI/CD & Git Hook Enforcement

### 6.1 Running the Linter
```bash
# Audit entire monorepo:
python3 06_scripts_and_tooling/scripts/figma_zero_mock_linter.py --target-dir .

# Audit specific staged file:
python3 06_scripts_and_tooling/scripts/figma_zero_mock_linter.py --target-file 01_apps/movesense_hub/src/components/HeartRateCard.tsx

# Generate automated remediation patch:
python3 06_scripts_and_tooling/scripts/figma_zero_mock_linter.py --target-dir . --fix --generate-patch remediation.patch
```

### 6.2 Pre-Commit Hook Integration (`.git/hooks/pre-commit`)
```bash
#!/bin/bash
# Monorepo Rule #0 Zero-Mock Pre-Commit Hook
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(tsx|jsx|vue|html|dart|py)$' | grep -vE '(tests/|test/|\.agents/)')

if [ -n "$STAGED_FILES" ]; then
  for F in $STAGED_FILES; do
    if [ -f "$F" ]; then
      python3 06_scripts_and_tooling/scripts/figma_zero_mock_linter.py --target-file "$F" --fail-under 100.0
      if [ $? -ne 0 ]; then
        echo "❌ Pre-commit failed: Rule #0 Zero-Mock violation detected in $F"
        exit 1
      fi
    fi
  done
fi
exit 0
```

---

## 7. Tri-Lens Visual Swarm Verification

To verify visual parity and dynamic rendering:
```bash
# Execute Tri-Lens audit against live dashboard:
python3 06_scripts_and_tooling/scripts/figma_tri_lens_auditor.py \
  --url http://localhost:4000/telemetry \
  --figma-image /path/to/figma_reference.png \
  --lens all \
  --frames 5 \
  --min-ssim 0.95
```

### Pass Criteria:
1. **SSIM Parity**: Structural similarity score $\ge 0.95$ relative to Figma reference rendering.
2. **5-Frame Delta**: $\text{len}(\text{unique}(\text{hashes})) == 5$ proving active dynamic rendering.
3. **DOM Zero-Mock**: Zero hardcoded telemetry strings found in the live DOM/AX tree snapshot.

---

## 8. Troubleshooting & Remediation

| Issue | Root Cause | Remediation Procedure |
| :--- | :--- | :--- |
| `ZM-JSX-01` on static metric | Developer copied Figma text frame literal directly into JSX. | Replace literal with `{telemetry?.val ?? '--'}`. Run linter with `--fix`. |
| `ZM-JS-03` on initial state | State array initialized with mock objects for visual testing. | Initialize with `useState<Device[]>([])` and hydrate from API. |
| `ZM-JS-05` in button handler | Synthetic `setTimeout` used to fake async network latency. | Call genuine backend endpoint via `fetch()` or WebSocket action. |
| `HTTP 401 Unauthorized` in Figma MCP | Missing or expired `FIGMA_ACCESS_TOKEN`. | Run `python3 setup_figma_mcp.py --auth-token <TOKEN>` to update settings. |
| Low SSIM Score (< 0.95) | Layout flexbox gaps or font family padding misaligned with Figma. | Extract exact AutoLayout padding and gap values via `figma_mcp_client.py get-nodes`. |

---
*Certified by Lauburu Swarm Architecture Board under Rule #0 Data Authenticity Standard.*
