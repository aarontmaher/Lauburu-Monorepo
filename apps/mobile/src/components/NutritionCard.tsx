/**
 * NutritionCard — first real mobile nutrition surface.
 *
 * Shows today's calories + macros + water with a compact edit-in-place
 * flow. Source today is manual entry only; the component reads/writes
 * through `useNutritionStore` which matches the shared `NutritionRecord`
 * shape so a future Cronometer API swap is a drop-in replacement.
 *
 * States:
 *   empty → "No fuel logged yet" + + Log meal button
 *   filled, not editing → 5-cell metric grid + updated-at line + Edit
 *   editing → five inline TextInputs + Save / Cancel
 *
 * When targets are set (via store.setTargets), the metric grid gets a
 * tiny percent-of-target badge under each value. Honest: the badge only
 * renders for fields that actually have a target AND a value.
 */
import { useEffect, useState } from 'react';
import { StyleSheet, Pressable, TextInput, ActivityIndicator, ScrollView, Keyboard } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useNutritionStore } from '../store/nutrition-store';
import { useNutritionEvidenceStore } from '../store/nutrition-evidence-store';
import { NUTRITION_SOURCE_LABELS } from '@lauburu/shared';
import type { NutritionSource } from '@lauburu/shared';
import {
  lookupBarcode,
  macrosForGrams,
  searchByName,
  type OpenFoodFactsProduct,
  type ProductSearchHit,
} from '../services/openfoodfacts';
import { BarcodeScanner } from './BarcodeScanner';
import { submitPhotoProposal, confirmPhotoProposal } from '../services/ai-photo-nutrition';
import { useAuthStore } from '../store/auth-store';
import { NutritionTargetsEditor } from './NutritionTargetsEditor';

/**
 * Entry modes exposed to the user. Ordered by real reliability + speed:
 *   1. Usual routine — one-tap re-add from saved favourites. Fastest
 *      path and zero lookup cost; matches how most people eat day-to-day.
 *   2. Barcode — OpenFoodFacts lookup, accuracy-first.
 *   3. Manual — the always-available fallback.
 *   4. AI photo — experimental, surfaced last and labelled as such so
 *      users don't treat it as a default truth source.
 * Label-scan was previously under Barcode but the OCR path isn't wired
 * yet — removed so the UI doesn't advertise a broken mode.
 */
type EntryMode = 'usual_routine' | 'search' | 'barcode' | 'manual' | 'ai_photo';

const ENTRY_MODES: { id: EntryMode; label: string; source: NutritionSource }[] = [
  { id: 'usual_routine', label: 'Usual routine', source: 'barcode' },
  { id: 'search', label: 'Search food', source: 'barcode' },
  { id: 'barcode', label: 'Barcode', source: 'barcode' },
  { id: 'manual', label: 'Manual', source: 'manual' },
  { id: 'ai_photo', label: 'AI photo · experimental', source: 'ai_estimate' },
];

function formatInt(value: number | undefined | null): string {
  if (value == null) return '—';
  return String(Math.round(value));
}

function formatRelative(iso: string | undefined): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffMs = Date.now() - then;
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function pctOfTarget(value: number | undefined, target: number | undefined): string | null {
  if (value == null || target == null || target === 0) return null;
  const pct = Math.round((value / target) * 100);
  return `${pct}%`;
}

function MetricCell({
  label,
  value,
  unit,
  targetPct,
}: {
  label: string;
  value: string;
  unit: string;
  targetPct: string | null;
}) {
  return (
    <View style={styles.metricCell}>
      <Text style={styles.metricValue}>
        {value}
        <Text style={styles.metricUnit}>{unit}</Text>
      </Text>
      <Text style={styles.metricLabel}>{label}</Text>
      {targetPct ? <Text style={styles.metricPct}>{targetPct} of target</Text> : null}
    </View>
  );
}

type BarcodeLookupState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'found'; product: OpenFoodFactsProduct; grams: string }
  | { phase: 'error'; message: string };

type SearchState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'results'; localHits: ProductSearchHit[]; remoteHits: ProductSearchHit[] }
  | { phase: 'selected'; product: OpenFoodFactsProduct; grams: string; confidence: 'high' | 'medium' | 'low' }
  | { phase: 'error'; message: string };

function confidenceLabel(source: ProductSearchHit['source'], confidence: ProductSearchHit['confidence']): string {
  if (source === 'verified_barcode') return 'Verified barcode';
  if (source === 'database_match') return confidence === 'high' ? 'Database match' : 'Database · partial';
  if (source === 'retailer_web') return 'Retailer/web';
  return 'Estimated';
}

function confidenceColor(source: ProductSearchHit['source']): string {
  if (source === 'verified_barcode') return '#4ade80';
  if (source === 'database_match') return '#d4e157';
  if (source === 'retailer_web') return '#a8b84a';
  return '#ff6b6b';
}

function SearchResultRow({
  hit,
  onPress,
}: {
  hit: ProductSearchHit;
  onPress: () => void;
}) {
  // Prefer the user's remembered serving (for local hits) so the macro
  // preview in the row matches what the next Add will actually log.
  const serving = hit.lastGrams ?? hit.product.serving_size_g ?? 100;
  const servingSource = hit.lastGrams != null ? 'your usual' : 'per serving';
  const k = hit.product.per_100g.calories_kcal;
  const p = hit.product.per_100g.protein_g;
  const c = hit.product.per_100g.carbs_g;
  const f = hit.product.per_100g.fat_g;
  const factor = serving / 100;
  const fmt = (v: number | null): string => v == null ? '—' : String(Math.round(v * factor));
  const fmtGram = (v: number | null): string => v == null ? '—' : `${Math.round((v * factor) * 10) / 10}`;
  return (
    <Pressable onPress={onPress} style={styles.searchResultRow} hitSlop={4}>
      <View style={styles.searchHeaderRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.searchResultName} numberOfLines={1}>
            {hit.product.name}
          </Text>
          {hit.product.brand && (
            <Text style={styles.searchResultBrand} numberOfLines={1}>
              {hit.product.brand}
            </Text>
          )}
        </View>
        <View style={[styles.confidencePill, { borderColor: confidenceColor(hit.source) }]}>
          <Text style={[styles.confidencePillText, { color: confidenceColor(hit.source) }]}>
            {confidenceLabel(hit.source, hit.confidence)}
          </Text>
        </View>
      </View>
      <Text style={styles.searchResultMeta}>
        {serving}g ({servingSource}) · {fmt(k)} kcal · {fmtGram(p)}g P · {fmtGram(c)}g C · {fmtGram(f)}g F
      </Text>
    </Pressable>
  );
}

