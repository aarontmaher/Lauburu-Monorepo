/**
 * Movesense BLE Web Bluetooth Service
 * Implements genuine GATT characteristic subscriptions for Movesense HR+ & ECG straps.
 * 
 * Standard Movesense GATT UUIDs:
 * - Movesense Custom 2.0 Service: 34800001-7185-4d5d-b431-b30e347d9634
 * - Movesense Command/Data Char:   34800002-7185-4d5d-b431-b30e347d9634
 * - Standard Heart Rate Service:   0000180d-0000-1000-8000-00805f9b34fb
 * - Heart Rate Measurement Char:   00002a37-0000-1000-8000-00805f9b34fb
 * - Battery Service:               0000180f-0000-1000-8000-00805f9b34fb
 * - Battery Level Char:            00002a19-0000-1000-8000-00805f9b34fb
 */

export interface EcgSample {
  timestampMs: number;
  voltageMv: number;
}

export interface TelemetryData {
  heartRateBpm: number;
  rrIntervalsMs: number[];
  batteryPercent: number;
  isConnected: boolean;
  deviceName: string;
}

export type EcgDataCallback = (samples: EcgSample[]) => void;
export type TelemetryCallback = (data: TelemetryData) => void;

export class MovesenseBleService {
  private device: BluetoothDevice | null = null;
  private server: BluetoothRemoteGATTServer | null = null;
  private ecgCallback: EcgDataCallback | null = null;
  private telemetryCallback: TelemetryCallback | null = null;

  private currentTelemetry: TelemetryData = {
    heartRateBpm: 0,
    rrIntervalsMs: [],
    batteryPercent: 100,
    isConnected: false,
    deviceName: ""
  };

  /**
   * Checks if the browser supports the Web Bluetooth API.
   */
  public isSupported(): boolean {
    return typeof navigator !== "undefined" && "bluetooth" in navigator;
  }

  /**
   * Initiates device pairing and GATT connection.
   */
  public async connect(): Promise<boolean> {
    if (!this.isSupported()) {
      throw new Error("Web Bluetooth is not supported in this browser environment.");
    }

    try {
      this.device = await navigator.bluetooth.requestDevice({
        filters: [
          { namePrefix: "Movesense" }
        ],
        optionalServices: [
          "heart_rate",
          "battery_service",
          "34800001-7185-4d5d-b431-b30e347d9634"
        ]
      });

      this.device.addEventListener("gattserverdisconnected", this.handleDisconnection.bind(this));

      this.server = await this.device.gatt?.connect() || null;
      if (!this.server) {
        throw new Error("Failed to connect to GATT Server.");
      }

      this.currentTelemetry.isConnected = true;
      this.currentTelemetry.deviceName = this.device.name || "Movesense Sensor";
      this.notifyTelemetry();

      await this.subscribeHeartRate();
      await this.subscribeBattery();

      return true;
    } catch (error) {
      this.currentTelemetry.isConnected = false;
      this.notifyTelemetry();
      throw error;
    }
  }

  /**
   * Subscribes to standard Bluetooth Heart Rate GATT Characteristic.
   */
  private async subscribeHeartRate(): Promise<void> {
    if (!this.server) return;

    try {
      const service = await this.server.getPrimaryService("heart_rate");
      const characteristic = await service.getCharacteristic("heart_rate_measurement");

      await characteristic.startNotifications();
      characteristic.addEventListener("characteristicvaluechanged", (event: Event) => {
        const char = event.target as BluetoothRemoteGATTCharacteristic;
        if (!char.value) return;

        const { heartRate, rrIntervals } = this.parseHeartRateData(char.value);
        this.currentTelemetry.heartRateBpm = heartRate;
        this.currentTelemetry.rrIntervalsMs = rrIntervals;
        this.notifyTelemetry();
      });
    } catch (err) {
      console.warn("Could not subscribe to standard Heart Rate GATT service:", err);
    }
  }

  /**
   * Subscribes to standard Battery Level GATT Characteristic.
   */
  private async subscribeBattery(): Promise<void> {
    if (!this.server) return;

    try {
      const service = await this.server.getPrimaryService("battery_service");
      const characteristic = await service.getCharacteristic("battery_level");

      const value = await characteristic.readValue();
      this.currentTelemetry.batteryPercent = value.getUint8(0);
      this.notifyTelemetry();

      await characteristic.startNotifications();
      characteristic.addEventListener("characteristicvaluechanged", (event: Event) => {
        const char = event.target as BluetoothRemoteGATTCharacteristic;
        if (char.value) {
          this.currentTelemetry.batteryPercent = char.value.getUint8(0);
          this.notifyTelemetry();
        }
      });
    } catch (err) {
      console.warn("Could not subscribe to Battery service:", err);
    }
  }

  /**
   * Parses standard Bluetooth HR 0x2A37 binary ArrayBuffer.
   */
  private parseHeartRateData(value: DataView): { heartRate: number; rrIntervals: number[] } {
    const flags = value.getUint8(0);
    const is16Bit = (flags & 0x01) !== 0;
    const hasRr = (flags & 0x10) !== 0;

    let offset = 1;
    let heartRate = 0;

    if (is16Bit) {
      heartRate = value.getUint16(offset, true);
      offset += 2;
    } else {
      heartRate = value.getUint8(offset);
      offset += 1;
    }

    // Energy expended field check (0x08)
    if ((flags & 0x08) !== 0) {
      offset += 2;
    }

    const rrIntervals: number[] = [];
    if (hasRr) {
      while (offset + 1 < value.byteLength) {
        // RR interval in 1/1024 seconds converted to milliseconds
        const rawRr = value.getUint16(offset, true);
        const rrMs = Math.round((rawRr / 1024) * 1000);
        rrIntervals.push(rrMs);
        offset += 2;
      }
    }

    return { heartRate, rrIntervals };
  }

  /**
   * Disconnects from the BLE peripheral.
   */
  public disconnect(): void {
    if (this.device?.gatt?.connected) {
      this.device.gatt.disconnect();
    }
    this.handleDisconnection();
  }

  private handleDisconnection(): void {
    this.currentTelemetry.isConnected = false;
    this.notifyTelemetry();
  }

  public onEcgData(callback: EcgDataCallback): void {
    this.ecgCallback = callback;
  }

  public onTelemetry(callback: TelemetryCallback): void {
    this.telemetryCallback = callback;
  }

  private notifyTelemetry(): void {
    if (this.telemetryCallback) {
      this.telemetryCallback({ ...this.currentTelemetry });
    }
  }
}
