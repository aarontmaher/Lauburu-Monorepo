# Endurance Biometrics Application Specification: ECG, DFA-alpha1 & Zone 2 Telemetry

**Target Subsystem**: `01_apps/zone2_endurance`  
**Monorepo Subsystem Spec**: `spec-01-apps-ecosystem` & `spec-03-biometrics-dsp`  
**Author**: Explorer 2 (Biometrics Domain Investigator)  
**Date**: August 26, 2026  
**Status**: APPROVED SPECIFICATION  

---

## 1. Executive Summary & Physiological Foundations

The **Zone 2 Endurance Biometrics Application** is an athlete-facing, medical-grade telemetry platform designed to identify and sustain the **aerobic base training zone (Zone 2)** in real time. Unlike traditional static heart rate percentage models (e.g., 60-70% of $HR_{\max}$) which fail to account for daily autonomic fatigue, cardiac drift, or individual metabolic variability, this application relies on **continuous biological feedback**:
1. **128Hz Raw Electrocardiography (ECG)**: Continuous P-Q-R-S-T wave acquisition, real-time R-peak detection, and beat-to-beat (RR) interval extraction.
2. **Detrended Fluctuation Analysis (DFA-alpha1 / $\alpha_1$)**: Dynamic fractal correlation properties of heart rate variability (HRV) that directly index the **First Aerobic Threshold ($LT_1 / VT_1$) at $\alpha_1 = 0.75$** and the **Second Anaerobic Threshold ($LT_2 / VT_2$) at $\alpha_1 = 0.50$** (Gronwald et al., 2020; Rogers et al., 2021).
3. **Aerobic Decoupling ($Pw:HR$ / $Pace:HR$ Drift)**: Real-time efficiency factor tracking to detect cardiac drift and neuromuscular/metabolic fatigue during prolonged endurance bouts.

The user interface is engineered with **Next.js App Router**, leveraging **React Server Components (RSC)** for structural shells, navigation, and static metadata, while strictly isolating **Client Components (`"use client"`)** for 60 FPS Canvas ECG rendering, dynamic SVG DFA-alpha1 trend charting, and low-latency WebSocket/Web-Bluetooth data feeds.

---

## 2. Electrocardiography (ECG) Specification

### 2.1 Waveform Morphology & Sampling Standards
- **Sensor Ingestion**: Movesense Medical single-lead ECG strap / bicep module.
- **Sampling Frequency ($F_s$)**: $128\text{ Hz}$ (128 samples per second, $\Delta t = 7.8125\text{ ms}$).
- **Nominal Amplitude Range**: $-1.5\text{ mV}$ to $+2.5\text{ mV}$ (dynamic range $4.0\text{ mV}$).
- **Standard Medical Calibration Grid**:
  - Horizontal Time Base: $25\text{ mm/s}$ ($1\text{ mm} = 0.04\text{ s} / 40\text{ ms}$; $5\text{ mm large box} = 0.20\text{ s} / 200\text{ ms}$).
  - Vertical Voltage Scale: $10\text{ mm/mV}$ ($1\text{ mm small box} = 0.1\text{ mV}$; $5\text{ mm large box} = 0.5\text{ mV}$).
- **Electrophysiological Components**:
  - **P Wave**: Atrial depolarization (duration 80–100 ms, amplitude < 0.25 mV).
  - **PR Interval**: Atrioventricular conduction delay (duration 120–200 ms).
  - **QRS Complex**: Ventricular depolarization (duration 80–120 ms, dominant R-spike 1.0–2.2 mV).
  - **ST Segment**: Isoelectric plateau before repolarization (duration 80–120 ms).
  - **T Wave**: Ventricular repolarization (duration ~160 ms, amplitude 0.1–0.5 mV).

```
        R-Peak (~1.5 to 2.2 mV)
          /\
         /  \
        /    \
  P    /      \        T
 _/\__/  Q     \__S___/\_
   |     |      |       |
   |<--->|      |<----->|
   PR Int       ST Seg
```

### 2.2 60 FPS Real-Time Canvas Rendering Architecture
To prevent React re-render thrashing from 128Hz sample packets, ECG visualization MUST use an isolated HTML5 `<canvas>` element driven by a decoupled circular ring buffer and `requestAnimationFrame`:

1. **Circular Ring Buffer**:
   - Size: 640 points (5.0 seconds of history at 128 Hz).
   - Float32Array memory structure to prevent garbage collection pauses.
