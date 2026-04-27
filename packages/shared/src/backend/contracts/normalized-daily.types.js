"use strict";
/**
 * Normalized daily metrics — Layer 2 (deterministic transforms).
 *
 * Transforms raw source records into a uniform shape.
 * Allowed transforms: unit conversion, daily rollups,
 * completeness assessment, source-age calculation.
 *
 * STRICTLY NO interpretation that depends on athlete memory:
 *   NO baseline comparison flags
 *   NO readiness classification
 *   NO coaching recommendations
 *   NO pattern detection
 * Those belong in Layer 3 (daily_refresh_artifact).
 */
Object.defineProperty(exports, "__esModule", { value: true });
