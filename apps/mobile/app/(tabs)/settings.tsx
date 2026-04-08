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
import { useConsentStore } from '../../src/store/consent-store';
import { useTierStore } from '../../src/store/tier-store';
import {
  DEFAULT_PREFERENCES, TIER_INFO, CAPABILITY_INFO, getTierCapabilities, minimumTierFor,
  DAYS_ORDER, DAY_LABELS, SCHEDULE_SESSION_LABELS, countPlannedSessions,
} from '@lauburu/shared';
import type { CoachingPreferences, Tier, Capability, DayOfWeek, ScheduleSessionType } from '@lauburu/shared';

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

      <ScheduleEditor />

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
// ---------------------------------------------------------------------------
// Data & Privacy
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Schedule Editor
// ---------------------------------------------------------------------------

const SCHEDULE_TYPES: import('@lauburu/shared').ScheduleSessionType[] = [
  'drilling', 'sparring', 'wrestling', 'takedowns', 'positional',
  'open_mat', 'comp_prep', 'conditioning', 'other',
];

function ScheduleEditor() {
  const prefs = usePreferencesStore((s) => s.preferences);
  const addSess = usePreferencesStore((s) => s.addSession);
  const removeSess = usePreferencesStore((s) => s.removeSession);
  const toggleSess = usePreferencesStore((s) => s.toggleSession);
  const [expandedDay, setExpandedDay] = useState<import('@lauburu/shared').DayOfWeek | null>(null);
  const [addingType, setAddingType] = useState<import('@lauburu/shared').ScheduleSessionType>('drilling');

  return (
    <View style={styles.prefRow}>
      <Text style={styles.prefLabel}>
        Weekly schedule ({countPlannedSessions(prefs.schedule)} sessions)
      </Text>

      {DAYS_ORDER.map((day) => {
        const sessions = prefs.schedule[day];
        const isExpanded = expandedDay === day;
        return (
          <View key={day}>
            <Pressable
              style={[styles.scheduleDayRow, isExpanded && styles.scheduleDayRowExpanded]}
              onPress={() => setExpandedDay(isExpanded ? null : day)}>
              <Text style={styles.scheduleDayName}>{DAY_LABELS[day]}</Text>
              <Text style={styles.scheduleDayCount}>
                {sessions.filter((s) => s.enabled).length > 0
                  ? sessions.filter((s) => s.enabled).map((s) =>
                      SCHEDULE_SESSION_LABELS[s.type] ?? s.type
                    ).join(', ')
                  : 'Rest'}
              </Text>
              <Text style={styles.scheduleChevron}>{isExpanded ? '▾' : '▸'}</Text>
            </Pressable>

            {isExpanded && (
              <View style={styles.scheduleDayExpanded}>
                {sessions.map((s) => (
                  <View key={s.id} style={styles.scheduleSessionRow}>
                    <Pressable onPress={() => toggleSess(day, s.id)}>
                      <Text style={[styles.scheduleSessionCheck, !s.enabled && { opacity: 0.3 }]}>
                        {s.enabled ? '✓' : '○'}
                      </Text>
                    </Pressable>
                    <Text style={[styles.scheduleSessionName, !s.enabled && { opacity: 0.3 }]}>
                      {SCHEDULE_SESSION_LABELS[s.type] ?? s.type}
                      {s.time ? ` · ${s.time}` : ''}
                    </Text>
                    <Pressable onPress={() => removeSess(day, s.id)}>
                      <Text style={styles.scheduleRemove}>✕</Text>
                    </Pressable>
                  </View>
                ))}

                {/* Add session */}
                <View style={styles.scheduleAddRow}>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                    <View style={styles.pillRow}>
                      {SCHEDULE_TYPES.map((st) => (
                        <Pressable
                          key={st}
                          style={[styles.pillSmall, addingType === st && styles.pillActive]}
                          onPress={() => setAddingType(st)}>
                          <Text style={[styles.pillSmallText, addingType === st && styles.pillTextActive]}>
                            {SCHEDULE_SESSION_LABELS[st]}
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  </ScrollView>
                  <Pressable
                    style={styles.scheduleAddBtn}
                    onPress={() => addSess(day, addingType)}>
                    <Text style={styles.scheduleAddBtnText}>+ Add</Text>
                  </Pressable>
                </View>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

function ConsentToggle({
  label,
  description,
  value,
  onChange,
  required,
}: {
  label: string;
  description: string;
  value: boolean;
  onChange: (v: boolean) => void;
  required?: boolean;
}) {
  return (
    <Pressable
      style={styles.consentRow}
      onPress={() => !required && onChange(!value)}>
      <View style={styles.consentText}>
        <Text style={styles.consentLabel}>
          {label}
          {required ? ' (required)' : ''}
        </Text>
        <Text style={styles.consentDesc}>{description}</Text>
      </View>
      <View
        style={[
          styles.consentToggle,
          value && styles.consentToggleOn,
        ]}>
        <Text style={styles.consentToggleText}>{value ? 'ON' : 'OFF'}</Text>
      </View>
    </Pressable>
  );
}

function ConsentSection() {
  const consent = useConsentStore((s) => s.consent);
  const updateConsent = useConsentStore((s) => s.updateConsent);
  const revokeAll = useConsentStore((s) => s.revokeAll);
  const restoreDefaults = useConsentStore((s) => s.restoreDefaults);

  const handleRevokeAll = () => {
    Alert.alert(
      'Revoke Data Consent',
      'This will stop all data collection for coaching improvement. Your existing data will be flagged for deletion.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Revoke All', style: 'destructive', onPress: revokeAll },
      ],
    );
  };

  if (consent.revoked) {
    return (
      <View style={styles.consentRevokedCard}>
        <Text style={styles.consentRevokedText}>
          All data-use consent has been revoked. No training examples will be collected or used.
        </Text>
        <Pressable style={styles.button} onPress={restoreDefaults}>
          <Text style={styles.buttonText}>Restore Defaults</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <>
      <Text style={styles.consentIntro}>
        Your health and training data is used to provide personalized coaching.
        You control how your data is used beyond your own account.
      </Text>

      <ConsentToggle
        label="Personal coaching"
        description="Use your data to improve recommendations for you. Data stays in your account."
        value={consent.personal_coaching}
        onChange={(v) => updateConsent({ personal_coaching: v })}
      />

      <ConsentToggle
        label="Improve global models"
        description="Allow de-identified data to improve coaching for all users. Your identity is stripped."
        value={consent.deidentified_models}
        onChange={(v) => updateConsent({ deidentified_models: v })}
      />

      <ConsentToggle
        label="Research & analytics"
        description="Allow aggregated, anonymous data for research. No individual records are exposed."
        value={consent.analytics_research}
        onChange={(v) => updateConsent({ analytics_research: v })}
      />

      <Pressable style={styles.resetButton} onPress={handleRevokeAll}>
        <Text style={[styles.resetText, { color: '#ff6b6b' }]}>
          Revoke All Data Consent
        </Text>
      </Pressable>
    </>
  );
}

// ---------------------------------------------------------------------------
// Tier & Capabilities
// ---------------------------------------------------------------------------

const ALL_TIERS: Tier[] = ['free', 'low_cost', 'pro', 'ai_premium'];

function TierSection() {
  const effectiveTier = useTierStore((s) => s.effectiveTier());
  const devOverride = useTierStore((s) => s.devOverride);
  const setDevOverride = useTierStore((s) => s.setDevOverride);
  const capabilities = useTierStore((s) => s.capabilities());
  const tierInfo = TIER_INFO[effectiveTier];

  // Group capabilities by tier for display
  const enabledCaps = capabilities;
  const allCaps: Capability[] = [
    'local_coaching', 'manual_training_log', 'feedback_capture',
    'local_health_view', 'basic_insights', 'health_sync',
    'backend_persistence', 'export_ai_payload', 'preference_coaching',
    'training_history', 'byo_ai', 'advanced_reports', 'cronometer_sync',
    'ergzone_sync', 'data_export_full', 'model_training_participation',
    'hosted_ai_coaching', 'daily_ai_recommendations',
    'advanced_ai_insights', 'priority_model_training',
  ];
  const disabledCaps = allCaps.filter((c) => !enabledCaps.includes(c));

  return (
    <>
      <View style={styles.tierHeader}>
        <Text style={[styles.tierBadge, { color: tierInfo.color, borderColor: tierInfo.color }]}>
          {tierInfo.label}
        </Text>
        <Text style={styles.tierNote}>
          {devOverride ? '(dev override)' : ''}
        </Text>
      </View>

      {/* Enabled capabilities */}
      <View style={styles.capList}>
        {enabledCaps.slice(0, 8).map((cap) => {
          const info = CAPABILITY_INFO[cap];
          return (
            <View key={cap} style={styles.capRow}>
              <Text style={styles.capEnabled}>✓</Text>
              <Text style={styles.capLabel}>{info.label}</Text>
            </View>
          );
        })}
        {enabledCaps.length > 8 && (
          <Text style={styles.capMore}>+{enabledCaps.length - 8} more</Text>
        )}
      </View>

      {/* Hidden premium capabilities */}
      {disabledCaps.length > 0 && (
        <View style={styles.capList}>
          <Text style={styles.capSectionLabel}>Premium</Text>
          {disabledCaps.slice(0, 5).map((cap) => {
            const info = CAPABILITY_INFO[cap];
            const minTier = minimumTierFor(cap);
            return (
              <View key={cap} style={styles.capRow}>
                <Text style={styles.capLocked}>✗</Text>
                <Text style={styles.capLabelLocked}>{info.label}</Text>
                <Text style={styles.capTierReq}>{TIER_INFO[minTier].label}</Text>
              </View>
            );
          })}
          {disabledCaps.length > 5 && (
            <Text style={styles.capMore}>+{disabledCaps.length - 5} more in higher tiers</Text>
          )}
        </View>
      )}

      {/* Dev tier override */}
      <View style={styles.devSection}>
        <Text style={styles.devLabel}>Dev Override</Text>
        <View style={styles.pillRow}>
          <Pressable
            style={[styles.pill, devOverride === null && styles.pillActive]}
            onPress={() => setDevOverride(null)}>
            <Text style={[styles.pillText, devOverride === null && styles.pillTextActive]}>
              None
            </Text>
          </Pressable>
          {ALL_TIERS.map((t) => (
            <Pressable
              key={t}
              style={[styles.pill, devOverride === t && { borderColor: TIER_INFO[t].color, backgroundColor: TIER_INFO[t].color + '15' }]}
              onPress={() => setDevOverride(t)}>
              <Text
                style={[styles.pillText, devOverride === t && { color: TIER_INFO[t].color, fontWeight: '600' }]}>
                {TIER_INFO[t].label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>
    </>
  );
}

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
        <Text style={styles.sectionTitle}>Subscription & Features</Text>
        <TierSection />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data & Privacy</Text>
        <ConsentSection />
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

  // Consent
  consentIntro: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
  consentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 12,
  },
  consentText: { flex: 1, gap: 2 },
  consentLabel: { fontSize: 14, fontWeight: '600' },
  consentDesc: { fontSize: 12, opacity: 0.5, lineHeight: 16 },
  consentToggle: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#666',
  },
  consentToggleOn: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.15)',
  },
  consentToggleText: { fontSize: 12, fontWeight: '600', color: '#999' },
  consentRevokedCard: {
    padding: 16,
    borderRadius: 10,
    backgroundColor: 'rgba(255,107,107,0.1)',
    borderWidth: 1,
    borderColor: '#ff6b6b',
    gap: 12,
  },
  consentRevokedText: { fontSize: 13, color: '#ff6b6b', lineHeight: 18 },

  // Tier
  tierHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  tierBadge: {
    fontSize: 16,
    fontWeight: '700',
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 4,
    paddingHorizontal: 10,
  },
  tierNote: { fontSize: 12, opacity: 0.4 },
  capList: { gap: 4 },
  capSectionLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 4 },
  capRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  capEnabled: { fontSize: 13, color: '#4ade80', width: 18 },
  capLocked: { fontSize: 13, color: '#666', width: 18 },
  capLabel: { fontSize: 13, flex: 1 },
  capLabelLocked: { fontSize: 13, opacity: 0.4, flex: 1 },
  capTierReq: { fontSize: 10, opacity: 0.3 },
  capMore: { fontSize: 11, opacity: 0.3, paddingLeft: 26 },
  devSection: { gap: 6, marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)' },
  devLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5 },

  // Schedule editor
  scheduleDayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    marginBottom: 2,
    gap: 8,
  },
  scheduleDayRowExpanded: { backgroundColor: 'rgba(232,255,71,0.06)', borderBottomLeftRadius: 0, borderBottomRightRadius: 0 },
  scheduleDayName: { fontSize: 14, fontWeight: '600', width: 36 },
  scheduleDayCount: { flex: 1, fontSize: 12, opacity: 0.6 },
  scheduleChevron: { fontSize: 12, opacity: 0.4 },
  scheduleDayExpanded: {
    backgroundColor: 'rgba(255,255,255,0.02)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
    marginBottom: 2,
    gap: 6,
  },
  scheduleSessionRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scheduleSessionCheck: { fontSize: 16, color: '#4ade80', width: 20 },
  scheduleSessionName: { flex: 1, fontSize: 13 },
  scheduleRemove: { fontSize: 14, color: '#ff6b6b', padding: 4 },
  scheduleAddRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  scheduleAddBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: 'rgba(232,255,71,0.15)',
  },
  scheduleAddBtnText: { color: '#e8ff47', fontSize: 12, fontWeight: '600' },
  pillSmall: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillSmallText: { fontSize: 11, color: '#999' },
});
