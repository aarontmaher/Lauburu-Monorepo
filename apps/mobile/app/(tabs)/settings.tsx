import { useState } from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

function AuthForm() {
  const signIn = useAuthStore((s) => s.signIn);
  const signUp = useAuthStore((s) => s.signUp);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  const handleSubmit = async () => {
    if (!email || !password) return;
    setBusy(true);
    const error =
      mode === 'login'
        ? await signIn(email, password)
        : await signUp(email, password);
    setBusy(false);

    if (error) {
      Alert.alert(mode === 'login' ? 'Sign In Failed' : 'Sign Up Failed', error);
    } else if (mode === 'signup') {
      Alert.alert('Check your email', 'Confirm your email address to finish signing up.');
    }
  };

  return (
    <View style={styles.authForm}>
      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor="#666"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        textContentType="emailAddress"
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#666"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        textContentType="password"
      />

      <Pressable
        style={[styles.button, busy && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={busy || !email || !password}>
        {busy ? (
          <ActivityIndicator color="#0a0a0a" />
        ) : (
          <Text style={styles.buttonText}>
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </Text>
        )}
      </Pressable>

      <Pressable onPress={() => setMode(mode === 'login' ? 'signup' : 'login')}>
        <Text style={styles.switchText}>
          {mode === 'login'
            ? "Don't have an account? Sign up"
            : 'Already have an account? Sign in'}
        </Text>
      </Pressable>
    </View>
  );
}

function SignedInSection() {
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);

  const handleSignOut = () => {
    Alert.alert('Log out?', undefined, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: signOut,
      },
    ]);
  };

  return (
    <>
      <SettingsRow label="Status" value="Member" />
      <SettingsRow label="Email" value={user?.email ?? '—'} />
      <Pressable style={styles.buttonDanger} onPress={handleSignOut}>
        <Text style={styles.buttonDangerText}>Sign Out</Text>
      </Pressable>
    </>
  );
}

export default function SettingsScreen() {
  const status = useAuthStore((s) => s.status);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Settings</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        {status === 'member' ? <SignedInSection /> : <AuthForm />}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <SettingsRow label="Version" value="0.1.0" />
        <SettingsRow label="Website" value="lauburugrapplingmap.com" />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 24 },
  heading: { fontSize: 24, fontWeight: '700' },
  section: { gap: 12 },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    opacity: 0.5,
    letterSpacing: 1,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  rowLabel: { fontSize: 16 },
  rowValue: { fontSize: 14, opacity: 0.5 },
  authForm: { gap: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  button: {
    backgroundColor: '#e8ff47',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#0a0a0a', fontSize: 16, fontWeight: '600' },
  buttonDanger: {
    borderWidth: 1,
    borderColor: '#ff4444',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  buttonDangerText: { color: '#ff4444', fontSize: 16, fontWeight: '600' },
  switchText: {
    textAlign: 'center',
    color: '#e8ff47',
    fontSize: 14,
    paddingVertical: 4,
  },
});
