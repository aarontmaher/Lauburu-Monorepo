/**
 * Hook to fetch prompt jobs from MCP HTTP API.
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { listPromptJobs } from '@lauburu/shared';
import type { PromptJob } from '@lauburu/shared';

const POLL_INTERVAL = 30_000;

export function usePromptJobs() {
  const [jobs, setJobs] = useState<PromptJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const data = await listPromptJobs();
      if (!mountedRef.current) return;
      setJobs(data ?? []);
      setError(data ? null : 'Could not load prompt jobs');
    } catch {
      if (!mountedRef.current) return;
      setError('Network error');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    refresh();
    timerRef.current = setInterval(refresh, POLL_INTERVAL);
    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refresh]);

  const pending = jobs.filter((j) => j.status === 'pending');
  const claimed = jobs.filter((j) => j.status === 'claimed');
  const completed = jobs.filter((j) => j.status === 'completed');

  return { jobs, pending, claimed, completed, loading, error, refresh };
}
