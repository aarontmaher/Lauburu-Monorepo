/**
 * Push approval notifications — lazy scaffold.
 *
 * The mobile app does NOT depend on expo-notifications today; that
 * is a native dependency change documented in
 * docs/APPROVAL_GATES_AND_PUSH.md. This module ships repo-ready
 * code that becomes operational the moment the dep is added in an
 * Aaron-approved EAS build. Until then, every entry point
 * gracefully no-ops.
 *
 * Three action buttons are wired:
 *
 *   - Approve   → useApprovalGatesStore.approve(gateId)
 *   - Deny      → useApprovalGatesStore.cancel(gateId, 'denied via push')
 *   - Defer     → useApprovalGatesStore.defer(gateId, +DEFAULT_DEFER_HOURS h)
 *
 * The pure mapper `mapNotificationActionToGateMutation` returns
 * the intended store transition without reaching for the store —
 * this keeps the mapping testable without React Native / zustand
 * imports. The non-pure helpers (registerApprovalCategory,
 * scheduleLocalApprovalReminder, dispatchNotificationAction)
 * lazy-load expo-notifications via require() and gracefully no-op
 * when the module is absent.
 *
 * iOS lock-screen action behaviour:
 *   - Apple delivers actionIdentifier on the user's tap; if the
 *     action is configured with `foreground: true` the app opens
 *     and dispatchNotificationAction runs.
 *   - If the user dismisses the notification or backgrounds it,
 *     the gate stays in the approval centre — same fallback the
 *     app already provides.
 */

import {
  APPROVAL_CATEGORY_IDENTIFIER,
  DEFAULT_NOTIFICATION_DEFER_HOURS as SHARED_DEFAULT_DEFER_HOURS,
  mapNotificationActionToGateMutation,
  type ApprovalGate,
  type ApprovalNotificationActionId,
  type ApprovalNotificationGateMutation,
} from '@lauburu/shared';
import { useApprovalGatesStore } from '../store/approval-gates-store';

// Re-export the pure helpers from @lauburu/shared so app-side
// callers don't have to import from two places.
export {
  APPROVAL_CATEGORY_IDENTIFIER,
  mapNotificationActionToGateMutation,
};
export type { ApprovalNotificationActionId, ApprovalNotificationGateMutation as GateMutation };
type GateMutation = ApprovalNotificationGateMutation;
/** Default defer window when the user taps "Defer" on a notification. */
export const DEFAULT_DEFER_HOURS = SHARED_DEFAULT_DEFER_HOURS;

/**
 * Lazy-load expo-notifications. Returns null when the dep is not
 * installed (which is the current state — see
 * docs/APPROVAL_GATES_AND_PUSH.md push setup blockers).
 */
function loadNotificationsModule(): unknown | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
    return require('expo-notifications');
  } catch {
    return null;
  }
}

interface NotificationActionShape {
  identifier: string;
  buttonTitle: string;
  options?: { isDestructive?: boolean; isAuthenticationRequired?: boolean; opensAppToForeground?: boolean };
}

/**
 * Register the Lauburu Approval Gate notification category. Idempotent.
 * No-op when expo-notifications is not installed (the current state)
 * so calling this from app boot is always safe.
 */
export async function registerApprovalCategory(): Promise<{ registered: boolean; reason: string }> {
  const Notifications = loadNotificationsModule() as null | {
    setNotificationCategoryAsync?: (
      identifier: string,
      actions: NotificationActionShape[],
    ) => Promise<unknown>;
  };
  if (!Notifications || typeof Notifications.setNotificationCategoryAsync !== 'function') {
    return { registered: false, reason: 'expo-notifications not installed' };
  }
  try {
    await Notifications.setNotificationCategoryAsync(APPROVAL_CATEGORY_IDENTIFIER, [
      { identifier: 'approve', buttonTitle: 'Approve', options: { opensAppToForeground: false } },
      { identifier: 'defer', buttonTitle: 'Defer 24h', options: { opensAppToForeground: false } },
      { identifier: 'deny', buttonTitle: 'Deny', options: { isDestructive: true, opensAppToForeground: true } },
    ]);
    return { registered: true, reason: 'category registered' };
  } catch (err) {
    return { registered: false, reason: err instanceof Error ? err.message : 'unknown error' };
  }
}

