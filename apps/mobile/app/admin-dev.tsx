/**
 * Admin / Dev Control Center — MVP.
 *
 * Hidden screen reachable only by long-pressing the Settings → About →
 * Version row when signed in as an admin. NOT a tab. NOT a public
 * surface. Read-only this batch — no command execution, no token
 * printing, no workflow_dispatch.
 *
 * Sections:
 *   1. App build / runtime info (from expo-application + expo-updates)
 *   2. Backend health (uses existing internal-token endpoint —
 *      /v1/internal/athletes/:id/ai-health-context)
 *   3. Data / AI status (counts and date range from the same call)
 *   4. Release / status links (Expo, Railway, Play Console reminders)
 *   5. Prompt library (clipboard copy)
 *   6. Status handoff template (clipboard copy)
 *   7. Workflow triggers — placeholders (disabled, copy explains why)
 *
 * Hard rules:
 *   - No tokens or secret values rendered.
 *   - No arbitrary shell. Disabled trigger buttons surface intent only.
 *   - Admin gate by email allowlist (matches Settings tester-tools gate).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, TextInput, Text as RNText } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import * as Application from 'expo-application';
import * as Updates from 'expo-updates';
import Constants from 'expo-constants';

import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../src/store/auth-store';
import { useDevUnlockStore } from '../src/store/dev-unlock-store';
import {
  useOwnerBacklogStore,
  type OwnerBacklogItem,
  type OwnerBacklogPlatform,
  type OwnerBacklogType,
} from '../src/store/owner-backlog-store';
import { useOwnerWorkflowStore } from '../src/store/owner-workflow-store';
import { useAuditEventStore } from '../src/store/audit-event-store';
import { fetchAgentStatus, type AgentStatusEntry } from '../src/services/agent-status-client';
import { fetchConnectorSnapshot, type ConnectorSnapshot } from '../src/services/connector-status-client';
import {
  buildClaudeCodePrompt,
  buildClaudeChromePrompt,
  buildChatGPTStatusPrompt,
  buildCodexPrompt,
  buildTerminalCheckPrompt,
  buildTmuxAttachInstructions,
} from '../src/services/prompt-templates';

const ADMIN_EMAILS = new Set(['aaron.t.maher@gmail.com']);

const EXPO_PROJECT_URL = 'https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map';
const EXPO_BUILDS_URL = `${EXPO_PROJECT_URL}/builds`;
const EXPO_UPDATES_URL = `${EXPO_PROJECT_URL}/updates`;
const RAILWAY_URL = 'https://railway.com/project';
const GITHUB_REPO_URL = 'https://github.com/aaronmaher/lauburu-grappling-map';
const GITHUB_ACTIONS_URL = `${GITHUB_REPO_URL}/actions`;
const PLAY_CONSOLE_URL = 'https://play.google.com/console';
const APPSTORE_CONNECT_URL = 'https://appstoreconnect.apple.com/';

interface BackendHealth {
  ok: boolean;
  totalNormalizedDays: number | null;
  firstDate: string | null;
  lastDate: string | null;
  sourcesConnected: number | null;
  readinessStatus: string | null;
  checkedAt: string;
  error?: string;
}

interface AdminStatus {
  workflowDispatchAvailable: boolean;
  workflowAllowlist: string[];
  blockers: string[];
  androidBuildWorkflowAvailable?: boolean;
  iosBuildWorkflowAvailable?: boolean;
  releaseAuditWorkflowAvailable?: boolean;
  playUploadConfigured?: boolean | null;
  testflightSubmitConfigured?: boolean | null;
  testflightGroupAssignmentConfigured?: boolean | null;
  androidPlayPromoteAutomatic?: boolean | null;
  otaBlocked?: boolean;
  otaBlockerReason?: string;
}

const PROMPT_LIBRARY: Array<{ label: string; body: string }> = [
  {
    label: 'Play metadata blocker status',
    body: 'Chrome is handling Play Console app-content / closed testing setup. Do not rerun Android proof until Chrome confirms play listing fully complete. If complete, rerun Android auto-promote proof once. Do not trigger Production.',
  },
  {
    label: 'Compact ChatGPT status block',
    body: [
      'Print a compact status block for ChatGPT. No secrets, no long logs.',
      '',
      'CHATGPT_STATUS_START',
      'Task:',
      'Live:',
      'Repo-only:',
      'Verified:',
      'Blocker:',
      'Next:',
      'CHATGPT_STATUS_END',
    ].join('\n'),
  },
  {
    label: 'Android AAB next build',
    body: 'Continue automation. Bump apps/mobile/app.json android.versionCode by 1, run mobile typecheck, build a new Android production AAB on EAS, then verify the manifest (CAMERA absent, target API 35) and report the artifact link + Play Console upload steps. Do not touch iOS. Do not run Supabase db push.',
  },
  {
    label: 'AI multi-timeframe trends',
    body: 'Audit /coach/ask + buildTrendsAnswer for any remaining hard-coded windows. Confirm 7/14/30/90/180/365/all-time bundles are produced and the answer header reflects the requested window. If the AI store has fewer normalised days than requested, the answer must say so explicitly. Run typecheck and deploy chat-app to Railway only if backend changed.',
  },
  {
    label: 'App-owned Readiness primary',
    body: 'Verify Lauburu Readiness is the only product-truth readiness. WHOOP/Polar/Health Connect/Samsung must remain evidence sources only. No "Polar readiness" or "WHOOP recovery" surfaced as primary. Surface explicit "evidence-only" framing wherever a third-party readiness might leak through.',
  },
  {
    label: 'Cloud runner workflow plan',
    body: 'Push the local repo to a private GitHub repo, add .github/workflows/deploy-backend.yml (typecheck + railway up on push to main when chat-app or packages/shared changes), and add .github/workflows/eas-android.yml (workflow_dispatch + push to release/android-* triggers eas-cli build). Use ${{ secrets.EXPO_TOKEN }} and ${{ secrets.RAILWAY_TOKEN }} — do not commit any secret values. Output the workflow YAML and setup steps for me to run from my phone.',
  },
  {
    label: 'Admin/Dev Control Center next stage',
    body: 'Extend the in-app Admin/Dev screen: connect the Backend health card to a live /api/admin/status endpoint that returns booleans/counts/links only (no secrets), and wire the Workflow trigger placeholders to a GitHub Actions workflow_dispatch through a signed backend proxy (do not call GitHub directly from the app). Keep it admin-gated.',
  },
];

const STATUS_HANDOFF_TEMPLATE = [
  'CHATGPT_STATUS_START',
  'Task:',
  'Live:',
  'Repo-only:',
  'Verified:',
  'Blocker:',
  'Next:',
  'CHATGPT_STATUS_END',
].join('\n');

/**
 * Top-of-screen workflow truths. These mirror docs/APP_DEVELOPMENTS.md
 * and are intentionally hard-coded for now — the long-term shape is a
 * backend route that serves the same fields. When the doc changes,
 * update these in the next paired build. Keep each line short; the UI
 * renders compact chips, not paragraphs.
 */
const CURRENT_PRIORITY = 'Apple Health (iPhone — Aaron) + Health Connect (Android — girlfriend) usable for daily testing.';
const NEXT_ACTION = 'Track Android v17 GitHub Actions / EAS result, then test Apple Health on iPhone + Health Connect on Android from the paired tester builds.';

function compactGitCommit(value: unknown): string {
  if (typeof value !== 'string') return '—';
  const trimmed = value.trim();
  if (trimmed.length === 0 || trimmed === '${GITHUB_SHA}') return '—';
  return trimmed.length > 12 ? trimmed.slice(0, 12) : trimmed;
}

function connectorFreshnessLabel(checkedAt: string | null | undefined): string {
  if (!checkedAt) return 'not checked';
  const checkedMs = new Date(checkedAt).getTime();
  if (!Number.isFinite(checkedMs)) return 'checked time unknown';
  const ageMinutes = Math.max(0, Math.floor((Date.now() - checkedMs) / 60_000));
  if (ageMinutes >= 10) return `stale · ${ageMinutes}m old`;
  if (ageMinutes >= 1) return `fresh · ${ageMinutes}m old`;
  return 'fresh · just now';
}

function connectorCheckedTime(checkedAt: string | null | undefined): string {
  if (!checkedAt) return '—';
  const checkedMs = new Date(checkedAt).getTime();
  if (!Number.isFinite(checkedMs)) return '—';
  return new Date(checkedAt).toLocaleTimeString();
}

