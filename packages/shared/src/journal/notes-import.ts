export type JournalNotesCategory =
  | 'medication'
  | 'peptide'
  | 'supplement'
  | 'nasal_spray'
  | 'inhaler'
  | 'sleep_aid'
  | 'caffeine'
  | 'nutrition_change'
  | 'training_change'
  | 'injury'
  | 'pain'
  | 'illness'
  | 'respiratory_treatment'
  | 'weight_cut_intervention'
  | 'surgery'
  | 'custom';

export type JournalNotesEventType =
  | 'start'
  | 'stop'
  | 'permanent_stop'
  | 'dose_change'
  | 'break'
  | 'single_use'
  | 'note'
  | 'training_note'
  | 'surgery_or_injury_event'
  | 'custom';

export type JournalNotesConfidence = 'high' | 'medium' | 'low';

export type JournalNotesPreviewStatus = 'ready_to_import' | 'needs_confirmation' | 'missing_required_field' | 'skipped';

export interface JournalTermCandidate {
  canonical: string;
  category: JournalNotesCategory;
  aliases: readonly string[];
  needsConfirmation: boolean;
  broadCategory?: boolean;
}

export interface ParsedJournalNotesEntry {
  id: string;
  status: JournalNotesPreviewStatus;
  section: string;
  rawLine: string;
  sourceLineNumber: number;
  date: string | null;
  itemText: string;
  canonicalName: string | null;
  category: JournalNotesCategory;
  eventType: JournalNotesEventType;
  amount: number | null;
  unit: string | null;
  frequency: string | null;
  periodStartDate: string | null;
  periodEndDate: string | null;
  confidence: JournalNotesConfidence;
  parseWarnings: string[];
  needsConfirmation: boolean;
  confirmationReason: string | null;
  skippedReason: string | null;
  readinessInput: JournalNotesReadinessInput;
}

export interface ParseJournalNotesResult {
  sourceKind: 'apple_notes_paste';
  entries: ParsedJournalNotesEntry[];
  skippedLines: Array<{ lineNumber: number; rawLine: string; reason: string }>;
  sections: string[];
  warnings: Array<{ lineNumber: number; rawLine: string; warning: string }>;
}

export interface JournalNotesReadinessInput {
  entryType: 'private_journal_context';
  userId: null;
  localUserScope: 'device_private';
  dateTime: string | null;
  dateRange: { start: string; end: string | null } | null;
  category: JournalNotesCategory;
  canonicalTermCandidate: string | null;
  amount: number | null;
  unit: string | null;
  timingFrequency: string | null;
  eventType: JournalNotesEventType;
  source: 'notes_import';
  confidence: JournalNotesConfidence;
  userConfirmed: false;
  warnings: string[];
  privateRawLine: string;
  contextOnly: true;
}

export const JOURNAL_NOTES_TERM_CANDIDATES: readonly JournalTermCandidate[] = [
  { canonical: 'Peptide category', category: 'peptide', aliases: ['peptide', 'peptides'], needsConfirmation: true, broadCategory: true },
  { canonical: 'HCG', category: 'peptide', aliases: ['hcg', 'human chorionic gonadotropin'], needsConfirmation: true },
  { canonical: 'HGH', category: 'peptide', aliases: ['hgh', 'growth hormone', 'human growth hormone', 'somatropin'], needsConfirmation: true },
  { canonical: 'BPC-157', category: 'peptide', aliases: ['bpc', 'bpc157', 'bpc 157', 'bpc-157'], needsConfirmation: true },
  { canonical: 'TB-500', category: 'peptide', aliases: ['tb500', 'tb 500', 'tb-500', 'thymosin beta-4'], needsConfirmation: true },
  { canonical: 'Salbutamol', category: 'inhaler', aliases: ['salbutamol', 'ventolin', 'albuterol', 'asmol'], needsConfirmation: true },
  { canonical: 'Budesonide/formoterol', category: 'inhaler', aliases: ['budesonide formoterol', 'budesonide/formoterol', 'symbicort'], needsConfirmation: true },
  { canonical: 'Pulmicort', category: 'inhaler', aliases: ['pulmicort'], needsConfirmation: true },
  { canonical: 'Budesonide nasal spray', category: 'nasal_spray', aliases: ['budesonide nasal spray', 'budesonide spray', 'rhinocort'], needsConfirmation: true },
  { canonical: 'Budesonide', category: 'inhaler', aliases: ['budesonide'], needsConfirmation: true },
  { canonical: 'Amitriptyline', category: 'medication', aliases: ['amitriptyline', 'amiltryptiline', 'amitriptaline', 'amitriptiline', 'endep', 'elavil'], needsConfirmation: true },
  { canonical: 'Dexamphetamine', category: 'medication', aliases: ['dexamphetamine', 'dexamfetamine', 'dex', 'dexamphetamine sulfate'], needsConfirmation: true },
  { canonical: 'Esomeprazole', category: 'medication', aliases: ['esomeprazole', 'nexium'], needsConfirmation: true },
  { canonical: 'Gaviscon', category: 'medication', aliases: ['gaviscon'], needsConfirmation: true },
  { canonical: 'Creatine', category: 'supplement', aliases: ['creatine', 'creatine monohydrate'], needsConfirmation: false },
  { canonical: 'Mouth tape', category: 'sleep_aid', aliases: ['mouth tape', 'mouth taping'], needsConfirmation: true },
  { canonical: 'Irrigation', category: 'respiratory_treatment', aliases: ['irrigation', 'nasal irrigation', 'sinus rinse', 'saline rinse'], needsConfirmation: false },
  { canonical: 'Surgery event', category: 'surgery', aliases: ['surgery', 'operation', 'procedure'], needsConfirmation: false },
  { canonical: 'Injury event', category: 'injury', aliases: ['injury', 'injured', 'strain', 'tear'], needsConfirmation: false },
] as const;

