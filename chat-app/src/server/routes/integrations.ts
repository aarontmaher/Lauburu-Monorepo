/**
 * Integration routes — per-user OAuth + status for all third-party
 * sources (Polar AccessLink, Cronometer, WHOOP direct, Concept2).
 *
 * Auth:
 *   Every route extracts the Supabase JWT from the Authorization header,
 *   decodes the `sub` claim, and scopes all reads/writes to that userId.
 *   The shared `x-athlete-memory-token` is checked as a secondary guard.
 *
 * Token storage:
 *   All access/refresh tokens are stored SERVER-SIDE only, under the
 *   athlete's private file namespace. Mobile never sees raw tokens —
 *   only `status` / `connected` / `auth_required` / `config_missing`.
 *
 * CSRF:
 *   OAuth `state` params carry a signed {userId, ts, nonce} JWT. The
 *   callback verifies this before accepting the token.
 */
import { Router } from 'express';
import path from 'path';
import crypto from 'crypto';
import { promises as fs } from 'fs';

const router = Router();
const DATA_DIR = path.resolve(__dirname, '../../../data/private-athlete-memory');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractUserIdFromJwt(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const match = /^Bearer\s+(.+)$/.exec(authHeader);
  if (!match) return null;
  const parts = match[1].split('.');
  if (parts.length !== 3) return null;
  try {
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
    const payload = JSON.parse(Buffer.from(padded, 'base64').toString('utf8'));
    return typeof payload?.sub === 'string' ? payload.sub : null;
  } catch { return null; }
}

function requireAuth(req: any, res: any, next: any) {
  const expectedToken = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expectedToken) { res.status(503).json({ error: 'Integration routes disabled.' }); return; }
  const sharedToken = req.header('x-athlete-memory-token');
  if (sharedToken !== expectedToken) { res.status(403).json({ error: 'Forbidden.' }); return; }
  const userId = extractUserIdFromJwt(req.header('authorization'));
  const allowDev = process.env.ALLOW_SHARED_TOKEN_ONLY === '1' || process.env.NODE_ENV === 'test';
  if (!userId && !allowDev) { res.status(401).json({ error: 'JWT required.' }); return; }
  (req as any).userId = userId ?? 'dev-athlete';
  next();
}

async function readJson<T>(filePath: string): Promise<T | null> {
  try { return JSON.parse(await fs.readFile(filePath, 'utf8')) as T; } catch { return null; }
}

async function writeJson(filePath: string, data: unknown): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function tokenPath(userId: string, provider: string): string {
  return path.join(DATA_DIR, userId, 'integrations', `${provider}_token.json`);
}

function statusPath(userId: string, provider: string): string {
  return path.join(DATA_DIR, userId, 'integrations', `${provider}_status.json`);
}

// ---------------------------------------------------------------------------
// CSRF state helpers (signed, time-limited)
// ---------------------------------------------------------------------------

const STATE_SECRET = process.env.INTEGRATION_STATE_SECRET ?? crypto.randomBytes(32).toString('hex');

function createOAuthState(userId: string): string {
  const payload = { userId, ts: Date.now(), nonce: crypto.randomBytes(8).toString('hex') };
  const json = JSON.stringify(payload);
  const b64 = Buffer.from(json).toString('base64url');
  const sig = crypto.createHmac('sha256', STATE_SECRET).update(b64).digest('base64url');
  return `${b64}.${sig}`;
}

function verifyOAuthState(state: string): { userId: string } | null {
  const [b64, sig] = state.split('.');
  if (!b64 || !sig) return null;
  const expected = crypto.createHmac('sha256', STATE_SECRET).update(b64).digest('base64url');
  if (sig !== expected) return null;
  try {
    const payload = JSON.parse(Buffer.from(b64, 'base64url').toString('utf8'));
    if (typeof payload.userId !== 'string') return null;
    // 10-minute window
    if (Date.now() - payload.ts > 600_000) return null;
    return { userId: payload.userId };
  } catch { return null; }
}

// ═══════════════════════════════════════════════════════════════════════════
// POLAR ACCESSLINK
// ═══════════════════════════════════════════════════════════════════════════

const POLAR_CLIENT_ID = process.env.POLAR_CLIENT_ID ?? '';
const POLAR_CLIENT_SECRET = process.env.POLAR_CLIENT_SECRET ?? '';
const POLAR_REDIRECT_URI = process.env.POLAR_REDIRECT_URI ?? '';
const POLAR_AUTH_URL = 'https://flow.polar.com/oauth2/authorization';
const POLAR_TOKEN_URL = 'https://polarremote.com/v2/oauth2/token';
const POLAR_API_BASE = process.env.POLAR_ACCESSLINK_BASE_URL ?? 'https://www.polaraccesslink.com/v3';

function polarConfigured(): boolean {
  return POLAR_CLIENT_ID.length > 0 && POLAR_CLIENT_SECRET.length > 0 && POLAR_REDIRECT_URI.length > 0;
}

// GET /api/integrations/polar/status
router.get('/polar/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  if (!polarConfigured()) {
    return res.json({
      provider: 'direct_polar',
      status: 'config_missing',
      reason: 'POLAR_CLIENT_ID, POLAR_CLIENT_SECRET, and POLAR_REDIRECT_URI must be set on the backend.',
      setupInstructions: [
        '1. Create a Polar AccessLink application at https://admin.polaraccesslink.com/',
        '2. Set POLAR_CLIENT_ID, POLAR_CLIENT_SECRET, POLAR_REDIRECT_URI in the backend environment.',
        '3. The redirect URI must match the one registered in the Polar admin console.',
      ],
    });
  }
  const token = await readJson<any>(tokenPath(userId, 'polar'));
  const status = await readJson<any>(statusPath(userId, 'polar'));
  if (!token) {
    return res.json({ provider: 'direct_polar', status: 'auth_required', reason: 'Polar not connected. Tap Connect to link your Polar account.' });
  }
  return res.json({
    provider: 'direct_polar',
    status: status?.status ?? 'connected',
    lastSyncAt: status?.lastSyncAt ?? null,
    polarUserId: token.x_user_id ?? null,
    domainsAvailable: status?.domainsAvailable ?? [],
    reason: status?.reason ?? null,
  });
});

// GET /api/integrations/polar/connect — returns OAuth URL for the mobile app to open
router.get('/polar/connect', requireAuth, async (req: any, res: any) => {
  if (!polarConfigured()) {
    return res.status(503).json({ error: 'Polar AccessLink credentials not configured on backend.' });
  }
  const state = createOAuthState(req.userId);
  const url = `${POLAR_AUTH_URL}?response_type=code&client_id=${encodeURIComponent(POLAR_CLIENT_ID)}&redirect_uri=${encodeURIComponent(POLAR_REDIRECT_URI)}&state=${encodeURIComponent(state)}`;
  res.json({ ok: true, url, state });
});

