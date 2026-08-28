/**
 * MachinePairHint — INTENTIONALLY NEUTRALIZED.
 *
 * This used to chip on the Train tab and route the user to the
 * Health tab's Machine capture card. Machine capture now lives
 * entirely inside the Train tab (see TrainMachineSection), so
 * there's nowhere for this hint to route to and no reason to
 * render it. Kept as a null export so any stale tree or older OTA
 * bundle that still tries to mount this renders nothing instead of
 * crashing with undefined-component.
 */
export function MachinePairHint(): null {
  return null;
}
