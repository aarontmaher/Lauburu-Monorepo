import React from "react";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { Zone2StatusBadge } from "@/components/dashboard/Zone2StatusBadge";
import { LiveEcgMonitor } from "@/components/charts/LiveEcgMonitor";
import { DfaAlpha1TrendChart } from "@/components/charts/DfaAlpha1TrendChart";
import { DfaAlpha1Point } from "@/types/biometrics";
import { Activity, ShieldCheck, HeartPulse } from "lucide-react";

// Baseline steady-state telemetry history data points for initial session view
const initialHistory: DfaAlpha1Point[] = [
  { timestamp: Date.now() - 600000, alpha1: 1.08, heartRate: 118, power: 140, artifactPercentage: 0.8, zone: "ZONE_1" },
  { timestamp: Date.now() - 540000, alpha1: 1.02, heartRate: 122, power: 155, artifactPercentage: 1.0, zone: "ZONE_1" },
  { timestamp: Date.now() - 480000, alpha1: 0.94, heartRate: 130, power: 170, artifactPercentage: 0.6, zone: "ZONE_2" },
  { timestamp: Date.now() - 420000, alpha1: 0.89, heartRate: 134, power: 175, artifactPercentage: 1.2, zone: "ZONE_2" },
  { timestamp: Date.now() - 360000, alpha1: 0.86, heartRate: 137, power: 180, artifactPercentage: 0.9, zone: "ZONE_2" },
  { timestamp: Date.now() - 300000, alpha1: 0.84, heartRate: 138, power: 180, artifactPercentage: 1.1, zone: "ZONE_2" },
  { timestamp: Date.now() - 240000, alpha1: 0.85, heartRate: 138, power: 180, artifactPercentage: 0.7, zone: "ZONE_2" },
  { timestamp: Date.now() - 180000, alpha1: 0.82, heartRate: 139, power: 180, artifactPercentage: 1.4, zone: "ZONE_2" },
  { timestamp: Date.now() - 120000, alpha1: 0.81, heartRate: 140, power: 180, artifactPercentage: 1.0, zone: "ZONE_2" },
  { timestamp: Date.now() - 60000, alpha1: 0.84, heartRate: 138, power: 180, artifactPercentage: 0.8, zone: "ZONE_2" },
  { timestamp: Date.now(), alpha1: 0.85, heartRate: 138, power: 180, artifactPercentage: 0.9, zone: "ZONE_2" },
];

export default function HomePage() {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6 focus:outline-none"
    >
      {/* Top Banner & Active Zone Status */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Endurance Biometrics Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time DFA-&alpha;<sub>1</sub> fractal correlation &amp; 128Hz single-lead electrocardiography telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Zone2StatusBadge zone="ZONE_2" alpha1={0.85} />
        </div>
      </div>

      {/* Summary KPI Cards (RSC) */}
      <section aria-labelledby="kpi-summary-heading">
        <h2 id="kpi-summary-heading" className="sr-only">
          Session Summary KPIs
        </h2>
        <SummaryCards
          summary={{
            heartRate: 138,
            currentDfaAlpha1: 0.85,
            currentZone: "ZONE_2",
            zone2DurationSeconds: 2220,
            totalDurationSeconds: 2700,
            aerobicDecouplingPercent: 3.2,
            avgHeartRate: 136,
            maxHeartRate: 148,
            leadStatus: "CONNECTED",
          }}
          decoupling={{
            decouplingPercentage: 3.2,
            isDecoupled: false,
            firstHalfAvgHr: 135,
            secondHalfAvgHr: 138,
          }}
        />
      </section>

      {/* Biometric Visualizers Grid (Client Components) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Live 128Hz Canvas ECG Monitor */}
        <section aria-labelledby="ecg-monitor-heading" className="w-full">
          <h2 id="ecg-monitor-heading" className="sr-only">
            Live ECG Waveform Monitor
          </h2>
          <LiveEcgMonitor
            ecgSamples={[]}
            leadStatus="CONNECTED"
            samplingRateHz={128}
            heartRate={138}
            heightPx={240}
          />
        </section>

        {/* DFA-alpha1 Fractal Trend Chart */}
        <section aria-labelledby="dfa-chart-heading" className="w-full">
          <h2 id="dfa-chart-heading" className="sr-only">
            DFA Alpha-1 Trend and Zone 2 Corridor Chart
          </h2>
          <DfaAlpha1TrendChart
            history={initialHistory}
            currentAlpha1={0.85}
            leadStatus="CONNECTED"
            heightPx={240}
          />
        </section>
      </div>
    </main>
  );
}
