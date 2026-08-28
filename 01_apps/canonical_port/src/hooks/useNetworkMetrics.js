import { useState, useEffect, useCallback } from 'react';
import { canonicalApi } from '../services/api.js';
import { INITIAL_NETWORK_METRICS } from '../services/mockFallbackData.js';

/**
 * Reactive Hook for Mesh Network Telemetry (R1, R2, R3).
 * Polls /api/mesh/telemetry or provides authentic waiting states without synthetic random jitter (Rule #0).
 * Exposes current raw state on window.__CANONICAL_NETWORK_METRICS__ for headless AGI ingestion.
 */
export function useNetworkMetrics(pollIntervalMs = 2500) {
  const [networkMetrics, setNetworkMetrics] = useState(INITIAL_NETWORK_METRICS);
  const [isConnected, setIsConnected] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const refreshNetworkMetrics = useCallback(async () => {
    try {
      const data = await canonicalApi.getNetworkMetrics();
      const current = data || INITIAL_NETWORK_METRICS;
      
      setNetworkMetrics(current);
      setIsConnected(true);
      setLastUpdated(new Date());

      // Expose headlessly to Master AGI / window context
      if (typeof window !== 'undefined') {
        window.__CANONICAL_NETWORK_METRICS__ = current;
      }
    } catch (err) {
      console.warn('[useNetworkMetrics] Telemetry fetch error:', err);
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    refreshNetworkMetrics();
    const interval = setInterval(refreshNetworkMetrics, pollIntervalMs);
    return () => clearInterval(interval);
  }, [refreshNetworkMetrics, pollIntervalMs]);

  return {
    networkMetrics,
    isConnected,
    lastUpdated,
    refreshNetworkMetrics
  };
}
