import { useEffect, useMemo, useState } from 'react';
import { Alert, Linking, Pressable, ScrollView, StyleSheet } from 'react-native';
import { router } from 'expo-router';

import { Text, View } from '@/components/Themed';
import {
  BELT_LABELS,
  BELT_LEVELS,
  BELT_SYLLABUS,
  type BeltLevel,
  type BeltSyllabusItem,
} from '../../src/data/belt-syllabus';
import {
  buildTechniqueProgressKey,
  useReferenceProgressStore,
  type ProgressStatus,
} from '../../src/store/reference-progress-store';
import { useProfile } from '../../src/hooks/useProfile';
import { useVideoAttachmentSummaries } from '../../src/hooks/useVideoAttachmentSummaries';
import {
  deriveTechniqueVideoDisplayState,
  fallbackVideoAttachmentSummary,
} from '../../src/services/video-attachment-display';
import type { VideoAttachmentSummary } from '@lauburu/shared';

const FULL_MAP_URL = 'https://www.lauburugrapplingmap.com/';
const DRILLED_RECENTLY_DAYS = 10;

type SyllabusStatus =
  | 'not_started'
  | 'learning'
  | 'learned'
  | 'drilled_recently';

const STATUS_META: Record<SyllabusStatus, { label: string; color: string }> = {
  not_started: { label: 'Not started', color: '#666' },
  learning: { label: 'Learning', color: '#d4e157' },
  learned: { label: 'Learned', color: '#4ade80' },
  drilled_recently: { label: 'Drilled recently', color: '#7fb8ff' },
};

function buildMapUrl(item: BeltSyllabusItem): string {
  return `${FULL_MAP_URL}#pos=${encodeURIComponent(item.position)}&sec=${encodeURIComponent(item.section)}`;
}

function isRecentlyUpdated(iso: string | undefined): boolean {
  if (!iso) return false;
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return false;
  return Date.now() - t <= DRILLED_RECENTLY_DAYS * 24 * 60 * 60 * 1000;
}

function deriveItemStatus(
  item: BeltSyllabusItem,
  progress: Record<string, ProgressStatus>,
  updatedAt: Record<string, string>,
): SyllabusStatus {
  const key = buildTechniqueProgressKey(
    item.section,
    item.position,
    item.role,
    item.heading,
    item.technique,
  );
  const status = progress[key] ?? 'none';
  if (status === 'drilling' && isRecentlyUpdated(updatedAt[key])) {
    return 'drilled_recently';
  }
  if (status === 'learned') return 'learned';
  if (status === 'drilling' || status === 'tracking') return 'learning';
  return 'not_started';
}

function SyllabusItemCard({
  item,
  status,
  videoSummary,
}: {
  item: BeltSyllabusItem;
  status: SyllabusStatus;
  videoSummary?: VideoAttachmentSummary | null;
}) {
  const meta = STATUS_META[status];
  const [playbackFailed, setPlaybackFailed] = useState(false);
  const videoState = deriveTechniqueVideoDisplayState(
    videoSummary ?? fallbackVideoAttachmentSummary(item.id),
    { playbackFailed },
  );

  const handleOpenVideo = async () => {
    if (!videoState.ctaUrl) return;
    try {
      await Linking.openURL(videoState.ctaUrl);
    } catch {
      setPlaybackFailed(true);
      Alert.alert('Playback failed', 'Use Reference or Map instead.');
    }
  };

  return (
    <View style={styles.itemCard}>
      <View style={styles.itemHeader}>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={styles.itemTitle}>{item.title}</Text>
          <Text style={styles.itemSummary}>{item.summary}</Text>
        </View>
        <View style={[styles.statusPill, { borderColor: `${meta.color}55` }]}>
          <Text style={[styles.statusText, { color: meta.color }]}>{meta.label}</Text>
        </View>
      </View>

      <Text style={styles.itemMeta}>
        {item.position} · {item.role} · {item.technique}
      </Text>
      <Text style={styles.videoMeta}>{videoState.note}</Text>
      <View style={styles.videoPill}>
        <Text style={styles.videoPillText}>{videoState.badge}</Text>
      </View>

      <View style={styles.actionRow}>
        <Pressable
          style={styles.actionBtn}
          onPress={() =>
            router.push({
              pathname: '/reference',
              params: {
                focus: item.position,
                focusRole: item.role,
                focusHeading: item.heading,
                focusTechnique: item.technique,
                focusReason: item.title,
                focusSource: 'syllabus',
                focusNonce: `${Date.now()}`,
              },
            })
          }>
          <Text style={styles.actionText}>Reference</Text>
        </Pressable>
        <Pressable
          style={styles.actionBtn}
          onPress={() =>
            router.navigate({
              pathname: '/(tabs)/map-3d',
              params: { url: buildMapUrl(item) },
            })
          }>
          <Text style={styles.actionText}>Map</Text>
        </Pressable>
        {videoState.ctaLabel ? (
          <Pressable
            style={styles.actionBtn}
            onPress={handleOpenVideo}>
            <Text style={styles.actionText}>{videoState.ctaLabel}</Text>
          </Pressable>
        ) : null}
        <Pressable
          style={styles.actionBtn}
          onPress={() => router.push('/train')}>
          <Text style={styles.actionText}>Train</Text>
        </Pressable>
      </View>
    </View>
  );
}

