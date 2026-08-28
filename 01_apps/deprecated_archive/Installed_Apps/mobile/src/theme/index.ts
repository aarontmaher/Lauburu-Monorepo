/**
 * Lauburu mobile dark-premium theme tokens.
 *
 * Tokens only — no React component, no provider runtime. Existing
 * screens keep using their inline `StyleSheet` values until each is
 * migrated; new components in `src/components/primitives/` consume
 * these tokens directly. This keeps the migration race-resistant
 * and avoids re-rendering the world.
 *
 * Colour palette is informed by the Grappling Readiness premium
 * concept (deep blue surfaces, green readiness accent, high-
 * contrast metric numerals). The readiness band colours below are
 * the ONLY allowed colours for the readiness gauge / band chip;
 * coders MUST NOT invent intermediate hues.
 *
 * Anti-rules:
 *  - Tokens are read-only. Mutations belong in a future theme
 *    provider (not in scope for this commit).
 *  - Readiness colours map 1:1 to band thresholds in
 *    `readinessBandFromScore` (in `primitives/_helpers.ts`).
 *    Adding colours here without updating that helper breaks the
 *    contract test.
 *  - Provisional / missing / stale states use neutral / warning
 *    tones — never the green readiness accent. Truthfulness rule:
 *    the accent green is reserved for fully-confident readings.
 */

export const colors = {
  // Primary surfaces (deep blue dark theme)
  bg: '#0a0e16',
  bgElevated: '#101622',
  bgCard: '#161e2e',
  bgSubtle: 'rgba(255,255,255,0.02)',

  // Borders
  border: 'rgba(255,255,255,0.08)',
  borderEmphasis: 'rgba(255,255,255,0.18)',

  // Text
  textPrimary: '#e6edf7',
  textSecondary: '#9aa6bd',
  textMuted: '#6b7593',
  textInverse: '#0a0e16',

  // Readiness bands (high-contrast, accessible on bg)
  readinessHigh: '#5dd39e',
  readinessMedium: '#f5b942',
  readinessLow: '#e76f51',
  readinessProvisional: '#7a8aab',

  // Accents
  accent: '#5dd39e',
  accentSoft: 'rgba(93,211,158,0.18)',
  warning: '#f5b942',
  warningSoft: 'rgba(245,185,66,0.18)',
  danger: '#e76f51',
  dangerSoft: 'rgba(231,111,81,0.18)',
  info: '#7aa6ff',
  infoSoft: 'rgba(122,166,255,0.18)',
  neutral: '#9aa6bd',
  neutralSoft: 'rgba(154,166,189,0.14)',

  // Tone aliases used by Pill/Chip variants
  toneFresh: '#5dd39e',
  toneStale: '#f5b942',
  toneMissing: '#6b7593',
  toneProvisional: '#7a8aab',
  toneSetupRequired: '#7aa6ff',
  tonePlanned: '#6b7593',
} as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radii = { sm: 6, md: 10, lg: 14, xl: 20, pill: 999 } as const;

export const typography = {
  display: { fontSize: 32, fontWeight: '700' as const, letterSpacing: -0.5 },
  h1: { fontSize: 22, fontWeight: '700' as const },
  h2: { fontSize: 18, fontWeight: '700' as const },
  body: { fontSize: 14, fontWeight: '400' as const, lineHeight: 20 },
  bodyEmphasis: { fontSize: 14, fontWeight: '600' as const, lineHeight: 20 },
  caption: { fontSize: 12, fontWeight: '500' as const, letterSpacing: 0.3, lineHeight: 16 },
  label: { fontSize: 10, fontWeight: '700' as const, textTransform: 'uppercase' as const, letterSpacing: 1.2 },
} as const;

export const elevation = {
  card: {
    shadowColor: '#000',
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
} as const;

export const theme = { colors, spacing, radii, typography, elevation } as const;
export type LauburuTheme = typeof theme;
