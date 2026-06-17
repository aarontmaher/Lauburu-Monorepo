/**
 * SamsungControllerHome — phone-first compact Admin/Dev controller.
 *
 * Designed for Samsung-class screen widths (≤ 380dp): one column,
 * tile rows ~ 64–96dp, no horizontal scroll, no rich text. Renders
 * three primary lanes (claude / codex / agent) plus the MCP
 * automation loops (bridge-watch / mcp-poll / prompt-dry-run) the
 * dispatcher exposes, each with a clear status, age, freshness
 * label, evidence label, and the recommended next prompt where MCP
 * supplies it.
 *
 * Honest by construction:
 *   - every status line is derived from the props the screen
 *     already computes (LaneProgressEntry / AndroidControllerContext
 *     / ControllerNotificationDecision);
 *   - the evidence label per tile makes repo-only / preview-only /
 *     installed-build verified visible at a glance — no tile claims
 *     live-now without server evidence;
 *   - action buttons surface intent only (copy commands, open
 *     approvals); no remote shell, no release actions, no upload.
 */
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { spacing, radii, typography, colors } from '../theme';
import { StatusPill } from './primitives/StatusPill';
import type { Tone } from './primitives/_helpers';
import type { AndroidControllerContext } from '../services/android-controller-context';
import type { LaneProgressEntry } from '../services/lane-progress-summary';
import type {
  ControllerNotificationDecision,
} from '../services/controller-notification-decisions';
import type { ControllerEvidenceLabel } from '../services/controller-overview-client';

/**
 * Automation-loop ids the dispatcher exposes (docs/PROMPT_DISPATCHER.md).
 * Treated as auxiliary lanes — visible when the lane summary lists
 * them, hidden when MCP doesn't yet emit them.
 */
const AUTOMATION_LOOPS: ReadonlyArray<string> = ['bridge-watch', 'mcp-poll', 'prompt-dry-run'];
const PRIMARY_LANES: ReadonlyArray<string> = ['claude', 'codex', 'agent'];

export interface SamsungControllerHomeProps {
  context: AndroidControllerContext;
  lanes: ReadonlyArray<LaneProgressEntry>;
  topPriority: string | null;
  recommendedNextAction: string | null;
  approvalsPending: number;
  topDecision: ControllerNotificationDecision | null;
  decisionCount: number;
  /** When false, the screen renders a soft "notifications muted" hint. */
  notificationsEnabled: boolean;
  onCopyText: (label: string, text: string) => void;
  onOpenApprovals: () => void;
  onAcknowledgeDecision: (key: string) => void;
}

function laneTone(idleStatus: LaneProgressEntry['idleStatus'], freshness: LaneProgressEntry['freshness']): Tone {
  if (idleStatus === 'blocked' || idleStatus === 'needs_user') return 'danger';
  if (idleStatus === 'needs_review' || idleStatus === 'complete_waiting_approval') return 'warning';
  if (freshness === 'stale') return 'warning';
  if (idleStatus === 'working') return 'fresh';
  if (idleStatus === 'idle' || idleStatus === 'stale') return 'info';
  return 'neutral';
}

function freshnessTone(freshness: AndroidControllerContext['mcp']['freshness']): Tone {
  if (freshness === 'fresh') return 'fresh';
  if (freshness === 'stale') return 'warning';
  return 'danger';
}

function gateTone(state: AndroidControllerContext['gates']['build']): Tone {
  if (state === 'clear') return 'fresh';
  if (state === 'partial') return 'warning';
  if (state === 'blocked') return 'danger';
  return 'neutral';
}

function evidenceTone(label: ControllerEvidenceLabel): Tone {
  switch (label) {
    case 'live-now':
      return 'fresh';
    case 'installed-build verified':
      return 'fresh';
    case 'preview-only':
      return 'info';
    case 'repo-only':
      return 'warning';
    case 'planned-only':
    default:
      return 'neutral';
  }
}

interface LaneTileProps {
  lane: LaneProgressEntry;
  isPrimary: boolean;
  onCopyPrompt: () => void;
}

function LaneTile({ lane, isPrimary, onCopyPrompt }: LaneTileProps) {
  const promptText = lane.recommendedNextPromptSummary
    ?? lane.recommendedNextPrompt
    ?? lane.taskSummary
    ?? null;
  return (
    <View style={[styles.tile, isPrimary ? styles.tilePrimary : styles.tileAux]}>
      <View style={styles.tileHeader}>
        <Text style={styles.tileTitle}>{lane.id}</Text>
        <StatusPill label={lane.idleStatus} tone={laneTone(lane.idleStatus, lane.freshness)} />
      </View>
      <Text style={styles.tileMeta}>
        {lane.freshness} · {lane.ageLabel}
        {lane.progressPct != null ? ` · ${lane.progressPct}%` : ''}
      </Text>
      <Text style={styles.tileBody} numberOfLines={2}>
        {promptText ?? 'No prompt recommendation yet.'}
      </Text>
      {promptText != null && (
        <Pressable
          accessibilityRole="button"
          style={styles.tileAction}
          onPress={onCopyPrompt}>
          <Text style={styles.tileActionText}>Copy {lane.id} prompt</Text>
        </Pressable>
      )}
    </View>
  );
}

