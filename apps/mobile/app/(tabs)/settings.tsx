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
import { usePreferencesStore } from '../../src/store/preferences-store';
import { DEFAULT_PREFERENCES } from '@lauburu/shared';
import type { CoachingPreferences } from '@lauburu/shared';

// ---------------------------------------------------------------------------
// Reusable components
// ---------------------------------------------------------------------------

function SettingsRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

function PrefPillRow<T extends string>({
  label,
  options,
  labels,
  value,
  onChange,
}: {
  label: string;
  options: T[];
  labels: Record<T, string>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.prefRow}>
      <Text style={styles.prefLabel}>{label}</Text>
      <View style={styles.pillRow}>
        {options.map((opt) => (
          <Pressable
            key={opt}
            style={[styles.pill, value === opt && styles.pillActive]}
            onPress={() => onChange(opt)}>
            <Text style={[styles.pillText, value === opt && styles.pillTextActive]}>
              {labels[opt]}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Auth section
// ---------------------------------------------------------------------------

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
      { text: 'Log Out', style: 'destructive', onPress: signOut },
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

// ---------------------------------------------------------------------------
// Coaching preferences section
// ---------------------------------------------------------------------------

function PreferencesSection() {
  const prefs = usePreferencesStore((s) => s.preferences);
  const update = usePreferencesStore((s) => s.update);
  const reset = usePreferencesStore((s) => s.reset);

  const isDefault =
    JSON.stringify(prefs) === JSON.stringify(DEFAULT_PREFERENCES);

  return (
    <>
      <PrefPillRow
        label="Recovery approach"
        options={['conservative', 'moderate', 'aggressive'] as const}
        labels={{
          conservative: 'Conservative',
          moderate: 'Balanced',
          aggressive: 'Aggressive',
        }}
        value={prefs.recovery_conservatism}
        onChange={(v) => update({ recovery_conservatism: v })}
      />

      <PrefPillRow
        label="Training bias"
        options={['err_on_rest', 'balanced', 'train_through'] as const}
        labels={{
          err_on_rest: 'Rest-first',
          balanced: 'Balanced',
          train_through: 'Train through',
        }}
        value={prefs.hard_day_bias}
        onChange={(v) => update({ hard_day_bias: v })}
      />

      <PrefPillRow
        label="Goal"
        options={[
          'skill_development',
          'competition',
          'general_fitness',
          'weight_management',
        ] as const}
        labels={{
          skill_development: 'Skill',
          competition: 'Competition',
          general_fitness: 'Fitness',
          weight_management: 'Weight',
        }}
        value={prefs.goal}
        onChange={(v) => update({ goal: v })}
      />

      <PrefPillRow
        label="Coaching tone"
        options={['direct', 'encouraging', 'analytical'] as const}
        labels={{
          direct: 'Direct',
          encouraging: 'Encouraging',
          analytical: 'Analytical',
        }}
        value={prefs.tone}
        onChange={(v) => update({ tone: v })}
      />

      <View style={styles.prefRow}>
        <Text style={styles.prefLabel}>Target sessions/week</Text>
        <View style={styles.pillRow}>
          {[2, 3, 4, 5, 6].map((n) => (
            <Pressable
              key={n}
              style={[
                styles.pill,
                prefs.target_sessions_per_week === n && styles.pillActive,
              ]}
              onPress={() => update({ target_sessions_per_week: n })}>
              <Text
                style={[
                  styles.pillText,
                  prefs.target_sessions_per_week === n && styles.pillTextActive,
                ]}>
                {n}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <Pressable
        style={[styles.row, { justifyContent: 'space-between' }]}
        onPress={() => update({ comp_prep: !prefs.comp_prep })}>
        <Text style={styles.rowLabel}>Competition prep mode</Text>
        <Text style={[styles.rowValue, prefs.comp_prep && { color: '#e8ff47' }]}>
          {prefs.comp_prep ? 'ON' : 'OFF'}
        </Text>
      </Pressable>

      {!isDefault && (
        <Pressable style={styles.resetButton} onPress={reset}>
          <Text style={styles.resetText}>Reset to Defaults</Text>
        </Pressable>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

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
        <Text style={styles.sectionTitle}>Coaching Preferences</Text>
        <PreferencesSection />
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
  content: { padding: 20, gap: 24, paddingBottom: 40 },
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

  // Preferences
  prefRow: { gap: 8 },
  prefLabel: { fontSize: 14 },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  pill: {
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillActive: {
    borderColor: '#e8ff47',
    backgroundColor: 'rgba(232,255,71,0.1)',
  },
  pillText: { fontSize: 13, color: '#999' },
  pillTextActive: { color: '#e8ff47', fontWeight: '600' },
  resetButton: {
    borderWidth: 1,
    borderColor: '#666',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  resetText: { color: '#999', fontSize: 14 },
});
