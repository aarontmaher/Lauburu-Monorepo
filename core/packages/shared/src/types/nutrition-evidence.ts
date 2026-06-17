/**
 * Nutrition evidence types — raw evidence before normalization.
 * Barcode scans, AI photo estimates, and manual entries all
 * produce evidence records that require confirmation before
 * entering normalized nutrition.
 */

export type NutritionEvidenceSource =
  | 'manual'
  | 'barcode_scan'
  | 'product_search'
  | 'ai_photo_estimate'
  | 'cronometer'
  | 'openfoodfacts';

export type NutritionEvidenceStatus =
  | 'confirmed'         // user confirmed → safe for normalized nutrition
  | 'pending_review'    // proposal awaiting user confirmation
  | 'rejected'          // user rejected this estimate
  | 'incomplete';       // captured but missing key fields

export interface NutritionEvidence {
  id: string;
  date: string;
  source: NutritionEvidenceSource;
  status: NutritionEvidenceStatus;
  createdAt: string;
  updatedAt: string;

  /** Raw evidence — what was captured. */
  raw: {
    /** Barcode string if from scan. */
    barcode: string | null;
    /** Photo URI if from camera. */
    photoUri: string | null;
    /** Product name from lookup or AI. */
    productName: string | null;
    /** Serving size description. */
    servingSize: string | null;
  };

  /** Proposed/confirmed macros. Null until estimated or entered. */
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fibre_g: number | null;

  /** How confident the estimate is (for AI photo/barcode lookup). */
  confidence: 'high' | 'medium' | 'low' | null;

  /** What's missing from this evidence. */
  missingFields: string[];

  /** Whether user has confirmed this for normalized nutrition. */
  confirmedByUser: boolean;
}