function buildAgentAuditPrompt(snapshot: ConnectorSnapshot | null): string {
  const work = snapshot?.workStatus ?? null;
  const lanes = snapshot?.coderLanes?.lanes ?? [];
  const laneSummary = lanes.length > 0
    ? lanes.map((lane) => `${lane.laneId}:${lane.status}`).join(', ')
    : 'no lanes reported';
  return [
    'PROMPT-ID: AGENT-MOBILE-UX-AUDIT-FROM-PHONE-01',
    'TYPE: AGENT / MOBILE UX AUDIT WORKER',
    'LANE: Mobile app UX audit only',
    '',
    'RULES',
    '- Work only from normal tester/user UX evidence.',
    '- Do not touch backend, Cloudflare, Supabase, MCP auth, health source logic, or app version/build numbers.',
    '- Do not add build triggers, raw terminal control, backlog editing, or paid AI.',
    '- Normal testers must not see Admin/Dev or coder state.',
    '',
    'CURRENT APP-CONTROL STATUS',
    `Priority: ${work?.currentPriority ?? '—'}`,
    `Blocker: ${work?.currentBlocker ?? 'none'}`,
    `Next action: ${work?.nextAction ?? '—'}`,
    `MCP: ${snapshot ? `${snapshot.source} · ${connectorFreshnessLabel(snapshot.checkedAt)}` : 'not connected'}`,
    `Lanes: ${laneSummary}`,
    '',
    'TASK',
    'Audit the mobile app UX from screenshots/device feedback. Identify tester-facing clutter, confusing hierarchy, duplicate actions, and developer/debug text that should be hidden or moved to Admin/Dev. Return findings and the smallest safe mobile-only patch plan.',
    '',
    'OUTPUT',
    '- Findings by screen',
    '- Smallest safe patch',
    '- What must stay untouched',
    '- Manual iPhone/Android verification checklist',
  ].join('\n');
}

/** Static label list for the dynamic prompt-bridge buttons. The
 * body of each prompt is computed at render time from the
 * `useOwnerWorkflowStore` context so changes to priority / blocker
 * / last status flow through without an app rebuild. */
const BRIDGE_PROMPT_KINDS = [
  'claude_code',
  'claude_chrome',
  'chatgpt_status',
  'codex',
  'current_status',
  'terminal_check',
] as const;
type BridgePromptKind = typeof BRIDGE_PROMPT_KINDS[number];

const BRIDGE_PROMPT_LABELS: Record<BridgePromptKind, string> = {
  claude_code: 'Copy next Claude Code prompt',
  claude_chrome: 'Copy Claude Chrome prompt',
  chatgpt_status: 'Copy ChatGPT check / status prompt',
  codex: 'Copy Codex prompt',
  current_status: 'Copy current status block',
  terminal_check: 'Copy terminal check prompt',
};

/** External dashboard / Termius shortcuts. Each is a `Linking.openURL`
 * with a single fallback path documented inline. None of them store
 * credentials; Termius / Play Console / ASC handle their own login. */
const EXTERNAL_SHORTCUTS: Array<{ label: string; url: string; fallbackHint?: string }> = [
  { label: 'Open Termius', url: 'termius://', fallbackHint: 'If Termius is not installed, the App Store opens. tmux attach instructions are also copyable below.' },
  { label: 'Open GitHub Actions', url: GITHUB_ACTIONS_URL },
  { label: 'Open EAS builds', url: EXPO_BUILDS_URL },
  { label: 'Open Play Console', url: PLAY_CONSOLE_URL },
  { label: 'Open App Store Connect', url: APPSTORE_CONNECT_URL },
];

async function fetchAdminStatus(): Promise<AdminStatus | null> {
  try {
    const apiBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
    const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    if (!apiBase || !memToken) return null;
    const res = await fetch(`${apiBase}/admin/status`, { headers: { 'x-athlete-memory-token': memToken } });
    if (!res.ok) return null;
    const json: any = await res.json();
    return {
      workflowDispatchAvailable: !!json?.workflowDispatchAvailable,
      workflowAllowlist: Array.isArray(json?.workflowAllowlist) ? json.workflowAllowlist : [],
      blockers: Array.isArray(json?.blockers) ? json.blockers : [],
      androidBuildWorkflowAvailable: !!json?.androidBuildWorkflowAvailable,
      iosBuildWorkflowAvailable: !!json?.iosBuildWorkflowAvailable,
      releaseAuditWorkflowAvailable: !!json?.releaseAuditWorkflowAvailable,
      playUploadConfigured: typeof json?.playUploadConfigured === 'boolean' ? json.playUploadConfigured : null,
      testflightSubmitConfigured: typeof json?.testflightSubmitConfigured === 'boolean' ? json.testflightSubmitConfigured : null,
      testflightGroupAssignmentConfigured: typeof json?.testflightGroupAssignmentConfigured === 'boolean' ? json.testflightGroupAssignmentConfigured : null,
      androidPlayPromoteAutomatic: typeof json?.androidPlayPromoteAutomatic === 'boolean' ? json.androidPlayPromoteAutomatic : null,
      otaBlocked: !!json?.otaBlocked,
      otaBlockerReason: typeof json?.otaBlockerReason === 'string' ? json.otaBlockerReason : undefined,
    };
  } catch { return null; }
}

async function fetchBackendHealth(): Promise<BackendHealth> {
  const checkedAt = new Date().toISOString();
  try {
    const apiBase = (process.env.EXPO_PUBLIC_AI_BACKEND_URL ?? '').replace(/\/$/, '');
    const internalToken = process.env.EXPO_PUBLIC_INTERNAL_API_TOKEN ?? '';
    const athleteId = process.env.EXPO_PUBLIC_ATHLETE_ID ?? '';
    if (!apiBase || !internalToken || !athleteId) {
      return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: 'Backend env not configured.' };
    }
    const res = await fetch(`${apiBase}/athletes/${encodeURIComponent(athleteId)}/ai-health-context`, {
      headers: { 'x-internal-token': internalToken },
    });
    if (!res.ok) return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: `HTTP ${res.status}` };
    const json: any = await res.json();
    return {
      ok: true,
      totalNormalizedDays: json?.data_coverage?.total_normalized_days ?? null,
      firstDate: json?.data_coverage?.first_date ?? null,
      lastDate: json?.data_coverage?.last_date ?? null,
      sourcesConnected: Array.isArray(json?.sources_connected) ? json.sources_connected.length : null,
      readinessStatus: json?.readiness?.status ?? null,
      checkedAt,
    };
  } catch (e: any) {
    return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: e?.message ?? 'unknown' };
  }
}

