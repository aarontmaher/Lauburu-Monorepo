/**
 * Machine connection state — tracks which workout devices
 * are available for HIIT data ingestion.
 */

import type { HIITMachineProvider } from '../../types/hiit-workout';

export type MachineConnectionStatus =
  | 'connected'
  | 'not_connected'
  | 'scaffold_only'
  | 'manual_only'
  | 'import_ready';

export interface MachineConnectionRecord {
  provider: HIITMachineProvider;
  status: MachineConnectionStatus;
  lastDataAt: string | null;
  capabilities: string[];
  reason: string | null;
}

export interface MachineConnectionSummary {
  providers: MachineConnectionRecord[];
  hasLiveConnection: boolean;
  primaryFallback: HIITMachineProvider;
}

/** Default state — no live machine connections. */
export function getDefaultMachineConnections(): MachineConnectionSummary {
  return {
    providers: [
      { provider: 'concept2', status: 'not_connected', lastDataAt: null, capabilities: ['watts', 'pace', 'distance', 'calories', 'hr'], reason: 'Concept2 integration not yet wired.' },
      { provider: 'assault_bike_manual', status: 'manual_only', lastDataAt: null, capabilities: ['calories', 'distance'], reason: 'Manual entry from console display.' },
      { provider: 'bluetooth_ftms', status: 'scaffold_only', lastDataAt: null, capabilities: ['watts', 'cadence', 'hr'], reason: 'Bluetooth FTMS not yet implemented.' },
      { provider: 'apple_health_workout', status: 'not_connected', lastDataAt: null, capabilities: ['calories', 'hr', 'duration'], reason: 'Apple Health workout import not yet wired for HIIT detail.' },
      { provider: 'whoop_workout', status: 'not_connected', lastDataAt: null, capabilities: ['hr', 'strain', 'calories'], reason: 'WHOOP workout detail not yet imported.' },
      { provider: 'manual', status: 'connected', lastDataAt: null, capabilities: ['calories', 'duration', 'sets'], reason: null },
    ],
    hasLiveConnection: false,
    primaryFallback: 'manual',
  };
}