export default function SyllabusScreen() {
  const progress = useReferenceProgressStore((s) => s.progress);
  const updatedAt = useReferenceProgressStore((s) => s.updatedAt);
  const { profile } = useProfile();
  const [belt, setBelt] = useState<BeltLevel>('white');

  useEffect(() => {
    const nextBelt = profile?.current_belt;
    if (
      nextBelt === 'white' ||
      nextBelt === 'blue' ||
      nextBelt === 'purple' ||
      nextBelt === 'brown' ||
      nextBelt === 'black'
    ) {
      setBelt(nextBelt);
    }
  }, [profile?.current_belt]);

  const items = useMemo(
    () => BELT_SYLLABUS.filter((item) => item.belt === belt),
    [belt],
  );
  const { byTargetId: videoByTargetId } = useVideoAttachmentSummaries(belt);

  const counts = useMemo(() => {
    const tally = {
      not_started: 0,
      learning: 0,
      learned: 0,
      drilled_recently: 0,
    } satisfies Record<SyllabusStatus, number>;
    for (const item of items) {
      tally[deriveItemStatus(item, progress, updatedAt)] += 1;
    }
    return tally;
  }, [items, progress, updatedAt]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.heading}>Belt Syllabus</Text>
        <Text style={styles.subtitle}>
          Use the app syllabus as a compact belt roadmap linked to Reference, Map, and your live drilling state.
        </Text>
      </View>

      <View style={styles.beltRow}>
        {BELT_LEVELS.map((level) => (
          <Pressable
            key={level}
            style={[styles.beltPill, belt === level && styles.beltPillActive]}
            onPress={() => setBelt(level)}>
            <Text style={[styles.beltPillText, belt === level && styles.beltPillTextActive]}>
              {BELT_LABELS[level]}
            </Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.summaryCard}>
        <Text style={styles.summaryTitle}>{BELT_LABELS[belt]} belt focus</Text>
        <Text style={styles.summaryBody}>
          {counts.learned} learned · {counts.drilled_recently} drilled recently · {counts.learning} learning
        </Text>
      </View>

      <View style={styles.list}>
        {items.map((item) => (
          <SyllabusItemCard
            key={item.id}
            item={item}
            status={deriveItemStatus(item, progress, updatedAt)}
            videoSummary={videoByTargetId.get(item.id) ?? null}
          />
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  header: { gap: 6 },
  heading: { fontSize: 24, fontWeight: '700' },
  subtitle: { fontSize: 14, opacity: 0.68, lineHeight: 20 },
  beltRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  beltPill: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  beltPillActive: {
    backgroundColor: 'rgba(212,225,87,0.16)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.28)',
  },
  beltPillText: { fontSize: 13, opacity: 0.8, fontWeight: '600' },
  beltPillTextActive: { color: '#d4e157', opacity: 1 },
  summaryCard: {
    padding: 14,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.04)',
    gap: 4,
  },
  summaryTitle: { fontSize: 15, fontWeight: '700' },
  summaryBody: { fontSize: 12, opacity: 0.72 },
  list: { gap: 12 },
  itemCard: {
    padding: 14,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.04)',
    gap: 10,
  },
  itemHeader: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  itemTitle: { fontSize: 16, fontWeight: '700' },
  itemSummary: { fontSize: 13, opacity: 0.74, lineHeight: 18 },
  statusPill: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.35,
  },
  itemMeta: { fontSize: 12, opacity: 0.68 },
  videoMeta: { fontSize: 12, opacity: 0.62, lineHeight: 17 },
  videoPill: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  videoPillText: {
    fontSize: 11,
    fontWeight: '700',
    opacity: 0.82,
    textTransform: 'uppercase',
    letterSpacing: 0.35,
  },
  actionRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  actionBtn: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  actionText: { fontSize: 12, fontWeight: '600', color: '#d4e157' },
});
