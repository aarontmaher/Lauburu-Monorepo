/**
 * Recent tester feedback viewer. Tester/admin surface reached from
 * Settings — not a normal end-user tab. Pulls /api/feedback/recent,
 * renders one card per submission with metadata + context + photo
 * thumbnails, supports pull-to-refresh and a full-screen image
 * viewer, and exposes Copy message / Copy full report via the
 * system Share sheet (no new native dep needed).
 */
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  Modal,
  Pressable,
  RefreshControl,
  Share,
  StyleSheet,
  View as RNView,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import {
  attachmentUrl,
  fetchRecentFeedback,
  formatFullReport,
  type FeedbackRecord,
} from '../src/services/feedback-viewer';

const TYPE_COLORS: Record<string, string> = {
  bug: '#ff6b6b',
  app_error: '#ff8a8a',
  ai_answer_issue: '#d4a157',
  health_source_issue: '#ffa500',
  apple_health_issue: '#ffb347',
  samsung_health_connect_issue: '#ffb347',
  nutrition_issue: '#6fcf97',
  hiit_workout_issue: '#4a9eff',
  suggestion: '#a8d96a',
  general: '#888',
};

const SEVERITY_COLORS: Record<string, string> = {
  low: '#888',
  medium: '#d4e157',
  high: '#ffa500',
  blocking: '#ff6b6b',
};

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return iso;
  const diffMin = Math.round((Date.now() - then) / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.round(diffH / 24);
  if (diffD < 7) return `${diffD}d ago`;
  return iso.slice(0, 10);
}

export default function FeedbackViewerScreen() {
  const router = useRouter();
  const [records, setRecords] = useState<FeedbackRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullImage, setFullImage] = useState<string | null>(null);

  const load = useCallback(async (mode: 'initial' | 'refresh') => {
    if (mode === 'initial') setLoading(true);
    else setRefreshing(true);
    const res = await fetchRecentFeedback();
    if (res.ok) {
      setRecords(res.records);
      setError(null);
    } else {
      setError(res.error ?? 'Could not load feedback.');
    }
    if (mode === 'initial') setLoading(false);
    else setRefreshing(false);
  }, []);

  useEffect(() => {
    void load('initial');
  }, [load]);

  const renderItem = useCallback(
    ({ item }: { item: FeedbackRecord }) => (
      <FeedbackCard item={item} onOpenImage={setFullImage} />
    ),
    [],
  );

  const keyExtractor = useCallback((r: FeedbackRecord) => r.id, []);

  return (
    <View style={styles.container}>
      <Stack.Screen
        options={{
          title: 'Recent feedback',
          headerBackTitle: 'Back',
          headerRight: () => (
            <Pressable
              onPress={() => void load('refresh')}
              hitSlop={10}
              disabled={refreshing || loading}
              accessibilityLabel="Refresh feedback"
            >
              <Text style={styles.headerAction}>
                {refreshing ? '…' : 'Refresh'}
              </Text>
            </Pressable>
          ),
        }}
      />

      {loading ? (
        <RNView style={styles.center}>
          <ActivityIndicator color="#d4e157" />
          <Text style={styles.muted}>Loading recent feedback…</Text>
        </RNView>
      ) : error && records.length === 0 ? (
        <RNView style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={() => void load('initial')}>
            <Text style={styles.retryBtnText}>Retry</Text>
          </Pressable>
          <Pressable onPress={() => router.back()} hitSlop={6}>
            <Text style={styles.muted}>Go back</Text>
          </Pressable>
        </RNView>
      ) : records.length === 0 ? (
        <RNView style={styles.center}>
          <Text style={styles.muted}>No feedback yet.</Text>
          <Text style={styles.subtle}>
            Once testers submit bug reports or suggestions, they appear here.
          </Text>
        </RNView>
      ) : (
        <FlatList
          data={records}
          keyExtractor={keyExtractor}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void load('refresh')}
              tintColor="#d4e157"
            />
          }
        />
      )}

      <Modal
        visible={fullImage != null}
        transparent
        animationType="fade"
        onRequestClose={() => setFullImage(null)}
      >
        <Pressable style={styles.fullOverlay} onPress={() => setFullImage(null)}>
          {fullImage && (
            <Image
              source={{ uri: fullImage }}
              style={styles.fullImage}
              resizeMode="contain"
            />
          )}
          <RNView style={styles.fullCloseHint}>
            <Text style={styles.fullCloseText}>Tap anywhere to close</Text>
          </RNView>
        </Pressable>
      </Modal>
    </View>
  );
}

