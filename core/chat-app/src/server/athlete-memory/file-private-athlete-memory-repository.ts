import { promises as fs } from 'fs';
import path from 'path';
import type {
  AthleteDailyRefreshArtifact,
  AthleteMemoryRecord,
  AthleteWeeklySynthesisArtifact,
  DailyMetrics,
} from '@lauburu/shared';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';
import type { WhoopDailyMetricsRaw } from '../../../../packages/shared/src/backend/contracts/whoop-raw.types';

export interface PrivateAthleteManifest {
  athleteId: string;
  displayName: string;
  timezone: string;
  autoRefresh: {
    daily: boolean;
    weekly: boolean;
  };
}

export class FilePrivateAthleteMemoryRepository {
  constructor(private readonly baseDir: string) {}

  async listAthletes(): Promise<PrivateAthleteManifest[]> {
    await fs.mkdir(this.baseDir, { recursive: true });
    const entries = await fs.readdir(this.baseDir, { withFileTypes: true });
    const manifests = await Promise.all(
      entries
        .filter((entry) => entry.isDirectory())
        .map(async (entry) => this.readJson<PrivateAthleteManifest>(this.fileFor(entry.name, 'manifest.json'))),
    );
    return manifests.filter((manifest): manifest is PrivateAthleteManifest => manifest != null);
  }

  async loadMetricsHistory(athleteId: string): Promise<DailyMetrics[]> {
    return (await this.readJson<DailyMetrics[]>(this.fileFor(athleteId, 'metrics-history.json'))) ?? [];
  }

  async loadMemoryRecord(athleteId: string): Promise<AthleteMemoryRecord | null> {
    return this.readJson<AthleteMemoryRecord>(this.fileFor(athleteId, 'memory.json'));
  }

  async saveMemoryRecord(athleteId: string, memory: AthleteMemoryRecord): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'memory.json'), memory);
  }

  async saveDailyRefresh(athleteId: string, artifact: AthleteDailyRefreshArtifact): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'daily-refreshes', `${artifact.sourceDate}.json`),
      artifact,
    );
    await this.writeJson(this.fileFor(athleteId, 'daily-refreshes', 'latest.json'), artifact);
  }

  async saveWeeklySynthesis(
    athleteId: string,
    artifact: AthleteWeeklySynthesisArtifact,
  ): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'weekly-syntheses', `${artifact.weekKey}.json`),
      artifact,
    );
    await this.writeJson(this.fileFor(athleteId, 'weekly-syntheses', 'latest.json'), artifact);
  }

  async getLatestDailyRefresh(athleteId: string): Promise<AthleteDailyRefreshArtifact | null> {
    return this.readJson<AthleteDailyRefreshArtifact>(
      this.fileFor(athleteId, 'daily-refreshes', 'latest.json'),
    );
  }

  async getLatestWeeklySynthesis(athleteId: string): Promise<AthleteWeeklySynthesisArtifact | null> {
    return this.readJson<AthleteWeeklySynthesisArtifact>(
      this.fileFor(athleteId, 'weekly-syntheses', 'latest.json'),
    );
  }

  async listDailyRefreshes(
    athleteId: string,
    options?: { startDate?: string; endDate?: string; limit?: number },
  ): Promise<AthleteDailyRefreshArtifact[]> {
    const dir = this.fileFor(athleteId, 'daily-refreshes');
    try {
      const files = (await fs.readdir(dir))
        .filter((file) => file.endsWith('.json') && file !== 'latest.json')
        .sort();
      const loaded = await Promise.all(
        files.map((file) => this.readJson<AthleteDailyRefreshArtifact>(path.join(dir, file))),
      );
      return loaded
        .filter((item): item is AthleteDailyRefreshArtifact => item != null)
        .filter((item) => (options?.startDate ? item.sourceDate >= options.startDate : true))
        .filter((item) => (options?.endDate ? item.sourceDate <= options.endDate : true))
        .slice(options?.limit ? -options.limit : undefined);
    } catch {
      return [];
    }
  }

  // ── Raw and normalized storage (Layer 1 + Layer 2) ──────────

  async saveRawDay(athleteId: string, record: WhoopDailyMetricsRaw): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'raw', `${record.localDate}.json`),
      record,
    );
  }

  async loadRawDay(athleteId: string, date: string): Promise<unknown | null> {
    return this.readJson(this.fileFor(athleteId, 'raw', `${date}.json`));
  }

  async saveNormalizedDay(athleteId: string, record: NormalizedDailyMetrics): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'normalized', `${record.date}.json`),
      record,
    );
  }

  async loadNormalizedDay(athleteId: string, date: string): Promise<unknown | null> {
    return this.readJson(this.fileFor(athleteId, 'normalized', `${date}.json`));
  }

  async loadNormalizedRange(athleteId: string, startDate: string, endDate: string): Promise<unknown[]> {
    const dir = this.fileFor(athleteId, 'normalized');
    try {
      const files = (await fs.readdir(dir))
        .filter((f) => f.endsWith('.json'))
        .map((f) => f.replace('.json', ''))
        .filter((d) => d >= startDate && d <= endDate)
        .sort();
      const results = await Promise.all(
        files.map((d) => this.readJson(path.join(dir, `${d}.json`))),
      );
      return results.filter((r): r is NonNullable<typeof r> => r != null);
    } catch {
      return [];
    }
  }

  private fileFor(athleteId: string, ...parts: string[]) {
    return path.join(this.baseDir, athleteId, ...parts);
  }

  private async readJson<T>(filePath: string): Promise<T | null> {
    try {
      const raw = await fs.readFile(filePath, 'utf8');
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  }

  private async writeJson(filePath: string, value: unknown): Promise<void> {
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  }
}
