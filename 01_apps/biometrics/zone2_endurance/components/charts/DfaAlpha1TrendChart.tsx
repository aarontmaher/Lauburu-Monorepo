"use client";

import React, { useState, useId } from "react";
import { DfaAlpha1Point, LeadStatus, BIOMETRIC_THRESHOLDS, classifyDfaZone, getZoneMetadata } from "@/types/biometrics";
import { AccessibleDataTable } from "./AccessibleDataTable";
import { TrendingUp, AlertTriangle, ShieldCheck, Eye, EyeOff, Info } from "lucide-react";

export interface DfaAlpha1TrendChartProps {
  history?: DfaAlpha1Point[];
  currentAlpha1?: number | null;
  targetThresholdLow?: number;
  targetThresholdHigh?: number;
  anaerobicThreshold?: number;
  heightPx?: number;
  className?: string;
  leadStatus?: LeadStatus;
}

/**
 * DfaAlpha1TrendChart Component
 * 
 * Interactive SVG trend chart visualizing DFA alpha-1 fractal scaling over time.
 * Features:
 * - Shaded [0.75, 1.00] Aerobic Zone 2 Corridor
 * - Horizontal dashed threshold guidelines at 0.75 (LT1) and 0.50 (LT2)
 * - Kamath 2004 20% RR interval artifact filter indicator
 * - Interactive hover & keyboard focus tooltip inspection
 * - Accessible data table toggle and screen-reader status
 */
