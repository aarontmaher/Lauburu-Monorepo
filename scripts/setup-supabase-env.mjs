#!/usr/bin/env node
/**
 * scripts/setup-supabase-env.mjs
 *
 * One-paste setup for the Supabase writer env that
 * `npm run bridge:snapshot` (and other local-only canonical-store
 * writers) need.
 *
 * Aaron runs:   npm run setup:supabase
 *
 * The script prompts for SUPABASE_URL + service-role secret,
 * validates both, and writes a clean .env.local at the repo root.
 * Existing .env.local keys unrelated to Supabase are preserved;
 * any pre-existing SUPABASE_* lines (including duplicate or
 * corrupted ones from manual nano edits) are removed first.
 *
 * Security invariants:
 *   - The secret is read with terminal echo OFF (raw stdin masked
 *     with '*'); ctrl-C exits cleanly.
 *   - The secret is never printed in full at any stage; only a
 *     prefix...suffix preview with the length is shown.
 *   - .env.local is chmod 600 after write.
 *   - .env.local is .gitignore'd by repo policy (already true; the
 *     script also asserts this and refuses to write if the
 *     gitignore contract is missing).
 *   - The script does NOT push the values to Cloudflare or any
 *     remote — that path uses `wrangler secret put` per the
 *     "Wrangler secret hints" output below.
 *   - Any existing secret in the working tree is treated as
 *     potentially exposed; the script reminds Aaron to rotate it
 *     after setup is confirmed.
 */

import { readFileSync, writeFileSync, existsSync, chmodSync, renameSync } from 'node:fs';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';

const ROOT = process.cwd();
const ENV_PATH = resolve(ROOT, '.env.local');
const ENV_TMP_PATH = resolve(ROOT, '.env.local.tmp');
const GITIGNORE_PATH = resolve(ROOT, '.gitignore');

const SUPABASE_KEYS = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_SECRET_KEY'];

// Control character codes (avoids editor / save stripping of literals).
const CC_CTRL_C = 0x03;
const CC_CTRL_D = 0x04;
const CC_BS = 0x08;
const CC_LF = 0x0a;
const CC_CR = 0x0d;
const CC_DEL = 0x7f;

// ── helpers ──────────────────────────────────────────────────────

function maskSecret(s) {
  if (!s) return '(empty)';
  if (s.length < 12) return `${'*'.repeat(s.length)} (${s.length} chars — looks too short for a real key)`;
  return `${s.slice(0, 6)}…${s.slice(-4)} (${s.length} chars)`;
}

function askLine(prompt) {
  return new Promise((resolveFn) => {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, (answer) => {
      rl.close();
      resolveFn(answer.trim());
    });
  });
}

/**
 * Read a single line from stdin with terminal echo OFF, replacing
 * each char with '*'. Handles backspace (DEL / BS) and ctrl-C.
 */
function askHidden(prompt) {
  return new Promise((resolveFn, rejectFn) => {
    if (!process.stdin.isTTY) {
      rejectFn(new Error('Refusing to read secret from non-TTY stdin (cannot mask). Run this script in an interactive shell, not piped.'));
      return;
    }
    process.stdout.write(prompt);
    let buf = '';
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');

    function done(answer) {
      process.stdin.setRawMode(false);
      process.stdin.pause();
      process.stdin.removeListener('data', onData);
      process.stdout.write('\n');
      resolveFn(answer);
    }

    function onData(chunk) {
      for (const c of chunk) {
        const code = c.charCodeAt(0);
        if (code === CC_CTRL_C) {
          process.stdin.setRawMode(false);
          process.stdout.write('\n');
          process.exit(130);
        }
        if (code === CC_CR || code === CC_LF || code === CC_CTRL_D) {
          done(buf.trim());
          return;
        }
        if (code === CC_DEL || code === CC_BS) {
          if (buf.length > 0) {
            buf = buf.slice(0, -1);
            process.stdout.write('\b \b');
          }
          continue;
        }
        if (code >= 0x20 && code <= 0x7e) {
          buf += c;
          process.stdout.write('*');
        }
      }
    }

    process.stdin.on('data', onData);
  });
}

function validateUrl(url) {
  if (!url) return 'SUPABASE_URL is empty.';
  if (!/^https:\/\/[A-Za-z0-9-]+\.supabase\.co\/?$/.test(url)) {
    return 'SUPABASE_URL must look like https://<project-ref>.supabase.co (no trailing path).';
  }
  return null;
}

function classifyKey(key) {
  if (!key) return { kind: 'empty', message: 'secret is empty.' };
  if (key.startsWith('sb_secret_') && key.length >= 30) return { kind: 'modern', message: 'sb_secret_* (modern Supabase secret format).' };
  if (key.startsWith('eyJ') && key.split('.').length === 3 && key.length >= 100) {
    return { kind: 'legacy_jwt', message: 'legacy JWT service_role key (eyJ...).' };
  }
  return { kind: 'unknown', message: 'does not match known Supabase secret formats (sb_secret_* or eyJ JWT).' };
}

function ensureGitignored() {
  if (!existsSync(GITIGNORE_PATH)) {
    throw new Error('.gitignore is missing at repo root. Refusing to write .env.local — would risk committing secrets.');
  }
  const gi = readFileSync(GITIGNORE_PATH, 'utf8');
  const ok = /^\.env\.local\b/m.test(gi) || /^\*\*\/\.env\.local\b/m.test(gi);
  if (!ok) {
    throw new Error('.gitignore does not list .env.local (or **/.env.local). Add it before re-running this setup.');
  }
}

