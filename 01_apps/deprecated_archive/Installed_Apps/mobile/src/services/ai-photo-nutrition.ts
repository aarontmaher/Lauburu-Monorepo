/**
 * AI meal photo nutrition service boundary.
 *
 * Mobile-side adapter for the AI photo proposal flow:
 * 1. User takes photo → submitPhotoProposal()
 * 2. Backend returns AI estimate → user reviews
 * 3. User confirms/edits → confirmPhotoProposal()
 * 4. Only confirmed/edited proposals enter nutrition totals
 *
 * The AI estimation backend endpoint is not yet implemented.
 * This service provides the clean boundary so screens can wire
 * to it when the backend is ready.
 */
import { AI_INTERNAL_BASE, AI_INTERNAL_TOKEN } from './ai-backend-config';

export type PhotoProposalStatus = 'proposed' | 'user_confirmed' | 'user_edited' | 'rejected';

export interface PhotoProposalResult {
  ok: boolean;
  proposalId: string;
  status: PhotoProposalStatus;
  enteredNormalized: boolean;
  proposedCalories: number | null;
  proposedProteinG: number | null;
  proposedCarbG: number | null;
  proposedFatG: number | null;
  confidence: 'high' | 'medium' | 'low';
  description: string;
  missingFields: string[];
  error?: string;
}

/**
 * Submit a photo for AI meal estimation.
 * Returns a proposal with proposed macros in `proposed` status.
 * The proposal does NOT enter nutrition totals until confirmed.
 */
export async function submitPhotoProposal(
  athleteId: string,
  photoRef: string,
): Promise<PhotoProposalResult> {
  const proposalId = `photo-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  if (!AI_INTERNAL_TOKEN) {
    return {
      ok: false, proposalId, status: 'proposed', enteredNormalized: false,
      proposedCalories: null, proposedProteinG: null, proposedCarbG: null, proposedFatG: null,
      confidence: 'low', description: 'Backend not configured.', missingFields: ['calories', 'protein', 'carbs', 'fat'],
      error: 'No backend token configured.',
    };
  }
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    const resp = await fetch(`${AI_INTERNAL_BASE}/nutrition/photo-proposal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({
        athleteId,
        proposal: {
          proposalId,
          photoRef,
          description: '',
          proposedCalories: null,
          proposedProteinG: null,
          proposedCarbG: null,
          proposedFatG: null,
          confidence: 'low',
          missingFields: ['calories', 'protein', 'carbs', 'fat'],
        },
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const data = await resp.json();
    return {
      ok: data.ok ?? false,
      proposalId,
      status: 'proposed',
      enteredNormalized: false,
      proposedCalories: null,
      proposedProteinG: null,
      proposedCarbG: null,
      proposedFatG: null,
      confidence: 'low',
      description: 'AI estimation not yet available. Enter macros manually.',
      missingFields: ['calories', 'protein', 'carbs', 'fat'],
    };
  } catch {
    return {
      ok: false,
      proposalId,
      status: 'proposed',
      enteredNormalized: false,
      proposedCalories: null,
      proposedProteinG: null,
      proposedCarbG: null,
      proposedFatG: null,
      confidence: 'low',
      description: 'AI estimation service unavailable.',
      missingFields: ['calories', 'protein', 'carbs', 'fat'],
      error: 'AI estimation backend not available.',
    };
  }
}

/**
 * Confirm, edit, or reject a photo proposal.
 * Only confirmed/edited proposals enter nutrition totals.
 */
export async function confirmPhotoProposal(
  athleteId: string,
  proposalId: string,
  action: 'user_confirmed' | 'user_edited' | 'rejected',
  finalMacros?: {
    calories?: number | null;
    proteinG?: number | null;
    carbG?: number | null;
    fatG?: number | null;
  },
): Promise<{ ok: boolean; enteredNormalized: boolean; error?: string }> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    const resp = await fetch(`${AI_INTERNAL_BASE}/nutrition/photo-confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({
        athleteId,
        proposalId,
        action,
        finalCalories: finalMacros?.calories ?? null,
        finalProteinG: finalMacros?.proteinG ?? null,
        finalCarbG: finalMacros?.carbG ?? null,
        finalFatG: finalMacros?.fatG ?? null,
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const data = await resp.json();
    return {
      ok: data.ok ?? false,
      enteredNormalized: data.enteredNormalized ?? false,
    };
  } catch {
    return { ok: false, enteredNormalized: false, error: 'Confirmation failed.' };
  }
}
