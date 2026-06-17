/**
 * Reference — mobile knowledge entry point for the Lauburu Grappling Map.
 *
 * Real technique content is now bundled via REFERENCE_TECHNIQUES,
 * generated from the web repo's canonical SECTIONS table (itself built
 * from the OPML pipeline). The screen no longer shows an empty
 * headings-only scaffold — each expanded position renders the actual
 * techniques for the selected role, headings with no content are
 * hidden, and the role toggle really does swap content between
 * perspectives.
 *
 * Content authority still = Aaron via the OPML pipeline. To refresh
 * the bundle, re-run the extractor described in the header of
 * reference-techniques.ts.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  Share,
  TextInput,
  Alert,
  Linking,
  View as RNView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { router, useLocalSearchParams } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { useProfile } from '../../src/hooks/useProfile';
import { useVideoAttachmentSummaries } from '../../src/hooks/useVideoAttachmentSummaries';
import {
  deriveTechniqueVideoDisplayState,
  fallbackVideoAttachmentSummary,
} from '../../src/services/video-attachment-display';

/** Live website base URL — the full Reference tree, 3D graph, and
 *  attached media all live here today. The mobile Reference screen
 *  bridges to it via explicit "Open ... in 3D map" CTAs that
 *  deep-link into a dedicated in-app scene. */
const FULL_MAP_URL = 'https://www.lauburugrapplingmap.com/';
import {
  REFERENCE_SECTIONS,
  REFERENCE_TOTAL_POSITIONS,
  REFERENCE_BUILT_OUT_COUNT,
  type ReferenceSection,
  type ReferencePosition,
} from '../../src/data/reference-seed';
import {
  REFERENCE_TECHNIQUES,
  REFERENCE_TECHNIQUE_COUNT,
} from '../../src/data/reference-techniques';
import {
  BELT_SYLLABUS,
  type BeltLevel,
} from '../../src/data/belt-syllabus';
import {
  useReferenceProgressStore,
  buildTechniqueProgressKey,
  buildTransitionProgressKey,
  buildProgressExportJSON,
  parseProgressImportPayload,
  parseProgressKey,
  type ProgressStatus,
  type ProgressExportPayload,
} from '../../src/store/reference-progress-store';
import type { VideoAttachmentSummary } from '@lauburu/shared';

interface CoachingTechniqueFocus {
  position: string;
  role: string | null;
  heading: string | null;
  technique: string | null;
}

interface CoachRecommendedTechniqueTarget {
  position: string;
  role: string | null;
  heading: string | null;
  technique: string | null;
  reason: string | null;
}

function isBeltLevel(value: string | null | undefined): value is BeltLevel {
  return value === 'white' || value === 'blue' || value === 'purple' || value === 'brown' || value === 'black';
}

function findTechniqueVideoTargetId(args: {
  belt: BeltLevel | null;
  position: string;
  role: string;
  heading: string;
  technique: string;
}): string | null {
  if (!args.belt) return null;
  const match = BELT_SYLLABUS.find(
    (item) =>
      item.belt === args.belt &&
      item.position === args.position &&
      item.role === args.role &&
      item.heading === args.heading &&
      item.technique === args.technique,
  );
  return match?.id ?? null;
}

/**
 * Normalize a position name for lookup into REFERENCE_TECHNIQUES.
 * Hand Fighting positions in the seed are clean ("Outside tie") but
 * in the web data they carry a "(You)" suffix ("Outside tie (You)")
 * because they disambiguate the grip-holder side. We try the exact
 * name first, then the "(You)"-suffixed form.
 */
function lookupPositionTechniques(
  positionName: string,
): Record<string, Record<string, string[]>> | null {
  const direct = REFERENCE_TECHNIQUES[positionName];
  if (direct) return direct;
  const withYou = REFERENCE_TECHNIQUES[`${positionName} (You)`];
  if (withYou) return withYou;
  return null;
}

/** Normalize a heading name so spacing differences AND the
 *  "Defence" vs "Defence/Escapes" inconsistency in the source data
 *  don't break lookups. Reduces a heading to its first significant
 *  word before any slash. Mobile seed's 6 canonical headings each
 *  start with a distinct word so this collision-free:
 *    "Setups/Entries"          → "setups"
 *    "Setups / Entries"        → "setups"
 *    "Control"                 → "control"
 *    "Offence"                 → "offence"
 *    "Defence"                 → "defence"
 *    "Defence/Escapes"         → "defence"
 *    "Defence / Escapes"       → "defence"
 *    "Submissions"             → "submissions"
 *    "Offensive transitions"   → "offensive transitions"
 */
function normalizeHeading(h: string): string {
  const base = h.split('/')[0]!.trim().toLowerCase();
  return base;
}

/** Look up a specific heading's technique list for a role, with the
 *  spacing-tolerant match above. Returns an empty array when the
 *  heading has no content for the given role. */
function techniquesForHeading(
  positionTechs: Record<string, Record<string, string[]>> | null,
  role: string,
  heading: string,
): string[] {
  if (!positionTechs) return [];
  const roleMap = positionTechs[role];
  if (!roleMap) return [];
  // Fast path — exact match.
  if (roleMap[heading]) return roleMap[heading];
  // Slow path — normalize and scan.
  const want = normalizeHeading(heading);
  for (const key of Object.keys(roleMap)) {
    if (normalizeHeading(key) === want) return roleMap[key];
  }
  return [];
}

/** True when at least one role for this position has at least one
 *  technique under any heading. Used to gate the "no content yet"
 *  footer distinction. */
function positionHasAnyContent(
  positionTechs: Record<string, Record<string, string[]>> | null,
): boolean {
  if (!positionTechs) return false;
  for (const role of Object.keys(positionTechs)) {
    for (const h of Object.keys(positionTechs[role])) {
      if (positionTechs[role][h].length > 0) return true;
    }
  }
  return false;
}

/**
 * Parsed offensive-transition edge derived from an "Offensive
 * transitions" heading entry. The raw data strings have the format
 * `<source label> → <destination label>` — we split on the arrow,
 * strip Hand Fighting's "(You)" disambiguation suffix, and record
 * whether the destination matches a known mobile-seed position
 * (i.e. whether tapping the row can jump somewhere useful in the
 * mobile tree).
 */
export interface TransitionEdge {
  /** Left-hand side of the arrow — the technique doing the transition. */
  label: string;
  /** Right-hand side of the arrow with "(You)" suffix stripped. */
  destination: string;
  /** True when `destination` matches a known mobile-seed position
   *  name so tapping can navigate the mobile Reference tree. When
   *  false, the row still renders (preserves information) but is
   *  non-tappable. */
  destinationKnown: boolean;
}

/** Build the set of known mobile-seed position names once at module
 *  load. Used by parseTransitionEdges to decide which destinations
 *  can be navigated to. */
const KNOWN_POSITION_NAMES: ReadonlySet<string> = (() => {
  const s = new Set<string>();
  for (const section of REFERENCE_SECTIONS) {
    for (const p of section.positions) s.add(p.name);
  }
  return s;
})();

/** Build a name → ReferencePosition lookup once at module load so
 *  transition-jump filter-escape logic can check built_out status
 *  in O(1) without re-walking REFERENCE_SECTIONS on every tap. */
const POSITION_BY_NAME: ReadonlyMap<string, ReferencePosition> = (() => {
  const m = new Map<string, ReferencePosition>();
  for (const section of REFERENCE_SECTIONS) {
    for (const p of section.positions) m.set(p.name, p);
  }
  return m;
})();

/** Build a position-name → section-label lookup once at module load.
 *  Used by the progress store's transition key builder to keep the
 *  inbound and outbound views of the same edge rooted at the same
 *  storage slot. */
const SECTION_LABEL_BY_POSITION_NAME: ReadonlyMap<string, string> = (() => {
  const m = new Map<string, string>();
  for (const section of REFERENCE_SECTIONS) {
    for (const p of section.positions) m.set(p.name, section.label);
  }
  return m;
})();

/**
 * Per-position search payload — flat lowercase corpus joined
 * across position name + every catalogued technique label +
 * every transition label/destination, for both perspectives.
 * Lets the search input match content INSIDE positions, not
 * just position names. One fast substring check per filter
 * pass. Built ONCE at module load and never mutated.
 *
 * Storage shape is intentionally simple — one big lowercase
 * string per position, joined by `||` so substrings can't
 * accidentally bleed across boundaries (a query like "guard
 * pass" won't false-match against "Closed guard||Pass to side
 * control" because the `||` between segments breaks the
 * adjacency). The structured per-row match index below
 * (`POSITION_SEARCH_INDEX`) handles the highlight-which-row
 * problem; this haystack is just the gate for "is this
 * position a search hit at all".
 */
const POSITION_SEARCH_HAYSTACK: ReadonlyMap<string, string> = (() => {
  const map = new Map<string, string>();
  for (const section of REFERENCE_SECTIONS) {
    for (const position of section.positions) {
      const parts: string[] = [position.name];
      const techs = lookupPositionTechniques(position.name);
      if (techs) {
        for (const role of position.perspectives) {
          for (const heading of position.headings) {
            const list = techniquesForHeading(techs, role, heading);
            for (const item of list) parts.push(item);
          }
        }
      }
      map.set(position.name, parts.join('||').toLowerCase());
    }
  }
  return map;
})();

/**
 * Structured per-position match index — for each position,
 * the set of technique-row keys (`role|heading|index`) and
 * transition-edge keys (`role|label|destination`) whose
 * lowercased label contains the active query. Built lazily on
 * the consumer side via `buildPositionQueryMatchIndex` keyed by
 * position + query, so it costs nothing while no search is
 * active. Drives the row-level highlight + the role-pivot
 * logic so an "armbar" search auto-flips to whichever
 * perspective actually has armbars catalogued.
 */
interface PositionQueryMatchIndex {
  /** `${role}|${heading}|${index}` keys for matching technique rows. */
  techKeys: ReadonlySet<string>;
  /** `${role}|${label}|${destination}` keys for matching transition rows. */
  transitionKeys: ReadonlySet<string>;
  /** Per-role total match counts (techniques + transitions on that role). */
  roleMatchCounts: ReadonlyMap<string, number>;
  /** Total matches across both roles. */
  total: number;
}

function buildPositionQueryMatchIndex(
  position: ReferencePosition,
  query: string,
): PositionQueryMatchIndex {
  const empty: PositionQueryMatchIndex = {
    techKeys: new Set(),
    transitionKeys: new Set(),
    roleMatchCounts: new Map(),
    total: 0,
  };
  const q = query.trim().toLowerCase();
  if (!q) return empty;
  const positionTechs = lookupPositionTechniques(position.name);
  if (!positionTechs) return empty;

  const techKeys = new Set<string>();
  const transitionKeys = new Set<string>();
  const roleMatchCounts = new Map<string, number>();
  let total = 0;

  for (const role of position.perspectives) {
    let roleHits = 0;
    // Technique rows — match against the technique label.
    for (const heading of position.headings) {
      if (heading === 'Offensive transitions') continue;
      const list = techniquesForHeading(positionTechs, role, heading);
      list.forEach((item, idx) => {
        if (item.toLowerCase().includes(q)) {
          techKeys.add(`${role}|${heading}|${idx}`);
          roleHits += 1;
          total += 1;
        }
      });
    }
    // Transition rows — match against label OR destination, since
    // a user searching "mount" expects to find "armbar finish →
    // Mount" too, not only transitions whose label contains
    // "mount" verbatim.
    const rawTransitions = techniquesForHeading(
      positionTechs,
      role,
      'Offensive transitions',
    );
    const edges = parseTransitionEdges(rawTransitions);
    for (const edge of edges) {
      if (
        edge.label.toLowerCase().includes(q) ||
        edge.destination.toLowerCase().includes(q)
      ) {
        transitionKeys.add(`${role}|${edge.label}|${edge.destination}`);
        roleHits += 1;
        total += 1;
      }
    }
    if (roleHits > 0) roleMatchCounts.set(role, roleHits);
  }

  return { techKeys, transitionKeys, roleMatchCounts, total };
}

/**
 * True when a position should appear in the search results for
 * the given query. Matches on the position name OR on any
 * catalogued technique / transition content inside the
 * position. Empty queries always pass.
 */
function positionMatchesQuery(
  positionName: string,
  query: string,
): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = POSITION_SEARCH_HAYSTACK.get(positionName);
  if (!haystack) return false;
  return haystack.includes(q);
}

/**
 * Structural hub metadata for a single canonical position —
 * inbound edge count + outbound edge count + a combined score
 * (simple sum) used to rank positions as "most structurally
 * important graph hubs" for the Top hubs quick-jump strip.
 *
 * Outbound counts are deduped per position by (label|destination)
 * so a transition listed under two perspectives doesn't inflate
 * the score. Self-loops and unknown destinations are already
 * filtered out by KNOWN_POSITION_NAMES gating upstream.
 */
export interface PositionHubEntry {
  name: string;
  inbound: number;
  outbound: number;
  score: number;
}

/**
 * A single inbound transition edge — represents the fact that some
 * source position transitions INTO this destination. Used by the
 * "Coming in from" block and the inbound-count chip on position
 * headers. Dedupe key is (sourceName, label) so the same source
 * technique cited twice against the same destination doesn't
 * inflate counts.
 */
export interface InboundTransitionEdge {
  /** Mobile-seed canonical source position name (no "(You)" suffix). */
  sourceName: string;
  /** Role/perspective on the source side that emits the transition. */
  sourceRole: string;
  /** Technique label that performs the transition. */
  label: string;
}

/**
 * Inverse transition index — keyed by destination position name,
 * built ONCE at module load by walking every (position, perspective)
 * tuple in REFERENCE_TECHNIQUES, parsing each "Offensive transitions"
 * heading's arrow entries, and appending each edge to the map keyed
 * by its canonical destination. Deduped by (sourceName, label) so
 * the same source technique cited twice doesn't double-count. This
 * keeps the per-position inbound lookup O(1) at render time.
 */
const INBOUND_TRANSITIONS: ReadonlyMap<string, InboundTransitionEdge[]> = (() => {
  const map = new Map<string, InboundTransitionEdge[]>();
  // Strip Hand Fighting's "(You)" suffix to get the mobile-seed
  // canonical source name. Mirrors resolveWebPositionName's reverse.
  const canonicalizeSourceName = (raw: string): string =>
    raw.replace(/\s*\(You\)\s*$/, '').trim();

  for (const [posKey, persps] of Object.entries(REFERENCE_TECHNIQUES)) {
    const sourceName = canonicalizeSourceName(posKey);
    for (const [role, headings] of Object.entries(persps)) {
      const raw = headings['Offensive transitions'];
      if (!raw) continue;
      for (const entry of raw) {
        if (typeof entry !== 'string') continue;
        const idx = entry.indexOf('→');
        if (idx < 0) continue;
        const label = entry.slice(0, idx).trim();
        const destRaw = entry.slice(idx + 1).trim();
        if (!label || !destRaw) continue;
        const destination = canonicalizeTransitionDestination(destRaw);
        // Only index edges whose destination is a known mobile-seed
        // position — unknown destinations (e.g. submissions like
        // "D'Arce", "Anaconda") have no landing card to render into.
        if (!KNOWN_POSITION_NAMES.has(destination)) continue;
        // Self-loops (source == destination) aren't useful as
        // inbound hints — skip them so the count stays meaningful.
        if (sourceName === destination) continue;
        const bucket = map.get(destination) ?? [];
        // Dedupe by (sourceName, label) — same technique mentioned
        // twice under two different perspectives shouldn't inflate.
        const isDuplicate = bucket.some(
          (e) => e.sourceName === sourceName && e.label === label,
        );
        if (!isDuplicate) {
          bucket.push({ sourceName, sourceRole: role, label });
        }
        if (!map.has(destination)) map.set(destination, bucket);
      }
    }
  }
  // Sort each bucket by source name for stable, readable rendering.
  for (const bucket of map.values()) {
    bucket.sort((a, b) =>
      a.sourceName.localeCompare(b.sourceName) ||
      a.label.localeCompare(b.label),
    );
  }
  return map;
})();

/**
 * Structural hub ranking — top N positions by combined
 * inbound + outbound transition-edge count, sorted descending
 * and sliced at TOP_HUBS_LIMIT. Built ONCE at module load from
 * INBOUND_TRANSITIONS plus a deduped pass through each
 * position's outbound "Offensive transitions" across all
 * perspectives. Serves the Top hubs overview strip at the top
 * of the Reference screen.
 *
 * Outbound dedupe key is (label|destination) per position so a
 * transition listed under two source perspectives contributes
 * once, not twice. Self-loops (source === destination) and
 * edges pointing at non-mobile-seed positions (submissions
 * like D'Arce / Anaconda) are already filtered out by the
 * same KNOWN_POSITION_NAMES gating used by INBOUND_TRANSITIONS
 * and the transition-row render path.
 *
 * Tie-break order: higher combined score first, then higher
 * inbound (more "hub-like"), then alphabetical by name for
 * stable render.
 *
 * Positions with score === 0 are filtered out entirely so the
 * strip never surfaces leaf positions as "top hubs".
 */
const TOP_HUBS_LIMIT = 5;