interface LocalScheduleResult {
  ok: boolean;
  reason: string;
  scheduledAt?: string;
}

/**
 * Schedule a single local notification reminding Aaron of an
 * approval gate ~60 min before expiresAt. Body is intentionally
 * generic — only the gate id + title travel over the local
 * notification channel; description / actionPayload / resolutionNote
 * stay on-device, never in the notification payload.
 *
 * No-op when expo-notifications is not installed OR when the gate
 * already expires within the leadMinutes window.
 */
export async function scheduleLocalApprovalReminder(
  gate: ApprovalGate,
  options: { leadMinutes?: number } = {},
): Promise<LocalScheduleResult> {
  const Notifications = loadNotificationsModule() as null | {
    scheduleNotificationAsync?: (input: unknown) => Promise<unknown>;
  };
  if (!Notifications || typeof Notifications.scheduleNotificationAsync !== 'function') {
    return { ok: false, reason: 'expo-notifications not installed' };
  }
  const lead = typeof options.leadMinutes === 'number' && options.leadMinutes > 0
    ? options.leadMinutes
    : 60;
  const expiresAt = new Date(gate.expiresAt).getTime();
  if (!Number.isFinite(expiresAt)) return { ok: false, reason: 'gate.expiresAt not parseable' };
  const fireAt = expiresAt - lead * 60_000;
  if (fireAt <= Date.now()) return { ok: false, reason: 'fireAt is in the past — gate already inside reminder window' };
  try {
    const fireDate = new Date(fireAt);
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Approval gate pending',
        body: `${gate.priority} · ${gate.title}`,
        categoryIdentifier: APPROVAL_CATEGORY_IDENTIFIER,
        data: { gateId: gate.id },
      },
      trigger: { date: fireDate, type: 'date' },
    });
    return { ok: true, reason: 'scheduled', scheduledAt: fireDate.toISOString() };
  } catch (err) {
    return { ok: false, reason: err instanceof Error ? err.message : 'unknown error' };
  }
}

interface NotificationResponseShape {
  actionIdentifier?: string;
  notification?: {
    request?: {
      content?: {
        data?: Record<string, unknown> | null;
        categoryIdentifier?: string;
      };
    };
  };
}

/**
 * Apply a notification action to the approval-gates store. Called
 * from a notification-response listener (registered by app code
 * once expo-notifications is installed). Returns the same shape as
 * the store transitions, so callers can surface the outcome.
 */
export async function dispatchNotificationAction(
  response: NotificationResponseShape | null | undefined,
  options: { now?: () => Date; deferHours?: number } = {},
): Promise<{ ok: boolean; reason: string; mutation: GateMutation | null }> {
  const actionId = response?.actionIdentifier ?? null;
  const gateId = (response?.notification?.request?.content?.data?.gateId as string | undefined) ?? null;
  const mutation = mapNotificationActionToGateMutation(actionId, gateId, options);
  if (!mutation) {
    return { ok: false, reason: 'unknown notification action', mutation: null };
  }
  const store = useApprovalGatesStore.getState();
  if (mutation.kind === 'approve') {
    const result = await store.approve(mutation.gateId, mutation.reason);
    return { ok: result.ok, reason: result.reason, mutation };
  }
  if (mutation.kind === 'deny') {
    const result = await store.cancel(mutation.gateId, mutation.reason);
    return { ok: result.ok, reason: result.reason, mutation };
  }
  const result = await store.defer(mutation.gateId, mutation.deferUntil, mutation.reason);
  return { ok: result.ok, reason: result.reason, mutation };
}
