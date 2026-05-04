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
import { Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, Text as RNText } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import * as Application from 'expo-application';
import * as Updates from 'expo-updates';

import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../src/store/auth-store';
import { useDevUnlockStore } from '../src/store/dev-unlock-store';

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
const CURRENT_PRIORITY = "Aaron's Play Console listing pass on v13 draft, then flip eas.json releaseStatus to completed.";
const CURRENT_BLOCKER = 'Play Console listing pass — repo-side wiring is done.';
const NEXT_ACTION = 'Walk PLAY_SUBMIT_SETUP §6 → click Review release → Start rollout once → reply "flip releaseStatus to completed".';

/** Bridge prompts copied to the in-app Prompt bridge. Short labels, terse bodies. */
const BRIDGE_PROMPTS: Array<{ label: string; body: string }> = [
  {
    label: 'Copy next Claude prompt',
    body: [
      'Continue the standing tester-auto-update lane. Do not touch grappling.opml. Do not expose secrets. Do not run Supabase db push. Do not upgrade SDK. Do not run OTA. Do not implement paid AI yet.',
      '',
      '1. Verify Android tester auto-promote status (Play Console listing pass + releaseStatus flip).',
      '2. Run npx tsc --noEmit in apps/mobile.',
      '3. Report a CHATGPT_STATUS_START / CHATGPT_STATUS_END block covering: live / repo-only / blocked / verified / next.',
    ].join('\n'),
  },
  {
    label: 'Copy next ChatGPT status prompt',
    body: [
      'Print a compact ChatGPT status block summarising the lane Aaron is on, in this exact shape:',
      '',
      'CHATGPT_STATUS_START',
      'Auto-update status:',
      'Android auto-promote:',
      'iOS status:',
      'AI API implementation:',
      'Files changed:',
      'Verified:',
      'Live:',
      'Repo-only:',
      'Blocked:',
      'Manual steps for Aaron:',
      'Next:',
      'CHATGPT_STATUS_END',
    ].join('\n'),
  },
  {
    label: 'Copy current status block',
    body: STATUS_HANDOFF_TEMPLATE,
  },
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
  const accessGranted = isAdmin || devUnlocked;

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [openPromptIdx, setOpenPromptIdx] = useState<number | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [h, a] = await Promise.all([fetchBackendHealth(), fetchAdminStatus()]);
      setHealth(h);
      setAdminStatus(a);
    } finally { setRefreshing(false); }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const buildInfo = useMemo(() => {
    return {
      appVersion: Application.nativeApplicationVersion ?? '—',
      buildNumber: Application.nativeBuildVersion ?? '—',
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

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Stack.Screen options={{ title: 'Admin / Dev', headerBackTitle: 'Settings' }} />
      <Text style={styles.heading}>Admin / Dev</Text>
      <Text style={styles.subtitle}>Owner control centre. Compact status. No secrets. No remote shell.</Text>

      <Section title="Now">
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Priority</Text>
          <Text style={styles.chipBody}>{CURRENT_PRIORITY}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Blocker</Text>
          <Text style={styles.chipBody}>{CURRENT_BLOCKER}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Next action</Text>
          <Text style={styles.chipBody}>{NEXT_ACTION}</Text>
        </View>
      </Section>

      <Section title="Android — Internal Testing">
        <Row label="Tester-live versionCode" value={Platform.OS === 'android' ? String(buildInfo.buildNumber) : 'see Play Console'} />
        <Row label="Build → Play upload" value={androidBuildAvailable ? 'auto ✓' : 'workflow not configured'} />
        <Row label="Promote to testers" value={androidPromoteAuto ? 'auto ✓' : 'manual per release (DRAFT)'} />
        <Row label="Play Console blocker" value={androidPromoteAuto ? 'none' : 'listing pass + releaseStatus flip'} />
        <Text style={styles.note}>
          Next: walk docs/PLAY_SUBMIT_SETUP.md §6, click Review release → Start rollout, then flip releaseStatus to completed.
        </Text>
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android AAB"
          subtitle="Builds an AAB on EAS. Does NOT upload to Play."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the Android AAB on EAS. Costs an EAS build credit. The AAB stays on EAS until you separately upload it. Continue?"
        />
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android + upload to Internal Testing"
          subtitle="Builds AAB and uploads it to Play Internal Testing as DRAFT."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_play: 'true' }}
          confirmCopy="Builds the AAB and uploads as a DRAFT Internal Testing release. After workflow finishes you must open Play Console → Internal testing → Review release → Start rollout. Costs an EAS build credit. Continue?"
        />
      </Section>

      <Section title="iOS — TestFlight">
        <Row label="Latest build number" value={Platform.OS === 'ios' ? String(buildInfo.buildNumber) : 'see App Store Connect'} />
        <Row label="Build / submit automation" value={iosBuildAvailable ? 'auto ✓' : 'workflow not configured'} />
        <Row label="Auto-assign to Team (Expo)" value={adminStatus?.testflightGroupAssignmentConfigured === true ? 'auto ✓' : '—'} />
        <Row label="HealthKit Mac/Vision warning" value="repo-only fix on main (ships with next iOS build)" />
        <Text style={styles.note}>
          Next: bump apps/mobile/app.json ios.buildNumber and dispatch the iOS build + submit workflow when ready.
        </Text>
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS"
          subtitle="Builds an IPA on EAS. Does NOT submit to TestFlight."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the iOS IPA on EAS. Costs an EAS build credit. The IPA stays on EAS until you separately submit it. Continue?"
        />
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS + submit to TestFlight"
          subtitle="Builds, submits to App Store Connect, assigns to Team (Expo)."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_testflight: 'true' }}
          confirmCopy="Builds the IPA, uploads to App Store Connect, and assigns to internal group Team (Expo). Internal testers receive a TestFlight notification after Apple processing (~10–30 min). Costs an EAS build credit. Continue?"
        />
      </Section>

      <Section title="OTA">
        <Row label="Status" value="blocked (EAS SDK 54 server gate)" />
        <Text style={styles.note}>
          OTA is unavailable on the EAS Update server for SDK 54. Use the Play / TestFlight build buttons above instead — there is no OTA dispatch button intentionally.
        </Text>
      </Section>

      <Section title="Fast workflow buttons">
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
        <WorkflowTriggerButton
          id="backend-smoke"
          label="Run backend smoke"
          subtitle="Pings the Railway backend health and AI context routes."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
      </Section>

      <Section title="Prompt bridge">
        <Text style={styles.note}>
          Long-press text after expanding to copy. The app can trigger workflows, show status, open dashboards, copy prompts, and store status summaries. Without API integration it cannot read your live ChatGPT conversation, type into Claude Code on your laptop, reason over screenshots/Notes, or run arbitrary terminal commands.
        </Text>
        {BRIDGE_PROMPTS.map((p, idx) => (
          <View key={p.label} style={{ gap: 6 }}>
            <Pressable
              style={styles.btn}
              onPress={() => setOpenPromptIdx(openPromptIdx === idx + 1000 ? null : idx + 1000)}>
              <Text style={styles.btnText}>{openPromptIdx === idx + 1000 ? '▾ ' : '▸ '}{p.label}</Text>
            </Pressable>
            {openPromptIdx === idx + 1000 && (
              <RNText selectable style={styles.copyBlock}>{p.body}</RNText>
            )}
          </View>
        ))}
      </Section>

      <Section title="External dashboards">
        <LinkRow label="Play Console" url={PLAY_CONSOLE_URL} />
        <LinkRow label="App Store Connect" url={APPSTORE_CONNECT_URL} />
        <LinkRow label="GitHub Actions" url={GITHUB_ACTIONS_URL} />
        <LinkRow label="Expo builds" url={EXPO_BUILDS_URL} />
        <LinkRow label="Railway dashboard" url={RAILWAY_URL} />
      </Section>

      <Section title="Backlog">
        <Text style={styles.note}>
          Source of truth: docs/APP_DEVELOPMENTS.md. The list below mirrors the file at build time; the long-term shape is a backend route that serves the same fields.
        </Text>
        <Row label="Top 1" value="Play Console listing pass + releaseStatus flip" />
        <Row label="Top 2" value="Paired tester build (v14 + Build 15)" />
        <Row label="Top 3" value="Grappler Readiness Batch B (NextDayCheckin sliders)" />
        <Row label="Top 4" value="Grappler Readiness Batch C (TrainingSession schema)" />
        <Row label="Top 5" value="Grappler Readiness Batch D (bucket-ring UI)" />
      </Section>

      <Section title="App build / runtime">
        <Row label="Version" value={buildInfo.appVersion} />
        <Row label={Platform.OS === 'ios' ? 'iOS build number' : 'Android versionCode'} value={String(buildInfo.buildNumber)} />
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

      <Section title="AI Coach">
        <Row label="Backend reachable" value={health == null ? '—' : health.ok ? 'yes' : 'no'} />
        <Row label="Multi-window analysis" value={health?.ok ? 'enabled' : '—'} />
        <Row label="All-history support" value={health?.ok && health.totalNormalizedDays != null && health.totalNormalizedDays > 0 ? `yes (${health.totalNormalizedDays}d)` : 'no data yet'} />
        <Row label="Trend windows" value="7d, 14d, 30d, 90d, 180d, 365d, all-time" />
        <Row label="Personal-data-backed labelling" value="on" />
        <Row label="Cross-user/general trends" value="off (consent + k-threshold pending)" />
        {health?.ok && (health?.totalNormalizedDays ?? 0) === 0 && (
          <Text style={styles.note}>
            Backend healthy but AI store has 0 normalised days — connect Apple Health / Health Connect, or import WHOOP CSV / Polar export, then re-ask Coach.
          </Text>
        )}
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
        <Row label="Source" value={isAdmin ? 'admin email' : devUnlocked ? 'local unlock' : '—'} />
        {!isAdmin && devUnlocked && (
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
  copyBlock: {
    fontSize: 11, lineHeight: 15, color: '#cfd3da',
    backgroundColor: 'rgba(255,255,255,0.04)',
    padding: 10, borderRadius: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