const TOP_HUBS: ReadonlyArray<PositionHubEntry> = (() => {
  const entries: PositionHubEntry[] = [];
  for (const section of REFERENCE_SECTIONS) {
    for (const p of section.positions) {
      const inbound = INBOUND_TRANSITIONS.get(p.name)?.length ?? 0;
      const posTechs = lookupPositionTechniques(p.name);
      let outbound = 0;
      if (posTechs) {
        const seen = new Set<string>();
        for (const headings of Object.values(posTechs)) {
          const raw = headings['Offensive transitions'];
          if (!raw) continue;
          for (const entry of raw) {
            if (typeof entry !== 'string') continue;
            const arrowIdx = entry.indexOf('→');
            if (arrowIdx < 0) continue;
            const label = entry.slice(0, arrowIdx).trim();
            const destRaw = entry.slice(arrowIdx + 1).trim();
            if (!label || !destRaw) continue;
            const dest = canonicalizeTransitionDestination(destRaw);
            if (!KNOWN_POSITION_NAMES.has(dest)) continue;
            if (dest === p.name) continue; // no self-loops
            const edgeKey = `${label}|${dest}`;
            if (seen.has(edgeKey)) continue;
            seen.add(edgeKey);
            outbound += 1;
          }
        }
      }
      const score = inbound + outbound;
      if (score > 0) {
        entries.push({ name: p.name, inbound, outbound, score });
      }
    }
  }
  entries.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (b.inbound !== a.inbound) return b.inbound - a.inbound;
    return a.name.localeCompare(b.name);
  });
  return entries.slice(0, TOP_HUBS_LIMIT);
})();

/** Normalize a raw destination string into a canonical mobile-seed
 *  position name. Strips the "(You)" suffix used by Hand Fighting
 *  positions in the web data and trims whitespace. Does NOT invent
 *  names — if the result still doesn't match a known position the
 *  caller marks the edge as non-navigable. */
function canonicalizeTransitionDestination(raw: string): string {
  let s = raw.trim();
  s = s.replace(/\s*\(You\)\s*$/, '');
  return s;
}

/**
 * Parse an array of "Offensive transitions" heading entries into
 * structured TransitionEdge rows. Entries that don't contain a
 * " → " arrow are skipped silently (occasional stray non-arrow
 * lines show up in the upstream data, filtering them out keeps
 * the mobile UI honest). The same source label feeding two
 * different destinations yields two separate edges.
 */
function parseTransitionEdges(
  rawEntries: string[] | undefined,
): TransitionEdge[] {
  if (!rawEntries) return [];
  const out: TransitionEdge[] = [];
  for (const raw of rawEntries) {
    if (!raw || typeof raw !== 'string') continue;
    const idx = raw.indexOf('→');
    if (idx < 0) continue;
    const label = raw.slice(0, idx).trim();
    const destRaw = raw.slice(idx + 1).trim();
    if (!label || !destRaw) continue;
    const destination = canonicalizeTransitionDestination(destRaw);
    out.push({
      label,
      destination,
      destinationKnown: KNOWN_POSITION_NAMES.has(destination),
    });
  }
  return out;
}

/**
 * Build a compact, human-readable text summary of the user's
 * stored Reference progress for Share.share export. Output is
 * deterministic and local-only — no network calls, no auth, no
 * backend sync — and safe to paste into ChatGPT, notes apps,
 * messages, or a coach DM.
 *
 * Output structure:
 *   Lauburu Grappling Map — training status
 *
 *   12 drilling · 47 learned · 8 tracking
 *
 *   Top positions:
 *     · Back Control (7)
 *     · Mount (5)
 *     · Crab ride (3)
 *
 *   [when a filter is active]
 *   All learned items:
 *     · Back Control · Submissions: Rear naked choke
 *     · Mount · Offence: Knee through to mounted triangle
 *     · <source>: <label> → <destination>
 *     ...
 *
 *   — Exported <locale date>
 *
 * Scope semantics:
 *   When `activeFilter` is null the export is the aggregate
 *   summary (counts + top positions, no per-item list).
 *   When `activeFilter` is set the export layers a full
 *   filtered list ON TOP of the aggregate so the user gets
 *   both "what I've flagged overall" AND "this specific
 *   status list I'm currently viewing". No scope switch — the
 *   aggregate header is always present so the recipient of
 *   the shared text sees the whole training context in one
 *   paste.
 */
