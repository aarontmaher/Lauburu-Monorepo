import type { AthleteDailyRefreshArtifact, AthleteMemoryRecord, AthleteWeeklySynthesisArtifact } from '@lauburu/shared';
import {
  generateAthleteDailyRefresh,
  generateAthleteWeeklySynthesis,
} from '@lauburu/shared';
import { FilePrivateAthleteMemoryRepository } from '../athlete-memory/file-private-athlete-memory-repository';
import type { AthletePerformanceSourceAdapter } from '../sources/athletePerformanceSource';

function toDateKey(date: Date, timeZone: string): string {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  return formatter.format(date);
}

function startOfWeek(dateKey: string): string {
  const date = new Date(`${dateKey}T00:00:00.000Z`);
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() - day + 1);
  return date.toISOString().slice(0, 10);
}

function enumerateDateRange(startDate: string, endDate: string): string[] {
  const dates: string[] = [];
  const cursor = new Date(`${startDate}T00:00:00.000Z`);
  const end = new Date(`${endDate}T00:00:00.000Z`);
  while (cursor <= end) {
    dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return dates;
}

export class AthleteRefreshService {
  constructor(
    private readonly repository: FilePrivateAthleteMemoryRepository,
    private readonly sourceAdapter: AthletePerformanceSourceAdapter,
  ) {}

  async runDailyRefreshForAthlete(
    athleteId: string,
    asOf: { date: Date; timeZone: string },
  ): Promise<AthleteDailyRefreshArtifact> {
    const sourceSnapshot = await this.sourceAdapter.loadAthleteSource(athleteId);
    const priorMemory = await this.repository.loadMemoryRecord(athleteId);
    const asOfDate = toDateKey(asOf.date, asOf.timeZone);
    const result = generateAthleteDailyRefresh({
      athleteId,
      history: sourceSnapshot.history,
      sourceState: sourceSnapshot.state,
      priorMemory,
      asOfDate,
    });
    await this.repository.saveDailyRefresh(athleteId, result.dailyRefresh);
    await this.repository.saveMemoryRecord(athleteId, result.updatedMemory);
    return result.dailyRefresh;
  }

  async ensureRecentDailyRefreshes(
    athleteId: string,
    asOf: { date: Date; timeZone: string },
    days = 7,
  ): Promise<AthleteDailyRefreshArtifact[]> {
    const targetEndDate = toDateKey(asOf.date, asOf.timeZone);
    const sourceSnapshot = await this.sourceAdapter.loadAthleteSource(athleteId);
    const historyDates = sourceSnapshot.history.map((day) => day.date).sort();
    const datesToEnsure = historyDates.filter(
      (date) => date >= startOfWeek(targetEndDate) && date <= targetEndDate,
    );

    const ensured: AthleteDailyRefreshArtifact[] = [];
    for (const date of datesToEnsure.slice(-days)) {
      const existing = (
        await this.repository.listDailyRefreshes(athleteId, { startDate: date, endDate: date, limit: 1 })
      )[0];
      if (existing) {
        ensured.push(existing);
        continue;
      }
      const priorMemory = await this.repository.loadMemoryRecord(athleteId);
      const result = generateAthleteDailyRefresh({
        athleteId,
        history: sourceSnapshot.history,
        sourceState: sourceSnapshot.state,
        priorMemory,
        asOfDate: date,
      });
      await this.repository.saveDailyRefresh(athleteId, result.dailyRefresh);
      await this.repository.saveMemoryRecord(athleteId, result.updatedMemory);
      ensured.push(result.dailyRefresh);
    }

    return ensured.sort((a, b) => a.sourceDate.localeCompare(b.sourceDate));
  }

  async runWeeklySynthesisForAthlete(
    athleteId: string,
    asOf: { date: Date; timeZone: string },
  ): Promise<AthleteWeeklySynthesisArtifact> {
    const asOfDate = toDateKey(asOf.date, asOf.timeZone);
    const weekStart = startOfWeek(asOfDate);
    const dailyRefreshes = await this.repository.listDailyRefreshes(athleteId, {
      startDate: weekStart,
      endDate: asOfDate,
    });
    const expectedDates = enumerateDateRange(weekStart, asOfDate);
    const availableDates = new Set(dailyRefreshes.map((daily) => daily.sourceDate));
    const missingDates = expectedDates.filter((date) => !availableDates.has(date));
    if (missingDates.length) {
      throw new Error(
        `Weekly synthesis requires stored daily refresh artifacts from ${weekStart} to ${asOfDate}. Missing: ${missingDates.join(', ')}`,
      );
    }

    const sourceSnapshot = await this.sourceAdapter.loadAthleteSource(athleteId);
    const priorMemory = await this.repository.loadMemoryRecord(athleteId);
    const result = generateAthleteWeeklySynthesis({
      athleteId,
      history: sourceSnapshot.history,
      sourceState: sourceSnapshot.state,
      priorMemory,
      asOfDate,
      dailyRefreshes,
    });
    await this.repository.saveWeeklySynthesis(athleteId, result.weeklySynthesis);
    await this.repository.saveMemoryRecord(athleteId, result.updatedMemory);
    return result.weeklySynthesis;
  }

  async readLatestArtifacts(
    athleteId: string,
  ): Promise<{
    memory: AthleteMemoryRecord | null;
    latestDaily: AthleteDailyRefreshArtifact | null;
    latestWeekly: AthleteWeeklySynthesisArtifact | null;
  }> {
    const [memory, latestDaily, latestWeekly] = await Promise.all([
      this.repository.loadMemoryRecord(athleteId),
      this.repository.getLatestDailyRefresh(athleteId),
      this.repository.getLatestWeeklySynthesis(athleteId),
    ]);
    return { memory, latestDaily, latestWeekly };
  }
}
