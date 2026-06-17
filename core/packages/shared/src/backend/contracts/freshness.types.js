"use strict";
/**
 * Freshness policy types — decides when live WHOOP reads are allowed.
 *
 * Live WHOOP is allowed ONLY when:
 *   1. artifact freshness is expired
 *   2. cached normalized/raw data is missing a required field
 *   3. source health indicates failed or incomplete ingest
 *   4. the user explicitly asks for current real-time status
 *
 * Everything else reads from cached artifacts.
 */
Object.defineProperty(exports, "__esModule", { value: true });
