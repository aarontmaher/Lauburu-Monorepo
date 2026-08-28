import type { VideoAttachmentSummary, VideoAvailability } from '@lauburu/shared';

export interface TechniqueVideoDisplayState {
  availability: VideoAvailability;
  badge: string;
  note: string;
  ctaLabel: string | null;
  ctaUrl: string | null;
}

export function deriveTechniqueVideoDisplayState(
  summary?: VideoAttachmentSummary | null,
  options?: { playbackFailed?: boolean },
): TechniqueVideoDisplayState {
  if (options?.playbackFailed) {
    return {
      availability: 'attached_unavailable',
      badge: 'Playback failed',
      note: 'This video could not be opened on this device. Use the reference or 3D map fallback instead.',
      ctaLabel: null,
      ctaUrl: null,
    };
  }
  const actionUrl = summary?.playbackUrl ?? summary?.externalUrl ?? null;
  switch (summary?.availability) {
    case 'attached_ready':
      return {
        availability: 'attached_ready',
        badge: actionUrl ? 'Video linked' : 'Video unavailable',
        note: actionUrl
          ? summary.title
            ? `${summary.title} is ready to open outside the app.`
            : 'Technique video is linked and ready to open outside the app.'
          : summary.fallbackReason ??
            'A linked video exists for this technique, but it is not openable right now.',
        ctaLabel: actionUrl
          ? summary.playbackUrl
            ? 'Watch video'
            : 'Open video'
          : null,
        ctaUrl: actionUrl,
      };
    case 'attached_unavailable':
      return {
        availability: 'attached_unavailable',
        badge: 'Video unavailable',
        note:
          summary.fallbackReason ??
          'A video is linked to this technique, but it is not playable right now.',
        ctaLabel: null,
        ctaUrl: null,
      };
    case 'not_attached':
    default:
      return {
        availability: 'not_attached',
        badge: 'No video',
        note:
          summary?.fallbackReason ??
          'No video is attached to this technique yet.',
        ctaLabel: null,
        ctaUrl: null,
      };
  }
}

export function fallbackVideoAttachmentSummary(
  targetId: string,
): VideoAttachmentSummary {
  return {
    targetId,
    availability: 'not_attached',
    provider: 'website_3d_map',
    title: null,
    playbackUrl: null,
    externalUrl: null,
    fallbackLabel: 'View in 3D map',
    fallbackReason: 'Video not attached in the mobile app.',
  };
}
