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
  TextInput,
  Linking,
  findNodeHandle,
  View as RNView,
} from 'react-native';
import { Text, View } from '@/components/Themed';

/** Live website base URL — the full Reference tree, 3D graph, and
 *  attached media all live here today. The mobile Reference screen
 *  bridges to it via explicit "Open ... in 3D map (web)" CTAs that
 *  launch the system browser so users don't expect an in-app 3D
 *  renderer. */
const FULL_MAP_URL = 'https://aarontmaher.github.io/lauburugrapplingmap/';
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
  useReferenceProgressStore,
  buildTechniqueProgressKey,
  buildTransitionProgressKey,
  type ProgressStatus,
} from '../../src/store/reference-progress-store';

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
 * Open the full website Reference, optionally focused on a specific
 * position/technique via the deep-link format above. Best-effort —
 * `Linking.openURL` rejection (rare on iOS) is swallowed silently.
 */
function openFullMap(args: FullMapDeepLinkArgs = {}): void {
  const url = buildFullMapDeepLink(args);
  Linking.openURL(url).catch(() => {
    // Silent — rare on iOS.
  });
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

function PositionRow({
  position,
  sectionLabel,
  focusTarget,
  onRequestFocus,
  registerOuterRef,
  progressFilter,
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

  // Auto-pivot to the role that actually has content. If both roles
  // have content, the user's manual selection wins. If only one has
  // content, silently flip to that side so the expanded view is never
  // "Viewing as Passer — 0 techniques" when Guard player has 14.
  const effectiveRoleIdx = useMemo(() => {
    if (roleCounts[selectedRoleIdx] > 0) return selectedRoleIdx;
    const firstWithContent = roleCounts.findIndex((n) => n > 0);
    return firstWithContent >= 0 ? firstWithContent : selectedRoleIdx;
  }, [roleCounts, selectedRoleIdx]);
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

  // Auto-expand when a progress filter is active so filtered items
  // are visible immediately without the user having to tap every
  // card. When the filter clears, user expansion state is preserved
  // (we only set expanded=true, we never force collapse).
  useEffect(() => {
    if (progressFilter) setExpanded(true);
  }, [progressFilter]);

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
        onPress={() => setExpanded(!expanded)}>
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
                  return (
                    <View key={techKey}>
                      <Pressable
                        style={[
                          styles.techniqueRow,
                          isOpen && styles.techniqueRowOpen,
                        ]}
                        onPress={() =>
                          setExpandedTechKey(isOpen ? null : techKey)
                        }>
                        <Text style={styles.techniqueItem} numberOfLines={2}>
                          • {t}
                        </Text>
                        <ProgressPill progressKey={progressKey} />
                        <Text style={styles.techniqueChevron}>
                          {isOpen ? '▾' : '▸'}
                        </Text>
                      </Pressable>
                      {isOpen && (
                        <View style={styles.techniqueDetail}>
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
                          <Text style={styles.techniqueDetailMeta}>
                            {position.built_out
                              ? 'Full text, transitions, and any attached video live in the interactive 3D map on web.'
                              : 'Full text and any attached video live in the interactive 3D map on web.'}
                          </Text>
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
                              Open this technique in 3D map (web) ↗
                            </Text>
                          </Pressable>
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
                return (
                  <Pressable
                    key={`${edge.label}|${edge.destination}|${i}`}
                    style={[
                      styles.transitionRow,
                      !navigable && styles.transitionRowMuted,
                    ]}
                    disabled={!navigable}
                    onPress={() => {
                      if (navigable) onRequestFocus(edge.destination);
                    }}>
                    <Text
                      style={styles.transitionLabel}
                      numberOfLines={2}>
                      {edge.label}
                    </Text>
                    <Text style={styles.transitionArrow}>→</Text>
                    <Text
                      style={[
                        styles.transitionDest,
                        navigable && styles.transitionDestNavigable,
                      ]}
                      numberOfLines={1}>
                      {edge.destination}
                    </Text>
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
                return (
                  <Pressable
                    key={`${edge.sourceName}|${edge.label}|${i}`}
                    style={styles.inboundRow}
                    onPress={() => onRequestFocus(edge.sourceName)}>
                    <Text
                      style={styles.inboundSource}
                      numberOfLines={1}>
                      {edge.sourceName}
                    </Text>
                    <Text style={styles.inboundArrow}>←</Text>
                    <Text
                      style={styles.inboundLabel}
                      numberOfLines={2}>
                      {edge.label}
                    </Text>
                    <ProgressPill progressKey={progressKey} />
                  </Pressable>
                );
              })}
            </View>
          )}

          {/* Position-level full-map bridge. Always rendered on
              expanded positions so the separation between mobile
              Reference and the full web 3D map feels intentional,
              not like a missing feature. Copy explicitly says "web"
              so users don't expect an in-app 3D renderer. */}
          <Pressable
            style={styles.positionBridgeBtn}
            onPress={() =>
              openFullMap({
                section: sectionLabel,
                position: position.name,
              })
            }>
            <Text style={styles.positionBridgeBtnText}>
              Open {position.name} in 3D map (web) ↗
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
}: {
  section: ReferenceSection;
  filter: string;
  builtOutOnly: boolean;
  focusTarget: string | null;
  onRequestFocus: (destination: string) => void;
  registerOuterRef: (name: string, ref: RNView | null) => void;
  progressFilter: ProgressStatus | null;
}) {
  // Read the progress store here so filter-induced visibility
  // checks react when a user marks/unmarks an item while a
  // progress filter is active. Only used in the progress-filter
  // branch of the filter closure below.
  const progress = useReferenceProgressStore((s) => s.progress);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return section.positions.filter((p) => {
      if (builtOutOnly && !p.built_out) return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      if (progressFilter) {
        if (!positionHasMatchingProgress(p, progress, progressFilter)) {
          return false;
        }
      }
      return true;
    });
  }, [section.positions, filter, builtOutOnly, progressFilter, progress]);

  if (filtered.length === 0) return null;

  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.sectionTitle}>{section.label}</Text>
          <Text style={styles.sectionDescription}>{section.description}</Text>
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
          />
        ))}
      </View>
    </View>
  );
}

