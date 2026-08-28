/**
 * Lauburu Grappling Map color palette.
 * Dark theme primary. Accent is a muted warm yellow-green.
 */

/** Primary accent — warmer and less neon than the website's #e8ff47 */
const accent = '#d4e157';
/** Dimmed accent for secondary text, suggestions */
const accentDim = '#a8b84a';
/** Subtle accent for backgrounds/borders */
const accentSubtle = 'rgba(212, 225, 87, 0.12)';

export { accent, accentDim, accentSubtle };

export default {
  light: {
    text: '#1a1a1a',
    textSecondary: '#666',
    background: '#f5f5f5',
    card: '#fff',
    tint: '#5d7a3a',
    tabIconDefault: '#999',
    tabIconSelected: '#5d7a3a',
    border: '#e0e0e0',
    accent,
  },
  dark: {
    text: '#f0f0f0',
    textSecondary: '#999',
    background: '#0a0a0a',
    card: '#1a1a1a',
    tint: accent,
    tabIconDefault: '#555',
    tabIconSelected: accent,
    border: '#2a2a2a',
    accent,
  },
};
