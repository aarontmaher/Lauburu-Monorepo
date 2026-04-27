import { useEffect, useMemo, useState } from 'react';

import type { VideoAttachmentSummary } from '@lauburu/shared';

import {
  buildAthleteMemoryClientConfig,
  fetchVideoAttachments,
} from '../services/athlete-memory-client';
import { useAuthStore } from '../store/auth-store';

export function useVideoAttachmentSummaries(belt?: string | null) {
  const authUserId = useAuthStore((s) => s.user?.id);
  const authAccessToken = useAuthStore((s) => s.session?.access_token ?? null);
  const [items, setItems] = useState<VideoAttachmentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const config = buildAthleteMemoryClientConfig(authUserId, authAccessToken);
      if (!config) {
        if (!cancelled) {
          setItems([]);
          setError('Sign in to load your video attachment summaries.');
          setLoading(false);
        }
        return;
      }
      const { data, error: nextError } = await fetchVideoAttachments(
        config,
        belt ?? undefined,
      );
      if (cancelled) return;
      setItems(data?.items ?? []);
      setError(nextError);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [authUserId, authAccessToken, belt]);

  const byTargetId = useMemo(() => {
    const next = new Map<string, VideoAttachmentSummary>();
    for (const item of items) next.set(item.targetId, item);
    return next;
  }, [items]);

  return { items, byTargetId, loading, error };
}