const SECTION_CATEGORY_HINTS: ReadonlyArray<{ pattern: RegExp; category: JournalNotesCategory }> = [
  { pattern: /\bpeptides?\b/i, category: 'peptide' },
  { pattern: /\b(lungs?|sinus|sinuses|inhaler|respiratory)\b/i, category: 'respiratory_treatment' },
  { pattern: /\b(drugs?|medications?|medicine)\b/i, category: 'medication' },
  { pattern: /\bsurgery\b/i, category: 'surgery' },
  { pattern: /\b(injury|injuries)\b/i, category: 'injury' },
  { pattern: /\b(supplements?)\b/i, category: 'supplement' },
];

const DATE_PATTERNS: readonly RegExp[] = [
  /\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b/,
  /\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2}|\d{2})\b/,
  /\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(20\d{2})\b/i,
  /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(20\d{2})\b/i,
];

const MONTHS: Record<string, string> = {
  jan: '01',
  feb: '02',
  mar: '03',
  apr: '04',
  may: '05',
  jun: '06',
  jul: '07',
  aug: '08',
  sep: '09',
  sept: '09',
  oct: '10',
  nov: '11',
  dec: '12',
};

function pad2(value: string): string {
  return value.padStart(2, '0');
}

function normalizeYear(value: string): string {
  return value.length === 2 ? `20${value}` : value;
}

function parseDate(raw: string): { date: string | null; rest: string } {
  for (const pattern of DATE_PATTERNS) {
    const match = raw.match(pattern);
    if (!match) continue;
    let iso: string | null = null;
    if (pattern === DATE_PATTERNS[0]) {
      iso = `${match[1]}-${pad2(match[2])}-${pad2(match[3])}`;
    } else if (pattern === DATE_PATTERNS[1]) {
      iso = `${normalizeYear(match[3])}-${pad2(match[2])}-${pad2(match[1])}`;
    } else if (pattern === DATE_PATTERNS[2]) {
      iso = `${match[3]}-${MONTHS[match[2].toLowerCase().slice(0, 4)] ?? MONTHS[match[2].toLowerCase().slice(0, 3)]}-${pad2(match[1])}`;
    } else {
      iso = `${match[3]}-${MONTHS[match[1].toLowerCase().slice(0, 4)] ?? MONTHS[match[1].toLowerCase().slice(0, 3)]}-${pad2(match[2])}`;
    }
    return { date: iso, rest: raw.replace(match[0], '').replace(/^[:\s-]+/, '').trim() };
  }
  return { date: null, rest: raw.trim() };
}

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function findTermCandidate(raw: string): JournalTermCandidate | null {
  const normalized = ` ${normalizeText(raw)} `;
  for (const candidate of JOURNAL_NOTES_TERM_CANDIDATES) {
    const aliases = [candidate.canonical, ...candidate.aliases].map(normalizeText);
    if (aliases.some((alias) => alias && normalized.includes(` ${alias} `))) return candidate;
  }
  return null;
}

function inferSectionCategory(section: string): JournalNotesCategory {
  const match = SECTION_CATEGORY_HINTS.find((hint) => hint.pattern.test(section));
  return match?.category ?? 'custom';
}

function stripListPrefix(raw: string): string {
  return raw.replace(/^[\s>*-]+/, '').replace(/^\d+\.\s+/, '').trim();
}

