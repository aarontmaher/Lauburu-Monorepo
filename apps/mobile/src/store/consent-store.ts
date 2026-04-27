/**
 * Data governance / consent store.
 * Tracks user's data-use preferences for training examples.
 */
import { create } from 'zustand';
import { CONSENT_VERSION, DEFAULT_CONSENT, buildEligibility } from '@lauburu/shared';
import type { DataConsent, DataEligibility } from '@lauburu/shared';
import { readStoredJson, writeStoredJson } from './secure-storage';

const STORAGE_KEY = 'data_consent_v1';
const VALID_SOURCES: ReadonlySet<DataConsent['source']> = new Set([
  'mobile_app',
  'website',
  'api',
]);

async function persistSafely(consent: DataConsent): Promise<void> {
  await writeStoredJson(STORAGE_KEY, consent);
}

function sanitizeConsent(value: unknown): DataConsent | null {
  if (!value || typeof value !== 'object') return null;
  const parsed = value as Partial<DataConsent>;
  const now = new Date().toISOString();
  const grantedAt =
    typeof parsed.granted_at === 'string' && parsed.granted_at.length > 0
      ? parsed.granted_at
      : now;
  const updatedAt =
    typeof parsed.updated_at === 'string' && parsed.updated_at.length > 0
      ? parsed.updated_at
      : grantedAt;

  return {
    // Merge onto defaults so newly added flags at a bumped CONSENT_VERSION
    // get sensible defaults rather than undefined, but only accept
    // fields that match the expected runtime shape.
    version: CONSENT_VERSION,
    granted_at: grantedAt,
    updated_at: updatedAt,
    source: VALID_SOURCES.has(parsed.source as DataConsent['source'])
      ? (parsed.source as DataConsent['source'])
      : DEFAULT_CONSENT.source,
    personal_coaching:
      typeof parsed.personal_coaching === 'boolean'
        ? parsed.personal_coaching
        : DEFAULT_CONSENT.personal_coaching,
    deidentified_models:
      typeof parsed.deidentified_models === 'boolean'
        ? parsed.deidentified_models
        : DEFAULT_CONSENT.deidentified_models,
    analytics_research:
      typeof parsed.analytics_research === 'boolean'
        ? parsed.analytics_research
        : DEFAULT_CONSENT.analytics_research,
    revoked:
      typeof parsed.revoked === 'boolean'
        ? parsed.revoked
        : DEFAULT_CONSENT.revoked,
  };
}

function freshDefaultConsent(): DataConsent {
  const now = new Date().toISOString();
  return {
    ...DEFAULT_CONSENT,
    granted_at: now,
    updated_at: now,
  };
}

interface ConsentState {
  consent: DataConsent;
  hydrated: boolean;

  hydrate: () => Promise<void>;

  /** Update specific consent flags */
  updateConsent: (partial: Partial<Pick<DataConsent, 'personal_coaching' | 'deidentified_models' | 'analytics_research'>>) => void;

  /** Revoke all data-use consent */
  revokeAll: () => void;

  /** Restore consent after revocation */
  restoreDefaults: () => void;

  /** Build eligibility tags from current consent for a user */
  getEligibility: (userId: string | null) => DataEligibility;

  /** Delete/reset all training data flags (marks as revoked) */
  deleteTrainingData: () => void;
}

export const useConsentStore = create<ConsentState>((set, get) => ({
  consent: freshDefaultConsent(),
  hydrated: false,

  hydrate: async () => {
    try {
      const parsed = await readStoredJson<unknown>(STORAGE_KEY);
      const next = sanitizeConsent(parsed);
      if (next) {
        // Rewrite the sanitized current-shape blob so partial or
        // older persisted values are upgraded in place on first launch.
        void persistSafely(next);
      }
      set({
        consent: next ?? freshDefaultConsent(),
        hydrated: true,
      });
    } catch {
      set({
        consent: freshDefaultConsent(),
        hydrated: true,
      });
    }
  },

  updateConsent: (partial) => {
    set((s) => {
      const consent: DataConsent = {
        ...s.consent,
        ...partial,
        updated_at: new Date().toISOString(),
        revoked: false,
      };
      void persistSafely(consent);
      return { consent };
    });
  },

  revokeAll: () => {
    set((s) => {
      const consent: DataConsent = {
        ...s.consent,
        personal_coaching: false,
        deidentified_models: false,
        analytics_research: false,
        revoked: true,
        updated_at: new Date().toISOString(),
      };
      void persistSafely(consent);
      return { consent };
    });
  },

  restoreDefaults: () => {
    const consent = freshDefaultConsent();
    set({ consent });
    void persistSafely(consent);
  },

  getEligibility: (userId) => {
    return buildEligibility(userId, get().consent);
  },

  deleteTrainingData: () => {
    // Revoke consent — actual data deletion would happen on backend
    get().revokeAll();
  },
}));
