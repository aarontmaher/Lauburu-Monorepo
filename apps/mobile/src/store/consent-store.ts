/**
 * Data governance / consent store.
 * Tracks user's data-use preferences for training examples.
 */
import { create } from 'zustand';
import { CONSENT_VERSION, DEFAULT_CONSENT, buildEligibility } from '@lauburu/shared';
import type { DataConsent, DataEligibility } from '@lauburu/shared';

interface ConsentState {
  consent: DataConsent;

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
  consent: {
    ...DEFAULT_CONSENT,
    granted_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },

  updateConsent: (partial) => {
    set((s) => ({
      consent: {
        ...s.consent,
        ...partial,
        updated_at: new Date().toISOString(),
        revoked: false,
      },
    }));
  },

  revokeAll: () => {
    set((s) => ({
      consent: {
        ...s.consent,
        personal_coaching: false,
        deidentified_models: false,
        analytics_research: false,
        revoked: true,
        updated_at: new Date().toISOString(),
      },
    }));
  },

  restoreDefaults: () => {
    set({
      consent: {
        ...DEFAULT_CONSENT,
        granted_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
  },

  getEligibility: (userId) => {
    return buildEligibility(userId, get().consent);
  },

  deleteTrainingData: () => {
    // Revoke consent — actual data deletion would happen on backend
    get().revokeAll();
  },
}));