function readExistingEnv() {
  if (!existsSync(ENV_PATH)) return { rawLines: [] };
  const raw = readFileSync(ENV_PATH, 'utf8');
  return { rawLines: raw.split(/\r?\n/) };
}

function rebuildEnvLines(rawLines, supabaseUrl, supabaseSecret) {
  const preserved = [];
  let removedNonSupabase = 0;
  let removedSupabaseDuplicates = 0;

  for (const line of rawLines) {
    const trimmed = line.trim();
    if (trimmed === '') {
      preserved.push(line);
      continue;
    }
    if (trimmed.startsWith('#')) {
      preserved.push(line);
      continue;
    }
    const eq = trimmed.indexOf('=');
    if (eq <= 0) {
      // No "=" at all (or starts with "=") — corruption (shell command leak, partial paste). Drop.
      removedNonSupabase += 1;
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    if (!/^[A-Z_][A-Z0-9_]*$/.test(key)) {
      // Not a valid env-var name (e.g. "set -a" leaked in). Drop.
      removedNonSupabase += 1;
      continue;
    }
    if (SUPABASE_KEYS.includes(key)) {
      removedSupabaseDuplicates += 1;
      continue;
    }
    preserved.push(line);
  }

  // Trim trailing blank lines from preserved.
  while (preserved.length && preserved[preserved.length - 1].trim() === '') {
    preserved.pop();
  }

  const out = [];
  if (preserved.length > 0) {
    out.push(...preserved, '');
  }
  out.push('# Supabase canonical-store writer env (set by scripts/setup-supabase-env.mjs).');
  out.push('# Required by npm run bridge:snapshot to upsert connector_* tables.');
  out.push('# Service-role keys bypass RLS — keep this file local only.');
  out.push(`SUPABASE_URL="${supabaseUrl}"`);
  out.push(`SUPABASE_SERVICE_ROLE_KEY="${supabaseSecret}"`);
  out.push(`SUPABASE_SECRET_KEY="${supabaseSecret}"`);
  out.push('');

  return { lines: out, removedNonSupabase, removedSupabaseDuplicates };
}

function writeEnvAtomic(lines) {
  writeFileSync(ENV_TMP_PATH, lines.join('\n'), { mode: 0o600 });
  renameSync(ENV_TMP_PATH, ENV_PATH);
  chmodSync(ENV_PATH, 0o600);
}

// ── main flow ────────────────────────────────────────────────────

async function main() {
  console.log('Lauburu Supabase env setup');
  console.log('--------------------------');
  console.log('This will replace the SUPABASE_* lines in .env.local.');
  console.log('Other unrelated keys in .env.local are preserved.');
  console.log('Nothing leaves your laptop.');
  console.log('');

  ensureGitignored();

  let url;
  for (;;) {
    url = await askLine('SUPABASE_URL (e.g. https://abcdefgh.supabase.co): ');
    const err = validateUrl(url);
    if (!err) break;
    console.log(`  ✗ ${err}`);
  }
  url = url.replace(/\/$/, '');

  let secret;
  for (;;) {
    secret = await askHidden('SUPABASE service-role secret (input hidden): ');
    const cls = classifyKey(secret);
    if (cls.kind === 'modern' || cls.kind === 'legacy_jwt') {
      console.log(`  → detected ${cls.message}`);
      console.log(`  → secret preview: ${maskSecret(secret)}`);
      break;
    }
    console.log(`  ✗ secret ${cls.message} retry.`);
  }

  const confirm = await askLine('Write .env.local with these values? (y/N): ');
  if (!/^y(es)?$/i.test(confirm)) {
    console.log('Aborted; .env.local not modified.');
    process.exit(1);
  }

  const { rawLines } = readExistingEnv();
  const { lines, removedNonSupabase, removedSupabaseDuplicates } = rebuildEnvLines(rawLines, url, secret);
  writeEnvAtomic(lines);

  console.log('');
  console.log(`✓ wrote ${ENV_PATH} (chmod 600)`);
  if (removedNonSupabase > 0) {
    console.log(`  removed ${removedNonSupabase} non-key line(s) (likely shell-command leak from manual edits)`);
  }
  if (removedSupabaseDuplicates > 0) {
    console.log(`  removed ${removedSupabaseDuplicates} prior SUPABASE_* line(s)`);
  }
  console.log('');
  console.log('Next:');
  console.log('  npm run bridge:snapshot   # should upsert to Supabase, no env_missing skip');
  console.log('');
  console.log('Wrangler secret hints (Cloudflare side — only if needed):');
  console.log('  cd cloudflare-worker');
  console.log('  npx wrangler secret put SUPABASE_URL --env preview');
  console.log('  npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --env preview');
  console.log('  # repeat with --env production if the production Worker also reads Supabase');
  console.log('');
  console.log('Security reminder:');
  console.log('  - This file is .gitignore\'d. Never commit it.');
  console.log('  - If the secret you pasted has been in any chat / log / doc / shell history before, rotate it in Supabase Dashboard → Project Settings → API → Reset service_role key, then re-run this script.');
}

main().catch((err) => {
  console.error('');
  console.error(`✗ setup failed: ${err.message}`);
  process.exit(1);
});
