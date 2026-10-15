#!/usr/bin/env python3
"""
Send Black Belt Sample Order to Subliminator (Hicham Amrani)
============================================================
Dispatches the formal manufacturing order email for the Black Belt Set
(1 Short Sleeve Compression Rashguard + 1 No-Gi Pro Fight Shorts, Size M)
with all pattern deltas vs. Absolute MMA sample parcel EJ350397089AU,
visual renders, JSON directive, and Tech Pack attached.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Add notifications module to path
NOTIFS_DIR = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling")
sys.path.insert(0, str(NOTIFS_DIR))

from notifications.gmail_workspace_client import GmailWorkspaceClient

ROOT_DIR = Path("/Volumes/Lauburu-Monorepo")
DRAFT_PATH = ROOT_DIR / "06_scripts_and_tooling/apparel/email_draft_hicham_amrani_optimal_pattern.md"
RECIPIENT = "hicham@subliminator.com"
SENDER = "aaron.t.maher@gmail.com"
SUBJECT = "Re: Absolute MMA: confirmed production terms and pricing — Black Belt Custom Sample Order (Parcel EJ350397089AU)"

ATTACHMENTS = [
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_set_black_color_sym_showcase.png"),
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_rashguard_color_sym_black.png"),
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_shorts_color_sym_black.png"),
    str(ROOT_DIR / "06_scripts_and_tooling/apparel/subliminator_sample_order_directive.json"),
    str(ROOT_DIR / "07_docs_and_architecture/LAUBURU_COMBAT_APPAREL_TECH_PACK.md"),
]


def extract_body_from_draft(draft_path: Path) -> str:
    """Extracts email body text starting from 'Hi Hicham,'."""
    lines = draft_path.read_text(encoding="utf-8").splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("Hi Hicham"):
            start_idx = i
            break
    return "\n".join(lines[start_idx:]).strip()


def markdown_to_html(md_text: str) -> str:
    """Converts markdown email content to clean, well-formatted email HTML."""
    html_lines = []
    in_list = False

    for line in md_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        if trimmed.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            heading = trimmed[4:]
            html_lines.append(f"<h3 style='color:#141414; border-bottom:1px solid #e0e0e0; padding-bottom:4px; margin-top:20px;'>{heading}</h3>")
        elif trimmed.startswith("* ") or trimmed.startswith("- "):
            if not in_list:
                html_lines.append("<ul style='line-height:1.6; color:#222222;'>")
                in_list = True
            item_text = trimmed[2:]
            # Replace bold markdown
            item_text = item_text.replace("**", "<b>", 1)
            while "**" in item_text:
                item_text = item_text.replace("**", "</b>", 1)
            html_lines.append(f"<li>{item_text}</li>")
        elif trimmed.startswith("1. ") or trimmed.startswith("2. ") or trimmed.startswith("3. ") or trimmed.startswith("4. ") or trimmed.startswith("5. "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            num = trimmed[:3]
            item_text = trimmed[3:]
            item_text = item_text.replace("**", "<b>", 1)
            while "**" in item_text:
                item_text = item_text.replace("**", "</b>", 1)
            html_lines.append(f"<p style='margin:4px 0; line-height:1.5;'><b>{num}</b> {item_text}</p>")
        elif trimmed.startswith("> "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            quote_text = trimmed[2:]
            html_lines.append(f"<blockquote style='border-left:3px solid #C8102E; margin:10px 0; padding-left:12px; color:#555555; font-style:italic;'>{quote_text}</blockquote>")
        elif trimmed == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<hr style='border:0; border-top:1px solid #eaeaea; margin:20px 0;'/>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            p_text = trimmed
            p_text = p_text.replace("**", "<b>", 1)
            while "**" in p_text:
                p_text = p_text.replace("**", "</b>", 1)
            html_lines.append(f"<p style='line-height:1.6; color:#222222; margin:10px 0;'>{p_text}</p>")

    if in_list:
        html_lines.append("</ul>")

    body_html = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #222222; max-width: 680px;">
{body_html}
</body>
</html>"""


def main():
    print(f"=== LAUBURU APPAREL FACTORY DISPATCH ===")
    print(f"Target Recipient: {RECIPIENT}")
    print(f"Sender Identity:  {SENDER}")
    print(f"Subject:          {SUBJECT}")
    print(f"Timestamp:        {datetime.now(timezone.utc).isoformat()}")

    # Verify attachments
    print("\nVerifying attachments:")
    for att in ATTACHMENTS:
        p = Path(att)
        if not p.is_file():
            print(f"[ERROR] Missing attachment: {att}", file=sys.stderr)
            sys.exit(1)
        size_kb = p.stat().st_size / 1024
        sha = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        print(f"  ✓ {p.name} ({size_kb:.1f} KB, sha256:{sha}...)")

    body_text = extract_body_from_draft(DRAFT_PATH)
    body_html = markdown_to_html(body_text)

    print(f"\nExtracted plain text body length: {len(body_text)} chars")
    print(f"Generated HTML body length:       {len(body_html)} chars")

    client = GmailWorkspaceClient()
    print("\nConnecting to Google SMTP (smtp.gmail.com:587) with authentic TLS...")
    result = client.send_email(
        to=RECIPIENT,
        subject=SUBJECT,
        body=body_text,
        html=body_html,
        attachments=ATTACHMENTS,
        sender=SENDER,
        force_transport="smtp_tls"
    )

    print("\nDispatch Result:")
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        print(f"[FAIL] Dispatch failed: {result.get('error')}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[SUCCESS] Sample order email successfully transmitted to {RECIPIENT}!")
    print(f"Message ID: {result.get('message_id')}")
    print(f"Latency:    {result.get('latency_ms')} ms")
    sys.exit(0)


if __name__ == "__main__":
    main()
