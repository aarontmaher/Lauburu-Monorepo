/**
 * External device source model.
 *
 * Lightweight abstraction for devices that feed data into the app.
 * No direct vendor integration yet — manual source path first,
 * with clear insertion points for future BLE/API connections.
 */

export type DeviceCategory = 'heart_rate_monitor' | 'respiratory_device' | 'machine' | 'other';

export type DeviceConnectionMode = 'manual' | 'bluetooth' | 'api' | 'healthkit';

export interface DeviceSource {
  id: string;
  category: DeviceCategory;
  name: string;
  manufacturer?: string;
  model?: string;
  connection_mode: DeviceConnectionMode;
  /** Whether this device is currently active/paired */
  active: boolean;
  last_used_at?: string;
}

/** Known device registry — for picker UX */
export interface KnownDevice {
  id: string;
  category: DeviceCategory;
  name: string;
  manufacturer: string;
  connection_modes: DeviceConnectionMode[];
}

export const KNOWN_DEVICES: KnownDevice[] = [
  // HR monitors
  { id: 'polar_h10', category: 'heart_rate_monitor', name: 'Polar H10', manufacturer: 'Polar', connection_modes: ['bluetooth', 'healthkit'] },
  { id: 'polar_h9', category: 'heart_rate_monitor', name: 'Polar H9', manufacturer: 'Polar', connection_modes: ['bluetooth', 'healthkit'] },
  { id: 'polar_verity', category: 'heart_rate_monitor', name: 'Polar Verity Sense', manufacturer: 'Polar', connection_modes: ['bluetooth', 'healthkit'] },
  { id: 'garmin_hrm', category: 'heart_rate_monitor', name: 'Garmin HRM', manufacturer: 'Garmin', connection_modes: ['bluetooth', 'healthkit'] },
  { id: 'whoop_band', category: 'heart_rate_monitor', name: 'WHOOP Band', manufacturer: 'WHOOP', connection_modes: ['api'] },
  { id: 'apple_watch', category: 'heart_rate_monitor', name: 'Apple Watch', manufacturer: 'Apple', connection_modes: ['healthkit'] },
  { id: 'other_hrm', category: 'heart_rate_monitor', name: 'Other HR Monitor', manufacturer: 'Other', connection_modes: ['bluetooth', 'manual'] },

  // Respiratory
  { id: 'airofit', category: 'respiratory_device', name: 'Airofit', manufacturer: 'Airofit', connection_modes: ['manual'] },
  { id: 'wello2', category: 'respiratory_device', name: 'WellO2', manufacturer: 'WellO2', connection_modes: ['manual'] },
  { id: 'powerbreathe', category: 'respiratory_device', name: 'POWERbreathe', manufacturer: 'POWERbreathe', connection_modes: ['manual'] },
  { id: 'other_resp', category: 'respiratory_device', name: 'Other Respiratory', manufacturer: 'Other', connection_modes: ['manual'] },

  // Machines (future FTMS/BLE)
  { id: 'rogue_echo', category: 'machine', name: 'Rogue Echo Bike', manufacturer: 'Rogue', connection_modes: ['bluetooth', 'manual'] },
  { id: 'rogue_echo_v3', category: 'machine', name: 'Rogue Echo Bike V3', manufacturer: 'Rogue', connection_modes: ['bluetooth', 'manual'] },
  { id: 'concept2_rower', category: 'machine', name: 'Concept2 Rower', manufacturer: 'Concept2', connection_modes: ['bluetooth', 'manual'] },
  { id: 'concept2_skierg', category: 'machine', name: 'Concept2 SkiErg', manufacturer: 'Concept2', connection_modes: ['bluetooth', 'manual'] },
  { id: 'other_machine', category: 'machine', name: 'Other Machine', manufacturer: 'Other', connection_modes: ['manual'] },
];

export const DEVICE_CATEGORY_LABELS: Record<DeviceCategory, string> = {
  heart_rate_monitor: 'Heart Rate Monitor',
  respiratory_device: 'Respiratory Device',
  machine: 'Machine',
  other: 'Other',
};
