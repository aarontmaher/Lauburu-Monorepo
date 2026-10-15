#!/usr/bin/env python3
"""
Send Black Belt Sample Order Direct Follow-Up to Hicham Amrani
=============================================================
Directly threads into Hicham's active Gmail thread:
"Re: Absolute MMA: confirmed production terms and pricing"
Requesting ONLY the Black Belt sample set (1x Rashguard + 1x Shorts, Size M)
with $200 USD sample fee invoice request and factory deltas attached.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

NOTIFS_DIR = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling")
sys.path.insert(0, str(NOTIFS_DIR))

from notifications.gmail_workspace_client import GmailWorkspaceClient

ROOT_DIR = Path("/Volumes/Lauburu-Monorepo")
RECIPIENT = "hicham@subliminator.com"
SENDER = "aaron.t.maher@gmail.com"
SUBJECT = "Re: Absolute MMA: confirmed production terms and pricing"

# Direct Gmail thread reference IDs for Hicham's thread
IN_REPLY_TO = "<CACJevmskbYfeJgbjnibcST4pm6SKCphRn-Cxm7yXwBPGgSdZqA@mail.gmail.com>"
REFERENCES = (
    "<CACJevmtd6j_FMkSGg9KmuwBjGY-g-ZAmWNWx4nTz_KJ2Or92QQ@mail.gmail.com> "
    "<CABcmYQXmf=t49ZN6RUWjgZNkuA8EtpnTj4gJo4JMB7wZaVxmzg@mail.gmail.com> "
    "<CACJevmviBWFwcjxmBZag=0StsdX6mbhPfd1eN1UrrUE6GOXySw@mail.gmail.com> "
    "<CABcmYQUK60mbwiCW6FS2CBKGTUqSGazi6qFas42kDW=Xw7njbA@mail.gmail.com> "
    "<CACJevmuymDrvdnU2d+WZAH9ZwQUg6C0crDVAH_Mn+ozXKHeasg@mail.gmail.com> "
    "<CABcmYQXfSuCbdmS=bzJNbJcBzZzikfH1VeSA7pqqKoQurbt-tw@mail.gmail.com> "
    "<CACJevmskbYfeJgbjnibcST4pm6SKCphRn-Cxm7yXwBPGgSdZqA@mail.gmail.com>"
)

ATTACHMENTS = [
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_set_black_color_sym_showcase.png"),
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_rashguard_color_sym_black.png"),
    str(ROOT_DIR / "assets/products/bjj_apparel/lauburu_shorts_color_sym_black.png"),
    str(ROOT_DIR / "06_scripts_and_tooling/apparel/subliminator_sample_order_directive.json"),
    str(ROOT_DIR / "07_docs_and_architecture/LAUBURU_COMBAT_APPAREL_TECH_PACK.md"),
]

BODY_TEXT = """Hi Hicham,

Hope you had a great weekend.

We are ready to get our physical samples organised and into production right away. 

To keep this initial sample phase simple and fast, we want to produce a BLACK BELT SAMPLE ONLY — exactly 1 Rashguard and 1 pair of Fight Shorts (Size M):
1. 1x Short Sleeve Compression Rashguard (Size M) — Black Belt Edition
2. 1x No-Gi Pro Fight Shorts (Size M) — Black Belt Edition

As confirmed, your Shaoxing pattern room already has our physical baseline garments on hand (Parcel EJ350397089AU, delivered May 30). Rather than a 1:1 copy of the Absolute cut, we want the pattern makers to use that digitized block and apply our custom deltas:

