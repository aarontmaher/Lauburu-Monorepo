/**
 * Coaching History — local-first self-review surface for completed
 * ChatGPT fallback cases.
 *
 * Consumes the `cases` MRU list from `useCoachingCasesStore` (landed
 * in the ChatGPT fallback batch 38029cd). Lists cases newest first,
 * shows date + readiness + usefulness verdict per row, expands on tap
 * to show the full prompt packet + outcome summary + context snapshot.
 *
 * Intentionally not a chat transcript viewer — this is a structured
 * self-review list that makes the learning data visible inside the
 * app. Future batches can layer on: outcome notes editing, filter by
 * usefulness verdict, export-to-file action, rule-mining insights.
 *
 * Hidden tab (href: null in _layout.tsx), reachable from Home via a
 * small entry card so the Coaching History is discoverable from the
 * same scroll as the Today's Coach card itself.
 */
import { useMemo, useState } from 'react';
import { StyleSheet, ScrollView, Pressable, Share } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useCoachingCasesStore } from '../../src/store/coaching-cases-store';
import type { CoachingCase, CoachingCaseUsefulness } from '@lauburu/shared';

const USEFULNESS_COLOR: Record<CoachingCaseUsefulness, string> = {
  helped: '#4ade80',
  neutral: '#d4e157',
  unhelpful: '#ff8a80',
};

const USEFULNESS_LABEL: Record<CoachingCaseUsefulness, string> = {
  helped: 'Helped',
  neutral: 'Neutral',
  unhelpful: 'Not useful',
};

