import assert from 'node:assert/strict';
import {
  parseJournalNotesPaste,
  type ParsedJournalNotesEntry,
} from '../../packages/shared/src/journal/notes-import';
import { SYNTHETIC_NOTES_PASTE_FIXTURES } from './fixtures/journal-import-synthetic-fixtures';

const PRIVATE_DATA_PATTERN = /\b(aaron|test@example|phone|token|secret|password|apikey|api_key|bearer|jwt)\b/i;
const PUBLIC_SURFACE_KEYS = ['section', 'date', 'itemText', 'canonicalName', 'category', 'eventType', 'amount', 'unit', 'confidence'];

function row(entries: ParsedJournalNotesEntry[], canonical: string, eventType?: string): ParsedJournalNotesEntry {
  const found = entries.find((entry) =>
    entry.canonicalName === canonical && (eventType == null || entry.eventType === eventType),
  );
  assert.ok(found, `expected ${canonical}${eventType ? ` ${eventType}` : ''} row`);
  return found;
}

const mainFixture = SYNTHETIC_NOTES_PASTE_FIXTURES.find((fixture) => fixture.id === 'apple-notes-structure-dose-periods');
assert.ok(mainFixture);
assert.equal(PRIVATE_DATA_PATTERN.test(mainFixture.rawText), false, 'fixture must not contain private-looking data');

const parsed = parseJournalNotesPaste(mainFixture.rawText);
assert.ok(parsed.sections.includes('Peptides'), 'section heading detected');
assert.ok(parsed.sections.includes('Lungs and Sinuses'), 'multi-word section heading detected');

const bpcStart = row(parsed.entries, 'BPC-157', 'start');
assert.equal(bpcStart.date, '2026-05-01');
assert.equal(bpcStart.amount, 100);
assert.equal(bpcStart.unit, 'mcg');
assert.equal(bpcStart.periodStartDate, '2026-05-01');
assert.equal(bpcStart.periodEndDate, '2026-05-08', 'dose-change period ends at next dose change');
assert.equal(bpcStart.needsConfirmation, true, 'sensitive peptide requires confirmation');

const bpcChange = parsed.entries.find((entry) => entry.canonicalName === 'BPC-157' && entry.date === '2026-05-08');
assert.ok(bpcChange);
assert.equal(bpcChange.periodEndDate, '2026-05-15', 'dose-change period ends at break');

const bpcBreak = parsed.entries.find((entry) => entry.canonicalName === 'BPC-157' && entry.eventType === 'break');
assert.ok(bpcBreak, 'break event parsed');

const salbutamol = row(parsed.entries, 'Salbutamol', 'single_use');
assert.equal(salbutamol.amount, 2);
assert.equal(salbutamol.unit, 'puffs');
assert.equal(salbutamol.periodStartDate, null, 'single-use event does not open a period');

const pulmicort = row(parsed.entries, 'Pulmicort', 'dose_change');
assert.equal(pulmicort.needsConfirmation, true, 'brand inhaler term requires confirmation');

const budesonideNasal = row(parsed.entries, 'Budesonide nasal spray', 'dose_change');
assert.equal(budesonideNasal.category, 'nasal_spray');
assert.equal(budesonideNasal.needsConfirmation, true);

const amitriptyline = row(parsed.entries, 'Amitriptyline', 'dose_change');
assert.equal(amitriptyline.needsConfirmation, true, 'misspelling alias requires confirmation');
assert.match(amitriptyline.confirmationReason ?? '', /confirm/i);

const dexamphetamine = row(parsed.entries, 'Dexamphetamine', 'dose_change');
assert.equal(dexamphetamine.needsConfirmation, true, 'misspelling/alias candidate requires confirmation');

const stop = row(parsed.entries, 'Esomeprazole', 'permanent_stop');
assert.ok(stop.parseWarnings.some((warning) => warning.includes('Permanent stop')), 'permanent stop warning recorded');

const creatine = row(parsed.entries, 'Creatine', 'dose_change');
assert.equal(creatine.status, 'ready_to_import', 'low-risk exact supplement row can import after preview');
assert.equal(creatine.needsConfirmation, false);

const mouthTape = row(parsed.entries, 'Mouth tape', 'note');
assert.equal(mouthTape.needsConfirmation, true);

const irrigation = row(parsed.entries, 'Irrigation', 'note');
assert.equal(irrigation.needsConfirmation, false);

const surgery = row(parsed.entries, 'Surgery event', 'surgery_or_injury_event');
assert.equal(surgery.category, 'surgery');

for (const entry of parsed.entries) {
  assert.equal(entry.readinessInput.source, 'notes_import');
  assert.equal(entry.readinessInput.contextOnly, true);
  assert.equal(entry.readinessInput.userConfirmed, false);
  assert.equal(entry.readinessInput.privateRawLine, entry.rawLine);
  assert.equal(entry.readinessInput.userId, null);
  assert.equal(entry.readinessInput.localUserScope, 'device_private');
  assert.equal(entry.readinessInput.canonicalTermCandidate, entry.canonicalName);
  assert.equal(entry.readinessInput.timingFrequency, entry.frequency);
}

const publicProjection = parsed.entries.map((entry) => Object.fromEntries(
  PUBLIC_SURFACE_KEYS.map((key) => [key, entry[key as keyof ParsedJournalNotesEntry]]),
));
assert.equal(JSON.stringify(publicProjection).includes('rawLine'), false, 'public projection does not include rawLine key');
assert.equal(JSON.stringify(publicProjection).includes('privateRawLine'), false, 'public projection does not include privateRawLine key');

const broadFixture = SYNTHETIC_NOTES_PASTE_FIXTURES.find((fixture) => fixture.id === 'apple-notes-broad-category');
assert.ok(broadFixture);
const broadParsed = parseJournalNotesPaste(broadFixture.rawText);
const broadRow = row(broadParsed.entries, 'Peptide category', 'dose_change');
assert.equal(broadRow.status, 'needs_confirmation');
assert.equal(broadRow.needsConfirmation, true);
assert.match(broadRow.confirmationReason ?? '', /Broad category/i);

console.log(`journal notes import parser OK (${parsed.entries.length + broadParsed.entries.length} synthetic rows)`);
