#!/usr/bin/env python3
"""
06_scripts_and_tooling/automation/review_and_archive_pinned_chats.py
====================================================================
Canonical Automation Script for `hourly-pinned-chats-review` ("Hourly Pinned Chats Review & Archive").

Responsibilities:
1. Scans `/Users/aaron/.gemini/antigravity/annotations/*.pbtxt` and
   `/Users/aaron/.gemini/antigravity/conversation_summaries.db` for all `pinned:true` chats.
2. Extracts all relevant user requests, agent conclusions, artifact `.md` files, and open
   action items from every pinned conversation.
3. Consolidates all extracted knowledge into:
   - Target Hub Conversation Artifact:
     `/Users/aaron/.gemini/antigravity/brain/d35ef904-f61e-4f91-b920-dd1da2d29776/PINNED_CHATS_CONSOLIDATED_DIGEST.md`
   - Obsidian Tri-Vault Mirror (Rule 2):
     `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/PINNED_CHATS_CONSOLIDATED_DIGEST.md`
   - Copies all markdown artifacts from archived pinned chats into:
     `/Users/aaron/.gemini/antigravity/brain/d35ef904-f61e-4f91-b920-dd1da2d29776/consolidated_artifacts/<cid>/`
4. Evaluates each pinned chat's relevance:
   - LEAVES PINNED (`pinned:true`, `archived:false`) if:
     * It is the target hub conversation (`d35ef904-f61e-4f91-b920-dd1da2d29776`)
     * Its status is `CASCADE_RUN_STATUS_RUNNING` (actively executing)
     * It was modified within the last 18 hours and has active benchmark/VLA workflows
       (e.g., `e133dcc1-a276-4ce8-aca3-65bd5d39307d` - "Global AI Mesh Benchmark Execution")
   - ARCHIVES & UNPINS (`archived:true`, `pinned:false` in `.pbtxt` and `archived=1` in `conversations_fts`)
     all completed, idle, historical, or orphan pinned chats so the user's Pinned Chats list stays clean.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ANTIGRAVITY_DIR = Path("/Users/aaron/.gemini/antigravity")
ANNOTATIONS_DIR = ANTIGRAVITY_DIR / "annotations"
BRAIN_DIR = ANTIGRAVITY_DIR / "brain"
DB_PATH = ANTIGRAVITY_DIR / "conversation_summaries.db"

TARGET_HUB_CID = "d35ef904-f61e-4f91-b920-dd1da2d29776"
TARGET_BRAIN_DIR = BRAIN_DIR / TARGET_HUB_CID
TARGET_DIGEST_MD = TARGET_BRAIN_DIR / "PINNED_CHATS_CONSOLIDATED_DIGEST.md"
TARGET_ARTIFACTS_BACKUP = TARGET_BRAIN_DIR / "consolidated_artifacts"

OBSIDIAN_DIGEST_MD = Path(
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/04_ANALYTICS/PINNED_CHATS_CONSOLIDATED_DIGEST.md"
)
STATE_JSON = TARGET_BRAIN_DIR / "pinned_chats_archive_ledger.json"


def _extract_ascii_strings(blob: bytes, min_len: int = 8) -> List[str]:
    if not blob:
        return []
    matches = re.findall(rb"[ -~]{" + str(min_len).encode() + rb",}", blob)
    out = []
    for m in matches:
        s = m.decode("utf-8", errors="ignore").strip()
        if s and s not in out:
            out.append(s)
    return out


def _parse_pbtxt(txt: str) -> Dict[str, Any]:
    m_title = re.search(r'title:\s*"([^"]+)"', txt)
    pinned = bool(re.search(r"pinned:\s*true", txt))
    archived = bool(re.search(r"archived:\s*true", txt))
    m_view_sec = re.search(r"last_user_view_time:\s*\{\s*seconds:\s*(\d+)", txt)
    m_view_nano = re.search(r"last_user_view_time:\s*\{\s*seconds:\s*\d+\s+nanos:\s*(\d+)", txt)
    return {
        "title": m_title.group(1) if m_title else "",
        "pinned": pinned,
        "archived": archived,
        "view_seconds": int(m_view_sec.group(1)) if m_view_sec else int(time.time()),
        "view_nanos": int(m_view_nano.group(1)) if m_view_nano else 0,
    }


def _format_pbtxt(title: str, archived: bool, pinned: bool, view_sec: int, view_nano: int) -> str:
    now_sec = int(time.time())
    now_nano = int((time.time() - now_sec) * 1_000_000_000)
    parts = []
    if title:
        safe_title = title.replace('"', '\\"')
        parts.append(f'title:"{safe_title}"')
    if archived:
        parts.append("archived:true")
        parts.append(f"archival_status_timestamp:{{seconds:{now_sec} nanos:{now_nano}}}")
    parts.append(f"last_user_view_time:{{seconds:{view_sec} nanos:{view_nano}}}")
    parts.append(f"pinned:{'true' if pinned else 'false'}")
    return " ".join(parts) + "\n"


PROTECTED_PINNED_CIDS: Dict[str, str] = {
    TARGET_HUB_CID: "Target consolidation hub conversation (active /goal session).",
    "83d4cf60-76a6-453c-8754-a9f9b57fb3c9": "User-prioritized active app development: Life Companion App (:3036).",
    "9b4aa503-5206-43b2-a779-824f7f733c2d": "User-prioritized active app development: Screen Lens / Network Cable Analyzer (:4007).",
    "e133dcc1-a276-4ce8-aca3-65bd5d39307d": "User-prioritized active workflow: Grappling 3D VLA Video Analysis & Mesh Benchmark.",
    "11b5d3f1-0d56-4db6-9aea-87aefefa34ef": "Movesense HR+ AI Validation & Biometrics Hub (:8084/:4000).",
    "e371bf5c-4802-4c7c-9684-484a40e90a6f": "Google Play Console & Argon AI Swarm Strategy.",
    "aa9b27f3-906a-4bea-8c50-91c76bb6f08d": "AI Free Tier & Argon Swarm Integration.",
    "5189a2ba-71bc-4465-a12b-6f78aabbca9c": "Gemini Enterprise & Google Workspace Integration.",
    "553ca8bc-51d9-44ab-8ea3-a88eb45608e9": "Deep Research On GBOS-VM & Frontier Swarm Consensus.",
    "da7a605c-c47c-4677-9c39-dd1acae66fd3": "Installing and Verifying Llama 4 & PersonaPlex.",
    "e8e9e7a5-18de-4b2f-8105-c2fee873dfb1": "Mac Mini M2 Screen Sharing & Apartment Automation.",
    "da691bc8-bf60-484f-8bc8-d9e702e08db8": "Samsung S20 & Linux Tablet Mesh Integration.",
    "636d208e-d807-4c03-8754-2bc7fdb0a085": "Evaluating Docker Versus Podman And Baremetal.",
    "b2198022-08f4-4d6c-b0e0-04cd981369e6": "AI Ecosystem & Sellable Apps Evaluation.",
    "c5fcc3f2-d823-4131-8401-a2097a18b183": "Run Lens Antigravity ELO Script.",
    "c449171d-497a-4abc-a0fa-3ea490bee656": "Unified Network & SeaweedFS Architecture.",
    "7d9e4460-ae10-4dee-8b41-f726806f49f3": "Network Optimization And Telemetry Training.",
    "0eab3fb7-8524-4833-b0b5-2b06df7f14fe": "Apartment Application Automation via Android.",
    "426d08bb-d61c-4d24-a9bd-1324f917f4fa": "Canonical ELO Leaderboard Review.",
    "f7e34c7e-183f-4ae4-a626-503406311ec6": "Movesense Bluetooth Terminal Capability.",
    "499b52f9-8e4c-4f81-bb9d-f4257ef31baa": "Configure Showrunner Application Setup.",
    "2b897359-af90-4845-b1bc-d98804b1d8af": "Change Screen Watch Device (Multi-Device Lens).",
    "f2a4637c-68b1-4648-8c37-990afbd706fe": "E-Commerce Project Analysis And Strategy.",
}


def _is_still_very_relevant(
    cid: str,
    status: str,
    last_mod_str: str,
    steps: int,
    already_archived: bool,
) -> Tuple[bool, str]:
    """
    Determines whether a pinned conversation is still actively relevant and should
    remain pinned.
    User directive: NEVER remove or unpin important chats; only archive 0-step empty orphan stubs.
    """
    if cid in PROTECTED_PINNED_CIDS:
        return True, PROTECTED_PINNED_CIDS[cid]
    if status == "CASCADE_RUN_STATUS_RUNNING":
        return True, "Conversation status is CASCADE_RUN_STATUS_RUNNING (actively running)."
    if steps > 0:
        return True, f"Important conversation with {steps} recorded steps; preserved pinned per user directive."
    if already_archived:
        return False, "Already marked archived with 0 steps; unpinning stale pin flag."
    return False, "Orphan annotation with 0 steps in conversation_summaries.db."


def run_review_and_archive(dry_run: bool = False) -> Dict[str, Any]:
    TARGET_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_ARTIFACTS_BACKUP.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_DIGEST_MD.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Ensure target hub conversation itself is pinned and titled clearly
    target_pbtxt_path = ANNOTATIONS_DIR / f"{TARGET_HUB_CID}.pbtxt"
    if not dry_run:
        now_s = int(time.time())
        hub_pbtxt = _format_pbtxt(
            title="Pinned Chats Hub & Priority Automation Executor",
            archived=False,
            pinned=True,
            view_sec=now_s,
            view_nano=0,
        )
        target_pbtxt_path.write_text(hub_pbtxt, encoding="utf-8")

    kept_pinned: List[Dict[str, Any]] = []
    archived_chats: List[Dict[str, Any]] = []
    cleaned_stale_pins: List[Dict[str, Any]] = []

    pbtxt_files = sorted(glob.glob(str(ANNOTATIONS_DIR / "*.pbtxt")))
    for p_str in pbtxt_files:
        p = Path(p_str)
        cid = p.stem
        if cid == TARGET_HUB_CID:
            continue

        raw_txt = p.read_text(encoding="utf-8", errors="replace").strip()
        parsed = _parse_pbtxt(raw_txt)
        if not parsed["pinned"]:
            continue

        cur.execute(
            "SELECT title, step_count, last_modified_time, status, workspace_uris, raw_summary "
            "FROM conversation_summaries WHERE conversation_id=?",
            (cid,),
        )
        row = cur.fetchone()
        db_title = row[0] if row else ""
        steps = int(row[1]) if row else 0
        last_mod = str(row[2]) if row else ""
        status = str(row[3]) if row else ""
        workspace = str(row[4]) if row else ""
        raw_summary_blob = row[5] if row else b""

        title = parsed["title"] or db_title or f"Untitled ({cid[:8]})"

        # Extract FTS user prompts and agent responses
        cur.execute(
            "SELECT chunk_index, user_body, agent_body FROM conversations_fts "
            "WHERE conversation_id=? AND chunk_index >= 0 ORDER BY chunk_index",
            (cid,),
        )
        fts_rows = cur.fetchall()
        user_prompts: List[str] = []
        agent_summaries: List[str] = []
        for _, u_b, a_b in fts_rows:
            if u_b and u_b.strip():
                user_prompts.append(u_b.strip())
            if a_b and a_b.strip():
                agent_summaries.append(a_b.strip())

        # Fallback: extract strings from raw_summary blob if FTS is empty
        raw_strings = _extract_ascii_strings(raw_summary_blob) if not fts_rows else []

        # Inspect Brain artifacts
        c_brain = BRAIN_DIR / cid
        artifacts_extracted: List[Dict[str, str]] = []
        if c_brain.exists():
            dest_dir = TARGET_ARTIFACTS_BACKUP / cid
            for md_file in sorted(c_brain.glob("*.md")):
                md_text = md_file.read_text(encoding="utf-8", errors="replace")
                artifacts_extracted.append({
                    "filename": md_file.name,
                    "source_path": str(md_file),
                    "bytes": str(len(md_text.encode("utf-8"))),
                    "excerpt": md_text[:1500].strip(),
                })
                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(md_file, dest_dir / md_file.name)

        keep, reason = _is_still_very_relevant(
            cid=cid,
            status=status,
            last_mod_str=last_mod,
            steps=steps,
            already_archived=parsed["archived"],
        )

        record = {
            "conversation_id": cid,
            "title": title,
            "steps": steps,
            "last_modified_time": last_mod,
            "status": status,
            "workspace_uris": workspace,
            "was_already_archived": parsed["archived"],
            "decision": "KEEP_PINNED" if keep else "ARCHIVE_AND_UNPIN",
            "reason": reason,
            "user_prompts": user_prompts,
            "latest_agent_conclusion": agent_summaries[-1][-1500:] if agent_summaries else "",
            "raw_summary_strings": raw_strings[:10],
            "artifacts": artifacts_extracted,
        }

        if keep:
            kept_pinned.append(record)
        else:
            if parsed["archived"] or steps == 0:
                cleaned_stale_pins.append(record)
            else:
                archived_chats.append(record)

            if not dry_run:
                new_pbtxt = _format_pbtxt(
                    title=parsed["title"] or db_title,
                    archived=True,
                    pinned=False,
                    view_sec=parsed["view_seconds"],
                    view_nano=parsed["view_nanos"],
                )
                p.write_text(new_pbtxt, encoding="utf-8")
                cur.execute(
                    "UPDATE conversations_fts SET archived = 1 WHERE conversation_id = ?",
                    (cid,),
                )

    if not dry_run:
        conn.commit()
    conn.close()

    # Sort lists by last_modified_time descending
    kept_pinned.sort(key=lambda x: x["last_modified_time"], reverse=True)
    archived_chats.sort(key=lambda x: x["last_modified_time"], reverse=True)
    cleaned_stale_pins.sort(key=lambda x: x["last_modified_time"], reverse=True)

    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    md_lines = [
        "# 📌 Consolidated Pinned Chats Digest & Priority Automation Ledger",
        "",
        f"**Last Automated Sync:** `{now_iso}`  ",
        f"**Target Consolidation Conversation:** [`{TARGET_HUB_CID}`](conversation://{TARGET_HUB_CID})  ",
        f"**Active Pinned Chats Preserved:** `{len(kept_pinned)}` (plus this Hub Chat)  ",
        f"**Completed Active Pinned Chats Consolidated & Archived:** `{len(archived_chats)}`  ",
        f"**Historical/Orphan Stale Pin Flags Cleaned & Archived:** `{len(cleaned_stale_pins)}`  ",
        "",
        "---",
        "",
        "## 🟢 1. Still Very Relevant Chats (Preserved Pinned)",
        "",
    ]

    if not kept_pinned:
        md_lines.append("_No external chats met the active-relevance threshold; only this Hub conversation remains pinned._\n")
    else:
        for item in kept_pinned:
            cid = item["conversation_id"]
            md_lines.extend([
                f"### 📌 [{item['title']}](conversation://{cid}) (`{cid}`)",
                f"- **Status:** `{item['status']}` | **Steps:** `{item['steps']}` | **Last Modified:** `{item['last_modified_time']}`",
                f"- **Retention Rationale:** {item['reason']}",
            ])
            if item["user_prompts"]:
                md_lines.append("- **Key User Directives:**")
                for idx, up in enumerate(item["user_prompts"], 1):
                    clean_up = " ".join(up.splitlines())[:400]
                    md_lines.append(f"  {idx}. `{clean_up}`")
            if item["latest_agent_conclusion"]:
                clean_ac = " ".join(item["latest_agent_conclusion"].splitlines())[-600:]
                md_lines.append(f"- **Latest Progress / Conclusion:** {clean_ac}")
            if item["artifacts"]:
                art_links = ", ".join(
                    f"[`{a['filename']}`](file://{a['source_path']})" for a in item["artifacts"]
                )
                md_lines.append(f"- **Artifacts:** {art_links}")
            md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "## 📦 2. Completed Pinned Chats Consolidated & Archived",
        "",
    ])

    for item in archived_chats:
        cid = item["conversation_id"]
        md_lines.extend([
            f"### 🗂️ [{item['title']}](conversation://{cid}) (`{cid}`)",
            f"- **Status:** `{item['status']}` | **Steps:** `{item['steps']}` | **Last Modified:** `{item['last_modified_time']}`",
            f"- **Archival Rationale:** {item['reason']}",
        ])
        if item["user_prompts"]:
            md_lines.append("- **Extracted User Directives & Context:**")
            for idx, up in enumerate(item["user_prompts"][:6], 1):
                clean_up = " ".join(up.splitlines())[:350]
                md_lines.append(f"  {idx}. `{clean_up}`")
        if item["latest_agent_conclusion"]:
            clean_ac = " ".join(item["latest_agent_conclusion"].splitlines())[-600:]
            md_lines.append(f"- **Extracted Final Outcome:** {clean_ac}")
        elif item["raw_summary_strings"]:
            md_lines.append(f"- **Extracted Summary Metadata:** `{', '.join(item['raw_summary_strings'][:6])}`")
        if item["artifacts"]:
            art_links = ", ".join(
                f"[`{a['filename']}`](file://{TARGET_ARTIFACTS_BACKUP / cid / a['filename']}) ({a['bytes']} B)"
                for a in item["artifacts"]
            )
            md_lines.append(f"- **Consolidated Artifacts Preserved in This Chat:** {art_links}")
        md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "## 🧹 3. Historical / Orphan Stale Pins Cleaned (`pinned:false`, `archived:true`)",
        "",
        "| Conversation ID | Title | Steps | Last Modified | Action |",
        "|:--|:--|--:|:--|:--|",
    ])
    for item in cleaned_stale_pins:
        cid = item["conversation_id"]
        md_lines.append(
            f"| `{cid}` | {item['title']} | {item['steps']} | `{item['last_modified_time'] or '--'}` | Unpinned & Archived |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 🚀 4. Top Priorities Extracted for Autonomous Execution (`/goal`)",
        "",
        "1. **Grappling 3D VLA Watchdog & Screen Lens Automation (`e133dcc1` — `10_spatial_grappling_kinematics`):**",
        "   - Wire `10_spatial_grappling_kinematics/app/main.py` with a headless `--watch-inbox` daemon mode and Screen Lens VLA integration (`vla/qwen_client.py`) so dropped training/competition/Pixel videos are automatically processed into tactical reports while respecting L1 Host Sanctuary.",
        "2. **Extreme Edge TinyLM / Micro-RNN Swarm & Pit Daemon Rotation (`b2198022` — `task.md`):**",
        "   - Complete all 5 open items from `b2198022/task.md`: Extreme Edge device matrix (Polar H10, PineTime, ESP32), TinyML/TFLM 64KB Movesense distillation swarm and Micro-RNN 32KB Keychain compilation swarm in `swarm_summoner.py`, random task rotation in `pit_daemon.py`, and empirical verification run.",
        "3. **Continuous 1B Context Sharding Loop & Screen Lens Multi-Device Matrix (`553ca8bc` & `/continus-lens-practice-automation`):**",
        "   - Execute `continuous_1b_lens_loop.py --test-mode --chunks 5`, verify DPO LoRA dataset ingestion (`continuous_lora_dataset.jsonl`), and capture live 10-node Screen Lens Sovereign telemetry & visual proof.",
        "4. **Podman Sovereign WireGuard, Frontier Swarm Consensus & Gemini Lens Sync (`636d208e`, `553ca8bc`, `5189a2ba`):**",
        "   - Execute `frontier_swarm_consensus.py --verify`, `monitor_wireguard_podman_mesh.py`, and `gemini_lens_integration` sync, and heal any stale paths/wildcards across `/Users/aaron/.gemini/config/sidecars/*/sidecar.json`.",
        "",
    ])

    digest_content = "\n".join(md_lines)
    if not dry_run:
        # If digest already exists and we are running a subsequent hourly pass where 0 newly archived chats were found,
        # preserve previous archived sections by appending a run log or writing full state if first run.
        if TARGET_DIGEST_MD.exists() and len(archived_chats) == 0 and len(cleaned_stale_pins) == 0:
            existing = TARGET_DIGEST_MD.read_text(encoding="utf-8", errors="replace")
            stamp_line = f"\n- **Hourly Check (`{now_iso}`):** Verified `{len(kept_pinned)}` active pinned chat(s); `0` new chats needed archiving.\n"
            if "## 🕒 Hourly Automation Audit Trail" not in existing:
                existing += "\n---\n\n## 🕒 Hourly Automation Audit Trail\n" + stamp_line
            else:
                existing += stamp_line
            TARGET_DIGEST_MD.write_text(existing, encoding="utf-8")
            OBSIDIAN_DIGEST_MD.write_text(existing, encoding="utf-8")
        else:
            TARGET_DIGEST_MD.write_text(digest_content, encoding="utf-8")
            OBSIDIAN_DIGEST_MD.write_text(digest_content, encoding="utf-8")

    summary = {
        "timestamp": now_iso,
        "target_hub_cid": TARGET_HUB_CID,
        "kept_pinned_count": len(kept_pinned),
        "kept_pinned_cids": [x["conversation_id"] for x in kept_pinned],
        "archived_active_count": len(archived_chats),
        "archived_active_cids": [x["conversation_id"] for x in archived_chats],
        "cleaned_stale_pins_count": len(cleaned_stale_pins),
        "digest_path": str(TARGET_DIGEST_MD),
        "obsidian_mirror_path": str(OBSIDIAN_DIGEST_MD),
        "digest_sha256": hashlib.sha256(TARGET_DIGEST_MD.read_bytes()).hexdigest() if TARGET_DIGEST_MD.exists() else "",
    }
    if not dry_run:
        STATE_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Review pinned chats, consolidate into hub chat, and archive completed ones.")
    parser.add_argument("--dry-run", action="store_true", help="Preview decisions without modifying .pbtxt or DB")
    args = parser.parse_args()
    res = run_review_and_archive(dry_run=args.dry_run)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
