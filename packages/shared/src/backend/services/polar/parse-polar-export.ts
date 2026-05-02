/**
 * Polar export parser — historical training-session importer.
 *
 * Polar Flow's "Export account data" produces a directory of CSV +
 * (sometimes) TCX files, one per training session. There is no single
 * unified all-sessions CSV; users typically paste a single session
 * file or a concatenated series of session CSVs.
 *
 * Goals of this module:
 *   - Detect the input format (polar-csv | polar-tcx | unknown).
 *   - Parse the supported shapes into a normalised PolarSession[].
 *   - Never crash on unknown content; surface diagnostics instead.
 *   - Stamp every session with `source: 'polar_export'` so downstream
 *     ingest paths can attribute provenance correctly.
 *
 * NOT supported this turn:
 *   - .FIT files (binary; would need a FIT decoder dependency).
 *   - Polar account-level "Activity summary" daily CSVs (different
 *     shape from training-session files; can be added later).
 *   - HRV/RR per-session sample arrays (parser stops at session-level
 *     summary fields).
 *
 * Pure module: no I/O, no network, no async.
 */

export type PolarExportFormat = 'polar-csv' | 'polar-tcx' | 'unknown';

export interface PolarSession {
  source: 'polar_export';
  format: PolarExportFormat;
  /** ISO 8601 if parsable. */
  startTime: string | null;
  endTime: string | null;
  durationSeconds: number | null;
  sport: string | null;
  calories: number | null;
  distanceKm: number | null;
  hrAvg: number | null;
  hrMax: number | null;
  cadenceAvg: number | null;
  speedAvgKmh: number | null;
  powerAvgW: number | null;
  rawHeaders: string[];
}

export interface ParsePolarExportResult {
  ok: boolean;
  format: PolarExportFormat;
  sessions: PolarSession[];
  diagnostics: string[];
}

const POLAR_CSV_HEADER_HINTS = [
  'Sport', 'Date', 'Start time', 'Duration', 'Total distance',
  'Average heart rate', 'Maximum heart rate', 'Calories',
];

function detectFormat(text: string): PolarExportFormat {
  const head = text.slice(0, 4096);
  if (/<TrainingCenterDatabase[\s>]/i.test(head)) return 'polar-tcx';
  // Polar training-session CSV headers usually include "Sport" and
  // either "Date" or "Start time" within the first non-empty line.
  const firstLine = head.split(/\r?\n/).find((l) => l.trim().length > 0) ?? '';
  if (/Sport/.test(firstLine) && /(Date|Start time)/.test(firstLine)) return 'polar-csv';
  if (/^Name,/i.test(firstLine) && /Polar/.test(head)) return 'polar-csv';
  return 'unknown';
}

function parseDuration(value: string): number | null {
  if (!value) return null;
  // Accept "HH:MM:SS", "MM:SS", "PT1H02M03S", or seconds as integer.
  const trimmed = value.trim();
  if (/^\d+(\.\d+)?$/.test(trimmed)) return Math.round(parseFloat(trimmed));
  if (/^\d+:\d{2}(:\d{2})?$/.test(trimmed)) {
    const parts = trimmed.split(':').map((n) => parseInt(n, 10));
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
  }
  const iso = trimmed.match(/^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$/i);
  if (iso) {
    const h = iso[1] ? parseInt(iso[1], 10) : 0;
    const m = iso[2] ? parseInt(iso[2], 10) : 0;
    const s = iso[3] ? Math.round(parseFloat(iso[3])) : 0;
    return h * 3600 + m * 60 + s;
  }
  return null;
}

function parseNumber(value: string): number | null {
  if (value == null) return null;
  const t = String(value).trim().replace(',', '.');
  if (t.length === 0) return null;
  const n = parseFloat(t);
  return Number.isFinite(n) ? n : null;
}

function parseDate(date: string, time: string | null): string | null {
  if (!date) return null;
  // Polar dates: "DD-MM-YYYY" or "YYYY-MM-DD".
  const dmY = date.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  const ymd = date.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  let isoDate: string | null = null;
  if (ymd) isoDate = `${ymd[1]}-${ymd[2]}-${ymd[3]}`;
  else if (dmY) isoDate = `${dmY[3]}-${dmY[2]}-${dmY[1]}`;
  if (!isoDate) return null;
  const t = time && /^\d{2}:\d{2}(:\d{2})?$/.test(time.trim())
    ? (time.trim().length === 5 ? `${time.trim()}:00` : time.trim())
    : '00:00:00';
  return `${isoDate}T${t}`;
}

