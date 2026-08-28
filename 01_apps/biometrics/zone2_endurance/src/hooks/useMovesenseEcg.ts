"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { MovesenseBleService, TelemetryData, EcgSample } from "../services/movesenseBleService";

export function useMovesenseEcg() {
  const serviceRef = useRef<MovesenseBleService | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryData>({
    heartRateBpm: 0,
    rrIntervalsMs: [],
    batteryPercent: 100,
    isConnected: false,
    deviceName: ""
  });
  const [recentEcgSamples, setRecentEcgSamples] = useState<EcgSample[]>([]);

  useEffect(() => {
    const service = new MovesenseBleService();
    serviceRef.current = service;
    setIsSupported(service.isSupported());

    service.onTelemetry((data) => {
      setTelemetry(data);
    });

    service.onEcgData((samples) => {
      setRecentEcgSamples((prev) => [...prev.slice(-500), ...samples]);
    });

    return () => {
      service.disconnect();
    };
  }, []);

  const connectDevice = useCallback(async () => {
    if (!serviceRef.current) return;
    setIsConnecting(true);
    setError(null);

    try {
      await serviceRef.current.connect();
    } catch (err: any) {
      if (err.name !== "NotFoundError") {
        setError(err.message || "Failed to pair with Movesense sensor.");
      }
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const disconnectDevice = useCallback(() => {
    if (serviceRef.current) {
      serviceRef.current.disconnect();
    }
  }, []);

  return {
    isSupported,
    isConnecting,
    isConnected: telemetry.isConnected,
    heartRateBpm: telemetry.heartRateBpm,
    rrIntervalsMs: telemetry.rrIntervalsMs,
    batteryPercent: telemetry.batteryPercent,
    deviceName: telemetry.deviceName,
    recentEcgSamples,
    error,
    connectDevice,
    disconnectDevice
  };
}