export function SamsungControllerHome(props: SamsungControllerHomeProps) {
  const {
    context,
    lanes,
    topPriority,
    recommendedNextAction,
    approvalsPending,
    topDecision,
    decisionCount,
    notificationsEnabled,
    onCopyText,
    onOpenApprovals,
    onAcknowledgeDecision,
  } = props;

  const primaryLanes = PRIMARY_LANES
    .map((id) => lanes.find((lane) => lane.id === id))
    .filter((lane): lane is LaneProgressEntry => lane != null);
  const automationLoops = AUTOMATION_LOOPS
    .map((id) => lanes.find((lane) => lane.id === id))
    .filter((lane): lane is LaneProgressEntry => lane != null);
  const otherLanes = lanes.filter(
    (lane) => !PRIMARY_LANES.includes(lane.id) && !AUTOMATION_LOOPS.includes(lane.id),
  );

  return (
    <View style={styles.root}>
      <View style={styles.headerRow}>
        <Text style={styles.heading}>Samsung controller</Text>
        <StatusPill
          label={`MCP ${context.mcp.freshness}`}
          tone={freshnessTone(context.mcp.freshness)}
        />
      </View>
      <Text style={styles.subheading} numberOfLines={2}>
        {topPriority ?? 'No top priority loaded.'}
      </Text>
      <Text style={styles.next} numberOfLines={2}>
        Next: {recommendedNextAction ?? '—'}
      </Text>

      {topDecision && notificationsEnabled && (
        <View style={[styles.banner, bannerStyleFor(topDecision.category)]}>
          <View style={styles.bannerHeader}>
            <Text style={styles.bannerTitle} numberOfLines={1}>{topDecision.title}</Text>
            <StatusPill label={topDecision.evidenceLabel} tone={evidenceTone(topDecision.evidenceLabel)} />
          </View>
          <Text style={styles.bannerBody} numberOfLines={3}>{topDecision.body}</Text>
          <View style={styles.bannerActions}>
            {decisionCount > 1 && (
              <Text style={styles.bannerMeta}>+ {decisionCount - 1} more</Text>
            )}
            {topDecision.category === 'approval_needed' ? (
              <Pressable style={styles.bannerBtn} onPress={onOpenApprovals}>
                <Text style={styles.bannerBtnText}>Open approvals</Text>
              </Pressable>
            ) : null}
            <Pressable
              style={[styles.bannerBtn, styles.bannerBtnSecondary]}
              onPress={() => onAcknowledgeDecision(topDecision.dedupeKey)}>
              <Text style={styles.bannerBtnText}>Mute 5m</Text>
            </Pressable>
          </View>
        </View>
      )}

      <View style={styles.metricsGrid}>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>Approvals</Text>
          <Text style={styles.metricValue}>{approvalsPending}</Text>
        </View>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>Audit queue</Text>
          <Text style={styles.metricValue}>{context.queues.auditCount}</Text>
        </View>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>Overnight</Text>
          <Text style={styles.metricValue}>{context.queues.overnightCount}</Text>
        </View>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>Build gate</Text>
          <StatusPill label={context.gates.build} tone={gateTone(context.gates.build)} />
        </View>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>QA gate</Text>
          <StatusPill label={context.gates.qa} tone={gateTone(context.gates.qa)} />
        </View>
        <View style={styles.metricCell}>
          <Text style={styles.metricLabel}>Health Connect</Text>
          <StatusPill
            label={context.healthConnect.state}
            tone={
              context.healthConnect.state === 'connected'
                ? 'fresh'
                : context.healthConnect.state === 'permission_needed' || context.healthConnect.state === 'sync_failed'
                  ? 'danger'
                  : 'warning'
            }
          />
        </View>
      </View>

      <Text style={styles.sectionLabel}>Lanes</Text>
      {primaryLanes.length === 0 ? (
        <Text style={styles.muted}>No primary lane data yet.</Text>
      ) : (
        primaryLanes.map((lane) => (
          <LaneTile
            key={lane.id}
            lane={lane}
            isPrimary
            onCopyPrompt={() => {
              const prompt = lane.recommendedNextPromptSummary
                ?? lane.recommendedNextPrompt
                ?? lane.taskSummary
                ?? '';
              onCopyText(`${lane.id} prompt`, prompt);
            }}
          />
        ))
      )}

      {automationLoops.length > 0 && (
        <>
          <Text style={styles.sectionLabel}>Automation loops</Text>
          {automationLoops.map((lane) => (
            <LaneTile
              key={lane.id}
              lane={lane}
              isPrimary={false}
              onCopyPrompt={() => onCopyText(
                `${lane.id} prompt`,
                lane.recommendedNextPromptSummary ?? lane.recommendedNextPrompt ?? lane.taskSummary ?? '',
              )}
            />
          ))}
        </>
      )}

      {otherLanes.length > 0 && (
        <>
          <Text style={styles.sectionLabel}>Other lanes</Text>
          {otherLanes.slice(0, 4).map((lane) => (
            <LaneTile
              key={lane.id}
              lane={lane}
              isPrimary={false}
              onCopyPrompt={() => onCopyText(
                `${lane.id} prompt`,
                lane.recommendedNextPromptSummary ?? lane.recommendedNextPrompt ?? lane.taskSummary ?? '',
              )}
            />
          ))}
        </>
      )}

      <Text style={styles.sectionLabel}>Audit Runner</Text>
      <View style={styles.commandList}>
        <CommandRow
          label="Start audit"
          body={context.auditRunner.startAuditCommand}
          onPress={() => onCopyText('Start audit', context.auditRunner.startAuditCommand)}
        />
        <CommandRow
          label="Screenshot"
          body={context.auditRunner.screenshotCommand}
          onPress={() => onCopyText('Screenshot', context.auditRunner.screenshotCommand)}
        />
        <CommandRow
          label="Video capture"
          body={context.auditRunner.videoCommand}
          onPress={() => onCopyText('Video capture', context.auditRunner.videoCommand)}
        />
      </View>
      <Text style={styles.disclaimer}>
        Mirror/simulator evidence finds bugs but cannot clear installed-device gates.
        No Play, TestFlight, EAS, upload, or release action runs from this controller.
      </Text>
      {!notificationsEnabled && (
        <Text style={styles.disclaimer}>Controller notifications muted in Admin/Dev settings.</Text>
      )}
    </View>
  );
}

