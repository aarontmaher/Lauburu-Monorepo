/**
 * App tour content — shared first-time guidance definitions.
 * Not athlete-specific. Consumed by mobile for onboarding/help.
 */

export interface TourStep {
  id: string;
  title: string;
  body: string;
  detail?: string | null;
  /** Which app surface this step relates to. */
  surface:
    | 'home'
    | 'health'
    | 'nutrition'
    | 'train'
    | 'hiit'
    | 'map'
    | 'reference'
    | 'syllabus'
    | 'coach'
    | 'filters'
    | 'settings'
    | 'general';
}

export interface AppTourContent {
  schemaVersion: 1;
  updatedAt: string;
  steps: TourStep[];
}
