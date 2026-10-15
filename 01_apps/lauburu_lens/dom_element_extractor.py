#!/usr/bin/env python3
"""
================================================================================
Lauburu Lens: Authentic DOM Element & Hierarchy Extractor (2026)
================================================================================
Subsystem: 01_apps/lauburu_lens/dom_element_extractor.py
Lauburu Mesh Ecosystem — Multimodal Screen Perception & Computer Use

Extracts live interactive DOM elements and bounding boxes via Chrome DevTools
Protocol (CDP) Runtime.evaluate from monorepo web endpoints:
  - Voilà Master Console (:8890)
  - Self-Healing Hub REST API / UI (:18802)
  - Port 4000 Biometrics Console (:4000)
================================================================================
"""

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
try:
    from .chrome_debugging_bridge import ChromeDebuggingBridge
except ImportError:
    from chrome_debugging_bridge import ChromeDebuggingBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Lens-DOM-Extractor] %(message)s")
log = logging.getLogger("DomElementExtractor")


@dataclass
class BoundingRect:
    left: float
    top: float
    width: float
    height: float
    cx: float
    cy: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class ElementStyles:
    color: str = "rgb(255, 255, 255)"
    backgroundColor: str = "transparent"
    fontSize: str = "16px"
    fontWeight: str = "400"
    display: str = "block"
    visibility: str = "visible"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class DomElement:
    tag: str
    id: str
    text: str
    rect: BoundingRect
    styles: ElementStyles
    attributes: Dict[str, str] = field(default_factory=dict)
    selector: str = ""
    is_visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "id": self.id,
            "text": self.text,
            "rect": self.rect.to_dict(),
            "styles": self.styles.to_dict(),
            "attributes": self.attributes,
            "selector": self.selector,
            "is_visible": self.is_visible
        }


DOM_EXTRACTION_SCRIPT = """
(() => {
    const selectors = [
        "button", "a", "input", "select", "textarea", "canvas", "pre",
        "[role='button']", "[role='tab']", "[role='link']", "[role='checkbox']",
        ".tab-btn", ".btn", ".p-TabBar-tab", ".lm-TabBar-tab", ".widget-tab",
        "li", "div[data-tab]", "[data-tab]", "[data-action]", "[onclick]",
        "span.badge", ".p-TabBar-tab", ".jupyter-widgets"
    ];

    const elements = Array.from(document.querySelectorAll(selectors.join(", ")));
    const results = [];
    const seenRects = new Set();

    for (const el of elements) {
        const r = el.getBoundingClientRect();
        if (!r || r.width <= 0 || r.height <= 0) continue;

        const left = Math.round(r.left);
        const top = Math.round(r.top);
        const width = Math.round(r.width);
        const height = Math.round(r.height);
        const cx = Math.round(r.left + r.width / 2);
        const cy = Math.round(r.top + r.height / 2);

        const key = el.tagName + "_" + left + "_" + top + "_" + width + "_" + height;
        if (seenRects.has(key)) continue;
        seenRects.add(key);

        const style = window.getComputedStyle(el);
        const isVisible = style.display !== "none" &&
                          style.visibility !== "hidden" &&
                          parseFloat(style.opacity || "1") > 0.05;

        const attrs = {};
        for (const attr of el.attributes) {
            if (["id", "class", "role", "data-tab", "data-action", "href", "type", "name", "aria-label"].includes(attr.name)) {
                attrs[attr.name] = attr.value;
            }
        }

        const text = (el.innerText || el.value || el.getAttribute("aria-label") || "").trim().slice(0, 80);

        results.push({
            tag: el.tagName,
            id: el.id || "",
            text: text,
            rect: {
                left: left,
                top: top,
                width: width,
                height: height,
                cx: cx,
                cy: cy
            },
            styles: {
                color: style.color || "rgb(255, 255, 255)",
                backgroundColor: style.backgroundColor || "transparent",
                fontSize: style.fontSize || "16px",
                fontWeight: style.fontWeight || "400",
                display: style.display || "block",
                visibility: style.visibility || "visible"
            },
            attributes: attrs,
            is_visible: isVisible
        });
    }

    return results;
})()
"""


