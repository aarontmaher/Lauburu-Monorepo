/**
 * NutritionSourceCard — INTENTIONALLY NEUTRALIZED.
 *
 * This used to render a "Nutrition Sources" block with a Cronometer
 * status row. Cronometer is no longer in the active product path:
 * nutrition runs through Apple Health / Health Connect dietary import,
 * manual entry, barcode (Open Food Facts), and AI photo. Any render
 * path that still references this component gets nothing — no block,
 * no row, no Cronometer string.
 *
 * The component name and export are preserved so any stale tree /
 * older OTA bundle that still tries to mount this renders an empty
 * fragment instead of crashing with an undefined-component error.
 * Delete this file once no stale bundles are in the field.
 */
export function NutritionSourceCard(): null {
  return null;
}