interface CommandRowProps {
  label: string;
  body: string;
  onPress: () => void;
}

function CommandRow({ label, body, onPress }: CommandRowProps) {
  return (
    <Pressable style={styles.commandRow} onPress={onPress}>
      <Text style={styles.commandLabel}>{label}</Text>
      <Text style={styles.commandBody} numberOfLines={1}>{body}</Text>
    </Pressable>
  );
}

function bannerStyleFor(category: ControllerNotificationDecision['category']) {
  switch (category) {
    case 'mcp_stale':
    case 'lane_blocked':
    case 'installed_device_qa_needed':
      return { backgroundColor: colors.dangerSoft };
    case 'approval_needed':
      return { backgroundColor: colors.warningSoft };
    case 'all_lanes_idle':
    case 'idle_lane':
    default:
      return { backgroundColor: colors.infoSoft };
  }
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.sm,
    paddingVertical: spacing.sm,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  heading: { ...typography.h2, fontWeight: '700' },
  subheading: { ...typography.body, fontWeight: '600' },
  next: { ...typography.caption, color: colors.textMuted ?? '#666' },
  banner: {
    padding: spacing.sm,
    borderRadius: radii.md,
    gap: 4,
  },
  bannerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  bannerTitle: { ...typography.body, fontWeight: '700', flexShrink: 1 },
  bannerBody: { ...typography.caption },
  bannerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: 4,
    flexWrap: 'wrap',
  },
  bannerBtn: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.pill,
    backgroundColor: colors.accentSoft ?? '#cce',
  },
  bannerBtnSecondary: {
    backgroundColor: colors.neutralSoft ?? '#eee',
  },
  bannerBtnText: { ...typography.caption, fontWeight: '700' },
  bannerMeta: { ...typography.caption, color: colors.textMuted ?? '#666' },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  metricCell: {
    flexBasis: '30%',
    minWidth: 96,
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    borderRadius: radii.md,
    backgroundColor: colors.neutralSoft ?? '#f4f4f4',
    gap: 4,
  },
  metricLabel: { ...typography.caption, fontWeight: '600' },
  metricValue: { ...typography.body, fontWeight: '700' },
  sectionLabel: {
    ...typography.caption,
    fontWeight: '700',
    marginTop: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  tile: {
    padding: spacing.sm,
    borderRadius: radii.md,
    gap: 4,
  },
  tilePrimary: {
    backgroundColor: colors.accentSoft ?? '#dde6f4',
  },
  tileAux: {
    backgroundColor: colors.neutralSoft ?? '#f0f0f0',
  },
  tileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  tileTitle: { ...typography.body, fontWeight: '700', textTransform: 'lowercase' },
  tileMeta: { ...typography.caption, color: colors.textMuted ?? '#666' },
  tileBody: { ...typography.caption },
  tileAction: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.pill,
    backgroundColor: colors.neutralSoft ?? '#e5e5e5',
  },
  tileActionText: { ...typography.caption, fontWeight: '700' },
  muted: { ...typography.caption, color: colors.textMuted ?? '#666' },
  commandList: { gap: 4 },
  commandRow: {
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    borderRadius: radii.md,
    backgroundColor: colors.neutralSoft ?? '#f4f4f4',
  },
  commandLabel: { ...typography.caption, fontWeight: '700' },
  commandBody: { ...typography.caption, color: colors.textMuted ?? '#444', fontFamily: 'Courier' },
  disclaimer: { ...typography.caption, color: colors.textMuted ?? '#666' },
});