class DomElementExtractor:
    """
    Extracts authentic DOM hierarchy and bounding box coordinates from running endpoints.
    """

    def __init__(self, bridge: Optional[ChromeDebuggingBridge] = None):
        self.bridge = bridge

    def wait_for_settled_dom(self, bridge: ChromeDebuggingBridge, max_seconds: float = 12.0) -> bool:
        """Wait for dynamic loaders (e.g. Voilà kernel execution) to settle."""
        start = time.time()
        while time.time() - start < max_seconds:
            is_loading = bridge.evaluate("""
                (() => {
                    const loading = document.getElementById("loading");
                    if (loading && loading.style.display !== "none") return true;
                    if (document.body && document.body.innerText.includes("Executing 1 of")) return true;
                    return false;
                })()
            """)
            if not is_loading:
                return True
            time.sleep(0.5)
        return False

    def extract_interactive_elements(
        self,
        bridge: Optional[ChromeDebuggingBridge] = None,
        url: Optional[str] = None,
        wait_seconds: float = 1.0
    ) -> List[DomElement]:
        """
        Extract all interactive elements from the current or specified URL.
        """
        active_bridge = bridge or self.bridge
        if not active_bridge:
            raise ValueError("A connected ChromeDebuggingBridge must be provided")

        if url:
            active_bridge.navigate(url, wait_seconds=wait_seconds)
            self.wait_for_settled_dom(active_bridge)

        raw_elements = active_bridge.evaluate(DOM_EXTRACTION_SCRIPT)
        if not raw_elements or not isinstance(raw_elements, list):
            log.warning("No interactive elements returned by DOM extraction script")
            return []

        dom_elements = []
        for item in raw_elements:
            r = item["rect"]
            st = item["styles"]
            dom_el = DomElement(
                tag=item["tag"],
                id=item.get("id", ""),
                text=item.get("text", ""),
                rect=BoundingRect(
                    left=float(r["left"]),
                    top=float(r["top"]),
                    width=float(r["width"]),
                    height=float(r["height"]),
                    cx=float(r["cx"]),
                    cy=float(r["cy"])
                ),
                styles=ElementStyles(
                    color=st.get("color", "rgb(255, 255, 255)"),
                    backgroundColor=st.get("backgroundColor", "transparent"),
                    fontSize=st.get("fontSize", "16px"),
                    fontWeight=st.get("fontWeight", "400"),
                    display=st.get("display", "block"),
                    visibility=st.get("visibility", "visible")
                ),
                attributes=item.get("attributes", {}),
                is_visible=item.get("is_visible", True)
            )
            dom_elements.append(dom_el)

        log.info(f"Extracted {len(dom_elements)} interactive DOM elements from {url or 'active page'}")
        return dom_elements

    def extract_from_endpoint(self, url: str) -> List[DomElement]:
        """Helper to extract elements from a specific endpoint using a temporary session."""
        should_close = False
        if not self.bridge:
            self.bridge = ChromeDebuggingBridge()
            self.bridge.connect()
            should_close = True

        try:
            return self.extract_interactive_elements(bridge=self.bridge, url=url)
        finally:
            if should_close:
                self.bridge.close()
                self.bridge = None


def main():
    bridge = ChromeDebuggingBridge()
    bridge.connect()

    extractor = DomElementExtractor(bridge)
    endpoints = [
        "http://127.0.0.1:4000",
        "http://127.0.0.1:8890",
        "http://127.0.0.1:18802/health"
    ]

    for ep in endpoints:
        print(f"=== Harvesting {ep} ===")
        elements = extractor.extract_interactive_elements(bridge, url=ep)
        print(f"Found {len(elements)} elements")
        for el in elements[:3]:
            print(f"  [{el.tag}] text={el.text!r} rect={el.rect}")

    bridge.close()

if __name__ == "__main__":
    main()
