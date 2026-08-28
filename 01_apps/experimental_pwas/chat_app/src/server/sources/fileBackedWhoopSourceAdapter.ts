import type { AthletePerformanceSourceAdapter } from './athletePerformanceSource';
import type { AthleteSourceSnapshot } from '@lauburu/shared';
import { FilePrivateAthleteMemoryRepository } from '../athlete-memory/file-private-athlete-memory-repository';

export class FileBackedWhoopSourceAdapter implements AthletePerformanceSourceAdapter {
  constructor(private readonly repository: FilePrivateAthleteMemoryRepository) {}

  async loadAthleteSource(athleteId: string): Promise<AthleteSourceSnapshot> {
    const history = await this.repository.loadMetricsHistory(athleteId);
    const sortedDates = history.map((day) => day.date).sort();
    const latestDataDate = sortedDates.length ? sortedDates[sortedDates.length - 1] : null;

    return {
      athleteId,
      history,
      state: {
        sourceType: 'cached_history_file',
        status: history.length ? 'degraded' : 'unavailable',
        authState: 'missing',
        latestDataDate,
        fallbackReason: history.length ? 'whoop_mcp_auth_not_restored' : 'cached_history_only',
        sourceCoverage: history.length ? ['cached_whoop_history_file'] : [],
        missingInputs: history.length ? [] : ['whoop_history'],
        confidence: history.length ? 'medium' : 'low',
        ruleBasis: [
          'Backend WHOOP MCP auth refresh is not restored in this repo yet.',
          'Private athlete refresh is using cached file-backed history as an explicit fallback.',
        ],
      },
    };
  }
}
