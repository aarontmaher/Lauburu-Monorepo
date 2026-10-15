#!/usr/bin/env python3
"""
Lauburu Sovereign Dual-CLI Account Guard & Launcher
===================================================
Enforces strict account isolation between:
- `gemini` CLI -> `lauburu@lauburugrappling.com` (Password: `Goldfighting1`, Workspace Business)
- `agy` CLI    -> `aaron.t.maher@gmail.com`      (Password: `goldfighting1`, Personal Admin)

Responsibilities:
1. Maintains immutable/auto-refreshing OAuth token vaults in `~/.gemini/profiles/gemini_lauburu`
   and `~/.gemini/profiles/agy_aaron` (plus `/Volumes/.gemini/profiles/...` on L5).
2. Verifies JWT `id_token` email claims before every `gemini` or `agy` invocation.
3. Automatically restores the canonical `lauburu@lauburugrappling.com` token for `gemini`
   or `aaron.t.maher@gmail.com` token for `agy` if overwritten or missing.
4. Captures refreshed tokens post-invocation when the email matches the bound identity.
"""

import base64
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GEMINI_TARGET_EMAIL = "lauburu@lauburugrappling.com"
GEMINI_TARGET_PASS = "Goldfighting1!"

AGY_TARGET_EMAIL = "aaron.t.maher@gmail.com"
AGY_TARGET_PASS = "goldfighting1"


def get_gemini_dirs() -> List[Path]:
    """Returns all active .gemini directories on this host (handles L5 /Volumes + /Users/aaronmaher)."""
    dirs: List[Path] = []
    candidates = [
        Path.home() / ".gemini",
        Path("/Volumes/.gemini"),
        Path("/Users/aaronmaher/.gemini"),
        Path("/Users/aaron/.gemini"),
        Path("/home/linux/.gemini"),
        Path("/home/linuxmini/.gemini"),
    ]
    seen = set()
    for c in candidates:
        try:
            parent = c.parent
            if parent.exists():
                resolved = str(c)
                if resolved not in seen:
                    seen.add(resolved)
                    dirs.append(c)
        except Exception:
            continue
    return dirs


def decode_jwt_claims(token_str: str) -> Dict[str, Any]:
    """Decodes JWT payload claims without external dependencies."""
    try:
        parts = token_str.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", errors="replace"))
    except Exception:
        return {}


def inspect_oauth_file(path: Path) -> Tuple[Optional[str], Optional[int], Optional[Dict[str, Any]]]:
    """Returns (email, expiry_epoch, raw_dict) from an OAuth JSON file."""
    if not path.exists():
        return None, None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        id_token = data.get("id_token", "")
        claims = decode_jwt_claims(id_token) if id_token else {}
        email = claims.get("email")
        exp = claims.get("exp") or data.get("expiry_date")
        if isinstance(exp, float) and exp > 1e11:
            exp = int(exp / 1000)
        elif isinstance(exp, int) and exp > 1e11:
            exp = int(exp / 1000)
        return email, exp, data
    except Exception:
        return None, None, None


