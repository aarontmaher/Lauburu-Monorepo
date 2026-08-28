"use client";

import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { LeadStatus } from "@/types/biometrics";
import { AccessibleDataTable } from "./AccessibleDataTable";
import { Activity, Play, Pause, RefreshCw, ZoomIn, Sliders, Eye, EyeOff } from "lucide-react";

export interface LiveEcgMonitorProps {
  ecgSamples?: number[];
  leadStatus?: LeadStatus;
  samplingRateHz?: number;
  timeWindowSeconds?: number;
  heightPx?: number;
  showGrid?: boolean;
  className?: string;
  heartRate?: number;
}

/**
 * 640-sample Circular Ring Buffer for 128Hz ECG streaming
 */
export class EcgSweepRingBuffer {
  public capacity: number;
  public buffer: Float32Array;
  public writeIndex: number = 0;
  public totalSamplesPushed: number = 0;

  constructor(capacity: number = 640) {
    this.capacity = capacity;
    this.buffer = new Float32Array(capacity);
  }

  public push(sampleVoltage: number): void {
    // Sanitize float (NaN, Infinity, undefined -> 0.0 mV; clamp [-5.0, 5.0] mV)
    let v = sampleVoltage;
    if (typeof v !== "number" || Number.isNaN(v) || !Number.isFinite(v)) {
      v = 0.0;
    } else {
      v = Math.max(-5.0, Math.min(5.0, v));
    }

    this.buffer[this.writeIndex] = v;
    this.writeIndex = (this.writeIndex + 1) % this.capacity;
    this.totalSamplesPushed++;
  }

  public pushBatch(samples: number[]): void {
    for (let i = 0; i < samples.length; i++) {
      this.push(samples[i]);
    }
  }

  public clear(): void {
    this.buffer.fill(0);
    this.writeIndex = 0;
    this.totalSamplesPushed = 0;
  }
}

/**
 * LiveEcgMonitor Component
 * 
 * High-performance 128Hz Canvas Oscilloscope with medical calibration grid,
 * circular ring buffer, sweep bar rendering, adjustable sweep speed & gain,
 * and full accessibility support.
 */
