/**
 * Hook to fetch technique progress from Supabase edge function.
 * Uses @lauburu/shared API layer.
 */
import { useEffect, useState, useCallback } from 'react';
import { getProgress } from '@lauburu/shared';
import type { ProgressEntry } from '@lauburu/shared';
import { useAuthStore } from '../store/auth-store';

export function useProgress() {
  const status = useAuthStore((s) => s.status);
  const getAccessToken = useAuthStore((s) => s.getAccessToken);
  const [entries, setEntries] = useState<ProgressEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (status !== 'member') return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProgress(getAccessToken);
      setEntries(data ?? []);
      if (!data) setError('Could not load progress');
    } catch {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  }, [status, getAccessToken]);

  useEffect(() => {
    if (status !== 'member') {
      setEntries([]);
      setError(null);
      return;
    }
    refresh();
  }, [status, refresh]);

  const drilling = entries.filter((e) => e.status === 'drilling').length;
  const learned = entries.filter((e) => e.status === 'learned').length;

  return { entries, drilling, learned, loading, error, refresh };
}
