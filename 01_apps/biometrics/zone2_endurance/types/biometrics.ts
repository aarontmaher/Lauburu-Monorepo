/**
 * Zone 2 Endurance Biometric Data Contracts & Telemetry Schema
 * Authoritative types for ECG streaming, DFA-alpha1 fractal analysis, and aerobic endurance metrics.
 */

export type LeadStatus =
  | 'CONNECTED'
  | 'DISCONNECTED'
  | 'NOISY'
  | 'POOR_CONTACT'
  | 'OFF_BODY'
  | 'OPTIMAL'
  | 'NOISY_MOTION'
  | 'LEAD_OFF';

export type BiometricZone =
  | 'ZONE_1' // Recovery / Active Rest (DFA-a1 > 1.00)
  | 'ZONE_2' // Aerobic Endurance Target (0.75 <= DFA-a1 <= 1.00)
  | 'ZONE_3' // Tempo / Aerobic Power (0.50 <= DFA-a1 < 0.75)
  | 'ZONE_4' // Threshold (Anaerobic entry)
  | 'ZONE_5'; // Neuromuscular / VO2Max (DFA-a1 < 0.50)

export interface EcgSample {
  timestamp: number; // Milliseconds Unix epoch or elapsed offset
  voltage: number;   // Millivolts (mV) or raw calibrated ADC signal
  sampleIndex?: number;
  leadStatus?: LeadStatus;
}

export interface DfaAlpha1Point {
  timestamp: number;          // Epoch milliseconds
  alpha1: number;             // DFA alpha-1 scaling exponent (e.g. 0.82)
  heartRate: number;          // Instantaneous or rolling BPM
  power?: number;             // Watts (cycling ergometer / smart trainer)
  pace?: number;              // Seconds per kilometer / m/s
  artifactPercentage: number; // Kamath 20% rule artifact filtering ratio (0.0 to 100.0)
  zone: BiometricZone;        // Current physiological zone based on DFA-a1
  windowSizeSeconds?: number; // Computation window size (typically 120s)
}

export interface AerobicDecouplingMetrics {
  firstHalfPwHrRatio: number;   // Power:HR or Pace:HR efficiency ratio (Split 1)
  secondHalfPwHrRatio: number;  // Power:HR or Pace:HR efficiency ratio (Split 2)
  decouplingPercentage: number; // ((Split 1 / Split 2) - 1) * 100, e.g. 3.4%
  isDecoupled: boolean;         // True if decoupling exceeds drift threshold (> 5.0%)
  firstHalfAvgHr: number;
  secondHalfAvgHr: number;
  firstHalfAvgPower: number;
  secondHalfAvgPower: number;
  durationSeconds: number;
}

export interface BiometricSummary {
  heartRate: number;
  currentDfaAlpha1: number;
  currentZone: BiometricZone;
  zone2DurationSeconds: number;
  totalDurationSeconds: number;
  aerobicDecouplingPercent: number;
  avgHeartRate: number;
  maxHeartRate: number;
  leadStatus: LeadStatus;
  samplingRateHz: number;
  signalQualityIndex: number; // 0 to 100% signal quality metric
}

export interface TelemetryStreamPacket {
  sequence: number;
  timestamp: number;
  deviceId: string;
  leadStatus: LeadStatus;
  ecgSamples: EcgSample[];
  hrBpm: number;
  rrIntervalsMs: number[];
  dfaAlpha1?: DfaAlpha1Point;
  summary?: BiometricSummary;
  aerobicDecoupling?: AerobicDecouplingMetrics;
}

/**
 * Physiological Threshold Constants
 */
export const BIOMETRIC_THRESHOLDS = {
  ZONE_2_UPPER: 1.00, // Upper boundary of Zone 2 (DFA-a1 > 1.00 is Zone 1 Recovery)
  ZONE_2_LOWER: 0.75, // LT1 - Aerobic Threshold (DFA-a1 = 0.75)
  ZONE_3_LOWER: 0.50, // LT2 - Anaerobic Threshold (DFA-a1 = 0.50)
  KAMATH_MAX_ARTIFACT_PCT: 20.0, // Maximum allowed artifact percentage before warning
  DECOUPLING_DRIFT_THRESHOLD_PCT: 5.0, // > 5% indicates aerobic decoupling / cardiac drift
} as const;

/**
 * Helper to classify biometric zone from DFA-alpha1 value
 */
export function classifyDfaZone(alpha1: number): BiometricZone {
  if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_2_UPPER) {
    return 'ZONE_1';
  } else if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_2_LOWER) {
    return 'ZONE_2';
  } else if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_3_LOWER) {
    return 'ZONE_3';
  } else if (alpha1 >= 0.35) {
    return 'ZONE_4';
  } else {
    return 'ZONE_5';
  }
}

/**
 * Helper to get human-readable name and colors for biometric zones
 */
export function getZoneMetadata(zone: BiometricZone) {
  switch (zone) {
    case 'ZONE_1':
      return {
        label: 'Zone 1 (Recovery)',
        shortLabel: 'Z1 Recovery',
        color: '#0284c7',
        bgClass: 'bg-zone1-subtle',
        textClass: 'text-zone1-text',
        borderClass: 'border-zone1',
      };
    case 'ZONE_2':
      return {
        label: 'Zone 2 (Aerobic Base)',
        shortLabel: 'Z2 Aerobic',
        color: '#059669',
        bgClass: 'bg-zone2-subtle',
        textClass: 'text-zone2-text',
        borderClass: 'border-zone2',
      };
    case 'ZONE_3':
      return {
        label: 'Zone 3 (Tempo)',
        shortLabel: 'Z3 Tempo',
        color: '#d97706',
        bgClass: 'bg-zone3-subtle',
        textClass: 'text-zone3-text',
        borderClass: 'border-zone3',
      };
    case 'ZONE_4':
      return {
        label: 'Zone 4 (Threshold)',
        shortLabel: 'Z4 Threshold',
        color: '#ea580c',
        bgClass: 'bg-zone4-subtle',
        textClass: 'text-zone4-text',
        borderClass: 'border-zone4',
      };
    case 'ZONE_5':
      return {
        label: 'Zone 5 (Anaerobic / VO2Max)',
        shortLabel: 'Z5 Anaerobic',
        color: '#e11d48',
        bgClass: 'bg-zone5-subtle',
        textClass: 'text-zone5-text',
        borderClass: 'border-zone5',
      };
  }
}