const READINESS_COLOR: Record<string, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function CaseRow({ c }: { c: CoachingCase }) {
  const [expanded, setExpanded] = useState(false);
  const readinessColor =
    READINESS_COLOR[c.context.readiness ?? 'grey'] ?? '#666';
  const usefulColor = USEFULNESS_COLOR[c.usefulness];

  return (
    <View style={styles.caseWrap}>
      <Pressable style={styles.caseRow} onPress={() => setExpanded(!expanded)}>
        <View style={{ flex: 1 }}>
          <View style={styles.caseHeaderRow}>
            <Text style={styles.caseDate}>
              {formatDate(c.shared_at)}
              <Text style={styles.caseTime}> · {formatTime(c.shared_at)}</Text>
            </Text>
            <Text style={[styles.caseUsefulness, { color: usefulColor }]}>
              {USEFULNESS_LABEL[c.usefulness]}
            </Text>
          </View>
          <View style={styles.caseMetaRow}>
            {c.context.readiness && (
              <View style={styles.readinessChip}>
                <View style={[styles.readinessDot, { backgroundColor: readinessColor }]} />
                <Text style={[styles.readinessText, { color: readinessColor }]}>
                  {c.context.readiness}
                </Text>
              </View>
            )}
            {c.context.whoop_recovery != null && (
              <Text style={styles.caseMetaChip}>
                WHOOP {Math.round(c.context.whoop_recovery)}%
              </Text>
            )}
            {c.context.plan_hint && (
              <Text style={styles.caseMetaChip} numberOfLines={1}>
                {c.context.plan_hint}
              </Text>
            )}
          </View>
        </View>
        <Text style={styles.chevron}>{expanded ? '▾' : '▸'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.caseDetail}>
          {/* Outcome summary first — that's what the user actually wants
              to remember. If not set, show a honest fallback. */}
          <Text style={styles.detailSectionLabel}>Outcome</Text>
          {c.outcome_summary ? (
            <Text style={styles.detailBody}>{c.outcome_summary}</Text>
          ) : (
            <Text style={styles.detailMuted}>
              No outcome notes saved. Only the usefulness verdict is on file.
            </Text>
          )}
          {c.followed != null && (
            <Text style={styles.detailBody}>
              Followed: {c.followed ? 'Yes' : 'No'}
            </Text>
          )}

          {/* Full context snapshot — honest about what the app saw at
              the time of the prompt. Only render fields that are
              actually present. */}
          <Text style={[styles.detailSectionLabel, { marginTop: 10 }]}>
            Context at time of ask
          </Text>
          {c.context.whoop_recovery != null && (
            <Text style={styles.detailBody}>
              WHOOP recovery: {Math.round(c.context.whoop_recovery)}%
            </Text>
          )}
          {c.context.whoop_strain != null && (
            <Text style={styles.detailBody}>
              Day strain: {c.context.whoop_strain.toFixed(1)}
            </Text>
          )}
          {c.context.recent_hard != null && c.context.recent_hard > 0 && (
            <Text style={styles.detailBody}>
              {c.context.recent_hard} hard session
              {c.context.recent_hard === 1 ? '' : 's'} in last 3 days
            </Text>
          )}
          {c.context.nutrition_calories != null && (
            <Text style={styles.detailBody}>
              Calories: {Math.round(c.context.nutrition_calories)}
              {c.context.nutrition_calorie_target
                ? ` / ${Math.round(c.context.nutrition_calorie_target)}`
                : ''} kcal
            </Text>
          )}
          {c.context.nutrition_protein_g != null && (
            <Text style={styles.detailBody}>
              Protein: {Math.round(c.context.nutrition_protein_g)}
              {c.context.nutrition_protein_target
                ? ` / ${Math.round(c.context.nutrition_protein_target)}`
                : ''} g
            </Text>
          )}
          {c.context.user_question && (
            <Text style={styles.detailBody}>
              Asked: {c.context.user_question}
            </Text>
          )}

          {/* Full prompt packet — rendered in a pre-like monospace block
              so the user can see exactly what was sent to ChatGPT. Long
              blocks scroll naturally with the parent ScrollView. */}
          <Text style={[styles.detailSectionLabel, { marginTop: 10 }]}>
            Prompt sent to ChatGPT
          </Text>
          <View style={styles.promptBlock}>
            <Text style={styles.promptText}>{c.prompt_packet}</Text>
          </View>

          {/* Re-share — lets the user send the same packet to ChatGPT
              again without re-generating from current state. Useful for
              "I want to ask the same thing again later" flows. */}
          <Pressable
            style={styles.reshareBtn}
            onPress={() =>
              Share.share({
                message: c.prompt_packet,
                title: 'Lauburu coaching context (re-share)',
              }).catch(() => {})
            }>
            <Text style={styles.reshareBtnText}>Re-share this prompt →</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

export default function CoachingHistoryScreen() {
  const cases = useCoachingCasesStore((s) => s.cases);
  const clearAll = useCoachingCasesStore((s) => s.clearAll);
  const exportJsonlLines = useCoachingCasesStore((s) => s.exportJsonlLines);

  const summary = useMemo(() => {
    const total = cases.length;
    let helped = 0;
    let neutral = 0;
    let unhelpful = 0;
    for (const c of cases) {
      if (c.usefulness === 'helped') helped++;
      else if (c.usefulness === 'neutral') neutral++;
      else unhelpful++;
    }
    return { total, helped, neutral, unhelpful };
  }, [cases]);

  const handleExportAll = () => {
    const lines = exportJsonlLines();
    if (lines.length === 0) return;
    const jsonl = lines.map((l) => JSON.stringify(l)).join('\n');
    Share.share({
      message: jsonl,
      title: `Lauburu coaching cases · ${lines.length} entries`,
    }).catch(() => {});
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.heading}>Coaching History</Text>
        <Text style={styles.subtitle}>
          Past "Ask ChatGPT" sessions and what the app saw when you asked.
        </Text>
      </View>

      {/* Summary strip — three counts, same pattern as Reference */}
      <View style={styles.summaryStrip}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{summary.total}</Text>
          <Text style={styles.summaryLabel}>total</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: USEFULNESS_COLOR.helped }]}>
            {summary.helped}
          </Text>
          <Text style={styles.summaryLabel}>helped</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: USEFULNESS_COLOR.neutral }]}>
            {summary.neutral}
          </Text>
          <Text style={styles.summaryLabel}>neutral</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: USEFULNESS_COLOR.unhelpful }]}>
            {summary.unhelpful}
          </Text>
          <Text style={styles.summaryLabel}>no help</Text>
        </View>
      </View>

      {/* Empty state */}
      {cases.length === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>No cases yet</Text>
          <Text style={styles.emptyBody}>
            Tap "Ask ChatGPT for a second opinion" on the Home coach card to
            start a case. When you come back and record whether it helped,
            the case is saved here for self-review.
          </Text>
        </View>
      )}

      {/* Case list */}
      {cases.map((c) => (
        <CaseRow key={c.id} c={c} />
      ))}

      {/* Footer actions — export + clear. Only shown when there's data. */}
      {cases.length > 0 && (
        <View style={styles.footerActions}>
          <Pressable style={styles.exportBtn} onPress={handleExportAll}>
            <Text style={styles.exportBtnText}>
              Export all as JSONL ({cases.length})
            </Text>
          </Pressable>
          <Pressable
            style={styles.clearBtn}
            onPress={clearAll}>
            <Text style={styles.clearBtnText}>Clear history</Text>
          </Pressable>
        </View>
      )}

      <Text style={styles.footerNote}>
        Local-first — cases live only on this device. Future batches will add
        cross-device sync and offline eval review.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 14, paddingBottom: 40 },

  header: { gap: 4 },
  heading: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 14, opacity: 0.6, lineHeight: 19 },

  summaryStrip: {
    flexDirection: 'row',
    gap: 10,
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryValue: { fontSize: 22, fontWeight: '700', color: '#d4e157' },
  summaryLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 2,
  },

  emptyCard: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 6,
  },
  emptyTitle: { fontSize: 15, fontWeight: '600' },
  emptyBody: { fontSize: 12, opacity: 0.55, lineHeight: 17 },

  caseWrap: {
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    overflow: 'hidden',
  },
  caseRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    padding: 12,
  },
  caseHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: 8,
  },
  caseDate: { fontSize: 13, fontWeight: '600' },
  caseTime: { fontSize: 11, opacity: 0.4, fontWeight: '400' },
  caseUsefulness: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  caseMetaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 6,
  },
  readinessChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  readinessDot: { width: 6, height: 6, borderRadius: 3 },
  readinessText: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  caseMetaChip: {
    fontSize: 10,
    opacity: 0.55,
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.03)',
    maxWidth: 160,
  },
  chevron: { fontSize: 12, opacity: 0.4, paddingTop: 4 },

  caseDetail: {
    padding: 12,
    paddingTop: 0,
    gap: 4,
  },
  detailSectionLabel: {
    fontSize: 10,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  detailBody: { fontSize: 12, opacity: 0.8, lineHeight: 16 },
  detailMuted: { fontSize: 12, opacity: 0.4, fontStyle: 'italic', lineHeight: 16 },

  promptBlock: {
    marginTop: 4,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(0,0,0,0.25)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(212,225,87,0.4)',
  },
  promptText: {
    fontSize: 11,
    fontFamily: 'SpaceMono',
    color: '#c4cdd8',
    lineHeight: 16,
  },

  reshareBtn: {
    alignSelf: 'flex-start',
    marginTop: 10,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.4)',
    backgroundColor: 'rgba(212,225,87,0.05)',
  },
  reshareBtnText: { color: '#d4e157', fontSize: 11, fontWeight: '600' },

  footerActions: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  exportBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.05)',
    alignItems: 'center',
  },
  exportBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  clearBtn: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
    alignItems: 'center',
  },
  clearBtnText: { color: '#888', fontSize: 12 },

  footerNote: {
    fontSize: 10,
    opacity: 0.35,
    fontStyle: 'italic',
    textAlign: 'center',
    lineHeight: 14,
    marginTop: 4,
  },
});