2. **Rendering Modes**:
   - **Oscilloscope Sweep Bar Mode (Recommended)**: A vertical cursor moves horizontally across the canvas at $25\text{ mm/s}$, clearing a 10px erase gap in front of the active drawing head. This mimics medical bedside patient monitors with zero redraw stutter.
   - **Continuous Scrolling Strip-Chart Mode (Alternative)**: Canvas translates leftward each frame, drawing new incoming points on the right edge.
3. **High-DPI Scaling**:
   - Automatically adapt canvas width/height to `window.devicePixelRatio` (e.g. 2x on Retina/OLED displays) to maintain crisp 1px ECG tracing.
4. **Grid Background**:
   - Drawn on a static background canvas layer or CSS grid with standard pink/gray major ($5\text{mm}$) and minor ($1\text{mm}$) gridlines to avoid redrawing grid on every animation frame.

### 2.3 Lead Status & Signal Quality State Machine
The UI must continuously reflect electrode contact impedance and signal fidelity:

| Lead Status Enum | Condition | UI Visual Representation | Accessible Audio/Aria |
| :--- | :--- | :--- | :--- |
| `OPTIMAL` | Signal-to-Noise Ratio (SNR) > 18 dB, baseline wander < 0.2 mV | Solid Green Badge (`bg-emerald-500/10 text-emerald-400`), Crisp Waveform | `aria-label="ECG signal optimal"` |
| `NOISY_MOTION` | High-frequency EMG artifact or baseline drift > 0.5 mV | Amber Warning Badge (`bg-amber-500/10 text-amber-400`), "Motion Artifact" | `aria-label="ECG signal noisy, check sensor fit"` |
| `POOR_CONTACT` | High impedance, intermittent sample drops | Orange Warning Badge (`bg-orange-500/10 text-orange-400`), "Dry Electrodes" | `aria-label="Poor electrode contact, moisten strap"` |
| `LEAD_OFF` | Disconnected lead / flatline / zero amplitude | Flashing Rose Badge (`bg-rose-500/20 text-rose-400 animate-pulse`), Flatline indicator | `aria-label="ECG lead disconnected"` |
| `DISCONNECTED` | Bluetooth / WebSocket connection closed | Gray Neutral Badge (`bg-slate-500/10 text-slate-400`), Dashed line `--` | `aria-label="Sensor disconnected"` |

---

## 3. Detrended Fluctuation Analysis (DFA-alpha1) Specification

### 3.1 Exercise Physiology & Threshold Mapping
Heart Rate Variability (HRV) non-linear dynamics change fundamentally as exercise intensity transitions from aerobic to anaerobic metabolism. **Detrended Fluctuation Analysis (DFA)** measures the short-term fractal self-similarity of consecutive $RR$ interval time series ($4 \le n \le 16$ beats):

$$\alpha_1 = \frac{\Delta \log F(s)}{\Delta \log s}$$

| DFA $\alpha_1$ Range | Physiological State | Training Zone | Metabolic Mechanism | UI Theme Accent |
| :--- | :--- | :--- | :--- | :--- |
| $\alpha_1 > 1.00$ | Rest / Active Recovery | **Zone 1** (Recovery) | Strong parasympathetic modulation, high autonomic correlation | Blue / Cyan (`#06b6d4`) |
| **$0.75 \le \alpha_1 \le 1.00$** | **Aerobic Threshold ($LT_1 / VT_1$)** | **Zone 2** (Aerobic Base) | **Optimal lipid oxidation (FatMax)**, minimal lactate accumulation (< 2.0 mmol/L) | **Emerald Green (`#10b981`)** |
| $0.50 \le \alpha_1 < 0.75$ | Tempo / Aerobic Power | **Zone 3** (Tempo) | Carbohydrate oxidation accelerates, blood lactate 2.0–4.0 mmol/L | Amber (`#f59e0b`) |
| $\alpha_1 < 0.50$ | **Anaerobic Threshold ($LT_2 / VT_2$)** | **Zone 4 / 5** (Anaerobic) | Severe metabolic acidosis, hyperventilation, white-noise stochastic RR | Crimson / Rose (`#f43f5e`) |

