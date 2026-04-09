/**
 * Health records / lab data — opt-in deeper health context.
 *
 * Supports future upload or manual entry of:
 * - Blood tests (CBC, metabolic panel, hormones, etc.)
 * - Spirometry / lung function
 * - Medications
 * - Supplements
 * - Confidential substance/hormone history
 *
 * Privacy:
 * - All records are opt-in
 * - Substance/hormone data is CONFIDENTIAL — never shared in
 *   de-identified or analytics paths even with consent
 * - Privacy level controls visibility to coaching/AI layers
 *
 * No parsing, dosing logic, or PED guidance is built.
 * This is structured context storage only.
 */

export type HealthRecordType =
  | 'blood_test'
  | 'spirometry'
  | 'body_composition'
  | 'medication'
  | 'supplement'
  | 'substance_history'
  | 'vaccination'
  | 'injury'
  | 'other';

export type HealthRecordSource = 'manual' | 'lab_upload' | 'provider_import' | 'photo_capture';

export type HealthRecordPrivacy =
  | 'coaching_visible'    // AI/coaching can see this
  | 'personal_only'       // Only the user sees this
  | 'confidential';       // Never leaves the device / never in any export

export interface HealthRecord {
  id: string;
  user_id: string;
  created_at: string;

  /** Record classification */
  record_type: HealthRecordType;
  source: HealthRecordSource;
  date: string; // YYYY-MM-DD

  /** Human-readable label (e.g., "Full blood panel", "Testosterone") */
  label: string;

  /** Structured values — flexible key-value for different record types */
  values: Record<string, string | number | boolean>;

  /** Free-text notes */
  notes?: string;

  /** Privacy level */
  privacy: HealthRecordPrivacy;

  /** Attachment metadata placeholder (future file upload) */
  attachment?: {
    filename: string;
    mime_type: string;
    size_bytes: number;
    /** Local URI or remote URL — populated when attachment is uploaded */
    uri?: string;
  };

  /** Backend persistence status */
  persisted: boolean;
}

export interface HealthRecordInput {
  record_type: HealthRecordType;
  source: HealthRecordSource;
  date: string;
  label: string;
  values: Record<string, string | number | boolean>;
  notes?: string;
  privacy: HealthRecordPrivacy;
}

export const HEALTH_RECORD_TYPE_LABELS: Record<HealthRecordType, string> = {
  blood_test: 'Blood Test',
  spirometry: 'Spirometry / Lung Function',
  body_composition: 'Body Composition',
  medication: 'Medication',
  supplement: 'Supplement',
  substance_history: 'Substance History',
  vaccination: 'Vaccination',
  injury: 'Injury',
  other: 'Other',
};

export const HEALTH_RECORD_PRIVACY_LABELS: Record<HealthRecordPrivacy, string> = {
  coaching_visible: 'Visible to coaching',
  personal_only: 'Personal only',
  confidential: 'Confidential (device only)',
};

/**
 * Common blood test value keys for structured entry.
 * Not exhaustive — users can add custom keys.
 */
export const COMMON_BLOOD_TEST_KEYS = [
  'hemoglobin',
  'hematocrit',
  'rbc',
  'wbc',
  'platelets',
  'ferritin',
  'iron',
  'vitamin_d',
  'vitamin_b12',
  'testosterone_total',
  'testosterone_free',
  'cortisol',
  'tsh',
  'crp',
  'glucose_fasting',
  'hba1c',
  'cholesterol_total',
  'hdl',
  'ldl',
  'triglycerides',
  'creatinine',
  'egfr',
] as const;
