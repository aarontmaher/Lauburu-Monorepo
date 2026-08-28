import React from "react";
import {
  Heart,
  Activity,
  Timer,
  TrendingUp,
  Radio,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  WifiOff,
} from "lucide-react";
import {
  BiometricSummary,
  AerobicDecouplingMetrics,
  LeadStatus,
  BIOMETRIC_THRESHOLDS,
  classifyDfaZone,
  getZoneMetadata,
} from "@/types/biometrics";
import { Zone2StatusBadge } from "./Zone2StatusBadge";

export interface SummaryCardsProps {
  summary?: Partial<BiometricSummary>;
  decoupling?: Partial<AerobicDecouplingMetrics>;
  leadStatus?: LeadStatus;
  restingHrReference?: number;
  maxHrReference?: number;
  className?: string;
}

/**
 * Helper to format seconds into HH:MM:SS format
 */
export function formatDuration(totalSeconds?: number): string {
  if (typeof totalSeconds !== "number" || isNaN(totalSeconds) || totalSeconds < 0) {
    return "--:--:--";
  }
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

/**
 * Helper to render lead status badge metadata
 */
function getLeadStatusDetails(status?: LeadStatus) {
  switch (status) {
    case "CONNECTED":
      return {
        label: "Optimal Lead II",
        description: "Optimal skin-electrode contact at 128Hz",
        badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
        icon: CheckCircle2,
      };
    case "NOISY":
      return {
        label: "Signal Noisy",
        description: "Electromyographic motion artifact detected",
        badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
        icon: AlertTriangle,
      };
    case "POOR_CONTACT":
      return {
        label: "Poor Contact",
        description: "High electrode impedance; adjust strap tension",
        badgeClass: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30",
        icon: AlertTriangle,
      };
    case "OFF_BODY":
      return {
        label: "Sensor Off Body",
        description: "Chest strap removed or unfastened",
        badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30",
        icon: XCircle,
      };
    case "DISCONNECTED":
    default:
      return {
        label: "Disconnected",
        description: "Movesense BLE sensor offline",
        badgeClass: "bg-muted text-muted-foreground border-border",
        icon: WifiOff,
      };
  }
}

/**
 * Pure React Server Component (RSC): SummaryCards
 * Renders real-time workout summary metric cards:
 * 1. Current Heart Rate (BPM) with resting/max reference
 * 2. DFA-alpha1 ($0.75 - 1.00$ target indicator)
 * 3. Zone 2 Time Accumulator (HH:MM:SS)
 * 4. Aerobic Decoupling (Pw:HR drift %)
 * 5. Movesense Lead Quality Status indicator badge
 */
export function SummaryCards({
  summary = {
    heartRate: 138,
    currentDfaAlpha1: 0.85,
    currentZone: "ZONE_2",
    zone2DurationSeconds: 2220,
    totalDurationSeconds: 2700,
    aerobicDecouplingPercent: 3.2,
    avgHeartRate: 136,
    maxHeartRate: 148,
    leadStatus: "CONNECTED",
  },
  decoupling,
  leadStatus: explicitLeadStatus,
  restingHrReference = 54,
  maxHrReference = 185,
  className = "",
}: SummaryCardsProps) {
  const currentLeadStatus = explicitLeadStatus ?? summary?.leadStatus ?? "DISCONNECTED";
  const isConnected = currentLeadStatus === "CONNECTED" || currentLeadStatus === "NOISY" || currentLeadStatus === "POOR_CONTACT";
  
  const leadDetails = getLeadStatusDetails(currentLeadStatus);
  const LeadIcon = leadDetails.icon;

  const heartRate = isConnected && typeof summary?.heartRate === "number" ? summary.heartRate : null;
  const avgHeartRate = isConnected && typeof summary?.avgHeartRate === "number" ? summary.avgHeartRate : null;
  const maxHeartRate = isConnected && typeof summary?.maxHeartRate === "number" ? summary.maxHeartRate : maxHrReference;

  const dfaAlpha1 = isConnected && typeof summary?.currentDfaAlpha1 === "number" ? summary.currentDfaAlpha1 : null;
  const zone = dfaAlpha1 !== null ? classifyDfaZone(dfaAlpha1) : (summary?.currentZone ?? null);
  const zoneMeta = zone ? getZoneMetadata(zone) : null;

  const zone2Seconds = summary?.zone2DurationSeconds ?? 0;
  const totalSeconds = summary?.totalDurationSeconds ?? 0;
  const zone2Ratio = totalSeconds > 0 ? Math.round((zone2Seconds / totalSeconds) * 100) : 0;

  const decouplingPct = typeof decoupling?.decouplingPercentage === "number"
    ? decoupling.decouplingPercentage
    : (typeof summary?.aerobicDecouplingPercent === "number" ? summary.aerobicDecouplingPercent : null);

  const isDecoupled = decoupling?.isDecoupled ?? (decouplingPct !== null && Math.abs(decouplingPct) > BIOMETRIC_THRESHOLDS.DECOUPLING_DRIFT_THRESHOLD_PCT);

  return (
    <section
      role="region"
      aria-label="Biometric Summary Metrics"
      className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 ${className}`.trim()}
    >
      {/* 1. Current Heart Rate Card */}
      <div
        role="article"
        aria-label={`Current Heart Rate: ${heartRate ? `${heartRate} BPM` : "No Signal"}`}
        className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Heart Rate
          </span>
          <div className="p-1.5 rounded-md bg-rose-500/10 text-rose-600 dark:text-rose-400">
            <Heart className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
              {heartRate !== null ? heartRate : "--"}
            </span>
            <span className="text-xs font-medium text-muted-foreground uppercase">
              BPM
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1 flex items-center justify-between">
            <span>Rest: <strong className="text-foreground font-mono">{restingHrReference}</strong></span>
            <span>Avg: <strong className="text-foreground font-mono">{avgHeartRate ?? "--"}</strong></span>
            <span>Max: <strong className="text-foreground font-mono">{maxHeartRate ?? "--"}</strong></span>
          </p>
        </div>
      </div>

      {/* 2. DFA-alpha1 Fractal Scaling Card */}
      <div
        role="article"
        aria-label={`DFA Alpha 1: ${dfaAlpha1 !== null ? dfaAlpha1.toFixed(2) : "No Signal"}, ${zoneMeta ? zoneMeta.label : "Target Corridor 0.75 - 1.00"}`}
        className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            DFA-&alpha;1 Fractal
          </span>
          <div className="p-1.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Activity className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
              {dfaAlpha1 !== null ? dfaAlpha1.toFixed(2) : "--"}
            </span>
            {zone && <Zone2StatusBadge zone={zone} size="sm" showDot={false} />}
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">
            Target Corridor: <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">[0.75 - 1.00]</span> (LT1: 0.75)
          </p>
        </div>
      </div>

      {/* 3. Zone 2 Time Accumulator Card */}
      <div
        role="article"
        aria-label={`Zone 2 Time: ${formatDuration(zone2Seconds)}, ${zone2Ratio}% of total workout`}
        className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Zone 2 Duration
          </span>
          <div className="p-1.5 rounded-md bg-sky-500/10 text-sky-600 dark:text-sky-400">
            <Timer className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
              {formatDuration(zone2Seconds)}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1 flex items-center justify-between">
            <span>Total: <strong className="text-foreground font-mono">{formatDuration(totalSeconds)}</strong></span>
            <span className="font-semibold text-zone2-text">{zone2Ratio}% in Z2</span>
          </p>
        </div>
      </div>

      {/* 4. Aerobic Decoupling (Pw:HR) Card */}
      <div
        role="article"
        aria-label={`Aerobic Decoupling: ${decouplingPct !== null ? `${decouplingPct.toFixed(1)}%` : "Calculating"}, ${isDecoupled ? "Cardiovascular drift detected" : "Aerobic durability stable"}`}
        className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Decoupling (Pw:HR)
          </span>
          <div className={`p-1.5 rounded-md ${isDecoupled ? "bg-amber-500/10 text-amber-600 dark:text-amber-400" : "bg-teal-500/10 text-teal-600 dark:text-teal-400"}`}>
            <TrendingUp className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
              {decouplingPct !== null ? `${decouplingPct > 0 ? "+" : ""}${decouplingPct.toFixed(1)}%` : "--"}
            </span>
          </div>
          <p className="text-[11px] mt-1 font-medium">
            {decouplingPct === null ? (
              <span className="text-muted-foreground">Requires &gt;20m data</span>
            ) : isDecoupled ? (
              <span className="text-amber-600 dark:text-amber-400 font-semibold">Drift Warning (&gt;5.0%)</span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Aerobic Base Stable (&lt;5%)</span>
            )}
          </p>
        </div>
      </div>

      {/* 5. Movesense Lead Quality Status Card */}
      <div
        role="article"
        aria-label={`Movesense Hardware Status: ${leadDetails.label}, ${leadDetails.description}`}
        className="flex flex-col justify-between p-4 rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sensor Quality
          </span>
          <div className="p-1.5 rounded-md bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Radio className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${leadDetails.badgeClass}`}>
              <LeadIcon className="w-3 h-3" aria-hidden="true" />
              {leadDetails.label}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1 truncate" title={leadDetails.description}>
            {summary?.signalQualityIndex ? `${summary.signalQualityIndex}% SNR` : leadDetails.description}
          </p>
        </div>
      </div>
    </section>
  );
}

export default SummaryCards;
