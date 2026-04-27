/**
 * Memory proposal review card — shows pending trend + weekly promotion
 * candidates with Accept/Reject/Keep actions.
 *
 * No silent promotion. Every accept requires an explicit user tap.
 * Rejections are informational. The card auto-refreshes after actions.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, Pressable, ActivityIndicator, Alert } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../store/auth-store';
import {
  buildBacklogClientConfig,
  getProposals,
  acceptProposal,
  rejectProposal,
  type ProposalsResponse,
} from '../services/backlog-analysis-client';
import { secureStorage } from '../store/secure-storage';

const ACTED_STORAGE_KEY = 'memory_proposals_acted_v1';

type Proposal = ProposalsResponse['trendProposals'][number] | ProposalsResponse['weeklyCandidates'][number];

export function MemoryProposalReview() {
  const userId = useAuthStore((s) => s.user?.id);
  const accessToken = useAuthStore((s) => s.session?.access_token);
  const authStatus = useAuthStore((s) => s.status);
  const [loading, setLoading] = useState(false);
  const [trendProposals, setTrends] = useState<ProposalsResponse['trendProposals']>([]);
  const [weeklyCandidates, setWeekly] = useState<ProposalsResponse['weeklyCandidates']>([]);
  const [actioning, setActioning] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  // Persistent blocklist of proposal ids the user has already accepted
  // or dismissed. Kept in secureStorage so a backend that doesn't
  // persist accept/reject can't resurrect the same cards on next
  // refresh. A hydrated ref lets us filter server responses without
  // needing to re-render when the set changes.
  const actedIdsRef = useRef<Set<string>>(new Set());
  const [actedHydrated, setActedHydrated] = useState(false);

  // Memoise — without this, `buildBacklogClientConfig` returns a new
  // object every render, `refresh` useCallback gets a new identity,
  // the mount useEffect re-fires, state updates, re-render, new cfg,
  // new refresh, effect fires again … infinite layout-jitter loop.
  // With useMemo keyed on userId+accessToken, `cfg` is stable across
  // renders and the proposals list stops bouncing.
  const cfg = useMemo(
    () => buildBacklogClientConfig(userId, accessToken),
    [userId, accessToken],
  );

  // Hydrate the acted-ids blocklist once per component lifetime.
  useEffect(() => {
    (async () => {
      try {
        const raw = await secureStorage.getItem(ACTED_STORAGE_KEY);
        if (raw) {
          const arr = JSON.parse(raw);
          if (Array.isArray(arr)) actedIdsRef.current = new Set(arr.map(String));
        }
      } catch { /* ignore — start with empty set */ }
      setActedHydrated(true);
    })();
  }, []);

  const persistActed = useCallback(() => {
    try {
      void secureStorage.setItem(
        ACTED_STORAGE_KEY,
        JSON.stringify(Array.from(actedIdsRef.current)),
      );
    } catch { /* ignore */ }
  }, []);

  const markActed = useCallback((id: string | number) => {
    actedIdsRef.current.add(String(id));
    persistActed();
  }, [persistActed]);

  const filterActed = useCallback(<T extends { id?: unknown; index?: unknown }>(items: T[]): T[] => {
    const blocked = actedIdsRef.current;
    return items.filter((item) => {
      const key = 'id' in item && item.id != null ? String(item.id) : 'index' in item && item.index != null ? String(item.index) : '';
      return !blocked.has(key);
    });
  }, []);

  const refresh = useCallback(async () => {
    if (!cfg) return;
    setLoading(true);
    const res = await getProposals(cfg);
    setLoading(false);
    if (res.ok) {
      setTrends(filterActed(res.data.trendProposals));
      setWeekly(filterActed(res.data.weeklyCandidates));
    }
  }, [cfg, filterActed]);

  useEffect(() => {
    if (authStatus === 'member' && userId && actedHydrated) void refresh();
  }, [authStatus, userId, actedHydrated, refresh]);

  // Optimistic removal — filter the card out of local state now AND
  // record the id in the persistent blocklist so any future refresh
  // (manual or mount) can't bring it back even if the backend didn't
  // actually persist the action.
  const removeFromLocal = useCallback((id: string | number) => {
    markActed(id);
    setTrends((prev) => prev.filter((p) => String(p.id) !== String(id)));
    setWeekly((prev) => prev.filter((c) => String(c.index) !== String(id)));
  }, [markActed]);

  const handleAccept = useCallback(async (id: string | number, source: string) => {
    if (!cfg) return;
    setActioning(String(id));
    removeFromLocal(id);
    const res = await acceptProposal(cfg, id, source);
    setActioning(null);
    setResult(res.ok ? (res.data?.reason ?? 'Accepted.') : 'Accepted locally (backend did not confirm).');
    // Do NOT auto-refresh after Accept — the optimistic removal +
    // persistent blocklist is the source of truth now. A silent
    // refresh would race with the ack and could resurrect the card
    // if the backend doesn't persist accepts yet.
  }, [cfg, removeFromLocal]);

  const handleReject = useCallback(async (id: string | number, source: string) => {
    if (!cfg) return;
    Alert.alert('Dismiss this proposal?', 'This does not change your memory.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Dismiss',
        onPress: async () => {
          setActioning(String(id));
          removeFromLocal(id);
          const res = await rejectProposal(cfg, id, source);
          setActioning(null);
          setResult(res.ok ? 'Dismissed.' : 'Dismissed locally (backend did not confirm).');
          // Same reason as Accept — skip auto-refresh.
        },
      },
    ]);
  }, [cfg, removeFromLocal]);

  if (authStatus !== 'member' || !userId) return null;

  const total = trendProposals.length + weeklyCandidates.length;

  if (loading && total === 0) {
    return (
      <View style={styles.card}>
        <ActivityIndicator color="#d4e157" />
        <Text style={styles.subtle}>Loading proposals…</Text>
      </View>
    );
  }

  if (total === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>Memory Proposals</Text>
        <Text style={styles.body}>No proposals yet. Run backlog analysis or log more data to generate pattern candidates.</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Memory Proposals ({total})</Text>
      <Text style={styles.subtle}>
        These are provisional patterns. Accept to flag for memory, reject to dismiss, or leave as draft.
      </Text>

      {trendProposals.map((p) => (
        <ProposalRow
          key={p.id}
          statement={p.statement}
          confidence={p.confidence}
          source="backlog_analysis"
          window={`${p.windowStart} → ${p.windowEnd}`}
          observations={p.observationCount}
          actioning={actioning === p.id}
          onAccept={() => handleAccept(p.id, 'backlog_trend')}
          onReject={() => handleReject(p.id, 'backlog_trend')}
        />
      ))}

      {weeklyCandidates.filter((c) => c.eligible).map((c) => (
        <ProposalRow
          key={`w_${c.index}`}
          statement={c.statement}
          confidence={c.confidence}
          source="weekly_synthesis"
          window={`${c.windowStart} → ${c.windowEnd}`}
          observations={null}
          actioning={actioning === String(c.index)}
          onAccept={() => handleAccept(c.index, 'weekly_synthesis')}
          onReject={() => handleReject(c.index, 'weekly_synthesis')}
        />
      ))}

      {result && (
        <Text style={styles.resultText}>{result}</Text>
      )}

      <View style={styles.footerRow}>
        <Pressable
          style={styles.refreshBtn}
          onPress={() => void refresh()}
          disabled={loading}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Refresh proposals">
          {loading ? (
            <ActivityIndicator size="small" color="#d4e157" />
          ) : (
            <Text style={styles.refreshText}>Refresh proposals</Text>
          )}
        </Pressable>
        <Pressable
          style={styles.resetBtn}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Reset dismissed proposals"
          onPress={() => {
            Alert.alert(
              'Reset dismissed proposals?',
              'This clears your local dismiss history so previously acted-on proposals can reappear. Does not change your memory.',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Reset',
                  style: 'destructive',
                  onPress: () => {
                    actedIdsRef.current = new Set();
                    persistActed();
                    setResult('Dismiss history cleared. Tap Refresh proposals.');
                  },
                },
              ],
            );
          }}>
          <Text style={styles.resetText}>Reset dismissed</Text>
        </Pressable>
      </View>
    </View>
  );
}

