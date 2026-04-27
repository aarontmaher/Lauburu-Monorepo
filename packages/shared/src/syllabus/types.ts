/**
 * Belt syllabus contracts — shared curriculum definitions that
 * the mobile app, map, and reference system can all consume.
 *
 * Architecture:
 *   - SyllabusBelt / SyllabusRequirement = SHARED curriculum definition
 *     (same for all athletes, curated by the product owner)
 *   - AthleteSyllabusProgress = PRIVATE per-athlete progress
 *     (stored separately, never mixed into shared definitions)
 *
 * Requirements reference canonical map/reference identifiers:
 *   - sectionId: matches ReferenceSection.id (e.g. 'dominant_positions')
 *   - positionName: matches ReferencePosition.name (e.g. 'Mount')
 *   - heading: matches standard headings (e.g. 'Submissions')
 *   - techniqueName: matches technique labels from REFERENCE_TECHNIQUES
 *
 * Progress key format is compatible with reference-progress-store:
 *   tech|<section>|<position>|<role>|<heading>|<technique>
 */

// ---------------------------------------------------------------------------
// Shared curriculum definitions (non-personal)
// ---------------------------------------------------------------------------

export type BeltLevel =
  | 'white'
  | 'blue'
  | 'purple'
  | 'brown'
  | 'black';

export type RequirementType =
  | 'technique'     // must know a specific technique
  | 'position'      // must be competent in a position (any role)
  | 'transition'    // must know a transition between positions
  | 'concept'       // must understand a concept (e.g. "guard retention principles")
  | 'sparring';     // must demonstrate live application

export type RequirementPriority = 'core' | 'recommended' | 'supplementary';

/** A single requirement in a belt syllabus. */
export interface SyllabusRequirement {
  /** Unique stable ID for this requirement. */
  id: string;
  /** Human-readable label. */
  label: string;
  /** What type of requirement this is. */
  type: RequirementType;
  /** Priority within the belt. */
  priority: RequirementPriority;
  /** Optional description / coaching note. */
  description: string | null;

  // ── Map/reference anchors ────────────────────────────────
  /** Section ID from reference-seed (e.g. 'dominant_positions'). Null for concept/sparring types. */
  sectionId: string | null;
  /** Position name from reference-seed (e.g. 'Mount'). Null for concept/sparring types. */
  positionName: string | null;
  /** Heading within the position (e.g. 'Submissions'). Null if position-level. */
  heading: string | null;
  /** Specific technique name. Null if position-level or concept. */
  techniqueName: string | null;
  /** Role/perspective (e.g. 'Attacker'). Null if both perspectives apply. */
  role: string | null;

  /**
   * Reference progress key — if this requirement maps to a specific
   * technique in the reference system, this is the key format:
   * tech|<section>|<position>|<role>|<heading>|<technique>
   * Null for concept/sparring/position-level requirements.
   */
  progressKey: string | null;
}

/** A belt-level syllabus definition. */
export interface SyllabusBelt {
  /** Belt level. */
  belt: BeltLevel;
  /** Human-readable title. */
  title: string;
  /** Estimated requirements count. */
  requirementCount: number;
  /** Ordered requirements for this belt. */
  requirements: SyllabusRequirement[];
}

/** The full syllabus across all belts. */
export interface Syllabus {
  /** Schema version. */
  schemaVersion: 1;
  /** When this syllabus was last updated. */
  updatedAt: string;
  /** Belts in order (white → black). */
  belts: SyllabusBelt[];
}

// ---------------------------------------------------------------------------
// Athlete-scoped progress (private, per-athlete)
// ---------------------------------------------------------------------------

export type SyllabusItemStatus =
  | 'not_started'
  | 'in_progress'
  | 'demonstrated'  // shown in drilling/technique context
  | 'verified';     // confirmed by coach or sparring

/** Progress on a single syllabus requirement for one athlete. */
export interface AthleteSyllabusItemProgress {
  /** The requirement ID this progress tracks. */
  requirementId: string;
  /** Current status. */
  status: SyllabusItemStatus;
  /** When this was last updated. */
  updatedAt: string;
  /** Optional notes from athlete or coach. */
  notes: string | null;
  /**
   * Whether this was auto-derived from reference progress store.
   * If true, the status was inferred from the athlete's existing
   * drilling/learned/tracking state on the mapped technique.
   */
  derivedFromReferenceProgress: boolean;
}

/** Full syllabus progress for one athlete. */
export interface AthleteSyllabusProgress {
  athleteId: string;
  /** Which belt this progress is being tracked against. */
  currentBelt: BeltLevel;
  /** When this progress record was last updated. */
  updatedAt: string;
  /** Per-requirement progress. */
  items: AthleteSyllabusItemProgress[];
  /** Summary counts. */
  summary: {
    total: number;
    notStarted: number;
    inProgress: number;
    demonstrated: number;
    verified: number;
  };
}

// ---------------------------------------------------------------------------
// Compact progress response for mobile consumption
// ---------------------------------------------------------------------------

export interface SyllabusSectionCount {
  total: number;
  started: number;
  demonstrated: number;
}

/** Compact response shape the backend returns for mobile syllabus display. */
export interface AthleteSyllabusProgressResponse {
  ok: boolean;
  athleteId: string;
  belt: BeltLevel;
  updatedAt: string;
  summary: AthleteSyllabusProgress['summary'];
  sectionCounts: Record<string, SyllabusSectionCount>;
  items: AthleteSyllabusItemProgress[];
  derivedFromReferenceProgress: boolean;
  progressConfidenceNote: string;
  promotionReadinessNote: string;
}