// GET /api/integrations/polar/callback?code=...&state=...
// In practice this is hit by the browser redirect; the mobile app
// opens the /connect URL in a webview, Polar redirects back here.
router.get('/polar/callback', async (req: any, res: any) => {
  const { code, state } = req.query as { code?: string; state?: string };
  if (!code || !state) return res.status(400).json({ error: 'code and state required' });
  const verified = verifyOAuthState(state);
  if (!verified) return res.status(403).json({ error: 'Invalid or expired OAuth state.' });
  const userId = verified.userId;

  try {
    const auth = Buffer.from(`${POLAR_CLIENT_ID}:${POLAR_CLIENT_SECRET}`).toString('base64');
    const tokenResp = await fetch(POLAR_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Basic ${auth}`,
        'Accept': 'application/json',
      },
      body: `grant_type=authorization_code&code=${encodeURIComponent(code)}&redirect_uri=${encodeURIComponent(POLAR_REDIRECT_URI)}`,
    });
    if (!tokenResp.ok) {
      const body = await tokenResp.text().catch(() => '');
      return res.status(502).json({ error: 'Polar token exchange failed.', detail: body.slice(0, 300) });
    }
    const tokenData = await tokenResp.json() as { access_token: string; token_type: string; x_user_id?: number };
    await writeJson(tokenPath(userId, 'polar'), {
      access_token: tokenData.access_token,
      token_type: tokenData.token_type,
      x_user_id: tokenData.x_user_id ?? null,
      storedAt: new Date().toISOString(),
      userId,
    });

    // Register user with AccessLink (required before pulling data)
    try {
      await fetch(`${POLAR_API_BASE}/users`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokenData.access_token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ 'member-id': String(tokenData.x_user_id ?? userId) }),
      });
    } catch { /* May 409 if already registered — that's fine. */ }

    await writeJson(statusPath(userId, 'polar'), {
      status: 'connected',
      lastSyncAt: null,
      reason: null,
      domainsAvailable: ['workouts', 'daily_activity', 'physical_info'],
    });

    // Redirect back to app (or show success page).
    res.send('<html><body><h2>Polar connected.</h2><p>You can close this tab and return to the app.</p></body></html>');
  } catch (e) {
    res.status(500).json({ error: 'OAuth callback failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// POST /api/integrations/polar/disconnect
router.post('/polar/disconnect', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  try {
    const token = await readJson<any>(tokenPath(userId, 'polar'));
    if (token?.access_token) {
      // Deregister from AccessLink
      try {
        await fetch(`${POLAR_API_BASE}/users/${token.x_user_id ?? 'current'}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token.access_token}` },
        });
      } catch { /* Non-fatal */ }
    }
    await fs.unlink(tokenPath(userId, 'polar')).catch(() => {});
    await writeJson(statusPath(userId, 'polar'), { status: 'disconnected', lastSyncAt: null, reason: 'User disconnected.', domainsAvailable: [] });
    res.json({ ok: true, status: 'disconnected' });
  } catch (e) {
    res.status(500).json({ error: 'Disconnect failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// POST /api/integrations/polar/sync — pull latest data from AccessLink
router.post('/polar/sync', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const token = await readJson<any>(tokenPath(userId, 'polar'));
  if (!token?.access_token) {
    return res.status(400).json({ error: 'Polar not connected.', status: 'auth_required' });
  }

  const results: { endpoint: string; ok: boolean; count: number; error?: string }[] = [];

  // Pull exercises (workouts)
  try {
    const resp = await fetch(`${POLAR_API_BASE}/users/${token.x_user_id ?? 'current'}/exercise-transactions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
    });
    if (resp.ok) {
      const tx = await resp.json() as { 'transaction-id'?: number; 'resource-uri'?: string };
      if (tx['resource-uri']) {
        const listResp = await fetch(tx['resource-uri'], {
          headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
        });
        const exerciseList = listResp.ok ? (await listResp.json() as { exercises?: string[] }) : { exercises: [] };
        const exercises = exerciseList.exercises ?? [];
        // Store each exercise as a raw record
        for (const uri of exercises.slice(0, 20)) {
          try {
            const exResp = await fetch(uri, {
              headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
            });
            if (exResp.ok) {
              const ex = await exResp.json() as Record<string, any>;
              await writeJson(
                path.join(DATA_DIR, userId, 'integrations', 'polar_exercises', `${ex.id ?? Date.now()}.json`),
                { ...ex, _source: 'direct_polar', _provider: 'polar_accesslink', _userId: userId, _storedAt: new Date().toISOString() },
              );
            }
          } catch { /* Per-exercise failure non-fatal */ }
        }
        // Commit the transaction
        try {
          await fetch(tx['resource-uri'], {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token.access_token}` },
          });
        } catch { /* commit failure non-fatal */ }
        results.push({ endpoint: 'exercises', ok: true, count: exercises.length });
      } else {
        results.push({ endpoint: 'exercises', ok: true, count: 0 });
      }
    } else {
      results.push({ endpoint: 'exercises', ok: false, count: 0, error: `HTTP ${resp.status}` });
    }
  } catch (e) {
    results.push({ endpoint: 'exercises', ok: false, count: 0, error: e instanceof Error ? e.message : 'unknown' });
  }

  // Pull daily activity
  try {
    const resp = await fetch(`${POLAR_API_BASE}/users/${token.x_user_id ?? 'current'}/activity-transactions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
    });
    if (resp.ok) {
      const tx = await resp.json() as { 'transaction-id'?: number; 'resource-uri'?: string };
      if (tx['resource-uri']) {
        const listResp = await fetch(tx['resource-uri'], {
          headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
        });
        const list = listResp.ok ? (await listResp.json() as { 'activity-log'?: string[] }) : { 'activity-log': [] };
        const activities = list['activity-log'] ?? [];
        for (const uri of activities.slice(0, 20)) {
          try {
            const aResp = await fetch(uri, {
              headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
            });
            if (aResp.ok) {
              const a = await aResp.json() as Record<string, any>;
              await writeJson(
                path.join(DATA_DIR, userId, 'integrations', 'polar_activity', `${a.date ?? Date.now()}.json`),
                { ...a, _source: 'direct_polar', _provider: 'polar_accesslink', _userId: userId, _storedAt: new Date().toISOString() },
              );
            }
          } catch { /* non-fatal */ }
        }
        try {
          await fetch(tx['resource-uri'], { method: 'PUT', headers: { 'Authorization': `Bearer ${token.access_token}` } });
        } catch { /* non-fatal */ }
        results.push({ endpoint: 'activity', ok: true, count: activities.length });
      } else {
        results.push({ endpoint: 'activity', ok: true, count: 0 });
      }
    } else {
      results.push({ endpoint: 'activity', ok: false, count: 0, error: `HTTP ${resp.status}` });
    }
  } catch (e) {
    results.push({ endpoint: 'activity', ok: false, count: 0, error: e instanceof Error ? e.message : 'unknown' });
  }

  // Pull physical info (body metrics)
  try {
    const resp = await fetch(`${POLAR_API_BASE}/users/${token.x_user_id ?? 'current'}/physical-information-transactions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
    });
    if (resp.ok) {
      const tx = await resp.json() as { 'resource-uri'?: string };
      if (tx['resource-uri']) {
        const listResp = await fetch(tx['resource-uri'], {
          headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
        });
        const list = listResp.ok ? (await listResp.json() as { 'physical-informations'?: string[] }) : { 'physical-informations': [] };
        const physicals = list['physical-informations'] ?? [];
        for (const uri of physicals.slice(0, 5)) {
          try {
            const pResp = await fetch(uri, {
              headers: { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' },
            });
            if (pResp.ok) {
              const p = await pResp.json() as Record<string, any>;
              await writeJson(
                path.join(DATA_DIR, userId, 'integrations', 'polar_physical', `${p.id ?? Date.now()}.json`),
                { ...p, _source: 'direct_polar', _provider: 'polar_accesslink', _userId: userId, _storedAt: new Date().toISOString() },
              );
            }
          } catch { /* non-fatal */ }
        }
        try { await fetch(tx['resource-uri'], { method: 'PUT', headers: { 'Authorization': `Bearer ${token.access_token}` } }); } catch { /* non-fatal */ }
        results.push({ endpoint: 'physical_info', ok: true, count: physicals.length });
      } else {
        results.push({ endpoint: 'physical_info', ok: true, count: 0 });
      }
    } else {
      results.push({ endpoint: 'physical_info', ok: false, count: 0, error: `HTTP ${resp.status}` });
    }
  } catch (e) {
    results.push({ endpoint: 'physical_info', ok: false, count: 0, error: e instanceof Error ? e.message : 'unknown' });
  }

  const now = new Date().toISOString();
  const anyOk = results.some((r) => r.ok && r.count > 0);
  await writeJson(statusPath(userId, 'polar'), {
    status: anyOk ? 'connected' : 'partial',
    lastSyncAt: now,
    reason: anyOk ? null : 'Sync completed but no new data pulled.',
    domainsAvailable: results.filter((r) => r.ok).map((r) => r.endpoint),
  });

  res.json({ ok: true, syncedAt: now, results });
});

// ═══════════════════════════════════════════════════════════════════════════
// CRONOMETER
// ═══════════════════════════════════════════════════════════════════════════

const CRONOMETER_CLIENT_ID = process.env.CRONOMETER_CLIENT_ID ?? '';

function cronometerConfigured(): boolean {
  return CRONOMETER_CLIENT_ID.length > 0;
}

// GET /api/integrations/cronometer/status
router.get('/cronometer/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  if (!cronometerConfigured()) {
    return res.json({
      provider: 'cronometer',
      status: 'api_unavailable',
      reason: 'Cronometer does not offer a public third-party API. Nutrition data enters the app via manual entry, barcode scan, or photo estimate.',
      fallbackPaths: [
        'Manual nutrition logging (always available)',
        'Barcode scan → confirm → ingest',
        'Photo estimate → confirm → ingest',
        'Cronometer diary export → import (future: CSV parse)',
      ],
    });
  }
  const status = await readJson<any>(statusPath(userId, 'cronometer'));
  return res.json({
    provider: 'cronometer',
    status: status?.status ?? 'auth_required',
    lastSyncAt: status?.lastSyncAt ?? null,
    reason: status?.reason ?? null,
  });
});

// POST /api/integrations/cronometer/import — future CSV import endpoint
router.post('/cronometer/import', requireAuth, async (req: any, res: any) => {
  // Placeholder: when Cronometer export parsing is implemented, the
  // mobile app sends the CSV content and this route parses + ingests.
  res.json({
    ok: false,
    status: 'not_implemented',
    reason: 'Cronometer diary export import is not yet implemented. Use manual nutrition logging, barcode scan, or photo estimate.',
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// WHOOP (per-user direct OAuth)
// ═══════════════════════════════════════════════════════════════════════════

const WHOOP_CLIENT_ID = process.env.WHOOP_CLIENT_ID ?? '';
const WHOOP_CLIENT_SECRET = process.env.WHOOP_CLIENT_SECRET ?? '';
const WHOOP_REDIRECT_URI = process.env.WHOOP_REDIRECT_URI ?? '';
const WHOOP_AUTH_URL = 'https://api.prod.whoop.com/oauth/oauth2/auth';
const WHOOP_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token';
const WHOOP_API_BASE = 'https://api.prod.whoop.com/developer/v1';

function whoopOAuthMissingVars(): string[] {
  const missing: string[] = [];
  if (WHOOP_CLIENT_ID.length === 0) missing.push('WHOOP_CLIENT_ID');
  if (WHOOP_CLIENT_SECRET.length === 0) missing.push('WHOOP_CLIENT_SECRET');
  if (WHOOP_REDIRECT_URI.length === 0) missing.push('WHOOP_REDIRECT_URI');
  return missing;
}

function whoopOAuthConfigured(): boolean {
  return whoopOAuthMissingVars().length === 0;
}

/**
 * Derive the canonical callback URL the client should register with
 * WHOOP. Prefers the env var so ops can override, but falls back to the
 * Railway-deployed URL Aaron has documented in docs/WHOOP_DIRECT_SETUP.md.
 */
function whoopExpectedRedirectUri(): string {
  if (WHOOP_REDIRECT_URI.length > 0) return WHOOP_REDIRECT_URI;
  return 'https://lauburu-ai-backend-production.up.railway.app/api/integrations/whoop/callback';
}

// GET /api/integrations/whoop/status
router.get('/whoop/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const missingVars = whoopOAuthMissingVars();
  if (missingVars.length > 0) {
    return res.json({
      provider: 'whoop_direct',
      status: 'config_missing',
      reason: `Missing backend env: ${missingVars.join(', ')}.`,
      missingVars,
      expectedRedirectUri: whoopExpectedRedirectUri(),
      setupInstructions: [
        '1. Apply for WHOOP developer API access at https://developer.whoop.com/',
        '2. Create an OAuth application. Register redirect URI exactly as shown above.',
        `3. Set in Railway (production): ${missingVars.join(', ')}.`,
      ],
      note: "Aaron's WHOOP data is available via the existing bridge for owner accounts only. This route is for per-user WHOOP OAuth — no shared fallback.",
    });
  }
  const token = await readJson<any>(tokenPath(userId, 'whoop'));
  const status = await readJson<any>(statusPath(userId, 'whoop_direct'));
  if (!token) {
    return res.json({ provider: 'whoop_direct', status: 'auth_required', reason: 'WHOOP not connected. Tap Connect to link your WHOOP account.' });
  }
  const domainsAvailable: string[] = Array.isArray(status?.domainsAvailable) ? status.domainsAvailable : [];
  const ALL_DOMAINS = ['recovery', 'hrv', 'resting_hr', 'strain', 'sleep', 'workouts'];
  const missingDomains = ALL_DOMAINS.filter((d) => !domainsAvailable.includes(d));
  const readiness = status?.status === 'connected' && domainsAvailable.includes('recovery') && domainsAvailable.includes('hrv') && domainsAvailable.includes('strain') && domainsAvailable.includes('sleep')
    ? 'available'
    : status?.status === 'connected' || status?.status === 'partial'
      ? 'partial'
      : 'unavailable';
  return res.json({
    provider: 'whoop_direct',
    status: status?.status ?? 'connected',
    lastSyncAt: status?.lastSyncAt ?? null,
    whoopUserId: token.user_id ?? null,
    reason: status?.reason ?? null,
    domainsAvailable,
    missingDomains,
    readinessStatus: readiness,
    latestDayDate: status?.latestDayDate ?? null,
    normalizedDaysCreated: status?.normalizedDaysCreated ?? 0,
  });
});

// GET /api/integrations/whoop/connect
router.get('/whoop/connect', requireAuth, async (req: any, res: any) => {
  const missingVars = whoopOAuthMissingVars();
  if (missingVars.length > 0) {
    return res.status(503).json({
      error: 'WHOOP OAuth credentials not configured.',
      missingVars,
      expectedRedirectUri: whoopExpectedRedirectUri(),
    });
  }
  const state = createOAuthState(req.userId);
  // `offline` scope is required for WHOOP to issue a refresh token
  // alongside the access token. Without it the access token expires
  // after ~1 hour and the user has to reconnect manually.
  const scopes = 'offline read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement';
  const url = `${WHOOP_AUTH_URL}?response_type=code&client_id=${encodeURIComponent(WHOOP_CLIENT_ID)}&redirect_uri=${encodeURIComponent(WHOOP_REDIRECT_URI)}&scope=${encodeURIComponent(scopes)}&state=${encodeURIComponent(state)}`;
  res.json({ ok: true, url, state });
});

// GET /api/integrations/whoop/callback?code=...&state=...
router.get('/whoop/callback', async (req: any, res: any) => {
  const { code, state } = req.query as { code?: string; state?: string };
  if (!code || !state) return res.status(400).json({ error: 'code and state required' });
  const verified = verifyOAuthState(state);
  if (!verified) return res.status(403).json({ error: 'Invalid or expired OAuth state.' });
  const userId = verified.userId;

  try {
    const tokenResp = await fetch(WHOOP_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: WHOOP_REDIRECT_URI,
        client_id: WHOOP_CLIENT_ID,
        client_secret: WHOOP_CLIENT_SECRET,
      }).toString(),
    });
    if (!tokenResp.ok) {
      const body = await tokenResp.text().catch(() => '');
      return res.status(502).json({ error: 'WHOOP token exchange failed.', detail: body.slice(0, 300) });
    }
    const tokenData = await tokenResp.json() as { access_token: string; refresh_token?: string; expires_in?: number; user_id?: number };
    await writeJson(tokenPath(userId, 'whoop'), {
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token ?? null,
      expires_in: tokenData.expires_in ?? null,
      user_id: tokenData.user_id ?? null,
      storedAt: new Date().toISOString(),
      userId,
    });
    await writeJson(statusPath(userId, 'whoop_direct'), {
      status: 'connected',
      lastSyncAt: null,
      reason: null,
    });
    res.send('<html><body><h2>WHOOP connected.</h2><p>Close this tab and return to the app.</p></body></html>');
  } catch (e) {
    res.status(500).json({ error: 'WHOOP OAuth callback failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// POST /api/integrations/whoop/disconnect
router.post('/whoop/disconnect', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  await fs.unlink(tokenPath(userId, 'whoop')).catch(() => {});
  await writeJson(statusPath(userId, 'whoop_direct'), { status: 'disconnected', lastSyncAt: null, reason: 'User disconnected.' });
  res.json({ ok: true, status: 'disconnected' });
});

// POST /api/integrations/whoop/sync — pull recovery/sleep/strain/workouts
// AND normalize into the canonical pipeline so analyseReadiness() works.
router.post('/whoop/sync', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const missingVars = whoopOAuthMissingVars();
  if (missingVars.length > 0) {
    return res.status(503).json({
      error: 'WHOOP OAuth credentials not configured.',
      status: 'config_missing',
      missingVars,
      expectedRedirectUri: whoopExpectedRedirectUri(),
    });
  }
  let token = await readJson<any>(tokenPath(userId, 'whoop'));
  if (!token?.access_token) {
    return res.status(400).json({ error: 'WHOOP not connected.', status: 'auth_required' });
  }

  // Refresh helper: when WHOOP returns 401 we try once with the stored
  // refresh_token. On success we persist the fresh tokens and retry
  // the original GET. On failure the per-endpoint result is logged
  // with the original HTTP 401 so the UI can surface it.
  async function refreshAccessToken(): Promise<boolean> {
    if (!token?.refresh_token) return false;
    try {
      const resp = await fetch(WHOOP_TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: token.refresh_token,
          client_id: WHOOP_CLIENT_ID,
          client_secret: WHOOP_CLIENT_SECRET,
          scope: 'offline',
        }).toString(),
      });
      if (!resp.ok) return false;
      const fresh = await resp.json() as { access_token: string; refresh_token?: string; expires_in?: number; user_id?: number };
      token = {
        ...token,
        access_token: fresh.access_token,
        refresh_token: fresh.refresh_token ?? token.refresh_token,
        expires_in: fresh.expires_in ?? token.expires_in,
        refreshedAt: new Date().toISOString(),
      };
      await writeJson(tokenPath(userId, 'whoop'), token);
      return true;
    } catch {
      return false;
    }
  }

  async function whoopFetchWithRefresh(url: string): Promise<Response> {
    const headers = { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' };
    let resp = await fetch(url, { headers });
    if (resp.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        const retryHeaders = { 'Authorization': `Bearer ${token.access_token}`, 'Accept': 'application/json' };
        resp = await fetch(url, { headers: retryHeaders });
      }
    }
    return resp;
  }

  const results: { endpoint: string; ok: boolean; count: number; error?: string }[] = [];
  const rawByEndpoint: Record<string, any[]> = {};

  // Pull from all four WHOOP Developer API v1 endpoints.
  for (const endpoint of ['recovery', 'cycle', 'sleep', 'workout']) {
    try {
      const resp = await whoopFetchWithRefresh(`${WHOOP_API_BASE}/${endpoint}?limit=7`);
      if (resp.ok) {
        const data = await resp.json() as { records?: any[] };
        const records = data.records ?? [];
        rawByEndpoint[endpoint] = records;
        for (const record of records.slice(0, 10)) {
          const id = record.id ?? record.cycle_id ?? Date.now();
          await writeJson(
            path.join(DATA_DIR, userId, 'integrations', 'whoop_data', `${endpoint}_${id}.json`),
            { ...record, _source: 'whoop_direct', _provider: 'whoop_oauth', _userId: userId, _storedAt: new Date().toISOString() },
          );
        }
        results.push({ endpoint, ok: true, count: records.length });
      } else {
        results.push({ endpoint, ok: false, count: 0, error: `HTTP ${resp.status}` });
      }
    } catch (e) {
      results.push({ endpoint, ok: false, count: 0, error: e instanceof Error ? e.message : 'unknown' });
    }
  }

  // ── Normalize into canonical pipeline ──��──────────────────────
  // Group recovery + cycle + sleep by date and produce one
  // NormalizedDailyMetrics per day, saved via the same store the
  // bridge/seed path uses.
  const now = new Date().toISOString();
  const today = now.slice(0, 10);
  const recoveries = rawByEndpoint.recovery ?? [];
  const cycles = rawByEndpoint.cycle ?? [];
  const sleeps = rawByEndpoint.sleep ?? [];
  const workouts = rawByEndpoint.workout ?? [];

  // Build per-day map from the freshest recovery record per day.
  const dayMap = new Map<string, {
    recoveryScore: number | null;
    hrvMs: number | null;
    restingHrBpm: number | null;
    dailyStrain: number | null;
    totalSleepHours: number | null;
    deepSleepHours: number | null;
    remSleepHours: number | null;
    workoutCount: number;
  }>();

  for (const r of recoveries) {
    const date = r.created_at?.slice(0, 10) ?? r.cycle?.days_info?.[0]?.date ?? today;
    const score = r.score ?? {};
    const existing = dayMap.get(date) ?? {
      recoveryScore: null, hrvMs: null, restingHrBpm: null,
      dailyStrain: null, totalSleepHours: null, deepSleepHours: null,
      remSleepHours: null, workoutCount: 0,
    };
    existing.recoveryScore = score.recovery_score ?? existing.recoveryScore;
    existing.hrvMs = score.hrv_rmssd_milli != null ? Math.round(score.hrv_rmssd_milli) : existing.hrvMs;
    existing.restingHrBpm = score.resting_heart_rate ?? existing.restingHrBpm;
    dayMap.set(date, existing);
  }

  for (const c of cycles) {
    const date = c.days?.[0] ?? c.created_at?.slice(0, 10) ?? today;
    const existing = dayMap.get(date) ?? {
      recoveryScore: null, hrvMs: null, restingHrBpm: null,
      dailyStrain: null, totalSleepHours: null, deepSleepHours: null,
      remSleepHours: null, workoutCount: 0,
    };
    existing.dailyStrain = c.score?.strain ?? existing.dailyStrain;
    dayMap.set(date, existing);
  }

  for (const s of sleeps) {
    const date = s.end?.slice(0, 10) ?? s.created_at?.slice(0, 10) ?? today;
    const existing = dayMap.get(date) ?? {
      recoveryScore: null, hrvMs: null, restingHrBpm: null,
      dailyStrain: null, totalSleepHours: null, deepSleepHours: null,
      remSleepHours: null, workoutCount: 0,
    };
    const score = s.score ?? {};
    const durationMs = (s.end && s.start)
      ? new Date(s.end).getTime() - new Date(s.start).getTime()
      : null;
    existing.totalSleepHours = durationMs != null ? Math.round(durationMs / 36_000) / 100 : existing.totalSleepHours;
    existing.deepSleepHours = score.stage_summary?.total_slow_wave_sleep_time_milli != null
      ? Math.round(score.stage_summary.total_slow_wave_sleep_time_milli / 3_600_000 * 100) / 100
      : existing.deepSleepHours;
    existing.remSleepHours = score.stage_summary?.total_rem_sleep_time_milli != null
      ? Math.round(score.stage_summary.total_rem_sleep_time_milli / 3_600_000 * 100) / 100
      : existing.remSleepHours;
    dayMap.set(date, existing);
  }

  // Count workouts per day
  for (const w of workouts) {
    const date = w.start?.slice(0, 10) ?? w.created_at?.slice(0, 10) ?? today;
    const existing = dayMap.get(date);
    if (existing) existing.workoutCount += 1;
  }

  // Save each day as a normalized record + update source-health.
  const { FileApiAiStateStore: StoreClass } = await import('../athlete-memory/file-api-ai-state-store');
  const storeInstance = new StoreClass(DATA_DIR);
  let normalizedDaysCreated = 0;

  for (const [date, day] of dayMap) {
    try {
      const existing = await storeInstance.getNormalizedDay(userId, date);
      const record: Record<string, any> = {
        id: `norm_whoop_direct_${date}_${Date.now()}`,
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        derivationVersion: 'whoop_direct_v1',
        athleteId: userId,
        date,
        recoveryScore: day.recoveryScore,
        hrvMs: day.hrvMs,
        restingHrBpm: day.restingHrBpm,
        spo2Pct: null, skinTempCelsius: null, respiratoryRate: null,
        totalSleepHours: day.totalSleepHours,
        deepSleepHours: day.deepSleepHours,
        remSleepHours: day.remSleepHours,
        lightSleepHours: null, awakeHours: null,
        sleepEfficiencyPct: null, sleepDebtHours: null,
        dailyStrain: day.dailyStrain,
        activeCaloriesKcal: null, totalCaloriesKj: null,
        workoutCount: day.workoutCount,
        workoutMinutesTotal: null, workoutStrainTotal: null,
        grapplingSessionCount: 0, workoutSportNames: [],
        nutritionCalories: existing?.nutritionCalories ?? null,
        nutritionProteinGrams: existing?.nutritionProteinGrams ?? null,
        nutritionCarbGrams: existing?.nutritionCarbGrams ?? null,
        nutritionFatGrams: existing?.nutritionFatGrams ?? null,
        nutritionCoverage: existing?.nutritionCoverage ?? 'none',
        presentFields: [] as string[],
        missingFields: [] as string[],
        completeness: 'partial',
        sourceAgeHours: 0,
        sourceRecordIds: [`whoop_direct_${userId}_${date}`],
        sourceRefs: [{ layer: 'raw', recordId: `whoop_direct_${date}`, fieldPath: null, date }],
        provider: 'whoop_direct',
      };
      // Compute present/missing
      const check: Record<string, unknown> = {
        recoveryScore: record.recoveryScore, hrvMs: record.hrvMs,
        restingHrBpm: record.restingHrBpm, totalSleepHours: record.totalSleepHours,
        deepSleepHours: record.deepSleepHours, remSleepHours: record.remSleepHours,
        activeCaloriesKcal: record.activeCaloriesKcal, dailyStrain: record.dailyStrain,
      };
      record.presentFields = Object.entries(check).filter(([, v]) => v != null).map(([k]) => k);
      record.missingFields = Object.entries(check).filter(([, v]) => v == null).map(([k]) => k);
      record.completeness = record.missingFields.length === 0 ? 'complete' : record.presentFields.length >= 4 ? 'partial' : 'minimal';

      // Merge with existing (keep non-WHOOP fields like nutrition)
      if (existing) {
        for (const key of Object.keys(record)) {
          if ((record as any)[key] == null && (existing as any)[key] != null && !['id', 'createdAt', 'derivationVersion', 'provider'].includes(key)) {
            (record as any)[key] = (existing as any)[key];
          }
        }
        record.provider = existing.provider === 'whoop_direct' ? 'whoop_direct' : 'mixed';
      }

      await storeInstance.saveNormalizedDay(userId, record as any);
      normalizedDaysCreated += 1;
    } catch { /* per-day failure non-fatal */ }
  }

  // Update whoop_direct source-health with per-domain coverage.
  //
  // WHOOP scores recovery / sleep / HRV / RHR the MORNING AFTER the
  // sleep completes — the strict latest day in dayMap therefore
  // routinely has only strain (today's in-progress cycle). Walk back
  // through the most recent 3 days so a domain still counts as
  // "fresh" if it landed on yesterday or the day before. That's the
  // realistic readiness signal. Strain is unaffected because cycles
  // score in real time.
  const domains: Record<string, { lastDate: string | null; status: 'fresh' }> = {};
  const sortedDates = Array.from(dayMap.keys()).sort();
  const latestDate = sortedDates[sortedDates.length - 1] ?? today;
  const recentDates = sortedDates.slice(-3).reverse();
  function findLatestWith(field: 'recoveryScore' | 'totalSleepHours' | 'dailyStrain' | 'hrvMs' | 'restingHrBpm'): string | null {
    for (const d of recentDates) {
      const day = dayMap.get(d);
      const v = day ? (day as any)[field] : null;
      if (typeof v === 'number' && Number.isFinite(v)) return d;
    }
    return null;
  }
  const recoveryAt = findLatestWith('recoveryScore');
  if (recoveryAt) domains.recovery = { lastDate: recoveryAt, status: 'fresh' };
  const sleepAt = findLatestWith('totalSleepHours');
  if (sleepAt) domains.sleep = { lastDate: sleepAt, status: 'fresh' };
  const strainAt = findLatestWith('dailyStrain');
  if (strainAt) domains.strain = { lastDate: strainAt, status: 'fresh' };
  const hrvAt = findLatestWith('hrvMs');
  if (hrvAt) domains.hrv = { lastDate: hrvAt, status: 'fresh' };
  const rhrAt = findLatestWith('restingHrBpm');
  if (rhrAt) domains.resting_hr = { lastDate: rhrAt, status: 'fresh' };
  for (const d of recentDates) {
    const day = dayMap.get(d);
    if (day?.workoutCount && day.workoutCount > 0) {
      domains.workouts = { lastDate: d, status: 'fresh' };
      break;
    }
  }

  const anyOk = results.some((r) => r.ok && r.count > 0);
  await storeInstance.saveSourceHealth(userId, 'whoop_direct', {
    id: `source_health_whoop_direct_${userId}`,
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId: userId,
    provider: 'whoop_direct',
    lastSuccessfulIngestAt: now,
    lastFailedIngestAt: null,
    freshnessStatus: Object.keys(domains).length > 0 ? 'fresh' : (anyOk ? 'stale' : 'missing'),
    coverageByDomain: domains,
    upstreamStatus: 'healthy',
    degradedReason: null,
  } as any);

  // Status file for the integration card. 'connected' when we have
  // the four readiness-gating domains; 'partial' when some present;
  // 'error' when nothing fetched at all.
  const ALL_DOMAINS = ['recovery', 'hrv', 'resting_hr', 'strain', 'sleep', 'workouts'];
  const domainsAvailable = Object.keys(domains);
  const missingDomains = ALL_DOMAINS.filter((d) => !domainsAvailable.includes(d));
  const readinessGating = ['recovery', 'hrv', 'strain', 'sleep'];
  const hasReadinessGating = readinessGating.every((d) => domainsAvailable.includes(d));
  const statusLabel =
    domainsAvailable.length === 0
      ? anyOk ? 'partial' : 'error'
      : hasReadinessGating ? 'connected' : 'partial';

  await writeJson(statusPath(userId, 'whoop_direct'), {
    status: statusLabel,
    lastSyncAt: now,
    reason: statusLabel === 'partial'
      ? `WHOOP synced but missing: ${missingDomains.join(', ')}. Likely the most recent sleep/cycle hasn't been scored by WHOOP yet.`
      : statusLabel === 'error'
        ? 'Sync failed — no WHOOP endpoints returned data.'
        : null,
    domainsAvailable,
    missingDomains,
    latestDayDate: latestDate,
    normalizedDaysCreated,
  });

  res.json({
    ok: true,
    syncedAt: now,
    results,
    normalizedDaysCreated,
    domainsAvailable,
    missingDomains,
    latestDayDate: latestDate,
    status: statusLabel,
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// WHOOP CSV — optional manual enrichment upload (deep history)
// ═══════════════════════════════════════════════════════════════════════════
//
// Live WHOOP API stays canonical for recent/readiness data. This path
// accepts a user-uploaded WHOOP export (`recoveries.csv`, `sleeps.csv`)
// and writes enriched rows under `derivationVersion: 'whoop_csv_v1'`
// in a separate directory so they never collide with API rows.
//
// No auto-sync. Everything is user-initiated upload. Smart incremental:
// same file hash → skipped; same date + unchanged fields → skipped;
// existing non-null fields preserved across re-uploads.

const WHOOP_CSV_MAX_BYTES = 20 * 1024 * 1024; // 20 MB — 5-year export fits comfortably

function whoopCsvDayPath(userId: string, date: string): string {
  return path.join(DATA_DIR, userId, 'api-ai', 'whoop_csv_enriched_daily', `${date}.json`);
}
function whoopCsvSourceHealthPath(userId: string): string {
  return path.join(DATA_DIR, userId, 'api-ai', 'source_health_status', 'whoop_csv.json');
}

// GET /api/integrations/whoop/csv/status
router.get('/whoop/csv/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const sh = await readJson<any>(whoopCsvSourceHealthPath(userId));
  if (!sh) {
    return res.json({
      provider: 'whoop_csv',
      status: 'not_imported',
      note: 'Optional deep-history enrichment. WHOOP CSV is user-upload only — there is no automated source.',
      lastImportAt: null,
      earliestDate: null,
      latestDate: null,
      totalRowsIngested: 0,
      domainsFilled: [],
    });
  }
  res.json({
    provider: 'whoop_csv',
    status: 'imported',
    lastImportAt: sh.lastImportAt ?? null,
    lastAttemptAt: sh.lastAttemptAt ?? null,
    earliestDate: sh.earliestDate ?? null,
    latestDate: sh.latestDate ?? null,
    totalRowsIngested: sh.totalRowsIngested ?? 0,
    lastImportRowsNew: sh.lastImportRowsNew ?? 0,
    lastImportWindowStart: sh.lastImportWindowStart ?? null,
    lastImportWindowEnd: sh.lastImportWindowEnd ?? null,
    domainsFilled: sh.domainsFilled ?? [],
    lastWarnings: sh.lastWarnings ?? [],
    note: sh.note ?? null,
  });
});

// POST /api/integrations/whoop/csv/upload
// Body shape: { files: { 'recoveries.csv': '<csv text>', 'sleeps.csv': '<csv text>' } }
// Each value is the full CSV contents as a string. Mobile reads the
// file with expo-document-picker + FileSystem.readAsStringAsync.
router.post('/whoop/csv/upload', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const files = req.body?.files;
  if (!files || typeof files !== 'object' || Array.isArray(files)) {
    return res.status(400).json({ error: "Missing 'files' map in body. Send { files: { 'recoveries.csv': '<csv>', ... } }" });
  }
  // Size guard — reject the whole upload if any single file exceeds
  // the cap. 20MB is generous enough for 5 years of recoveries +
  // sleeps with decimal precision.
  let totalBytes = 0;
  for (const v of Object.values(files)) {
    if (typeof v !== 'string') {
      return res.status(400).json({ error: 'Each file value must be a string (CSV text).' });
    }
    totalBytes += Buffer.byteLength(v, 'utf8');
    if (totalBytes > WHOOP_CSV_MAX_BYTES) {
      return res.status(413).json({ error: `Upload exceeds ${WHOOP_CSV_MAX_BYTES / 1024 / 1024}MB combined size.` });
    }
  }
  // Hash the canonicalised bundle — sorted filenames + contents —
  // so reuploading the same zip in different order still dedups.
  const hash = crypto.createHash('sha256');
  for (const name of Object.keys(files).sort()) {
    hash.update(name);
    hash.update('\n');
    hash.update(String(files[name]));
    hash.update('\n');
  }
  const fileHash = hash.digest('hex');

  // Lazy-load the parser + ingest to keep server cold start light.
  const { parseWhoopCsvBundle } = await import('../../../../packages/shared/src/backend/services/whoop/parse-whoop-csv');
  const { ingestWhoopCsvForAthlete } = await import('../../../../packages/shared/src/backend/services/whoop/ingest-whoop-csv');
  const parsed = parseWhoopCsvBundle(files as Record<string, string>);

  // Adapter bridging CsvIngestStore to our file layout. CSV rows live
  // under `whoop_csv_enriched_daily/` so they never collide with
  // `normalized_daily_metrics/` (which is owned by whoop_direct_v1).
  const store = {
    async getNormalizedDay(_athleteId: string, date: string, _derivationVersion: string) {
      return readJson<any>(whoopCsvDayPath(userId, date));
    },
    async saveNormalizedDay(_athleteId: string, day: any) {
      await writeJson(whoopCsvDayPath(userId, day.date), day);
    },
    async getSourceHealth(_athleteId: string, _provider: 'whoop_csv') {
      return readJson<any>(whoopCsvSourceHealthPath(userId));
    },
    async saveSourceHealth(_athleteId: string, _provider: 'whoop_csv', sh: any) {
      await writeJson(whoopCsvSourceHealthPath(userId), sh);
    },
  };

  const result = await ingestWhoopCsvForAthlete({
    athleteId: userId,
    fileHash,
    parsed,
    store,
  });

  res.json({
    ok: true,
    fileHash,
    rowsConsidered: result.rowsConsidered,
    rowsNew: result.rowsNew,
    rowsSkippedDuplicate: result.rowsSkippedDuplicate,
    windowStart: result.windowStart,
    windowEnd: result.windowEnd,
    domainsFilled: result.domainsFilled,
    warnings: result.warnings,
    skippedReason: result.skippedReason ?? null,
    // Per-file detection summary so the UI can show
    // "Imported X · Skipped Y" truthfully.
    filesDetected: parsed.filesDetected,
    filesSkipped: parsed.filesSkipped,
  });
});

// POST /api/integrations/whoop/csv/upload-zip
// Body shape: { zipBase64: '<base64 of the WHOOP export .zip>' }
// Server-side unzips, picks out supported CSVs, reuses the bundle
// parser + ingest adapter. Mobile sends one file instead of copy-
// pasting each CSV. Rejects > WHOOP_CSV_MAX_BYTES of decoded bytes.
router.post('/whoop/csv/upload-zip', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const b64 = req.body?.zipBase64;
  if (typeof b64 !== 'string' || b64.length === 0) {
    return res.status(400).json({ error: "Missing 'zipBase64' in body." });
  }
  let zipBuffer: Buffer;
  try {
    zipBuffer = Buffer.from(b64, 'base64');
  } catch {
    return res.status(400).json({ error: 'zipBase64 is not valid base64.' });
  }
  if (zipBuffer.length > WHOOP_CSV_MAX_BYTES) {
    return res.status(413).json({ error: `Zip exceeds ${WHOOP_CSV_MAX_BYTES / 1024 / 1024}MB.` });
  }
  // Dynamic import jszip so the server cold-start isn't blocked
  // when no one is using this route.
  let JSZip: any;
  try {
    ({ default: JSZip } = await import('jszip'));
  } catch (e: any) {
    return res.status(500).json({ error: 'Zip library not installed on server.' });
  }
  let zip: any;
  try {
    zip = await JSZip.loadAsync(zipBuffer);
  } catch (e: any) {
    return res.status(400).json({ error: `Not a valid zip: ${e?.message ?? 'parse failed'}` });
  }
  // Walk the archive. Pick out every entry that looks like a CSV
  // regardless of directory nesting — WHOOP exports often nest files
  // under a timestamped folder. Cap total extracted size so a bomb
  // can't eat memory.
  const files: Record<string, string> = {};
  let extractedBytes = 0;
  const entries = Object.entries(zip.files as Record<string, any>);
  for (const [entryName, entry] of entries) {
    if (entry.dir) continue;
    if (!/\.csv$/i.test(entryName)) continue;
    // Take basename only so the parser's filename-based detection
    // (recoveries.csv / sleeps.csv / etc.) works regardless of path.
    const baseName = entryName.split('/').pop() ?? entryName;
    try {
      const text = await entry.async('string');
      extractedBytes += Buffer.byteLength(text, 'utf8');
      if (extractedBytes > WHOOP_CSV_MAX_BYTES) {
        return res.status(413).json({ error: `Extracted content exceeds ${WHOOP_CSV_MAX_BYTES / 1024 / 1024}MB.` });
      }
      // If the zip has duplicate basenames (unusual) prefix with a
      // short hash of the path to disambiguate.
      const key = files[baseName] ? `${baseName.replace(/\.csv$/i, '')}_${Math.abs(entryName.length).toString(36)}.csv` : baseName;
      files[key] = text;
    } catch {
      /* skip a single unreadable entry, continue with the rest */
    }
  }
  if (Object.keys(files).length === 0) {
    return res.status(400).json({ error: 'No CSV files found inside the zip.' });
  }
  // Hash the canonicalised bundle — sorted filenames + contents —
  // so re-uploading the same zip is a no-op.
  const hash = crypto.createHash('sha256');
  for (const name of Object.keys(files).sort()) {
    hash.update(name); hash.update('\n'); hash.update(files[name]); hash.update('\n');
  }
  const fileHash = hash.digest('hex');

  const { parseWhoopCsvBundle } = await import('../../../../packages/shared/src/backend/services/whoop/parse-whoop-csv');
  const { ingestWhoopCsvForAthlete } = await import('../../../../packages/shared/src/backend/services/whoop/ingest-whoop-csv');
  const parsed = parseWhoopCsvBundle(files);

  const store = {
    async getNormalizedDay(_athleteId: string, date: string, _derivationVersion: string) {
      return readJson<any>(whoopCsvDayPath(userId, date));
    },
    async saveNormalizedDay(_athleteId: string, day: any) {
      await writeJson(whoopCsvDayPath(userId, day.date), day);
    },
    async getSourceHealth(_athleteId: string, _provider: 'whoop_csv') {
      return readJson<any>(whoopCsvSourceHealthPath(userId));
    },
    async saveSourceHealth(_athleteId: string, _provider: 'whoop_csv', sh: any) {
      await writeJson(whoopCsvSourceHealthPath(userId), sh);
    },
  };

  const result = await ingestWhoopCsvForAthlete({
    athleteId: userId,
    fileHash,
    parsed,
    store,
  });

  res.json({
    ok: true,
    fileHash,
    rowsConsidered: result.rowsConsidered,
    rowsNew: result.rowsNew,
    rowsSkippedDuplicate: result.rowsSkippedDuplicate,
    windowStart: result.windowStart,
    windowEnd: result.windowEnd,
    domainsFilled: result.domainsFilled,
    warnings: result.warnings,
    skippedReason: result.skippedReason ?? null,
    filesDetected: parsed.filesDetected,
    filesSkipped: parsed.filesSkipped,
    zipFilesExtracted: Object.keys(files).length,
  });
});

// POST /api/integrations/whoop/csv/clear
router.post('/whoop/csv/clear', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  try {
    const dir = path.join(DATA_DIR, userId, 'api-ai', 'whoop_csv_enriched_daily');
    await fs.rm(dir, { recursive: true, force: true });
    await fs.rm(whoopCsvSourceHealthPath(userId), { force: true });
    res.json({ ok: true });
  } catch (e: any) {
    res.status(500).json({ error: e?.message ?? 'Clear failed' });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// CONCEPT2 (import-ready boundary)
// ═══════════════════════════════════════════════════════════════════════════

// GET /api/integrations/concept2/status
router.get('/concept2/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  const status = await readJson<any>(statusPath(userId, 'concept2'));
  res.json({
    provider: 'concept2',
    status: status?.status ?? 'not_connected',
    reason: status?.reason ?? 'Concept2 integration is import-ready. You can log sessions manually or import from the Concept2 Logbook when that adapter is built.',
    availablePaths: [
      { path: 'manual', status: 'available', description: 'Manual HIIT session entry with sets/watts/HR.' },
      { path: 'concept2_logbook', status: 'not_implemented', description: 'Import from Concept2 Logbook API (requires Concept2 developer credentials).' },
      { path: 'ergdata_health_connect', status: 'detection_only', description: 'Detect Concept2/ErgData-origin workouts in Health Connect data by provenance.' },
      { path: 'concept2_pm5_live', status: 'not_implemented', description: 'Direct BLE connection to PM5 (requires native BLE module).' },
    ],
    lastSyncAt: status?.lastSyncAt ?? null,
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// SAMSUNG HEALTH DIRECT
// ═══════════════════════════════════════════════════════════════════════════

// GET /api/integrations/samsung-health/status
router.get('/samsung-health/status', requireAuth, async (req: any, res: any) => {
  const userId = req.userId;
  // Check for Samsung Health via Health Connect first (existing working path)
  const viaHcStatus = await readJson<any>(
    path.join(DATA_DIR, userId, 'api-ai', 'source_health_status', 'samsung_health_via_health_connect.json'),
  );
  const directStatus = await readJson<any>(statusPath(userId, 'samsung_health_direct'));

  res.json({
    provider: 'samsung_health',
    paths: {
      via_health_connect: {
        status: viaHcStatus?.freshnessStatus ?? 'not_connected',
        lastIngestAt: viaHcStatus?.lastSuccessfulIngestAt ?? null,
        coverage: Object.keys(viaHcStatus?.coverageByDomain ?? {}),
        description: 'Samsung Health → Health Connect → app. Works when Samsung Health has Health Connect sync enabled.',
      },
      direct: {
        status: directStatus?.status ?? 'sdk_required',
        lastSyncAt: directStatus?.lastSyncAt ?? null,
        reason: directStatus?.reason ?? 'Samsung Health Data SDK integration is not yet implemented. The old Samsung Health SDK was deprecated in July 2025 in favor of the Samsung Health Data SDK.',
        setupRequired: [
          'Samsung Health Data SDK must be added as a native dependency.',
          'Samsung Partner approval may be required for privileged health data access.',
          'A new APK build is required after adding the native SDK.',
        ],
        description: 'Direct Samsung Health Data SDK for richer data access (stress, blood oxygen, detailed sleep stages).',
      },
    },
    recommendation: viaHcStatus?.freshnessStatus === 'fresh'
      ? 'Samsung Health via Health Connect is working. Direct SDK integration is optional for additional data types.'
      : 'Enable Health Connect sync in Samsung Health settings first. Direct SDK integration is a future option.',
  });
});

export default router;
