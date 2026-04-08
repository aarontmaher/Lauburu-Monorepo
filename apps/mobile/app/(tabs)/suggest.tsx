import { useState } from 'react';
import { StyleSheet, ScrollView, TextInput, Pressable } from 'react-native';
import { Text, View } from '@/components/Themed';

export default function SuggestScreen() {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');

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

      <TextInput
        style={[styles.input, styles.textArea]}
        placeholder="Describe your suggestion..."
        placeholderTextColor="#666"
        value={body}
        onChangeText={setBody}
        multiline
        numberOfLines={6}
        textAlignVertical="top"
      />

      <Pressable
        style={[styles.button, (!title || !body) && styles.buttonDisabled]}
        disabled={!title || !body}>
        <Text style={styles.buttonText}>Submit</Text>
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
});
