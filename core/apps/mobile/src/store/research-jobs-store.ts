/**
 * Research jobs store — local cache of pending Deep Research
 * offload jobs and completed cached artifacts.
 *
 * MVP wiring:
 *   - hydrate() reads secureStorage; first run seeds from
 *     DEFAULT_RESEARCH_JOBS so the AdminDev surface has at least
 *     one example job to render.
 *   - createJob(input) — produces a new draft job (validates +
 *     refuses secret-shaped input; deduplicates by reuseHash —
 *     if a completed job with the same hash and a valid (non-stale)
 *     artifact exists, the new job goes straight to status 'reused'
 *     pointing at the existing artifact).
 *   - markSubmitted / markCompleted / cancel — dispatch through
 *     @lauburu/shared transitions.
 *   - exportPrompt(id) returns the paste-into-ChatGPT shorthand.
 *   - refreshArtifactStatuses() runs the freshness sweep.
 */
import { create } from 'zustand';
import {
  cancelJob,
  completeResearch,
  computeResearchReuseHash,
  exportResearchPrompt,
  makeResearchJob,
  markSubmitted,
  refreshArtifactStatus,
  reuseFromExisting,
  supersedeJob,
  type ResearchJob,
  type ResearchJobInput,
  type ResearchTriggerType,
} from '@lauburu/shared';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_research_jobs_v1';

const DEFAULT_RESEARCH_JOBS: readonly ResearchJob[] = [
  {
    id: 'research-readiness-anomaly-2026-05-09',
    triggerType: 'readiness_pattern',
    topic: 'Multi-day readiness drop — recovery vs travel correlation',
    prompt:
      'Summarise published findings on multi-day recovery-score drops in athletes after long-haul travel within 72 hours. Associations only; no clinical recommendations. Cite review papers and meta-analyses.',
    scopeKeys: ['readiness', 'travel', 'recovery_score', '72h'],
    reuseHash: computeResearchReuseHash({
      triggerType: 'readiness_pattern',
      topic: 'Multi-day readiness drop — recovery vs travel correlation',
      scopeKeys: ['readiness', 'travel', 'recovery_score', '72h'],
    }),
    status: 'draft',
    artifactStatus: null,
    result: null,
    citations: [],
    createdAt: '2026-05-09T07:30:00Z',
    submittedAt: null,
    completedAt: null,
    freshnessWindowDays: 30,
    staleAfter: null,
    supersededBy: null,
    reuseNote: null,
  },
];

interface ResearchJobsPersistedBlob {
  jobs: ResearchJob[];
}

interface ResearchJobsState {
  jobs: ResearchJob[];
  hydrated: boolean;
  hydrate: () => Promise<void>;
  refreshArtifactStatuses: () => Promise<void>;
  createJob: (input: ResearchJobInput) => Promise<{ ok: boolean; reason: string; jobId: string | null; reused: boolean }>;
  markSubmitted: (id: string) => Promise<{ ok: boolean; reason: string }>;
  markCompleted: (id: string, result: string, citations?: readonly string[]) => Promise<{ ok: boolean; reason: string }>;
  cancel: (id: string, reason?: string | null) => Promise<{ ok: boolean; reason: string }>;
  exportPrompt: (id: string) => string | null;
  byId: (id: string) => ResearchJob | null;
  pendingCount: () => number;
  /** Find an existing completed (and not-stale) artifact for the same reuseHash. */
  findReusableByHash: (reuseHash: string, options?: { now?: () => Date }) => ResearchJob | null;
}

function persist(state: { jobs: ResearchJob[] }): Promise<void> {
  return writeStoredJson(KEY, { jobs: state.jobs } as ResearchJobsPersistedBlob);
}

