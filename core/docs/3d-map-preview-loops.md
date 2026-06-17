# 3D Mind Map — Preview Loop Media Plan (design only)

Status: design-approved in principle, **not implemented**. Do not start
work without explicit "approve" from Aaron. Do not modify
`grappling.opml` unless approval explicitly covers it.

## Summary

Each technique in the 3D mind map should be able to display a tiny,
muted, autoplaying preview loop in its detail panel. Instructional and
live-footage videos stay as separate buttons (typically YouTube). The
preview loop is a short hosted MP4/WebM (3–8 s) — never a YouTube
embed.

## Data model

```ts
interface TechniqueMedia {
  instructional?: { url: string; label?: string }[];
  liveFootage?: { url: string; label?: string }[];
  previewLoop?: {
    type: 'mp4' | 'webm' | 'gif';
    url: string;
    poster?: string;          // optional still frame
    durationSeconds?: number; // expected 3–8 s
  };
}
```

`previewLoop` is optional. Panel hides the loop slot if absent.

## Panel rendering rules

- Lazy-load when the panel opens (do not preload across all techniques).
- Autoplay, muted, looping, plays inline. No fullscreen takeover.
- If `previewLoop.poster` is present, show poster until first frame
  decodes.
- Pause loop when panel closes / scrolls offscreen.
- Instructional + liveFootage continue as plain buttons that open the
  external URL.

## Implementation batches (ordered)

- A. Add the `previewLoop` field to the technique TypeScript type and
  parser path (no OPML edits — design-only until approved).
- B. Render the preview-loop slot in the technique detail panel using
  `expo-video` (autoplay/muted/loop/inline). Hide cleanly when absent.
- C. Native dependency: `expo-video` requires a fresh native build. OTA
  alone cannot ship Batch B.
- D. Hosting: Bunny Storage / Cloudflare R2; CDN-served MP4/WebM with
  small Range responses. Cost is negligible at our volume.
- E. Author one or two demo techniques with real `previewLoop` URLs to
  validate the path end-to-end.
- F. Document the authoring contract for technique editors (URL, type,
  duration target).

## OPML / parser impact (deferred)

If/when approved to extend authoring through OPML, the smallest change
is to add attributes on the existing technique outline:

- `previewLoopUrl`
- `previewLoopType` (`mp4` | `webm` | `gif`)
- `previewPoster`
- `previewDuration`

Plus existing `instructional` / `liveFootage` attribute groups already
in the parser. **Do not edit `grappling.opml` until that batch is
explicitly approved.**

## Future feature — preview-loop generator (backlog)

When Aaron returns to 3D Mind Map work, build an authoring tool that
lets each technique reference:

- Source video URL (typically a YouTube link or hosted MP4)
- Start time
- End time
- Optional crop / label

The tool should generate (and cache) a short muted MP4/WebM preview
loop, then return a hosted URL that the technique panel consumes via
the `previewLoop.url` field above.

Constraints:

- The 3D panel must keep consuming a ready `previewLoop` URL — it must
  not load YouTube directly as the looping preview.
- YouTube / instructional / live videos remain full-video buttons.
- Generated clips should be tiny, 3–8 s where possible.
- Cache generated clips so they load fast on repeated panel opens.
- Build this AFTER the 3D panel already supports `previewLoop`
  rendering (Batches A + B must land first).
