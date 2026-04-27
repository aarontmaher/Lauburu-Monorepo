# Map Tab Behavior

## Purpose
Documents how the Map tab works — a WebView embedding the hosted GrapplingMap site with chrome hiding to create a native-feeling experience.

## What Belongs
- WebView loading behavior and target URL
- CSS injection rules for chrome hiding
- Activation cascade for 3D view
- Known issues and runtime gaps

## What Does NOT Belong
- Website source code or deployment details
- Graph data model or node/edge schemas
- Other tab behaviors

## Truth Status
Implemented but runtime-unverified for chrome hiding completeness. The WebView loads and injects CSS, but full visual verification that all website chrome is hidden across all site states has not been done.

## Stability
Moderately stable. Core approach (WebView + CSS injection) is settled. Specific selectors may change when the website updates.

## Update Cadence
When the hosted site changes its DOM structure or when runtime verification is completed.

## Key Rules

### Loading
- WebView loads `lauburugrapplingmap.com` as its source URL.
- No authentication required — the site is publicly accessible.
- The WebView is the only way the map is accessed in the mobile app. There is no native re-implementation.

### Chrome Hiding
- CSS is injected into the WebView after page load to hide website navigation, headers, footers, and other non-graph UI.
- Goal: the user sees only the graph and its controls — no website branding or navigation that would break the native app feel.
- Injected CSS targets specific selectors. These are brittle — a site redesign can break hiding.

### Activation Cascade
- After load, the app attempts to switch the view to 3D mode automatically.
- This is a best-effort cascade: if the 3D toggle element is found, it is clicked programmatically. If not found, the view stays in its default state.
- Graph-specific controls (zoom, pan, node selection, filters) are preserved and remain interactive.

### Known Issues
- **Site may not complete load in WebView.** The hosted site is heavy (3D rendering, large graph). On slower connections or older devices, the WebView may time out or partially render. No retry mechanism exists currently.
- **Chrome hiding completeness is unverified.** Some site states (e.g., modal overlays, error pages, cookie banners) may not have their chrome hidden.
- **3D activation is not guaranteed.** The cascade depends on DOM elements being present and interactive at injection time. Race conditions with site JS can cause it to miss.