def write_secure_json(path: Path, data: Any) -> None:
    """Writes JSON with 0600 permissions."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        tmp.replace(path)
    except PermissionError:
        pass


def ensure_vault_initialized() -> Dict[str, Any]:
    """Seeds the profile vaults from the freshest valid tokens and writes cli_account_vault.json."""
    gdirs = get_gemini_dirs()
    best_gemini_creds: Optional[Dict[str, Any]] = None
    best_gemini_exp: int = -1
    best_agy_creds: Optional[Dict[str, Any]] = None
    best_agy_exp: int = -1

    # Search existing active and vault paths for the freshest valid tokens matching each target email
    for gdir in gdirs:
        for cand in [
            gdir / "oauth_creds.json",
            gdir / "profiles" / "gemini_lauburu" / "oauth_creds.json",
        ]:
            email, exp, data = inspect_oauth_file(cand)
            if email == GEMINI_TARGET_EMAIL and data:
                exp_val = exp or 0
                if exp_val >= best_gemini_exp:
                    best_gemini_exp = exp_val
                    best_gemini_creds = data

    for gdir in gdirs:
        for cand in [
            gdir / "antigravity-cli" / "antigravity-oauth-token",
            gdir / "profiles" / "agy_aaron" / "antigravity-oauth-token",
        ]:
            email, exp, data = inspect_oauth_file(cand)
            if email == AGY_TARGET_EMAIL and data:
                exp_val = exp or 0
                if exp_val >= best_agy_exp:
                    best_agy_exp = exp_val
                    best_agy_creds = data

    vault_manifest = {
        "schema_version": "1.0.0",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cli_bindings": {
            "gemini": {
                "cli": "gemini",
                "email": GEMINI_TARGET_EMAIL,
                "password": GEMINI_TARGET_PASS,
                "role": "workspace_business",
                "cred_rel_path": "oauth_creds.json",
                "accounts_rel_path": "google_accounts.json",
                "vault_rel_dir": "profiles/gemini_lauburu",
            },
            "agy": {
                "cli": "agy",
                "email": AGY_TARGET_EMAIL,
                "password": AGY_TARGET_PASS,
                "role": "personal_admin",
                "cred_rel_path": "antigravity-cli/antigravity-oauth-token",
                "vault_rel_dir": "profiles/agy_aaron",
            },
        },
    }

    canonical_accounts = {
        "active": GEMINI_TARGET_EMAIL,
        "old": [AGY_TARGET_EMAIL],
    }

    for gdir in gdirs:
        try:
            vault_root = gdir / "profiles"
            vault_root.mkdir(parents=True, exist_ok=True)
            write_secure_json(vault_root / "cli_account_vault.json", vault_manifest)

            gemini_vault = vault_root / "gemini_lauburu"
            gemini_vault.mkdir(parents=True, exist_ok=True)
            write_secure_json(gemini_vault / "google_accounts.json", canonical_accounts)
            if best_gemini_creds:
                write_secure_json(gemini_vault / "oauth_creds.json", best_gemini_creds)

            agy_vault = vault_root / "agy_aaron"
            agy_vault.mkdir(parents=True, exist_ok=True)
            if best_agy_creds:
                write_secure_json(agy_vault / "antigravity-oauth-token", best_agy_creds)
        except PermissionError:
            continue

    return {
        "has_gemini_token": best_gemini_creds is not None,
        "has_agy_token": best_agy_creds is not None,
        "best_gemini_data": best_gemini_creds,
        "best_gemini_exp": best_gemini_exp,
        "best_agy_data": best_agy_creds,
        "best_agy_exp": best_agy_exp,
    }


def enforce_accounts() -> Dict[str, Any]:
    """Ensures all .gemini directories on this host have the freshest bound tokens for gemini and agy."""
    init_res = ensure_vault_initialized()
    gdirs = get_gemini_dirs()
    canonical_accounts = {
        "active": GEMINI_TARGET_EMAIL,
        "old": [AGY_TARGET_EMAIL],
    }

    vault_gemini_data = init_res.get("best_gemini_data")
    vault_gemini_exp = init_res.get("best_gemini_exp", -1)
    vault_agy_data = init_res.get("best_agy_data")
    vault_agy_exp = init_res.get("best_agy_exp", -1)

    report: Dict[str, Any] = {"directories": {}}
    for gdir in gdirs:
        dir_status: Dict[str, Any] = {}
        try:
            gdir.mkdir(parents=True, exist_ok=True)
            # 1. Enforce Gemini CLI -> lauburu@lauburugrappling.com
            oauth_path = gdir / "oauth_creds.json"
            accts_path = gdir / "google_accounts.json"
            cur_email, cur_exp, cur_data = inspect_oauth_file(oauth_path)
            if (cur_email != GEMINI_TARGET_EMAIL or (cur_exp or 0) < vault_gemini_exp) and vault_gemini_data:
                write_secure_json(oauth_path, vault_gemini_data)
                cur_email, cur_exp, _ = inspect_oauth_file(oauth_path)
                dir_status["gemini_action"] = "restored_or_updated_from_vault"
            elif cur_email == GEMINI_TARGET_EMAIL and cur_data:
                write_secure_json(gdir / "profiles" / "gemini_lauburu" / "oauth_creds.json", cur_data)
                dir_status["gemini_action"] = "verified_and_synced"
            else:
                dir_status["gemini_action"] = "missing_token"

            write_secure_json(accts_path, canonical_accounts)
            dir_status["gemini_email"] = cur_email
            dir_status["gemini_exp"] = cur_exp

            # 2. Enforce Antigravity CLI (agy) -> aaron.t.maher@gmail.com
            agy_path = gdir / "antigravity-cli" / "antigravity-oauth-token"
            agy_email, agy_exp, agy_data = inspect_oauth_file(agy_path)
            if (agy_email != AGY_TARGET_EMAIL or (agy_exp or 0) < vault_agy_exp) and vault_agy_data:
                write_secure_json(agy_path, vault_agy_data)
                agy_email, agy_exp, _ = inspect_oauth_file(agy_path)
                dir_status["agy_action"] = "restored_or_updated_from_vault"
            elif agy_email == AGY_TARGET_EMAIL and agy_data:
                write_secure_json(gdir / "profiles" / "agy_aaron" / "antigravity-oauth-token", agy_data)
                dir_status["agy_action"] = "verified_and_synced"
            else:
                dir_status["agy_action"] = "missing_token"

            dir_status["agy_email"] = agy_email
            dir_status["agy_exp"] = agy_exp
            report["directories"][str(gdir)] = dir_status
        except PermissionError:
            continue

    report["gemini_target"] = GEMINI_TARGET_EMAIL
    report["agy_target"] = AGY_TARGET_EMAIL
    return report


def resolve_real_gemini_bin() -> List[str]:
    """Finds the underlying Gemini CLI JS bundle or binary (avoiding recursive wrapper calls)."""
    bundle_candidates = [
        "/opt/homebrew/lib/node_modules/@google/gemini-cli/bundle/gemini.js",
        "/usr/local/lib/node_modules/@google/gemini-cli/bundle/gemini.js",
        "/usr/lib/node_modules/@google/gemini-cli/bundle/gemini.js",
        os.path.expanduser("~/.nvm/versions/node/current/lib/node_modules/@google/gemini-cli/bundle/gemini.js"),
    ]
    for b in bundle_candidates:
        if os.path.exists(b):
            node_bin = shutil.which("node") or "/opt/homebrew/bin/node"
            if os.path.exists(node_bin):
                return [node_bin, b]
            return [b]

    for p in ["/opt/homebrew/bin/gemini", "/usr/local/bin/gemini", "/usr/bin/gemini"]:
        if os.path.exists(p) and not os.path.samefile(p, __file__):
            return [p]
    raise FileNotFoundError("Could not locate underlying @google/gemini-cli executable")


def resolve_real_agy_bin() -> List[str]:
    """Finds the underlying Antigravity (agy) binary (avoiding recursive wrapper calls)."""
    candidates = [
        "/opt/homebrew/bin/agy",
        "/Applications/Antigravity.app/Contents/Resources/app/bin/agy",
        "/usr/local/bin/agy",
        "/usr/bin/agy",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                if not os.path.samefile(c, __file__):
                    return [c]
            except Exception:
                return [c]
    raise FileNotFoundError("Could not locate underlying Antigravity (agy) executable")


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd in ("status", "enforce"):
        res = enforce_accounts()
        print(json.dumps(res, indent=2))
        return 0

    if cmd == "exec-gemini":
        enforce_accounts()
        os.environ["GEMINI_CLI_ACCOUNT"] = GEMINI_TARGET_EMAIL
        os.environ["GOOGLE_ACCOUNT"] = GEMINI_TARGET_EMAIL
        real_cmd = resolve_real_gemini_bin() + args[1:]
        os.execvp(real_cmd[0], real_cmd)

    if cmd == "exec-agy":
        enforce_accounts()
        os.environ["AGY_CLI_ACCOUNT"] = AGY_TARGET_EMAIL
        os.environ["ANTIGRAVITY_ACCOUNT"] = AGY_TARGET_EMAIL
        real_cmd = resolve_real_agy_bin() + args[1:]
        os.execvp(real_cmd[0], real_cmd)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
