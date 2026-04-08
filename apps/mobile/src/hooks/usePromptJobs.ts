/**
 * Hook to fetch prompt jobs from MCP HTTP API.
 */
import { useEffect, useState, useCallback } from 'react';
import { listPromptJobs } from '@lauburu/shared';
import type { PromptJob } from '@lauburu/shared';

export function usePromptJobs() {
  const [jobs, setJobs] = useState<PromptJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listPromptJobs();
      setJobs(data ?? []);
      setError(data ? null : 'Could not load prompt jobs');
    } catch {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const pending = jobs.filter((j) => j.status === 'pending');
  const claimed = jobs.filter((j) => j.status === 'claimed');
  const completed = jobs.filter((j) => j.status === 'completed');

  return { jobs, pending, claimed, completed, loading, error, refresh };
}