function FeedbackCard({
  item,
  onOpenImage,
}: {
  item: FeedbackRecord;
  onOpenImage: (url: string) => void;
}) {
  const typeColor = TYPE_COLORS[item.type] ?? '#888';
  const sevColor = SEVERITY_COLORS[item.severity] ?? '#888';

  const contextLines = item.context
    ? Object.keys(item.context)
        .filter((k) => item.context![k] != null)
        .slice(0, 8)
    : [];

  const copyMessage = async () => {
    if (!item.message) return;
    await Share.share({ message: item.message }).catch(() => {});
  };

  const copyFull = async () => {
    await Share.share({ message: formatFullReport(item) }).catch(() => {});
  };

  return (
    <View style={styles.card}>
      <RNView style={styles.cardHeader}>
        <RNView style={[styles.typePill, { borderColor: typeColor }]}>
          <Text style={[styles.typePillText, { color: typeColor }]}>
            {item.type}
          </Text>
        </RNView>
        <RNView style={[styles.sevPill, { borderColor: sevColor }]}>
          <Text style={[styles.sevPillText, { color: sevColor }]}>
            {item.severity}
          </Text>
        </RNView>
        <Text style={styles.timeText}>{relativeTime(item.createdAt)}</Text>
      </RNView>

      {item.message ? (
        <Text style={styles.messageText} numberOfLines={8}>
          {item.message}
        </Text>
      ) : (
        <Text style={[styles.messageText, styles.muted]}>(no message)</Text>
      )}

      {contextLines.length > 0 && (
        <RNView style={styles.contextBlock}>
          {contextLines.map((key) => (
            <Text key={key} style={styles.contextLine}>
              <Text style={styles.contextKey}>{key}:</Text>{' '}
              {String(item.context![key] ?? '')}
            </Text>
          ))}
        </RNView>
      )}

      {item.attachments && item.attachments.length > 0 && (
        <RNView style={styles.thumbRow}>
          {item.attachments.map((a) => {
            const url = attachmentUrl(a.filename);
            return (
              <Pressable
                key={a.filename}
                onPress={() => onOpenImage(url)}
                accessibilityRole="imagebutton"
                accessibilityLabel={`Open ${a.filename}`}
              >
                <Image source={{ uri: url }} style={styles.thumb} />
              </Pressable>
            );
          })}
        </RNView>
      )}

      <RNView style={styles.actionRow}>
        {item.message ? (
          <Pressable style={styles.actionBtn} onPress={copyMessage}>
            <Text style={styles.actionBtnText}>Copy message</Text>
          </Pressable>
        ) : null}
        <Pressable style={styles.actionBtn} onPress={copyFull}>
          <Text style={styles.actionBtnText}>Copy full report</Text>
        </Pressable>
      </RNView>

      <Text style={styles.idLine}>{item.id}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10, padding: 24 },
  listContent: { padding: 16, gap: 12, paddingBottom: 40 },
  headerAction: {
    color: '#d4e157',
    fontSize: 14,
    fontWeight: '600',
    paddingHorizontal: 8,
  },

  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  typePill: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: 'transparent',
  },
  typePillText: { fontSize: 11, fontWeight: '700' },
  sevPill: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: 'transparent',
  },
  sevPillText: { fontSize: 11, fontWeight: '700' },
  timeText: { fontSize: 11, opacity: 0.55, marginLeft: 'auto' },

  messageText: { fontSize: 14, lineHeight: 20 },

  contextBlock: {
    gap: 2,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(0,0,0,0.25)',
  },
  contextLine: { fontSize: 11, opacity: 0.8, fontFamily: 'SpaceMono' },
  contextKey: { opacity: 0.6 },

  thumbRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  thumb: {
    width: 84,
    height: 84,
    borderRadius: 8,
    backgroundColor: '#111',
  },

  actionRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  actionBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.4)',
  },
  actionBtnText: { fontSize: 12, fontWeight: '600', color: '#d4e157' },

  idLine: { fontSize: 10, opacity: 0.4, fontFamily: 'SpaceMono' },

  muted: { fontSize: 13, opacity: 0.55 },
  subtle: { fontSize: 12, opacity: 0.4, textAlign: 'center' },
  errorText: { fontSize: 14, color: '#ff6b6b', textAlign: 'center' },

  retryBtn: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: '#d4e157',
  },
  retryBtnText: { color: '#0a0a0a', fontSize: 14, fontWeight: '700' },

  fullOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.92)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullImage: { width: '100%', height: '100%' },
  fullCloseHint: {
    position: 'absolute',
    bottom: 40,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  fullCloseText: { color: '#ccc', fontSize: 12 },
});
