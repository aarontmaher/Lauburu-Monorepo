/**
 * Video attachment types — truthful availability model for
 * technique/requirement video content.
 *
 * Three states:
 *   attached_ready       — video exists and is playable
 *   attached_unavailable — video reference exists but is not playable
 *   not_attached         — no video is linked to this item
 *
 * Mobile must NOT infer attachment from a bare URL.
 * Only backend/curator can set attached_ready.
 */

export type VideoAvailability =
  | 'attached_ready'
  | 'attached_unavailable'
  | 'not_attached';

export type VideoProvider = 'website_3d_map' | 'youtube' | 'instructor' | 'internal' | 'unknown';

export interface VideoAttachment {
  id: string;
  targetType: 'technique' | 'requirement' | 'position';
  targetId: string;
  availability: VideoAvailability;
  /** Playback URL — only meaningful when availability is attached_ready. */
  playbackUrl: string | null;
  /** External link (e.g. website deep-link) when no in-app playback exists. */
  externalUrl: string | null;
  /** Where the video comes from. */
  provider: VideoProvider;
  title: string | null;
  durationSeconds: number | null;
  /** Why the video is unavailable. Always set when attached_unavailable. */
  unavailableReason: string | null;
  /** Human-readable fallback label when video can't play in-app. */
  fallbackLabel: string | null;
  /** Why the fallback is shown instead of real playback. */
  fallbackReason: string | null;
}

/** Compact video summary for mobile list/detail views. */
export interface VideoAttachmentSummary {
  targetId: string;
  availability: VideoAvailability;
  provider: VideoProvider;
  title: string | null;
  /** Direct playback URL if attached_ready. */
  playbackUrl: string | null;
  /** External link for techniques whose video lives on the hosted site. */
  externalUrl: string | null;
  /** Shown when video is not_attached or attached_unavailable. */
  fallbackLabel: string | null;
  /** Why the fallback applies. */
  fallbackReason: string | null;
}
