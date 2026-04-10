/**
 * Reference — mobile knowledge entry point for the Lauburu Grappling Map.
 *
 * First slice: bundled canonical preview. Shows the locked section/position
 * schema from CLAUDE.md so the user can browse the canonical structure
 * without blocking on OPML sync. Technique content and media intentionally
 * live behind an explicit "coming soon" line — this screen never invents
 * BJJ content, that's the website's OPML pipeline.
 *
 * Future drop-in: swap REFERENCE_SECTIONS for a live feed without changing
 * the UI shape. `ReferencePosition` is the stable contract.
 */
import { useMemo, useState } from 'react';
import { StyleSheet, ScrollView, Pressable, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import {
  REFERENCE_SECTIONS,
  REFERENCE_TOTAL_POSITIONS,
  REFERENCE_BUILT_OUT_COUNT,
  type ReferenceSection,
  type ReferencePosition,
} from '../../src/data/reference-seed';

function PositionRow({ position }: { position: ReferencePosition }) {
  const [expanded, setExpanded] = useState(false);
  // Selected perspective index — defaults to 0 (first role in the pair).
  // Future role-specific heading/technique data drops in behind
  // `position.perspectives[selectedRoleIdx]` without changing the UI.
  const [selectedRoleIdx, setSelectedRoleIdx] = useState(0);
  const hasMultipleRoles = position.perspectives.length > 1;
  const selectedRole = position.perspectives[selectedRoleIdx] ?? '';

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
                const isActive = idx === selectedRoleIdx;
                return (
                  <Pressable
                    key={role}
                    style={[
                      styles.rolePill,
                      isActive && styles.rolePillActive,
                    ]}
                    onPress={(ev) => {
                      ev.stopPropagation();
                      setSelectedRoleIdx(idx);
                      // Auto-expand on first role tap so the user sees
                      // the effect of the selection immediately.
                      if (!expanded) setExpanded(true);
                    }}>
                    <Text
                      style={[
                        styles.rolePillText,
                        isActive && styles.rolePillTextActive,
                      ]}>
                      {role}
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
          {/* "Viewing as" subtitle — makes the toggle's effect explicit
              even when the underlying headings are the same for both
              roles in the current bundled seed. Once role-specific
              heading data lands, this subtitle stays and the headings
              list below will swap per-role without any UI change. */}
          {hasMultipleRoles && (
            <Text style={styles.viewingAs}>
              Viewing as <Text style={styles.viewingAsName}>{selectedRole}</Text>
            </Text>
          )}
          <Text style={styles.detailLabel}>Headings</Text>
          {position.headings.map((h) => (
            <Text key={h} style={styles.detailItem}>
              • {h}
            </Text>
          ))}
          <Text style={styles.emptyNote}>
            Technique content and media for {selectedRole || 'this position'}
            {' '}live in the full map — coming to mobile next.
          </Text>
        </View>
      )}
    </View>
  );
}

function SectionBlock({
  section,
  filter,
}: {
  section: ReferenceSection;
  filter: string;
}) {
  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return section.positions;
    return section.positions.filter((p) =>
      p.name.toLowerCase().includes(q),
    );
  }, [section.positions, filter]);

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
          <PositionRow key={p.name} position={p} />
        ))}
      </View>
    </View>
  );
}

export default function ReferenceScreen() {
  const [query, setQuery] = useState('');

  const totalFiltered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return REFERENCE_TOTAL_POSITIONS;
    return REFERENCE_SECTIONS.reduce(
      (acc, s) =>
        acc + s.positions.filter((p) => p.name.toLowerCase().includes(q)).length,
      0,
    );
  }, [query]);

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
          <Text style={styles.summaryValue}>
            {REFERENCE_SECTIONS.length}
          </Text>
          <Text style={styles.summaryLabel}>sections</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{REFERENCE_TOTAL_POSITIONS}</Text>
          <Text style={styles.summaryLabel}>positions</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{REFERENCE_BUILT_OUT_COUNT}</Text>
          <Text style={styles.summaryLabel}>built out</Text>
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

      {query.trim().length > 0 && (
        <Text style={styles.searchMeta}>
          {totalFiltered} position{totalFiltered === 1 ? '' : 's'} match
        </Text>
      )}

      {/* Empty match state */}
      {query.trim().length > 0 && totalFiltered === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>No positions match</Text>
          <Text style={styles.emptyBody}>
            Try a broader search. Techniques and media are not yet in the
            mobile preview.
          </Text>
        </View>
      )}

      {/* Sections */}
      {REFERENCE_SECTIONS.map((s) => (
        <SectionBlock key={s.id} section={s} filter={query} />
      ))}

      {/* Honest footer about scope */}
      <View style={styles.footerCard}>
        <Text style={styles.footerTitle}>Preview catalogue</Text>
        <Text style={styles.footerBody}>
          This is the canonical structure from the Grappling Map schema.
          Technique text, videos, and the interactive 3D graph live on the
          website today — a mobile version is coming in a later batch.
        </Text>
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
  searchMeta: { fontSize: 12, opacity: 0.5, marginTop: -8 },

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
  rolePillText: { fontSize: 11, color: '#888' },
  rolePillTextActive: { color: '#d4e157', fontWeight: '600' },

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
});
