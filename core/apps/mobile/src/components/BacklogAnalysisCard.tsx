/**
 * First-run permission card for backlog analysis.
 *
 * Renders when the user is signed-in AND the backend says the status
 * is 'not_started' (or no record exists). Lets the user:
 *   - tap "Analyse my history" to start a 30-day backlog run
 *   - tap "Not now" to record a skip (suppresses the card)
 *   - learn what data the scan will consider
 *
 * Never auto-starts. Never silently promotes memory. The card is
 * explicit about data scope, privacy, and the provisional nature of
 * what the scan produces.
 *
 * Once analysis finishes, the same card flips into a compact
 * "What Coach can tell so far" summary — users see the data found,
 * early patterns, what's missing, and safe next steps without
 * leaving the Home tab. A "Review memory proposals" footer link
 * appears only when at least one candidate cleared eligibility.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useBacklogAnalysisStore } from '../store/backlog-analysis-store';
import { useAuthStore } from '../store/auth-store';
import { useHealthStore } from '../store/health-store';

export function BacklogAnalysisCard() {
  const user = useAuthStore((s) => s.user);
  const authStatus = useAuthStore((s) => s.status);
  const status = useBacklogAnalysisStore((s) => s.status);
  const record = useBacklogAnalysisStore((s) => s.record);
  const summary = useBacklogAnalysisStore((s) => s.summary);
  const starting = useBacklogAnalysisStore((s) => s.starting);
  const loading = useBacklogAnalysisStore((s) => s.loading);
  const error = useBacklogAnalysisStore((s) => s.error);
  const refresh = useBacklogAnalysisStore((s) => s.refresh);
  const start = useBacklogAnalysisStore((s) => s.start);
  const skip = useBacklogAnalysisStore((s) => s.skip);

  const historyAccess = useHealthStore((s) => s.historyAccess);
  const requestHistoryAccess = useHealthStore((s) => s.requestHistoryAccess);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);

  const [learnMore, setLearnMore] = useState(false);

  // Fetch once the user is authenticated.
  useEffect(() => {
    if (authStatus === 'member' && user?.id) {
      void refresh();
    }
  }, [authStatus, user?.id, refresh]);

  const visible = useMemo(() => {
    if (authStatus !== 'member' || !user?.id) return false;
    // Hide while the initial status is being fetched to avoid a flash.
    if (loading && !record) return false;
    // Show permission UX until an end state is reached.
    if (status === 'not_started' || status === 'permission_requested') return true;
    // Show the compact summary once the analysis has data to show.
    if (status === 'complete' || status === 'partial') return !!summary;
    // Show a retry row on failure.
    if (status === 'failed') return true;
    // Running: show progress
    if (status === 'running') return true;
    // Skipped: hide the card — user will re-run from Settings.
    return false;
  }, [authStatus, user?.id, loading, record, status, summary]);

  const onStart = useCallback(async () => {
    // 1. Request Health Connect data permissions if not yet granted.
    try { await requestPermissions(); } catch { /* non-fatal */ }

    // 2. Request Health Connect history permission (Android 14+)
    //    for deeper backlog analysis. Graceful if denied or unavailable.
    let historyGranted = false;
    try { historyGranted = await requestHistoryAccess(); } catch { /* non-fatal */ }

    // 3. Start backlog analysis with the appropriate window.
    const windowDays = historyGranted ? 90 : 30;
    void start({ windowDays });
  }, [start, requestPermissions, requestHistoryAccess]);

  const onSkip = useCallback(() => {
    void skip();
  }, [skip]);

  if (!visible) return null;

  // ── Running / pending ──────────────────────────────────────
  if (status === 'running' || starting) {
    return (
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>Analysing your history…</Text>
        </View>
        <View style={styles.bodyRow}>
          <ActivityIndicator color="#d4e157" />
          <Text style={styles.bodyText}>
            Reading connected sources for the last 30 days and building provisional patterns.
          </Text>
        </View>
      </View>
    );
  }

  // ── Failed ───────────────────────────────────────────────
  if (status === 'failed') {
    return (
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>Backlog scan failed</Text>
        </View>
        <Text style={styles.bodyText}>
          {error ?? record?.missingnessNote ?? 'The scan could not complete.'}
        </Text>
        <View style={styles.actions}>
          <Pressable style={styles.primaryBtn} onPress={onStart}>
            <Text style={styles.primaryText}>Try again</Text>
          </Pressable>
          <Pressable style={styles.secondaryBtn} onPress={onSkip}>
            <Text style={styles.secondaryText}>Not now</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  // ── Summary (complete / partial) ───────────────────────────
  if ((status === 'complete' || status === 'partial') && summary) {
    const df = summary.dataFound;
    return (
      <View style={styles.card}>
        <Text style={styles.title}>What Coach can tell so far</Text>
        <Text style={styles.eyebrow}>
          Provisional · confidence {summary.confidence}
          {status === 'partial' ? ' · partial coverage' : ''}
        </Text>

        <SectionLabel>Data found</SectionLabel>
        <Text style={styles.bodyText}>
          {df.normalizedDays} logged day{df.normalizedDays === 1 ? '' : 's'} ·
          {' '}{df.hiitSessions} HIIT session{df.hiitSessions === 1 ? '' : 's'} ·
          {' '}{df.grapplingSessions} grappling · {df.cronometerDays + df.manualNutritionDays} nutrition days
          {df.whoopDays > 0 ? ` · ${df.whoopDays} WHOOP days` : ''}
          {df.healthConnectDays > 0 ? ` · ${df.healthConnectDays} Health Connect days` : ''}
          {df.polarViaHealthConnectDays > 0 ? ` · ${df.polarViaHealthConnectDays} Polar-via-HC days` : ''}.
        </Text>

        {summary.earlyPatterns.length > 0 && (
          <>
            <SectionLabel>Early patterns</SectionLabel>
            {summary.earlyPatterns.slice(0, 4).map((p, i) => (
              <Text style={styles.bullet} key={`p${i}`}>• {p}</Text>
            ))}
          </>
        )}

        {summary.whatsMissing.length > 0 && (
          <>
            <SectionLabel>What's missing</SectionLabel>
            {summary.whatsMissing.slice(0, 4).map((m, i) => (
              <Text style={styles.bullet} key={`m${i}`}>• {m}</Text>
            ))}
          </>
        )}

        {summary.safeNextSteps.length > 0 && (
          <>
            <SectionLabel>Safe next steps</SectionLabel>
            {summary.safeNextSteps.slice(0, 3).map((s, i) => (
              <Text style={styles.bullet} key={`s${i}`}>• {s}</Text>
            ))}
          </>
        )}

        {summary.comparison && summary.comparison.comparisonType !== 'none' && (
          <>
            <SectionLabel>Comparison</SectionLabel>
            <Text style={styles.bodyText}>{summary.comparison.statement}</Text>
          </>
        )}

        {summary.reviewableMemoryCandidateIds.length > 0 && (
          <Text style={styles.reviewableNote}>
            {summary.reviewableMemoryCandidateIds.length} pattern
            {summary.reviewableMemoryCandidateIds.length === 1 ? '' : 's'}
            {' '}ready for your review — open Coach to promote or dismiss.
          </Text>
        )}

        <View style={styles.actions}>
          <Pressable style={styles.secondaryBtn} onPress={onStart}>
            <Text style={styles.secondaryText}>Analyse again</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  // ── Permission prompt (not_started / permission_requested) ──
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Build your athlete context?</Text>
      <Text style={styles.bodyText}>
        With your permission, Coach can analyse your connected health,
        nutrition, and training history to find early patterns. This stays
        private to your account.
      </Text>
      <Text style={styles.historyNote}>
        You'll be asked to grant Health Connect access. On Android 14+,
        a second prompt for history access lets Coach read older data
        (up to 90 days) for better baselines and longer trends.
        {historyAccess === 'granted' ? ' History access: granted.' :
         historyAccess === 'denied' ? ' History access: denied — limited to ~30 days.' :
         historyAccess === 'unavailable' ? ' History access: not available on this device.' : ''}
      </Text>
      {learnMore && (
        <View style={styles.learnMoreBlock}>
          <Text style={styles.learnMoreItem}>• Uses only data you connect or log.</Text>
          <Text style={styles.learnMoreItem}>• Creates provisional patterns, not permanent conclusions.</Text>
          <Text style={styles.learnMoreItem}>• You can review what gets saved as memory.</Text>
          <Text style={styles.learnMoreItem}>
            • Granting history access lets Coach see older sleep, workouts, and
            heart-rate data for sharper baseline detection and longer trend windows.
            You can skip this — Coach will use the last 30 days only.
          </Text>
          <Text style={styles.learnMoreItem}>
            • Anonymous cohort comparisons may be used for confidence, but other
            users' private data is never shown.
          </Text>
          <Text style={styles.learnMoreItem}>
            Sources: Health Connect / Apple Health, Samsung Health via HC, Polar
            via HC, WHOOP (only your own account), Cronometer, nutrition logs,
            HIIT/session logs, machine sessions.
          </Text>
        </View>
      )}
      <Pressable onPress={() => setLearnMore((v) => !v)} hitSlop={6}>
        <Text style={styles.learnMoreToggle}>{learnMore ? 'Hide details' : 'Learn more'}</Text>
      </Pressable>

      <View style={styles.actions}>
        <Pressable
          style={[styles.primaryBtn, starting && styles.btnDisabled]}
          onPress={onStart}
          disabled={starting}>
          {starting ? <ActivityIndicator color="#0a0a0a" /> : <Text style={styles.primaryText}>Analyse my history</Text>}
        </Pressable>
        <Pressable style={styles.secondaryBtn} onPress={onSkip} disabled={starting}>
          <Text style={styles.secondaryText}>Not now</Text>
        </Pressable>
      </View>
    </View>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <Text style={styles.sectionLabel}>{children}</Text>;
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(212, 225, 87, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(212, 225, 87, 0.25)',
    gap: 8,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { fontSize: 17, fontWeight: '700' },
  eyebrow: {
    fontSize: 11,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  bodyRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bodyText: { fontSize: 13, opacity: 0.8, lineHeight: 19 },
  historyNote: { fontSize: 12, opacity: 0.6, lineHeight: 17, marginTop: 2 },
  sectionLabel: {
    fontSize: 11,
    opacity: 0.55,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginTop: 6,
  },
  bullet: { fontSize: 13, opacity: 0.8, lineHeight: 19, marginLeft: 4 },
  learnMoreToggle: { fontSize: 12, color: '#d4e157', marginTop: 2 },
  learnMoreBlock: {
    gap: 4,
    paddingVertical: 6,
    paddingLeft: 4,
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(212, 225, 87, 0.35)',
  },
  learnMoreItem: { fontSize: 12, opacity: 0.7, lineHeight: 17 },
  reviewableNote: {
    fontSize: 12,
    color: '#d4e157',
    marginTop: 6,
    lineHeight: 17,
  },
  actions: { flexDirection: 'row', gap: 8, marginTop: 10, flexWrap: 'wrap' },
  primaryBtn: {
    flex: 1,
    minWidth: 140,
    backgroundColor: '#d4e157',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  primaryText: { color: '#0a0a0a', fontWeight: '700', fontSize: 14 },
  secondaryBtn: {
    minWidth: 100,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  secondaryText: { fontSize: 14, opacity: 0.75 },
  btnDisabled: { opacity: 0.5 },
});