export default function AdminDevScreen() {
  const router = useRouter();
  const userEmail = useAuthStore((s) => s.user?.email ?? null);
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail.toLowerCase());
  const devUnlocked = useDevUnlockStore((s) => s.unlocked);
  const lockDevTools = useDevUnlockStore((s) => s.lock);
  const localDevAccess = __DEV__ && devUnlocked;
  const accessGranted = isAdmin || localDevAccess;

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null);
  const [connectorSnapshot, setConnectorSnapshot] = useState<ConnectorSnapshot | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [openPromptIdx, setOpenPromptIdx] = useState<number | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [h, a, c] = await Promise.all([
        fetchBackendHealth(),
        fetchAdminStatus(),
        isAdmin ? fetchConnectorSnapshot() : Promise.resolve(null),
      ]);
      setHealth(h);
      setAdminStatus(a);
      setConnectorSnapshot(c);
    } finally { setRefreshing(false); }
  }, [isAdmin]);

  useEffect(() => { void refresh(); }, [refresh]);

  const buildInfo = useMemo(() => {
    const expoExtra = Constants.expoConfig?.extra as Record<string, unknown> | undefined;
    const easExtra = expoExtra?.eas as Record<string, unknown> | undefined;
    const gitCommit =
      process.env.EXPO_PUBLIC_GIT_COMMIT
      ?? expoExtra?.gitCommit
      ?? easExtra?.gitCommit;
    return {
      appVersion: Application.nativeApplicationVersion ?? '—',
      buildNumber: Application.nativeBuildVersion ?? '—',
      repoHead: compactGitCommit(gitCommit),
      platform: Platform.OS,
      runtimeVersion: Updates.runtimeVersion ?? '—',
      updateId: (Updates as any).updateId ?? null,
      channel: (Updates as any).channel ?? null,
      isEmbeddedLaunch: (Updates as any).isEmbeddedLaunch ?? null,
    };
  }, []);

  // expo-clipboard isn't bundled in the current native build, so we
  // surface prompt text inside selectable RNText blocks. Users
  // long-press to invoke the system copy menu — no new native dep.

  if (!accessGranted) {
    return (
      <View style={styles.container}>
        <Stack.Screen options={{ title: 'Admin / Dev', headerBackTitle: 'Settings' }} />
        <Text style={styles.heading}>Admin / Dev</Text>
        <Text style={styles.body}>
          This screen is gated to the project admin account, or after a local 7-tap unlock on the Settings → About → Version row.
        </Text>
        <Pressable style={styles.btn} onPress={() => router.back()}>
          <Text style={styles.btnText}>Back to Settings</Text>
        </Pressable>
      </View>
    );
  }

  const apiHost = (process.env.EXPO_PUBLIC_AI_BACKEND_URL ?? '').replace(/^https?:\/\//, '').split('/')[0] || '—';

  // Truth chips — derived from adminStatus + buildInfo so the UI can
  // distinguish live / uploaded / repo-only / blocked at a glance.
  const androidPromoteAuto = adminStatus?.androidPlayPromoteAutomatic === true;
  const iosBuildAvailable = adminStatus?.iosBuildWorkflowAvailable === true;
  const androidBuildAvailable = adminStatus?.androidBuildWorkflowAvailable === true;
  const dispatchAvailable = adminStatus?.workflowDispatchAvailable === true;
  const connectorWork = connectorSnapshot?.workStatus ?? null;
  const nowPriority = connectorWork?.currentPriority ?? CURRENT_PRIORITY;
  const nowBlocker = connectorWork?.currentBlocker ?? 'No MCP blocker reported.';
  const nowNextAction = connectorWork?.nextAction ?? NEXT_ACTION;
  const nowLanes = connectorSnapshot?.coderLanes?.lanes ?? [];
  const nowLaneSummary = nowLanes.length > 0
    ? nowLanes.map((lane) => `${lane.laneId}: ${lane.status}`).join(' · ')
    : 'No lane status yet.';
  const mcpStatus = isAdmin
    ? connectorSnapshot
      ? `MCP ${connectorSnapshot.source === 'mcp' ? 'connected' : 'fallback'} · ${connectorFreshnessLabel(connectorSnapshot.checkedAt)} · updated ${connectorCheckedTime(connectorSnapshot.checkedAt)}`
      : refreshing
        ? 'MCP refreshing…'
        : 'MCP not connected'
    : null;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Stack.Screen options={{ title: 'Admin / Dev', headerBackTitle: 'Settings' }} />
      <Text style={styles.heading}>Admin / Dev</Text>
      <Text style={styles.subtitle}>Owner control centre. Compact status. No secrets. No remote shell.</Text>

      <Section title="Now">
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Priority</Text>
          <Text style={styles.chipBody}>{nowPriority}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Blocker</Text>
          <Text style={styles.chipBody}>{nowBlocker}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Next action</Text>
          <Text style={styles.chipBody}>{nowNextAction}</Text>
        </View>
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Lanes</Text>
            <Text style={styles.chipBody}>{nowLaneSummary}</Text>
          </View>
        )}
        {mcpStatus && (
          <Text style={styles.note}>{mcpStatus}</Text>
        )}
      </Section>

      {isAdmin && <ConnectorStatusSection snapshot={connectorSnapshot} refreshing={refreshing} onRefresh={refresh} />}
      <AgentStatusSection />

      <Section title="AI Coach status">
        <Row label="Backend reachable" value={health == null ? '—' : health.ok ? 'yes ✓' : 'no'} />
        <Row label="Trend windows" value="7d / 14d / 30d / 90d / 180d / 365d / all-time" />
        <Row
          label="All-history analysis"
          value={
            health?.ok && health.totalNormalizedDays != null && health.totalNormalizedDays > 0
              ? `enabled (${health.totalNormalizedDays} normalised days)`
              : health?.ok ? 'no data yet — connect Apple Health / Health Connect / WHOOP'
              : '—'
          }
        />
        {health?.ok && (health?.totalNormalizedDays ?? 0) > 0 && (health?.totalNormalizedDays ?? 0) < 95 && (
          <Text style={styles.note}>
            Coverage {health?.totalNormalizedDays}d &lt; 95 — long-term answers say so explicitly.
          </Text>
        )}
        {!health?.ok && (
          <Text style={styles.note}>
            Backend not reachable — Coach answers fall back to deterministic local templates. Trend windows still work over locally-cached normalized days.
          </Text>
        )}
      </Section>

      <Section title="Primary actions">
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android + upload to Internal Testing"
          subtitle="Routine: builds AAB, uploads as COMPLETED Internal Testing release, testers auto-update within 15–60 min."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_play: 'true' }}
          confirmCopy="Builds the Android AAB and uploads as a COMPLETED Internal Testing release (verified working on run 25361589282). Tester devices auto-update within 15–60 min — no Play Console click. Costs an EAS build credit. Continue?"
        />
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS + submit to TestFlight"
          subtitle="Builds IPA, submits to ASC, assigns Team (Expo)."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_testflight: 'true' }}
          confirmCopy="Builds the iOS IPA, uploads to App Store Connect, and assigns the build to internal group Team (Expo). Apple processing 5–30 min then TestFlight notifies testers. Costs an EAS build credit. Continue?"
        />
        <WorkflowTriggerButton
          id="mobile-typecheck"
          label="Run typecheck"
          subtitle="Checks if app code still compiles."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
        <WorkflowTriggerButton
          id="release-audit"
          label="Run release audit"
          subtitle="Checks Android, iOS, EAS, GitHub Actions, and store blockers."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
      </Section>

      <Section title="Android — Internal Testing">
        <Row label="Tester-live" value="v14 ✓ received; repo target v17" />
        <Row label="Auto-promote" value="PROVEN end-to-end — run 25361589282" />
        <Row label="Routine path" value="Build Android + upload → tester device updates within 15–60 min, no manual steps" />
        <Row label="releaseStatus" value="completed (eas.json)" />
        <Text style={styles.note}>
          Play Console "Release history" UI paginates / filters EAS-COMPLETED releases differently from manual rollouts — if earlier pages don't show v14, that's a Play Console UI quirk, not a missing release. Ground truth: tester device receives the new versionCode. Settings → About → Version code on the device confirms which build is running.
        </Text>
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android AAB (no upload)"
          subtitle="Builds an AAB on EAS only. For dry runs / external upload."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the Android AAB on EAS. Costs an EAS build credit. The AAB stays on EAS until you separately upload it. Continue?"
        />
      </Section>

      <Section title="iOS — TestFlight">
        <Row label="TestFlight channel" value="works ✓; repo target Build 18" />
        <Row label="Build / submit automation" value={iosBuildAvailable ? 'auto ✓' : 'workflow not configured'} />
        <Row label="Auto-assign to Team (Expo)" value={adminStatus?.testflightGroupAssignmentConfigured === true ? 'auto ✓' : '—'} />
        <Row label="HealthKit Mac/Vision warning" value="fixed in prior TestFlight builds — accept any prompt" />
        <Text style={styles.note}>
          TestFlight is not silent OTA — testers update through the TestFlight app once Apple finishes processing each build (5–30 min after EAS submit).
        </Text>
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS (no submit)"
          subtitle="Builds an IPA on EAS only. For dry runs / external submit."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the iOS IPA on EAS. Costs an EAS build credit. The IPA stays on EAS until you separately submit it. Continue?"
        />
      </Section>

      <Section title="OTA">
        <Row label="Status" value="blocked (EAS SDK 54 server gate)" />
        <Text style={styles.note}>
          OTA is unavailable on the EAS Update server for SDK 54. Use the Play / TestFlight build buttons above instead — there is no OTA dispatch button intentionally.
        </Text>
      </Section>

      <Section title="Diagnostics">
        <WorkflowTriggerButton
          id="backend-smoke"
          label="Run backend smoke"
          subtitle="Pings the Railway backend health and AI context routes."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
      </Section>

      <QuickCaptureSection />

      <HealthConnectAuditStatusSection />

      <AuditSummarySection />

      <PromptBridgeSection statusBlock={STATUS_HANDOFF_TEMPLATE} />

      <Section title="Open shortcuts">
        <Text style={styles.note}>
          Termius is the manual-fallback terminal. Workflow buttons above are the safe automation path; raw shell stays out of the app intentionally — see docs/TERMINAL_WORKFLOW_STRATEGY.md.
        </Text>
        {EXTERNAL_SHORTCUTS.map((s) => (
          <ExternalShortcutButton key={s.label} label={s.label} url={s.url} fallbackHint={s.fallbackHint} />
        ))}
      </Section>

      <Section title="Advanced details">
        <Text style={styles.note}>
          Build / runtime / backend / data sections below. Read-only diagnostics — useful for handoffs to ChatGPT or Claude. Long-press any value to copy.
        </Text>
      </Section>

      <Section title="App build / runtime">
        <Row label="Version" value={buildInfo.appVersion} />
        <Row label={Platform.OS === 'ios' ? 'iOS build number' : 'Android versionCode'} value={String(buildInfo.buildNumber)} />
        <Row label="Repo HEAD" value={buildInfo.repoHead} />
        <Row label="Platform" value={buildInfo.platform} />
        <Row label="Runtime version" value={String(buildInfo.runtimeVersion)} />
        <Row label="Update id" value={buildInfo.updateId ? String(buildInfo.updateId).slice(0, 18) + '…' : 'embedded'} />
        <Row label="Channel" value={buildInfo.channel ?? 'production'} />
        <Row label="OTA status" value="Blocked (EAS SDK 54 server gate)" />
      </Section>

      <Section title="Backend status">
        <Row label="Host" value={apiHost} />
        <Row label="Healthy" value={health == null ? '—' : health.ok ? 'yes' : 'no'} />
        <Row label="Last checked" value={health?.checkedAt ? new Date(health.checkedAt).toLocaleTimeString() : '—'} />
        {health?.error && <Row label="Error" value={health.error} />}
        <Pressable style={[styles.btn, refreshing && { opacity: 0.5 }]} disabled={refreshing} onPress={refresh}>
          <Text style={styles.btnText}>{refreshing ? 'Refreshing…' : 'Refresh status'}</Text>
        </Pressable>
      </Section>

      <Section title="Data / AI status">
        <Row label="Normalised days" value={health?.totalNormalizedDays != null ? String(health.totalNormalizedDays) : '—'} />
        <Row label="Date range" value={health?.firstDate && health?.lastDate ? `${health.firstDate} → ${health.lastDate}` : '—'} />
        <Row label="Sources connected" value={health?.sourcesConnected != null ? String(health.sourcesConnected) : '—'} />
        <Row label="Readiness status" value={health?.readinessStatus ?? '—'} />
        <Row label="Multi-window trends" value="7 / 14 / 30 / 90 / 180 / 365 / all-time (live)" />
        {health?.totalNormalizedDays != null && health.totalNormalizedDays < 95 && (
          <Text style={styles.note}>AI store coverage is &lt; 95 days — long-term answers will say so explicitly.</Text>
        )}
      </Section>

      <Section title="AI Coach — provenance">
        <Row label="Personal-data-backed labelling" value="on" />
        <Row label="Cross-user / general trends" value="off (consent + k-threshold pending)" />
        <Row label="Paid LLM API" value="not implemented (deferred — see docs/AI_PROVIDER_STRATEGY.md)" />
        <Text style={styles.note}>
          Top-of-screen "AI Coach status" is the live state (reachability, trend windows, all-history). This section carries the policy guarantees that don't change at runtime.
        </Text>
      </Section>

      <Section title="Release / status links">
        <LinkRow label="Expo project" url={EXPO_PROJECT_URL} />
        <LinkRow label="Expo builds" url={EXPO_BUILDS_URL} />
        <LinkRow label="Expo updates" url={EXPO_UPDATES_URL} />
        <LinkRow label="Railway dashboard" url={RAILWAY_URL} />
        <LinkRow label="GitHub repo" url={GITHUB_REPO_URL} />
        <LinkRow label="GitHub Actions" url={GITHUB_ACTIONS_URL} />
        <LinkRow label="Play Console" url={PLAY_CONSOLE_URL} />
        <LinkRow label="App Store Connect" url={APPSTORE_CONNECT_URL} />
        <Text style={styles.note}>
          Reminders: Play Console → Lauburu Grappling Map → Testing → Internal testing → Create new release; TestFlight for iOS Build 12 stays separate.
        </Text>
      </Section>

      <Section title="Prompt library">
        <Text style={styles.note}>Tap to expand. Long-press text to copy.</Text>
        {PROMPT_LIBRARY.map((p, idx) => (
          <View key={p.label} style={{ gap: 6 }}>
            <Pressable
              style={styles.btn}
              onPress={() => setOpenPromptIdx(openPromptIdx === idx ? null : idx)}>
              <Text style={styles.btnText}>{openPromptIdx === idx ? '▾ ' : '▸ '}{p.label}</Text>
            </Pressable>
            {openPromptIdx === idx && (
              <RNText selectable style={styles.copyBlock}>{p.body}</RNText>
            )}
          </View>
        ))}
      </Section>

      <Section title="Status handoff template">
        <Pressable style={styles.btn} onPress={() => setHandoffOpen((v) => !v)}>
          <Text style={styles.btnText}>{handoffOpen ? '▾ Hide' : '▸ Show'} template</Text>
        </Pressable>
        {handoffOpen && (
          <RNText selectable style={styles.copyBlock}>{STATUS_HANDOFF_TEMPLATE}</RNText>
        )}
      </Section>

      <Section title="Access">
        <Row label="Source" value={isAdmin ? 'admin email' : localDevAccess ? 'local dev unlock' : '—'} />
        {!isAdmin && localDevAccess && (
          <Pressable
            style={[styles.btn, { backgroundColor: 'rgba(255,80,80,0.12)', borderColor: 'rgba(255,80,80,0.4)' }]}
            onPress={async () => {
              await lockDevTools();
              router.back();
            }}>
            <Text style={[styles.btnText, { color: '#ff8a8a' }]}>Lock developer tools on this device</Text>
          </Pressable>
        )}
      </Section>

      <Section title="Workflow dispatch — diagnostics">
        <Row label="Dispatch endpoint" value={dispatchAvailable ? 'reachable' : 'not configured'} />
        <Row label="Allowlist" value={adminStatus?.workflowAllowlist?.length ? `${adminStatus.workflowAllowlist.length} workflows` : '—'} />
        <WorkflowTriggerButton
          id="ota-diagnostic"
          label="Run OTA diagnostic"
          subtitle="Reads-only — verifies the EAS Update server SDK 54 block."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
        {adminStatus?.blockers && adminStatus.blockers.length > 0 && (
          <Text style={styles.note}>
            {adminStatus.blockers.join(' ')}
          </Text>
        )}
        <Text style={styles.note}>
          {dispatchAvailable
            ? 'Each workflow button posts to the protected dispatch endpoint, which triggers a single GitHub Actions workflow_dispatch on main. No secrets pass through this app.'
            : 'Workflow buttons stay disabled until: (1) push repo to GitHub, (2) mint a fine-grained PAT with Actions:read/write + Contents/Metadata:read, (3) add it to Railway as GITHUB_DISPATCH_TOKEN with GITHUB_REPO=owner/repo. One-time setup.'}
        </Text>
      </Section>
    </ScrollView>
  );
}