export function LiveEcgMonitor({
  ecgSamples = [],
  leadStatus = "CONNECTED",
  samplingRateHz = 128,
  timeWindowSeconds = 5.0,
  heightPx = 220,
  showGrid = true,
  className = "",
  heartRate = 0,
}: LiveEcgMonitorProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const animationFrameId = useRef<number | null>(null);

  // Ring buffer of 640 samples (5s @ 128Hz)
  const ringBuffer = useMemo(() => new EcgSweepRingBuffer(640), []);

  // UI Interactive States
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [sweepSpeed, setSweepSpeed] = useState<number>(25); // 12.5, 25, 50 mm/s
  const [gainMmPerMv, setGainMmPerMv] = useState<number>(10); // 5, 10, 20 mm/mV
  const [isTableVisible, setIsTableVisible] = useState<boolean>(false);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

  // Check theme mode
  useEffect(() => {
    const checkDark = () => {
      setIsDarkMode(document.documentElement.classList.contains("dark"));
    };
    checkDark();

    const observer = new MutationObserver(checkDark);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  // Ingest incoming sample batch
  useEffect(() => {
    if (!isPaused && ecgSamples && ecgSamples.length > 0) {
      ringBuffer.pushBatch(ecgSamples);
    }
  }, [ecgSamples, isPaused, ringBuffer]);

  // Lead status UI badge helper
  const getLeadBadge = useCallback((status: LeadStatus) => {
    switch (status) {
      case "OPTIMAL":
      case "CONNECTED":
        return {
          label: "Lead: Optimal",
          bg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
          dot: "bg-emerald-500",
          aria: "ECG lead contact is optimal",
        };
      case "NOISY_MOTION":
      case "NOISY":
        return {
          label: "Motion Artifact",
          bg: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
          dot: "bg-amber-500",
          aria: "ECG signal contains motion artifacts",
        };
      case "POOR_CONTACT":
        return {
          label: "Dry Electrodes",
          bg: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30",
          dot: "bg-orange-500",
          aria: "Poor electrode contact, moisten sensor strap",
        };
      case "LEAD_OFF":
      case "OFF_BODY":
        return {
          label: "Lead Off",
          bg: "bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/40 animate-pulse",
          dot: "bg-rose-500",
          aria: "ECG lead disconnected from body",
        };
      case "DISCONNECTED":
      default:
        return {
          label: "Disconnected (--)",
          bg: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30",
          dot: "bg-slate-500",
          aria: "ECG sensor is disconnected",
        };
    }
  }, []);

  const leadBadge = getLeadBadge(leadStatus);

  // Main Canvas Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const render = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;

      if (width === 0 || height === 0) {
        animationFrameId.current = requestAnimationFrame(render);
        return;
      }

      // Update canvas resolution for high-DPI crispness
      if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) {
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
      }

      ctx.save();
      ctx.scale(dpr, dpr);

      // 1. Background
      ctx.fillStyle = isDarkMode ? "#020617" : "#090d16";
      ctx.fillRect(0, 0, width, height);

      // 2. Standard Medical Grid
      if (showGrid) {
        const mmPx = width / (timeWindowSeconds * 25); // pixels per mm (at 25 mm/s nominal base)
        const minorStep = Math.max(4, mmPx); // 1 mm
        const majorStep = minorStep * 5; // 5 mm

        // Minor Grid Lines
        ctx.beginPath();
        ctx.strokeStyle = isDarkMode ? "rgba(52, 211, 153, 0.08)" : "rgba(16, 185, 129, 0.08)";
        ctx.lineWidth = 0.5;

        for (let x = 0; x < width; x += minorStep) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
        }
        for (let y = 0; y < height; y += minorStep) {
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
        }
        ctx.stroke();

        // Major Grid Lines
        ctx.beginPath();
        ctx.strokeStyle = isDarkMode ? "rgba(52, 211, 153, 0.24)" : "rgba(16, 185, 129, 0.22)";
        ctx.lineWidth = 1.0;

        for (let x = 0; x < width; x += majorStep) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
        }
        for (let y = 0; y < height; y += majorStep) {
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
        }
        ctx.stroke();
      }

      // 3. ECG Waveform Tracing
      const centerY = height / 2;
      const capacity = ringBuffer.capacity;
      const writeIdx = ringBuffer.writeIndex;
      const buffer = ringBuffer.buffer;

      // Vertical gain scaling: 1 mV = gainMmPerMv * (height / 40)
      const scaleY = (gainMmPerMv / 10) * (height / 4.0);

      // Trace styling
      const traceColor = isDarkMode ? "#34d399" : "#059669";
      ctx.strokeStyle = traceColor;
      ctx.lineWidth = 2.0;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.shadowColor = isDarkMode ? "rgba(52, 211, 153, 0.4)" : "rgba(5, 150, 105, 0.3)";
      ctx.shadowBlur = 4;

      const isOff = leadStatus === "DISCONNECTED" || leadStatus === "LEAD_OFF" || leadStatus === "OFF_BODY";

      if (isOff) {
        // Flatline isoelectric baseline
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.stroke();
      } else {
        // Oscilloscope Sweep Rendering with Erase Gap
        const eraseGapSamples = 16; // gap width in samples
        const cursorX = (writeIdx / capacity) * width;

        // Draw Section 1: From writeIndex to capacity (older segment)
        ctx.beginPath();
        let section1Started = false;
        const startSec1 = (writeIdx + eraseGapSamples) % capacity;

        if (startSec1 > writeIdx) {
          for (let i = startSec1; i < capacity; i++) {
            const x = (i / capacity) * width;
            const y = centerY - (buffer[i] * scaleY);
            if (!section1Started) {
              ctx.moveTo(x, y);
              section1Started = true;
            } else {
              ctx.lineTo(x, y);
            }
          }
        }

        // Draw Section 2: From 0 to writeIndex (newly written segment)
        for (let i = 0; i < writeIdx; i++) {
          const x = (i / capacity) * width;
          const y = centerY - (buffer[i] * scaleY);
          if (!section1Started && i === 0) {
            ctx.moveTo(x, y);
            section1Started = true;
          } else if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();

        // Draw Sweep Head Cursor
        ctx.beginPath();
        ctx.strokeStyle = isDarkMode ? "#a7f3d0" : "#6ee7b7";
        ctx.lineWidth = 1.5;
        ctx.shadowBlur = 6;
        ctx.moveTo(cursorX, 0);
        ctx.lineTo(cursorX, height);
        ctx.stroke();
      }

      // 4. Calibration Pulse & Scale Overlay (Top Left)
      ctx.shadowBlur = 0;
      ctx.fillStyle = isDarkMode ? "rgba(148, 163, 184, 0.8)" : "rgba(148, 163, 184, 0.9)";
      ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace";
      ctx.fillText(`25 mm/s | ${gainMmPerMv} mm/mV | 128 Hz`, 10, 16);

      ctx.restore();

      animationFrameId.current = requestAnimationFrame(render);
    };

    animationFrameId.current = requestAnimationFrame(render);

    return () => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [isDarkMode, showGrid, timeWindowSeconds, gainMmPerMv, leadStatus, ringBuffer]);

  const handleReset = () => {
    ringBuffer.clear();
  };

  return (
    <div
      ref={containerRef}
      className={`flex flex-col rounded-xl border border-border bg-card p-4 shadow-sm ${className}`}
      role="region"
      aria-label="Real-time ECG Oscilloscope Monitor"
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border mb-3">
        <div className="flex items-center gap-2.5">
          <Activity className="w-5 h-5 text-emerald-500" aria-hidden="true" />
          <h2 className="text-base font-semibold text-foreground">
            Live Electrocardiography (ECG)
          </h2>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${leadBadge.bg}`}
            role="status"
            aria-label={leadBadge.aria}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${leadBadge.dot}`} aria-hidden="true" />
            {leadBadge.label}
          </span>
        </div>

        {/* Live Metrics Quick View */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="text-muted-foreground">
            HR:{" "}
            <span className="font-bold text-foreground">
              {heartRate > 0 && leadStatus !== "DISCONNECTED" && leadStatus !== "OFF_BODY"
                ? `${heartRate} BPM`
                : "--"}
            </span>
          </div>
          <div className="text-muted-foreground">
            Rate: <span className="text-foreground">{samplingRateHz} Hz</span>
          </div>
        </div>
      </div>

      {/* Oscilloscope Canvas Area */}
      <div className="relative rounded-lg overflow-hidden border border-border bg-black">
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`Real-time 128Hz ECG oscilloscope waveform, Lead status: ${leadBadge.label}, Heart rate: ${
            heartRate > 0 ? heartRate + " BPM" : "unconnected"
          }`}
          tabIndex={0}
          className="w-full block cursor-crosshair focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          style={{ height: `${heightPx}px` }}
        >
          {/* Accessible fallback for screen readers */}
          <p>
            Real-time single-lead ECG oscilloscope stream at 128Hz. Current lead status is {leadBadge.label}.
            Current heart rate is {heartRate > 0 ? heartRate + " BPM" : "not available"}.
          </p>
        </canvas>
      </div>

      {/* Interactive Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 mt-1 text-xs">
        {/* Left: Playback & Gain Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Pause / Resume Button */}
          <button
            type="button"
            onClick={() => setIsPaused(!isPaused)}
            aria-pressed={isPaused}
            aria-label={isPaused ? "Resume live ECG sweep" : "Pause live ECG sweep"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-muted font-medium transition-colors min-h-[44px] min-w-[44px] focus-visible:ring-2 focus-visible:ring-primary"
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4 text-emerald-500" aria-hidden="true" />
                <span>Resume</span>
              </>
            ) : (
              <>
                <Pause className="w-4 h-4 text-amber-500" aria-hidden="true" />
                <span>Pause</span>
              </>
            )}
          </button>

          {/* Sweep Speed Selector */}
          <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-lg border border-border">
            <span className="px-1.5 text-muted-foreground font-semibold">Speed:</span>
            {[12.5, 25, 50].map((speed) => (
              <button
                key={speed}
                type="button"
                onClick={() => setSweepSpeed(speed)}
                aria-pressed={sweepSpeed === speed}
                aria-label={`Set sweep speed to ${speed} mm per second`}
                className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors min-h-[36px] ${
                  sweepSpeed === speed
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-foreground hover:bg-muted"
                } focus-visible:ring-2 focus-visible:ring-primary`}
              >
                {speed} mm/s
              </button>
            ))}
          </div>

          {/* Gain / Sensitivity Selector */}
          <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-lg border border-border">
            <span className="px-1.5 text-muted-foreground font-semibold">Gain:</span>
            {[5, 10, 20].map((gain) => (
              <button
                key={gain}
                type="button"
                onClick={() => setGainMmPerMv(gain)}
                aria-pressed={gainMmPerMv === gain}
                aria-label={`Set ECG sensitivity gain to ${gain} mm per millivolt`}
                className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors min-h-[36px] ${
                  gainMmPerMv === gain
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-foreground hover:bg-muted"
                } focus-visible:ring-2 focus-visible:ring-primary`}
              >
                {gain} mm/mV
              </button>
            ))}
          </div>

          {/* Reset Buffer Button */}
          <button
            type="button"
            onClick={handleReset}
            aria-label="Clear oscilloscope trace buffer"
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-muted font-medium transition-colors min-h-[44px] focus-visible:ring-2 focus-visible:ring-primary"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Clear</span>
          </button>
        </div>

        {/* Right: Accessible Table View Toggle */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsTableVisible(!isTableVisible)}
            aria-expanded={isTableVisible}
            aria-controls="ecg-accessible-table"
            aria-label={isTableVisible ? "Hide accessible data table" : "Show accessible data table"}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-foreground hover:bg-muted font-medium transition-colors min-h-[44px] focus-visible:ring-2 focus-visible:ring-primary"
          >
            {isTableVisible ? (
              <>
                <EyeOff className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                <span>Hide Table</span>
              </>
            ) : (
              <>
                <Eye className="w-4 h-4 text-primary" aria-hidden="true" />
                <span>View Data Table</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Accessible Table Collapsible Section */}
      {isTableVisible && (
        <div id="ecg-accessible-table" className="mt-4 pt-4 border-t border-border">
          <AccessibleDataTable
            data={[]}
            leadStatus={leadStatus}
            caption="Real-time ECG Stream Telemetry Record"
          />
        </div>
      )}
    </div>
  );
}

export default LiveEcgMonitor;
