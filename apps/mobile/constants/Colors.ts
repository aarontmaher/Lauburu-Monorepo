/**
 * Lauburu Grappling Map color palette.
 * Dark theme primary — matches the website's dark UI.
 */
const accent = '#e8ff47'; // Wrestling yellow from website SECTIONS
const accentDim = '#b8cc39';

export default {
  light: {
    text: '#1a1a1a',
    textSecondary: '#666',
    background: '#f5f5f5',
    card: '#fff',
    tint: '#2d6a4f',
    tabIconDefault: '#999',
    tabIconSelected: '#2d6a4f',
    border: '#e0e0e0',
    accent,
  },
  dark: {
    text: '#f0f0f0',
    textSecondary: '#999',
    background: '#0a0a0a',
    card: '#1a1a1a',
    tint: accent,
    tabIconDefault: '#666',
    tabIconSelected: accent,
    border: '#333',
    accent,
  },
};
