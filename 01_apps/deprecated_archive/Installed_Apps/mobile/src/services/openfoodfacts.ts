/**
 * Open Food Facts barcode → product lookup client.
 *
 * Architecture notes:
 * - No auth. Open Food Facts is a free, community-maintained database
 *   accessible via the public v2 endpoint. See https://world.openfoodfacts.org.
 * - Pure fetch, no native module, no camera. This service is the
 *   back-half of the barcode flow — the front-half is a TextInput in
 *   NutritionCard today, and will become a camera capture in a future
 *   batch without changing this file.
 * - Every nutriments field is optional — different products expose
 *   different subsets. We extract what's there and leave the rest null.
 *
 * Response reference (2026-04-10):
 *   Product URL pattern: https://world.openfoodfacts.org/api/v2/product/{barcode}.json
 *   Success: { code: string, product: { product_name, brands, serving_size,
 *              quantity, nutriments: { energy-kcal_100g, proteins_100g,
 *              carbohydrates_100g, fat_100g, fiber_100g, sugars_100g,
 *              sodium_100g, ... } }, status: 1 }
 *   Not found: { code, status: 0, status_verbose: "product not found" }
 */

const OFF_BASE = 'https://world.openfoodfacts.org/api/v2/product';

/** Clean per-100g snapshot for one product. */
export interface OpenFoodFactsProduct {
  barcode: string;
  name: string;
  brand: string | null;
  /** Parsed serving size in grams, if available (e.g. "15 g" → 15). */
  serving_size_g: number | null;
  /** Raw serving size string from the API, for display. */
  serving_size_raw: string | null;
  /** Macros normalised per 100g — NaN-safe, missing fields are null. */
  per_100g: {
    calories_kcal: number | null;
    protein_g: number | null;
    carbs_g: number | null;
    fat_g: number | null;
    fibre_g: number | null;
    sugar_g: number | null;
    sodium_mg: number | null;
  };
}

export type LookupResult =
  | { ok: true; product: OpenFoodFactsProduct }
  | { ok: false; error: string };

/**
 * Source/confidence tier for a nutrition hit. Keeps web/retailer results
 * clearly below barcode-confirmed rows so Coach and the UI can rank them.
 */
export type ProductMatchSource =
  | 'verified_barcode'  // confirmed product row keyed by UPC/EAN — highest trust
  | 'database_match'    // product-name search hit in OpenFoodFacts
  | 'retailer_web'      // generic web/retailer fallback — not used yet, reserved
  | 'estimated';        // AI / loose guess — lowest trust

export interface ProductSearchHit {
  product: OpenFoodFactsProduct;
  source: ProductMatchSource;
  confidence: 'high' | 'medium' | 'low';
  /**
   * For local/favourite hits — the last grams the user actually ate.
   * Makes one-tap re-add snappier: jump straight to that serving size
   * instead of the package-default. Null for fresh database rows.
   */
  lastGrams?: number | null;
}

export type SearchResult =
  | { ok: true; hits: ProductSearchHit[] }
  | { ok: false; error: string };

/**
 * Parse "15 g" → 15, "100 ml" → null (we only want grams), "15" → 15.
 * Returns null on anything we can't confidently read as grams.
 */
function parseServingSizeGrams(raw: string | undefined | null): number | null {
  if (!raw) return null;
  const trimmed = String(raw).trim().toLowerCase();
  // Match "<number> g" or "<number>g" — ignore ml, oz, etc.
  const match = trimmed.match(/^(\d+(?:\.\d+)?)\s*g$/);
  if (match) {
    const n = Number(match[1]);
    return Number.isFinite(n) ? n : null;
  }
  // Bare number — assume grams.
  const bare = Number(trimmed);
  if (Number.isFinite(bare) && bare > 0) return bare;
  return null;
}

