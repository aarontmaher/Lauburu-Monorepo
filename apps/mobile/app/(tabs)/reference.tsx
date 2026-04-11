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
import { useMemo, useState } from 'react';
import { StyleSheet, ScrollView, Pressable, TextInput, Linking } from 'react-native';
import { Text, View } from '@/components/Themed';

/** Live website base URL — the full Reference tree, 3D graph, and
 *  attached media all live here today. The mobile Reference screen
 *  bridges to it via the "Open in full map" CTAs. */
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

function PositionRow({
  position,
  sectionLabel,
}: {
  position: ReferencePosition;
  /** Mobile-seed section label the position belongs to. Threaded
   *  through to the full-map deep link so the web hash handler
   *  receives the correct section segment. */
  sectionLabel: string;
}) {
  const [expanded, setExpanded] = useState(false);
  // Selected perspective index — defaults to 0 (first role in the pair),
  // but switches on mount to whichever role actually has content.
  const [selectedRoleIdx, setSelectedRoleIdx] = useState(0);
  // Inline technique detail expansion — the single technique row that
  // is currently expanded, or null when collapsed. Keyed by
  // `${role}|${heading}|${index}` so switching role/heading resets
  // the expansion cleanly.
  const [expandedTechKey, setExpandedTechKey] = useState<string | null>(null);

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

  // Count of techniques rendered for the CURRENTLY selected role.
  const headingsWithContent = useMemo(() => {
    return position.headings
      .map((h) => ({
        heading: h,
        techs: techniquesForHeading(positionTechs, selectedRole, h),
      }))
      .filter((entry) => entry.techs.length > 0);
  }, [positionTechs, selectedRole, position.headings]);

  const totalForRole = headingsWithContent.reduce(
    (acc, e) => acc + e.techs.length,
    0,
  );

  return (
    <View style={styles.positionWrap}>
      <Pressable
        style={styles.positionRow}
        onPress={() => setExpanded(!expanded)}>
        <View style={{ flex: 1 }}>
          <Text style={styles.positionName}>
            {position.name}
            {position.built_out ? (
              <Text style={styles.builtBadge}> · built out</Text>
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
                              ? 'Part of a built-out position — full text and video live on the web map.'
                              : 'Text and any attached video live on the web map.'}
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
                              View in full map ↗
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

          {/* Position-level full-map bridge. Always rendered on
              expanded positions so the separation between mobile
              Reference and the full web 3D map feels intentional,
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
              Open {position.name} in full map ↗
            </Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

function SectionBlock({
  section,
  filter,
  builtOutOnly,
}: {
  section: ReferenceSection;
  filter: string;
  builtOutOnly: boolean;
}) {
  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return section.positions.filter((p) => {
      if (builtOutOnly && !p.built_out) return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [section.positions, filter, builtOutOnly]);

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
          <PositionRow key={p.name} position={p} sectionLabel={section.label} />
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

  const totalFiltered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return REFERENCE_SECTIONS.reduce(
      (acc, s) =>
        acc +
        s.positions.filter((p) => {
          if (builtOutOnly && !p.built_out) return false;
          if (q && !p.name.toLowerCase().includes(q)) return false;
          return true;
        }).length,
      0,
    );
  }, [query, builtOutOnly]);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <Text style={styles.heading}>Reference</Text>
        <Text style={styles.subtitle}>
          Canonical positions from the Lauburu Grappling Map.
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

      {/* Filter toggles — built-out only. Extensible to more toggles
          later (e.g. role-aware filter, has-video filter) without
          rewiring the screen layout. */}
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
        {(query.trim().length > 0 || builtOutOnly) && (
          <Text style={styles.searchMeta}>
            {totalFiltered} position{totalFiltered === 1 ? '' : 's'}
          </Text>
        )}
      </View>

      {/* Empty match state */}
      {(query.trim().length > 0 || builtOutOnly) && totalFiltered === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>No positions match</Text>
          <Text style={styles.emptyBody}>
            Try a broader search or turn off "Built out only".
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
        />
      ))}

      {/* Full-map bridge footer — stops pretending the 3D map is a
          week away and makes the separation intentional. Tap opens
          the live website Reference + 3D graph in the system browser. */}
      <View style={styles.footerCard}>
        <Text style={styles.footerTitle}>Full 3D map</Text>
        <Text style={styles.footerBody}>
          The interactive 3D graph, position-to-position transitions,
          full technique text, and attached videos live on the website.
          Mobile Reference shows the bundled technique list for quick
          review; the full map is where the graph tools and media
          playback live.
        </Text>
        <Pressable
          style={styles.footerBridgeBtn}
          onPress={() => openFullMap({})}>
          <Text style={styles.footerBridgeBtnText}>
            Open full map ↗
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
