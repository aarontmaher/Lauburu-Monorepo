/**
 * Hook to fetch user profile from Supabase edge function.
 * Uses @lauburu/shared API layer.
 */
import { useEffect, useState } from 'react';
import { getProfile } from '@lauburu/shared';
import type { UserProfile } from '@lauburu/shared';
import { useAuthStore } from '../store/auth-store';

export function useProfile() {
  const status = useAuthStore((s) => s.status);
  const getAccessToken = useAuthStore((s) => s.getAccessToken);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== 'member') {
      setProfile(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getProfile(getAccessToken)
      .then((data) => {
        if (!cancelled) {
          setProfile(data);
          if (!data) setError('Could not load profile');
        }
      })
      .catch(() => {
        if (!cancelled) setError('Network error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [status, getAccessToken]);

  return { profile, loading, error };
}
