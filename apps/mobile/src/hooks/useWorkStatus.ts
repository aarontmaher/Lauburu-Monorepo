/**
 * Hook to fetch agent work status from MCP HTTP API.
 * Polls every 30s while active (matches website auto-refresh).
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { getWorkStatus } from '@lauburu/shared';
import type { WorkStatusResponse } from '@lauburu/shared';

const POLL_INTERVAL = 30_000;

export function useWorkStatus() {
  const [data, setData] = useState<WorkStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await getWorkStatus();
      setData(result);
      setError(result ? null : 'Could not reach Control Centre');
    } catch {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, POLL_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refresh]);

  return { data, loading, error, refresh };
}