export function DfaAlpha1TrendChart({
  history = [],
  currentAlpha1 = null,
  targetThresholdLow = BIOMETRIC_THRESHOLDS.ZONE_2_LOWER, // 0.75
  targetThresholdHigh = BIOMETRIC_THRESHOLDS.ZONE_2_UPPER, // 1.00
  anaerobicThreshold = BIOMETRIC_THRESHOLDS.ZONE_3_LOWER, // 0.50
  heightPx = 280,
  className = "",
  leadStatus = "CONNECTED",
}: DfaAlpha1TrendChartProps) {
  const chartId = useId();
  const [hoveredPoint, setHoveredPoint] = useState<DfaAlpha1Point | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);
  const [isTableVisible, setIsTableVisible] = useState<boolean>(false);

  // Derive latest value and zone
  const latestPoint = history.length > 0 ? history[history.length - 1] : null;
  const activeAlpha1 = currentAlpha1 ?? (latestPoint ? latestPoint.alpha1 : null);
  const activeZone = activeAlpha1 !== null ? classifyDfaZone(activeAlpha1) : null;
  const activeZoneMeta = activeZone ? getZoneMetadata(activeZone) : null;

  // Artifact calculation from latest point
  const latestArtifactPct = latestPoint ? latestPoint.artifactPercentage : 0;
  const isHighArtifact = latestArtifactPct > BIOMETRIC_THRESHOLDS.KAMATH_MAX_ARTIFACT_PCT;

  // SVG Chart Dimensions
  const padding = { top: 24, right: 36, bottom: 36, left: 48 };
  const chartWidth = 720;
  const chartHeight = heightPx;
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;

  // Y-Scale Mapping: from 0.20 to 1.40
  const yMin = 0.20;
  const yMax = 1.40;
  const getY = (val: number) => {
    const clamped = Math.max(yMin, Math.min(yMax, val));
    return padding.top + plotHeight - ((clamped - yMin) / (yMax - yMin)) * plotHeight;
  };

  // X-Scale Mapping
  const getX = (index: number, total: number) => {
    if (total <= 1) return padding.left + plotWidth / 2;
    return padding.left + (index / (total - 1)) * plotWidth;
  };

  // Calculate Corridor and Guidelines
  const yZone2Top = getY(targetThresholdHigh); // 1.00
  const yZone2Bottom = getY(targetThresholdLow); // 0.75
  const corridorHeight = Math.abs(yZone2Bottom - yZone2Top);

  const yLt2 = getY(anaerobicThreshold); // 0.50

  // Build SVG Path
  const dataPoints = history;
  const pathD = dataPoints.length > 0
    ? dataPoints.map((pt, i) => `${i === 0 ? "M" : "L"} ${getX(i, dataPoints.length)} ${getY(pt.alpha1)}`).join(" ")
    : "";

  const isDisconnected = leadStatus === "DISCONNECTED" || leadStatus === "OFF_BODY";

  return (
    <div
      className={`flex flex-col rounded-xl border border-border bg-card p-4 shadow-sm ${className}`}
      role="region"
      aria-label="DFA-alpha1 Aerobic Threshold Trend Chart"
    >
      {/* Header & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border mb-3">
        <div className="flex items-center gap-2.5">
          <TrendingUp className="w-5 h-5 text-primary" aria-hidden="true" />
          <h2 className="text-base font-semibold text-foreground">
            DFA-&alpha;<sub>1</sub> Aerobic Threshold Trend
          </h2>
          {activeZoneMeta && !isDisconnected && (
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{
                backgroundColor: `${activeZoneMeta.color}15`,
                color: activeZoneMeta.color,
                border: `1px solid ${activeZoneMeta.color}40`,
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: activeZoneMeta.color }} aria-hidden="true" />
              {activeZoneMeta.label}
            </span>
          )}
        </div>

        {/* Kamath Artifact Filter Indicator */}
        <div className="flex items-center gap-2">
          {isHighArtifact ? (
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
              role="status"
              aria-label="Kamath artifact warning: motion artifact exceeds 20%"
            >
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Low Confidence ({latestArtifactPct.toFixed(1)}% Artifact)</span>
            </div>
          ) : (
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
              role="status"
              aria-label="Kamath artifact filter active and optimal"
            >
              <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Kamath Filter Clean ({latestArtifactPct.toFixed(1)}%)</span>
            </div>
          )}
        </div>
      </div>

      {/* Screen Reader Live Summary */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {isDisconnected
          ? "Sensor disconnected. DFA alpha-1 telemetry inactive."
          : `Current DFA alpha-1 is ${
              activeAlpha1 !== null ? activeAlpha1.toFixed(2) : "not available"
            }, corresponding to ${activeZoneMeta ? activeZoneMeta.label : "unclassified"}. Time-series contains ${
              dataPoints.length
            } data points.`}
      </div>

      {/* Interactive SVG Chart Canvas */}
      <div className="relative w-full overflow-hidden rounded-lg border border-border bg-slate-950/20 dark:bg-slate-950/60">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto block select-none"
          role="img"
          aria-label={`DFA alpha-1 time trend chart showing aerobic zone corridor 0.75 to 1.00 and ${dataPoints.length} recorded points`}
        >
          <defs>
            {/* Zone 2 Corridor Gradient */}
            <linearGradient id={`${chartId}-zone2-grad`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#059669" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0.08" />
            </linearGradient>

            {/* Line Glow */}
            <filter id={`${chartId}-glow`} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Y-Axis Grid Lines & Labels */}
          {[1.40, 1.20, 1.00, 0.75, 0.50, 0.35].map((val) => {
            const y = getY(val);
            return (
              <g key={val}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={chartWidth - padding.right}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity="0.12"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 3.5}
                  textAnchor="end"
                  className="fill-muted-foreground font-mono text-[10px]"
                >
                  {val.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Shaded Zone 2 Aerobic Corridor [0.75, 1.00] */}
          <rect
            x={padding.left}
            y={yZone2Top}
            width={plotWidth}
            height={corridorHeight}
            fill={`url(#${chartId}-zone2-grad)`}
            stroke="#059669"
            strokeWidth="1"
            strokeOpacity="0.4"
            strokeDasharray="4 4"
          />

          {/* Corridor Label */}
          <text
            x={padding.left + 8}
            y={yZone2Top + 14}
            className="fill-emerald-600 dark:fill-emerald-400 font-sans font-semibold text-[10px]"
          >
            AEROBIC ZONE 2 CORRIDOR [0.75 – 1.00]
          </text>

          {/* LT1 Aerobic Threshold Line (0.75) */}
          <line
            x1={padding.left}
            y1={yZone2Bottom}
            x2={chartWidth - padding.right}
            y2={yZone2Bottom}
            stroke="#059669"
            strokeWidth="1.5"
            strokeDasharray="6 3"
          />
          <text
            x={chartWidth - padding.right}
            y={yZone2Bottom - 5}
            textAnchor="end"
            className="fill-emerald-600 dark:fill-emerald-400 font-mono font-medium text-[9px]"
          >
            LT1 Aerobic (0.75)
          </text>

          {/* LT2 Anaerobic Threshold Line (0.50) */}
          <line
            x1={padding.left}
            y1={yLt2}
            x2={chartWidth - padding.right}
            y2={yLt2}
            stroke="#e11d48"
            strokeWidth="1.5"
            strokeDasharray="6 3"
          />
          <text
            x={chartWidth - padding.right}
            y={yLt2 - 5}
            textAnchor="end"
            className="fill-rose-600 dark:fill-rose-400 font-mono font-medium text-[9px]"
          >
            LT2 Anaerobic (0.50)
          </text>

          {/* Historical Trend Line */}
          {dataPoints.length > 0 && !isDisconnected && (
            <path
              d={pathD}
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter={`url(#${chartId}-glow)`}
            />
          )}

          {/* Data Point Dots with Hover / Keyboard Inspection */}
          {dataPoints.map((pt, index) => {
            const x = getX(index, dataPoints.length);
            const y = getY(pt.alpha1);
            const zoneMeta = getZoneMetadata(pt.zone);
            const isHovered = hoveredPoint === pt || focusedIndex === index;

            return (
              <g key={pt.timestamp || index}>
                {/* Focus Ring and Click Area */}
                <circle
                  cx={x}
                  cy={y}
                  r={isHovered ? 6 : 3.5}
                  fill={zoneMeta.color}
                  stroke="#ffffff"
                  strokeWidth={isHovered ? 2 : 1}
                  className="cursor-pointer transition-all duration-150"
                  tabIndex={0}
                  role="button"
                  aria-label={`Data point ${index + 1}: DFA alpha-1 ${pt.alpha1.toFixed(2)}, Heart rate ${
                    pt.heartRate
                  } BPM, Zone ${zoneMeta.label}`}
                  onMouseEnter={() => setHoveredPoint(pt)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  onFocus={() => setFocusedIndex(index)}
                  onBlur={() => setFocusedIndex(null)}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowRight" && index < dataPoints.length - 1) {
                      setFocusedIndex(index + 1);
                    } else if (e.key === "ArrowLeft" && index > 0) {
                      setFocusedIndex(index - 1);
                    }
                  }}
                />
              </g>
            );
          })}

          {/* Empty / Disconnected Message */}
          {(dataPoints.length === 0 || isDisconnected) && (
            <text
              x={chartWidth / 2}
              y={chartHeight / 2}
              textAnchor="middle"
              className="fill-muted-foreground font-sans text-xs italic"
            >
              {isDisconnected
                ? "Sensor disconnected. Connect Movesense strap to stream DFA-α1 telemetry."
                : "Awaiting sufficient RR interval buffer for 120s rolling window..."}
            </text>
          )}
        </svg>

        {/* Hover / Focused Point Tooltip */}
        {(hoveredPoint || (focusedIndex !== null && dataPoints[focusedIndex])) && (
          (() => {
            const pt = hoveredPoint || dataPoints[focusedIndex!];
            const zoneMeta = getZoneMetadata(pt.zone);
            const d = new Date(pt.timestamp);
            const timeStr = isNaN(d.getTime()) ? "--:--" : d.toLocaleTimeString();

            return (
              <div
                className="absolute top-2 right-2 rounded-lg border border-border bg-card/95 p-2.5 text-xs shadow-lg backdrop-blur-sm pointer-events-none transition-all"
                role="tooltip"
              >
                <div className="font-semibold text-foreground flex items-center justify-between gap-3 border-b border-border pb-1 mb-1">
                  <span>{timeStr}</span>
                  <span className="font-mono" style={{ color: zoneMeta.color }}>
                    {zoneMeta.shortLabel}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono text-[11px]">
                  <span className="text-muted-foreground">DFA &alpha;<sub>1</sub>:</span>
                  <span className="font-bold text-foreground">{pt.alpha1.toFixed(2)}</span>
                  <span className="text-muted-foreground">Heart Rate:</span>
                  <span className="text-foreground">{pt.heartRate > 0 ? `${pt.heartRate} BPM` : "--"}</span>
                  {pt.power ? (
                    <>
                      <span className="text-muted-foreground">Power:</span>
                      <span className="text-foreground">{pt.power} W</span>
                    </>
                  ) : null}
                  <span className="text-muted-foreground">Artifact:</span>
                  <span className="text-foreground">{pt.artifactPercentage.toFixed(1)}%</span>
                </div>
              </div>
            );
          })()
        )}
      </div>

      {/* Bottom Summary Bar & Table Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 mt-1 text-xs">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Info className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
          <span>
            Target: Sustain &alpha;<sub>1</sub> &ge; 0.75 for maximum aerobic lipid oxidation.
          </span>
        </div>

        <button
          type="button"
          onClick={() => setIsTableVisible(!isTableVisible)}
          aria-expanded={isTableVisible}
          aria-controls="dfa-accessible-table"
          aria-label={isTableVisible ? "Hide history table" : "Show history table"}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-muted font-medium transition-colors min-h-[44px] focus-visible:ring-2 focus-visible:ring-primary"
        >
          {isTableVisible ? (
            <>
              <EyeOff className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
              <span>Hide History</span>
            </>
          ) : (
            <>
              <Eye className="w-4 h-4 text-primary" aria-hidden="true" />
              <span>View History Table</span>
            </>
          )}
        </button>
      </div>

      {/* Accessible Data Table Drawer */}
      {isTableVisible && (
        <div id="dfa-accessible-table" className="mt-4 pt-4 border-t border-border">
          <AccessibleDataTable
            data={dataPoints}
            leadStatus={leadStatus}
            caption="DFA-alpha1 Rolling Calculation History"
          />
        </div>
      )}
    </div>
  );
}

export default DfaAlpha1TrendChart;
