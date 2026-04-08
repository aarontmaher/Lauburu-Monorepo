import { useState } from 'react';
import {
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Alert,
  ActivityIndicator,
  Keyboard,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { submitSuggestion } from '@lauburu/shared';

const AREA_OPTIONS = [
  'technique',
  'graph',
  'ux',
  'health',
  'content',
  'other',
] as const;

export default function SuggestScreen() {
  const [title, setTitle] = useState('');
  const [detail, setDetail] = useState('');
  const [area, setArea] = useState<string>('technique');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const canSubmit = title.trim().length > 0 && detail.trim().length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    Keyboard.dismiss();
    setSubmitting(true);

    const ok = await submitSuggestion({
      title: title.trim(),
      detail: detail.trim(),
      source: 'mobile-app',
      area,
    });

    setSubmitting(false);

    if (ok) {
      setSubmitted(true);
      setTitle('');
      setDetail('');
      setArea('technique');
    } else {
      Alert.alert('Submission Failed', 'Could not submit suggestion. Check your connection and try again.');
    }
  };

  if (submitted) {
    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={[styles.content, styles.centeredContent]}>
        <Text style={styles.successIcon}>✓</Text>
        <Text style={styles.successTitle}>Suggestion Submitted</Text>
        <Text style={styles.successBody}>
          It will appear in the Control Centre for review. Aaron approves all
          technique names and content.
        </Text>
        <Pressable
          style={styles.button}
          onPress={() => setSubmitted(false)}>
          <Text style={styles.buttonText}>Submit Another</Text>
        </Pressable>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Submit a Suggestion</Text>
      <Text style={styles.description}>
        Suggest technique additions, corrections, or improvements to the
        grappling map.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Title"
        placeholderTextColor="#666"
        value={title}
        onChangeText={setTitle}
      />

      <View style={styles.areaRow}>
        {AREA_OPTIONS.map((opt) => (
          <Pressable
            key={opt}
            style={[styles.areaPill, area === opt && styles.areaPillActive]}
            onPress={() => setArea(opt)}>
            <Text
              style={[
                styles.areaPillText,
                area === opt && styles.areaPillTextActive,
              ]}>
              {opt}
            </Text>
          </Pressable>
        ))}
      </View>

      <TextInput
        style={[styles.input, styles.textArea]}
        placeholder="Describe your suggestion..."
        placeholderTextColor="#666"
        value={detail}
        onChangeText={setDetail}
        multiline
        numberOfLines={6}
        textAlignVertical="top"
      />

      <Pressable
        style={[styles.button, (!canSubmit || submitting) && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={!canSubmit || submitting}>
        {submitting ? (
          <ActivityIndicator color="#0a0a0a" />
        ) : (
          <Text style={styles.buttonText}>Submit</Text>
        )}
      </Pressable>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>How suggestions work</Text>
        <Text style={styles.cardBody}>
          Suggestions are reviewed through the Control Centre. Aaron approves
          all technique names and content. Approved suggestions become OPML
          patches applied to the map.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16 },
  centeredContent: { alignItems: 'center', justifyContent: 'center', flex: 1 },
  heading: { fontSize: 24, fontWeight: '700' },
  description: { fontSize: 14, opacity: 0.7, lineHeight: 20 },
  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  textArea: { minHeight: 120 },

  areaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  areaPill: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#444',
    backgroundColor: 'transparent',
  },
  areaPillActive: {
    borderColor: '#e8ff47',
    backgroundColor: 'rgba(232,255,71,0.1)',
  },
  areaPillText: { fontSize: 13, color: '#999' },
  areaPillTextActive: { color: '#e8ff47', fontWeight: '600' },

  button: {
    backgroundColor: '#e8ff47',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: { color: '#0a0a0a', fontSize: 16, fontWeight: '600' },
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
    marginTop: 8,
  },
  cardTitle: { fontSize: 16, fontWeight: '600' },
  cardBody: { fontSize: 14, opacity: 0.7, lineHeight: 20 },

  successIcon: { fontSize: 48, color: '#4ade80', marginBottom: 8 },
  successTitle: { fontSize: 22, fontWeight: '700' },
  successBody: {
    fontSize: 14,
    opacity: 0.7,
    lineHeight: 20,
    textAlign: 'center',
    marginBottom: 8,
  },
});