```
DFA alpha-1 Value
1.40 ──┐  ZONE 1: Active Recovery (Parasympathetic Dominant)
1.20   │
1.00 ──┴──────────────────────────────────────────────────────
       ▲
0.90   │  ZONE 2: Aerobic Base / FatMax (Optimal Lipid Oxidation)
0.80   │
0.75 ──┼── [AEROBIC THRESHOLD LT1] ──────────────────────────
       ▼
0.65   │  ZONE 3: Tempo / Aerobic Power
0.50 ──┼── [ANAEROBIC THRESHOLD LT2] ────────────────────────
       ▼  ZONE 4/5: Threshold & VO2max (Metabolic Acidosis)
0.40 ──┘
```

### 3.2 Rolling Window Computation & Kamath 2004 Artifact Filter
To calculate valid, noise-resilient $\alpha_1$ values during active motion:
1. **Kamath et al. (2004) 20% Clinical RR Filter**:
   - Any beat deviating by $> 20\%$ from the preceding beat is flagged as ectopic or motion artifact and replaced via linear interpolation:
     $$\frac{|RR_i - RR_{i-1}|}{RR_{i-1}} \le 0.20$$
2. **Rolling Window Duration**:
   - Window size: $120\text{ seconds}$ (approximately $120\text{ to }240\text{ beats}$ at exercise heart rates).
   - Recalculation cadence: Step update every $5\text{ seconds}$.
3. **Artifact Threshold Gate**:
   - If artifact percentage in a 120s window exceeds $5\%$, the UI displays a `"Low Confidence — High Motion"` badge and dims the $\alpha_1$ gauge.

### 3.3 Visual Trend Charting Specifications
- **Chart Type**: Multi-zone area line chart with shaded horizontal threshold corridors.
- **Visual Threshold Guides**:
  - Horizontal reference dashed line at $\alpha_1 = 0.75$ labeled `"LT1 (Aerobic)"`.
  - Horizontal reference dashed line at $\alpha_1 = 0.50$ labeled `"LT2 (Anaerobic)"`.
  - Shaded green corridor spanning $[0.75, 1.00]$ with subtle pulsing highlight when active $\alpha_1$ is inside Zone 2.
- **Interactive Capabilities**: Tooltip on hover/touch displaying:
  - Timestamp (Elapsed Workout Time: `MM:SS` or `HH:MM:SS`)
  - Instantaneous $\alpha_1$ and 2-min smoothed $\alpha_1$
  - Heart Rate ($BPM$) and $RR_{mean}$ ($ms$)
  - Current Active Zone.

---

## 4. Zone 2 Endurance & Decoupling Metrics

### 4.1 Aerobic Decoupling ($Pw:HR$ / $Pace:HR$ Drift)
Aerobic decoupling measures physiological drift during steady-state aerobic efforts. As muscle glycogen depletes, core temperature rises, or autonomic fatigue accumulates, heart rate drifts upward while mechanical output remains constant.

1. **Efficiency Factor ($EF$)**:
   $$EF = \frac{\text{Mechanical Power (Watts) or Speed (m/s)}}{\text{Heart Rate (BPM)}}$$
2. **Decoupling Percentage ($Decoupling\%$)**:
   - Splits a continuous Zone 2 workout session into two equal duration halves (First Half $H_1$, Second Half $H_2$):
   $$Decoupling = \left( \frac{EF_1 - EF_2}{EF_1} \right) \times 100\%$$
3. **Clinical Interpretation**:
   - $< 3.5\%$: Superior aerobic base endurance; zero cardiac drift.
   - $3.5\% - 5.0\%$: Standard optimal Zone 2 decoupling; workout can continue.
   - $> 5.0\%$: Aerobic decoupling detected; athlete is fatiguing out of true lipid metabolism.
   - $> 10.0\%$: Severe cardiac drift; app issues audio/visual recommendation to wind down workout.

### 4.2 Time-in-Zone Accumulator
- Continuous counter tracking seconds spent in:
  - `Zone 1 (Recovery)`
  - `Zone 2 (Target Aerobic)`
  - `Zone 3 (Tempo)`
  - `Zone 4/5 (Anaerobic / VO2max)`
- Summary donut / progress bar showing **Zone 2 Compliance Ratio**:
  $$\text{Zone 2 Compliance} = \frac{T_{\text{Zone 2}}}{T_{\text{Total}}} \times 100\%$$

---

## 5. Next.js App Router Architecture & Hybrid Rendering Boundaries