function looksLikeHeading(line: string): boolean {
  const clean = line.trim();
  if (!clean || clean.length > 80) return false;
  if (parseDate(clean).date) return false;
  if (/[.:;]$/.test(clean)) return true;
  if (/\b(start|stop|break|pause|change|dose|used|single|once)\b/i.test(clean)) return false;
  if (/\d/.test(clean) && !findTermCandidate(clean)) return false;
  return /^[A-Z][A-Za-z0-9 /&,+-]+:?$/.test(clean);
}

function parseDose(raw: string): { amount: number | null; unit: string | null } {
  const match = raw.match(/\b(\d+(?:\.\d+)?)\s*(mcg|micrograms?|mg|g|iu|units?|puffs?|sprays?|ml|tabs?|tablets?|caps?|capsules?)\b/i);
  if (!match) return { amount: null, unit: null };
  return { amount: Number(match[1]), unit: match[2].toLowerCase() };
}

function parseFrequency(raw: string): string | null {
  const match = raw.match(/\b(once daily|twice daily|daily|nightly|morning|evening|weekly|post[- ]training|pre[- ]training|as needed|prn)\b/i);
  return match ? match[1].toLowerCase() : null;
}

function inferEventType(raw: string, hasDose: boolean): JournalNotesEventType {
  const text = raw.toLowerCase();
  if (/\b(single use|single-use|one[- ]off|once only|used once|one time|1x)\b/.test(text)) return 'single_use';
  if (/\b(permanent(?:ly)? stop|stopped permanently|permanent stop|forever off)\b/.test(text)) return 'permanent_stop';
  if (/\b(stop|stopped|ceased|finished|discontinued|ended)\b/.test(text)) return 'stop';
  if (/\b(break|pause|paused|holiday|off for)\b/.test(text)) return 'break';
  if (/\b(surgery|operation|procedure|injury|injured|pain|strain|tear)\b/.test(text)) return 'surgery_or_injury_event';
  if (/\b(started|start|began)\b/.test(text) && hasDose) return 'start';
  if (hasDose || /\b(dose|changed|change|increase|increased|decrease|decreased|from|to)\b/.test(text)) return 'dose_change';
  return 'note';
}

function makeId(lineNumber: number, raw: string): string {
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) hash = ((hash << 5) - hash + raw.charCodeAt(i)) | 0;
  return `notes-${lineNumber}-${Math.abs(hash)}`;
}

function statusFor(entry: Pick<ParsedJournalNotesEntry, 'date' | 'itemText' | 'needsConfirmation'>): JournalNotesPreviewStatus {
  if (!entry.date || !entry.itemText.trim()) return 'missing_required_field';
  if (entry.needsConfirmation) return 'needs_confirmation';
  return 'ready_to_import';
}

function buildWarnings(input: {
  date: string | null;
  candidate: JournalTermCandidate | null;
  broadCategory: boolean;
  eventType: JournalNotesEventType;
  amount: number | null;
  raw: string;
}): string[] {
  const warnings: string[] = [];
  if (!input.date) warnings.push('Missing date.');
  if (!input.candidate) warnings.push('No canonical term match.');
  if (input.broadCategory) warnings.push('Broad category needs exact item confirmation.');
  if (input.candidate?.needsConfirmation) warnings.push('Canonical term requires user confirmation.');
  if ((input.eventType === 'dose_change' || input.eventType === 'start') && input.amount == null) {
    warnings.push('Dose-change row has no parsed amount.');
  }
  if (input.eventType === 'permanent_stop') {
    warnings.push('Permanent stop ends future active periods until a new user-confirmed start.');
  }
  return warnings;
}

function toReadinessInput(entry: Omit<ParsedJournalNotesEntry, 'status' | 'readinessInput'>): JournalNotesReadinessInput {
  return {
    entryType: 'private_journal_context',
    userId: null,
    localUserScope: 'device_private',
    dateTime: entry.date ? `${entry.date}T00:00:00.000Z` : null,
    dateRange: entry.periodStartDate ? { start: entry.periodStartDate, end: entry.periodEndDate } : null,
    category: entry.category,
    canonicalTermCandidate: entry.canonicalName,
    amount: entry.amount,
    unit: entry.unit,
    timingFrequency: entry.frequency,
    eventType: entry.eventType,
    source: 'notes_import',
    confidence: entry.confidence,
    userConfirmed: false,
    warnings: entry.parseWarnings,
    privateRawLine: entry.rawLine,
    contextOnly: true,
  };
}

