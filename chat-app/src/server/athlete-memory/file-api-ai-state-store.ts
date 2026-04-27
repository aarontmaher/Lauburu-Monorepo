import { promises as fs } from 'fs';
import path from 'path';
import type { AthleteMemoryRecord, AthletePhysiologyBaseline } from '@lauburu/shared';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';
import type { DailyRefreshArtifact, WeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/contracts/refresh-artifacts.types';
import type { SourceHealthStatus } from '../../../../packages/shared/src/backend/contracts/freshness.types';
import type { WhoopDailyMetricsRaw } from '../../../../packages/shared/src/backend/contracts/whoop-raw.types';
import type { AthleteStateStore } from '../../../../packages/shared/src/backend/services/orchestrate/read-athlete-state';
import type { HIITWorkoutRecord } from '../../../../packages/shared/src/types/hiit-workout';
import type {
  BacklogAnalysisStatusRecord,
  BacklogInitialSummary,
  BacklogTrendCandidate,
} from '../../../../packages/shared/src/backend/contracts/backlog-analysis.types';

export class FileApiAiStateStore implements AthleteStateStore {
  constructor(private readonly baseDir: string) {}

  async getLatestDailyRefresh(athleteId: string): Promise<DailyRefreshArtifact | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'daily_refresh_artifact', 'latest.json'));
  }

  async getLatestWeeklySynthesis(athleteId: string): Promise<WeeklySynthesisArtifact | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'weekly_synthesis_artifact', 'latest.json'));
  }

  async getStableMemory(athleteId: string): Promise<AthleteMemoryRecord | null> {
    return this.readJson(this.fileFor(athleteId, 'memory.json'));
  }

  async getNormalizedDay(athleteId: string, date: string): Promise<NormalizedDailyMetrics | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'normalized_daily_metrics', `${date}.json`));
  }

  async getNormalizedRecent(athleteId: string, days: number): Promise<NormalizedDailyMetrics[]> {
    const dir = this.fileFor(athleteId, 'api-ai', 'normalized_daily_metrics');
    try {
      const files = (await fs.readdir(dir))
        .filter((file) => file.endsWith('.json') && file !== 'latest.json')
        .sort()
        .slice(-days);
      const records = await Promise.all(
        files.map((file) => this.readJson<NormalizedDailyMetrics>(path.join(dir, file))),
      );
      return records.filter((record): record is NormalizedDailyMetrics => record != null);
    } catch {
      return [];
    }
  }

  async getRawDay(athleteId: string, date: string): Promise<WhoopDailyMetricsRaw | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'whoop_daily_metrics_raw', `${date}.json`));
  }

  async getSourceHealth(athleteId: string, provider: string): Promise<SourceHealthStatus | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'source_health_status', `${provider}.json`));
  }

  // ── Write methods (used by internal pipeline routes) ─────────

  async saveRawDay(athleteId: string, record: WhoopDailyMetricsRaw): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'whoop_daily_metrics_raw', `${record.localDate}.json`), record);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'whoop_daily_metrics_raw', 'latest.json'), record);
  }

  async saveNormalizedDay(athleteId: string, record: NormalizedDailyMetrics): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'normalized_daily_metrics', `${record.date}.json`), record);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'normalized_daily_metrics', 'latest.json'), record);
  }

  async saveDailyRefresh(athleteId: string, artifact: DailyRefreshArtifact): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'daily_refresh_artifact', `${artifact.sourceDate}.json`), artifact);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'daily_refresh_artifact', 'latest.json'), artifact);
  }

  async saveStableMemory(athleteId: string, memory: AthleteMemoryRecord): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'memory.json'), memory);
  }

  async saveWeeklySynthesis(athleteId: string, artifact: WeeklySynthesisArtifact): Promise<void> {
    const weekKey = `${artifact.weekStart}__${artifact.weekEnd}`;
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'weekly_synthesis_artifact', `${weekKey}.json`), artifact);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'weekly_synthesis_artifact', 'latest.json'), artifact);
  }

  async saveSourceHealth(athleteId: string, provider: string, status: SourceHealthStatus): Promise<void> {
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'source_health_status', `${provider}.json`), status);
  }

  async listDailyRefreshes(athleteId: string, opts?: { startDate?: string; endDate?: string }): Promise<DailyRefreshArtifact[]> {
    const dir = this.fileFor(athleteId, 'api-ai', 'daily_refresh_artifact');
    try {
      const files = (await fs.readdir(dir))
        .filter((f) => f.endsWith('.json') && f !== 'latest.json')
        .sort();
      const loaded = await Promise.all(files.map((f) => this.readJson<DailyRefreshArtifact>(path.join(dir, f))));
      return loaded
        .filter((a): a is DailyRefreshArtifact => a != null)
        .filter((a) => (!opts?.startDate || a.sourceDate >= opts.startDate))
        .filter((a) => (!opts?.endDate || a.sourceDate <= opts.endDate));
    } catch {
      return [];
    }
  }

  async loadNormalizedRange(athleteId: string, startDate: string, endDate: string): Promise<NormalizedDailyMetrics[]> {
    const dir = this.fileFor(athleteId, 'api-ai', 'normalized_daily_metrics');
    try {
      const files = (await fs.readdir(dir))
        .filter((f) => f.endsWith('.json') && f !== 'latest.json')
        .map((f) => f.replace('.json', ''))
        .filter((d) => d >= startDate && d <= endDate)
        .sort();
      const results = await Promise.all(files.map((d) => this.readJson<NormalizedDailyMetrics>(path.join(dir, `${d}.json`))));
      return results.filter((r): r is NormalizedDailyMetrics => r != null);
    } catch {
      return [];
    }
  }

  // ── Raw session storage ─────────────────────────────────────

  async saveRawSession(athleteId: string, record: Record<string, unknown>): Promise<void> {
    const sessionId = (record as any).payload?.sessionId ?? (record as any).id;
    const date = (record as any).payload?.date ?? (record as any).date;
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'session_raw', `${sessionId}.json`), record);
    if (date) {
      await this.writeJson(this.fileFor(athleteId, 'api-ai', 'session_raw', `${date}_latest.json`), record);
    }
  }

  async getRawSession(athleteId: string, sessionId: string): Promise<Record<string, unknown> | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'session_raw', `${sessionId}.json`));
  }

  // ── Session log methods ─────────────────────────────────────

  async saveSessionSummary(athleteId: string, summary: Record<string, unknown>): Promise<void> {
    const sessionId = summary.sessionId as string;
    const date = summary.date as string;
    // Store individual session
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'session_summaries', `${sessionId}.json`), summary);
    // Update the session index (append to a JSON array file)
    const indexPath = this.fileFor(athleteId, 'api-ai', 'session_summaries', '_index.json');
    let index: Array<{ sessionId: string; date: string; templateId: string | null }> = [];
    try {
      const existing = await this.readJson<typeof index>(indexPath);
      if (Array.isArray(existing)) index = existing;
    } catch { /* empty index */ }
    // Dedupe and prepend
    index = index.filter((e) => e.sessionId !== sessionId);
    index.unshift({ sessionId, date, templateId: (summary.templateId as string | null) ?? null });
    // Keep last 30
    index = index.slice(0, 30);
    await this.writeJson(indexPath, index);
  }

  async getRecentSessionSummaries(athleteId: string, limit: number): Promise<Record<string, unknown>[]> {
    const indexPath = this.fileFor(athleteId, 'api-ai', 'session_summaries', '_index.json');
    let index: Array<{ sessionId: string; date: string; templateId: string | null }> = [];
    try {
      const existing = await this.readJson<typeof index>(indexPath);
      if (Array.isArray(existing)) index = existing;
    } catch { return []; }
    const results: Record<string, unknown>[] = [];
    for (const entry of index.slice(0, limit)) {
      const s = await this.readJson<Record<string, unknown>>(
        this.fileFor(athleteId, 'api-ai', 'session_summaries', `${entry.sessionId}.json`),
      );
      if (s) results.push(s);
    }
    return results;
  }

  async getSessionsForTemplate(athleteId: string, templateId: string, limit: number): Promise<Record<string, unknown>[]> {
    const indexPath = this.fileFor(athleteId, 'api-ai', 'session_summaries', '_index.json');
    let index: Array<{ sessionId: string; date: string; templateId: string | null }> = [];
    try {
      const existing = await this.readJson<typeof index>(indexPath);
      if (Array.isArray(existing)) index = existing;
    } catch { return []; }
    const matching = index.filter((e) => e.templateId === templateId).slice(0, limit);
    const results: Record<string, unknown>[] = [];
    for (const entry of matching) {
      const s = await this.readJson<Record<string, unknown>>(
        this.fileFor(athleteId, 'api-ai', 'session_summaries', `${entry.sessionId}.json`),
      );
      if (s) results.push(s);
    }
    return results;
  }

  // ── Raw nutrition methods ────────────────────────────────────

  async saveRawNutrition(athleteId: string, record: Record<string, unknown>): Promise<void> {
    const date = record.date as string;
    const source = record.source as string;
    const id = record.id as string;
    // Store by date (latest per date) and by id (audit trail)
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'nutrition_raw', `${date}_${source}.json`), record);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'nutrition_raw', `${id}.json`), record);
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'nutrition_raw', `${date}_latest.json`), record);
  }

  async getRawNutrition(athleteId: string, date: string): Promise<Record<string, unknown> | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'nutrition_raw', `${date}_latest.json`));
  }

  async getRawNutritionBySource(athleteId: string, date: string, source: string): Promise<Record<string, unknown> | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'nutrition_raw', `${date}_${source}.json`));
  }

  // ── Nutrition evidence methods ──────────────────────────────

  async saveNutritionEvidence(athleteId: string, evidence: Record<string, unknown>): Promise<void> {
    const id = evidence.id as string ?? evidence.proposalId as string;
    await this.writeJson(this.fileFor(athleteId, 'api-ai', 'nutrition_evidence', `${id}.json`), evidence);
  }

  async getNutritionEvidence(athleteId: string, id: string): Promise<Record<string, unknown> | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'nutrition_evidence', `${id}.json`));
  }

  // ── Seeded supplementary state (read-only) ───────────────────

  async getSeededState(athleteId: string): Promise<Record<string, unknown>> {
    const files = [
      'baseline_profile',
      'baseline_thresholds',
      'recurring_patterns_candidates',
      'current_block_summary',
      'manifest',
    ];
    const result: Record<string, unknown> = {};
    for (const name of files) {
      result[name] = await this.readJson(this.fileFor(athleteId, 'api-ai', `${name}.json`));
    }
    return result;
  }

  // ── HIIT session enumeration (for backlog analysis) ──────────

  async listHiitSessions(
    athleteId: string,
    opts?: { startDate?: string; endDate?: string },
  ): Promise<HIITWorkoutRecord[]> {
    const indexPath = this.fileFor(athleteId, 'api-ai', 'session_summaries', '_index.json');
    let index: Array<{ sessionId: string; date: string; templateId: string | null }> = [];
    try {
      const existing = await this.readJson<typeof index>(indexPath);
      if (Array.isArray(existing)) index = existing;
    } catch { return []; }
    const filtered = index.filter((e) => {
      if (opts?.startDate && e.date < opts.startDate) return false;
      if (opts?.endDate && e.date > opts.endDate) return false;
      return true;
    });
    const sessions: HIITWorkoutRecord[] = [];
    for (const entry of filtered) {
      const s = await this.readJson<any>(
        this.fileFor(athleteId, 'api-ai', 'session_summaries', `${entry.sessionId}.json`),
      );
      if (s) sessions.push(s as HIITWorkoutRecord);
    }
    return sessions;
  }

  // ── Baseline access (for backlog analysis) ────────────────────

  async getBaseline(athleteId: string): Promise<AthletePhysiologyBaseline | null> {
    // Prefer stable-memory baseline; fall back to seed baseline profile.
    const stable = await this.getStableMemory(athleteId);
    if (stable?.physiologyBaseline) return stable.physiologyBaseline;
    const seed = await this.readJson<AthletePhysiologyBaseline>(
      this.fileFor(athleteId, 'api-ai', 'baseline_profile.json'),
    );
    return seed;
  }

  // ── Backlog analysis persistence ──────────────────────────────

  async saveBacklogStatus(
    athleteId: string,
    record: BacklogAnalysisStatusRecord,
  ): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'status.json'),
      record,
    );
  }

  async getBacklogStatus(athleteId: string): Promise<BacklogAnalysisStatusRecord | null> {
    return this.readJson(this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'status.json'));
  }

  async saveBacklogSummary(
    athleteId: string,
    summary: BacklogInitialSummary,
  ): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', `summary_${summary.id}.json`),
      summary,
    );
    await this.writeJson(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'latest_summary.json'),
      summary,
    );
  }

  async getLatestBacklogSummary(athleteId: string): Promise<BacklogInitialSummary | null> {
    return this.readJson(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'latest_summary.json'),
    );
  }

  async saveBacklogTrendCandidates(
    athleteId: string,
    trends: BacklogTrendCandidate[],
  ): Promise<void> {
    await this.writeJson(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'trend_candidates.json'),
      trends,
    );
  }

  async getBacklogTrendCandidates(athleteId: string): Promise<BacklogTrendCandidate[]> {
    const loaded = await this.readJson<BacklogTrendCandidate[]>(
      this.fileFor(athleteId, 'api-ai', 'backlog_analysis', 'trend_candidates.json'),
    );
    return Array.isArray(loaded) ? loaded : [];
  }

  // ── Internal helpers ────────────────────────────────────────

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
