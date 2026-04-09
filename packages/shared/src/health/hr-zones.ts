/**
 * Heart rate zone model — WHOOP-style 5-zone system.
 *
 * Zone boundaries are percentage of max HR.
 * Max HR estimated from age: 220 - age (default age 30 → max 190).
 *
 * Colors are chosen so NO zone color matches the REST phase color (#ff6b6b).
 * REST is bright red — zones use blue, green, yellow, orange, deep red/magenta.
 */

export interface HRZone {
  zone: 1 | 2 | 3 | 4 | 5;
  label: string;
  color: string;
  minPct: number;
  maxPct: number;
}

export const HR_ZONES: HRZone[] = [
  { zone: 1, label: 'Recovery',  color: '#64b5f6', minPct: 0,   maxPct: 60 },  // blue
  { zone: 2, label: 'Fat Burn',  color: '#4ade80', minPct: 60,  maxPct: 70 },  // green
  { zone: 3, label: 'Aerobic',   color: '#d4e157', minPct: 70,  maxPct: 80 },  // yellow-green
  { zone: 4, label: 'Threshold', color: '#ffa726', minPct: 80,  maxPct: 90 },  // orange
  { zone: 5, label: 'Max',       color: '#e040fb', minPct: 90,  maxPct: 100 }, // magenta (NOT red)
];

/** REST phase color — must NEVER overlap with any zone */
export const REST_COLOR = '#ff6b6b';

/** Estimate max HR from age */
export function estimateMaxHR(age: number = 30): number {
  return 220 - age;
}

/** Get current zone from HR + max HR */
export function getHRZone(hr: number, maxHR: number = 190): HRZone {
  const pct = (hr / maxHR) * 100;
  for (let i = HR_ZONES.length - 1; i >= 0; i--) {
    if (pct >= HR_ZONES[i].minPct) return HR_ZONES[i];
  }
  return HR_ZONES[0];
}

/** Get zone color for a given HR */
export function getHRZoneColor(hr: number, maxHR: number = 190): string {
  return getHRZone(hr, maxHR).color;
}
