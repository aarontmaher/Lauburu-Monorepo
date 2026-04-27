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
  const [type, setType] = useState<FeedbackType>('bug');
  const [severity, setSeverity] = useState<FeedbackSeverity>('medium');
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<FeedbackAttachment[]>([]);
  const [pickingAttachment, setPickingAttachment] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<'ok' | 'error' | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

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

  const handleSubmit = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed && attachments.length === 0) return;
    if (submitting) return;
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
    healthPermAvailable, healthLastSyncAt, healthLastError, healthDaysCount,
  ]);

  const handleClose = useCallback(() => {
    if (!submitting) setOpen(false);
  }, [submitting]);

  const attachmentsFull = attachments.length >= MAX_ATTACHMENTS;
  const canSubmit = (message.trim().length > 0 || attachments.length > 0) && !submitting;

  return (
    <>
      <Pressable
        style={[styles.fab, { bottom: Math.max(insets.bottom, 10) + 72 + 56 }]}
        accessibilityRole="button"
        accessibilityLabel="Send feedback"
        onPress={() => setOpen(true)}>
        <FontAwesome name="flag" size={14} color="#fff" />
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

              <Text style={styles.sectionLabel}>Severity</Text>
              <View style={styles.typeRow}>
                {SEVERITIES.map((s) => (
                  <Pressable
                    key={s}
                    style={[styles.pill, severity === s && styles.pillActive]}
                    onPress={() => setSeverity(s)}>
                    <Text style={[styles.pillText, severity === s && styles.pillTextActive]}>
                      {s}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Text style={styles.sectionLabel}>What happened or what should change?</Text>
              <TextInput
                style={styles.textArea}
                value={message}
                onChangeText={setMessage}
                placeholder="Describe the issue, what you expected, and what actually happened."
                placeholderTextColor="#666"
                multiline
                numberOfLines={6}
                textAlignVertical="top"
              />

              <Text style={styles.sectionLabel}>
                Screenshots / photos ({attachments.length}/{MAX_ATTACHMENTS})
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
                <Pressable
                  style={[styles.attachBtn, (attachmentsFull || pickingAttachment) && styles.attachBtnDisabled]}
                  onPress={() => handleAttach('library')}
                  disabled={attachmentsFull || pickingAttachment}
                  accessibilityLabel="Attach from photos">
                  <FontAwesome name="image" size={14} color={attachmentsFull ? '#555' : '#d4e157'} />
                  <Text style={[styles.attachBtnText, attachmentsFull && styles.attachBtnTextDisabled]}>
                    Attach photo
                  </Text>
                </Pressable>
                <Pressable
                  style={[styles.attachBtn, (attachmentsFull || pickingAttachment) && styles.attachBtnDisabled]}
                  onPress={() => handleAttach('camera')}
                  disabled={attachmentsFull || pickingAttachment}
                  accessibilityLabel="Take a photo">
                  <FontAwesome name="camera" size={14} color={attachmentsFull ? '#555' : '#d4e157'} />
                  <Text style={[styles.attachBtnText, attachmentsFull && styles.attachBtnTextDisabled]}>
                    Take photo
                  </Text>
                </Pressable>
                {pickingAttachment && <ActivityIndicator size="small" color="#d4e157" />}
              </View>

              <Pressable onPress={() => setHelpOpen((v) => !v)} style={styles.helpToggle}>
                <Text style={styles.helpToggleText}>
                  {helpOpen ? '▾' : '▸'} For testers — tips
                </Text>
              </Pressable>
              {helpOpen && (
                <View style={styles.helpBox}>
                  <Text style={styles.helpLine}>• Send screenshots of bugs or confusing screens.</Text>
                  <Text style={styles.helpLine}>• Apple Health / Samsung-HC issues — attach the Health card screenshot.</Text>
                  <Text style={styles.helpLine}>• AI answer issues — include the question you asked and the answer you got.</Text>
                  <Text style={styles.helpLine}>• Suggestions — include what you expected to happen.</Text>
                </View>
              )}

              <Text style={styles.contextNote}>
                Sent: screen ({pathname ?? 'unknown'}), platform ({Platform.OS}), build ({__DEV__ ? 'dev' : 'preview'}), user id (if signed in). No tokens or raw health data.
              </Text>

              {result === 'ok' && (
                <Text style={styles.success}>Thanks — feedback sent.</Text>
              )}
              {result === 'error' && (
                <Text style={styles.errorText}>
                  Couldn't send feedback. Please try again.
                  {errorMsg ? ` (${errorMsg})` : ''}
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
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#444',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
    zIndex: 998,
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
