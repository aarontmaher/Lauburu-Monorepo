import React from "react";
import {
  BiometricZone,
  classifyDfaZone,
  getZoneMetadata,
  BIOMETRIC_THRESHOLDS,
} from "@/types/biometrics";

export interface Zone2StatusBadgeProps {
  zone?: BiometricZone;
  dfaAlpha1?: number | null;
  alpha1?: number | null; // Prop alias for backward/cross compatibility
  size?: "sm" | "md" | "lg";
  showDot?: boolean;
  showCorridorHint?: boolean;
  className?: string;
}

/**
 * Pure React Server Component (RSC): Zone2StatusBadge
 * Renders an accessible, high-contrast physiological zone indicator
 * adhering to clinical DFA-alpha1 thresholds and WCAG 2.1 AA contrast requirements.
 */
export function Zone2StatusBadge({
  zone,
  dfaAlpha1,
  alpha1,
  size = "md",
  showDot = true,
  showCorridorHint = false,
  className = "",
}: Zone2StatusBadgeProps) {
  const numericAlpha1 = typeof dfaAlpha1 === "number" ? dfaAlpha1 : (typeof alpha1 === "number" ? alpha1 : null);

  // Determine physiological zone from direct zone or DFA-alpha1 value
  const resolvedZone: BiometricZone =
    zone ?? (numericAlpha1 !== null ? classifyDfaZone(numericAlpha1) : "ZONE_2");

  const metadata = getZoneMetadata(resolvedZone);
  const isZone2 = resolvedZone === "ZONE_2";

  // Size styling variants
  const sizeStyles = {
    sm: "px-2 py-0.5 text-xs gap-1.5",
    md: "px-3 py-1 text-xs sm:text-sm font-medium gap-2",
    lg: "px-4 py-1.5 text-sm sm:text-base font-semibold gap-2.5",
  }[size];

  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  }[size];

  return (
    <div
      role="status"
      aria-label={`Physiological Zone Status: ${metadata.label}${numericAlpha1 !== null ? `, DFA-alpha1: ${numericAlpha1.toFixed(2)}` : ""}`}
      className={`inline-flex items-center rounded-full border transition-colors ${metadata.bgClass} ${metadata.textClass} ${metadata.borderClass} ${sizeStyles} ${className}`.trim()}
    >
      {showDot && (
        <span
          className={`rounded-full shrink-0 ${dotSizes} ${isZone2 ? "animate-pulse" : ""}`}
          style={{ backgroundColor: metadata.color }}
          aria-hidden="true"
        />
      )}
      <span className="font-semibold tracking-tight">{metadata.label}</span>
      {showCorridorHint && isZone2 && (
        <span
          className="text-[10px] sm:text-xs opacity-90 border-l border-current pl-1.5 ml-0.5 font-mono"
          aria-label="Target corridor 0.75 to 1.00"
        >
          [{BIOMETRIC_THRESHOLDS.ZONE_2_LOWER.toFixed(2)} - {BIOMETRIC_THRESHOLDS.ZONE_2_UPPER.toFixed(2)}]
        </span>
      )}
    </div>
  );
}

export default Zone2StatusBadge;
