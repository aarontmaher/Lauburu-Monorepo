/**
 * Hook to fetch technique progress from Supabase edge function.
 * Uses @lauburu/shared API layer.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { getProgress } from '@lauburu/shared';
import type { ProgressEntry } from '@lauburu/shared';
import { useAuthStore } from '../store/auth-store';

export function useProgress() {
  const status = useAuthStore((s) => s.status);
  const getAccessToken = useAuthStore((s) => s.getAccessToken);
  const [entries, setEntries] = useState<ProgressEntry[]>([]);
  const [loading, setLoading] = useState(status === 'member');
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    if (status !== 'member') {
      if (!mountedRef.current) return;
      setEntries([]);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getProgress(getAccessToken);
      if (!mountedRef.current) return;
      setEntries(data ?? []);
      if (!data) setError('Could not load progress');
    } catch {
      if (!mountedRef.current) return;
      setError('Network error');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [status, getAccessToken]);

  useEffect(() => {
    mountedRef.current = true;
    if (status !== 'member') {
      setEntries([]);
      setError(null);
      setLoading(false);
      return () => {
        mountedRef.current = false;
      };
    }
    refresh();
    return () => {
      mountedRef.current = false;
    };
  }, [status, refresh]);

  const drilling = entries.filter((e) => e.status === 'drilling').length;
  const learned = entries.filter((e) => e.status === 'learned').length;

  return { entries, drilling, learned, loading, error, refresh };
}
