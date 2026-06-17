/**
 * Session log ingestion — converts session log payloads into
 * raw records (Layer 1) and normalized summaries (Layer 2).
 *
 * Pure function. No network calls. No interpretation.
 */

import type {
  SessionLogIngestPayload,
  SessionLogRaw,
  NormalizedSessionSummary,
} from '../../contracts/session-log.types';
import { normalizeSessionLog } from '../../contracts/session-log.types';

let _idCounter = 0;
function generateId(date: string, prefix: string): string {
  return `${prefix}_${date}_${Date.now()}_${++_idCounter}`;
}

/** Ingest a session log into a raw record. */
export function ingestSessionLog(
  payload: SessionLogIngestPayload,
): SessionLogRaw {
  const now = new Date().toISOString();
  return {
    id: generateId(payload.date, 'sess_raw'),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId: payload.athleteId,
    date: payload.date,
    payload,
  };
}

/** Ingest + normalize a session log in one step. */
export function ingestAndNormalizeSessionLog(
  payload: SessionLogIngestPayload,
): { raw: SessionLogRaw; normalized: NormalizedSessionSummary } {
  const raw = ingestSessionLog(payload);
  const now = new Date().toISOString();
  const norm = normalizeSessionLog(payload);
  const normalized: NormalizedSessionSummary = {
    id: generateId(payload.date, 'sess_norm'),
    schemaVersion: 1,
    createdAt: now,
    ...norm,
  };
  return { raw, normalized };
}