function buildProgressExportText(
  progressMap: Record<string, ProgressStatus>,
  counts: { drilling: number; learned: number; tracking: number },
  activeFilter: ProgressStatus | null,
  notesMap: Record<string, string> = {},
  updatedAtMap: Record<string, string> = {},
): string {
  const lines: string[] = [];
  lines.push('Lauburu Grappling Map — training status');
  lines.push('');

  // Aggregate count line
  const countParts: string[] = [];
  if (counts.drilling > 0) countParts.push(`${counts.drilling} drilling`);
  if (counts.learned > 0) countParts.push(`${counts.learned} learned`);
  if (counts.tracking > 0) countParts.push(`${counts.tracking} tracking`);
  if (countParts.length === 0) {
    lines.push('No items flagged yet.');
  } else {
    lines.push(countParts.join(' · '));
  }

  // Top positions — parsed from the progress key format. Both
  // technique keys ('tech|section|position|role|heading|label')
  // and transition keys ('tx|sourceSection|sourcePosition|
  // sourceRole|label|destination') put the position / source
  // position at index 2, so the scan is a single split + read
  // per entry.
  const byPosition = new Map<string, number>();
  for (const [key, status] of Object.entries(progressMap)) {
    if (status === 'none') continue;
    const parts = key.split('|');
    if (
      (parts[0] === 'tech' || parts[0] === 'tx') &&
      parts.length >= 3 &&
      parts[2]
    ) {
      const pos = parts[2];
      byPosition.set(pos, (byPosition.get(pos) ?? 0) + 1);
    }
  }
  const topPositions = Array.from(byPosition.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  if (topPositions.length > 0) {
    lines.push('');
    lines.push('Top positions:');
    for (const [pos, count] of topPositions) {
      lines.push(`  · ${pos} (${count})`);
    }
  }

  // Filtered list — when a filter is active, list every item
  // currently in that state with a readable breadcrumb. Parses
  // the key format into human-readable breadcrumbs so the
  // recipient doesn't see raw `tech|Guard|K guard|...` keys.
  // Notes attached to a flagged item are folded inline as a
  // second indented line so a coach reading the share text sees
  // the user's annotation right next to the move.
  if (activeFilter) {
    const filteredKeys = Object.entries(progressMap)
      .filter(([, v]) => v === activeFilter)
      .map(([k]) => k);
    if (filteredKeys.length > 0) {
      lines.push('');
      lines.push(`All ${activeFilter} items (${filteredKeys.length}):`);
      for (const key of filteredKeys) {
        const parts = key.split('|');
        let readable = key;
        if (parts[0] === 'tech' && parts.length >= 6) {
          // tech|section|position|role|heading|label
          const pos = parts[2];
          const heading = parts[4];
          // Label may contain pipes in edge cases — rejoin
          // any trailing segments just in case so we never
          // drop data.
          const label = parts.slice(5).join('|');
          readable = `${pos} · ${heading}: ${label}`;
        } else if (parts[0] === 'tx' && parts.length >= 6) {
          // tx|sourceSection|sourcePosition|sourceRole|label|destination
          const src = parts[2];
          const label = parts[4];
          const dest = parts.slice(5).join('|');
          readable = `${src}: ${label} → ${dest}`;
        }
        lines.push(`  · ${readable}`);
        const note = notesMap[key];
        if (typeof note === 'string' && note.length > 0) {
          // Wrap long notes by indenting continuation lines two
          // extra spaces. Plain text export — no markdown — so
          // recipients in any chat app see clean alignment.
          const noteLines = note.split('\n');
          for (const ln of noteLines) {
            lines.push(`      ↳ ${ln}`);
          }
        }
      }
    }
  }

  // Notes-included aggregate count (only when there are notes
  // outside the active filter, so an aggregate-only export still
  // surfaces the fact that the user has annotations). Stays out
  // of the way for users who haven't started using notes yet.
  const totalNotes = Object.values(notesMap).filter(
    (v) => typeof v === 'string' && v.length > 0,
  ).length;
  if (totalNotes > 0 && !activeFilter) {
    lines.push('');
    lines.push(
      `Notes attached to ${totalNotes} item${totalNotes === 1 ? '' : 's'}.`,
    );
  }

  lines.push('');
  lines.push(`— Exported ${new Date().toLocaleDateString()}`);

  // Machine-readable import payload — appended at the bottom of
  // the human export so a single share string can be either read
  // by a human or re-imported on another device. The Import pane
  // parser scans for the first `{"version"` anchor so the JSON
  // survives any leading human-readable content. Now passes the
  // notes and updated_at maps so a v2 export carries the full
  // tracked context across devices.
  lines.push('');
  lines.push(
    '--- Import payload (paste below into Import on another device) ---',
  );
  lines.push(buildProgressExportJSON(progressMap, notesMap, updatedAtMap));

  return lines.join('\n');
}

/**
 * Test whether a position has at least one technique, outbound
 * transition, or inbound transition whose stored progress status
 * matches the active filter. Used by SectionBlock to hide position
 * cards that would render empty under a progress filter, and by
 * PositionRow to auto-expand when it does match.
 *
 * Scans all perspectives on the position AND all inbound edges
 * pointing at it. Transitions are intentionally counted on BOTH
 * the source and the destination side so users can find the same
 * edge from either card in the filtered view. The global
 * screen-top aggregate count in ReferenceScreen uses a different
 * path (Object.values(progress).filter(...)) which is already
 * dedupe-safe because a single storage key represents one edge.
 */
function positionHasMatchingProgress(
  position: ReferencePosition,
  progress: Record<string, ProgressStatus>,
  filter: ProgressStatus | null,
): boolean {
  if (!filter) return true;
  const sectionLabel =
    SECTION_LABEL_BY_POSITION_NAME.get(position.name) ?? '';
  const posTechs = lookupPositionTechniques(position.name);
  if (posTechs) {
    for (const [role, headings] of Object.entries(posTechs)) {
      for (const [heading, techs] of Object.entries(headings)) {
        if (heading === 'Offensive transitions') {
          for (const raw of techs) {
            const idx = raw.indexOf('→');
            if (idx < 0) continue;
            const label = raw.slice(0, idx).trim();
            const destRaw = raw.slice(idx + 1).trim();
            if (!label || !destRaw) continue;
            const dest = canonicalizeTransitionDestination(destRaw);
            const key = buildTransitionProgressKey(
              sectionLabel,
              position.name,
              role,
              label,
              dest,
            );
            if (progress[key] === filter) return true;
          }
        } else {
          for (const t of techs) {
            const key = buildTechniqueProgressKey(
              sectionLabel,
              position.name,
              role,
              heading,
              t,
            );
            if (progress[key] === filter) return true;
          }
        }
      }
    }
  }
  // Inbound edges — count if the edge was flagged from the source
  // side (inbound + outbound share a key rooted at the source).
  const inbound = INBOUND_TRANSITIONS.get(position.name) ?? [];
  for (const e of inbound) {
    const srcSection =
      SECTION_LABEL_BY_POSITION_NAME.get(e.sourceName) ?? '';
    const key = buildTransitionProgressKey(
      srcSection,
      e.sourceName,
      e.sourceRole,
      e.label,
      position.name,
    );
    if (progress[key] === filter) return true;
  }
  return false;
}

/** Count the total techniques available for a specific role on a
 *  position. Used to badge role toggle pills with per-role counts
 *  and to de-emphasize role pills whose side of the catalogue is
 *  still empty, so the toggle stops feeling decorative. */
function countTechniquesForRole(
  positionTechs: Record<string, Record<string, string[]>> | null,
  role: string,
): number {
  if (!positionTechs) return 0;
  const roleMap = positionTechs[role];
  if (!roleMap) return 0;
  let total = 0;
  for (const h of Object.keys(roleMap)) total += roleMap[h].length;
  return total;
}

/**
 * Map a mobile-seed section label to the web site's section name.
 * The web SECTIONS bundle has no top-level "Hand Fighting" — those
 * positions live inside the "Wrestling" section under the
 * "Hand fighting" container — so we redirect Hand Fighting deep
 * links to Wrestling to match the web DOM's data-section attribute.
 * Every other section label is a passthrough.
 */
function resolveWebSectionName(mobileSectionLabel: string): string {
  if (mobileSectionLabel === 'Hand Fighting') return 'Wrestling';
  return mobileSectionLabel;
}

/**
 * Map a mobile-seed position name to the web site's canonical
 * position name. Hand Fighting positions on mobile are clean
 * ("Outside tie") but on the web carry a "(You)" suffix
 * ("Outside tie (You)") — we check the REFERENCE_TECHNIQUES map
 * to find which variant the web side recognises, preferring the
 * direct name and falling back to the suffixed form. This is the
 * same resolution order used by `lookupPositionTechniques`.
 */
function resolveWebPositionName(mobilePositionName: string): string {
  if (REFERENCE_TECHNIQUES[mobilePositionName]) return mobilePositionName;
  if (REFERENCE_TECHNIQUES[`${mobilePositionName} (You)`]) {
    return `${mobilePositionName} (You)`;
  }
  return mobilePositionName;
}

/**
 * Encode a single path segment for the web's `#tech=` deep-link
 * format. The web's hash parser does `replace(/_/g, ' ')` on each
 * segment, so we need to round-trip spaces → underscores BEFORE
 * URI-encoding the whole key. Pipe characters in label strings
 * would break the segment split; we replace them defensively.
 */
function encodeDeepLinkSegment(s: string): string {
  return s.replace(/\|/g, '').replace(/\s+/g, '_');
}

export interface FullMapDeepLinkArgs {
  /** Mobile-seed section label for the position (e.g. "Guard",
   *  "Hand Fighting"). Optional — omit for a plain site-root link. */
  section?: string;
  /** Mobile-seed position name. Omit for a plain site-root link. */
  position?: string;
  /** Role/perspective name for the expanded card. Only used when
   *  building a technique-level deep link. */
  role?: string;
  /** Heading name containing the technique. Only used for
   *  technique-level deep links. */
  heading?: string;
  /** Exact technique name for technique-level deep links. */
  technique?: string;
}

/**
 * Build a hash-based deep link URL for the full-web Reference that
 * matches the existing web hash handlers:
 *   • technique present → `#tech=section|position|role|heading|technique`
 *     (web: parses segment 0 as section, last segment as technique label,
 *      falls back to position focus when no exact match is found)
 *   • position only → `#pos=<position>&sec=<section>`
 *     (web: direct position focus via switchToReferenceNode)
 *   • nothing → plain FULL_MAP_URL
 *
 * Mobile always builds the link with the WEB-resolved section +
 * position name via resolveWebSectionName / resolveWebPositionName
 * so Hand Fighting and other cross-repo naming differences don't
 * silently break focus.
 */
function buildFullMapDeepLink(args: FullMapDeepLinkArgs): string {
  const { section, position, role, heading, technique } = args;
  if (!position) return FULL_MAP_URL;

  const webSection = section ? resolveWebSectionName(section) : '';
  const webPosition = resolveWebPositionName(position);

  // Technique-level deep link — build a 5-segment pipe key that
  // matches the web's KEY_VERSION=2 convention. Segment 0 must be
  // the section so the web hash handler picks it up; segment 1
  // must be the position so the fallback path can focus it when
  // the leaf technique isn't found in the DOM.
  if (technique && webSection) {
    const segs = [
      encodeDeepLinkSegment(webSection),
      encodeDeepLinkSegment(webPosition),
      encodeDeepLinkSegment(role ?? ''),
      encodeDeepLinkSegment(heading ?? ''),
      encodeDeepLinkSegment(technique),
    ];
    const key = segs.join('|');
    return `${FULL_MAP_URL}#tech=${encodeURIComponent(key)}`;
  }

  // Position-level fallback — matches `#pos=<label>&sec=<section>`
  // which the web's applyHashRoute already parses and forwards to
  // switchToReferenceNode.
  const posPart = `pos=${encodeURIComponent(webPosition)}`;
  const secPart = webSection
    ? `&sec=${encodeURIComponent(webSection)}`
    : '';
  return `${FULL_MAP_URL}#${posPart}${secPart}`;
}

/**
 * Open the in-app 3D map tab, optionally focused on a specific
 * position/technique via the deep-link URL fragment. Uses
 * `router.navigate` so tapping the Map tab bar icon and tapping
 * a Reference CTA both end up on the same screen without
 * stacking duplicate routes.
 */
function openFullMap(args: FullMapDeepLinkArgs = {}): void {
  const url = buildFullMapDeepLink(args);
  router.navigate({
    pathname: '/(tabs)/map-3d',
    params: { url },
  });
}

function SyllabusEntryCard() {
  return (
    <Pressable
      style={styles.footerCard}
      onPress={() => router.push('/syllabus')}>
      <Text style={styles.footerTitle}>Belt syllabus</Text>
      <Text style={styles.footerBody}>
        Track a compact belt roadmap in-app, then jump straight into Reference or the 3D map for each linked position.
      </Text>
    </Pressable>
  );
}

/**
 * Compact relative-time formatter for the Recent activity strip.
 * Returns "just now", "5m ago", "3h ago", "2d ago", or a locale
 * date for anything older than a week. Tolerant of malformed
 * timestamps — returns an empty string so the chip can render
 * without a stale relative reading.
 */
function formatRelativeTime(iso: string | undefined): string {
  if (!iso) return '';
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '';
  const diff = Date.now() - t;
  if (diff < 0) return 'just now';
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)}d ago`;
  return new Date(t).toLocaleDateString();
}

/**
 * Compact progress pill — one tap cycles through
 * none → drilling → learned → tracking → none. Displays a single
 * glyph per state so it fits cleanly at the right edge of technique
 * and transition rows without eating horizontal space. Uses
 * stopPropagation on its onPress so the parent row's Pressable
 * (which handles tap-to-expand for techniques and tap-to-jump for
 * transitions) doesn't fire alongside the progress update.
 */
const PROGRESS_GLYPH: Record<ProgressStatus, string> = {
  none: '+',
  drilling: 'D',
  learned: '✓',
  tracking: '◎',
};

function ProgressPill({ progressKey }: { progressKey: string }) {
  const status = useReferenceProgressStore(
    (s) => s.progress[progressKey] ?? 'none',
  );
  const cycleProgress = useReferenceProgressStore((s) => s.cycleProgress);
  return (
    <Pressable
      hitSlop={8}
      onPress={(ev) => {
        ev.stopPropagation();
        cycleProgress(progressKey);
      }}
      style={[
        styles.progressPill,
        status === 'drilling' && styles.progressPillDrilling,
        status === 'learned' && styles.progressPillLearned,
        status === 'tracking' && styles.progressPillTracking,
      ]}>
      <Text
        style={[
          styles.progressPillText,
          status === 'drilling' && styles.progressPillTextDrilling,
          status === 'learned' && styles.progressPillTextLearned,
          status === 'tracking' && styles.progressPillTextTracking,
        ]}>
        {PROGRESS_GLYPH[status]}
      </Text>
    </Pressable>
  );
}

/**
 * Tiny "has a note" indicator — renders a pencil glyph when the
 * given progress key has a non-empty note attached. Subscribes to
 * just that single key's note slot so it only re-renders when the
 * note for THIS row changes, not on every store mutation. Returns
 * null when there's no note, so an unannotated row stays visually
 * untouched.
 */
function NoteIndicator({ progressKey }: { progressKey: string }) {
  const hasNote = useReferenceProgressStore(
    (s) => typeof s.notes[progressKey] === 'string' && s.notes[progressKey]!.length > 0,
  );
  if (!hasNote) return null;
  return <Text style={styles.noteIndicator}>✎</Text>;
}

/**
 * Inline note editor for a single progress key — rendered inside
 * the technique-row expanded detail. Holds a local draft so each
 * keystroke doesn't bounce through Zustand and re-render every
 * subscriber; commits the draft to the store on blur. The store
 * subscription syncs the draft back when the underlying note
 * changes from elsewhere (e.g. an import that overwrites this
 * key) so the editor never goes stale relative to the store.
 *
 * Empty draft on blur clears the note via setNote('') — same
 * one-call-clears semantics as the rest of the progress store.
 *
 * Notes can attach to ANY technique key — the row doesn't have to
 * be flagged first. Untracked-with-note is a meaningful state
 * (e.g. "haven't started this yet but coach said it's important")
 * and the store's setNote / persistSafely combo handles it.
 */
function NoteEditor({ progressKey }: { progressKey: string }) {
  const storedNote = useReferenceProgressStore(
    (s) => s.notes[progressKey] ?? '',
  );
  const setNote = useReferenceProgressStore((s) => s.setNote);
  const [draft, setDraft] = useState<string>(storedNote);
  const [isFocused, setIsFocused] = useState(false);
  const prevStoredNoteRef = useRef(storedNote);
  const prevProgressKeyRef = useRef(progressKey);

  // Resync the local draft when the stored note changes from
  // outside (import, share-import, replace mode). The progressKey
  // dependency also handles the case where the same NoteEditor
  // instance is recycled across different rows during scroll.
  useEffect(() => {
    const prevStoredNote = prevStoredNoteRef.current;
    const keyChanged = prevProgressKeyRef.current !== progressKey;
    const localMatchesPreviousStore = draft === prevStoredNote;
    if (!isFocused || localMatchesPreviousStore || keyChanged) {
      setDraft(storedNote);
    }
    prevStoredNoteRef.current = storedNote;
    prevProgressKeyRef.current = progressKey;
  }, [storedNote, progressKey, draft, isFocused]);

  const dirty = draft !== storedNote;

  const handleCommit = useCallback(() => {
    if (!dirty) return;
    setNote(progressKey, draft);
  }, [dirty, draft, progressKey, setNote]);

  return (
    <View style={styles.noteEditorWrap}>
      <View style={styles.noteEditorHeaderRow}>
        <Text style={styles.noteEditorLabel}>Note</Text>
        {dirty && (
          <Text style={styles.noteEditorDirtyHint}>unsaved · tap away to save</Text>
        )}
        {!dirty && draft.length > 0 && (
          <Pressable
            onPress={() => {
              setDraft('');
              setNote(progressKey, '');
            }}
            hitSlop={8}>
            <Text style={styles.noteEditorClearLink}>clear</Text>
          </Pressable>
        )}
      </View>
      <TextInput
        style={styles.noteEditorInput}
        value={draft}
        onChangeText={setDraft}
        onFocus={() => setIsFocused(true)}
        onBlur={() => {
          setIsFocused(false);
          handleCommit();
        }}
        placeholder="Coach said, what to focus on, drill counts…"
        placeholderTextColor="#555"
        multiline
        textAlignVertical="top"
        autoCorrect={false}
        autoCapitalize="sentences"
      />
    </View>
  );
}

function PositionRow({
  position,
  sectionLabel,
  focusTarget,
  onRequestFocus,
  registerOuterRef,
  progressFilter,
  query,
  coachingFocus,
  coachRecommendedTarget,
  onDismissCoachRecommendation,
  onConsumeCoachingFocus,
  currentBelt,
  videoByTargetId,
}: {
  position: ReferencePosition;
  /** Mobile-seed section label the position belongs to. Threaded
   *  through to the full-map deep link so the web hash handler
   *  receives the correct section segment. */
  sectionLabel: string;
  /** Cross-tree navigation target. When it matches this position's
   *  name the card auto-expands and flashes its border for a moment
   *  so the user sees where they landed. */
  focusTarget: string | null;
  /** Called when a transition row is tapped. Triggers a tree-level
   *  navigation to the destination position's card. */
  onRequestFocus: (destination: string) => void;
  /** Registers the outer wrapper's native ref with the parent so
   *  the parent ScrollView can measureLayout + scrollTo this card
   *  when focusTarget changes. */
  registerOuterRef: (name: string, ref: RNView | null) => void;
  /** Active progress-status filter from the top-of-screen summary
   *  strip, or null when no progress filter is applied. When set,
   *  only items whose stored status matches are rendered, and the
   *  card auto-expands so results are visible without tapping. */
  progressFilter: ProgressStatus | null;
  /** Active search query from the top-of-screen TextInput. Drives
   *  the structured per-row match index — when non-empty and at
   *  least one technique/transition row inside this position has
   *  a label or destination containing the query, the card auto-
   *  expands, the role pivots to whichever side has the match,
   *  and matching rows render with a gold search-match accent. */
  query: string;
  coachingFocus: CoachingTechniqueFocus | null;
  coachRecommendedTarget: CoachRecommendedTechniqueTarget | null;
  onDismissCoachRecommendation: () => void;
  onConsumeCoachingFocus: () => void;
  currentBelt: BeltLevel | null;
  videoByTargetId: ReadonlyMap<string, VideoAttachmentSummary>;
}) {
  // Subscribe to the progress store so filter changes re-render
  // this card. Selector keeps the dependency scoped to the map
  // itself; individual pill subscribers still scope their own
  // re-renders via per-key selectors elsewhere.
  const progress = useReferenceProgressStore((s) => s.progress);
  const [expanded, setExpanded] = useState(false);
  // Selected perspective index — defaults to 0 (first role in the pair),
  // but switches on mount to whichever role actually has content.
  const [selectedRoleIdx, setSelectedRoleIdx] = useState(0);
  // Inline technique detail expansion — the single technique row that
  // is currently expanded, or null when collapsed. Keyed by
  // `${role}|${heading}|${index}` so switching role/heading resets
  // the expansion cleanly.
  const [expandedTechKey, setExpandedTechKey] = useState<string | null>(null);
  // Temporary flash after a cross-tree navigation jump lands on
  // this card. Drives the gold border highlight and clears itself
  // after ~1.8s so stale highlights don't persist.
  const [jumpFlash, setJumpFlash] = useState(false);
  const [coachingFlashTechKey, setCoachingFlashTechKey] = useState<string | null>(
    null,
  );
  const [playbackFailedKeys, setPlaybackFailedKeys] = useState<Record<string, true>>({});

  const hasMultipleRoles = position.perspectives.length > 1;

  // Position-level technique lookup happens once per render — cheap
  // (single dictionary read, normalized position name). Returns null
  // when the position has no content in the bundled catalogue yet.
  const positionTechs = useMemo(
    () => lookupPositionTechniques(position.name),
    [position.name],
  );
  const anyContent = useMemo(
    () => positionHasAnyContent(positionTechs),
    [positionTechs],
  );

  // Per-role technique counts. Used to (a) badge role pills with
  // "Passer · 12" style chips and (b) grey out pills whose role
  // side of the catalogue is empty so the toggle stops looking
  // decorative.
  const roleCounts = useMemo(() => {
    return position.perspectives.map((role) =>
      countTechniquesForRole(positionTechs, role),
    );
  }, [positionTechs, position.perspectives]);

  // Structured per-position search-match index. Empty when no
  // query is active (cheap path — early returns inside the
  // builder), otherwise contains the per-row keys + per-role
  // match counts that drive auto-pivot, auto-expand, and the
  // gold row highlights below. Memoised on (position, query)
  // so repeat renders during scroll/expansion are free.
  const queryMatchIndex = useMemo(
    () => buildPositionQueryMatchIndex(position, query),
    [position, query],
  );
  const queryActive = query.trim().length > 0;
  const hasQueryMatches = queryMatchIndex.total > 0;

  // Auto-pivot rule order:
  //   1. If a query is active and the user's manually selected
  //      role has zero search matches, but another role does,
  //      pivot to the first role that does — search hits should
  //      always be visible without an extra tap.
  //   2. Otherwise fall back to the existing rule: if the
  //      manually selected role has zero techniques at all, pivot
  //      to the first role that has any. (Prevents "Viewing as
  //      Passer — 0 techniques" when Guard player has 14.)
  //   3. Otherwise honour the manual selection.
  const effectiveRoleIdx = useMemo(() => {
    if (queryActive && hasQueryMatches) {
      const selectedRoleName = position.perspectives[selectedRoleIdx];
      const selectedRoleHits =
        (selectedRoleName &&
          queryMatchIndex.roleMatchCounts.get(selectedRoleName)) ||
        0;
      if (selectedRoleHits === 0) {
        const pivotIdx = position.perspectives.findIndex(
          (r) => (queryMatchIndex.roleMatchCounts.get(r) ?? 0) > 0,
        );
        if (pivotIdx >= 0) return pivotIdx;
      }
    }
    if (roleCounts[selectedRoleIdx] > 0) return selectedRoleIdx;
    const firstWithContent = roleCounts.findIndex((n) => n > 0);
    return firstWithContent >= 0 ? firstWithContent : selectedRoleIdx;
  }, [
    roleCounts,
    selectedRoleIdx,
    queryActive,
    hasQueryMatches,
    queryMatchIndex,
    position.perspectives,
  ]);
  const selectedRole = position.perspectives[effectiveRoleIdx] ?? '';

  // Count of techniques rendered for the CURRENTLY selected role —
  // the "Offensive transitions" heading is deliberately EXCLUDED
  // from this list because transitions render as their own
  // distinct "Transitions out" block below (tappable cross-tree
  // navigation), not as plain technique bullets. When a progress
  // filter is active, techs are additionally filtered to only
  // those matching the selected progress state.
  const headingsWithContent = useMemo(() => {
    return position.headings
      .filter((h) => h !== 'Offensive transitions')
      .map((h) => {
        let techs = techniquesForHeading(positionTechs, selectedRole, h);
        if (progressFilter) {
          techs = techs.filter((t) => {
            const key = buildTechniqueProgressKey(
              sectionLabel,
              position.name,
              selectedRole,
              h,
              t,
            );
            return progress[key] === progressFilter;
          });
        }
        return { heading: h, techs };
      })
      .filter((entry) => entry.techs.length > 0);
  }, [
    positionTechs,
    selectedRole,
    position.headings,
    progressFilter,
    progress,
    sectionLabel,
    position.name,
  ]);

  const totalForRole = headingsWithContent.reduce(
    (acc, e) => acc + e.techs.length,
    0,
  );

  // Outer wrapper ref — registered with the parent ScrollView so
  // cross-tree navigation jumps can measureLayout + scroll to this
  // card.
  const outerRef = useRef<RNView | null>(null);
  const handleOuterRef = useCallback(
    (ref: RNView | null) => {
      outerRef.current = ref;
      registerOuterRef(position.name, ref);
    },
    [position.name, registerOuterRef],
  );

  // React to cross-tree focus signal. When the user taps a
  // transition row elsewhere in the tree, the parent sets
  // focusTarget to this position's name; we auto-expand the card
  // and flash a gold border for ~1.8s so the user clearly sees
  // where they landed. The parent ScrollView separately measures
  // and scrolls to the card.
  useEffect(() => {
    if (focusTarget !== position.name) return;
    setExpanded(true);
    setJumpFlash(true);
    const t = setTimeout(() => setJumpFlash(false), 1800);
    return () => clearTimeout(t);
  }, [focusTarget, position.name]);

  useEffect(() => {
    if (coachingFocus?.position !== position.name) return;
    setExpanded(true);
    setJumpFlash(true);
    const flashTimer = setTimeout(() => setJumpFlash(false), 1800);

    const desiredRole = coachingFocus.role;
    if (desiredRole) {
      const roleIdx = position.perspectives.findIndex((role) => role === desiredRole);
      if (roleIdx >= 0) setSelectedRoleIdx(roleIdx);
    }

    const targetRole = desiredRole ?? position.perspectives[0] ?? null;
    const targetHeading = coachingFocus.heading;
    const targetTechnique = coachingFocus.technique;
    if (!targetRole || !targetHeading || !targetTechnique) {
      return () => clearTimeout(flashTimer);
    }

    const headingEntry = position.headings.find(
      (heading) => normalizeHeading(heading) === normalizeHeading(targetHeading),
    );
    if (!headingEntry) {
      return () => clearTimeout(flashTimer);
    }

    const techs = techniquesForHeading(positionTechs, targetRole, headingEntry);
    const techIdx = techs.findIndex((label) => label === targetTechnique);
    if (techIdx < 0) {
      return () => clearTimeout(flashTimer);
    }

    const techKey = `${targetRole}|${headingEntry}|${techIdx}`;
    setExpandedTechKey(techKey);
    setCoachingFlashTechKey(techKey);
    onConsumeCoachingFocus();
    const rowTimer = setTimeout(() => setCoachingFlashTechKey(null), 2600);
    return () => {
      clearTimeout(flashTimer);
      clearTimeout(rowTimer);
    };
  }, [
    coachingFocus,
    position.name,
    position.perspectives,
    position.headings,
    positionTechs,
    onConsumeCoachingFocus,
  ]);

  // Auto-expand when a progress filter is active so filtered items
  // are visible immediately without the user having to tap every
  // card. When the filter clears, user expansion state is preserved
  // (we only set expanded=true, we never force collapse).
  useEffect(() => {
    if (progressFilter) setExpanded(true);
  }, [progressFilter]);

  // Auto-expand on a search-match the same way. Without this, a
  // user typing "armbar" would see Closed guard surface in the
  // results list (because parseTransitionEdges has armbar in
  // there) but the card would still be collapsed and they'd have
  // to tap to see why it matched. Combined with the role-pivot
  // rule above, the matching row is always one render away from
  // the search input.
  useEffect(() => {
    if (hasQueryMatches) setExpanded(true);
  }, [hasQueryMatches]);

  // Parsed offensive-transition edges for the currently selected
  // role. Derived from whatever "Offensive transitions" entries the
  // web data already carries for this (position, perspective)
  // tuple — no second parallel dataset, no invented content. When
  // a progress filter is active, edges are additionally filtered
  // to only those matching the selected progress state.
  const transitionsForRole = useMemo(() => {
    const raw = techniquesForHeading(
      positionTechs,
      selectedRole,
      'Offensive transitions',
    );
    let edges = parseTransitionEdges(raw);
    if (progressFilter) {
      edges = edges.filter((edge) => {
        const key = buildTransitionProgressKey(
          sectionLabel,
          position.name,
          selectedRole,
          edge.label,
          edge.destination,
        );
        return progress[key] === progressFilter;
      });
    }
    return edges;
  }, [
    positionTechs,
    selectedRole,
    progressFilter,
    progress,
    sectionLabel,
    position.name,
  ]);

  // Per-position aggregate progress counts. Derived from a single
  // pass over the persisted progress map, scoped by storage-key
  // prefix to keys rooted at THIS position (techniques + outbound
  // transitions). Inbound edges are intentionally excluded — they
  // belong to the source position's prefix, not this one — so
  // section-wide totals stay consistent and an edge isn't double-
  // counted on its destination card. Drives the small colored
  // count chips rendered on the collapsed header so users can scan
  // a section and immediately see which positions they've actually
  // been working on, without having to expand every card.
  const positionProgressCounts = useMemo(() => {
    const techPrefix = `tech|${sectionLabel}|${position.name}|`;
    const txPrefix = `tx|${sectionLabel}|${position.name}|`;
    const counts = { drilling: 0, learned: 0, tracking: 0 };
    for (const key of Object.keys(progress)) {
      if (!key.startsWith(techPrefix) && !key.startsWith(txPrefix)) continue;
      const v = progress[key];
      if (v === 'drilling') counts.drilling++;
      else if (v === 'learned') counts.learned++;
      else if (v === 'tracking') counts.tracking++;
    }
    return counts;
  }, [progress, sectionLabel, position.name]);
  const positionProgressTotal =
    positionProgressCounts.drilling +
    positionProgressCounts.learned +
    positionProgressCounts.tracking;

  // Inbound transition edges — every source position that feeds
  // INTO this position. Derived once at module load and stable
  // across renders, so this useMemo is a single ReadonlyMap lookup
  // (plus an optional progress filter pass). Returns an empty
  // array when the position is not a destination for any
  // transition (so the header chip + block both hide).
  const inboundEdges = useMemo(() => {
    const edges = INBOUND_TRANSITIONS.get(position.name) ?? [];
    if (!progressFilter) return edges;
    return edges.filter((e) => {
      const srcSection =
        SECTION_LABEL_BY_POSITION_NAME.get(e.sourceName) ?? '';
      const key = buildTransitionProgressKey(
        srcSection,
        e.sourceName,
        e.sourceRole,
        e.label,
        position.name,
      );
      return progress[key] === progressFilter;
    });
  }, [position.name, progressFilter, progress]);

  return (
    <RNView
      ref={handleOuterRef}
      style={[
        styles.positionWrap,
        jumpFlash && styles.positionWrapJumpFlash,
      ]}
      collapsable={false}>
      <Pressable
        style={styles.positionRow}
        onPress={() => {
          if (expanded) onDismissCoachRecommendation();
          setExpanded(!expanded);
        }}>
        <View style={{ flex: 1 }}>
          <Text style={styles.positionName}>
            {position.name}
            {position.built_out ? (
              <Text style={styles.builtBadge}> · built out</Text>
            ) : null}
            {inboundEdges.length > 0 ? (
              <Text style={styles.inboundChip}>
                {'  '}← {inboundEdges.length} inbound
              </Text>
            ) : null}
            {/* Search-match chip — surfaces "this card is in the
                results because of N hits inside it" so the user
                isn't confused when "armbar" matches Closed guard
                even though "armbar" doesn't appear anywhere in
                the title. Only renders when the match came from
                content (not from the position name itself), since
                a name match needs no explanation. */}
            {queryActive &&
              hasQueryMatches &&
              !position.name.toLowerCase().includes(query.trim().toLowerCase()) ? (
              <Text style={styles.searchMatchChip}>
                {'  '}⌕ {queryMatchIndex.total} match
                {queryMatchIndex.total === 1 ? '' : 'es'}
              </Text>
            ) : null}
            {/* Per-position progress chips — render only the
                statuses that have at least one flagged item rooted
                at this position so the header stays quiet on
                untouched cards but lights up the moment you start
                investing study time. Each chip uses the same
                colour as the corresponding ProgressPill so the
                visual language is consistent across the screen
                (drilling=blue, learned=green, tracking=yellow). */}
            {positionProgressTotal > 0 ? (
              <Text style={styles.positionProgressChip}>
                {positionProgressCounts.drilling > 0 ? (
                  <Text style={styles.positionProgressDrilling}>
                    {'  '}● {positionProgressCounts.drilling}
                  </Text>
                ) : null}
                {positionProgressCounts.learned > 0 ? (
                  <Text style={styles.positionProgressLearned}>
                    {'  '}● {positionProgressCounts.learned}
                  </Text>
                ) : null}
                {positionProgressCounts.tracking > 0 ? (
                  <Text style={styles.positionProgressTracking}>
                    {'  '}● {positionProgressCounts.tracking}
                  </Text>
                ) : null}
              </Text>
            ) : null}
          </Text>
          {/* Role toggles — real pressable pills when there are multiple
              perspectives, static text when there's only one (the seed
              type enforces 2 today but the UI stays robust to future
              single-role positions). Tapping a pill selects that role
              without toggling the expand state. */}
          {hasMultipleRoles ? (
            <View style={styles.rolePillRow}>
              {position.perspectives.map((role, idx) => {
                const isActive = idx === effectiveRoleIdx;
                const count = roleCounts[idx];
                const isEmpty = count === 0;
                return (
                  <Pressable
                    key={role}
                    style={[
                      styles.rolePill,
                      isActive && styles.rolePillActive,
                      isEmpty && !isActive && styles.rolePillEmpty,
                    ]}
                    onPress={(ev) => {
                      ev.stopPropagation();
                      onDismissCoachRecommendation();
                      setSelectedRoleIdx(idx);
                      setExpandedTechKey(null);
                      if (!expanded) setExpanded(true);
                    }}>
                    <Text
                      style={[
                        styles.rolePillText,
                        isActive && styles.rolePillTextActive,
                        isEmpty && !isActive && styles.rolePillTextEmpty,
                      ]}>
                      {role}
                      {count > 0 && (
                        <Text style={styles.rolePillCount}>{'  '}{count}</Text>
                      )}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          ) : (
            <Text style={styles.positionPersp}>{selectedRole}</Text>
          )}
        </View>
        <Text style={styles.chevron}>{expanded ? '▾' : '▸'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.positionDetail}>
          {hasMultipleRoles && (
            <Text style={styles.viewingAs}>
              Viewing as <Text style={styles.viewingAsName}>{selectedRole}</Text>
              {totalForRole > 0 && (
                <Text style={styles.viewingAsCount}>
                  {' '}· {totalForRole} technique{totalForRole === 1 ? '' : 's'}
                </Text>
              )}
            </Text>
          )}

          {/* Real techniques — grouped by heading. Each row is
              pressable: tapping expands a lightweight inline detail
              block below it showing the full "position → role →
              heading → name" breadcrumb and a "View in full map"
              action that opens the website Reference at this
              position. Headings with zero content are hidden. */}
          {headingsWithContent.length > 0 ? (
            headingsWithContent.map(({ heading, techs }) => (
              <View key={heading} style={styles.headingBlock}>
                <Text style={styles.headingLabel}>
                  {heading}
                  <Text style={styles.headingLabelCount}>
                    {'  '}{techs.length}
                  </Text>
                </Text>
                {techs.map((t, i) => {
                  const techKey = `${selectedRole}|${heading}|${i}`;
                  const isOpen = expandedTechKey === techKey;
                  const progressKey = buildTechniqueProgressKey(
                    sectionLabel,
                    position.name,
                    selectedRole,
                    heading,
                    t,
                  );
                  const rowStatus = progress[progressKey] ?? 'none';
                  // Search-match accent — gold left border + faint
                  // gold background, applied in addition to (not
                  // instead of) the existing progress accent so a
                  // technique that's both flagged AND a search
                  // match still reads as flagged. The progress
                  // accent uses a 3px left border and the search
                  // accent overlays a 2px right border so neither
                  // signal hides the other.
                  const isQueryMatch =
                    queryActive && queryMatchIndex.techKeys.has(techKey);
                  const isCoachingMatch = coachingFlashTechKey === techKey;
                  const isCoachRecommendedDetail =
                    coachRecommendedTarget?.position === position.name &&
                    (coachRecommendedTarget.role ?? selectedRole) === selectedRole &&
                    coachRecommendedTarget?.technique === t &&
                    coachRecommendedTarget?.heading != null &&
                    normalizeHeading(coachRecommendedTarget.heading) ===
                      normalizeHeading(heading);
                  return (
                    <View key={techKey}>
                      <Pressable
                        style={[
                          styles.techniqueRow,
                          isOpen && styles.techniqueRowOpen,
                          rowStatus === 'drilling' && styles.rowAccentDrilling,
                          rowStatus === 'learned' && styles.rowAccentLearned,
                          rowStatus === 'tracking' && styles.rowAccentTracking,
                          isQueryMatch && styles.rowAccentSearchMatch,
                          isCoachingMatch && styles.rowAccentCoachingTarget,
                        ]}
                        onPress={() => {
                          const nextExpandedTechKey = isOpen ? null : techKey;
                          if (!nextExpandedTechKey || !isCoachRecommendedDetail) {
                            onDismissCoachRecommendation();
                          }
                          setExpandedTechKey(nextExpandedTechKey);
                        }}>
                        <Text style={styles.techniqueItem}>
                          • {t}
                        </Text>
                        <NoteIndicator progressKey={progressKey} />
                        <ProgressPill progressKey={progressKey} />
                        <Text style={styles.techniqueChevron}>
                          {isOpen ? '▾' : '▸'}
                        </Text>
                      </Pressable>
                      {isOpen && (
                        <View style={styles.techniqueDetail}>
                          {isCoachRecommendedDetail && (
                            <View style={styles.coachRecommendedBlock}>
                              <View style={styles.coachRecommendedBadge}>
                                <Text style={styles.coachRecommendedBadgeText}>
                                  Recommended by coach
                                </Text>
                              </View>
                              {coachRecommendedTarget?.reason ? (
                                <Text style={styles.coachRecommendedReason}>
                                  Why: {coachRecommendedTarget.reason}
                                </Text>
                              ) : null}
                            </View>
                          )}
                          <Text style={styles.techniqueDetailCrumb}>
                            {position.name}
                            {' '}·{' '}
                            <Text style={styles.techniqueDetailCrumbRole}>
                              {selectedRole}
                            </Text>
                            {' '}·{' '}
                            {heading}
                          </Text>
                          <Text style={styles.techniqueDetailName}>{t}</Text>
                          {(() => {
                            const videoTargetId = findTechniqueVideoTargetId({
                              belt: currentBelt,
                              position: position.name,
                              role: selectedRole,
                              heading,
                              technique: t,
                            });
                            const videoState = deriveTechniqueVideoDisplayState(
                              (videoTargetId
                                ? videoByTargetId.get(videoTargetId)
                                : null) ?? fallbackVideoAttachmentSummary(progressKey),
                              { playbackFailed: Boolean(playbackFailedKeys[progressKey]) },
                            );
                            const handleOpenVideo = async () => {
                              if (!videoState.ctaUrl) return;
                              try {
                                await Linking.openURL(videoState.ctaUrl);
                              } catch {
                                setPlaybackFailedKeys((current) => ({
                                  ...current,
                                  [progressKey]: true,
                                }));
                                Alert.alert(
                                  'Playback failed',
                                  'Use the 3D map for the full technique path.',
                                );
                              }
                            };
                            return (
                              <>
                          <View style={styles.techniqueVideoStatePill}>
                            <Text style={styles.techniqueVideoStatePillText}>
                              {videoState.badge}
                            </Text>
                          </View>
                          <Text style={styles.techniqueDetailMeta}>
                            {videoState.note}
                          </Text>
                          {position.built_out ? (
                            <Text style={styles.techniqueDetailMeta}>
                              Explore full details and transitions in the 3D map.
                            </Text>
                          ) : null}
                          {/* Inline note editor — saves to the
                              progress store on blur. Local draft
                              prevents per-keystroke re-renders
                              outside this single subtree. Notes
                              can attach to any tech row whether
                              or not it's been flagged. */}
                          <NoteEditor progressKey={progressKey} />
                          {videoState.ctaLabel ? (
                            <Pressable
                              style={styles.techniqueDetailBridgeBtn}
                              onPress={handleOpenVideo}>
                              <Text style={styles.techniqueDetailBridgeBtnText}>
                                {videoState.ctaLabel}
                              </Text>
                            </Pressable>
                          ) : null}
                          <Pressable
                            style={styles.techniqueDetailBridgeBtn}
                            onPress={() =>
                              openFullMap({
                                section: sectionLabel,
                                position: position.name,
                                role: selectedRole,
                                heading,
                                technique: t,
                              })
                            }>
                            <Text style={styles.techniqueDetailBridgeBtnText}>
                              Open technique in 3D map
                            </Text>
                          </Pressable>
                              </>
                            );
                          })()}
                        </View>
                      )}
                    </View>
                  );
                })}
              </View>
            ))
          ) : anyContent && hasMultipleRoles ? (
            <Text style={styles.emptyNote}>
              No techniques catalogued for {selectedRole} yet — try the
              other role.
            </Text>
          ) : (
            <Text style={styles.emptyNote}>
              No techniques catalogued for this position yet. Content
              flows from the website OPML pipeline.
            </Text>
          )}

          {/* Transitions out — arrow-format "label → destination"
              rows parsed from the Offensive transitions heading.
              Only rendered when at least one edge exists for the
              current role. Each row is a tappable link that jumps
              the mobile Reference tree to the destination position's
              card when the destination resolves to a known mobile-
              seed position. Non-navigable destinations (submissions,
              non-canonical names) render as muted italic rows that
              preserve the information without claiming a jump path. */}
          {transitionsForRole.length > 0 && (
            <View style={styles.transitionsBlock}>
              <Text style={styles.transitionsLabel}>
                Transitions out
                <Text style={styles.transitionsLabelCount}>
                  {'  '}{transitionsForRole.length}
                </Text>
              </Text>
              {transitionsForRole.map((edge, i) => {
                const navigable = edge.destinationKnown;
                // Outbound edges are rooted at THIS position/role;
                // the transition-progress key uses (sectionLabel,
                // position.name, selectedRole, label, destination).
                // Inbound rendering below reuses the same key for
                // the same edge so marking on either side reflects
                // on both.
                const progressKey = buildTransitionProgressKey(
                  sectionLabel,
                  position.name,
                  selectedRole,
                  edge.label,
                  edge.destination,
                );
                const rowStatus = progress[progressKey] ?? 'none';
                const transitionMatchKey = `${selectedRole}|${edge.label}|${edge.destination}`;
                const isQueryMatch =
                  queryActive &&
                  queryMatchIndex.transitionKeys.has(transitionMatchKey);
                return (
                  <Pressable
                    key={`${edge.label}|${edge.destination}|${i}`}
                    style={[
                      styles.transitionRow,
                      !navigable && styles.transitionRowMuted,
                      rowStatus === 'drilling' && styles.rowAccentDrilling,
                      rowStatus === 'learned' && styles.rowAccentLearned,
                      rowStatus === 'tracking' && styles.rowAccentTracking,
                      isQueryMatch && styles.rowAccentSearchMatch,
                    ]}
                    disabled={!navigable}
                    onPress={() => {
                      if (navigable) {
                        onDismissCoachRecommendation();
                        onRequestFocus(edge.destination);
                      }
                    }}>
                    <Text style={styles.transitionLabel}>{edge.label}</Text>
                    <Text style={styles.transitionArrow}>→</Text>
                    <Text
                      style={[
                        styles.transitionDest,
                        navigable && styles.transitionDestNavigable,
                      ]}>
                      {edge.destination}
                    </Text>
                    <NoteIndicator progressKey={progressKey} />
                    <ProgressPill progressKey={progressKey} />
                  </Pressable>
                );
              })}
            </View>
          )}

          {/* Coming in from — inverse transition view. Source
              positions that feed INTO this position (derived once
              at module load from REFERENCE_TECHNIQUES). Each row
              is a tappable back-jump that reuses the same
              cross-tree navigation model as Transitions out:
              onRequestFocus(source), card auto-expands, scrolls,
              flashes. Not role-filtered on the destination side —
              the set of inbound sources is a property of the
              position as a graph node, not of the role you're
              currently viewing. Hidden entirely when empty. */}
          {inboundEdges.length > 0 && (
            <View style={styles.inboundBlock}>
              <Text style={styles.inboundBlockLabel}>
                Coming in from
                <Text style={styles.inboundBlockLabelCount}>
                  {'  '}{inboundEdges.length}
                </Text>
              </Text>
              {inboundEdges.map((edge, i) => {
                // Look up the source position's section so the
                // inbound key matches the corresponding outbound
                // key built on the source-side render. Falls back
                // to empty string on the rare case a source
                // position isn't in the mobile seed (shouldn't
                // happen since INBOUND_TRANSITIONS is gated on
                // KNOWN_POSITION_NAMES at build time).
                const sourceSectionLabel =
                  SECTION_LABEL_BY_POSITION_NAME.get(edge.sourceName) ?? '';
                const progressKey = buildTransitionProgressKey(
                  sourceSectionLabel,
                  edge.sourceName,
                  edge.sourceRole,
                  edge.label,
                  position.name,
                );
                const rowStatus = progress[progressKey] ?? 'none';
                return (
                  <Pressable
                    key={`${edge.sourceName}|${edge.label}|${i}`}
                    style={[
                      styles.inboundRow,
                      rowStatus === 'drilling' && styles.rowAccentDrilling,
                      rowStatus === 'learned' && styles.rowAccentLearned,
                      rowStatus === 'tracking' && styles.rowAccentTracking,
                    ]}
                    onPress={() => {
                      onDismissCoachRecommendation();
                      onRequestFocus(edge.sourceName);
                    }}>
                    <Text style={styles.inboundSource}>
                      {edge.sourceName}
                    </Text>
                    <Text style={styles.inboundArrow}>←</Text>
                    <Text style={styles.inboundLabel}>{edge.label}</Text>
                    <NoteIndicator progressKey={progressKey} />
                    <ProgressPill progressKey={progressKey} />
                  </Pressable>
                );
              })}
            </View>
          )}

          {/* Position-level full-map bridge. Always rendered on
              expanded positions so the separation between mobile
              Reference and the full 3D map feels intentional,
              not like a missing feature. */}
          <Pressable
            style={styles.positionBridgeBtn}
            onPress={() =>
              openFullMap({
                section: sectionLabel,
                position: position.name,
              })
            }>
            <Text style={styles.positionBridgeBtnText}>
              Open {position.name} in 3D map
            </Text>
          </Pressable>
        </View>
      )}
    </RNView>
  );
}

function SectionBlock({
  section,
  filter,
  builtOutOnly,
  focusTarget,
  onRequestFocus,
  registerOuterRef,
  progressFilter,
  query,
  coachingFocus,
  coachRecommendedTarget,
  onDismissCoachRecommendation,
  onConsumeCoachingFocus,
  currentBelt,
  videoByTargetId,
}: {
  section: ReferenceSection;
  filter: string;
  builtOutOnly: boolean;
  focusTarget: string | null;
  onRequestFocus: (destination: string) => void;
  registerOuterRef: (name: string, ref: RNView | null) => void;
  progressFilter: ProgressStatus | null;
  /** Same value as `filter` — passed through to PositionRow so
   *  the row can run the structured search-match index for
   *  per-row highlights and role-pivot logic. Kept as a separate
   *  prop name purely for clarity at the call site. */
  query: string;
  coachingFocus: CoachingTechniqueFocus | null;
  coachRecommendedTarget: CoachRecommendedTechniqueTarget | null;
  onDismissCoachRecommendation: () => void;
  onConsumeCoachingFocus: () => void;
  currentBelt: BeltLevel | null;
  videoByTargetId: ReadonlyMap<string, VideoAttachmentSummary>;
}) {
  // Read the progress store here so filter-induced visibility
  // checks react when a user marks/unmarks an item while a
  // progress filter is active. Only used in the progress-filter
  // branch of the filter closure below.
  const progress = useReferenceProgressStore((s) => s.progress);

  const filtered = useMemo(() => {
    return section.positions.filter((p) => {
      if (builtOutOnly && !p.built_out) return false;
      // Search match — now content-aware. Falls through to
      // positionMatchesQuery which checks position name AND every
      // catalogued technique/transition label inside via the
      // precomputed POSITION_SEARCH_HAYSTACK. Empty filter always
      // passes.
      if (!positionMatchesQuery(p.name, filter)) return false;
      if (progressFilter) {
        if (!positionHasMatchingProgress(p, progress, progressFilter)) {
          return false;
        }
      }
      return true;
    });
  }, [section.positions, filter, builtOutOnly, progressFilter, progress]);

  // Section-scope aggregate progress counts. Single prefix-scan
  // pass over the persisted progress map, scoped to keys rooted
  // in this section (technique + outbound transition keys both
  // start with `<kind>|<sectionLabel>|`). Drives the small
  // colored count strip in the section header so users get a
  // mid-tier readout between the global summary strip at the top
  // of the screen and the per-position chips inside each card.
  // The per-section view is intentionally NOT filter-aware — it
  // reflects what you've flagged in the whole section, not what's
  // currently visible under the active query/filter, so the
  // numbers stay stable as you peel filters on and off and a
  // hidden card never silently subtracts from the section's
  // sense of "where am I invested".
  const sectionProgressCounts = useMemo(() => {
    const techPrefix = `tech|${section.label}|`;
    const txPrefix = `tx|${section.label}|`;
    const counts = { drilling: 0, learned: 0, tracking: 0 };
    for (const key of Object.keys(progress)) {
      if (!key.startsWith(techPrefix) && !key.startsWith(txPrefix)) continue;
      const v = progress[key];
      if (v === 'drilling') counts.drilling++;
      else if (v === 'learned') counts.learned++;
      else if (v === 'tracking') counts.tracking++;
    }
    return counts;
  }, [progress, section.label]);
  const sectionProgressTotal =
    sectionProgressCounts.drilling +
    sectionProgressCounts.learned +
    sectionProgressCounts.tracking;

  if (filtered.length === 0) return null;

  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.sectionTitle}>{section.label}</Text>
          <Text style={styles.sectionDescription}>{section.description}</Text>
          {/* Section-level progress strip — small colored count
              chips below the description, mirroring the per-
              position chip language. Only renders when at least
              one item in the section has been flagged so brand-
              new sections stay quiet. Each chip shows only when
              its status has at least one entry, so a section
              you've only drilled (no learned/tracking) shows a
              single blue dot instead of three pills with two
              zeroes. Completes the tiered progress visibility
              model: top-of-screen summary → section header →
              position header → row pill. */}
          {sectionProgressTotal > 0 && (
            <View style={styles.sectionProgressStrip}>
              {sectionProgressCounts.drilling > 0 && (
                <Text style={styles.sectionProgressDrilling}>
                  ● {sectionProgressCounts.drilling} drilling
                </Text>
              )}
              {sectionProgressCounts.learned > 0 && (
                <Text style={styles.sectionProgressLearned}>
                  ● {sectionProgressCounts.learned} learned
                </Text>
              )}
              {sectionProgressCounts.tracking > 0 && (
                <Text style={styles.sectionProgressTracking}>
                  ● {sectionProgressCounts.tracking} tracking
                </Text>
              )}
            </View>
          )}
        </View>
        <View style={styles.sectionCountBlock}>
          <Text style={styles.sectionCountValue}>{filtered.length}</Text>
          <Text style={styles.sectionCountLabel}>
            {filtered.length === 1 ? 'position' : 'positions'}
          </Text>
        </View>
      </View>
      <View style={styles.positionsList}>
        {filtered.map((p) => (
        <PositionRow
          key={p.name}
          position={p}
          sectionLabel={section.label}
          focusTarget={focusTarget}
          onRequestFocus={onRequestFocus}
          registerOuterRef={registerOuterRef}
          progressFilter={progressFilter}
          query={query}
          coachingFocus={coachingFocus}
          coachRecommendedTarget={coachRecommendedTarget}
          onDismissCoachRecommendation={onDismissCoachRecommendation}
          onConsumeCoachingFocus={onConsumeCoachingFocus}
          currentBelt={currentBelt}
          videoByTargetId={videoByTargetId}
        />
        ))}
      </View>
    </View>
  );
}

export default function ReferenceScreen() {
  const { profile } = useProfile();
  const currentBelt = isBeltLevel(profile?.current_belt) ? profile.current_belt : null;
  const { byTargetId: videoByTargetId } = useVideoAttachmentSummaries(currentBelt);
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{
    focus?: string | string[];
    focusRole?: string | string[];
    focusHeading?: string | string[];
    focusTechnique?: string | string[];
    focusReason?: string | string[];
    focusSource?: string | string[];
    focusNonce?: string | string[];
  }>();
  const consumedRouteFocusRef = useRef<string | null>(null);
  const [coachingFocus, setCoachingFocus] = useState<CoachingTechniqueFocus | null>(
    null,
  );
  const [coachRecommendedTarget, setCoachRecommendedTarget] =
    useState<CoachRecommendedTechniqueTarget | null>(null);
  const [query, setQuery] = useState('');
  // Built-out filter — when on, hides positions that are not yet
  // built out on the website. Reuses the same built_out flag the
  // pill badges use so the two signals stay consistent.
  const [builtOutOnly, setBuiltOutOnly] = useState(false);

  // Cross-tree navigation — set by PositionRow transition rows via
  // onRequestFocus, consumed by the target PositionRow's focus
  // effect. Cleared on a short delay so subsequent taps on the same
  // destination still re-fire the effect.
  const [focusTarget, setFocusTarget] = useState<string | null>(null);

  // Escape-hatch note shown when a transition jump had to clear
  // search and/or disable the Built-out filter so the destination
  // card could mount and receive focus. Null when no escape was
  // needed. Auto-dismisses via a timeout so the note never lingers.
  const [filterEscapeNote, setFilterEscapeNote] = useState<string | null>(null);

  // Progress-state filter — when set, the Reference view shows only
  // techniques/transitions whose stored progress status matches.
  // Null means no filter (normal full view). Composes with the
  // existing search + built-out filter via AND.
  const [progressFilter, setProgressFilter] = useState<ProgressStatus | null>(
    null,
  );

  // Aggregate counts across the entire persisted progress store.
  // Derived from Object.values so each storage key contributes
  // exactly once — transitions tracked from source side and shown
  // on both source/destination UI surfaces never double-count in
  // the screen-top strip.
  const progressMap = useReferenceProgressStore((s) => s.progress);
  const notesMap = useReferenceProgressStore((s) => s.notes);
  const updatedAtMap = useReferenceProgressStore((s) => s.updatedAt);
  const importProgress = useReferenceProgressStore((s) => s.importProgress);

  // Import pane state. `importPaneOpen` gates visibility of the
  // inline paste-and-apply panel. `importText` is the user's
  // pasted payload. `importResultNote` is a transient confirmation
  // sentence shown after a successful import so the user knows
  // how many entries landed. `importReplaceMode` gates the
  // destructive replace-all path behind a native Alert
  // confirmation when the user opts in.
  const [importPaneOpen, setImportPaneOpen] = useState(false);
  const [importText, setImportText] = useState('');
  const [importReplaceMode, setImportReplaceMode] = useState(false);
  const [importResultNote, setImportResultNote] = useState<string | null>(
    null,
  );
  const progressCounts = useMemo(() => {
    const c = { drilling: 0, learned: 0, tracking: 0 };
    for (const v of Object.values(progressMap)) {
      if (v === 'drilling') c.drilling++;
      else if (v === 'learned') c.learned++;
      else if (v === 'tracking') c.tracking++;
    }
    return c;
  }, [progressMap]);
  const totalProgressItems =
    progressCounts.drilling + progressCounts.learned + progressCounts.tracking;

  // Outer scroll container ref + per-position native wrapper refs.
  // measureLayout off the position ref against the scroll container
  // gives us a y offset in the scroll coordinate space so we can
  // smoothly scroll the target card into view regardless of how
  // deep it is inside the section hierarchy.
  const scrollViewRef = useRef<ScrollView>(null);
  const positionRefs = useRef<Map<string, RNView>>(new Map());

  const registerOuterRef = useCallback(
    (name: string, ref: RNView | null) => {
      if (ref) {
        positionRefs.current.set(name, ref);
      } else {
        positionRefs.current.delete(name);
      }
    },
    [],
  );

  const handleRequestFocus = useCallback(
    (destination: string) => {
      setCoachRecommendedTarget(null);
      // Filter / search escape hatch — before kicking off the jump,
      // check whether the destination card would actually be mounted
      // under the current filter/search state. If not, clear the
      // minimum set of state needed to make it visible, show a brief
      // explanatory note so the user understands why the filters
      // changed, then fall through to the normal jump path.
      //
      // This fixes the one remaining silent no-op in the transition
      // system: prior to this batch, a user with "Built out only"
      // toggled on who tapped a transition pointing at a
      // not-yet-built-out position (or a search query mismatching
      // the destination) would see nothing happen — the
      // positionRefs.current.get(destination) lookup inside the
      // jump effect would return undefined because SectionBlock had
      // filtered that card out.
      const targetPos = POSITION_BY_NAME.get(destination);
      if (!targetPos) {
        // Destination not in the mobile seed at all — shouldn't
        // happen since transition rows are only enabled when
        // destinationKnown is true, but we fail safe here and skip
        // the jump instead of changing filters for nothing.
        return;
      }
      const q = query.trim().toLowerCase();
      const hiddenBySearch =
        q.length > 0 && !positionMatchesQuery(destination, query);
      const hiddenByBuiltOut = builtOutOnly && !targetPos.built_out;
      const hiddenByProgress =
        progressFilter != null &&
        !positionHasMatchingProgress(targetPos, progressMap, progressFilter);
      let escapeNote: string | null = null;
      if (hiddenBySearch && hiddenByBuiltOut && hiddenByProgress) {
        setQuery('');
        setBuiltOutOnly(false);
        setProgressFilter(null);
        escapeNote = `Cleared search, Built-out filter, and progress filter to reach ${destination}.`;
      } else if (hiddenBySearch && hiddenByBuiltOut) {
        setQuery('');
        setBuiltOutOnly(false);
        escapeNote = `Cleared search and turned off Built-out filter to reach ${destination}.`;
      } else if (hiddenBySearch && hiddenByProgress) {
        setQuery('');
        setProgressFilter(null);
        escapeNote = `Cleared search and progress filter to reach ${destination}.`;
      } else if (hiddenByBuiltOut && hiddenByProgress) {
        setBuiltOutOnly(false);
        setProgressFilter(null);
        escapeNote = `Turned off Built-out filter and cleared progress filter to reach ${destination}.`;
      } else if (hiddenBySearch) {
        setQuery('');
        escapeNote = `Cleared search to reach ${destination}.`;
      } else if (hiddenByBuiltOut) {
        setBuiltOutOnly(false);
        escapeNote = `Turned off Built-out filter to reach ${destination}.`;
      } else if (hiddenByProgress) {
        setProgressFilter(null);
        escapeNote = `Cleared progress filter to reach ${destination}.`;
      }
      if (escapeNote) setFilterEscapeNote(escapeNote);

      // Always set to null first so the useEffect subscription in
      // the destination PositionRow re-fires even when the user taps
      // two transition rows pointing to the same destination back-to-
      // back. Without this, React's reference-equality check would
      // swallow the second event. Delay bumped to 50ms when filters
      // were cleared so React has time to commit the state updates
      // and re-render the (now-visible) destination card before the
      // focus effect tries to measureLayout it.
      const jumpDelay = escapeNote ? 80 : 0;
      setFocusTarget(null);
      setTimeout(() => setFocusTarget(destination), jumpDelay);
    },
    [query, builtOutOnly, progressFilter, progressMap],
  );

  useEffect(() => {
    const routeFocus = Array.isArray(params.focus)
      ? params.focus[0]
      : params.focus;
    const routeRole = Array.isArray(params.focusRole)
      ? params.focusRole[0]
      : params.focusRole;
    const routeHeading = Array.isArray(params.focusHeading)
      ? params.focusHeading[0]
      : params.focusHeading;
    const routeTechnique = Array.isArray(params.focusTechnique)
      ? params.focusTechnique[0]
      : params.focusTechnique;
    const routeReason = Array.isArray(params.focusReason)
      ? params.focusReason[0]
      : params.focusReason;
    const routeSource = Array.isArray(params.focusSource)
      ? params.focusSource[0]
      : params.focusSource;
    const routeNonce = Array.isArray(params.focusNonce)
      ? params.focusNonce[0]
      : params.focusNonce;
    const routeKey = [
      routeFocus ?? '',
      routeRole ?? '',
      routeHeading ?? '',
      routeTechnique ?? '',
      routeNonce ?? '',
    ].join('|');
    if (!routeFocus) {
      consumedRouteFocusRef.current = null;
      return;
    }
    if (routeKey === consumedRouteFocusRef.current) return;
    consumedRouteFocusRef.current = routeKey;
    setCoachingFocus({
      position: routeFocus,
      role: routeRole ?? null,
      heading: routeHeading ?? null,
      technique: routeTechnique ?? null,
    });
    handleRequestFocus(routeFocus);
    if (routeSource === 'coach') {
      setCoachRecommendedTarget({
        position: routeFocus,
        role: routeRole ?? null,
        heading: routeHeading ?? null,
        technique: routeTechnique ?? null,
        reason: routeReason ?? null,
      });
    } else {
      setCoachRecommendedTarget(null);
    }
    router.setParams({
      focus: undefined,
      focusRole: undefined,
      focusHeading: undefined,
      focusTechnique: undefined,
      focusReason: undefined,
      focusSource: undefined,
      focusNonce: undefined,
    });
  }, [
    params.focus,
    params.focusRole,
    params.focusHeading,
    params.focusTechnique,
    params.focusReason,
    params.focusSource,
    params.focusNonce,
    handleRequestFocus,
  ]);

  // Auto-dismiss the filter-escape note after 4.5s so it never
  // becomes permanent visual noise. The timer is scoped to each
  // fresh note so overlapping jumps reset the timer cleanly.
  useEffect(() => {
    if (!filterEscapeNote) return;
    const t = setTimeout(() => setFilterEscapeNote(null), 4500);
    return () => clearTimeout(t);
  }, [filterEscapeNote]);

  // Progress export share — builds a compact plain-text summary
  // of the user's stored Reference progress and opens the native
  // share sheet so they can send it to a coach / chat / notes
  // without requiring any backend sync. Behaviour is
  // scope-aware: when a progressFilter is active, the aggregate
  // summary is followed by a per-item breakdown of the filtered
  // status list, so the recipient sees "overall state AND this
  // specific list I'm currently looking at". Share rejection
  // (e.g. user dismisses the share sheet) is silently swallowed
  // since it's not an error.
  const handleShareProgress = useCallback(async () => {
    const text = buildProgressExportText(
      progressMap,
      progressCounts,
      progressFilter,
      notesMap,
      updatedAtMap,
    );
    try {
      await Share.share({
        message: text,
        title: 'Lauburu training status',
      });
    } catch {
      // Silent — RN Share.share only rejects on hard failure
      // (no share sheet available on device) which is rare on
      // iOS/Android simulators.
    }
  }, [progressMap, progressCounts, progressFilter, notesMap, updatedAtMap]);

  // Import open/close/apply handlers. The user-facing flow is:
  //   1. Tap "Import ↓" on the summary strip → opens inline
  //      pastebox panel below the strip.
  //   2. Paste the exported payload (full text export OR bare
  //      JSON block) into the textarea.
  //   3. A live preview line parses the current text and shows
  //      "Found N entries" or "Couldn't read that payload".
  //   4. Tap "Apply import" → merges entries into the local
  //      progress store (existing keys are overwritten on
  //      conflict, other keys survive), shows a confirmation
  //      count, auto-closes the pane after 3.5s.
  // Close-without-applying leaves the pastebox state intact so
  // the user can reopen without re-pasting, but resets the
  // destructive replace toggle so reopening always defaults to
  // the safer merge path.
  const handleToggleImport = useCallback(() => {
    setImportPaneOpen((v) => {
      if (v) setImportReplaceMode(false);
      else setImportResultNote(null);
      return !v;
    });
  }, []);

  const handleImportTextChange = useCallback((text: string) => {
    setImportText(text);
    setImportResultNote(null);
  }, []);

  const handleToggleImportReplaceMode = useCallback(() => {
    setImportReplaceMode((v) => !v);
    setImportResultNote(null);
  }, []);

  /**
   * Commit a parsed payload to the store via the requested mode.
   * Pulled out of handleApplyImport so both the direct merge
   * path and the Alert-confirmed replace path share identical
   * completion behaviour (result note, state cleanup, pane
   * close). Result note wording adapts to the mode so "replaced
   * local progress" reads clearly vs "merged on top of existing".
   * Now passes the FULL parsed payload through to the store so
   * v2 imports carry notes + timestamps; v1 payloads still work
   * because the store reads `payload.notes` / `payload.updated_at`
   * defensively (both undefined in v1).
   */
  const commitImport = useCallback(
    (payload: ProgressExportPayload, mode: 'merge' | 'replace') => {
      const result = importProgress(payload, mode);
      // Notes-included suffix — only mention when the v2 payload
      // actually carried notes, so v1 payload imports still read
      // exactly the same as before this batch.
      const notesSuffix =
        result.notesAdded > 0
          ? ` + ${result.notesAdded} note${result.notesAdded === 1 ? '' : 's'}`
          : '';
      if (mode === 'replace') {
        setImportResultNote(
          `Replaced local progress — ${result.added} entries now tracked${notesSuffix} (${result.skipped} skipped).`,
        );
      } else {
        setImportResultNote(
          `Imported ${result.added} new + ${result.updated} updated${notesSuffix} (${result.skipped} skipped).`,
        );
      }
      setImportText('');
      setImportReplaceMode(false);
      setImportPaneOpen(false);
    },
    [importProgress],
  );

  const handleApplyImport = useCallback(() => {
    const parsed = parseProgressImportPayload(importText);
    if (!parsed) {
      setImportResultNote(
        "Couldn't read that payload — paste the full text export or just the JSON block.",
      );
      return;
    }
    const keyCount = Object.keys(parsed.entries).length;
    if (keyCount === 0) {
      setImportResultNote(
        'Payload parsed, but contained zero valid entries.',
      );
      return;
    }

    // Replace mode is destructive — gate it behind a native
    // Alert.alert so the user has to positively confirm wiping
    // their existing local state. Cancel leaves the pane + the
    // pasted payload + the replace-mode checkbox intact so the
    // user can adjust without losing their paste.
    if (importReplaceMode) {
      Alert.alert(
        'Replace existing progress?',
        `This will wipe your current ${totalProgressItems} locally-tracked item${
          totalProgressItems === 1 ? '' : 's'
        } and install the ${keyCount} entr${
          keyCount === 1 ? 'y' : 'ies'
        } from the pasted payload in their place. Any local items not in the payload will be LOST.`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Replace',
            style: 'destructive',
            onPress: () => commitImport(parsed, 'replace'),
          },
        ],
      );
      return;
    }

    commitImport(parsed, 'merge');
  }, [importText, importReplaceMode, totalProgressItems, commitImport]);

  // Auto-dismiss the import result confirmation after 4.5s so
  // the note doesn't linger. Timer is scoped to the note's
  // identity so overlapping imports reset cleanly.
  useEffect(() => {
    if (!importResultNote) return;
    const t = setTimeout(() => setImportResultNote(null), 4500);
    return () => clearTimeout(t);
  }, [importResultNote]);

  // Whenever focusTarget changes, measureLayout the destination
  // card's native ref against the scroll container and scrollTo
  // its offset (with an 80px header breathing room). The target
  // card may expand in a sibling effect first, so we wait until
  // after layout has committed (double RAF) and retry a couple of
  // times if measureLayout still races the expansion. This keeps
  // recent-activity / hub / transition jumps landing reliably
  // without changing the visible jump behavior.
  useEffect(() => {
    if (!focusTarget) return;
    let cancelled = false;
    let frameA: number | null = null;
    let frameB: number | null = null;

    const measureAndScroll = (attempt: number) => {
      if (cancelled) return;
      const cardRef = positionRefs.current.get(focusTarget);
      const sv = scrollViewRef.current;
      if (!cardRef || !sv) return;
      const scrollContainerRef =
        typeof sv.getNativeScrollRef === 'function'
          ? sv.getNativeScrollRef()
          : null;
      if (!scrollContainerRef) return;
      try {
        cardRef.measureLayout(
          scrollContainerRef,
          (_x, y) => {
            if (cancelled) return;
            sv.scrollTo({
              y: Math.max(0, y - 80),
              animated: true,
            });
          },
          () => {
            // Layout may still be settling after the target card
            // expanded. Retry on the next frame a couple of times
            // before giving up silently.
            if (attempt < 2 && !cancelled) {
              frameA = requestAnimationFrame(() =>
                measureAndScroll(attempt + 1),
              );
            }
          },
        );
      } catch {
        if (attempt < 2 && !cancelled) {
          frameA = requestAnimationFrame(() =>
            measureAndScroll(attempt + 1),
          );
        }
      }
    };

    frameA = requestAnimationFrame(() => {
      frameB = requestAnimationFrame(() => {
        measureAndScroll(0);
      });
    });

    return () => {
      cancelled = true;
      if (frameA != null) cancelAnimationFrame(frameA);
      if (frameB != null) cancelAnimationFrame(frameB);
    };
  }, [focusTarget]);

  const totalFiltered = useMemo(() => {
    return REFERENCE_SECTIONS.reduce(
      (acc, s) =>
        acc +
        s.positions.filter((p) => {
          if (builtOutOnly && !p.built_out) return false;
          // Mirror SectionBlock's content-aware filter so the
          // active-filter banner's count agrees with what actually
          // renders below — if a position only matches because of
          // a technique inside, it still counts here.
          if (!positionMatchesQuery(p.name, query)) return false;
          if (progressFilter) {
            if (!positionHasMatchingProgress(p, progressMap, progressFilter)) {
              return false;
            }
          }
          return true;
        }).length,
      0,
    );
  }, [query, builtOutOnly, progressFilter, progressMap]);

  /**
   * Recent activity descriptor — one entry per recently-touched
   * progress key, sorted newest first, capped at RECENT_ACTIVITY_LIMIT.
   * Drives the Recent activity strip below the progress summary
   * row. Each entry carries everything the chip needs to render
   * without re-deriving (parsed key parts, status, target position
   * for the jump, formatted relative time).
   *
   * Built from `updatedAtMap` which is the union of "any key with
   * a status" and "any key with a note" — so a user who attaches
   * a note to an unflagged technique still sees that activity
   * surface here. Stale keys (parseProgressKey returns null) are
   * silently dropped so a malformed key from a corrupted import
   * never crashes the strip.
   *
   * Total dependency footprint: progress map, notes map, updated_at
   * map. The current-time component (which would otherwise tick
   * every minute and force re-renders) is intentionally NOT a
   * dependency — the relative time string is recomputed on each
   * full screen render, which happens often enough during normal
   * use that "5m ago" stays accurate without a setInterval.
   */
  const recentActivity = useMemo(() => {
    const RECENT_ACTIVITY_LIMIT = 5;
    type Entry = {
      key: string;
      iso: string;
      ts: number;
      status: ProgressStatus | null;
      hasNote: boolean;
      jumpTo: string;
      title: string;
      subtitle: string;
    };
    const entries: Entry[] = [];
    for (const [key, iso] of Object.entries(updatedAtMap)) {
      if (typeof iso !== 'string' || iso.length === 0) continue;
      const ts = Date.parse(iso);
      if (!Number.isFinite(ts)) continue;
      const parsed = parseProgressKey(key);
      if (!parsed) continue;
      const status = (progressMap[key] as ProgressStatus | undefined) ?? null;
      const hasNote =
        typeof notesMap[key] === 'string' && notesMap[key]!.length > 0;
      // Skip entries that have no status AND no note — these are
      // ghosts (timestamps left behind by a bug or by a clear-and-
      // resave race). Defensive but cheap.
      if (!status && !hasNote) continue;
      let jumpTo = '';
      let title = '';
      let subtitle = '';
      if (parsed.kind === 'tech') {
        jumpTo = parsed.position;
        title = parsed.label;
        subtitle = `${parsed.position} · ${parsed.heading}`;
      } else {
        jumpTo = parsed.sourcePosition;
        title = `${parsed.label} → ${parsed.destination}`;
        subtitle = parsed.sourcePosition;
      }
      entries.push({
        key,
        iso,
        ts,
        status,
        hasNote,
        jumpTo,
        title,
        subtitle,
      });
    }
    entries.sort((a, b) => b.ts - a.ts);
    return entries.slice(0, RECENT_ACTIVITY_LIMIT);
  }, [updatedAtMap, progressMap, notesMap]);

  return (
    <View style={styles.container}>
    <ScrollView
      ref={scrollViewRef}
      style={styles.scrollView}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Text style={styles.heading}>Reference</Text>
      </View>

      {/* Summary strip */}
      <View style={styles.summaryStrip}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{REFERENCE_TOTAL_POSITIONS}</Text>
          <Text style={styles.summaryLabel}>positions</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{REFERENCE_BUILT_OUT_COUNT}</Text>
          <Text style={styles.summaryLabel}>built out</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{REFERENCE_TECHNIQUE_COUNT}</Text>
          <Text style={styles.summaryLabel}>techniques</Text>
        </View>
      </View>

      {/* Top hubs — compact quick-jump strip showing the top N
          positions by combined inbound+outbound transition edge
          count. Each chip taps into the same onRequestFocus
          pipeline used by Transitions out and Coming in from,
          so jumps auto-expand + scroll + flash the destination
          card, and the filter-escape hatch automatically clears
          search / Built-out only when a hub is hidden by an
          active filter. Ranking is computed once at module load
          from INBOUND_TRANSITIONS + a deduped outbound scan —
          no per-render cost, fully deterministic. */}
      {TOP_HUBS.length > 0 && (
        <View style={styles.topHubsBlock}>
          <Text style={styles.topHubsLabel}>
            Top hubs
            <Text style={styles.topHubsLabelHint}>
              {'  '}most connected
            </Text>
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.topHubsRow}>
            {TOP_HUBS.map((hub) => (
              <Pressable
                key={hub.name}
                style={styles.topHubChip}
                onPress={() => handleRequestFocus(hub.name)}>
                <Text
                  style={styles.topHubChipName}
                  numberOfLines={1}>
                  {hub.name}
                </Text>
                <View style={styles.topHubChipScoreRow}>
                  <Text style={styles.topHubChipScoreValue}>
                    {hub.score}
                  </Text>
                  <Text style={styles.topHubChipScoreLabel}>edges</Text>
                </View>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Search — now content-aware. Matches against position
          names AND every catalogued technique label / transition
          label / transition destination via the precomputed
          POSITION_SEARCH_HAYSTACK at module load. A query like
          "armbar" surfaces every position whose corpus mentions
          armbar, auto-expands those cards, pivots to the role
          that has the match, and highlights the matching rows
          with a gold search-match accent. */}
      <TextInput
        style={styles.search}
        placeholder="Search positions or techniques…"
        placeholderTextColor="#666"
        value={query}
        onChangeText={(value) => {
          setCoachRecommendedTarget(null);
          setQuery(value);
        }}
        autoCorrect={false}
        autoCapitalize="none"
      />

      {/* Filter toggles — built-out only. The active-filter banner
          below handles result counts + tappable clear actions, so
          this row focuses just on the toggle itself. */}
      <View style={styles.filterRow}>
        <Pressable
          onPress={() => {
            setCoachRecommendedTarget(null);
            setBuiltOutOnly((v) => !v);
          }}
          style={[
            styles.filterPill,
            builtOutOnly && styles.filterPillActive,
          ]}>
          <Text
            style={[
              styles.filterPillText,
              builtOutOnly && styles.filterPillTextActive,
            ]}>
            Built out only
          </Text>
        </Pressable>
      </View>

      {/* Filter-escape note — rendered when a transition jump had
          to clear search and/or disable Built-out filter so the
          destination card could mount. Auto-dismisses after 4.5s
          via the useEffect timer above. Tap to dismiss manually. */}
      {filterEscapeNote && (
        <Pressable
          onPress={() => setFilterEscapeNote(null)}
          style={styles.filterEscapeNoteBanner}>
          <Text style={styles.filterEscapeNoteText}>
            {filterEscapeNote}
          </Text>
          <Text style={styles.filterEscapeNoteDismiss}>Tap to dismiss</Text>
        </Pressable>
      )}

      {/* Progress summary strip — shows aggregate counts of items
          marked Drilling / Learned / Tracking across the whole
          persisted progress store, and each chip is tappable as a
          filter. Tapping the same chip again clears the filter.
          Hidden entirely when no progress has been flagged yet so
          brand-new users don't see an empty row of zero chips. */}
      {totalProgressItems > 0 && (
        <View style={styles.progressSummaryStrip}>
          <Pressable
            onPress={() => {
              setCoachRecommendedTarget(null);
              setProgressFilter((v) => (v === 'drilling' ? null : 'drilling'));
            }}
            style={[
              styles.progressSummaryChip,
              progressFilter === 'drilling' &&
                styles.progressSummaryChipDrillingActive,
            ]}>
            <Text
              style={[
                styles.progressSummaryCount,
                { color: '#7fb8ff' },
              ]}>
              {progressCounts.drilling}
            </Text>
            <Text style={styles.progressSummaryLabel}>drilling</Text>
          </Pressable>
          <Pressable
            onPress={() => {
              setCoachRecommendedTarget(null);
              setProgressFilter((v) => (v === 'learned' ? null : 'learned'));
            }}
            style={[
              styles.progressSummaryChip,
              progressFilter === 'learned' &&
                styles.progressSummaryChipLearnedActive,
            ]}>
            <Text
              style={[
                styles.progressSummaryCount,
                { color: '#4ade80' },
              ]}>
              {progressCounts.learned}
            </Text>
            <Text style={styles.progressSummaryLabel}>learned</Text>
          </Pressable>
          <Pressable
            onPress={() => {
              setCoachRecommendedTarget(null);
              setProgressFilter((v) => (v === 'tracking' ? null : 'tracking'));
            }}
            style={[
              styles.progressSummaryChip,
              progressFilter === 'tracking' &&
                styles.progressSummaryChipTrackingActive,
            ]}>
            <Text
              style={[
                styles.progressSummaryCount,
                { color: '#d4e157' },
              ]}>
              {progressCounts.tracking}
            </Text>
            <Text style={styles.progressSummaryLabel}>tracking</Text>
          </Pressable>
          <View style={styles.progressSummaryRightGroup}>
            {progressFilter && (
              <Pressable
                onPress={() => {
                  setCoachRecommendedTarget(null);
                  setProgressFilter(null);
                }}
                style={styles.progressSummaryClearBtn}>
                <Text style={styles.progressSummaryClearText}>
                  Show all ×
                </Text>
              </Pressable>
            )}
            <Pressable
              onPress={handleShareProgress}
              style={styles.progressSummaryShareBtn}>
              <Text style={styles.progressSummaryShareText}>
                Share ↗
              </Text>
            </Pressable>
            <Pressable
              onPress={handleToggleImport}
              style={[
                styles.progressSummaryImportBtn,
                importPaneOpen && styles.progressSummaryImportBtnActive,
              ]}>
              <Text
                style={[
                  styles.progressSummaryImportText,
                  importPaneOpen && styles.progressSummaryImportTextActive,
                ]}>
                {importPaneOpen ? 'Close ×' : 'Import ↓'}
              </Text>
            </Pressable>
          </View>
        </View>
      )}

      {/* Import pastebox pane — rendered below the summary strip
          when open. Contains a multiline TextInput for the
          payload paste, a live parse preview line, and Apply /
          Cancel buttons. Always mounts when importPaneOpen is
          true, regardless of whether the summary strip is
          currently visible, so a brand-new user with zero
          flagged items can still paste an import payload to
          restore state from another device. That case still
          needs a way to open it — we render a small "Import
          progress ↓" pill in the filter row when the strip is
          hidden, below. */}
      {importPaneOpen && (() => {
        // Live preview — parse the current textbox contents and
        // surface a one-line hint so the user sees whether the
        // paste is good before they apply it.
        const preview = parseProgressImportPayload(importText);
        const previewCount = preview
          ? Object.keys(preview.entries).length
          : 0;
        const isValid = preview != null && previewCount > 0;
        return (
          <View style={styles.importPane}>
            <Text style={styles.importPaneLabel}>Import progress</Text>
            <Text style={styles.importPaneHelp}>
              Paste the full text export from Share, or just the
              JSON block. Existing entries are merged — your
              local unmatched items are kept.
            </Text>
            <TextInput
              style={styles.importPaneInput}
              value={importText}
              onChangeText={handleImportTextChange}
              placeholder="Paste export here…"
              placeholderTextColor="#555"
              multiline
              textAlignVertical="top"
              autoCorrect={false}
              autoCapitalize="none"
            />
            <Text
              style={[
                styles.importPanePreview,
                isValid && styles.importPanePreviewValid,
                importText.trim().length > 0 &&
                  !isValid &&
                  styles.importPanePreviewInvalid,
              ]}>
              {importText.trim().length === 0
                ? 'Waiting for payload…'
                : isValid
                  ? importReplaceMode
                    ? `Found ${previewCount} entr${previewCount === 1 ? 'y' : 'ies'} — Apply will REPLACE local progress.`
                    : `Found ${previewCount} entr${previewCount === 1 ? 'y' : 'ies'} — tap Apply to merge.`
                  : "Couldn't read that payload."}
            </Text>

            {/* Replace-mode toggle — compact checkbox-style row
                positioned BELOW the TextInput and ABOVE the Apply
                action so the user sees the destructive choice
                before tapping Apply. Defaults to OFF (merge) —
                turning it ON routes Apply through a native
                Alert.alert confirmation instead of the one-tap
                merge path. */}
            <Pressable
              onPress={handleToggleImportReplaceMode}
              style={styles.importReplaceRow}>
              <View
                style={[
                  styles.importReplaceBox,
                  importReplaceMode && styles.importReplaceBoxActive,
                ]}>
                {importReplaceMode && (
                  <Text style={styles.importReplaceBoxMark}>✓</Text>
                )}
              </View>
              <View style={styles.importReplaceTextWrap}>
                <Text
                  style={[
                    styles.importReplaceLabel,
                    importReplaceMode && styles.importReplaceLabelActive,
                  ]}>
                  Replace existing progress
                </Text>
                <Text style={styles.importReplaceHint}>
                  {importReplaceMode
                    ? 'Destructive — your local items not in the payload will be lost.'
                    : 'Leave off to merge (safest). Turn on to wipe and restore.'}
                </Text>
              </View>
            </Pressable>

            <View style={styles.importPaneActions}>
              <Pressable
                onPress={handleApplyImport}
                disabled={!isValid}
                style={[
                  styles.importPaneApplyBtn,
                  !isValid && styles.importPaneApplyBtnDisabled,
                  importReplaceMode && isValid && styles.importPaneApplyBtnReplace,
                ]}>
                <Text
                  style={[
                    styles.importPaneApplyBtnText,
                    !isValid && styles.importPaneApplyBtnTextDisabled,
                    importReplaceMode &&
                      isValid &&
                      styles.importPaneApplyBtnTextReplace,
                  ]}>
                  {importReplaceMode ? 'Replace local…' : 'Apply import'}
                </Text>
              </Pressable>
              <Pressable
                onPress={() => {
                  handleImportTextChange('');
                }}
                style={styles.importPaneClearBtn}>
                <Text style={styles.importPaneClearBtnText}>Clear</Text>
              </Pressable>
            </View>
          </View>
        );
      })()}

      {/* Zero-progress-state import entry point — when there are
          no flagged items the summary strip doesn't render, so
          the Import button inside it is invisible. This fallback
          pill in the filter row gives new users a way to open
          the import pane without first having to flag something. */}
      {totalProgressItems === 0 && !importPaneOpen && (
        <Pressable
          onPress={handleToggleImport}
          style={styles.zeroStateImportBtn}>
          <Text style={styles.zeroStateImportText}>
            Import progress ↓
          </Text>
        </Pressable>
      )}

      {/* Recent activity strip — last N keys touched (status set
          OR note saved), newest first. Each chip shows the
          technique label, its position context, the status, a
          note glyph if annotated, and a relative timestamp. Tap
          a chip to jump to the source position via the same
          handleRequestFocus pipeline used by Top hubs and
          transitions, with the filter-escape hatch automatically
          clearing search/Built-out only when needed. Hidden
          entirely when there's no recent activity yet so brand-
          new users don't see an empty row. */}
      {recentActivity.length > 0 && (
        <View style={styles.recentActivityBlock}>
          <Text style={styles.recentActivityLabel}>
            Recent activity
            <Text style={styles.recentActivityLabelHint}>
              {'  '}last {recentActivity.length} touched
            </Text>
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.recentActivityRow}>
            {recentActivity.map((entry) => (
              <Pressable
                key={entry.key}
                style={styles.recentActivityChip}
                onPress={() => handleRequestFocus(entry.jumpTo)}>
                <View style={styles.recentActivityChipHeaderRow}>
                  {entry.status && (
                    <Text
                      style={[
                        styles.recentActivityStatusDot,
                        entry.status === 'drilling' && { color: '#7fb8ff' },
                        entry.status === 'learned' && { color: '#4ade80' },
                        entry.status === 'tracking' && { color: '#d4e157' },
                      ]}>
                      ●
                    </Text>
                  )}
                  {entry.hasNote && (
                    <Text style={styles.recentActivityNoteGlyph}>✎</Text>
                  )}
                  <Text
                    style={styles.recentActivityWhen}
                    numberOfLines={1}>
                    {formatRelativeTime(entry.iso)}
                  </Text>
                </View>
                <Text
                  style={styles.recentActivityTitle}
                  numberOfLines={1}>
                  {entry.title}
                </Text>
                <Text
                  style={styles.recentActivitySubtitle}
                  numberOfLines={1}>
                  {entry.subtitle}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Import result note — transient confirmation of added /
          updated / skipped counts after a successful import,
          auto-dismisses via the useEffect timer above. */}
      {importResultNote && (
        <Pressable
          onPress={() => setImportResultNote(null)}
          style={styles.importResultNoteBanner}>
          <Text style={styles.importResultNoteText}>
            {importResultNote}
          </Text>
        </Pressable>
      )}

      {/* Progress-filter empty state — when the user activates a
          filter that currently matches zero items, the sections map
          below would render nothing. Explain and offer a reset. */}
      {progressFilter && totalFiltered === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>
            No items currently marked {progressFilter}
          </Text>
          <Text style={styles.emptyBody}>
            Tap the pill on any technique or transition to flag it.
          </Text>
          <Pressable
            style={styles.emptyResetBtn}
            onPress={() => setProgressFilter(null)}>
            <Text style={styles.emptyResetBtnText}>
              Show all ×
            </Text>
          </Pressable>
        </View>
      )}

      {/* Active filter context banner — renders ONLY when at least
          one filter is active (search, built-out, or a progress
          status). Each active filter shows as a small token chip
          with an × tap target that clears only that filter, so
          users can see and peel off filters individually without
          having to remember which of the three switches did what.
          Result count sits on the right so scanability reads
          "what's on → what matches" left-to-right. When the combo
          filters to zero matches, the banner stays visible and
          tints red-muted to make the empty state obvious. */}
      {(progressFilter != null ||
        builtOutOnly ||
        query.trim().length > 0) && (
        <View
          style={[
            styles.activeFilterBanner,
            totalFiltered === 0 && styles.activeFilterBannerEmpty,
          ]}>
          <Text style={styles.activeFilterBannerLabel}>Showing</Text>
          <View style={styles.activeFilterTokenRow}>
            {progressFilter && (
              <Pressable
                style={[
                  styles.activeFilterToken,
                  progressFilter === 'drilling' &&
                    styles.activeFilterTokenDrilling,
                  progressFilter === 'learned' &&
                    styles.activeFilterTokenLearned,
                  progressFilter === 'tracking' &&
                    styles.activeFilterTokenTracking,
                ]}
                onPress={() => setProgressFilter(null)}>
                <Text
                  style={[
                    styles.activeFilterTokenText,
                    progressFilter === 'drilling' && {
                      color: '#7fb8ff',
                    },
                    progressFilter === 'learned' && { color: '#4ade80' },
                    progressFilter === 'tracking' && {
                      color: '#d4e157',
                    },
                  ]}>
                  {progressFilter} ×
                </Text>
              </Pressable>
            )}
            {builtOutOnly && (
              <Pressable
                style={styles.activeFilterToken}
                onPress={() => setBuiltOutOnly(false)}>
                <Text style={styles.activeFilterTokenText}>
                  built out only ×
                </Text>
              </Pressable>
            )}
            {query.trim().length > 0 && (
              <Pressable
                style={styles.activeFilterToken}
                onPress={() => setQuery('')}>
                <Text
                  style={styles.activeFilterTokenText}
                  numberOfLines={1}>
                  “{query.trim()}” ×
                </Text>
              </Pressable>
            )}
          </View>
          <Text
            style={[
              styles.activeFilterCount,
              totalFiltered === 0 && styles.activeFilterCountEmpty,
            ]}>
            {totalFiltered}{' '}
            {totalFiltered === 1 ? 'position' : 'positions'}
          </Text>
        </View>
      )}

      <SyllabusEntryCard />

      {/* Sections */}
      {REFERENCE_SECTIONS.map((s) => (
        <SectionBlock
          key={s.id}
          section={s}
          filter={query}
          builtOutOnly={builtOutOnly}
          focusTarget={focusTarget}
          onRequestFocus={handleRequestFocus}
          registerOuterRef={registerOuterRef}
          progressFilter={progressFilter}
          query={query}
          coachingFocus={coachingFocus}
          coachRecommendedTarget={coachRecommendedTarget}
          onDismissCoachRecommendation={() => setCoachRecommendedTarget(null)}
          onConsumeCoachingFocus={() => setCoachingFocus(null)}
          currentBelt={currentBelt}
          videoByTargetId={videoByTargetId}
        />
      ))}

      {/* Full-map bridge footer — keeps the full graph as a dedicated
          embedded experience without collapsing Reference into it. */}
      <View style={styles.footerCard}>
        <Text style={styles.footerTitle}>Interactive 3D map</Text>
        <Text style={styles.footerBody}>
          Mobile Reference is the fast lookup view — positions,
          techniques, role breakdowns, and built-out filters. The
          full interactive 3D graph (transitions, position physics,
          filter modes) opens as a dedicated in-app scene.
        </Text>
        <Pressable
          style={styles.footerBridgeBtn}
          onPress={() => openFullMap({})}>
          <Text style={styles.footerBridgeBtnText}>
            Open 3D map
          </Text>
        </Pressable>
      </View>
    </ScrollView>
    <Pressable
      style={styles.floatingMapPill}
      onPress={() => router.navigate({ pathname: '/(tabs)/map-3d' })}>
      <Text style={styles.floatingMapPillText}>3D Map</Text>
    </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollView: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 60 },

  header: { gap: 4 },
  heading: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 14, opacity: 0.6 },

  floatingMapPill: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    height: 36,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 18,
    backgroundColor: 'rgba(212,225,87,0.92)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
  },
  floatingMapPillText: {
    color: '#0b0b0b',
    fontSize: 12,
    fontWeight: '700',
  },
  summaryStrip: {
    flexDirection: 'row',
    gap: 10,
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryValue: { fontSize: 22, fontWeight: '700', color: '#d4e157' },
  summaryLabel: { fontSize: 11, opacity: 0.5, textTransform: 'uppercase', letterSpacing: 0.5 },

  // Top hubs — compact quick-jump strip near the top of Reference
  topHubsBlock: {
    gap: 6,
    marginTop: -4,
  },
  topHubsLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontWeight: '700',
  },
  topHubsLabelHint: {
    opacity: 0.55,
    fontWeight: '500',
  },
  topHubsRow: {
    flexDirection: 'row',
    gap: 8,
    paddingRight: 4,
  },
  topHubChip: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(74,158,255,0.45)',
    backgroundColor: 'rgba(74,158,255,0.08)',
    minWidth: 110,
    maxWidth: 180,
    gap: 4,
  },
  topHubChipName: {
    fontSize: 13,
    color: '#cfe3ff',
    fontWeight: '700',
  },
  topHubChipScoreRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
    backgroundColor: 'transparent',
  },
  topHubChipScoreValue: {
    fontSize: 14,
    color: '#7fb8ff',
    fontWeight: '700',
  },
  topHubChipScoreLabel: {
    fontSize: 9,
    color: '#7fb8ff',
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    fontWeight: '600',
  },

  search: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  searchMeta: { fontSize: 12, opacity: 0.5 },

  filterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: -6,
  },
  filterPill: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.02)',
  },
  filterPillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  filterPillText: { fontSize: 11, color: '#888', fontWeight: '600' },
  filterPillTextActive: { color: '#d4e157' },

  sectionCard: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  sectionTitle: { fontSize: 17, fontWeight: '600' },
  sectionDescription: { fontSize: 12, opacity: 0.5, marginTop: 2, lineHeight: 16 },
  sectionCountBlock: { alignItems: 'center', minWidth: 46 },
  sectionCountValue: { fontSize: 18, fontWeight: '700', color: '#d4e157' },
  sectionCountLabel: { fontSize: 10, opacity: 0.4 },

  // Section-level progress strip — sits under the section
  // description, above the positions list. Horizontal row of
  // colored count chips that mirrors the per-position chip
  // language one tier up. Slight top margin pulls it away from
  // the description without competing with the count block on
  // the right.
  sectionProgressStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 6,
  },
  sectionProgressDrilling: {
    fontSize: 11,
    fontWeight: '700',
    color: '#7fb8ff',
    opacity: 0.9,
  },
  sectionProgressLearned: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4ade80',
    opacity: 0.9,
  },
  sectionProgressTracking: {
    fontSize: 11,
    fontWeight: '700',
    color: '#d4e157',
    opacity: 0.9,
  },

  positionsList: { gap: 2 },
  positionWrap: {
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.02)',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'transparent',
  },
  positionWrapJumpFlash: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.06)',
  },
  positionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  positionName: { fontSize: 14, fontWeight: '500' },
  builtBadge: { fontSize: 11, color: '#d4e157', opacity: 0.8 },
  positionPersp: { fontSize: 11, opacity: 0.4, marginTop: 2 },

  // Role toggle pills
  rolePillRow: {
    flexDirection: 'row',
    gap: 6,
    marginTop: 6,
  },
  rolePill: {
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.02)',
  },
  rolePillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  rolePillEmpty: {
    opacity: 0.35,
  },
  rolePillText: { fontSize: 11, color: '#888' },
  rolePillTextActive: { color: '#d4e157', fontWeight: '600' },
  rolePillTextEmpty: { fontStyle: 'italic' },
  rolePillCount: {
    fontSize: 10,
    opacity: 0.6,
    fontWeight: '700',
  },

  viewingAs: {
    fontSize: 11,
    opacity: 0.6,
    // marginBottom removed — parent `positionDetail.gap` now
    // provides consistent inter-child spacing across every block
    // inside the expanded card.
  },
  viewingAsName: {
    color: '#d4e157',
    fontWeight: '600',
  },

  chevron: { fontSize: 12, opacity: 0.4, paddingHorizontal: 4 },

  positionDetail: {
    paddingHorizontal: 12,
    paddingBottom: 12,
    paddingTop: 4,
    // Parent gap owns the vertical rhythm between every direct
    // child (viewingAs, heading blocks, Transitions out, Coming
    // in from, position bridge button). Bumped from 4 → 12 so
    // individual blocks no longer need per-block marginTop
    // values — inter-block spacing is now consistent 12px
    // wherever the scroll reaches.
    gap: 12,
  },
  detailLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 4,
  },
  detailItem: { fontSize: 13, opacity: 0.7, lineHeight: 18 },

  // Real technique content — grouped by heading
  headingBlock: {
    // marginTop removed — parent positionDetail.gap (12) drives
    // inter-block spacing consistently across ALL blocks inside
    // an expanded card.
    backgroundColor: 'transparent',
    gap: 2,
  },
  headingLabel: {
    fontSize: 11,
    color: '#d4e157',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  headingLabelCount: {
    fontSize: 10,
    opacity: 0.55,
    fontWeight: '700',
  },
  techniqueRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    // Normalized to match transitionRow + inboundRow so row
    // density is consistent across all three block types —
    // visual rhythm doesn't change when scanning from techniques
    // into Transitions out into Coming in from.
    paddingVertical: 4,
    paddingLeft: 6,
    paddingRight: 4,
    borderRadius: 6,
    backgroundColor: 'transparent',
    // Reserve 3px of left border on every row — transparent by
    // default, flipped to a status colour by rowAccentDrilling /
    // rowAccentLearned / rowAccentTracking variants below. Keeps
    // all rows in a block aligned whether or not they're flagged.
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
  },
  techniqueRowOpen: {
    backgroundColor: 'rgba(212,225,87,0.06)',
  },
  techniqueItem: {
    flex: 1,
    fontSize: 13,
    color: '#d4dce6',
    opacity: 0.85,
    lineHeight: 19,
  },
  techniqueChevron: {
    fontSize: 11,
    opacity: 0.4,
    paddingLeft: 8,
    paddingTop: 2,
  },

  // Progress pill — compact Drilling/Learned/Tracking chip used
  // across technique rows, outbound transition rows, and inbound
  // transition rows. Single-glyph so rows stay uncluttered.
  progressPill: {
    width: 24,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
    backgroundColor: 'rgba(255,255,255,0.03)',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 6,
  },
  progressPillDrilling: {
    borderColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.18)',
  },
  progressPillLearned: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.2)',
  },
  progressPillTracking: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.18)',
  },
  progressPillText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#777',
  },
  progressPillTextDrilling: { color: '#7fb8ff' },
  progressPillTextLearned: { color: '#4ade80' },
  progressPillTextTracking: { color: '#d4e157' },

  // Row-level progress accents — restrained left-rail colour +
  // subtle matching tinted fill so scanning an expanded card
  // instantly surfaces which items have a drilling/learned/
  // tracking state. The base techniqueRow / transitionRow /
  // inboundRow styles reserve a 3px transparent borderLeft so
  // these variants only flip the colour, never the layout — no
  // horizontal shift between accented and non-accented rows
  // inside the same block.
  rowAccentDrilling: {
    borderLeftColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.06)',
  },
  rowAccentLearned: {
    borderLeftColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.07)',
  },
  rowAccentTracking: {
    borderLeftColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.06)',
  },
  // Search-match accent — gold left rail + warm gold tint, applied
  // AFTER the progress accent in the style array so search matches
  // visually dominate while the search is active. The progress
  // pill on the right remains visible so the persistent progress
  // state isn't lost — just the row-level rail temporarily reads
  // as "this is your search hit" instead of "this is your drilling
  // state". When the user clears the query the rail reverts.
  rowAccentSearchMatch: {
    borderLeftColor: '#facc15',
    backgroundColor: 'rgba(250,204,21,0.12)',
  },
  rowAccentCoachingTarget: {
    borderLeftColor: '#ffd866',
    backgroundColor: 'rgba(255,216,102,0.16)',
  },

  // Note-attached indicator — small pencil glyph rendered between
  // the row's main label and the ProgressPill on any row whose
  // progressKey has a non-empty note in the store. Subtly tinted
  // so it reads as "metadata" rather than competing with status
  // colour.
  noteIndicator: {
    fontSize: 12,
    color: '#facc15',
    opacity: 0.8,
    marginLeft: 4,
    marginRight: -2,
  },
  coachRecommendedBlock: {
    alignSelf: 'stretch',
    marginBottom: 6,
    gap: 4,
  },
  coachRecommendedBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(255,216,102,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(255,216,102,0.3)',
  },
  coachRecommendedBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#ffd866',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  coachRecommendedReason: {
    fontSize: 12,
    lineHeight: 17,
    color: 'rgba(255,216,102,0.92)',
    opacity: 0.9,
  },

  // Inline note editor — sits inside the technique-row expanded
  // detail block alongside the breadcrumb and bridge button.
  // Header row for the "Note" label + dirty hint + clear button.
  // Input is multiline, top-aligned, and uses a darker fill so
  // it reads as a distinct interactive surface inside the already-
  // dark detail card.
  noteEditorWrap: {
    marginTop: 4,
    gap: 4,
  },
  noteEditorHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  noteEditorLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#facc15',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  noteEditorDirtyHint: {
    fontSize: 10,
    color: '#facc15',
    opacity: 0.65,
    fontStyle: 'italic',
  },
  noteEditorClearLink: {
    fontSize: 10,
    color: '#888',
    textDecorationLine: 'underline',
  },
  noteEditorInput: {
    minHeight: 56,
    maxHeight: 140,
    padding: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(250,204,21,0.25)',
    backgroundColor: 'rgba(0,0,0,0.4)',
    color: '#e6e9ef',
    fontSize: 12,
    lineHeight: 17,
  },

  // Recent activity strip — horizontal scroll of chips below the
  // progress summary strip. Each chip is a compact pill showing
  // status colour, optional note glyph, relative time, the
  // touched item's title, and a position-context subtitle.
  recentActivityBlock: {
    gap: 8,
  },
  recentActivityLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#aab4c2',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  recentActivityLabelHint: {
    fontSize: 10,
    fontWeight: '500',
    color: '#aab4c2',
    opacity: 0.5,
    textTransform: 'none',
    letterSpacing: 0,
  },
  recentActivityRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 2,
    paddingRight: 4,
  },
  recentActivityChip: {
    minWidth: 160,
    maxWidth: 220,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 2,
  },
  recentActivityChipHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 2,
  },
  recentActivityStatusDot: {
    fontSize: 10,
    fontWeight: '700',
  },
  recentActivityNoteGlyph: {
    fontSize: 11,
    color: '#facc15',
    opacity: 0.85,
  },
  recentActivityWhen: {
    flex: 1,
    fontSize: 10,
    color: '#888',
    textAlign: 'right',
  },
  recentActivityTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#e6e9ef',
  },
  recentActivitySubtitle: {
    fontSize: 11,
    color: '#888',
    opacity: 0.85,
  },
  techniqueDetail: {
    marginTop: 2,
    marginLeft: 14,
    marginBottom: 6,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(0,0,0,0.25)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(212,225,87,0.5)',
    gap: 4,
  },
  techniqueDetailCrumb: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  techniqueDetailCrumbRole: {
    color: '#d4e157',
    fontWeight: '600',
  },
  techniqueDetailName: {
    fontSize: 14,
    color: '#e6ecf3',
    fontWeight: '600',
    lineHeight: 19,
  },
  techniqueDetailMeta: {
    fontSize: 11,
    opacity: 0.55,
    lineHeight: 16,
    marginTop: 2,
  },
  techniqueVideoStatePill: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.06)',
    marginTop: 2,
  },
  techniqueVideoStatePillText: {
    fontSize: 11,
    fontWeight: '700',
    opacity: 0.82,
    textTransform: 'uppercase',
    letterSpacing: 0.35,
  },
  techniqueDetailBridgeBtn: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.5)',
    backgroundColor: 'rgba(212,225,87,0.08)',
  },
  techniqueDetailBridgeBtnText: {
    color: '#d4e157',
    fontSize: 11,
    fontWeight: '600',
  },
  // Transitions out — arrow-format edge rows
  transitionsBlock: {
    // marginTop removed — positionDetail.gap (12) provides the
    // inter-block rhythm.
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(74,158,255,0.06)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(74,158,255,0.45)',
    gap: 2,
  },
  transitionsLabel: {
    fontSize: 11,
    color: '#7fb8ff',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  transitionsLabelCount: {
    fontSize: 10,
    opacity: 0.6,
    fontWeight: '700',
  },
  transitionRow: {
    flexDirection: 'row',
    // Top-align so arrow + pill stay at the first line of text when
    // labels / destinations wrap to multiple lines. Previously this
    // was `center` which caused the right-side controls to float
    // mid-block on long wrapping rows.
    alignItems: 'flex-start',
    gap: 6,
    // Normalized from 5 → 4 to match techniqueRow and inboundRow —
    // one consistent row height across all three block types.
    paddingVertical: 4,
    paddingLeft: 4,
    paddingRight: 2,
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
    borderRadius: 4,
  },
  transitionRowMuted: {
    opacity: 0.45,
  },
  transitionLabel: {
    // flex:1 + flexBasis:0 so label and destination share row space
    // proportionally and can wrap freely instead of competing for
    // a natural-width pixel allocation that triggered truncation.
    flex: 1,
    flexBasis: 0,
    minWidth: 0,
    fontSize: 12,
    color: '#d4dce6',
    lineHeight: 17,
  },
  transitionArrow: {
    fontSize: 13,
    color: '#7fb8ff',
    fontWeight: '700',
    paddingHorizontal: 2,
    // Nudge the arrow to sit on the same baseline as the first
    // line of wrapped label text.
    paddingTop: 1,
  },
  transitionDest: {
    flex: 1,
    flexBasis: 0,
    minWidth: 0,
    fontSize: 12,
    color: '#aab4c2',
    fontWeight: '600',
    lineHeight: 17,
  },
  transitionDestNavigable: {
    color: '#7fb8ff',
    textDecorationLine: 'underline',
  },

  // Inbound count chip on the position header row
  inboundChip: {
    fontSize: 11,
    color: '#7fb8ff',
    opacity: 0.75,
    fontWeight: '600',
  },

  // Search-match chip on the position header — same idiom as
  // inboundChip but in the gold search palette. Only renders when
  // the position is in the results because of an internal content
  // match (technique or transition label) rather than a position-
  // name match, so the user understands why the card surfaced
  // even though the title doesn't contain the query.
  searchMatchChip: {
    fontSize: 11,
    color: '#facc15',
    opacity: 0.85,
    fontWeight: '700',
  },

  // Per-position progress chips on the collapsed header. Wrapper
  // is a bare Text so the per-status colored chunks below can be
  // nested inline without breaking the parent positionName layout.
  // Each colored chunk uses the same colour as the corresponding
  // ProgressPill (drilling=blue, learned=green, tracking=yellow)
  // so users recognise the language immediately. Slightly muted
  // at rest via opacity so a fully-flagged card doesn't shout
  // over the position name itself.
  positionProgressChip: {
    fontSize: 11,
    fontWeight: '700',
  },
  positionProgressDrilling: {
    color: '#7fb8ff',
    opacity: 0.85,
  },
  positionProgressLearned: {
    color: '#4ade80',
    opacity: 0.85,
  },
  positionProgressTracking: {
    color: '#d4e157',
    opacity: 0.85,
  },

  // Coming in from — inverse transition block
  inboundBlock: {
    // marginTop removed — positionDetail.gap (12) provides the
    // inter-block rhythm and keeps Transitions out → Coming in
    // from spacing identical to every other block pair.
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(74,158,255,0.04)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(74,158,255,0.3)',
    gap: 2,
  },
  inboundBlockLabel: {
    fontSize: 11,
    color: '#7fb8ff',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
    opacity: 0.85,
  },
  inboundBlockLabelCount: {
    fontSize: 10,
    opacity: 0.6,
    fontWeight: '700',
  },
  inboundRow: {
    flexDirection: 'row',
    // Top-align — same reasoning as transitionRow. Source position
    // names and technique labels both wrap freely now, so arrow +
    // pill stay on the first line.
    alignItems: 'flex-start',
    gap: 6,
    // Normalized from 5 → 4 to match techniqueRow + transitionRow.
    paddingVertical: 4,
    paddingLeft: 4,
    paddingRight: 2,
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
    borderRadius: 4,
  },
  inboundSource: {
    flex: 1,
    flexBasis: 0,
    minWidth: 0,
    fontSize: 12,
    color: '#7fb8ff',
    fontWeight: '600',
    textDecorationLine: 'underline',
    lineHeight: 17,
  },
  inboundArrow: {
    fontSize: 13,
    color: '#7fb8ff',
    fontWeight: '700',
    paddingHorizontal: 2,
    opacity: 0.7,
    paddingTop: 1,
  },
  inboundLabel: {
    flex: 1,
    flexBasis: 0,
    minWidth: 0,
    fontSize: 12,
    color: '#aab4c2',
    lineHeight: 17,
  },

  positionBridgeBtn: {
    // Parent positionDetail.gap (12) already provides the inter-
    // block rhythm. A small extra marginTop (4) gives the CTA a
    // little more breathing room so it reads as a distinct
    // terminal action rather than "another block", reaching a
    // 16px gap from the last block above it.
    marginTop: 4,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.04)',
    alignItems: 'center',
  },
  positionBridgeBtnText: {
    color: '#d4e157',
    fontSize: 12,
    fontWeight: '600',
  },
  viewingAsCount: {
    opacity: 0.5,
    fontSize: 11,
  },
  emptyNote: {
    fontSize: 11,
    fontStyle: 'italic',
    opacity: 0.4,
    marginTop: 6,
    lineHeight: 14,
  },

  emptyCard: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 4,
  },
  emptyTitle: { fontSize: 14, fontWeight: '600' },
  emptyBody: { fontSize: 12, opacity: 0.5, lineHeight: 16 },

  // Progress summary strip — aggregate drilling/learned/tracking
  // counts across the whole persisted progress store, each chip
  // tappable as a filter.
  progressSummaryStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
    flexWrap: 'wrap',
  },
  progressSummaryChip: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 5,
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.02)',
  },
  progressSummaryChipDrillingActive: {
    borderColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.15)',
  },
  progressSummaryChipLearnedActive: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.15)',
  },
  progressSummaryChipTrackingActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.15)',
  },
  progressSummaryCount: {
    fontSize: 16,
    fontWeight: '700',
  },
  progressSummaryLabel: {
    fontSize: 10,
    opacity: 0.55,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  progressSummaryRightGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginLeft: 'auto',
  },
  progressSummaryClearBtn: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
  },
  progressSummaryClearText: {
    fontSize: 10,
    color: '#aaa',
    fontWeight: '600',
  },
  progressSummaryShareBtn: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.5)',
    backgroundColor: 'rgba(212,225,87,0.05)',
  },
  progressSummaryShareText: {
    fontSize: 10,
    color: '#d4e157',
    fontWeight: '700',
  },
  progressSummaryImportBtn: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(127,184,255,0.5)',
    backgroundColor: 'rgba(74,158,255,0.06)',
  },
  progressSummaryImportBtnActive: {
    borderColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.18)',
  },
  progressSummaryImportText: {
    fontSize: 10,
    color: '#7fb8ff',
    fontWeight: '700',
  },
  progressSummaryImportTextActive: {
    color: '#cfe3ff',
  },

  // Import pastebox pane — inline panel shown below the
  // summary strip when the Import button is active.
  importPane: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(74,158,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(74,158,255,0.35)',
    gap: 8,
  },
  importPaneLabel: {
    fontSize: 11,
    color: '#7fb8ff',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  importPaneHelp: {
    fontSize: 11,
    color: '#b0b8c3',
    opacity: 0.7,
    lineHeight: 15,
  },
  importPaneInput: {
    minHeight: 84,
    maxHeight: 180,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    borderRadius: 8,
    padding: 10,
    fontSize: 12,
    color: '#e6ecf3',
    backgroundColor: 'rgba(0,0,0,0.35)',
    fontFamily: 'SpaceMono',
    lineHeight: 16,
  },
  importPanePreview: {
    fontSize: 11,
    color: '#888',
    fontStyle: 'italic',
  },
  importPanePreviewValid: {
    color: '#4ade80',
    fontStyle: 'normal',
    fontWeight: '600',
  },
  importPanePreviewInvalid: {
    color: '#ff8a80',
    fontStyle: 'normal',
    fontWeight: '600',
  },
  importPaneActions: {
    flexDirection: 'row',
    gap: 8,
  },
  importPaneApplyBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.1)',
    alignItems: 'center',
  },
  importPaneApplyBtnDisabled: {
    opacity: 0.35,
  },
  importPaneApplyBtnText: {
    color: '#7fb8ff',
    fontSize: 12,
    fontWeight: '700',
  },
  importPaneApplyBtnTextDisabled: {
    color: '#555',
  },
  importPaneApplyBtnReplace: {
    borderColor: '#ff8a80',
    backgroundColor: 'rgba(255,138,128,0.14)',
  },
  importPaneApplyBtnTextReplace: {
    color: '#ff8a80',
  },

  // Replace-mode checkbox row
  importReplaceRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    paddingVertical: 2,
    paddingHorizontal: 2,
  },
  importReplaceBox: {
    width: 18,
    height: 18,
    borderRadius: 4,
    borderWidth: 1.5,
    borderColor: '#555',
    backgroundColor: 'rgba(0,0,0,0.35)',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  importReplaceBoxActive: {
    borderColor: '#ff8a80',
    backgroundColor: 'rgba(255,138,128,0.18)',
  },
  importReplaceBoxMark: {
    fontSize: 11,
    color: '#ff8a80',
    fontWeight: '800',
  },
  importReplaceTextWrap: {
    flex: 1,
    backgroundColor: 'transparent',
    gap: 1,
  },
  importReplaceLabel: {
    fontSize: 12,
    color: '#d4dce6',
    fontWeight: '600',
  },
  importReplaceLabelActive: {
    color: '#ff8a80',
  },
  importReplaceHint: {
    fontSize: 10,
    color: '#888',
    opacity: 0.85,
    lineHeight: 14,
  },
  importPaneClearBtn: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#444',
    alignItems: 'center',
  },
  importPaneClearBtnText: {
    color: '#888',
    fontSize: 12,
  },

  zeroStateImportBtn: {
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(127,184,255,0.45)',
    backgroundColor: 'rgba(74,158,255,0.05)',
  },
  zeroStateImportText: {
    fontSize: 11,
    color: '#7fb8ff',
    fontWeight: '600',
  },

  importResultNoteBanner: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(74,222,128,0.08)',
    borderLeftWidth: 3,
    borderLeftColor: '#4ade80',
  },
  importResultNoteText: {
    fontSize: 12,
    color: '#d8fbe0',
    fontWeight: '600',
    lineHeight: 17,
  },
  emptyResetBtn: {
    alignSelf: 'flex-start',
    marginTop: 8,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#888',
  },
  emptyResetBtnText: {
    fontSize: 11,
    color: '#ccc',
    fontWeight: '600',
  },

  // Active-filter context banner — shown whenever any combination
  // of search / built-out / progressFilter is on, so users can see
  // AND peel off filters without guessing which toggle did what.
  activeFilterBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderLeftWidth: 2,
    borderLeftColor: '#d4e157',
  },
  activeFilterBannerEmpty: {
    borderLeftColor: '#ff8a80',
    backgroundColor: 'rgba(255,138,128,0.07)',
  },
  activeFilterBannerLabel: {
    fontSize: 10,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontWeight: '700',
  },
  activeFilterTokenRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    flexShrink: 1,
  },
  activeFilterToken: {
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#555',
    backgroundColor: 'rgba(255,255,255,0.04)',
    maxWidth: 180,
  },
  activeFilterTokenText: {
    fontSize: 11,
    color: '#ccc',
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  activeFilterTokenDrilling: {
    borderColor: '#7fb8ff',
    backgroundColor: 'rgba(74,158,255,0.12)',
  },
  activeFilterTokenLearned: {
    borderColor: '#4ade80',
    backgroundColor: 'rgba(74,222,128,0.12)',
  },
  activeFilterTokenTracking: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.12)',
  },
  activeFilterCount: {
    marginLeft: 'auto',
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '700',
  },
  activeFilterCountEmpty: {
    color: '#ff8a80',
  },

  // Filter/search auto-escape note when a transition jump revealed
  // a hidden destination. Blue-accented to match the transition-
  // block palette — reads as continuation of the transition action,
  // not as an error banner.
  filterEscapeNoteBanner: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(74,158,255,0.1)',
    borderLeftWidth: 3,
    borderLeftColor: '#7fb8ff',
    gap: 3,
  },
  filterEscapeNoteText: {
    fontSize: 12,
    color: '#cfe3ff',
    fontWeight: '600',
    lineHeight: 17,
  },
  filterEscapeNoteDismiss: {
    fontSize: 10,
    color: '#7fb8ff',
    opacity: 0.6,
    fontStyle: 'italic',
  },

  footerCard: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.05)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 4,
  },
  footerTitle: {
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  footerBody: { fontSize: 12, opacity: 0.6, lineHeight: 18 },
  footerBridgeBtn: {
    marginTop: 10,
    paddingVertical: 11,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
    alignItems: 'center',
  },
  footerBridgeBtnText: {
    color: '#d4e157',
    fontSize: 14,
    fontWeight: '700',
  },
});
