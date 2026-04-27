import type { AthleteSourceSnapshot } from '@lauburu/shared';

export interface AthletePerformanceSourceAdapter {
  loadAthleteSource(athleteId: string): Promise<AthleteSourceSnapshot>;
}
