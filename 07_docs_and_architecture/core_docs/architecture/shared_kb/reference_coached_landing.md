# Reference Coached Landing

## Purpose
Documents the Home-to-Reference coaching focus pipeline — how a technique recommendation on the Home screen navigates the user to the Reference screen with the correct technique pre-expanded.

## What Belongs
- Navigation flow and parameter passing
- Focus/scroll behavior on the Reference screen
- Deduplication and re-trigger mechanisms

## What Does NOT Belong
- Home screen layout or coaching logic (those are separate concerns)
- Reference screen full behavior (only the focus-landing subset)
- Technique data model

## Truth Status
Implemented. The pipeline works end-to-end.

## Stability
Stable for the current navigation architecture. Would need revisiting if navigation is restructured.

## Update Cadence
When navigation patterns or the Reference screen's focus mechanism changes.

## Key Rules

### Flow
1. **Home recommends a technique.** The coaching surface identifies a technique the user should review (based on readiness, training history, or curriculum).
2. **Navigation with focus params.** `router.navigate` is called with focus parameters that identify the target technique.
3. **Reference auto-expands and scrolls.** On mount or re-focus, the Reference screen reads the focus params, expands the relevant section, and scrolls to the target technique.

### Focus Nonce
- A `focusNonce` parameter is included in the navigation params.
- Purpose: forces the Reference screen to re-process the focus even if the technique ID is the same as a previous focus.
- Without the nonce, React Navigation may not trigger a re-render if the params look identical to the previous navigation.

### Deduplication
- `consumedRouteFocusRef` is a ref that tracks the last processed focus nonce.
- When the Reference screen processes a focus, it sets `consumedRouteFocusRef.current` to the current nonce.
- On subsequent renders or focus events, if the nonce matches the consumed value, the focus logic is skipped.
- This prevents the screen from re-scrolling on tab switches or background/foreground transitions that re-trigger the focus event.

### Parameter Shape
```
{
  focusTechnique: string,   // technique identifier
  focusNonce: number        // unique value per navigation, e.g., Date.now()
}
```

### Edge Cases
- If the technique is not found in the Reference data, the screen loads normally without scrolling. No error is shown.
- If the user navigates to Reference manually (not via Home), no focus params are present and the screen behaves as default.
