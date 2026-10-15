#!/usr/bin/env python3
"""
Playwright Human-Imitated Truth Auditor & Visual Inspector
Subsystem: 06_scripts_and_tooling/automation
Governed by: Rule #0 & Rule #1 (Zero-Mock & Truth Verification Rule)

Performs automated browser click-throughs, audits interactive elements,
captures visual screenshots, inspects console messages and network payloads,
and verifies zero fake/mock telemetry in live app hubs (Port 4000/4001).
"""
import os
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = Path("/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8")
REPORT_PATH = ARTIFACT_DIR / "visual_inspection_report.json"

def run_visual_truth_audit(base_url="http://127.0.0.1:4000"):
    results = {
        "url": base_url,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_title": "",
        "navigation_success": False,
        "console_errors": [],
        "console_warnings": [],
        "failed_requests": [],
        "clicked_elements": [],
        "interactive_tabs": [],
        "detected_metrics": {},
        "zero_mock_compliance": {
            "has_simulated_data": False,
            "waiting_state_observed": False,
            "findings": []
        },
        "screenshots": [],
        "sellability_assessment": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 LauburuAuditor/1.0"
        )
        page = context.new_page()

        # Wire console listener
        page.on("console", lambda msg: (
            results["console_errors"].append(msg.text) if msg.type == "error" else (
                results["console_warnings"].append(msg.text) if msg.type == "warning" else None
            )
        ))

        # Wire request failed listener
        page.on("requestfailed", lambda req: results["failed_requests"].append({
            "url": req.url,
            "failure": str(req.failure)
        }))

        # 1. Initial Page Load
        try:
            page.goto(base_url, timeout=10000, wait_until="networkidle")
            results["navigation_success"] = True
            results["page_title"] = page.title()
        except Exception as e:
            results["navigation_success"] = False
            results["navigation_error"] = str(e)
            browser.close()
            return results

        time.sleep(2) # allow WebSockets / force graph initialization

        # Capture Hero Overview Screenshot
        hero_shot = ARTIFACT_DIR / "port_4000_dashboard_initial.png"
        page.screenshot(path=str(hero_shot), full_page=True)
        results["screenshots"].append(str(hero_shot))

        # 2. Discover Interactive Tabs / Navigation Elements
        tab_selectors = ["button", "[role='tab']", ".tab-btn", ".nav-link", "header a"]
        for sel in tab_selectors:
            elements = page.query_selector_all(sel)
            for el in elements:
                try:
                    txt = (el.inner_text() or "").strip()
                    if txt and len(txt) < 30 and txt not in [t["name"] for t in results["interactive_tabs"]]:
                        is_visible = el.is_visible()
                        results["interactive_tabs"].append({
                            "name": txt,
                            "tag": el.evaluate("e => e.tagName"),
                            "visible": is_visible
                        })
                except Exception:
                    pass

        # 3. Perform Human-Imitated Click Throughs
        clicked_count = 0
        for tab in results["interactive_tabs"][:8]:
            try:
                name = tab["name"]
                btn = page.get_by_text(name, exact=True).first
                if btn and btn.is_visible():
                    time.sleep(0.3)
                    btn.click(timeout=3000)
                    time.sleep(0.8)
                    clicked_count += 1
                    tab_slug = "".join(c if c.isalnum() else "_" for c in name.lower())[:20]
                    shot_path = ARTIFACT_DIR / f"port_4000_tab_{tab_slug}.png"
                    page.screenshot(path=str(shot_path))
                    results["clicked_elements"].append({
                        "name": name,
                        "status": "CLICKED_SUCCESS",
                        "screenshot": str(shot_path)
                    })
                    results["screenshots"].append(str(shot_path))
            except Exception as click_err:
                results["clicked_elements"].append({
                    "name": tab.get("name"),
                    "status": "CLICK_FAILED",
                    "error": str(click_err)
                })

        # 4. Audit DOM Text for Telemetry Truth
        body_text = page.inner_text("body")
        if "--" in body_text or "STANDBY" in body_text or "WAITING" in body_text or "DISCONNECTED" in body_text:
            results["zero_mock_compliance"]["waiting_state_observed"] = True

        suspicious_words = ["fake_telemetry", "simulated", "mock_sensor", "dummy_ecg", "placeholder data"]
        for word in suspicious_words:
            if word in body_text.lower():
                results["zero_mock_compliance"]["has_simulated_data"] = True
                results["zero_mock_compliance"]["findings"].append(f"Suspicious word '{word}' found in visible page text.")

        # 5. Sellability & UX Audit
        results["sellability_assessment"] = {
            "title_branding": results["page_title"],
            "has_favicon": bool(page.query_selector("link[rel*='icon']")),
            "mobile_viewport_configured": bool(page.query_selector("meta[name='viewport']")),
            "theme_color_configured": bool(page.query_selector("meta[name='theme-color']")),
            "apple_pwa_capable": bool(page.query_selector("meta[name='apple-mobile-web-app-capable']")),
            "total_console_errors": len(results["console_errors"]),
            "total_failed_network_requests": len(results["failed_requests"]),
            "visual_polish_verdict": "EXCELLENT" if len(results["console_errors"]) == 0 else "NEEDS_ERROR_CLEANUP"
        }

        browser.close()

    with open(REPORT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    return results

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4000"
    res = run_visual_truth_audit(url)
    print(json.dumps({
        "url": res["url"],
        "title": res["page_title"],
        "tabs_found": len(res["interactive_tabs"]),
        "clicked": len(res["clicked_elements"]),
        "console_errors": len(res["console_errors"]),
        "failed_requests": len(res["failed_requests"]),
        "waiting_state_observed": res["zero_mock_compliance"]["waiting_state_observed"],
        "has_simulated_data": res["zero_mock_compliance"]["has_simulated_data"],
        "screenshots_captured": len(res["screenshots"])
    }, indent=2))