function splitCsvLine(line: string): string[] {
  // Minimal CSV splitter: handles quoted fields with embedded commas
  // but does not need full RFC 4180 compliance for Polar shapes.
  const out: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; }
      else inQuotes = !inQuotes;
    } else if (ch === ',' && !inQuotes) {
      out.push(cur); cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map((c) => c.trim());
}

function parsePolarCsv(text: string): { sessions: PolarSession[]; diagnostics: string[] } {
  const diagnostics: string[] = [];
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) {
    diagnostics.push('CSV has fewer than 2 non-empty lines.');
    return { sessions: [], diagnostics };
  }
  const headers = splitCsvLine(lines[0]);
  const idx = (name: string) => headers.findIndex((h) => h.toLowerCase() === name.toLowerCase());

  const iSport = idx('Sport');
  const iDate = idx('Date');
  const iStart = idx('Start time');
  const iDuration = idx('Duration');
  const iDistance = idx('Total distance (km)') !== -1 ? idx('Total distance (km)') : idx('Distance (km)');
  const iHrAvg = idx('Average heart rate (bpm)') !== -1 ? idx('Average heart rate (bpm)') : idx('Average heart rate');
  const iHrMax = idx('Maximum heart rate (bpm)') !== -1 ? idx('Maximum heart rate (bpm)') : idx('Maximum heart rate');
  const iCalories = idx('Calories') !== -1 ? idx('Calories') : idx('Energy expenditure (kcal)');
  const iCadence = idx('Average cadence (rpm)') !== -1 ? idx('Average cadence (rpm)') : idx('Average cadence');
  const iSpeed = idx('Average speed (km/h)') !== -1 ? idx('Average speed (km/h)') : idx('Average speed');
  const iPower = idx('Average power (W)') !== -1 ? idx('Average power (W)') : idx('Average power');

  if (iSport === -1 && iDate === -1 && iStart === -1) {
    diagnostics.push('No Polar-shaped session columns detected (expected Sport / Date / Start time).');
    return { sessions: [], diagnostics };
  }

  const sessions: PolarSession[] = [];
  for (let li = 1; li < lines.length; li++) {
    const cells = splitCsvLine(lines[li]);
    if (cells.length === 0 || (cells.length === 1 && cells[0].length === 0)) continue;
    const sport = iSport >= 0 ? (cells[iSport] || null) : null;
    const dateRaw = iDate >= 0 ? cells[iDate] : '';
    const timeRaw = iStart >= 0 ? cells[iStart] : '';
    const startTime = parseDate(dateRaw, timeRaw);
    const durationSeconds = iDuration >= 0 ? parseDuration(cells[iDuration]) : null;
    let endTime: string | null = null;
    if (startTime && durationSeconds != null) {
      const ms = new Date(startTime).getTime() + durationSeconds * 1000;
      if (Number.isFinite(ms)) endTime = new Date(ms).toISOString();
    }
    sessions.push({
      source: 'polar_export',
      format: 'polar-csv',
      startTime,
      endTime,
      durationSeconds,
      sport,
      calories: iCalories >= 0 ? parseNumber(cells[iCalories]) : null,
      distanceKm: iDistance >= 0 ? parseNumber(cells[iDistance]) : null,
      hrAvg: iHrAvg >= 0 ? parseNumber(cells[iHrAvg]) : null,
      hrMax: iHrMax >= 0 ? parseNumber(cells[iHrMax]) : null,
      cadenceAvg: iCadence >= 0 ? parseNumber(cells[iCadence]) : null,
      speedAvgKmh: iSpeed >= 0 ? parseNumber(cells[iSpeed]) : null,
      powerAvgW: iPower >= 0 ? parseNumber(cells[iPower]) : null,
      rawHeaders: headers,
    });
  }
  if (sessions.length === 0) {
    diagnostics.push('CSV header parsed but no data rows produced sessions.');
  }
  return { sessions, diagnostics };
}

