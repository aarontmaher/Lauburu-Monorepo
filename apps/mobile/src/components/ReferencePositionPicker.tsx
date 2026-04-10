/**
 * ReferencePositionPicker — inline picker that links a grappling segment
 * to a canonical position from the Lauburu Grappling Map reference.
 *
 * Writes into `SessionSegment.map_ref.position_key` using the canonical
 * position name as the key. That key is the stable contract — it matches
 * the names in `reference-seed.ts`, which in turn match the locked schema
 * in CLAUDE.md. When the live OPML feed lands, the same key will still
 * point at the same node.
 *
 * UI pattern (intentional):
 *   - Collapsed: one tappable row. Shows the current linked position name
 *     if set, or "Link reference position" placeholder if not.
 *   - Expanded: inline search input + grouped list of all positions from
 *     the reference seed. Tapping a position sets the link and collapses.
 *     If the segment already has a link, an ✕ button clears it without
 *     opening the picker.
 *   - Inline expand-in-place matches the rest of Train's UI (SelectorRow,
 *     segment expand) — no modal, no navigation push, no keyboard surprise.
 *
 * Optional by design: nothing in Train requires a position link; the
 * picker is a progressive-disclosure row that lives inside the already-
 * expanded segment detail.
 */
import { useMemo, useState } from 'react';
import { StyleSheet, Pressable, ScrollView, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import {
  REFERENCE_SECTIONS,
  type ReferencePosition,
  type ReferenceSection,
} from '../data/reference-seed';

export interface ReferencePositionPickerProps {
  /** Currently linked canonical position name, if any. */
  value: string | undefined;
  /** Called with the new position name, or null to clear the link. */
  onChange: (positionName: string | null) => void;
}

/**
 * Find which section a canonical position name belongs to, if any.
 * Used to render the section label alongside a currently-linked position.
 */
function findSectionForPosition(name: string): ReferenceSection | null {
  for (const section of REFERENCE_SECTIONS) {
    if (section.positions.some((p) => p.name === name)) return section;
  }
  return null;
}

export function ReferencePositionPicker({
  value,
  onChange,
}: ReferencePositionPickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [query, setQuery] = useState('');

  const linkedSection = value ? findSectionForPosition(value) : null;

  // Filter the full reference list by a case-insensitive substring query.
  // Empty query shows every section + position so the user can browse.
  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return REFERENCE_SECTIONS;
    return REFERENCE_SECTIONS
      .map((section) => ({
        ...section,
        positions: section.positions.filter((p) =>
          p.name.toLowerCase().includes(q),
        ),
      }))
      .filter((section) => section.positions.length > 0);
  }, [query]);

  const totalMatches = useMemo(
    () =>
      filteredSections.reduce((acc, s) => acc + s.positions.length, 0),
    [filteredSections],
  );

  const handlePick = (position: ReferencePosition) => {
    onChange(position.name);
    setExpanded(false);
    setQuery('');
  };

  const handleClear = () => {
    onChange(null);
    setExpanded(false);
    setQuery('');
  };

  return (
    <View style={styles.wrap}>
      {/* Collapsed header row */}
      <View style={styles.headerRow}>
        <Pressable
          style={styles.headerPressable}
          onPress={() => setExpanded(!expanded)}>
          <Text style={styles.label}>Canonical position</Text>
          <Text style={value ? styles.valueLinked : styles.valuePlaceholder}>
            {value ?? 'Link reference position'}
            {linkedSection ? (
              <Text style={styles.sectionSuffix}> · {linkedSection.label}</Text>
            ) : null}
          </Text>
        </Pressable>
        {value && !expanded && (
          <Pressable onPress={handleClear} hitSlop={8} style={styles.clearBtn}>
            <Text style={styles.clearBtnText}>✕</Text>
          </Pressable>
        )}
        <Pressable
          onPress={() => setExpanded(!expanded)}
          hitSlop={6}
          style={styles.chevronBtn}>
          <Text style={styles.chevron}>{expanded ? '▾' : '▸'}</Text>
        </Pressable>
      </View>

      {/* Expanded picker — search + grouped list */}
      {expanded && (
        <View style={styles.pickerBody}>
          <TextInput
            style={styles.search}
            value={query}
            onChangeText={setQuery}
            placeholder="Search positions…"
            placeholderTextColor="#666"
            autoCorrect={false}
            autoCapitalize="none"
          />
          {query.trim().length > 0 && (
            <Text style={styles.searchMeta}>
              {totalMatches} match{totalMatches === 1 ? '' : 'es'}
            </Text>
          )}

          <ScrollView
            style={styles.listScroll}
            nestedScrollEnabled
            keyboardShouldPersistTaps="handled">
            {filteredSections.length === 0 && (
              <Text style={styles.emptyNote}>
                No positions match that search.
              </Text>
            )}
            {filteredSections.map((section) => (
              <View key={section.id} style={styles.sectionBlock}>
                <Text style={styles.sectionLabel}>{section.label}</Text>
                {section.positions.map((p) => {
                  const isActive = p.name === value;
                  return (
                    <Pressable
                      key={p.name}
                      onPress={() => handlePick(p)}
                      style={[
                        styles.positionRow,
                        isActive && styles.positionRowActive,
                      ]}>
                      <Text
                        style={[
                          styles.positionName,
                          isActive && styles.positionNameActive,
                        ]}>
                        {p.name}
                        {p.built_out ? (
                          <Text style={styles.builtBadge}> · built out</Text>
                        ) : null}
                      </Text>
                      <Text style={styles.positionPersp}>
                        {p.perspectives.join(' · ')}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            ))}
          </ScrollView>

          {value && (
            <Pressable onPress={handleClear} style={styles.clearLinkBtn}>
              <Text style={styles.clearLinkText}>Clear link</Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: 'rgba(255,255,255,0.02)',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 6,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  headerPressable: { flex: 1, gap: 2 },
  label: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  valuePlaceholder: { fontSize: 13, opacity: 0.5 },
  valueLinked: { fontSize: 13, fontWeight: '600', color: '#d4e157' },
  sectionSuffix: { fontSize: 11, opacity: 0.4, fontWeight: '400', color: '#999' },
  clearBtn: { paddingHorizontal: 6, paddingVertical: 4 },
  clearBtnText: { color: '#ff6b6b', fontSize: 13 },
  chevronBtn: { paddingHorizontal: 4, paddingVertical: 4 },
  chevron: { fontSize: 12, opacity: 0.4 },

  pickerBody: {
    marginTop: 4,
    gap: 6,
    paddingTop: 4,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  search: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 13,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  searchMeta: { fontSize: 11, opacity: 0.4 },

  listScroll: {
    maxHeight: 260,
  },
  emptyNote: {
    fontSize: 12,
    opacity: 0.4,
    paddingVertical: 12,
    textAlign: 'center',
  },

  sectionBlock: { marginBottom: 6 },
  sectionLabel: {
    fontSize: 10,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingHorizontal: 4,
    paddingTop: 4,
    paddingBottom: 2,
  },
  positionRow: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 6,
    gap: 2,
  },
  positionRowActive: { backgroundColor: 'rgba(212,225,87,0.12)' },
  positionName: { fontSize: 13, color: '#e0e0e0' },
  positionNameActive: { color: '#d4e157', fontWeight: '600' },
  builtBadge: { fontSize: 10, color: '#d4e157', opacity: 0.8 },
  positionPersp: { fontSize: 10, opacity: 0.4 },

  clearLinkBtn: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#444',
  },
  clearLinkText: { fontSize: 11, color: '#ff6b6b' },
});
