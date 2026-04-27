import type { DailyMetrics } from '../types/health';
import type { AthleteSourceState } from './types';

export interface AthleteSourceSnapshot {
  athleteId: string;
  state: AthleteSourceState;
  history: DailyMetrics[];
}
