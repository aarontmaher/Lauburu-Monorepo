/**
 * Future Rogue Echo Bike / FTMS device connectivity scaffold.
 *
 * This file defines the interface for direct machine connection.
 * Currently returns stubs — no BLE implementation yet.
 *
 * Target protocol: Bluetooth FTMS (Fitness Machine Service)
 * Target devices: Rogue Echo Bike, Rogue connected machines
 *
 * Metrics available via FTMS:
 * - cadence (RPM)
 * - power (watts)
 * - calories
 * - distance
 * - elapsed time
 * - heart rate (if chest strap connected to bike)
 *
 * Architecture:
 * - IBikeService: platform-agnostic interface
 * - Timer screen checks connection state and shows live metrics if available
 * - Phone timer always runs — bike metrics are additive, not required
 *
 * Implementation path when ready:
 * 1. npm install react-native-ble-plx (or expo-ble)
 * 2. Implement scan/connect/subscribe for FTMS service UUID 0x1826
 * 3. Parse Indoor Bike Data characteristic (0x2AD2)
 * 4. Feed parsed metrics to timer-store as live data
 *
 * TODO: Verify Rogue Echo Bike FTMS compliance
 * TODO: Test BLE scan/connect on real device
 * TODO: Determine if Rogue uses standard FTMS or proprietary protocol
 */

export type BikeConnectionState =
  | 'disconnected'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'error';

export interface BikeMetrics {
  cadence_rpm: number | null;
  power_watts: number | null;
  calories: number | null;
  distance_m: number | null;
  elapsed_s: number | null;
  heart_rate: number | null;
}

export interface IBikeService {
  /** Current connection state */
  getState(): BikeConnectionState;

  /** Start scanning for FTMS devices */
  startScan(): Promise<void>;

  /** Stop scanning */
  stopScan(): void;

  /** Connect to a specific device */
  connect(deviceId: string): Promise<boolean>;

  /** Disconnect */
  disconnect(): Promise<void>;

  /** Get latest metrics (null if not connected) */
  getMetrics(): BikeMetrics | null;

  /** Subscribe to metric updates */
  onMetrics(callback: (metrics: BikeMetrics) => void): () => void;
}

/**
 * Stub implementation — returns disconnected state for everything.
 * Replace with real BLE implementation when ready.
 */
export function getBikeService(): IBikeService {
  return {
    getState: () => 'disconnected',
    startScan: async () => {},
    stopScan: () => {},
    connect: async () => false,
    disconnect: async () => {},
    getMetrics: () => null,
    onMetrics: () => () => {},
  };
}
