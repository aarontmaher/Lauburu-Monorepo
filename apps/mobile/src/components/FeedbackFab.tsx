/**
 * FeedbackFab — tester feedback button + modal.
 *
 * Sits next to the AI Coach FAB. Opens a compact modal with:
 *   - type selector (bug / app error / AI answer / health / nutrition /
 *                    HIIT / Apple Health / Samsung-HC / suggestion / general)
 *   - severity (low / medium / high / blocking)
 *   - free-text "What happened or what should change?"
 *   - up to 3 photo/screenshot attachments (camera or library)
 *   - "For testers" helper (collapsible)
 *
 * Safe context auto-filled: current route, userId, athleteId, platform,
 * app version, build profile. Never includes tokens/secrets/raw health
 * data. Attachments are resized + compressed client-side before upload.
 */
import { useState, useCallback } from 'react';
import {
  StyleSheet, Pressable, Modal, TextInput, ActivityIndicator,
  Platform, KeyboardAvoidingView, ScrollView, Image, Alert,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { usePathname } from 'expo-router';
import { FontAwesome } from '@expo/vector-icons';
import { useAuthStore } from '../store/auth-store';
import { useHealthStore } from '../store/health-store';
import {
  submitTesterFeedback,
  MAX_ATTACHMENTS,
  type FeedbackAttachment,
  type FeedbackType,
  type FeedbackSeverity,
} from '../services/tester-feedback';
import { pickAttachment, type AttachmentSource } from '../services/feedback-attachments';

const TYPES: { id: FeedbackType; label: string }[] = [
  { id: 'ui_cleanup', label: 'UI cleanup' },
  { id: 'bug', label: 'Bug' },
  { id: 'app_error', label: 'App error' },
  { id: 'ai_answer_issue', label: 'AI answer' },
  { id: 'apple_health_issue', label: 'Apple Health' },
  { id: 'samsung_health_connect_issue', label: 'Samsung / HC' },
  { id: 'health_source_issue', label: 'Other health' },
  { id: 'nutrition_issue', label: 'Nutrition' },
  { id: 'hiit_workout_issue', label: 'HIIT / workout' },
  { id: 'suggestion', label: 'Suggestion' },
  { id: 'general', label: 'General' },
];

/**
 * Tester type — always tagged on every submission so Aaron can filter
 * `/api/feedback/recent` by cohort. Distinct from feedback type: one
 * tester can file UI-cleanup, bug, AND health issues across a session,
 * but their tester role doesn't change.
 */
type TesterType = 'friend_ui_cleanup' | 'health_data_tester' | 'general_tester';
const TESTER_TYPES: { id: TesterType; label: string; hint: string }[] = [
  { id: 'friend_ui_cleanup', label: 'Friend · UI cleanup', hint: 'Helping clean up what feels confusing or cluttered' },
  { id: 'health_data_tester', label: 'Health data tester', hint: 'Checking sync, metrics, trends' },
  { id: 'general_tester', label: 'General', hint: 'Anything else' },
];

/** Friend-tester prompt — structured prompts the user listed. */
const UI_CLEANUP_PLACEHOLDER = [
  '• What did you try?',
  '• What confused you?',
  '• Duplicated or cluttered areas?',
  '• Broken or unclear buttons?',
  '• Tap targets / readability issues?',
  '• Trust blockers (anything that felt off)?',
  '• Top 5 cleanup suggestions',
  '• What did you like?',
].join('\n');

/** Health/AI tester prompt — structured prompts to make submissions actionable. */
const HEALTH_PLACEHOLDER = [
  '• What were you trying to do?',
  '• What happened? (e.g. sync failed, no data showed, wrong score)',
  '• What did you expect to happen?',
  '• Which health source? (Apple Health / Health Connect / WHOOP / Polar / BLE / manual)',
  '• Was the data already synced? When did you last sync?',
].join('\n');

/** AI advice tester prompt. */
const AI_PLACEHOLDER = [
  '• What did you ask the AI?',
  '• What did the AI say?',
  '• Did the advice feel: useful / wrong / confusing / missing data?',
  '• What would have been more useful?',
  '• Was data missing or stale?',
].join('\n');

/** Bug placeholder. */
const BUG_PLACEHOLDER = [
  '• What were you trying to do?',
  '• What screen were you on?',
  '• What happened (error message? wrong result?)?',
  '• What did you expect?',
  '• Was the Feedback button easy to find?',
].join('\n');

const SEVERITIES: FeedbackSeverity[] = ['low', 'medium', 'high', 'blocking'];

const APP_VERSION = '0.1.0';

export function FeedbackFab() {
  const insets = useSafeAreaInsets();
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  // Pull a minimal safe source-status snapshot so health/Apple-Health
  // feedback auto-includes enough context to diagnose sync issues
  // without leaking raw health data.
  const healthPermAvailable = useHealthStore((s) => s.permissions?.available ?? false);
  const healthLastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const healthLastError = useHealthStore((s) => s.error);
  const healthDaysCount = useHealthStore((s) => s.days.length);

  const [open, setOpen] = useState(false);
  const [testerType, setTesterType] = useState<TesterType>('general_tester');
  const [type, setType] = useState<FeedbackType>('bug');
  const [severity, setSeverity] = useState<FeedbackSeverity>('medium');
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<FeedbackAttachment[]>([]);
  const [pickingAttachment, setPickingAttachment] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<'ok' | 'error' | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAttach = useCallback(
    async (source: AttachmentSource) => {
      if (attachments.length >= MAX_ATTACHMENTS || pickingAttachment) return;
      setPickingAttachment(true);
      const res = await pickAttachment(source);
      setPickingAttachment(false);
      if (!res.ok) {
        if ('cancelled' in res && res.cancelled) return;
        const errorMessage = 'error' in res ? res.error : 'Unknown error';
        Alert.alert('Could not attach image', errorMessage);
        return;
      }
      setAttachments((prev) => [...prev, res.attachment]);
    },
    [attachments.length, pickingAttachment],
  );

  const handleRemoveAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Some categories cannot be acted on without a written description —
  // a screenshot alone is too hard to interpret. Enforce a minimum
  // text length for these, surface a clear inline reason, and keep
  // anonymous-but-described submissions allowed.
  const requiresDescription =
    severity === 'blocking' ||
    type === 'health_source_issue' ||
    type === 'ai_answer_issue' ||
    type === 'apple_health_issue' ||
    type === 'samsung_health_connect_issue';
  const REQUIRED_DESCRIPTION_MIN = 20;
  const trimmedMessage = message.trim();
  const descriptionTooShort =
    requiresDescription && trimmedMessage.length < REQUIRED_DESCRIPTION_MIN;

  const handleSubmit = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed && attachments.length === 0) return;
    if (submitting) return;
    if (requiresDescription && trimmed.length < REQUIRED_DESCRIPTION_MIN) {
      setResult('error');
      setErrorMsg(
        `Please describe the issue in at least ${REQUIRED_DESCRIPTION_MIN} characters. Screenshots alone are hard to interpret for ${type === 'health_source_issue' ? 'health-source' : type === 'ai_answer_issue' ? 'AI advice' : 'blocking'} issues.`,
      );
      return;
    }
    setSubmitting(true);
    setResult(null);
    setErrorMsg(null);

    const context: Record<string, string | number | boolean | null> = {
      route: pathname ?? 'unknown',
      platform: Platform.OS,
      os_version: String(Platform.Version ?? ''),
      app_version: APP_VERSION,
      build_profile: __DEV__ ? 'dev' : 'preview',
      attachment_count: attachments.length,
      timestamp: new Date().toISOString(),
    };
    if (
      type === 'apple_health_issue' ||
      type === 'samsung_health_connect_issue' ||
      type === 'health_source_issue'
    ) {
      context.health_permission_available = healthPermAvailable;
      context.health_last_sync_at = healthLastSyncAt ?? null;
      context.health_last_error = healthLastError ?? null;
      context.health_days_count = healthDaysCount;
    }
    // Tester-type cohort tag — always populated so Aaron can filter
    // /api/feedback/recent by `friend_ui_cleanup` / `health_data_tester`
    // / `general_tester` regardless of which feedback type the user
    // chose. Picker default is 'general_tester' to avoid mislabelling.
    context.tester_type = testerType;

    const res = await submitTesterFeedback({
      type,
      severity,
      message: trimmed,
      userId: user?.id ?? null,
      athleteId: user?.id ?? null,
      context,
      attachments: attachments.length > 0 ? attachments : undefined,
    });
    setSubmitting(false);
    if (res.ok) {
      setResult('ok');
      // Clear after short delay
      setTimeout(() => {
        setMessage('');
        setAttachments([]);
        setOpen(false);
        setResult(null);
      }, 1500);
    } else {
      setResult('error');
      setErrorMsg(res.error ?? 'Unknown error');
      // Keep message text + attachments so user doesn't lose them
    }
  }, [
    type, severity, message, attachments, submitting, user?.id, pathname,
    healthPermAvailable, healthLastSyncAt, healthLastError, healthDaysCount, testerType,
  ]);

  const handleClose = useCallback(() => {
    if (!submitting) setOpen(false);
  }, [submitting]);

  const attachmentsFull = attachments.length >= MAX_ATTACHMENTS;
  const canSubmit = (message.trim().length > 0 || attachments.length > 0)
    && !submitting
    && !descriptionTooShort;

  return (
    <>
      <Pressable
        style={[styles.fab, { bottom: Math.max(insets.bottom, 10) + 72 + 56 }]}
        accessibilityRole="button"
        accessibilityLabel="Send feedback"
        hitSlop={6}
        onPress={() => setOpen(true)}>
        <FontAwesome name="flag" size={14} color="#fff" />
        <Text style={styles.fabLabel}>Feedback</Text>
      </Pressable>

      <Modal visible={open} transparent animationType="slide" onRequestClose={handleClose}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.headerRow}>
              <Text style={styles.title}>Send feedback</Text>
              <Pressable onPress={handleClose} hitSlop={8}>
                <Text style={styles.closeText}>Close</Text>
              </Pressable>
            </View>

            <ScrollView style={styles.scroll} keyboardShouldPersistTaps="handled">
              {!user?.id && (
                <Text style={[styles.helpBody, { marginBottom: 8 }]}>
                  Not signed in — submission will be anonymous.
                </Text>
              )}

              <Text style={[styles.sectionLabel, { marginBottom: 4 }]}>You are testing as</Text>
              <View style={styles.typeRow}>
                {TESTER_TYPES.map((t) => (
                  <Pressable
                    key={t.id}
                    style={[styles.pill, testerType === t.id && styles.pillActive]}
                    onPress={() => {
                      setTesterType(t.id);
                      if (t.id === 'friend_ui_cleanup') setType('ui_cleanup');
                      else if (t.id === 'health_data_tester' && type === 'ui_cleanup') setType('apple_health_issue');
                      else if (t.id === 'general_tester' && type === 'ui_cleanup') setType('bug');
                    }}>
                    <Text style={[styles.pillText, testerType === t.id && styles.pillTextActive]}>
                      {t.label}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <Text style={[styles.helpBody, { marginBottom: 8 }]}>
                {TESTER_TYPES.find((t) => t.id === testerType)?.hint}
              </Text>

              <Text style={styles.sectionLabel}>Type</Text>
              <View style={styles.typeRow}>
                {TYPES.map((t) => (
                  <Pressable
                    key={t.id}
                    style={[styles.pill, type === t.id && styles.pillActive]}
                    onPress={() => setType(t.id)}>
                    <Text style={[styles.pillText, type === t.id && styles.pillTextActive]}>
                      {t.label}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Text style={styles.sectionLabel}>Severity of bug</Text>
              <View style={styles.typeRow}>
                {SEVERITIES.map((s) => (
                  <Pressable
                    key={s}
                    style={[styles.pill, severity === s && styles.pillActive]}
                    onPress={() => setSeverity(s)}>
                    <Text style={[styles.pillText, severity === s && styles.pillTextActive]}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Text style={styles.sectionLabel}>
                What happened, or what should change?{requiresDescription ? ' (required)' : ''}
              </Text>
              <TextInput
                style={[styles.textArea, descriptionTooShort && trimmedMessage.length > 0 && styles.textAreaError]}
                value={message}
                onChangeText={setMessage}
                placeholder={
                  type === 'ui_cleanup' ? UI_CLEANUP_PLACEHOLDER
                  : type === 'health_source_issue' || type === 'apple_health_issue' || type === 'samsung_health_connect_issue' ? HEALTH_PLACEHOLDER
                  : type === 'ai_answer_issue' ? AI_PLACEHOLDER
                  : type === 'bug' || type === 'app_error' ? BUG_PLACEHOLDER
                  : 'Describe the issue, what you expected, and what actually happened.'
                }
                placeholderTextColor="#666"
                multiline
                numberOfLines={6}
                textAlignVertical="top"
              />
              {requiresDescription && (
                <Text style={styles.requiredHint}>
                  Please describe the issue too — screenshots can be hard to interpret. Min {REQUIRED_DESCRIPTION_MIN} characters.
                  {trimmedMessage.length > 0 && (
                    descriptionTooShort
                      ? ` (${trimmedMessage.length}/${REQUIRED_DESCRIPTION_MIN})`
                      : ' ✓'
                  )}
                </Text>
              )}

              <Text style={styles.sectionLabel}>
                Upload screenshot {attachments.length > 0 ? `(${attachments.length}/${MAX_ATTACHMENTS})` : ''}
              </Text>
              {attachments.length > 0 && (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.thumbRow}>
                  {attachments.map((a, i) => (
                    <View key={`${i}-${a.sizeBytes ?? 0}`} style={styles.thumbWrap}>
                      <Image
                        source={{ uri: `data:${a.mime};base64,${a.dataBase64}` }}
                        style={styles.thumb}
                      />
                      <Pressable
                        style={styles.thumbRemove}
                        onPress={() => handleRemoveAttachment(i)}
                        hitSlop={8}
                        accessibilityLabel={`Remove attachment ${i + 1}`}>
                        <Text style={styles.thumbRemoveText}>×</Text>
                      </Pressable>
                    </View>
                  ))}
                </ScrollView>
              )}
              <View style={styles.attachRow}>
                {/* Camera-capture button removed by product decision —
                    feedback flow only needs photo/screenshot upload.
                    The underlying `pickAttachment('camera')` path is
                    intentionally retained in feedback-attachments.ts
                    so a future surface (e.g. tester-only debug menu)
                    can re-enable it without re-implementing the
                    permission/compress flow. */}
                <Pressable
                  style={[styles.attachBtn, (attachmentsFull || pickingAttachment) && styles.attachBtnDisabled]}
                  onPress={() => handleAttach('library')}
                  disabled={attachmentsFull || pickingAttachment}
                  accessibilityLabel="Upload a screenshot or photo from your library">
                  <FontAwesome name="image" size={14} color={attachmentsFull ? '#555' : '#d4e157'} />
                  <Text style={[styles.attachBtnText, attachmentsFull && styles.attachBtnTextDisabled]}>
                    Upload screenshot
                  </Text>
                </Pressable>
                {pickingAttachment && <ActivityIndicator size="small" color="#d4e157" />}
              </View>

              {result === 'ok' && (
                <Text style={styles.success}>Thanks — feedback sent.</Text>
              )}
              {result === 'error' && (
                <Text style={styles.errorText}>
                  {errorMsg ?? 'Couldn\u2019t send feedback. Your draft is saved — tap Send to retry.'}
                </Text>
              )}
            </ScrollView>

            <Pressable
              style={[
                styles.submitBtn,
                !canSubmit && styles.submitBtnDisabled,
              ]}
              onPress={handleSubmit}
              disabled={!canSubmit}>
              {submitting ? (
                <ActivityIndicator color="#0a0a0a" />
              ) : (
                <Text style={styles.submitBtnText}>Send feedback</Text>
              )}
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    left: 16,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#444',
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
    zIndex: 998,
  },
  fabLabel: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
    marginTop: 2,
    letterSpacing: 0.2,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 20,
    maxHeight: '92%',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: { fontSize: 18, fontWeight: '700', color: '#fff' },
  closeText: { fontSize: 14, color: '#888' },
  scroll: { maxHeight: 560 },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#999',
    textTransform: 'uppercase',
    marginBottom: 6,
    marginTop: 10,
  },
  helpBody: { fontSize: 11, color: '#aaa', lineHeight: 15 },
  textAreaError: { borderColor: '#ff6b6b', borderWidth: 1 },
  requiredHint: { fontSize: 11, color: '#d4e157', marginTop: 4, marginBottom: 4 },
  anonNotice: {
    backgroundColor: 'rgba(212, 225, 87, 0.12)',
    borderColor: '#d4e157',
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  anonNoticeText: { fontSize: 12, color: '#d4e157', lineHeight: 16 },
  typeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 4 },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
    backgroundColor: '#2a2a2a',
  },
  pillActive: { backgroundColor: '#d4e157' },
  pillText: { fontSize: 12, color: '#ccc', fontWeight: '500' },
  pillTextActive: { color: '#0a0a0a', fontWeight: '700' },
  textArea: {
    backgroundColor: '#0f0f0f',
    color: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    minHeight: 100,
    marginBottom: 8,
  },
  thumbRow: { marginBottom: 8 },
  thumbWrap: {
    position: 'relative',
    marginRight: 8,
  },
  thumb: {
    width: 72,
    height: 72,
    borderRadius: 8,
    backgroundColor: '#0f0f0f',
  },
  thumbRemove: {
    position: 'absolute',
    top: -6,
    right: -6,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#ff6b6b',
    alignItems: 'center',
    justifyContent: 'center',
  },
  thumbRemoveText: { color: '#fff', fontSize: 16, fontWeight: '700', lineHeight: 18 },
  attachRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 4,
    alignItems: 'center',
  },
  attachBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#2a2a2a',
    borderWidth: 1,
    borderColor: '#333',
  },
  attachBtnDisabled: { opacity: 0.4 },
  attachBtnText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },
  attachBtnTextDisabled: { color: '#555' },
  helpToggle: { marginTop: 12, marginBottom: 4 },
  helpToggleText: { color: '#aaa', fontSize: 13, fontWeight: '600' },
  helpBox: {
    backgroundColor: '#0f0f0f',
    borderRadius: 8,
    padding: 10,
    marginBottom: 6,
    gap: 4,
  },
  helpLine: { color: '#ccc', fontSize: 12, lineHeight: 17 },
  contextNote: { fontSize: 11, color: '#666', marginTop: 6, marginBottom: 8 },
  success: { color: '#4ade80', fontSize: 13, marginTop: 8 },
  errorText: { color: '#ff6b6b', fontSize: 13, marginTop: 8 },
  submitBtn: {
    backgroundColor: '#d4e157',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 12,
  },
  submitBtnDisabled: { opacity: 0.4 },
  submitBtnText: { color: '#0a0a0a', fontSize: 15, fontWeight: '700' },
});