function ProposalRow({ statement, confidence, source, window: windowStr, observations, actioning, onAccept, onReject }: {
  statement: string;
  confidence: string;
  source: string;
  window: string;
  observations: number | null;
  actioning: boolean;
  onAccept: () => void;
  onReject: () => void;
}) {
  const confColor = confidence === 'high' ? '#4ade80' : confidence === 'medium' ? '#d4e157' : '#888';
  return (
    <View style={styles.proposalRow}>
      <Text style={styles.proposalStatement}>{statement}</Text>
      <View style={styles.proposalMeta}>
        <Text style={[styles.proposalBadge, { color: confColor }]}>{confidence}</Text>
        <Text style={styles.proposalBadge}>{source === 'weekly_synthesis' ? 'weekly' : 'backlog'}</Text>
        {observations != null && <Text style={styles.proposalBadge}>{observations} obs</Text>}
        <Text style={styles.proposalBadge}>{windowStr}</Text>
      </View>
      <View style={styles.proposalActions}>
        <Pressable style={styles.acceptBtn} onPress={onAccept} disabled={actioning}>
          {actioning ? <ActivityIndicator size="small" color="#0a0a0a" /> : <Text style={styles.acceptText}>Accept</Text>}
        </Pressable>
        <Pressable style={styles.rejectBtn} onPress={onReject} disabled={actioning}>
          <Text style={styles.rejectText}>Dismiss</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { padding: 14, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.05)', gap: 10 },
  title: { fontSize: 16, fontWeight: '700' },
  subtle: { fontSize: 12, opacity: 0.5, lineHeight: 17 },
  body: { fontSize: 13, opacity: 0.7, lineHeight: 18 },
  proposalRow: { padding: 10, borderRadius: 8, backgroundColor: 'rgba(255,255,255,0.04)', gap: 6 },
  proposalStatement: { fontSize: 13, lineHeight: 18 },
  proposalMeta: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  proposalBadge: { fontSize: 10, opacity: 0.5, textTransform: 'uppercase' },
  proposalActions: { flexDirection: 'row', gap: 8, marginTop: 4 },
  acceptBtn: { backgroundColor: '#d4e157', paddingVertical: 6, paddingHorizontal: 14, borderRadius: 6, alignItems: 'center' },
  acceptText: { color: '#0a0a0a', fontWeight: '700', fontSize: 12 },
  rejectBtn: { borderWidth: 1, borderColor: 'rgba(255,255,255,0.15)', paddingVertical: 6, paddingHorizontal: 14, borderRadius: 6, alignItems: 'center' },
  rejectText: { fontSize: 12, opacity: 0.6 },
  resultText: { fontSize: 12, color: '#4ade80', marginTop: 4 },
  footerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 4, gap: 12 },
  refreshBtn: {
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.4)',
    backgroundColor: 'rgba(212,225,87,0.06)',
    minWidth: 140,
    minHeight: 40,
    justifyContent: 'center',
  },
  refreshText: { fontSize: 13, color: '#d4e157', fontWeight: '600' },
  resetBtn: { alignItems: 'center', paddingVertical: 10, paddingHorizontal: 10 },
  resetText: { fontSize: 11, color: '#888', textDecorationLine: 'underline' },
});
