/**
 * Expo Go detection — isolated from all native module paths.
 * This file must have ZERO imports from native health packages
 * or anything that could crash in Expo Go.
 */
let _cached: boolean | null = null;

export function isExpoGo(): boolean {
  if (_cached !== null) return _cached;
  try {
    const Constants = require('expo-constants');
    const mod = Constants?.default ?? Constants;
    _cached = mod?.appOwnership === 'expo';
  } catch {
    _cached = false;
  }
  return _cached;
}