### 5.1 Server vs Client Demarcation Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│ React Server Component (RSC) Root Shell (app/layout.tsx)               │
│ - Global Header, Navigation Bar, Dark/Light Mode Theme Provider        │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ RSC Page Layout (app/page.tsx)                                     │ │
│ │ - Static Metric Grid Headers, Session Metadata, Accessibility Tree │ │
│ │                                                                    │ │
│ │ ┌────────────────────────────────────────────────────────────────┐ │ │
│ │ │ Client Component Boundary ("use client")                       │ │ │
│ │ │ <TelemetryProvider> (Web Bluetooth & WebSocket State)          │ │ │
│ │ │                                                                │ │ │
│ │ │ ┌───────────────────────────┐ ┌──────────────────────────────┐ │ │ │
│ │ │ │ <LiveEcgMonitor />        │ │ │ <DfaAlpha1TrendChart />    │ │ │ │
│ │ │ │ - 60 FPS Canvas Sweep     │ │ │ - Dynamic SVG Zone Overlay │ │ │ │
│ │ │ │ - 128Hz Ring Buffer       │ │ │ - 120s Rolling Calculation │ │ │ │
│ │ │ └───────────────────────────┘ └──────────────────────────────┘ │ │ │
│ │ │ ┌───────────────────────────┐ ┌──────────────────────────────┐ │ │ │
│ │ │ │ <ZoneGauge />             │ │ │ <AerobicDecouplingCard />  │ │ │ │
│ │ │ │ - Dynamic Radial Scale    │ │ │ - Pw:HR Drift Calculator   │ │ │ │
│ │ │ └───────────────────────────┘ └──────────────────────────────┘ │ │ │
│ │ └────────────────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

| Component | Boundary | Justification |
| :--- | :--- | :--- |
| `app/layout.tsx` | **Server (RSC)** | Root HTML/body, font optimization, static metadata, theme wrapper |
| `app/page.tsx` | **Server (RSC)** | Dashboard grid container, static section titles, SEO/OpenGraph tags |
| `app/history/page.tsx` | **Server (RSC)** | Workout history table rendered on server from persistent DB/file store |
| `app/settings/page.tsx` | **Server (RSC)** | User threshold profiles, sensor MAC address configurations |
| `components/telemetry/TelemetryProvider.tsx` | **Client (`"use client"`)** | Web Bluetooth GATT API, WebSocket channels, browser lifecycle listeners |
| `components/biometrics/LiveEcgMonitor.tsx` | **Client (`"use client"`)** | HTML5 `<canvas>` rendering loop at 60 FPS, high-frequency requestAnimationFrame |
| `components/biometrics/DfaAlpha1TrendChart.tsx`| **Client (`"use client"`)** | Dynamic SVG rendering, user interactions, hover tooltips, live point streaming |
| `components/biometrics/ZoneGauge.tsx` | **Client (`"use client"`)** | Animated radial gauge showing current instantaneous DFA $\alpha_1$ vs HR zone |
| `components/biometrics/AerobicDecouplingCard.tsx` | **Client (`"use client"`)** | Split-half efficiency calculator updating every 10 seconds |
| `components/biometrics/MetricsSummaryGrid.tsx` | **Client (`"use client"`)** | Live numerical KPI tiles ($HR$, $RR_{mean}$, $RMSSD$, $SDNN$, $TimeInZone$) |
| `components/ui/ThemeToggle.tsx` | **Client (`"use client"`)** | Browser `localStorage` reading/writing and DOM class toggling |

---

## 6. TypeScript Data Contracts & Interfaces

The following TypeScript definitions govern the telemetry stream, biometrics processing pipeline, and UI component props:

```typescript
/**
 * Core Telemetry & Biometrics Type Definitions
 * File: 01_apps/zone2_endurance/src/types/biometrics.ts
 */

export type LeadStatus = 'OPTIMAL' | 'NOISY_MOTION' | 'POOR_CONTACT' | 'LEAD_OFF' | 'DISCONNECTED';

export type TrainingZoneId = 'ZONE_1' | 'ZONE_2' | 'ZONE_3' | 'ZONE_4_5';

export interface TrainingZoneInfo {
  id: TrainingZoneId;
  name: string;
  shortLabel: string;
  description: string;
  minDfaAlpha1: number;
  maxDfaAlpha1: number;
  targetHrMin?: number;
  targetHrMax?: number;
  colorClass: string;
  hexColor: string;
}

export interface EcgSample {
  timestampMs: number;
  voltageMv: number;
  sampleIndex: number;
}

export interface EcgFrame {
  samples: number[];        // 128Hz voltage values in millivolts (mV)
  samplingRateHz: number;   // 128
  leadStatus: LeadStatus;
  packetSequence: number;
  timestampEpochMs: number;
}

export interface RrIntervalPoint {
  timestampEpochMs: number;
  rrIntervalMs: number;     // Raw beat-to-beat interval (300ms - 2000ms)
  isFilteredOut: boolean;   // True if rejected by Kamath 20% filter
}

export interface HrvMetrics {
  heartRateBpm: number;
  instantaneousRrMs: number;
  meanRrMs: number;
  rmssdMs: number;          // Root Mean Square of Successive Differences
  sdnnMs: number;           // Standard Deviation of NN intervals
  pnn50Percent: number;     // Percentage of successive intervals > 50ms
  artifactPercentage: number;
}

export interface DfaAlpha1Point {
  elapsedSeconds: number;
  timestampEpochMs: number;
  alpha1Value: number;      // e.g. 0.82
  alpha1Smoothed: number;    // 3-point rolling average
  windowDurationSeconds: number; // 120
  activeZone: TrainingZoneId;
  heartRateBpm: number;
}

export interface AerobicDecouplingMetrics {
  firstHalfAvgHrBpm: number;
  firstHalfEfficiencyFactor: number;
  secondHalfAvgHrBpm: number;
  secondHalfEfficiencyFactor: number;
  decouplingPercentage: number; // e.g. +3.2%
  isDecoupled: boolean;         // True if > 5.0%
}

export interface ZoneDurationSummary {
  zone1Seconds: number;
  zone2Seconds: number;
  zone3Seconds: number;
  zone45Seconds: number;
  totalWorkoutSeconds: number;
  zone2ComplianceRatio: number; // 0.0 - 1.0 (e.g. 0.84 = 84%)
}

export interface TelemetryStreamPacket {
  sessionId: string;
  timestampUtc: string;
  connectionState: 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';
  sensorId: string;
  batteryLevelPercent: number | null;
  ecg: EcgFrame;
  hrv: HrvMetrics;
  dfa: DfaAlpha1Point | null;
  decoupling: AerobicDecouplingMetrics | null;
  durations: ZoneDurationSummary;
}

// -------------------------------------------------------------------------
// Component Props Interfaces
// -------------------------------------------------------------------------

export interface LiveEcgMonitorProps {
  ecgSamples: number[];
  leadStatus: LeadStatus;
  samplingRateHz?: number;
  timeWindowSeconds?: number; // Default: 5.0
  heightPx?: number;          // Default: 200
  showGrid?: boolean;
  className?: string;
}

export interface DfaAlpha1TrendChartProps {
  history: DfaAlpha1Point[];
  currentAlpha1: number | null;
  targetThresholdLow?: number;  // Default: 0.75 (LT1)
  targetThresholdHigh?: number; // Default: 1.00
  anaerobicThreshold?: number;  // Default: 0.50 (LT2)
  heightPx?: number;            // Default: 280
  className?: string;
}

export interface ZoneGaugeProps {
  currentAlpha1: number | null;
  currentHrBpm: number | null;
  activeZone: TrainingZoneId;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export interface MetricsSummaryGridProps {
  hrvMetrics: HrvMetrics | null;
  dfaPoint: DfaAlpha1Point | null;
  durations: ZoneDurationSummary | null;
  leadStatus: LeadStatus;
  className?: string;
}

export interface AerobicDecouplingCardProps {
  metrics: AerobicDecouplingMetrics | null;
  elapsedSeconds: number;
  className?: string;
}
```

---

## 7. Visual Design, Theming & Accessibility (a11y) Standards

### 7.1 Tailwind CSS Theme Palette (Dark / Light Mode)

The UI must enforce high contrast ratios ($\ge 4.5:1$ for normal text, $\ge 3:1$ for large text and UI components) conforming to **WCAG 2.2 AA**:

| UI Element | Dark Mode Token (`dark:`) | Light Mode Token | Color Hex (Approx) | Contrast Ratio |
| :--- | :--- | :--- | :--- | :--- |
| **Page Background** | `bg-slate-950` (`#020617`) | `bg-slate-50` (`#f8fafc`) | `#020617` / `#f8fafc` | $\ge 15:1$ |
| **Card Surface** | `bg-slate-900/80 border-slate-800` | `bg-white border-slate-200 shadow-sm` | `#0f172a` / `#ffffff` | $\ge 12:1$ |
| **Primary Text** | `text-slate-100` (`#f1f5f9`) | `text-slate-900` (`#0f172a`) | `#f1f5f9` / `#0f172a` | $\ge 14:1$ |
| **Muted Text** | `text-slate-400` (`#94a3b8`) | `text-slate-500` (`#64748b`) | `#94a3b8` / `#64748b` | $\ge 4.8:1$ |
| **ECG Waveform Trace** | `text-emerald-400` (`#34d399`) | `text-emerald-600` (`#059669`) | `#34d399` / `#059669` | High Contrast |
| **ECG Grid Background**| `border-emerald-500/10` | `border-emerald-600/15` | Subtly visible | $\ge 3:1$ |
| **Zone 1 (Recovery)** | `text-cyan-400 bg-cyan-500/10` | `text-cyan-700 bg-cyan-50` | `#22d3ee` / `#0e7490` | $\ge 4.5:1$ |
| **Zone 2 (Aerobic Base)**| `text-emerald-400 bg-emerald-500/10`| `text-emerald-700 bg-emerald-50`| `#34d399` / `#047857`| $\ge 4.5:1$ |
| **Zone 3 (Tempo)** | `text-amber-400 bg-amber-500/10`| `text-amber-700 bg-amber-50`| `#fbbf24` / `#b45309` | $\ge 4.5:1$ |
| **Zone 4/5 (Anaerobic)**| `text-rose-400 bg-rose-500/10` | `text-rose-700 bg-rose-50` | `#fb7185` / `#be123c` | $\ge 4.5:1$ |

### 7.2 Strict Accessibility (a11y) Implementation Rules
1. **ARIA Live Regions**:
   - Rapidly changing numerical values ($HR$, $DFA \alpha_1$, $Zone$) MUST use `aria-live="polite"` and `aria-atomic="true"` on their parent containers so screen readers announce transitions without flooding the audio queue.
2. **Text Equivalents for Graphical Data**:
   - The `<canvas>` ECG element MUST contain fallback semantic markup:
     ```html
     <canvas role="img" aria-label="Real-time ECG waveform showing normal sinus rhythm at 134 BPM, Lead status: Optimal.">
       <p>Real-time ECG stream active. Heart rate: 134 BPM.</p>
     </canvas>
     ```
   - The DFA-alpha1 chart MUST have a screen-reader summary table or live text status:
     ```html
     <div class="sr-only" aria-live="polite">
       Current DFA alpha-1 is 0.84, in Zone 2 Aerobic Base. Time in Zone 2: 34 minutes 12 seconds.
     </div>
     ```
3. **Keyboard Navigability**:
   - All modal toggles, Bluetooth connection buttons, chart time-window selectors (e.g., `5m`, `15m`, `Session`), and theme switches MUST be reachable via `Tab` and activatable via `Enter` / `Space`.
   - Focus rings MUST use high-visibility styles (`focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none`).
4. **Colorblind-Safe Indicator Redundancy**:
   - Never rely on color alone to indicate training zones. Always pair colors with distinct textual labels (`"ZONE 2 - AEROBIC BASE"`, `"ZONE 1 - RECOVERY"`), icon glyphs, and numeric range indicators.

---

## 8. Verification & Implementation Blueprint

### 8.1 Verification Criteria
1. **RSC / Client Boundary Check**: Verify `app/layout.tsx` and `app/page.tsx` have NO `"use client"` directive, while `LiveEcgMonitor.tsx` and `DfaAlpha1TrendChart.tsx` have `"use client"` at line 1.
2. **60 FPS ECG Smoothness**: Confirm continuous canvas animation loop without DOM layout thrashing.
3. **DFA Threshold Compliance**: Verify visual corridor highlighting triggers when $\alpha_1 \in [0.75, 1.00]$.
4. **Accessible Keyboard & Contrast Audit**: Validate against Axe / Chrome DevTools a11y scoring $\ge 98\%$.
5. **Zero-Mock Telemetry**: Verify disconnected state cleanly displays `"--"` and `"Awaiting physical sensor"` without simulated fake data.

