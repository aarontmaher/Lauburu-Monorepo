/**
 * Pure helpers for push-driven approval-gate transitions.
 *
 * The mobile app does NOT depend on expo-notifications today; the
 * native dep is documented in docs/APPROVAL_GATES_AND_PUSH.md as
 * a push setup blocker. The helpers below are platform-free
 * (no React Native, no expo, no fs) so they can be tested in node
 * and shared between mobile-side dispatch code and any future
 * worker-side webhook router.
 */

export type ApprovalNotificationActionId = 'approve' | 'deny' | 'defer';

export type ApprovalNotificationGateMutation =
  | { kind: 'approve'; gateId: string; reason: string }
  | { kind: 'deny'; gateId: string; reason: string }
  | { kind: 'defer'; gateId: string; deferUntil: string; reason: string };

/** Default defer window when the user taps "Defer" on a notification. */
export const DEFAULT_NOTIFICATION_DEFER_HOURS = 24;

/** Notification category id Aaron's iOS device will register. */
export const APPROVAL_CATEGORY_IDENTIFIER = 'lauburu_approval_gate_v1';

const ACTION_REASON: Record<ApprovalNotificationActionId, string> = {
  approve: 'approved via push notification action',
  deny: 'denied via push notification action',
  defer: 'deferred via push notification action',
};

/**
 * Pure mapping from a notification action identifier (as delivered
 * by expo-notifications) to the intended gate mutation. Returns
 * null when the action id is unknown OR the gateId is missing.
 *
 * The default defer is 24 hours; pass `deferHours` to override.
 * Pass `now` to make the function deterministic in tests.
 */
export function mapNotificationActionToGateMutation(
  actionId: string | null | undefined,
  gateId: string | null | undefined,
  options: { now?: () => Date; deferHours?: number } = {},
): ApprovalNotificationGateMutation | null {
  if (typeof actionId !== 'string' || actionId.length === 0) return null;
  if (typeof gateId !== 'string' || gateId.length === 0) return null;
  const lower = actionId.toLowerCase();
  if (lower !== 'approve' && lower !== 'deny' && lower !== 'defer') return null;
  if (lower === 'defer') {
    const now = options.now ?? (() => new Date());
    const hours = typeof options.deferHours === 'number' && options.deferHours > 0
      ? options.deferHours
      : DEFAULT_NOTIFICATION_DEFER_HOURS;
    const deferUntil = new Date(now().getTime() + hours * 3_600_000).toISOString();
    return { kind: 'defer', gateId, deferUntil, reason: ACTION_REASON.defer };
  }
  if (lower === 'approve') {
    return { kind: 'approve', gateId, reason: ACTION_REASON.approve };
  }
  return { kind: 'deny', gateId, reason: ACTION_REASON.deny };
}