function readNumber(obj: any, key: string): number | null {
  const v = obj?.[key];
  if (v == null) return null;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

const OFF_SEARCH_BASE = 'https://world.openfoodfacts.org/cgi/search.pl';

/**
 * Product-name search via Open Food Facts. Typed queries like
 * "golden gaytime vegan" or "greek yogurt woolworths" hit the same
 * database as barcode lookup, but return an ordered array of hits
 * ranked by OFF's relevance scoring. Confidence is capped at
 * 'database_match' tier (never 'verified_barcode') because an OFF row
 * can be crowd-edited; only a confirmed barcode scan fills a UPC/EAN
 * to that highest trust tier.
 *
 * Hits that already have a numeric barcode from OFF are still
 * database_match — upgrading them to verified_barcode would require
 * an actual scan against a package.
 */
export async function searchByName(query: string, pageSize = 12): Promise<SearchResult> {
  const clean = String(query ?? '').trim();
  if (clean.length < 2) {
    return { ok: false, error: 'Type at least two characters to search.' };
  }
  try {
    const url = `${OFF_SEARCH_BASE}?search_terms=${encodeURIComponent(clean)}&search_simple=1&action=process&json=1&page_size=${pageSize}&fields=code,product_name,product_name_en,brands,serving_size,nutriments`;
    const resp = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } });
    if (!resp.ok) return { ok: false, error: `Open Food Facts search returned HTTP ${resp.status}` };
    const payload = await resp.json();
    const products: any[] = Array.isArray(payload?.products) ? payload.products : [];
    if (products.length === 0) return { ok: true, hits: [] };
    const hits: ProductSearchHit[] = [];
    for (const p of products) {
      const n = p?.nutriments ?? {};
      const rawBarcode = (p?.code ?? '').toString().trim();
      const name = p?.product_name || p?.product_name_en || p?.abbreviated_product_name || '';
      if (!name) continue; // skip unnamed rows — they're unusable
      const product: OpenFoodFactsProduct = {
        barcode: /^\d{6,14}$/.test(rawBarcode) ? rawBarcode : `off-name-${Math.random().toString(36).slice(2, 10)}`,
        name,
        brand: (p?.brands ?? '').split(',')[0]?.trim() || null,
        serving_size_g: parseServingSizeGrams(p?.serving_size),
        serving_size_raw: p?.serving_size ?? null,
        per_100g: {
          calories_kcal: readNumber(n, 'energy-kcal_100g'),
          protein_g: readNumber(n, 'proteins_100g'),
          carbs_g: readNumber(n, 'carbohydrates_100g'),
          fat_g: readNumber(n, 'fat_100g'),
          fibre_g: readNumber(n, 'fiber_100g'),
          sugar_g: readNumber(n, 'sugars_100g'),
          sodium_mg: (() => {
            const g = readNumber(n, 'sodium_100g');
            return g == null ? null : Math.round(g * 1000);
          })(),
        },
      };
      // Skip rows with zero usable macros — OFF occasionally returns
      // empty stubs for regions with thin data.
      const hasAnyMacro =
        product.per_100g.calories_kcal != null ||
        product.per_100g.protein_g != null ||
        product.per_100g.carbs_g != null ||
        product.per_100g.fat_g != null;
      if (!hasAnyMacro) continue;
      hits.push({
        product,
        source: 'database_match',
        confidence: product.per_100g.calories_kcal != null && product.per_100g.protein_g != null ? 'high' : 'medium',
      });
    }
    return { ok: true, hits };
  } catch (e: any) {
    return { ok: false, error: e?.message ?? 'Network error reaching Open Food Facts search' };
  }
}

export async function lookupBarcode(barcode: string): Promise<LookupResult> {
  const clean = String(barcode).trim();
  if (!clean) return { ok: false, error: 'Enter a barcode' };
  if (!/^\d{6,14}$/.test(clean)) {
    return { ok: false, error: 'Barcodes are 6–14 digits' };
  }
  try {
    const resp = await fetch(`${OFF_BASE}/${encodeURIComponent(clean)}.json`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!resp.ok) {
      return { ok: false, error: `Open Food Facts returned HTTP ${resp.status}` };
    }
    const payload = await resp.json();
    if (!payload || payload.status !== 1 || !payload.product) {
      return {
        ok: false,
        error: 'Product not found in Open Food Facts — try Manual entry',
      };
    }
    const p = payload.product;
    const n = p.nutriments ?? {};

    const product: OpenFoodFactsProduct = {
      barcode: clean,
      name:
        p.product_name ||
        p.product_name_en ||
        p.abbreviated_product_name ||
        'Unnamed product',
      brand: (p.brands ?? '').split(',')[0]?.trim() || null,
      serving_size_g: parseServingSizeGrams(p.serving_size),
      serving_size_raw: p.serving_size ?? null,
      per_100g: {
        calories_kcal: readNumber(n, 'energy-kcal_100g'),
        protein_g: readNumber(n, 'proteins_100g'),
        carbs_g: readNumber(n, 'carbohydrates_100g'),
        fat_g: readNumber(n, 'fat_100g'),
        fibre_g: readNumber(n, 'fiber_100g'),
        sugar_g: readNumber(n, 'sugars_100g'),
        sodium_mg: (() => {
          const g = readNumber(n, 'sodium_100g');
          return g == null ? null : Math.round(g * 1000);
        })(),
      },
    };

    return { ok: true, product };
  } catch (e: any) {
    return {
      ok: false,
      error: e?.message ?? 'Network error reaching Open Food Facts',
    };
  }
}

/**
 * Compute consumed macros from a per-100g product + grams eaten.
 * Returns the Partial<NutritionRecord> shape the store expects.
 */
export function macrosForGrams(
  product: OpenFoodFactsProduct,
  grams: number,
): {
  calories_kcal?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
  fibre_g?: number;
  sugar_g?: number;
  sodium_mg?: number;
} {
  const factor = grams / 100;
  const scale = (v: number | null): number | undefined =>
    v == null ? undefined : Math.round(v * factor * 10) / 10;
  const scaleInt = (v: number | null): number | undefined =>
    v == null ? undefined : Math.round(v * factor);
  return {
    calories_kcal: scaleInt(product.per_100g.calories_kcal),
    protein_g: scale(product.per_100g.protein_g),
    carbs_g: scale(product.per_100g.carbs_g),
    fat_g: scale(product.per_100g.fat_g),
    fibre_g: scale(product.per_100g.fibre_g),
    sugar_g: scale(product.per_100g.sugar_g),
    sodium_mg: scaleInt(product.per_100g.sodium_mg),
  };
}