function PromptBridgeSection({ statusBlock }: { statusBlock: string }) {
  const ctx = useOwnerWorkflowStore((s) => s.context);
  const setSelectedTaskBundle = useOwnerWorkflowStore((s) => s.setSelectedTaskBundle);
  const [openKind, setOpenKind] = useState<BridgePromptKind | null>(null);
  const [taskBundleDraft, setTaskBundleDraft] = useState(ctx.selectedTaskBundle ?? '');

  // Apply the user's typed task bundle to the store on blur — so the
  // template builders pick it up. Local-only.
  const onTaskBundleBlur = useCallback(() => {
    setSelectedTaskBundle(taskBundleDraft);
  }, [taskBundleDraft, setSelectedTaskBundle]);

  const bodyFor = useCallback(
    (kind: BridgePromptKind): string => {
      switch (kind) {
        case 'claude_code': return buildClaudeCodePrompt(ctx);
        case 'claude_chrome': return buildClaudeChromePrompt(ctx);
        case 'chatgpt_status': return buildChatGPTStatusPrompt(ctx);
        case 'codex': return buildCodexPrompt(ctx);
        case 'current_status': return statusBlock;
        case 'terminal_check': return buildTerminalCheckPrompt(ctx);
      }
    },
    [ctx, statusBlock],
  );

  return (
    <Section title="Prompt bridge">
      <Text style={styles.note}>
        Templates are deterministic — no paid AI API. Long-press text after expanding to copy, then open Termius / Claude Code / ChatGPT and paste. Templates pull priority / blocker / last status / protected rules / manual steps from the workflow context; edit task bundle below to scope the prompt.
      </Text>
      <Text style={styles.captureLabel}>Selected task bundle (optional)</Text>
      <TextInput
        value={taskBundleDraft}
        onChangeText={setTaskBundleDraft}
        onBlur={onTaskBundleBlur}
        placeholder='e.g. "Grappler Readiness Batch B"'
        placeholderTextColor="#666"
        style={styles.captureInput}
      />
      {BRIDGE_PROMPT_KINDS.map((kind) => (
        <View key={kind} style={{ gap: 6 }}>
          <Pressable
            style={styles.btn}
            onPress={() => setOpenKind(openKind === kind ? null : kind)}>
            <Text style={styles.btnText}>{openKind === kind ? '▾ ' : '▸ '}{BRIDGE_PROMPT_LABELS[kind]}</Text>
          </Pressable>
          {openKind === kind && (
            <>
              <Text style={styles.btnSubtitle}>Long-press the block below to copy. Then open Termius / Claude Code and paste.</Text>
              <RNText selectable style={styles.copyBlock}>{bodyFor(kind)}</RNText>
            </>
          )}
        </View>
      ))}
    </Section>
  );
}