function parsePolarTcx(text: string): { sessions: PolarSession[]; diagnostics: string[] } {
  const diagnostics: string[] = [];
  const sessions: PolarSession[] = [];

  // Cheap regex-driven extraction. Avoids pulling an XML parser in.
  const activityRegex = /<Activity\b[^>]*Sport="([^"]+)"[\s\S]*?<\/Activity>/g;
  const idMatch = (chunk: string) => {
    const m = chunk.match(/<Id>([^<]+)<\/Id>/);
    return m ? m[1].trim() : null;
  };
  const totalTime = (chunk: string) => {
    const m = chunk.match(/<TotalTimeSeconds>([\d.]+)<\/TotalTimeSeconds>/);
    return m ? Math.round(parseFloat(m[1])) : null;
  };
  const distanceMeters = (chunk: string) => {
    const m = chunk.match(/<DistanceMeters>([\d.]+)<\/DistanceMeters>/);
    return m ? parseFloat(m[1]) : null;
  };
  const calories = (chunk: string) => {
    const m = chunk.match(/<Calories>([\d.]+)<\/Calories>/);
    return m ? parseFloat(m[1]) : null;
  };
  const avgHr = (chunk: string) => {
    const m = chunk.match(/<AverageHeartRateBpm>\s*<Value>([\d.]+)<\/Value>/);
    return m ? parseFloat(m[1]) : null;
  };
  const maxHr = (chunk: string) => {
    const m = chunk.match(/<MaximumHeartRateBpm>\s*<Value>([\d.]+)<\/Value>/);
    return m ? parseFloat(m[1]) : null;
  };

  let m: RegExpExecArray | null;
  while ((m = activityRegex.exec(text)) !== null) {
    const fullChunk = m[0];
    const sport = m[1];
    const id = idMatch(fullChunk);
    const tt = totalTime(fullChunk);
    const startTime = id ? id : null;
    let endTime: string | null = null;
    if (startTime && tt != null) {
      const ms = new Date(startTime).getTime() + tt * 1000;
      if (Number.isFinite(ms)) endTime = new Date(ms).toISOString();
    }
    const dm = distanceMeters(fullChunk);
    sessions.push({
      source: 'polar_export',
      format: 'polar-tcx',
      startTime,
      endTime,
      durationSeconds: tt,
      sport,
      calories: calories(fullChunk),
      distanceKm: dm != null ? Number((dm / 1000).toFixed(2)) : null,
      hrAvg: avgHr(fullChunk),
      hrMax: maxHr(fullChunk),
      cadenceAvg: null,
      speedAvgKmh: null,
      powerAvgW: null,
      rawHeaders: ['tcx'],
    });
  }
  if (sessions.length === 0) diagnostics.push('TCX parsed but no <Activity> elements yielded sessions.');
  return { sessions, diagnostics };
}

export function parsePolarExport(text: string, fileName?: string): ParsePolarExportResult {
  const diagnostics: string[] = [];
  if (!text || typeof text !== 'string' || text.length === 0) {
    return { ok: false, format: 'unknown', sessions: [], diagnostics: ['Empty input.'] };
  }
  // Safety cap: refuse > 8MB to avoid mobile UITextView OOM on paste
  // path. Real exports are far smaller (per-session files).
  if (text.length > 8 * 1024 * 1024) {
    return { ok: false, format: 'unknown', sessions: [], diagnostics: ['Input over 8MB. Split into per-session files.'] };
  }

  const format = detectFormat(text);
  if (format === 'unknown') {
    if (fileName && /\.fit$/i.test(fileName)) {
      diagnostics.push('FIT file detected — FIT decoding is not yet supported. Export the same session as TCX or CSV from Polar Flow.');
    } else {
      diagnostics.push('Could not identify Polar export shape (expected CSV with Sport/Date/Start-time columns or TCX TrainingCenterDatabase).');
    }
    return { ok: false, format, sessions: [], diagnostics };
  }

  const { sessions, diagnostics: parserDiags } = format === 'polar-tcx'
    ? parsePolarTcx(text)
    : parsePolarCsv(text);
  diagnostics.push(...parserDiags);

  return {
    ok: sessions.length > 0,
    format,
    sessions,
    diagnostics,
  };
}
