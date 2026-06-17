/**
 * WHOOP bridge ownership — which Supabase user.id(s) are allowed to
 * see WHOOP bridge data in the mobile app.
 *
 * The bridge is a single-user proxy to Aaron's WHOOP account. Showing
 * its data to any other signed-in user would leak private health data.
 *
 * Allowlist sources (OR'd together, deduped, normalized):
 *   1. EXPO_PUBLIC_WHOOP_BRIDGE_OWNER_IDS env var (comma-separated).
 *      Inlined by Metro at bundle time from apps/mobile/.env.production.
 *   2. expo-constants extra.whoopBridgeOwnerIds from app.json. Survives
 *      any case where Metro's process.env substitution didn't bake the
 *      env (e.g. EAS export running with a different NODE_ENV than
 *      expected). The app.json extra block is always bundled.
 *   3. 'dev-athlete' legacy dev-mode fallback id.
 *
 * Evaluated on every call rather than at module import — avoids any
 * frozen-constant bug where a previously-bundled module kept a stale
 * empty allowlist after an OTA.
 *
 * Comparison is case-insensitive + trimmed so a copy/paste with a
 * stray newline or an uppercase UUID still matches.
 */

function readExtraOwnerIds(): string | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Constants = require('expo-constants')?.default ?? require('expo-constants');
    const extra = (Constants?.expoConfig?.extra ?? Constants?.manifest?.extra ?? Constants?.manifest2?.extra) as Record<string, unknown> | undefined;
    const raw = extra?.whoopBridgeOwnerIds;
    return typeof raw === 'string' && raw.length > 0 ? raw : null;
  } catch {
    return null;
  }
}

function readEnvOwnerIds(): string | null {
  const raw = process.env.EXPO_PUBLIC_WHOOP_BRIDGE_OWNER_IDS;
  return typeof raw === 'string' && raw.length > 0 ? raw : null;
}

function normalize(id: string): string {
  return id.trim().toLowerCase();
}

function buildOwnerSet(): Set<string> {
  const pieces: string[] = [];
  const env = readEnvOwnerIds();
  if (env) pieces.push(env);
  const extra = readExtraOwnerIds();
  if (extra) pieces.push(extra);
  // Legacy dev-mode id — never a real Supabase UUID, so having it in
  // the set doesn't broaden exposure to any real account.
  pieces.push('dev-athlete');
  const parts = pieces
    .join(',')
    .split(',')
    .map((s) => normalize(s))
    .filter(Boolean);
  return new Set(parts);
}

export function isWhoopBridgeOwner(userId: string | null | undefined): boolean {
  if (!userId) return false;
  const set = buildOwnerSet();
  return set.has(normalize(userId));
}

/**
 * Diagnostic count — number of parsed owner ids in the current set.
 * Callers can surface this in error copy so testers know whether the
 * allowlist was actually loaded from env/extra or silently empty.
 * Never exposes the ids themselves.
 */
export function whoopBridgeOwnerCount(): number {
  return buildOwnerSet().size;
}

/**
 * Which source(s) contributed ids. Safe to log — returns an array of
 * source labels like ['env','extra'] or ['extra'] etc. Useful for
 * testers to see whether .env.production or app.json extra is live.
 */
export function whoopBridgeOwnerSources(): string[] {
  const sources: string[] = [];
  if (readEnvOwnerIds()) sources.push('env');
  if (readExtraOwnerIds()) sources.push('extra');
  sources.push('legacy');
  return sources;
}