export function parseJournalNotesPaste(input: string): ParseJournalNotesResult {
  const entries: ParsedJournalNotesEntry[] = [];
  const skippedLines: ParseJournalNotesResult['skippedLines'] = [];
  const warnings: ParseJournalNotesResult['warnings'] = [];
  const sections = new Set<string>();
  let currentSection = 'Unsectioned';
  let currentItemHeading: string | null = null;

  input.split(/\r?\n/).forEach((rawLine, index) => {
    const lineNumber = index + 1;
    const line = stripListPrefix(rawLine);
    if (!line) return;

    if (looksLikeHeading(line)) {
      const heading = line.replace(/:$/, '').trim();
      const candidate = findTermCandidate(heading);
      const headingCategory = inferSectionCategory(heading);
      const isCategoryHeading =
        candidate?.broadCategory === true ||
        ((candidate?.category === 'surgery' || candidate?.category === 'injury') && headingCategory === candidate.category);
      if (candidate && !isCategoryHeading) {
        currentItemHeading = heading;
      } else {
        currentSection = heading;
        currentItemHeading = null;
        sections.add(currentSection);
      }
      return;
    }

    const { date, rest } = parseDate(line);
    const parseSource = rest || line;
    const candidate = findTermCandidate(parseSource) ?? (currentItemHeading ? findTermCandidate(currentItemHeading) : null);
    const sectionCategory = inferSectionCategory(currentSection);
    const dose = parseDose(parseSource);
    const eventType = inferEventType(parseSource, dose.amount != null);
    const itemText = candidate?.canonical ?? currentItemHeading ?? parseSource.split(/[:,-]/)[0]?.trim() ?? 'Journal note';
    const broadCategory = candidate?.broadCategory === true;
    const needsConfirmation = candidate?.needsConfirmation === true || broadCategory || !candidate;
    const confirmationReason = broadCategory
      ? 'Broad category; confirm exact item before saving.'
      : candidate?.needsConfirmation
        ? 'Sensitive term; confirm before saving.'
        : !candidate
          ? 'No canonical term match; confirm or edit before saving.'
          : null;
    const withoutRequired = !date || !itemText.trim();
    const parseWarnings = buildWarnings({
      date,
      candidate: candidate ?? null,
      broadCategory,
      eventType,
      amount: dose.amount,
      raw: parseSource,
    });
    const entryBase: Omit<ParsedJournalNotesEntry, 'status' | 'readinessInput'> = {
      id: makeId(lineNumber, rawLine),
      section: currentSection,
      rawLine,
      sourceLineNumber: lineNumber,
      date,
      itemText,
      canonicalName: candidate?.canonical ?? null,
      category: candidate?.category ?? sectionCategory,
      eventType,
      amount: dose.amount,
      unit: dose.unit,
      frequency: parseFrequency(parseSource),
      periodStartDate: eventType === 'dose_change' || eventType === 'start' ? date : null,
      periodEndDate: null,
      confidence: date && candidate ? (dose.amount != null || eventType !== 'custom' ? 'high' : 'medium') : 'low',
      parseWarnings,
      needsConfirmation,
      confirmationReason,
      skippedReason: withoutRequired ? 'Date and item are required before saving.' : null,
    };
    for (const warning of parseWarnings) warnings.push({ lineNumber, rawLine, warning });
    entries.push({ ...entryBase, readinessInput: toReadinessInput(entryBase), status: statusFor(entryBase) });
    sections.add(currentSection);
  });

  const timelineRows = entries
    .filter((entry) => entry.date)
    .sort((a, b) => (a.canonicalName ?? a.itemText).localeCompare(b.canonicalName ?? b.itemText) || (a.date ?? '').localeCompare(b.date ?? ''));
  const periodRows = timelineRows.filter((entry) => entry.periodStartDate && (entry.eventType === 'dose_change' || entry.eventType === 'start'));
  for (const entry of periodRows) {
    const next = timelineRows.find((candidate) =>
      candidate !== entry &&
      (candidate.canonicalName ?? candidate.itemText) === (entry.canonicalName ?? entry.itemText) &&
      (candidate.date ?? '') > (entry.date ?? '') &&
      (candidate.eventType === 'dose_change' || candidate.eventType === 'start' || candidate.eventType === 'stop' || candidate.eventType === 'break' || candidate.eventType === 'permanent_stop'),
    );
    entry.periodEndDate = next?.date ?? null;
    entry.readinessInput.dateRange = { start: entry.periodStartDate!, end: entry.periodEndDate };
  }

  return {
    sourceKind: 'apple_notes_paste',
    entries,
    skippedLines,
    sections: [...sections],
    warnings,
  };
}