export function NutritionCard() {
  const today = useNutritionStore((s) => s.today);
  const targets = useNutritionStore((s) => s.targets);
  const updateToday = useNutritionStore((s) => s.updateToday);
  const addToToday = useNutritionStore((s) => s.addToToday);
  const favorites = useNutritionStore((s) => s.favorites);
  const addFavorite = useNutritionStore((s) => s.addFavorite);
  const removeFavorite = useNutritionStore((s) => s.removeFavorite);
  const historyDays = useNutritionStore((s) => s.historyDays);

  const [editing, setEditing] = useState(false);
  const [entryMode, setEntryMode] = useState<EntryMode>('usual_routine');
  const [draftCalories, setDraftCalories] = useState('');
  const [draftProtein, setDraftProtein] = useState('');
  const [draftCarbs, setDraftCarbs] = useState('');
  const [draftFat, setDraftFat] = useState('');
  const [draftFibre, setDraftFibre] = useState('');
  const [draftSugar, setDraftSugar] = useState('');
  const [draftSodium, setDraftSodium] = useState('');
  const [draftWater, setDraftWater] = useState('');
  const [draftWeight, setDraftWeight] = useState('');

  // Barcode flow state — lives alongside the manual draft state so
  // switching between modes preserves both independently.
  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeLookup, setBarcodeLookup] = useState<BarcodeLookupState>({
    phase: 'idle',
  });
  const [scannerOpen, setScannerOpen] = useState(false);

  // Search-food flow state — parallel to barcode so switching between
  // modes preserves both independently.
  const [searchQuery, setSearchQuery] = useState('');
  const [search, setSearch] = useState<SearchState>({ phase: 'idle' });

  // Transient "Added" confirmation banner. Gives instant feedback that
  // the food landed and shows exactly what was added, so the user
  // knows totals updated even before they scroll to the metrics grid.
  const [addedToast, setAddedToast] = useState<{
    name: string;
    kcal: number | null;
    protein: number | null;
  } | null>(null);
  useEffect(() => {
    if (!addedToast) return;
    const t = setTimeout(() => setAddedToast(null), 2800);
    return () => clearTimeout(t);
  }, [addedToast]);
  const addEvidence = useNutritionEvidenceStore((s) => s.addEvidence);
  const confirmEvidence = useNutritionEvidenceStore((s) => s.confirmEvidence);

  /**
   * Layered search: local favourites first (instant match by name/brand),
   * then OpenFoodFacts database search. Local hits carry the same
   * database_match confidence because they're foods the user has
   * already added — a light endorsement beyond a raw database row.
   */
  const runSearch = async () => {
    const q = searchQuery.trim();
    if (q.length < 2) return;
    setSearch({ phase: 'loading' });
    // Local pass — case-insensitive substring over saved favourites
    // (name + brand). Fast, offline, and gives zero-latency results
    // for the user's repeat foods.
    const qLower = q.toLowerCase();
    const terms = qLower.split(/\s+/).filter(Boolean);
    const localHits: ProductSearchHit[] = favorites
      .filter((f) => {
        const hay = `${f.product.name} ${f.product.brand ?? ''}`.toLowerCase();
        return terms.every((t) => hay.includes(t));
      })
      .slice(0, 6)
      .map((f) => ({
        product: f.product,
        source: f.product.barcode && /^\d{6,14}$/.test(f.product.barcode) ? 'verified_barcode' : 'database_match',
        confidence: 'high' as const,
        lastGrams: f.last_grams ?? null,
      }));
    // Remote pass — OpenFoodFacts name search. Fire in parallel; local
    // hits are already in state so the user sees them immediately.
    const remote = await searchByName(q, 12);
    if (!remote.ok) {
      // If remote failed but local has matches, still show local.
      if (localHits.length > 0) {
        setSearch({ phase: 'results', localHits, remoteHits: [] });
        return;
      }
      setSearch({ phase: 'error', message: remote.error });
      return;
    }
    // Dedupe remote against local by barcode to avoid showing the
    // same product twice.
    const localCodes = new Set(localHits.map((h) => h.product.barcode));
    // Re-rank remote hits client-side: complete-macros rows first,
    // then score by how many query terms match in name+brand. OFF's
    // relevance is rough for retailer-prefixed queries like "golden
    // gaytime vegan coles" — this nudges obvious matches to the top.
    const scored = remote.hits
      .filter((h) => !localCodes.has(h.product.barcode))
      .map((h) => {
        const hay = `${h.product.name} ${h.product.brand ?? ''}`.toLowerCase();
        const termScore = terms.reduce((acc, t) => acc + (hay.includes(t) ? 1 : 0), 0);
        const macroComplete = h.product.per_100g.calories_kcal != null && h.product.per_100g.protein_g != null ? 1 : 0;
        return { hit: h, score: macroComplete * 100 + termScore };
      })
      .sort((a, b) => b.score - a.score);
    const remoteHits = scored.map((s) => s.hit);
    setSearch({ phase: 'results', localHits, remoteHits });
  };

  const confirmSearchAdd = () => {
    if (search.phase !== 'selected') return;
    const grams = Number(search.grams);
    if (!Number.isFinite(grams) || grams <= 0) return;
    const macros = macrosForGrams(search.product, grams);
    addToToday(macros, 'barcode');
    // Save to favourites so future searches hit the local layer
    // instantly — user-scoped via secureStorage, no cross-user leak.
    addFavorite(search.product, grams);
    addEvidence({
      source: 'product_search',
      raw: {
        barcode: search.product.barcode,
        photoUri: null,
        productName: search.product.name,
        servingSize: search.product.serving_size_raw,
      },
      calories: search.product.per_100g.calories_kcal,
      protein_g: search.product.per_100g.protein_g,
      carbs_g: search.product.per_100g.carbs_g,
      fat_g: search.product.per_100g.fat_g,
      fibre_g: search.product.per_100g.fibre_g,
      confidence: search.confidence === 'high' ? 'high' : 'medium',
    });
    // Confirmation toast — shows the exact contribution so the user
    // can verify the add without scrolling to recheck the totals.
    setAddedToast({
      name: search.product.name,
      kcal: macros.calories_kcal ?? null,
      protein: macros.protein_g ?? null,
    });
    // Stay in the Search panel but clear the selection + query so the
    // user can immediately type the next food. Common case during a
    // meal log session is three or four items in a row.
    setSearch({ phase: 'idle' });
    setSearchQuery('');
  };

  const runBarcodeLookup = async () => {
    setBarcodeLookup({ phase: 'loading' });
    const result = await lookupBarcode(barcodeInput);
    if (!result.ok) {
      setBarcodeLookup({ phase: 'error', message: result.error });
      return;
    }
    // Default the serving to the product's own serving size if it has
    // one in grams, otherwise fall back to 100g so the user sees per-100g
    // numbers until they override.
    const defaultGrams =
      result.product.serving_size_g != null
        ? String(result.product.serving_size_g)
        : '100';
    setBarcodeLookup({
      phase: 'found',
      product: result.product,
      grams: defaultGrams,
    });
  };

  const confirmBarcodeAdd = () => {
    if (barcodeLookup.phase !== 'found') return;
    const grams = Number(barcodeLookup.grams);
    if (!Number.isFinite(grams) || grams <= 0) return;
    const macros = macrosForGrams(barcodeLookup.product, grams);
    addToToday(macros, 'barcode');
    // Save the product to favorites for quick re-add next time —
    // dedupe + MRU ordering + grams memory is handled by the store.
    addFavorite(barcodeLookup.product, grams);
    setAddedToast({
      name: barcodeLookup.product.name,
      kcal: macros.calories_kcal ?? null,
      protein: macros.protein_g ?? null,
    });
    // Reset barcode state and exit editing so the user sees updated totals.
    setBarcodeInput('');
    setBarcodeLookup({ phase: 'idle' });
    setEntryMode('usual_routine');
    setEditing(false);
  };

  /**
   * Tap a saved favorite → skip the network lookup and go straight to
   * the review state with the cached product + its last grams, so
   * re-adding a regular food is instant and offline-friendly.
   */
  const openFavoriteForReview = (favoriteIndex: number) => {
    const fav = favorites[favoriteIndex];
    if (!fav) return;
    setBarcodeInput(fav.product.barcode);
    setBarcodeLookup({
      phase: 'found',
      product: fav.product,
      grams:
        fav.last_grams != null
          ? String(fav.last_grams)
          : fav.product.serving_size_g != null
            ? String(fav.product.serving_size_g)
            : '100',
    });
  };

  const handleBarcodeScan = async (barcode: string) => {
    setScannerOpen(false);
    setBarcodeInput(barcode);
    // Auto-run lookup after camera scan.
    setBarcodeLookup({ phase: 'loading' });
    const result = await lookupBarcode(barcode);
    if (!result.ok) {
      setBarcodeLookup({ phase: 'error', message: result.error });
      return;
    }
    const defaultGrams =
      result.product.serving_size_g != null
        ? String(result.product.serving_size_g)
        : '100';
    setBarcodeLookup({ phase: 'found', product: result.product, grams: defaultGrams });
    // Record evidence for audit trail.
    addEvidence({
      source: 'barcode_scan',
      raw: {
        barcode,
        photoUri: null,
        productName: result.product.name,
        servingSize: result.product.serving_size_raw,
      },
      calories: result.product.per_100g.calories_kcal,
      protein_g: result.product.per_100g.protein_g,
      carbs_g: result.product.per_100g.carbs_g,
      fat_g: result.product.per_100g.fat_g,
      fibre_g: result.product.per_100g.fibre_g,
      confidence: 'high',
    });
  };

  const resetBarcodeLookup = () => {
    setBarcodeLookup({ phase: 'idle' });
  };

  const startEdit = () => {
    setDraftCalories(today?.calories_kcal?.toString() ?? '');
    setDraftProtein(today?.protein_g?.toString() ?? '');
    setDraftCarbs(today?.carbs_g?.toString() ?? '');
    setDraftFat(today?.fat_g?.toString() ?? '');
    setDraftFibre(today?.fibre_g?.toString() ?? '');
    setDraftSugar(today?.sugar_g?.toString() ?? '');
    setDraftSodium(today?.sodium_mg?.toString() ?? '');
    setDraftWater(today?.water_ml?.toString() ?? '');
    setDraftWeight(today?.body_weight_kg?.toString() ?? '');
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
  };

  const saveEdit = () => {
    const parseOpt = (s: string): number | undefined => {
      if (!s.trim()) return undefined;
      const n = Number(s);
      return Number.isFinite(n) ? n : undefined;
    };
    updateToday({
      calories_kcal: parseOpt(draftCalories),
      protein_g: parseOpt(draftProtein),
      carbs_g: parseOpt(draftCarbs),
      fat_g: parseOpt(draftFat),
      fibre_g: parseOpt(draftFibre),
      sugar_g: parseOpt(draftSugar),
      sodium_mg: parseOpt(draftSodium),
      water_ml: parseOpt(draftWater),
      body_weight_kg: parseOpt(draftWeight),
    });
    setEditing(false);
  };

  const hasAnyValue =
    today &&
    (today.calories_kcal != null ||
      today.protein_g != null ||
      today.carbs_g != null ||
      today.fat_g != null ||
      today.water_ml != null);

  const sourceLabel = today ? NUTRITION_SOURCE_LABELS[today.source] : null;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.cardTitle}>Nutrition</Text>
          <Text style={styles.sourceLabel}>
            {sourceLabel ? `${sourceLabel} · today` : 'No nutrition logged · today'}
          </Text>
        </View>
        {!editing && (
          <Pressable onPress={startEdit} style={styles.editBtn} hitSlop={6}>
            <Text style={styles.editBtnText}>{hasAnyValue ? 'Edit' : '+ Log'}</Text>
          </Pressable>
        )}
      </View>

      {/* Always-visible quick-action row. The full edit sheet is
          behind a single tap to any of these chips — no more hunting
          inside the '+ Log' flow to find Search or Barcode. Order
          matches the product direction: Search first (fastest for
          "I don't have a barcode on me"), then Barcode, then Manual. */}
      {!editing && (
        <View style={styles.quickActionRow}>
          <Pressable
            onPress={() => { setEntryMode('search'); setEditing(true); }}
            style={[styles.quickActionChip, styles.quickActionChipPrimary]}
            hitSlop={4}
          >
            <Text style={styles.quickActionChipTextPrimary}>Search food</Text>
          </Pressable>
          <Pressable
            onPress={() => { setEntryMode('barcode'); setEditing(true); }}
            style={styles.quickActionChip}
            hitSlop={4}
          >
            <Text style={styles.quickActionChipText}>Barcode</Text>
          </Pressable>
          <Pressable
            onPress={() => { setEntryMode('manual'); setEditing(true); }}
            style={styles.quickActionChip}
            hitSlop={4}
          >
            <Text style={styles.quickActionChipText}>Manual</Text>
          </Pressable>
          {favorites.length > 0 && (
            <Pressable
              onPress={() => { setEntryMode('usual_routine'); setEditing(true); }}
              style={styles.quickActionChip}
              hitSlop={4}
            >
              <Text style={styles.quickActionChipText}>Usual</Text>
            </Pressable>
          )}
        </View>
      )}

      {!editing && <NutritionTargetsEditor />}

      {/* Transient confirmation banner — renders right under the
          header so instantaneous adds have visible feedback. Totals
          below update in parallel via the zustand store. */}
      {addedToast && (
        <View style={styles.addedToast}>
          <Text style={styles.addedToastTitle} numberOfLines={1}>
            Added: {addedToast.name}
          </Text>
          <Text style={styles.addedToastMeta}>
            {addedToast.kcal != null ? `+${addedToast.kcal} kcal` : ''}
            {addedToast.kcal != null && addedToast.protein != null ? ' · ' : ''}
            {addedToast.protein != null ? `+${addedToast.protein} g protein` : ''}
          </Text>
        </View>
      )}

      {/* Empty state */}
      {!editing && !hasAnyValue && (
        <Text style={styles.emptyText}>
          No fuel logged yet today. Tap + Log to enter manually, scan a barcode, or pull from Apple Health.
        </Text>
      )}

      {/* Display mode */}
      {!editing && hasAnyValue && today && (
        <>
          {/* Protein-per-kg headline — shown only when weight + protein
              are both logged. This is the single most useful fueling
              number for a strength/grappling athlete, so surface it
              prominently rather than burying it inside the Coach. */}
          {today.protein_g != null && today.body_weight_kg != null && today.body_weight_kg > 0 && (() => {
            const perKg = today.protein_g / today.body_weight_kg;
            const color = perKg < 1.2 ? '#ff6b6b' : perKg <= 2.2 ? '#4ade80' : '#d4e157';
            // If below training target (1.6 g/kg), compute the exact
            // grams needed to reach 1.6 g/kg. Makes the fix actionable.
            const targetPerKg = 1.6;
            const gramsNeeded = perKg < targetPerKg
              ? Math.round(targetPerKg * today.body_weight_kg - today.protein_g)
              : 0;
            return (
              <>
                <Text style={[styles.trendLine, { color, fontWeight: '700' }]}>
                  {perKg.toFixed(1)} g protein / kg{perKg < 1.2 ? ' — below 1.6 g/kg training target' : perKg <= 2.2 ? '' : ' — on the high end'}
                </Text>
                {gramsNeeded > 0 && (
                  <Text style={[styles.trendLine, { color: '#d4e157' }]}>
                    Need ~{gramsNeeded}g more protein today to hit 1.6 g/kg.
                  </Text>
                )}
              </>
            );
          })()}
          <View style={styles.metricsGrid}>
            <MetricCell
              label="Calories"
              value={formatInt(today.calories_kcal)}
              unit=" kcal"
              targetPct={pctOfTarget(today.calories_kcal, targets?.calories_kcal)}
            />
            <MetricCell
              label="Protein"
              value={formatInt(today.protein_g)}
              unit=" g"
              targetPct={pctOfTarget(today.protein_g, targets?.protein_g)}
            />
            <MetricCell
              label="Carbs"
              value={formatInt(today.carbs_g)}
              unit=" g"
              targetPct={pctOfTarget(today.carbs_g, targets?.carbs_g)}
            />
            <MetricCell
              label="Fat"
              value={formatInt(today.fat_g)}
              unit=" g"
              targetPct={pctOfTarget(today.fat_g, targets?.fat_g)}
            />
            <MetricCell
              label="Water"
              value={formatInt(today.water_ml)}
              unit=" ml"
              targetPct={null}
            />
            {today.fibre_g != null && (
              <MetricCell
                label="Fibre"
                value={formatInt(today.fibre_g)}
                unit=" g"
                targetPct={null}
              />
            )}
            {today.sugar_g != null && (
              <MetricCell
                label="Sugar"
                value={formatInt(today.sugar_g)}
                unit=" g"
                targetPct={null}
              />
            )}
            {today.sodium_mg != null && (
              <MetricCell
                label="Sodium"
                value={formatInt(today.sodium_mg)}
                unit=" mg"
                targetPct={null}
              />
            )}
            {today.body_weight_kg != null && (
              <MetricCell
                label="Weight"
                value={today.body_weight_kg.toFixed(1)}
                unit=" kg"
                targetPct={null}
              />
            )}
          </View>
          <Text style={styles.updatedAt}>
            Updated {formatRelative(today.updated_at)}
          </Text>
          {/* Multi-day trend cue — single line, shown only when at least
              2 history days exist so a brand-new user doesn't see it. */}
          {historyDays.length >= 2 && (() => {
            const recent = historyDays.slice(0, 7);
            const cals = recent
              .map((d) => d.calories_kcal)
              .filter((v): v is number => v != null);
            const protein = recent
              .map((d) => d.protein_g)
              .filter((v): v is number => v != null);
            const avgCal =
              cals.length > 0
                ? Math.round(cals.reduce((a, b) => a + b, 0) / cals.length)
                : null;
            const avgProtein =
              protein.length > 0
                ? Math.round(protein.reduce((a, b) => a + b, 0) / protein.length)
                : null;
            if (avgCal == null && avgProtein == null) return null;
            const parts: string[] = [];
            if (avgCal != null) parts.push(`${avgCal} kcal`);
            if (avgProtein != null) parts.push(`${avgProtein}g protein`);
            return (
              <Text style={styles.trendLine}>
                {recent.length}-day avg: {parts.join(' · ')}
              </Text>
            );
          })()}
        </>
      )}

      {/* Edit mode */}
      {editing && (
        <>
          {/* Entry mode picker — ordering: Usual routine, Search food,
              Barcode, Manual, AI photo (experimental). Label scan was
              removed in favour of product-name Search, which covers
              the same "no barcode handy" case via OpenFoodFacts. */}
          <View style={styles.modeRow}>
            {ENTRY_MODES.map((m) => {
              const isActive = entryMode === m.id;
              return (
                <Pressable
                  key={m.id}
                  style={[styles.modePill, isActive && styles.modePillActive]}
                  onPress={() => setEntryMode(m.id)}>
                  <Text
                    style={[
                      styles.modePillText,
                      isActive && styles.modePillTextActive,
                    ]}>
                    {m.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {/* Usual routine — one-tap re-add from favourites */}
          {entryMode === 'usual_routine' && (
            <View style={styles.placeholderPanel}>
              {favorites.length === 0 ? (
                <>
                  <Text style={styles.placeholderTitle}>No saved favourites yet</Text>
                  <Text style={styles.placeholderBody}>
                    Scan a barcode once and the product is saved here for
                    one-tap re-add on the days you eat the same thing.
                  </Text>
                </>
              ) : (
                <>
                  <Text style={styles.placeholderTitle}>Tap to add your usual</Text>
                  {favorites.slice(0, 8).map((fav, i) => (
                    <Pressable
                      key={`${fav.product.barcode}-${i}`}
                      onPress={() => {
                        openFavoriteForReview(i);
                        setEntryMode('barcode');
                      }}
                      style={styles.favoriteRow}
                      hitSlop={6}
                    >
                      <Text style={styles.favoriteName} numberOfLines={1}>
                        {fav.product.name}
                      </Text>
                      <Text style={styles.favoriteMeta}>
                        {fav.last_grams ?? fav.product.serving_size_g ?? 100} g
                      </Text>
                    </Pressable>
                  ))}
                </>
              )}
            </View>
          )}

          {/* Search food — product-name search with layered sources:
              local favourites first (instant), then OpenFoodFacts name
              search. Confidence/source labels are explicit so users
              can see which rows are database-grade vs estimates. */}
          {entryMode === 'search' && (
            <View style={styles.barcodePanel}>
              {(search.phase === 'idle' || search.phase === 'error') && (
                <>
                  <Text style={styles.placeholderHint}>
                    Search by product + brand + retailer for best hits — e.g. "golden gaytime vegan coles".
                  </Text>
                  <View style={styles.barcodeInputRow}>
                    <TextInput
                      value={searchQuery}
                      onChangeText={setSearchQuery}
                      placeholder="e.g. greek yogurt woolworths"
                      placeholderTextColor="#666"
                      style={styles.barcodeInput}
                      returnKeyType="search"
                      onSubmitEditing={() => {
                        Keyboard.dismiss();
                        void runSearch();
                      }}
                    />
                    {searchQuery.length > 0 && (
                      <Pressable
                        onPress={() => setSearchQuery('')}
                        hitSlop={8}
                        style={styles.searchClearBtn}
                      >
                        <Text style={styles.searchClearText}>×</Text>
                      </Pressable>
                    )}
                    <Pressable
                      onPress={() => { Keyboard.dismiss(); void runSearch(); }}
                      style={styles.barcodeLookupBtn}
                      disabled={searchQuery.trim().length < 2}
                    >
                      <Text style={styles.barcodeLookupBtnText}>Search</Text>
                    </Pressable>
                  </View>
                  {search.phase === 'error' && (
                    <Text style={styles.barcodeError}>{search.message}</Text>
                  )}
                </>
              )}

              {search.phase === 'loading' && (
                <View style={styles.barcodeLoadingRow}>
                  <ActivityIndicator size="small" color="#d4e157" />
                  <Text style={styles.barcodeLoadingText}>Searching for "{searchQuery}"…</Text>
                </View>
              )}

              {search.phase === 'results' && (
                <>
                  <View style={styles.searchResultsHeader}>
                    <Text style={styles.searchResultsHeaderText} numberOfLines={1}>
                      Results for "{searchQuery}"
                    </Text>
                    <Pressable
                      onPress={() => { setSearch({ phase: 'idle' }); setSearchQuery(''); }}
                      hitSlop={6}
                    >
                      <Text style={styles.searchResultsReset}>New search</Text>
                    </Pressable>
                  </View>
                  <ScrollView style={{ maxHeight: 360 }}>
                  {search.localHits.length === 0 && search.remoteHits.length === 0 && (
                    <Text style={styles.barcodeError}>No matches. Try fewer / different words, or use Manual.</Text>
                  )}
                  {search.localHits.length > 0 && (
                    <>
                      <Text style={styles.searchGroupHeader}>From your saved foods</Text>
                      {search.localHits.map((hit, i) => (
                        <SearchResultRow
                          key={`local-${hit.product.barcode}-${i}`}
                          hit={hit}
                          onPress={() => setSearch({
                            phase: 'selected',
                            product: hit.product,
                            // Prefer the grams this user last ate of this
                            // product; fall back to package serving, then
                            // to 100g. Makes repeat foods one tap + Add.
                            grams: hit.lastGrams != null
                              ? String(hit.lastGrams)
                              : hit.product.serving_size_g != null ? String(hit.product.serving_size_g) : '100',
                            confidence: hit.confidence,
                          })}
                        />
                      ))}
                    </>
                  )}
                  {search.remoteHits.length > 0 && (
                    <>
                      <Text style={styles.searchGroupHeader}>Database matches</Text>
                      {search.remoteHits.map((hit, i) => (
                        <SearchResultRow
                          key={`remote-${hit.product.barcode}-${i}`}
                          hit={hit}
                          onPress={() => setSearch({
                            phase: 'selected',
                            product: hit.product,
                            grams: hit.product.serving_size_g != null ? String(hit.product.serving_size_g) : '100',
                            confidence: hit.confidence,
                          })}
                        />
                      ))}
                    </>
                  )}
                </ScrollView>
                </>
              )}

              {search.phase === 'selected' && (() => {
                const grams = Number(search.grams);
                const validGrams = Number.isFinite(grams) && grams > 0;
                const preview = validGrams ? macrosForGrams(search.product, grams) : null;
                return (
                  <View style={{ gap: 10 }}>
                    <View style={styles.searchHeaderRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.searchResultName}>{search.product.name}</Text>
                        {search.product.brand && (
                          <Text style={styles.searchResultBrand}>{search.product.brand}</Text>
                        )}
                      </View>
                      <View style={[styles.confidencePill, { borderColor: confidenceColor('database_match') }]}>
                        <Text style={[styles.confidencePillText, { color: confidenceColor('database_match') }]}>
                          {confidenceLabel('database_match', search.confidence)}
                        </Text>
                      </View>
                    </View>
                    <View style={styles.barcodeInputRow}>
                      <TextInput
                        value={search.grams}
                        onChangeText={(g) => setSearch((prev) => prev.phase === 'selected' ? { ...prev, grams: g } : prev)}
                        placeholder="grams"
                        placeholderTextColor="#666"
                        keyboardType="numeric"
                        style={styles.barcodeInput}
                      />
                      <Text style={styles.barcodeUnit}>g</Text>
                    </View>
                    {preview && (
                      <View style={styles.searchPreviewGrid}>
                        <Text style={styles.searchPreviewCell}>{preview.calories_kcal ?? '—'} kcal</Text>
                        <Text style={styles.searchPreviewCell}>{preview.protein_g ?? '—'} P</Text>
                        <Text style={styles.searchPreviewCell}>{preview.carbs_g ?? '—'} C</Text>
                        <Text style={styles.searchPreviewCell}>{preview.fat_g ?? '—'} F</Text>
                      </View>
                    )}
                    <View style={styles.barcodeActionRow}>
                      <Pressable onPress={() => setSearch({ phase: 'idle' })} style={styles.barcodeCancelBtn}>
                        <Text style={styles.barcodeCancelText}>Back</Text>
                      </Pressable>
                      <Pressable
                        onPress={() => confirmSearchAdd()}
                        style={styles.barcodeLookupBtn}
                        disabled={!validGrams}
                      >
                        <Text style={styles.barcodeLookupBtnText}>Add to today</Text>
                      </Pressable>
                    </View>
                  </View>
                );
              })()}
            </View>
          )}

          {/* Barcode flow — real Open Food Facts lookup + review + add */}
          {entryMode === 'barcode' && (
            <View style={styles.barcodePanel}>
              {/* Idle / error state — favorites strip + barcode input + Lookup */}
              {(barcodeLookup.phase === 'idle' ||
                barcodeLookup.phase === 'error') && (
                <>
                  {/* Quick-add favorites strip — saved products from
                      previous scans. Tap to jump straight to review
                      with the cached product + last grams, no network.
                      Most-recently-used first, capped at 12 in the
                      store. Hidden entirely when the list is empty. */}
                  {favorites.length > 0 && (
                    <View style={styles.favoritesBlock}>
                      <Text style={styles.favoritesLabel}>Quick add</Text>
                      <ScrollView
                        horizontal
                        showsHorizontalScrollIndicator={false}
                        keyboardShouldPersistTaps="handled">
                        <View style={styles.favoritesRow}>
                          {favorites.map((fav, i) => (
                            <Pressable
                              key={fav.product.barcode}
                              style={styles.favoritePill}
                              onPress={() => openFavoriteForReview(i)}
                              onLongPress={() =>
                                removeFavorite(fav.product.barcode)
                              }
                              delayLongPress={500}>
                              <Text
                                style={styles.favoritePillName}
                                numberOfLines={1}>
                                {fav.product.name}
                              </Text>
                              {fav.product.brand ? (
                                <Text
                                  style={styles.favoritePillBrand}
                                  numberOfLines={1}>
                                  {fav.product.brand}
                                </Text>
                              ) : null}
                              {fav.last_grams != null ? (
                                <Text style={styles.favoritePillGrams}>
                                  {fav.last_grams}g
                                </Text>
                              ) : null}
                            </Pressable>
                          ))}
                        </View>
                      </ScrollView>
                      <Text style={styles.favoritesHint}>
                        Long-press a favorite to remove it.
                      </Text>
                    </View>
                  )}

                  <Text style={styles.barcodeHint}>
                    Scan a barcode or type it manually. Lookup uses the
                    free Open Food Facts database.
                  </Text>
                  <Pressable
                    style={styles.scanCameraBtn}
                    onPress={() => setScannerOpen(true)}>
                    <Text style={styles.scanCameraBtnText}>Scan with camera</Text>
                  </Pressable>
                  <Text style={styles.barcodeOrDivider}>or type manually</Text>
                  <TextInput
                    style={styles.editInput}
                    value={barcodeInput}
                    onChangeText={setBarcodeInput}
                    keyboardType="number-pad"
                    placeholder="Barcode (6–14 digits)"
                    placeholderTextColor="#555"
                    maxLength={14}
                  />
                  {barcodeLookup.phase === 'error' && (
                    <Text style={styles.barcodeError}>
                      {barcodeLookup.message}
                    </Text>
                  )}
                  <Pressable
                    style={[
                      styles.barcodeLookupBtn,
                      !barcodeInput.trim() && { opacity: 0.4 },
                    ]}
                    onPress={runBarcodeLookup}
                    disabled={!barcodeInput.trim()}>
                    <Text style={styles.barcodeLookupBtnText}>Look up</Text>
                  </Pressable>
                </>
              )}

              {/* Loading state */}
              {barcodeLookup.phase === 'loading' && (
                <View style={styles.barcodeLoadingRow}>
                  <ActivityIndicator size="small" color="#d4e157" />
                  <Text style={styles.barcodeHint}>
                    Looking up {barcodeInput}…
                  </Text>
                </View>
              )}

              {/* Found state — review panel with grams input + computed macros */}
              {barcodeLookup.phase === 'found' && (
                <>
                  <View style={styles.productHeaderRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.productName}>
                        {barcodeLookup.product.name}
                      </Text>
                      {barcodeLookup.product.brand && (
                        <Text style={styles.productBrand}>
                          {barcodeLookup.product.brand}
                        </Text>
                      )}
                      {barcodeLookup.product.serving_size_raw && (
                        <Text style={styles.productServing}>
                          Package serving · {barcodeLookup.product.serving_size_raw}
                        </Text>
                      )}
                    </View>
                    <Pressable onPress={resetBarcodeLookup} hitSlop={6}>
                      <Text style={styles.productResetText}>✕</Text>
                    </Pressable>
                  </View>

                  <View style={styles.editField}>
                    <Text style={styles.editLabel}>Grams consumed</Text>
                    <TextInput
                      style={styles.editInput}
                      value={barcodeLookup.grams}
                      onChangeText={(t) =>
                        setBarcodeLookup({
                          phase: 'found',
                          product: barcodeLookup.product,
                          grams: t,
                        })
                      }
                      keyboardType="number-pad"
                      placeholder="100"
                      placeholderTextColor="#555"
                    />
                  </View>

                  {/* Live-computed macros for the current grams value */}
                  {(() => {
                    const grams = Number(barcodeLookup.grams);
                    const valid = Number.isFinite(grams) && grams > 0;
                    const macros = valid
                      ? macrosForGrams(barcodeLookup.product, grams)
                      : null;
                    return (
                      <View style={styles.metricsGrid}>
                        <MetricCell
                          label="Calories"
                          value={formatInt(macros?.calories_kcal)}
                          unit=" kcal"
                          targetPct={null}
                        />
                        <MetricCell
                          label="Protein"
                          value={formatInt(macros?.protein_g)}
                          unit=" g"
                          targetPct={null}
                        />
                        <MetricCell
                          label="Carbs"
                          value={formatInt(macros?.carbs_g)}
                          unit=" g"
                          targetPct={null}
                        />
                        <MetricCell
                          label="Fat"
                          value={formatInt(macros?.fat_g)}
                          unit=" g"
                          targetPct={null}
                        />
                      </View>
                    );
                  })()}

                  <Text style={styles.barcodeHint}>
                    Confirm to add these macros to today's total. Provenance
                    will be recorded as Barcode for audit.
                  </Text>
                  <View style={styles.editActions}>
                    <Pressable onPress={resetBarcodeLookup} style={styles.cancelBtn}>
                      <Text style={styles.cancelBtnText}>Back</Text>
                    </Pressable>
                    <Pressable onPress={confirmBarcodeAdd} style={styles.saveBtn}>
                      <Text style={styles.saveBtnText}>Add to today</Text>
                    </Pressable>
                  </View>
                </>
              )}
            </View>
          )}

          {/* AI photo — capture meal, propose macros, confirm before logging */}
          {entryMode === 'ai_photo' && (
            <View style={styles.barcodePanel}>
              <Text style={styles.barcodeHint}>
                Take a photo of your meal. AI estimation is not yet available
                — enter the macros manually after capture. Only confirmed
                entries count toward your nutrition total.
              </Text>
              <Text style={styles.barcodeHint}>
                Ranking: Barcode {'>'} Search {'>'} Manual {'>'} AI photo.
                AI photo estimates always require your review.
              </Text>
              <View style={styles.editGrid}>
                <View style={styles.editField}>
                  <Text style={styles.editLabel}>Calories (kcal)</Text>
                  <TextInput
                    style={styles.editInput}
                    value={draftCalories}
                    onChangeText={setDraftCalories}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.editField}>
                  <Text style={styles.editLabel}>Protein (g)</Text>
                  <TextInput
                    style={styles.editInput}
                    value={draftProtein}
                    onChangeText={setDraftProtein}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.editField}>
                  <Text style={styles.editLabel}>Carbs (g)</Text>
                  <TextInput
                    style={styles.editInput}
                    value={draftCarbs}
                    onChangeText={setDraftCarbs}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#555"
                  />
                </View>
                <View style={styles.editField}>
                  <Text style={styles.editLabel}>Fat (g)</Text>
                  <TextInput
                    style={styles.editInput}
                    value={draftFat}
                    onChangeText={setDraftFat}
                    keyboardType="number-pad"
                    placeholder="—"
                    placeholderTextColor="#555"
                  />
                </View>
              </View>
              <Pressable
                style={styles.barcodeLookupBtn}
                onPress={() => {
                  const parseOpt = (s: string) => { const n = Number(s); return Number.isFinite(n) ? n : undefined; };
                  const macros = {
                    calories_kcal: parseOpt(draftCalories),
                    protein_g: parseOpt(draftProtein),
                    carbs_g: parseOpt(draftCarbs),
                    fat_g: parseOpt(draftFat),
                  };
                  if (macros.calories_kcal == null && macros.protein_g == null) return;
                  addToToday(macros, 'ai_estimate');
                  // Record as confirmed photo evidence
                  addEvidence({
                    source: 'ai_photo_estimate',
                    raw: { barcode: null, photoUri: null, productName: 'AI photo meal', servingSize: null },
                    calories: macros.calories_kcal ?? null,
                    protein_g: macros.protein_g ?? null,
                    carbs_g: macros.carbs_g ?? null,
                    fat_g: macros.fat_g ?? null,
                    confidence: 'low',
                    missingFields: [
                      ...(macros.calories_kcal == null ? ['calories'] : []),
                      ...(macros.protein_g == null ? ['protein'] : []),
                      ...(macros.carbs_g == null ? ['carbs'] : []),
                      ...(macros.fat_g == null ? ['fat'] : []),
                    ],
                  });
                  setDraftCalories('');
                  setDraftProtein('');
                  setDraftCarbs('');
                  setDraftFat('');
                  setEntryMode('manual');
                  setEditing(false);
                }}>
                <Text style={styles.barcodeLookupBtnText}>Add as AI photo estimate</Text>
              </Pressable>
            </View>
          )}

          {/* Manual entry grid — the only live entry path today */}
          {entryMode === 'manual' && (
          <View style={styles.editGrid}>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Calories (kcal)</Text>
              <TextInput
                style={styles.editInput}
                value={draftCalories}
                onChangeText={setDraftCalories}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Protein (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftProtein}
                onChangeText={setDraftProtein}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Carbs (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftCarbs}
                onChangeText={setDraftCarbs}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Fat (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftFat}
                onChangeText={setDraftFat}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Water (ml)</Text>
              <TextInput
                style={styles.editInput}
                value={draftWater}
                onChangeText={setDraftWater}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Fibre (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftFibre}
                onChangeText={setDraftFibre}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Weight (kg)</Text>
              <TextInput
                style={styles.editInput}
                value={draftWeight}
                onChangeText={setDraftWeight}
                keyboardType="decimal-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Sugar (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftSugar}
                onChangeText={setDraftSugar}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Sodium (mg)</Text>
              <TextInput
                style={styles.editInput}
                value={draftSodium}
                onChangeText={setDraftSodium}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
          </View>
          )}

          {/* Action row — Save only shows for Manual; AI photo
              placeholders show just Close; Barcode mode has its own internal
              Back + Add to today buttons so the shared action row is hidden
              for that mode entirely. */}
          {entryMode !== 'barcode' && (
            <View style={styles.editActions}>
              <Pressable onPress={cancelEdit} style={styles.cancelBtn}>
                <Text style={styles.cancelBtnText}>
                  {entryMode === 'manual' ? 'Cancel' : 'Close'}
                </Text>
              </Pressable>
              {entryMode === 'manual' && (
                <Pressable onPress={saveEdit} style={styles.saveBtn}>
                  <Text style={styles.saveBtnText}>Save</Text>
                </Pressable>
              )}
            </View>
          )}
        </>
      )}
      <BarcodeScanner
        visible={scannerOpen}
        onScanned={handleBarcodeScan}
        onClose={() => setScannerOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  titleBlock: { gap: 2 },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  sourceLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#d4e157',
  },
  editBtnText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },

  emptyText: { fontSize: 13, opacity: 0.5, lineHeight: 18 },

  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  metricCell: {
    minWidth: '30%',
    flexGrow: 1,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 2,
  },
  metricValue: { fontSize: 16, fontWeight: '700', color: '#d4e157' },
  metricUnit: { fontSize: 11, opacity: 0.5, fontWeight: '500' },
  metricLabel: { fontSize: 11, opacity: 0.5 },
  metricPct: { fontSize: 10, color: '#a8b84a', opacity: 0.8 },

  updatedAt: { fontSize: 11, opacity: 0.4 },
  trendLine: { fontSize: 11, opacity: 0.5, color: '#a8b84a', marginTop: 2 },

  modeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  modePill: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#444',
  },
  modePillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  modePillText: { fontSize: 12, color: '#999' },
  modePillTextActive: { color: '#d4e157', fontWeight: '600' },

  placeholderPanel: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.05)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 6,
  },
  placeholderTitle: {
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  placeholderBody: { fontSize: 12, opacity: 0.7, lineHeight: 17 },
  placeholderHint: { fontSize: 11, opacity: 0.45, lineHeight: 15, fontStyle: 'italic' },
  favoriteRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.04)',
    marginTop: 4,
  },
  favoriteName: { fontSize: 13, flex: 1, marginRight: 8 },
  favoriteMeta: { fontSize: 11, opacity: 0.6, fontWeight: '600' },
  searchGroupHeader: {
    fontSize: 10,
    color: '#d4e157',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 8,
    marginBottom: 4,
  },
  searchResultRow: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.04)',
    marginBottom: 6,
    gap: 4,
  },
  searchHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  searchResultName: { fontSize: 13, fontWeight: '600' },
  searchResultBrand: { fontSize: 11, opacity: 0.6, marginTop: 1 },
  searchResultMeta: { fontSize: 11, opacity: 0.7 },
  searchPreviewGrid: {
    flexDirection: 'row',
    gap: 10,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(212,225,87,0.08)',
    flexWrap: 'wrap',
  },
  searchPreviewCell: { fontSize: 12, color: '#d4e157', fontWeight: '600' },
  confidencePill: {
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 999,
    borderWidth: 1,
  },
  confidencePillText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.3 },
  barcodeInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  barcodeInput: {
    flex: 1,
    backgroundColor: '#0a0a0a',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    color: '#fff',
    fontSize: 13,
  },
  barcodeUnit: { fontSize: 12, opacity: 0.6, fontWeight: '600', paddingHorizontal: 4 },
  barcodeLoadingText: { fontSize: 12, opacity: 0.7 },
  barcodeActionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  barcodeCancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  barcodeCancelText: { fontSize: 13, opacity: 0.7 },
  addedToast: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(74,222,128,0.12)',
    borderLeftWidth: 3,
    borderLeftColor: '#4ade80',
    gap: 2,
  },
  addedToastTitle: { fontSize: 12, color: '#4ade80', fontWeight: '700' },
  addedToastMeta: { fontSize: 11, color: '#4ade80', opacity: 0.8 },
  quickActionRow: {
    flexDirection: 'row',
    gap: 6,
    marginTop: 8,
    flexWrap: 'wrap',
  },
  quickActionChip: {
    paddingVertical: 7,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  quickActionChipPrimary: {
    backgroundColor: 'rgba(212,225,87,0.12)',
    borderColor: '#d4e157',
  },
  quickActionChipText: { fontSize: 12, color: '#ccc', fontWeight: '600' },
  quickActionChipTextPrimary: { fontSize: 12, color: '#d4e157', fontWeight: '700' },
  searchClearBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  searchClearText: { color: '#999', fontSize: 16, fontWeight: '700', lineHeight: 18 },
  searchResultsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
    marginBottom: 4,
  },
  searchResultsHeaderText: { fontSize: 12, opacity: 0.7, flex: 1, marginRight: 8 },
  searchResultsReset: { fontSize: 12, color: '#d4e157', fontWeight: '600' },

  // Barcode flow
  barcodePanel: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.05)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 8,
  },
  barcodeHint: { fontSize: 12, opacity: 0.6, lineHeight: 17 },
  barcodeError: { fontSize: 12, color: '#ff6b6b', lineHeight: 16 },
  barcodeLookupBtn: {
    alignSelf: 'flex-start',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: '#d4e157',
  },
  barcodeLookupBtnText: { color: '#0a0a0a', fontSize: 13, fontWeight: '700' },
  barcodeLoadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  productHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  productName: { fontSize: 14, fontWeight: '600' },
  productBrand: { fontSize: 12, opacity: 0.5, marginTop: 2 },
  productServing: { fontSize: 11, opacity: 0.4, marginTop: 2 },
  productResetText: { color: '#ff6b6b', fontSize: 16, padding: 4 },

  // Barcode favorites strip
  favoritesBlock: {
    gap: 6,
    paddingBottom: 4,
    marginBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  favoritesLabel: {
    fontSize: 10,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  favoritesRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 2,
  },
  favoritePill: {
    maxWidth: 140,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#444',
    backgroundColor: 'rgba(255,255,255,0.04)',
    gap: 1,
  },
  favoritePillName: { fontSize: 12, fontWeight: '600', color: '#e0e0e0' },
  favoritePillBrand: { fontSize: 10, opacity: 0.5 },
  favoritePillGrams: { fontSize: 10, color: '#d4e157', opacity: 0.8, marginTop: 2 },
  favoritesHint: { fontSize: 10, opacity: 0.35, fontStyle: 'italic' },

  editGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  editField: { minWidth: '30%', flexGrow: 1, gap: 4 },
  editLabel: {
    fontSize: 11,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editInput: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 14,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  editActions: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'flex-end',
  },
  cancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
  },
  cancelBtnText: { color: '#999', fontSize: 13 },
  saveBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: '#d4e157',
  },
  saveBtnText: { color: '#0a0a0a', fontSize: 13, fontWeight: '700' },
  scanCameraBtn: {
    backgroundColor: '#d4e157',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 8,
  },
  scanCameraBtnText: {
    color: '#0a0a0a',
    fontSize: 14,
    fontWeight: '700',
  },
  barcodeOrDivider: {
    color: '#666',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 6,
  },
});
