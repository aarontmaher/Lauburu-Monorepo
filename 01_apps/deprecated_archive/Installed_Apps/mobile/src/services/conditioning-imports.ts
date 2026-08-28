import { Platform } from 'react-native';
import type { Workout } from '@lauburu/shared';

export type ConditioningSourceType =
  | 'apple_health'
  | 'health_connect'
  | 'fit_file'
  | 'tcx_file'
  | 'csv_file'
  | 'manual';

export type ConditioningWorkoutType =
  | 'HIIT'
  | 'rowing'
  | 'ski_erg'
  | 'bike_erg'
  | 'assault_bike'
  | 'conditioning'
  | 'unknown';

export interface ConditioningImportSummary {
  sourceApp: string;
  sourceType: ConditioningSourceType;
  workoutType: ConditioningWorkoutType;
  startTime: string | null;
  endTime: string | null;
  durationMin: number;
  calories: number | null;
  distanceM: number | null;
  avgHr: number | null;
  maxHr: number | null;
  intervalsAvailable: boolean;
  provenanceLabel: string;
  missingIntervalLabel: string | null;
}

export const CONDITIONING_IMPORT_COPY = {
  title: 'Conditioning imports',
  body:
    'Import conditioning workouts from apps that sync to Apple Health / Health Connect.',
  examples:
    'ErgZone, Rogue, Concept2, Strava, TrainingPeaks, Intervals.icu, and others may appear here if they write to your health hub.',
  future:
    'FIT / TCX / CSV file import is optional backlog, not the primary path.',
} as const;

export function buildConditioningImportSummaries(
  workouts: Workout[],
  sourceType: ConditioningSourceType = Platform.OS === 'ios' ? 'apple_health' : 'health_connect',
): ConditioningImportSummary[] {
  return workouts
    .filter((workout) => isConditioningLikeWorkout(workout))
    .map((workout) => {
      const sourceApp = friendlySourceApp(workout.source);
      const intervalsAvailable = (workout.detail?.intervals?.length ?? 0) > 0;
      return {
        sourceApp,
        sourceType,
        workoutType: classifyWorkoutType(workout),
        startTime: workout.start_time ?? null,
        endTime: workout.end_time ?? null,
        durationMin: workout.duration_min,
        calories: workout.calories ?? null,
        distanceM: workout.distance_m ?? null,
        avgHr: workout.avg_hr ?? null,
        maxHr: workout.max_hr ?? null,
        intervalsAvailable,
        provenanceLabel: `${sourceApp} via ${sourceTypeLabel(sourceType)}`,
        missingIntervalLabel: intervalsAvailable
          ? null
          : 'Workout summary imported; interval splits not available.',
      };
    });
}

export function sourceTypeLabel(sourceType: ConditioningSourceType): string {
  switch (sourceType) {
    case 'apple_health':
      return 'Apple Health';
    case 'health_connect':
      return 'Health Connect';
    case 'fit_file':
      return 'FIT file';
    case 'tcx_file':
      return 'TCX file';
    case 'csv_file':
      return 'CSV file';
    case 'manual':
      return 'Manual entry';
  }
}

function isConditioningLikeWorkout(workout: Workout): boolean {
  const haystack = workoutText(workout);
  if (workout.is_grappling) return false;
  return /(hiit|interval|conditioning|row|rowing|erg|bike|cycling|cycle|assault|airbike|ski|cardio|run|treadmill|elliptical|concept2|ergdata|ergzone|rogue|strava|trainingpeaks|intervals\.?icu)/i.test(haystack);
}

function classifyWorkoutType(workout: Workout): ConditioningWorkoutType {
  const haystack = workoutText(workout);
  if (/(hiit|interval|tabata|sprint)/i.test(haystack)) return 'HIIT';
  if (/(row|rowing|rower|ergdata|concept2)/i.test(haystack)) return 'rowing';
  if (/(ski|skierg|ski erg)/i.test(haystack)) return 'ski_erg';
  if (/(assault|airbike|echo bike|rogue)/i.test(haystack)) return 'assault_bike';
  if (/(bike|cycling|cycle|erg)/i.test(haystack)) return 'bike_erg';
  if (/(conditioning|cardio|treadmill|elliptical|run)/i.test(haystack)) return 'conditioning';
  return 'unknown';
}

function workoutText(workout: Workout): string {
  return [
    workout.type,
    workout.sport_label,
    workout.source,
    workout.detail?.machine_type,
  ]
    .filter(Boolean)
    .join(' ');
}

export function friendlySourceApp(source: string | undefined): string {
  if (!source) return 'Health hub';
  if (/apple|healthkit|com\.apple/i.test(source)) return 'Apple Health';
  if (/health\s?connect|android\.health|com\.google\.android\.apps\.healthdata/i.test(source)) return 'Health Connect';
  if (/samsung/i.test(source)) return 'Samsung Health';
  if (/google\s?fit|com\.google\.android\.apps\.fitness/i.test(source)) return 'Google Fit';
  if (/polar|flow/i.test(source)) return 'Polar Flow';
  if (/whoop/i.test(source)) return 'WHOOP';
  if (/ergdata/i.test(source)) return 'ErgData';
  if (/concept\s?2|com\.concept2/i.test(source)) return 'Concept2';
  if (/ergzone/i.test(source)) return 'ErgZone';
  if (/rogue/i.test(source)) return 'Rogue';
  if (/strava/i.test(source)) return 'Strava';
  if (/trainingpeaks/i.test(source)) return 'TrainingPeaks';
  if (/intervals\.?icu/i.test(source)) return 'Intervals.icu';
  return source;
}
