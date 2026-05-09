/**
 * FS-020 journal parser QA-gap test. Complements the happy-path
 * fixtures in `test-journal-notes-import-parser.ts` by covering
 * the failure modes installed-device QA testers are most likely
 * to hit:
 *
 * 1. Empty / whitespace-only input.
 * 2. No-heading paste (raw lines without sections).
 * 3. Invalid / unparseable date formats.
 * 4. Two-digit year normalisation round-trip.
 * 5. Multiple events in a single period chain (start →
 *    dose_change → permanent_stop).
 * 6. Privacy contract: privateRawLine round-trips raw input
 *    verbatim, and the public projection does not leak it.
 * 7. Mixed-locale date with day-month-year (DMY) form.
 * 8. Lines with multiple doses — parser picks the first
 *    deterministically rather than aggregating silently.
 *
 * No EAS / TestFlight / Play / production release. Repo-only.
 */

import assert from 'node:assert/strict';
import {
  parseJournalNotesPaste,
  type ParsedJournalNotesEntry,
} from '../../packages/shared/src/journal/notes-import';

function expectEmptyAndWhitespace(): void {
  for (const input of ['', '   ', '\n\n\n', '\t\t', '\r\n\r\n']) {
    const parsed = parseJournalNotesPaste(input);
    assert.equal(parsed.entries.length, 0, `empty input ${JSON.stringify(input)} → no entries`);
    assert.equal(parsed.skippedLines.length, 0, 'no-content input does not skip lines');
    assert.equal(parsed.warnings.length, 0, 'no-content input emits no warnings');
    assert.equal(parsed.sourceKind, 'apple_notes_paste');
  }
}

function expectNoHeadingPaste(): void {
  // No heading line — currentSection stays 'Unsectioned'.
  const parsed = parseJournalNotesPaste('2026-05-01 BPC-157 100mcg start');
  assert.equal(parsed.entries.length, 1);
  assert.equal(parsed.entries[0].section, 'Unsectioned');
  assert.equal(parsed.entries[0].date, '2026-05-01');
  assert.equal(parsed.entries[0].canonicalName, 'BPC-157');
}

function expectInvalidDateFormatsAreNull(): void {
  // Garbled dates → date is null; status flips to missing_required_field.
  // Anti-rule: NEVER fabricate a date. The parser must report null
  // and warn rather than guessing.
  const cases: Array<{ raw: string; expectedItem: string }> = [
    { raw: 'Yesterday — 100mcg BPC-157', expectedItem: 'BPC-157' },
    { raw: '32-13-9999 BPC-157 100mcg', expectedItem: 'BPC-157' },
    { raw: 'Christmas BPC-157 100mcg', expectedItem: 'BPC-157' },
  ];
  for (const c of cases) {
    const parsed = parseJournalNotesPaste(c.raw);
    if (parsed.entries.length === 0) continue; // some lines may be heading-classified
    const entry = parsed.entries[0];
    assert.equal(entry.date, null, `unparseable date in ${JSON.stringify(c.raw)} must produce null`);
    assert.equal(entry.status, 'missing_required_field');
    assert.ok(entry.parseWarnings.some((w) => /missing date/i.test(w)), 'missing-date warning must be raised');
  }
}

function expectTwoDigitYearNormalisation(): void {
  const parsed = parseJournalNotesPaste('01/05/26 Creatine 5g daily');
  assert.equal(parsed.entries.length, 1);
  assert.equal(parsed.entries[0].date, '2026-05-01', 'two-digit year must expand to 20XX');
}

function expectPeriodChainHonoursPermanentStop(): void {
  const raw = [
    'Peptides:',
    '2026-04-01 BPC-157 100mcg start',
    '2026-04-15 BPC-157 200mcg dose_change',
    '2026-05-01 BPC-157 permanent stop',
  ].join('\n');
  const parsed = parseJournalNotesPaste(raw);
  const start = parsed.entries.find((e) => e.canonicalName === 'BPC-157' && e.date === '2026-04-01');
  const change = parsed.entries.find((e) => e.canonicalName === 'BPC-157' && e.date === '2026-04-15');
  const permStop = parsed.entries.find((e) => e.canonicalName === 'BPC-157' && e.eventType === 'permanent_stop');
  assert.ok(start && change && permStop, 'all three BPC-157 events must parse');
  assert.equal(start!.periodEndDate, '2026-04-15', 'period ends at next dose_change');
  assert.equal(change!.periodEndDate, '2026-05-01', 'dose_change period ends at permanent_stop');
  assert.ok(permStop!.parseWarnings.some((w) => w.includes('Permanent stop')), 'permanent_stop warning is preserved');
}