export const useResearchJobsStore = create<ResearchJobsState>((set, get) => ({
  jobs: [],
  hydrated: false,
  hydrate: async () => {
    try {
      const stored = await readStoredJson<Partial<ResearchJobsPersistedBlob>>(KEY);
      if (stored && Array.isArray(stored.jobs) && stored.jobs.length > 0) {
        set({ jobs: stored.jobs, hydrated: true });
        return;
      }
      const seeded = DEFAULT_RESEARCH_JOBS.map((j) => ({ ...j, scopeKeys: [...j.scopeKeys], citations: [...j.citations] }));
      try { await writeStoredJson(KEY, { jobs: seeded }); } catch { /* non-fatal */ }
      set({ jobs: seeded, hydrated: true });
    } catch {
      set({
        jobs: DEFAULT_RESEARCH_JOBS.map((j) => ({ ...j, scopeKeys: [...j.scopeKeys], citations: [...j.citations] })),
        hydrated: true,
      });
    }
  },
  refreshArtifactStatuses: async () => {
    let changed = false;
    const next = get().jobs.map((job) => {
      const updated = refreshArtifactStatus(job);
      if (updated !== job) changed = true;
      return updated;
    });
    if (!changed) return;
    set({ jobs: next });
    try { await persist({ jobs: next }); } catch { /* non-fatal */ }
  },
  createJob: async (input) => {
    let draft: ResearchJob;
    try { draft = makeResearchJob(input); }
    catch (err) { return { ok: false, reason: err instanceof Error ? err.message : 'invalid input', jobId: null, reused: false }; }
    const reusable = get().findReusableByHash(draft.reuseHash);
    if (reusable) {
      const reused = reuseFromExisting(draft, reusable);
      if (reused.ok) {
        const jobs = [...get().jobs, reused.next];
        set({ jobs });
        try { await persist({ jobs }); } catch { /* non-fatal */ }
        return { ok: true, reason: 'reused existing artifact', jobId: reused.next.id, reused: true };
      }
    }
    const jobs = [...get().jobs, draft];
    set({ jobs });
    try { await persist({ jobs }); } catch { /* non-fatal */ }
    return { ok: true, reason: 'draft created', jobId: draft.id, reused: false };
  },
  markSubmitted: async (id) => {
    const job = get().byId(id);
    if (!job) return { ok: false, reason: 'job not found' };
    const result = markSubmitted(job);
    if (!result.ok) return { ok: false, reason: result.reason };
    const jobs = get().jobs.map((j) => (j.id === id ? result.next : j));
    set({ jobs });
    try { await persist({ jobs }); } catch { /* non-fatal */ }
    return { ok: true, reason: 'submitted' };
  },
  markCompleted: async (id, result, citations) => {
    const job = get().byId(id);
    if (!job) return { ok: false, reason: 'job not found' };
    const completed = completeResearch(job, { result, citations });
    if (!completed.ok) return { ok: false, reason: completed.reason };
    // Mark older jobs with the same reuseHash as superseded.
    const jobs = get().jobs.map((j) => {
      if (j.id === id) return completed.next;
      if (j.reuseHash === completed.next.reuseHash && j.status === 'completed' && j.id !== completed.next.id) {
        const sup = supersedeJob(j, completed.next);
        return sup.ok ? sup.older : j;
      }
      return j;
    });
    set({ jobs });
    try { await persist({ jobs }); } catch { /* non-fatal */ }
    return { ok: true, reason: 'completed' };
  },
  cancel: async (id, reason) => {
    const job = get().byId(id);
    if (!job) return { ok: false, reason: 'job not found' };
    const result = cancelJob(job, { reason });
    if (!result.ok) return { ok: false, reason: result.reason };
    const jobs = get().jobs.map((j) => (j.id === id ? result.next : j));
    set({ jobs });
    try { await persist({ jobs }); } catch { /* non-fatal */ }
    return { ok: true, reason: 'cancelled' };
  },
  exportPrompt: (id) => {
    const job = get().byId(id);
    return job ? exportResearchPrompt(job) : null;
  },
  byId: (id) => get().jobs.find((j) => j.id === id) ?? null,
  pendingCount: () => get().jobs.filter((j) => j.status === 'draft' || j.status === 'submitted').length,
  findReusableByHash: (reuseHash, options) => {
    const now = options?.now ?? (() => new Date());
    const completed = get().jobs.filter((j) => j.reuseHash === reuseHash && j.status === 'completed' && !j.supersededBy);
    if (completed.length === 0) return null;
    // Pick the freshest valid artifact, fall back to the freshest stale one.
    const sorted = completed
      .map((j) => refreshArtifactStatus(j, { now }))
      .sort((a, b) => (b.completedAt ?? '').localeCompare(a.completedAt ?? ''));
    return sorted.find((j) => j.artifactStatus === 'valid') ?? sorted[0] ?? null;
  },
}));