/**
 * External shortcut button. Tries the deep-link URL first; if the
 * URL scheme isn't installed (most common case for `termius://`),
 * shows a fallback Alert with the App Store hint and offers to copy
 * a tmux attach snippet via the existing long-press-to-copy block.
 */
function ExternalShortcutButton({
  label,
  url,
  fallbackHint,
}: {
  label: string;
  url: string;
  fallbackHint?: string;
}) {
  const [tmuxOpen, setTmuxOpen] = useState(false);
  const isTermius = url.startsWith('termius:');
  const onPress = useCallback(async () => {
    try {
      const supported = await Linking.canOpenURL(url);
      if (!supported) throw new Error('not_supported');
      await Linking.openURL(url);
    } catch {
      Alert.alert(
        label,
        fallbackHint ?? `Could not open ${url}. The app may not be installed on this device.`,
      );
    }
  }, [url, label, fallbackHint]);
  return (
    <View style={{ gap: 4 }}>
      <Pressable style={styles.btn} onPress={onPress}>
        <Text style={styles.btnText}>{label}</Text>
      </Pressable>
      {isTermius && (
        <>
          <Pressable
            style={[styles.btn, { backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.12)' }]}
            onPress={() => setTmuxOpen((v) => !v)}>
            <Text style={[styles.btnText, { color: '#cfd3da' }]}>{tmuxOpen ? '▾ Hide tmux attach instructions' : '▸ Copy tmux attach instructions'}</Text>
          </Pressable>
          {tmuxOpen && (
            <RNText selectable style={styles.copyBlock}>{buildTmuxAttachInstructions()}</RNText>
          )}
        </>
      )}
    </View>
  );
}

const QUICK_CAPTURE_TYPES: { id: OwnerBacklogType; label: string }[] = [
  { id: 'bug', label: 'Bug' },
  { id: 'ux', label: 'UX' },
  { id: 'feature', label: 'Feature' },
  { id: 'release_blocker', label: 'Release' },
  { id: 'health_data', label: 'Health' },
  { id: 'ai_coaching', label: 'AI' },
  { id: 'monetisation', label: 'Money' },
];

const QUICK_CAPTURE_PLATFORMS: { id: OwnerBacklogPlatform; label: string }[] = [
  { id: 'both', label: 'Both' },
  { id: 'ios', label: 'iOS' },
  { id: 'android', label: 'Android' },
];

const STANDING_TOP_FIVE: string[] = [
  '1. Play Console listing pass + releaseStatus flip (Aaron-side)',
  '2. Paired tester build (v14 + Build 15)',
  '3. Grappler Readiness Batch B — NextDayCheckin sliders',
  '4. Grappler Readiness Batch C — TrainingSession schema',
  '5. Grappler Readiness Batch D — bucket-ring UI',
];

function AgentStatusSection() {
  // Hard gate: this surface is owner-email-allowlisted. The local
  // 7-tap dev unlock alone is NOT enough — devUnlocked grants
  // access to the rest of Admin/Dev (read-only diagnostics) but
  // must NOT pull `Coder status` content because the underlying
  // statuses can carry summaries Aaron writes (commit refs, run
  // ids, work-in-progress notes) that are not for testers even if
  // they've stumbled onto Admin/Dev via the unlock taps.
  // Re-compute isAdmin here rather than trusting a prop so the
  // surface is self-protective: if a future caller mounts this
  // component outside Admin/Dev, the email gate still applies.
  const userEmail = useAuthStore((s) => s.user?.email ?? null);
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail.toLowerCase());

  const [agents, setAgents] = useState<Record<string, AgentStatusEntry | null> | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refresh = useCallback(async () => {
    if (!isAdmin) return;  // never fetch for non-admin
    setLoading(true);
    const data = await fetchAgentStatus();
    if (data) {
      setAgents(data.agents);
      setGeneratedAt(data.generatedAt);
    }
    setLoading(false);
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;  // never poll for non-admin
    void refresh();
    const t = setInterval(() => { void refresh(); }, 30_000);
    return () => clearInterval(t);
  }, [refresh, isAdmin]);

  if (!isAdmin) {
    // Per the hardening pass: non-admin users get NO placeholder
    // section at all. Even the "owner-account only" note signalled
    // that this surface exists, which is more than testers /
    // dev-unlock viewers need to know. Return null so the layout
    // collapses cleanly.
    return null;
  }

  const order = ['claude', 'codex', 'claude-code-guide', 'other'] as const;
  const populated = agents
    ? order.filter((k) => agents[k] != null) as Array<typeof order[number]>
    : [];

  return (
    <Section title="Coder status">
      <Text style={styles.note}>
        Owner-only. Reads `data/agent-status/*.json` written by `scripts/mark-agent-done.sh` on the backend. Refreshes every 30s.
      </Text>
      <Pressable style={[styles.btn, loading && { opacity: 0.5 }]} disabled={loading} onPress={refresh}>
        <Text style={styles.btnText}>{loading ? 'Refreshing…' : 'Refresh now'}</Text>
      </Pressable>
      {generatedAt && <Row label="Last fetched" value={new Date(generatedAt).toLocaleTimeString()} />}
      {agents == null && !loading && (
        <Text style={styles.note}>Backend not reachable — connector route may not be deployed yet.</Text>
      )}
      {agents != null && populated.length === 0 && (
        <Text style={styles.note}>No agent has reported a status yet. Run scripts/mark-agent-done.sh to seed one.</Text>
      )}
      {populated.map((agent) => {
        const e = agents![agent]!;
        const tone =
          e.status === 'done' ? '#4ade80'
          : e.status === 'in_progress' ? '#d4e157'
          : e.status === 'needs_review' ? '#ffa500'
          : e.status === 'blocked' ? '#ff8a8a'
          : '#888';
        return (
          <View key={agent} style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
            <Text style={[styles.rowLabel, { color: tone }]}>
              {agent} · {e.status}
            </Text>
            {e.task.length > 0 && <Text style={styles.rowValue}>Task: {e.task}</Text>}
            {e.summary.length > 0 && <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={4}>{e.summary}</Text>}
            {e.verification.length > 0 && <Text style={styles.rowValue}>Verified: {e.verification}</Text>}
            {e.nextAction.length > 0 && <Text style={[styles.rowValue, { color: '#d4e157' }]}>Next: {e.nextAction}</Text>}
            {e.updatedAt && (
              <Text style={[styles.rowValue, { opacity: 0.6, fontSize: 10 }]}>
                Updated {new Date(e.updatedAt).toLocaleString()}
              </Text>
            )}
          </View>
        );
      })}
    </Section>
  );
}

function ConnectorStatusSection({
  snapshot,
  refreshing,
  onRefresh,
}: {
  snapshot: ConnectorSnapshot | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const work = snapshot?.workStatus ?? null;
  const build = snapshot?.buildStatus ?? null;
  const handoff = snapshot?.handoff ?? null;
  const lanes = snapshot?.coderLanes?.lanes ?? [];
  const terminalEntries = snapshot?.terminalSummary?.entries ?? [];
  const latestTerminal = terminalEntries[0] ?? null;
  const claudeLane = lanes.find((lane) => lane.laneId.toLowerCase().includes('claude')) ?? null;
  const codexLane = lanes.find((lane) => lane.laneId.toLowerCase().includes('codex')) ?? null;
  const [detailsOpen, setDetailsOpen] = useState(false);
  const mcpState = snapshot
    ? `${snapshot.source === 'mcp' ? 'MCP connected' : 'Backend fallback'} · ${connectorFreshnessLabel(snapshot.checkedAt)} · updated ${connectorCheckedTime(snapshot.checkedAt)}`
    : refreshing
      ? 'MCP refreshing…'
      : 'MCP not connected';
  const summaryLine = snapshot
    ? `${lanes.length} lanes · ${terminalEntries.length} terminal summaries · ${handoff ? 'handoff ready' : 'no handoff'}`
    : 'Set EXPO_PUBLIC_MCP_BASE_URL + admin token, then refresh.';
  const handoffSummary = snapshot ? [
    'MOBILE_CONTROL_CENTRE_HANDOFF',
    `Checked: ${snapshot.checkedAt}`,
    `Source: ${snapshot.source}`,
    `Priority: ${work?.currentPriority ?? '—'}`,
    `Blocker: ${work?.currentBlocker ?? 'none'}`,
    `Next action: ${work?.nextAction ?? '—'}`,
    `Repo: ${work ? `${work.repoStatus.branch}@${work.repoStatus.head} · ${work.repoStatus.lastCommitMessage}` : '—'}`,
    `Claude: ${claudeLane ? `${claudeLane.status} · ${claudeLane.lastSummary ?? 'no summary'}` : '—'}`,
    `Codex: ${codexLane ? `${codexLane.status} · ${codexLane.lastSummary ?? 'no summary'}` : '—'}`,
    `Android: ${build ? `v${build.android.versionCode ?? '—'} · ${build.android.githubStatus ?? '—'} · Play ${build.android.playStatus ?? '—'}` : '—'}`,
    `iOS: ${build ? `${build.ios.buildNumber ?? '—'} · ${build.ios.githubStatus ?? '—'} · TestFlight ${build.ios.testflightStatus ?? '—'}` : '—'}`,
    `Latest terminal: ${latestTerminal ? `${latestTerminal.laneId} · ${latestTerminal.summary}` : '—'}`,
    `Safe to build: ${handoff ? (handoff.safeToBuild ? 'yes' : 'no') : '—'}`,
    `Build gate: ${handoff?.safeToBuildReason ?? '—'}`,
    `Manual steps: ${handoff?.manualSteps.slice(0, 3).join(' | ') || '—'}`,
  ].join('\n') : null;
  return (
    <Section title="Connector control centre">
      <Text style={styles.note}>
        Owner-only connector snapshot. No raw terminal logs, no shell execution, no secrets. Terminal rows are compact summaries only.
      </Text>
      <View style={styles.chipBlock}>
        <Text style={styles.chipLabel}>MCP status</Text>
        <Text style={styles.chipBody}>{mcpState}</Text>
        <Text style={styles.note}>{summaryLine}</Text>
      </View>
      <Pressable style={[styles.btn, refreshing && { opacity: 0.5 }]} disabled={refreshing} onPress={onRefresh}>
        <Text style={styles.btnText}>{refreshing ? 'Refreshing…' : 'Refresh connector status'}</Text>
      </Pressable>
      {snapshot == null && (
        <Text style={styles.note}>Connector routes are not reachable or the admin token is not configured.</Text>
      )}
      {snapshot?.checkedAt && <Row label="Checked" value={new Date(snapshot.checkedAt).toLocaleTimeString()} />}
      {snapshot && (
        <Row
          label="Status source"
          value={snapshot.source === 'mcp' ? 'Cloudflare MCP / repo-only until verified' : 'Backend fallback / repo-only'}
        />
      )}
      {snapshot && (
        <View style={{ gap: 6 }}>
          <Text style={styles.rowLabel}>Phone copy prompts</Text>
          <SelectableCopyButton
            label="Copy next Claude prompt"
            body={handoff?.latestClaudePrompt ?? claudeLane?.nextPrompt ?? 'No Claude prompt available yet.'}
          />
          <SelectableCopyButton
            label="Copy next Codex prompt"
            body={handoff?.latestCodexPrompt ?? codexLane?.nextPrompt ?? 'No Codex prompt available yet.'}
          />
          <SelectableCopyButton
            label="Copy handoff summary"
            body={handoffSummary ?? 'Connector snapshot is not available yet.'}
          />
          <SelectableCopyButton
            label="Copy Agent audit prompt"
            body={buildAgentAuditPrompt(snapshot)}
          />
        </View>
      )}
      {lanes.length > 0 && (
        <View style={{ gap: 6 }}>
          {lanes.map((lane) => (
            <View key={lane.laneId} style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
              <Text style={styles.rowLabel}>{lane.laneId} · {lane.status}</Text>
              {lane.currentPromptId && <Text style={styles.rowValue}>Prompt: {lane.currentPromptId}</Text>}
              {lane.lastSummary && <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={3}>{lane.lastSummary}</Text>}
              <Text style={[styles.rowValue, { opacity: 0.6 }]}>
                Typecheck: {lane.lastTypecheckResult ?? '—'} · Dirty files: {lane.dirtyFiles.length}
              </Text>
              {lane.nextPrompt && (
                <Text style={[styles.rowValue, { color: '#d4e157', opacity: 1, textAlign: 'left' }]} numberOfLines={2}>
                  Next prompt: {lane.nextPrompt}
                </Text>
              )}
            </View>
          ))}
        </View>
      )}
      <Pressable
        style={[styles.btn, { backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.12)' }]}
        onPress={() => setDetailsOpen((v) => !v)}>
        <Text style={[styles.btnText, { color: '#cfd3da' }]}>{detailsOpen ? '▾ Hide diagnostics' : '▸ Show diagnostics'}</Text>
      </Pressable>
      {detailsOpen && (
        <>
          {work && (
            <>
              <Row label="Priority" value={work.currentPriority ?? '—'} />
              <Row label="Blocker" value={work.currentBlocker ?? 'none'} />
              <Row label="Repo" value={`${work.repoStatus.branch}@${work.repoStatus.head} · ${work.repoStatus.dirtyFileCount} dirty / ${work.repoStatus.untrackedFileCount} untracked`} />
              <Row label="Latest commit" value={work.repoStatus.lastCommitMessage || '—'} />
              <Row label="Next action" value={work.nextAction ?? '—'} />
              <Row label="Live status" value={work.liveStatus.cloudflareWorkerDeployed ? 'Cloudflare worker marked live' : 'Repo-only / not marked live'} />
              <Row label="Tester builds" value={`Android ${work.liveStatus.androidVersionCode ?? '—'} · iOS ${work.liveStatus.iosBuildNumber ?? '—'}`} />
            </>
          )}
          {build && (
            <>
              <Row label="Android build" value={`v${build.android.versionCode ?? '—'} · ${build.android.githubStatus ?? '—'} · Play ${build.android.playStatus ?? '—'}`} />
              <Row label="iOS build" value={`${build.ios.buildNumber ?? '—'} · ${build.ios.githubStatus ?? '—'} · TestFlight ${build.ios.testflightStatus ?? '—'}`} />
            </>
          )}
          {handoff && (
            <>
              <Row label="Safe to build" value={handoff.safeToBuild ? 'yes' : 'no'} />
              <Row label="Build gate reason" value={handoff.safeToBuildReason} />
              <Row label="Latest Claude prompt" value={handoff.latestClaudePrompt ?? '—'} />
              <Row label="Latest Codex prompt" value={handoff.latestCodexPrompt ?? '—'} />
              {handoff.manualSteps.slice(0, 3).map((step, idx) => (
                <Row key={`${idx}-${step}`} label={`Manual ${idx + 1}`} value={step} />
              ))}
            </>
          )}
          {latestTerminal && (
            <View style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
              <Text style={styles.rowLabel}>Latest terminal · {latestTerminal.laneId}</Text>
              <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={3}>{latestTerminal.summary}</Text>
              <Text style={[styles.rowValue, { textAlign: 'left', opacity: 0.65 }]} numberOfLines={2}>
                Verified: {latestTerminal.verification || '—'}
              </Text>
              <Text style={[styles.rowValue, { textAlign: 'left', color: '#d4e157', opacity: 1 }]} numberOfLines={2}>
                Next: {latestTerminal.nextAction || '—'}
              </Text>
            </View>
          )}
        </>
      )}
    </Section>
  );
}

function SelectableCopyButton({ label, body }: { label: string; body: string }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={{ gap: 4 }}>
      <Pressable style={styles.btn} onPress={() => setOpen((v) => !v)}>
        <Text style={styles.btnText}>{open ? '▾ ' : '▸ '}{label}</Text>
      </Pressable>
      {open && (
        <>
          <Text style={styles.btnSubtitle}>Long-press the block below to copy from the phone.</Text>
          <RNText selectable style={styles.copyBlock}>{body}</RNText>
        </>
      )}
    </View>
  );
}

function HealthConnectAuditStatusSection() {
  const events = useAuditEventStore((s) => s.events);
  const hcEvents = events.filter((e) => e.sourceId === 'health_connect');
  const latest = hcEvents[hcEvents.length - 1] ?? null;
  const latestVisible = [...hcEvents].reverse().find((e) =>
    e.eventType === 'health_source_visible' || e.eventType === 'health_source_missing'
  ) ?? null;
  const latestPermission = [...hcEvents].reverse().find((e) =>
    e.eventType === 'permission_granted' || e.eventType === 'permission_denied' || e.eventType === 'permission_requested'
  ) ?? null;
  const latestSync = [...hcEvents].reverse().find((e) =>
    e.eventType === 'sync_succeeded' || e.eventType === 'sync_failed' || e.eventType === 'sync_started'
  ) ?? null;
  const latestMissing = [...hcEvents].reverse().find((e) => e.eventType === 'missing_metrics') ?? null;

  const fmt = (e: { eventType: string; severity: string; createdAt: string } | null) => e
    ? `${e.eventType} · ${e.severity} · ${new Date(e.createdAt).toLocaleTimeString()}`
    : '—';

  return (
    <Section title="Health Connect audit">
      <Text style={styles.note}>
        Android local audit only — source-state metadata, not raw health values.
      </Text>
      <Row label="Events" value={String(hcEvents.length)} />
      <Row label="Latest" value={fmt(latest)} />
      <Row label="Visibility" value={fmt(latestVisible)} />
      <Row label="Permission" value={fmt(latestPermission)} />
      <Row label="Sync" value={fmt(latestSync)} />
      <Row label="Missing metrics" value={fmt(latestMissing)} />
      {latestSync?.availableFields && latestSync.availableFields.length > 0 && (
        <Row label="Available fields" value={latestSync.availableFields.join(', ')} />
      )}
      {latestMissing?.missingFields && latestMissing.missingFields.length > 0 && (
        <Row label="Missing fields" value={latestMissing.missingFields.join(', ')} />
      )}
    </Section>
  );
}

function AuditSummarySection() {
  const events = useAuditEventStore((s) => s.events);
  const recent = events.slice(-8).reverse();
  const counts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.eventType] = (acc[e.eventType] ?? 0) + 1;
    return acc;
  }, {});
  const totalErrors = events.filter((e) => e.severity === 'error').length;
  const totalWarnings = events.filter((e) => e.severity === 'warning').length;
  return (
    <Section title="Audit · last events">
      <Text style={styles.note}>
        Local-only metadata about source state — never raw health values. Capped at 200 events. See docs/IN_APP_AUDIT_SYSTEM.md.
      </Text>
      <Row label="Total events" value={String(events.length)} />
      <Row label="Errors / Warnings" value={`${totalErrors} / ${totalWarnings}`} />
      {Object.keys(counts).length === 0 && (
        <Text style={styles.note}>No events captured yet. Capture sites land in follow-up batches per the audit doc.</Text>
      )}
      {recent.map((e) => (
        <View key={e.id} style={styles.row}>
          <Text style={styles.rowLabel} numberOfLines={1}>{e.eventType}{e.sourceId ? ` · ${e.sourceId}` : ''}</Text>
          <Text style={styles.rowValue} numberOfLines={2} ellipsizeMode="tail">
            {e.severity}{e.userVisibleMessage ? ` · ${e.userVisibleMessage}` : ''}
          </Text>
        </View>
      ))}
    </Section>
  );
}