export default function ReferenceScreen() {
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
        q.length > 0 && !destination.toLowerCase().includes(q);
      const hiddenByBuiltOut = builtOutOnly && !targetPos.built_out;
      let escapeNote: string | null = null;
      if (hiddenBySearch && hiddenByBuiltOut) {
        setQuery('');
        setBuiltOutOnly(false);
        escapeNote = `Cleared search and turned off Built-out filter to reach ${destination}.`;
      } else if (hiddenBySearch) {
        setQuery('');
        escapeNote = `Cleared search to reach ${destination}.`;
      } else if (hiddenByBuiltOut) {
        setBuiltOutOnly(false);
        escapeNote = `Turned off Built-out filter to reach ${destination}.`;
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
    [query, builtOutOnly],
  );

  // Auto-dismiss the filter-escape note after 4.5s so it never
  // becomes permanent visual noise. The timer is scoped to each
  // fresh note so overlapping jumps reset the timer cleanly.
  useEffect(() => {
    if (!filterEscapeNote) return;
    const t = setTimeout(() => setFilterEscapeNote(null), 4500);
    return () => clearTimeout(t);
  }, [filterEscapeNote]);

  // Whenever focusTarget changes, measureLayout the destination
  // card's native ref against the scroll container and scrollTo
  // its offset (with an 80px header breathing room). The inner
  // setTimeout gives the destination card's expand-on-focus effect
  // a tick to re-render before we measure; otherwise the newly-
  // expanded content would shift the position we scrolled to.
  useEffect(() => {
    if (!focusTarget) return;
    const cardRef = positionRefs.current.get(focusTarget);
    const sv = scrollViewRef.current;
    if (!cardRef || !sv) return;
    const scrollNode = findNodeHandle(sv);
    if (scrollNode == null) return;
    const timer = setTimeout(() => {
      try {
        cardRef.measureLayout(
          scrollNode as unknown as number,
          (_x, y) => {
            sv.scrollTo({
              y: Math.max(0, y - 80),
              animated: true,
            });
          },
          () => {
            // measureLayout can reject if the destination card has
            // been unmounted mid-navigation — silent swallow is
            // acceptable since the card's own focus effect still
            // handled the expand+flash fallback.
          },
        );
      } catch {
        // Defensive — never let a scroll failure crash Reference.
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [focusTarget]);

  const totalFiltered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return REFERENCE_SECTIONS.reduce(
      (acc, s) =>
        acc +
        s.positions.filter((p) => {
          if (builtOutOnly && !p.built_out) return false;
          if (q && !p.name.toLowerCase().includes(q)) return false;
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

  return (
    <ScrollView
      ref={scrollViewRef}
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Text style={styles.heading}>Reference</Text>
        <Text style={styles.subtitle}>
          Canonical positions and techniques from the Lauburu Grappling Map.
          The interactive 3D graph opens in your browser.
        </Text>
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

      {/* Search */}
      <TextInput
        style={styles.search}
        placeholder="Search positions…"
        placeholderTextColor="#666"
        value={query}
        onChangeText={setQuery}
        autoCorrect={false}
        autoCapitalize="none"
      />

      {/* Filter toggles — built-out only. The active-filter banner
          below handles result counts + tappable clear actions, so
          this row focuses just on the toggle itself. */}
      <View style={styles.filterRow}>
        <Pressable
          onPress={() => setBuiltOutOnly((v) => !v)}
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
            onPress={() =>
              setProgressFilter((v) => (v === 'drilling' ? null : 'drilling'))
            }
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
            onPress={() =>
              setProgressFilter((v) => (v === 'learned' ? null : 'learned'))
            }
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
            onPress={() =>
              setProgressFilter((v) => (v === 'tracking' ? null : 'tracking'))
            }
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
          {progressFilter && (
            <Pressable
              onPress={() => setProgressFilter(null)}
              style={styles.progressSummaryClearBtn}>
              <Text style={styles.progressSummaryClearText}>
                Show all ×
              </Text>
            </Pressable>
          )}
        </View>
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
        />
      ))}

      {/* Full-map bridge footer — stops pretending the 3D map is a
          week away and makes the separation intentional. Copy is
          explicit: the 3D graph is a web experience, and tapping
          Open launches it in the system browser. */}
      <View style={styles.footerCard}>
        <Text style={styles.footerTitle}>Interactive 3D map (web)</Text>
        <Text style={styles.footerBody}>
          Mobile Reference is the fast lookup view — positions,
          techniques, role breakdowns, and built-out filters. The
          full interactive 3D graph (transitions, position physics,
          filter modes, attached video playback) is a browser
          experience that opens outside the app in your default
          browser.
        </Text>
        <Pressable
          style={styles.footerBridgeBtn}
          onPress={() => openFullMap({})}>
          <Text style={styles.footerBridgeBtnText}>
            Open 3D map in browser ↗
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },

  header: { gap: 4 },
  heading: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 14, opacity: 0.6 },

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
    marginBottom: 4,
  },
  viewingAsName: {
    color: '#d4e157',
    fontWeight: '600',
  },

  chevron: { fontSize: 12, opacity: 0.4, paddingHorizontal: 4 },

  positionDetail: {
    paddingHorizontal: 12,
    paddingBottom: 10,
    paddingTop: 2,
    gap: 4,
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
    marginTop: 8,
    backgroundColor: 'transparent',
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
    paddingVertical: 3,
    paddingHorizontal: 4,
    borderRadius: 6,
    backgroundColor: 'transparent',
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
    marginTop: 12,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(74,158,255,0.06)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(74,158,255,0.45)',
    gap: 4,
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
    alignItems: 'center',
    gap: 6,
    paddingVertical: 4,
    paddingHorizontal: 2,
  },
  transitionRowMuted: {
    opacity: 0.45,
  },
  transitionLabel: {
    flexShrink: 1,
    fontSize: 12,
    color: '#d4dce6',
    lineHeight: 17,
  },
  transitionArrow: {
    fontSize: 13,
    color: '#7fb8ff',
    fontWeight: '700',
    paddingHorizontal: 2,
  },
  transitionDest: {
    fontSize: 12,
    color: '#aab4c2',
    fontWeight: '600',
    flexShrink: 1,
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

  // Coming in from — inverse transition block
  inboundBlock: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(74,158,255,0.04)',
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(74,158,255,0.3)',
    gap: 4,
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
    alignItems: 'center',
    gap: 6,
    paddingVertical: 4,
    paddingHorizontal: 2,
  },
  inboundSource: {
    fontSize: 12,
    color: '#7fb8ff',
    fontWeight: '600',
    textDecorationLine: 'underline',
    flexShrink: 1,
  },
  inboundArrow: {
    fontSize: 13,
    color: '#7fb8ff',
    fontWeight: '700',
    paddingHorizontal: 2,
    opacity: 0.7,
  },
  inboundLabel: {
    flexShrink: 1,
    fontSize: 12,
    color: '#aab4c2',
    lineHeight: 17,
  },

  positionBridgeBtn: {
    marginTop: 12,
    paddingVertical: 9,
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
  progressSummaryClearBtn: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
    marginLeft: 'auto',
  },
  progressSummaryClearText: {
    fontSize: 10,
    color: '#aaa',
    fontWeight: '600',
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