### 1. Short Sleeve Compression Rashguard (Size M)
* Sleeve Length: -2.5 cm to -3.0 cm shorter than sample (hits mid-bicep, zero elbow bunching).
* Bicep Opening: -1.5 cm tighter flat circumference with double-needle compression cuff (sits flush against the arm).
* Rear Hem: +2.0 cm curved drop-tail extension for inversion/guard coverage.
* Hem Gripper: Continuous 25mm inner silicone gel elastic band inside bottom hem.
* Collar: Low-profile 1.2 cm crew collar band with 10mm soft black herringbone interior neck tape.
* Fabric & Stitching: 250 GSM (82% Poly / 18% Spandex), 4-needle 6-thread flatlock in 100% tone-on-tone stealth black thread (zero white contrast thread).
* Artwork: Stealth black (#141414) base, 80px Lauburu emblem centered on sternum, Crimson Red (#C8102E) rank bar accent on underarm flank panels.

### 2. No-Gi Pro Fight Shorts (Size M)
* Inseam Length: Modern 5.5" (14.5 cm) athletic high-cut (-4.5 cm shorter than the 8" sample, sits ~2.5" above the knee for 100% leglock & wrestling mobility).
* Waistband: 50mm quad-stitched elastic waistband + flat recessed internal drawstring + non-abrasive micro-hook-and-loop tab (no bulky/scratchy external velcro flaps).
* Mobility Slits: 3.5" (9.0 cm) deep curved scalloped side slits with bartack reinforcement.
* Gusset: Continuous diamond 4-way stretch crotch panel.
* Fabric: 165 GSM 4-way stretch micro-ripstop polyester with DWR water-repellent finish.
* Artwork: Stealth black (#141414) base, 90px Lauburu emblem on lower right quad, Crimson Red (#C8102E) interior slit lining accent.

### Commercials & Invoice:
As previously confirmed in writing by Corinne (Ticket #50573), the sample charge is $100 per style. 

Please send through the invoice for $200 USD total ($100 for 1 Rashguard + $100 for 1 Fight Shorts, Size M) under your express ~2-week turnaround, or share the direct payment link so we can settle payment today and get Shaoxing cutting.

Attached for your team and the factory:
- lauburu_set_black_color_sym_showcase.png (Visual render of the Black Belt Set)
- lauburu_rashguard_color_sym_black.png (Front render of Black Belt Rashguard)
- lauburu_shorts_color_sym_black.png (Front render of Black Belt Shorts)
- subliminator_sample_order_directive.json (Pattern spec & grading matrix)
- LAUBURU_COMBAT_APPAREL_TECH_PACK.md (Master technical pack)

Looking forward to getting this first Black Belt sample set moving!

Best regards,
Aaron Maher
Founder, Lauburu Grappling
aaron.t.maher@gmail.com
"""

BODY_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #222222; max-width: 680px;">

<p>Hi Hicham,</p>

<p>Hope you had a great weekend.</p>

<p>We are ready to get our physical samples organised and into production right away.</p>

<p>To keep this initial sample phase simple and fast, we want to produce a <b>BLACK BELT SAMPLE ONLY — exactly 1 Rashguard and 1 pair of Fight Shorts (Size M)</b>:</p>
<ol style="line-height: 1.6;">
  <li><b>1x Short Sleeve Compression Rashguard (Size M)</b> — Black Belt Edition</li>
  <li><b>1x No-Gi Pro Fight Shorts (Size M)</b> — Black Belt Edition</li>
</ol>

<p>As confirmed, your Shaoxing pattern room already has our physical baseline garments on hand (Parcel <b>EJ350397089AU</b>, delivered May 30). Rather than a 1:1 copy of the Absolute cut, we want the pattern makers to use that digitized block and apply our custom deltas:</p>

<h3 style="color:#141414; border-bottom:1px solid #e0e0e0; padding-bottom:4px; margin-top:20px;">1. Short Sleeve Compression Rashguard (Size M)</h3>
<ul style="line-height:1.6; color:#222222;">
  <li><b>Sleeve Length:</b> -2.5 cm to -3.0 cm shorter than sample (hits mid-bicep, zero elbow bunching).</li>
  <li><b>Bicep Opening:</b> -1.5 cm tighter flat circumference with double-needle compression cuff (sits flush against arm).</li>
  <li><b>Rear Hem:</b> +2.0 cm curved drop-tail extension for full inversion/guard coverage.</li>
  <li><b>Hem Gripper:</b> Continuous 25mm inner silicone gel elastic band along interior bottom hem.</li>
  <li><b>Collar:</b> Low-profile 1.2 cm crew collar band with 10mm soft black herringbone interior neck tape.</li>
  <li><b>Fabric & Stitching:</b> 250 GSM (82% Poly / 18% Spandex), 4-needle 6-thread flatlock in <b>100% tone-on-tone stealth black thread</b> (zero white contrast thread).</li>
  <li><b>Artwork:</b> Stealth black (<code>#141414</code>) body, 80px Lauburu emblem centered on sternum, Crimson Red (<code>#C8102E</code>) rank bar accent on underarm flank panels.</li>
</ul>

<h3 style="color:#141414; border-bottom:1px solid #e0e0e0; padding-bottom:4px; margin-top:20px;">2. No-Gi Pro Fight Shorts (Size M)</h3>
<ul style="line-height:1.6; color:#222222;">
  <li><b>Inseam Length:</b> Modern 5.5" (14.5 cm) athletic high-cut (-4.5 cm shorter than 8" sample, rests ~2.5" above knee for 100% leglock & wrestling mobility).</li>
  <li><b>Waistband:</b> 50mm quad-stitched elastic waistband + flat recessed internal drawstring + non-abrasive micro-hook-and-loop tab (no bulky/scratchy external velcro flaps).</li>
  <li><b>Mobility Slits:</b> 3.5" (9.0 cm) deep curved scalloped side slits with bartack reinforcement.</li>
  <li><b>Gusset:</b> Continuous diamond 4-way stretch crotch panel.</li>
  <li><b>Fabric:</b> 165 GSM 4-way stretch micro-ripstop polyester with DWR water-repellent finish.</li>
  <li><b>Artwork:</b> Stealth black (<code>#141414</code>) body, 90px Lauburu emblem on lower right quad, Crimson Red (<code>#C8102E</code>) interior slit lining accent.</li>
</ul>

<h3 style="color:#141414; border-bottom:1px solid #e0e0e0; padding-bottom:4px; margin-top:20px;">Commercials & Invoice</h3>
<p>As previously confirmed in writing by Corinne (Ticket #50573), the sample charge is <b>$100 per style</b>.</p>

<p>Please send through the invoice for <b>$200 USD total</b> ($100 for 1 Rashguard + $100 for 1 Fight Shorts, Size M) under your express ~2-week turnaround, or share the direct payment link so we can settle payment today and get Shaoxing cutting.</p>

<p><b>Attached for your team and the factory:</b></p>
<ul style="line-height:1.5; color:#444444; font-size:13px;">
  <li><code>lauburu_set_black_color_sym_showcase.png</code> (Visual render of the Black Belt Set)</li>
  <li><code>lauburu_rashguard_color_sym_black.png</code> (Front render of Black Belt Rashguard)</li>
  <li><code>lauburu_shorts_color_sym_black.png</code> (Front render of Black Belt Shorts)</li>
  <li><code>subliminator_sample_order_directive.json</code> (Pattern spec & grading matrix)</li>
  <li><code>LAUBURU_COMBAT_APPAREL_TECH_PACK.md</code> (Master technical pack)</li>
</ul>

<p>Looking forward to getting this first Black Belt sample set moving!</p>

<p>Best regards,<br/>
<b>Aaron Maher</b><br/>
Founder, Lauburu Grappling<br/>
<a href="mailto:aaron.t.maher@gmail.com">aaron.t.maher@gmail.com</a></p>

</body>
</html>"""


def main():
    print("=== LAUBURU DIRECT SAMPLE ORDER DISPATCH ===")
    print(f"Target Recipient: {RECIPIENT}")
    print(f"Sender Identity:  {SENDER}")
    print(f"Subject:          {SUBJECT}")
    print(f"In-Reply-To:      {IN_REPLY_TO}")
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

    client = GmailWorkspaceClient()
    print("\nConnecting to Google SMTP (smtp.gmail.com:587) with authentic TLS...")
    result = client.send_email(
        to=RECIPIENT,
        subject=SUBJECT,
        body=BODY_TEXT,
        html=BODY_HTML,
        attachments=ATTACHMENTS,
        sender=SENDER,
        force_transport="smtp_tls",
        in_reply_to=IN_REPLY_TO,
        references=REFERENCES
    )

    print("\nDispatch Result:")
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        print(f"[FAIL] Dispatch failed: {result.get('error')}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[SUCCESS] Black Belt Sample Order directly threaded and transmitted to {RECIPIENT}!")
    print(f"Message ID: {result.get('message_id')}")
    print(f"Latency:    {result.get('latency_ms')} ms")
    sys.exit(0)


if __name__ == "__main__":
    main()