function QuickCaptureSection() {
  const items = useOwnerBacklogStore((s) => s.items);
  const add = useOwnerBacklogStore((s) => s.add);
  const remove = useOwnerBacklogStore((s) => s.remove);
  const updateStatus = useOwnerBacklogStore((s) => s.updateStatus);

  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [blocker, setBlocker] = useState('');
  const [type, setType] = useState<OwnerBacklogType>('bug');
  const [platform, setPlatform] = useState<OwnerBacklogPlatform>('both');
  const [priority, setPriority] = useState<number>(7);

  const canSubmit = title.trim().length > 0;

  const onAdd = useCallback(async () => {
    if (!canSubmit) return;
    const trimmedBlocker = blocker.trim();
    await add({
      title: title.trim(),
      details: details.trim(),
      blocker: trimmedBlocker.length > 0 ? trimmedBlocker : undefined,
      type,
      platform,
      priority,
      status: trimmedBlocker.length > 0 ? 'blocked' : 'new',
    });
    setTitle('');
    setDetails('');
    setBlocker('');
    setType('bug');
    setPlatform('both');
    setPriority(7);
    setOpen(false);
  }, [canSubmit, title, details, blocker, type, platform, priority, add]);

  return (
    <Section title="Backlog · Quick capture">
      <Text style={styles.note}>
        Standing top-5 mirrors docs/APP_DEVELOPMENTS.md. Quick capture stores ad-hoc items locally only — never synced. Backend sync is a separate batch.
      </Text>
      {STANDING_TOP_FIVE.map((line) => (
        <Text key={line} style={styles.backlogStandingLine}>{line}</Text>
      ))}

      <Pressable style={styles.btn} onPress={() => setOpen((v) => !v)}>
        <Text style={styles.btnText}>{open ? '▾ Close capture' : `▸ Quick capture${items.length > 0 ? ` (${items.length} stored)` : ''}`}</Text>
      </Pressable>

      {open && (
        <View style={styles.captureBox}>
          <Text style={styles.captureLabel}>Title</Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="One-line summary"
            placeholderTextColor="#666"
            style={styles.captureInput}
          />
          <Text style={styles.captureLabel}>Details</Text>
          <TextInput
            value={details}
            onChangeText={setDetails}
            placeholder="Optional — repro, links, why it matters"
            placeholderTextColor="#666"
            multiline
            numberOfLines={3}
            textAlignVertical="top"
            style={[styles.captureInput, styles.captureInputMulti]}
          />
          <Text style={styles.captureLabel}>Blocker (optional — sets status to blocked)</Text>
          <TextInput
            value={blocker}
            onChangeText={setBlocker}
            placeholder="e.g. needs Play listing screenshots"
            placeholderTextColor="#666"
            style={styles.captureInput}
          />
          <Text style={styles.captureLabel}>Type</Text>
          <View style={styles.captureRow}>
            {QUICK_CAPTURE_TYPES.map((t) => (
              <Pressable key={t.id} style={[styles.pill, type === t.id && styles.pillActive]} onPress={() => setType(t.id)}>
                <Text style={[styles.pillText, type === t.id && styles.pillTextActive]}>{t.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.captureLabel}>Platform</Text>
          <View style={styles.captureRow}>
            {QUICK_CAPTURE_PLATFORMS.map((p) => (
              <Pressable key={p.id} style={[styles.pill, platform === p.id && styles.pillActive]} onPress={() => setPlatform(p.id)}>
                <Text style={[styles.pillText, platform === p.id && styles.pillTextActive]}>{p.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.captureLabel}>Priority — see docs/FEEDBACK_PRIORITY_MODEL.md</Text>
          <View style={styles.captureRow}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
              <Pressable key={n} style={[styles.pillSmall, priority === n && styles.pillActive]} onPress={() => setPriority(n)}>
                <Text style={[styles.pillText, priority === n && styles.pillTextActive]}>{n}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable
            style={[styles.btn, !canSubmit && { opacity: 0.4 }]}
            disabled={!canSubmit}
            onPress={onAdd}>
            <Text style={styles.btnText}>Save to backlog</Text>
          </Pressable>
        </View>
      )}

      {items.length > 0 && (
        <View style={{ gap: 6 }}>
          {items.map((it) => <BacklogItemRow key={it.id} item={it} onRemove={remove} onStatus={updateStatus} />)}
        </View>
      )}
    </Section>
  );
}

function BacklogItemRow({
  item,
  onRemove,
  onStatus,
}: {
  item: OwnerBacklogItem;
  onRemove: (id: string) => Promise<void>;
  onStatus: (id: string, status: OwnerBacklogItem['status']) => Promise<void>;
}) {
  return (
    <View style={styles.backlogItem}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={styles.backlogTitle} numberOfLines={2}>P{item.priority} · {item.title}</Text>
        <Text style={styles.backlogMeta}>
          {item.type} · {item.platform} · {item.status} · {new Date(item.createdAt).toLocaleDateString()}
        </Text>
        {item.blocker && item.blocker.length > 0 && (
          <Text style={[styles.backlogMeta, { color: '#ff8a8a' }]} numberOfLines={2}>Blocker: {item.blocker}</Text>
        )}
        {item.details.length > 0 && <Text style={styles.backlogDetails} numberOfLines={3}>{item.details}</Text>}
      </View>
      <View style={{ gap: 4 }}>
        {item.status !== 'tester_live' && item.status !== 'done' && (
          <Pressable onPress={() => onStatus(item.id, 'tester_live')} hitSlop={6}>
            <Text style={[styles.backlogAction, { color: '#4ade80' }]}>Tester-live</Text>
          </Pressable>
        )}
        {item.status !== 'done' && (
          <Pressable onPress={() => onStatus(item.id, 'done')} hitSlop={6}>
            <Text style={[styles.backlogAction, { color: '#9ca3af' }]}>Done</Text>
          </Pressable>
        )}
        <Pressable onPress={() => onRemove(item.id)} hitSlop={6}>
          <Text style={[styles.backlogAction, { color: '#ff8a8a' }]}>Delete</Text>
        </Pressable>
      </View>
    </View>
  );
}

function WorkflowTriggerButton({
  id,
  label,
  subtitle,
  enabled,
  inputs,
  confirmCopy,
  disabledReason,
}: {
  id: string;
  label: string;
  /** One-line plain-language explanation of what this button does. */
  subtitle?: string;
  enabled: boolean;
  /** Optional `inputs` to forward to GitHub Actions workflow_dispatch. */
  inputs?: Record<string, string>;
  /** Optional override for the confirm Alert body. */
  confirmCopy?: string;
  /** Shown beneath the label when `enabled` is false — must explain
   * the exact blocker so the user knows what step to take next. */
  disabledReason?: string;
}) {
  const [busy, setBusy] = useState(false);
  const onPress = useCallback(() => {
    if (!enabled || busy) return;
    Alert.alert(
      `Trigger "${label}"?`,
      confirmCopy ?? `Dispatches the GitHub Actions workflow "${id}" on main. No app code change. Continue?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Dispatch',
          style: 'default',
          onPress: async () => {
            setBusy(true);
            try {
              const apiBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
              const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
              const res = await fetch(
                `${apiBase}/admin/workflows/${encodeURIComponent(id)}/dispatch`,
                {
                  method: 'POST',
                  headers: {
                    'content-type': 'application/json',
                    'x-athlete-memory-token': memToken,
                  },
                  body: JSON.stringify({ ref: 'main', inputs: inputs ?? {} }),
                },
              );
              const json: any = await res.json().catch(() => ({}));
              if (!res.ok || json?.ok === false) {
                throw new Error(json?.error ?? `HTTP ${res.status}`);
              }
              Alert.alert(
                'Dispatched',
                `${label} accepted. Check GitHub Actions for the run.`,
              );
            } catch (e: any) {
              Alert.alert('Dispatch failed', e?.message ?? 'Unknown error.');
            } finally {
              setBusy(false);
            }
          },
        },
      ],
    );
  }, [id, label, enabled, busy, inputs, confirmCopy]);
  const dimmed = !enabled || busy;
  return (
    <View style={{ gap: 2 }}>
      <Pressable
        style={[styles.btn, dimmed && { opacity: 0.4 }]}
        disabled={dimmed}
        onPress={onPress}>
        <Text style={styles.btnText}>{busy ? 'Dispatching…' : label}</Text>
      </Pressable>
      {subtitle && enabled && <Text style={styles.btnSubtitle}>{subtitle}</Text>}
      {!enabled && disabledReason && <Text style={styles.btnDisabledReason}>{disabledReason}</Text>}
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={2} ellipsizeMode="tail">{value}</Text>
    </View>
  );
}

function LinkRow({ label, url }: { label: string; url: string }) {
  return (
    <Pressable style={styles.row} onPress={() => Linking.openURL(url)}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, { color: '#d4e157' }]} numberOfLines={1} ellipsizeMode="tail">Open</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 18, paddingBottom: 40 },
  heading: { fontSize: 22, fontWeight: '700' },
  subtitle: { fontSize: 12, opacity: 0.55 },
  section: { gap: 8 },
  sectionTitle: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1, opacity: 0.5 },
  body: { fontSize: 13, opacity: 0.7 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)', gap: 8,
  },
  rowLabel: { fontSize: 13, fontWeight: '600' },
  rowValue: { fontSize: 12, opacity: 0.65, textAlign: 'right', flexShrink: 1 },
  btn: {
    paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.15)', borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.35)', alignItems: 'center',
  },
  btnText: { fontSize: 12, fontWeight: '700', color: '#d4e157' },
  btnSubtitle: { fontSize: 11, opacity: 0.55, paddingHorizontal: 4, marginTop: 1, marginBottom: 2 },
  btnDisabledReason: { fontSize: 11, color: '#ff8a8a', paddingHorizontal: 4, marginTop: 1, marginBottom: 2 },
  note: { fontSize: 11, opacity: 0.55, lineHeight: 15, marginTop: 2 },
  chipBlock: {
    paddingVertical: 8, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderWidth: 1, borderColor: 'rgba(212,225,87,0.2)',
    gap: 4,
  },
  chipLabel: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1, opacity: 0.55 },
  chipBody: { fontSize: 13, lineHeight: 17 },
  backlogStandingLine: { fontSize: 12, lineHeight: 17, opacity: 0.75 },
  captureBox: {
    gap: 8, padding: 10, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
  },
  captureLabel: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, opacity: 0.55 },
  captureInput: {
    backgroundColor: '#0f0f0f', color: '#e0e0e0',
    borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8, fontSize: 13,
  },
  captureInputMulti: { minHeight: 64 },
  captureRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  pill: {
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 14,
    backgroundColor: '#2a2a2a',
  },
  pillSmall: {
    paddingHorizontal: 9, paddingVertical: 5, borderRadius: 12,
    backgroundColor: '#2a2a2a', minWidth: 30, alignItems: 'center',
  },
  pillActive: { backgroundColor: '#d4e157' },
  pillText: { fontSize: 12, color: '#ccc', fontWeight: '600' },
  pillTextActive: { color: '#0a0a0a', fontWeight: '700' },
  backlogItem: {
    flexDirection: 'row', gap: 10, padding: 10, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
    alignItems: 'flex-start',
  },
  backlogTitle: { fontSize: 13, fontWeight: '700' },
  backlogMeta: { fontSize: 11, opacity: 0.55 },
  backlogDetails: { fontSize: 12, opacity: 0.75, lineHeight: 16 },
  backlogAction: { fontSize: 11, fontWeight: '700' },
  copyBlock: {
    fontSize: 11, lineHeight: 15, color: '#cfd3da',
    backgroundColor: 'rgba(255,255,255,0.04)',
    padding: 10, borderRadius: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