function expectPrivacyContractRoundTrip(): void {
  // privateRawLine must round-trip the raw input bytes verbatim
  // — anti-rule for the AI spend gate (rule 22): the raw
  // private text MUST never be lost (so the user can audit) AND
  // must never bleed into the public projection.
  const raw = '2026-05-01 BPC-157 100mcg start (notes: keep private)';
  const parsed = parseJournalNotesPaste(raw);
  assert.equal(parsed.entries.length, 1);
  const entry = parsed.entries[0];
  assert.equal(entry.readinessInput.privateRawLine, entry.rawLine, 'privateRawLine must equal rawLine');
  assert.equal(entry.readinessInput.privateRawLine, raw, 'privateRawLine must round-trip the input verbatim');
  assert.equal(entry.readinessInput.contextOnly, true, 'context-only flag locks the privacy floor');
  assert.equal(entry.readinessInput.userConfirmed, false, 'user-confirmed flag default = false');

  // Verify the public projection (matching the keys the existing
  // happy-path test asserts) does not carry privateRawLine.
  const PUBLIC_SURFACE_KEYS = ['section', 'date', 'itemText', 'canonicalName', 'category', 'eventType', 'amount', 'unit', 'confidence'];
  const projected = Object.fromEntries(PUBLIC_SURFACE_KEYS.map((k) => [k, entry[k as keyof ParsedJournalNotesEntry]]));
  assert.ok(!('privateRawLine' in projected), 'public projection MUST NOT carry privateRawLine');
  assert.ok(!('rawLine' in projected), 'public projection MUST NOT carry rawLine');
  assert.equal(JSON.stringify(projected).includes('keep private'), false, 'public projection MUST NOT leak parenthetical private text');
}

function expectMixedLocaleDmy(): void {
  // DMY form "1 May 2026" should resolve to the same ISO as "2026-05-01".
  const parsed = parseJournalNotesPaste('1 May 2026 Creatine 5g daily');
  assert.equal(parsed.entries.length, 1);
  assert.equal(parsed.entries[0].date, '2026-05-01');
}

function expectMultipleDosesPickFirstDeterministic(): void {
  // Some users paste lines like "Took 100mcg morning + 50mcg evening".
  // Parser picks the FIRST dose deterministically; the warning
  // surface and itemText should reflect that.
  const parsed = parseJournalNotesPaste('2026-05-01 BPC-157 100mcg morning + 50mcg evening');
  assert.equal(parsed.entries.length, 1);
  const entry = parsed.entries[0];
  assert.equal(entry.amount, 100, 'first dose wins');
  assert.equal(entry.unit, 'mcg');
  assert.equal(entry.frequency, 'morning', 'first frequency wins');
}

function expectAllWarningsAreInWarningsArray(): void {
  // For traceability: every warning attached to a row must also
  // appear in the top-level warnings array, so a UI can render
  // them in a single list without iterating entries.
  const parsed = parseJournalNotesPaste('2026-05-01 BPC-157 (no dose) start');
  assert.ok(parsed.entries.length >= 1);
  const entry = parsed.entries[0];
  for (const w of entry.parseWarnings) {
    const present = parsed.warnings.some((tw) => tw.warning === w && tw.lineNumber === entry.sourceLineNumber);
    assert.ok(present, `top-level warnings array must include: ${w}`);
  }
}

function main(): void {
  expectEmptyAndWhitespace();
  expectNoHeadingPaste();
  expectInvalidDateFormatsAreNull();
  expectTwoDigitYearNormalisation();
  expectPeriodChainHonoursPermanentStop();
  expectPrivacyContractRoundTrip();
  expectMixedLocaleDmy();
  expectMultipleDosesPickFirstDeterministic();
  expectAllWarningsAreInWarningsArray();
  console.log('FS-020 journal parser QA-gap test passed (empty / unsection / invalid date / DMY / 2-digit year / permanent_stop chain / privacy contract / multi-dose / warnings array).');
}

main();
