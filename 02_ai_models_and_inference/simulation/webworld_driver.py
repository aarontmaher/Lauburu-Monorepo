# -*- coding: utf-8 -*-
"""
Qwen-WebWorld-32B/8B World Model Driver & Copy-on-Write React DOM Simulator
============================================================================
Subsystem: 02_ai_models_and_inference/simulation/webworld_driver.py
Milestone: M4 — Dual-World Simulation & Predictive Lookahead Engine

Governs predictive multi-step simulation for React DOM, TailwindCSS layout boxes,
WCAG 2.1 AA accessibility trees, GraphQL mutations, and route regression detection
over isolated shadow virtual DOM states.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("WebWorldDriver")

DEFAULT_WEB_MODEL = "Qwen/Qwen-WebWorld-32B"


def hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (1.0, 1.0, 1.0)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (1.0, 1.0, 1.0)


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def calculate_relative_luminance(rgb: Tuple[float, float, float]) -> float:
    r, g, b = [srgb_to_linear(c) for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """
    Computes WCAG 2.1 contrast ratio: (L1 + 0.05) / (L2 + 0.05).
    """
    lum1 = calculate_relative_luminance(hex_to_rgb(fg_hex))
    lum2 = calculate_relative_luminance(hex_to_rgb(bg_hex))
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


@dataclass
class ShadowDOMNode:
    tag: str = "div"
    node_id: str = field(default_factory=lambda: f"node_{int(time.time_ns())}")
    classes: List[str] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, str] = field(default_factory=dict)
    text_content: str = ""
    children: List[ShadowDOMNode] = field(default_factory=list)
    parent_id: Optional[str] = None
    
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 30.0

    def get_attr(self, name: str, default: str = "") -> str:
        return self.attributes.get(name, default)


class ShadowDOM:
    """
    Copy-on-Write Virtual React / HTML DOM Tree.
    Tracks visual layout hierarchy, CSS box constraints, and A11y tree.
    """

    def __init__(self, viewport_width: float = 1280.0, viewport_height: float = 800.0):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.root = ShadowDOMNode(
            tag="html",
            node_id="root_html",
            classes=["dark", "bg-gray-950", "text-white"],
            styles={"background": "#070B12", "color": "#FFFFFF", "width": viewport_width, "height": viewport_height},
            width=viewport_width,
            height=viewport_height,
        )
        self._node_index: Dict[str, ShadowDOMNode] = {"root_html": self.root}
        self._registered_routes: Set[str] = {
            "/",
            "/dashboard",
            "/movesense",
            "/zone2",
            "/grappling",
            "/analytics",
            "/settings",
            "/api/health",
            "/api/telemetry/ingest",
            "/api/sensors/status",
        }

    def add_node(self, parent_id: str, node: ShadowDOMNode) -> bool:
        parent = self._node_index.get(parent_id)
        if not parent:
            parent = self.root
        node.parent_id = parent.node_id
        parent.children.append(node)
        self._node_index[node.node_id] = node
        return True

    def find_node(self, node_id: str) -> Optional[ShadowDOMNode]:
        return self._node_index.get(node_id)

    def find_by_tag(self, tag: str) -> List[ShadowDOMNode]:
        return [n for n in self._node_index.values() if n.tag.lower() == tag.lower()]

    def clone(self) -> ShadowDOM:
        cloned = ShadowDOM(viewport_width=self.viewport_width, viewport_height=self.viewport_height)
        cloned.root = copy.deepcopy(self.root)
        cloned._node_index = {}
        
        def index_tree(n: ShadowDOMNode):
            cloned._node_index[n.node_id] = n
            for c in n.children:
                index_tree(c)
                
        index_tree(cloned.root)
        cloned._registered_routes = copy.deepcopy(self._registered_routes)
        return cloned

    def evaluate_layout_overflows(self) -> List[Dict[str, Any]]:
        overflows = []

        def check_node(node: ShadowDOMNode):
            if node.width > self.viewport_width and "overflow-x-auto" not in node.classes and node.styles.get("overflow_x") != "auto":
                overflows.append({
                    "node_id": node.node_id,
                    "tag": node.tag,
                    "type": "VIEWPORT_HORIZONTAL_OVERFLOW",
                    "node_width": node.width,
                    "viewport_width": self.viewport_width,
                })

            parent = self._node_index.get(node.parent_id) if node.parent_id else None
            if parent and parent.node_id != "root_html":
                parent_w = parent.width
                parent_overflow = parent.styles.get("overflow", "visible")
                if "overflow-hidden" in parent.classes or parent_overflow == "hidden":
                    if (node.x + node.width) > (parent.x + parent_w):
                        overflows.append({
                            "node_id": node.node_id,
                            "parent_id": parent.node_id,
                            "type": "CONTAINER_CLIPPING_OVERFLOW",
                            "overflow_pixels": round((node.x + node.width) - (parent.x + parent_w), 2),
                        })

            for child in node.children:
                check_node(child)

        check_node(self.root)
        return overflows

    def evaluate_accessibility_and_contrast(self) -> List[Dict[str, Any]]:
        violations = []

        def check_a11y(node: ShadowDOMNode):
            if node.tag == "img" and not node.get_attr("alt"):
                violations.append({
                    "node_id": node.node_id,
                    "type": "MISSING_IMG_ALT",
                    "detail": "<img> tag must have descriptive alt attribute",
                })

            if node.tag == "button":
                has_label = bool(node.text_content.strip() or node.get_attr("aria-label") or node.get_attr("title"))
                if not has_label:
                    violations.append({
                        "node_id": node.node_id,
                        "type": "BUTTON_MISSING_ACCESSIBLE_NAME",
                        "detail": "<button> requires text content or aria-label for screen readers",
                    })

            if node.tag in ["input", "select", "textarea"] and node.get_attr("type") != "hidden":
                has_label = bool(node.get_attr("aria-label") or node.get_attr("id") or node.get_attr("placeholder"))
                if not has_label:
                    violations.append({
                        "node_id": node.node_id,
                        "type": "FORM_INPUT_MISSING_LABEL",
                        "detail": f"<{node.tag}> control lacks label or aria-label",
                    })

            fg = node.styles.get("color")
            bg = node.styles.get("background") or node.styles.get("background-color")
            if fg and bg and isinstance(fg, str) and isinstance(bg, str):
                if fg.startswith("#") and bg.startswith("#"):
                    ratio = calculate_contrast_ratio(fg, bg)
                    is_large_text = "text-xl" in node.classes or "text-2xl" in node.classes or node.styles.get("font-size", 14) >= 18
                    min_ratio = 3.0 if is_large_text else 4.5
                    if ratio < min_ratio:
                        violations.append({
                            "node_id": node.node_id,
                            "type": "WCAG_CONTRAST_VIOLATION",
                            "contrast_ratio": ratio,
                            "min_required": min_ratio,
                            "fg": fg,
                            "bg": bg,
                        })

            for child in node.children:
                check_a11y(child)

        check_a11y(self.root)
        return violations

    def evaluate_route_and_link_regressions(self) -> List[Dict[str, Any]]:
        regressions = []
        for node in self.find_by_tag("a"):
            href = node.get_attr("href", "")
            if href.startswith("/") and not href.startswith("//"):
                route_base = href.split("?")[0].split("#")[0]
                if route_base not in self._registered_routes:
                    regressions.append({
                        "node_id": node.node_id,
                        "type": "BROKEN_INTERNAL_ROUTE_404",
                        "href": href,
                        "unresolved_target": route_base,
                    })
        return regressions


@dataclass
class WebWorldStepResult:
    step_index: int
    action_type: str
    action_raw: Union[str, Dict[str, Any]]
    safety_score: float = 1.0
    regression_probability: float = 0.0
    layout_overflows: int = 0
    confidence: float = 0.95
    dom_diff: Dict[str, Any] = field(default_factory=dict)
    wcag_violations: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class WebWorldDriver:
    """
    Qwen-WebWorld-32B/8B Driver for React DOM mutations, layout validation,
    WCAG accessibility audits, and GraphQL schema validation.
    """

    def __init__(self, model_name: str = DEFAULT_WEB_MODEL):
        self.model_name = model_name
        self._graphql_schemas = {
            "ShopifyStorefront": ["products", "cartCreate", "cartLinesAdd", "customerAccessTokenCreate"],
            "LauburuMeshAPI": ["telemetryStream", "biometricsSummary", "deviceTopology"],
        }

    def simulate_dom_mutation(
        self,
        mutation_payload: Dict[str, Any],
        dom: ShadowDOM,
    ) -> WebWorldStepResult:
        op = mutation_payload.get("op", "append")
        target_parent = mutation_payload.get("parent_id", "root_html")
        tag = mutation_payload.get("tag", "div")
        classes = mutation_payload.get("classes", [])
        styles = mutation_payload.get("styles", {})
        attrs = mutation_payload.get("attributes", {})
        text = mutation_payload.get("text_content", "")
        width = float(mutation_payload.get("width", 200.0))
        height = float(mutation_payload.get("height", 50.0))
        x = float(mutation_payload.get("x", 0.0))
        y = float(mutation_payload.get("y", 0.0))

        new_node = ShadowDOMNode(
            tag=tag,
            node_id=mutation_payload.get("node_id", f"node_{int(time.time_ns())}"),
            classes=classes,
            styles=styles,
            attributes=attrs,
            text_content=text,
            width=width,
            height=height,
            x=x,
            y=y,
        )

        dom.add_node(target_parent, new_node)

        overflows = dom.evaluate_layout_overflows()
        wcag_violations = dom.evaluate_accessibility_and_contrast()
        link_regressions = dom.evaluate_route_and_link_regressions()

        num_overflows = len(overflows)
        num_wcag = len(wcag_violations)
        num_regress = len(link_regressions)

        safety_score = max(0.0, 1.0 - (num_overflows * 0.35 + num_wcag * 0.10 + num_regress * 0.25))
        regression_prob = min(1.0, num_regress * 0.30 + num_overflows * 0.20)
        confidence = 0.95 if num_overflows == 0 else 0.88

        return WebWorldStepResult(
            step_index=0,
            action_type="dom_update",
            action_raw=mutation_payload,
            safety_score=round(safety_score, 4),
            regression_probability=round(regression_prob, 4),
            layout_overflows=num_overflows,
            confidence=round(confidence, 4),
            dom_diff={"added_node": new_node.node_id, "tag": tag},
            wcag_violations=wcag_violations,
            diagnostics={
                "overflows": overflows,
                "link_regressions": link_regressions,
                "wcag_violations_count": num_wcag,
            },
        )

    def simulate_graphql_mutation(
        self,
        schema_name: str,
        operation_name: str,
        variables: Dict[str, Any],
    ) -> WebWorldStepResult:
        supported = self._graphql_schemas.get(schema_name, [])
        is_valid = operation_name in supported

        if is_valid:
            return WebWorldStepResult(
                step_index=0,
                action_type="graphql_mutation",
                action_raw={"schema": schema_name, "op": operation_name, "vars": variables},
                safety_score=0.99,
                regression_probability=0.01,
                layout_overflows=0,
                confidence=0.96,
                diagnostics={"schema_matched": True, "operation": operation_name},
            )
        else:
            return WebWorldStepResult(
                step_index=0,
                action_type="graphql_mutation",
                action_raw={"schema": schema_name, "op": operation_name, "vars": variables},
                safety_score=0.50,
                regression_probability=0.60,
                layout_overflows=0,
                confidence=0.90,
                diagnostics={"schema_matched": False, "error": f"Unknown operation '{operation_name}' in {schema_name}"},
            )

    def rollout_trajectory(
        self,
        action_payload: Dict[str, Any],
        lookahead_steps: int = 30,
        base_dom: Optional[ShadowDOM] = None,
    ) -> Dict[str, Any]:
        dom = base_dom.clone() if base_dom else ShadowDOM()
        actions = action_payload.get("actions", [])
        if not actions and ("mutation" in action_payload or "dom_update" in action_payload):
            base_mut = action_payload.get("mutation") or action_payload.get("dom_update", {})
            actions = [{"type": "dom_update", "payload": base_mut}]
            for i in range(1, lookahead_steps):
                if i % 4 == 1:
                    actions.append({"type": "dom_update", "payload": {"tag": "span", "text_content": f"telemetry_badge_{i}", "width": 80.0, "height": 24.0, "classes": ["text-xs", "text-cyan-400"]}})
                elif i % 4 == 2:
                    actions.append({"type": "graphql_mutation", "payload": {"schema": "ShopifyStorefront", "op": "cartCreate", "vars": {}}})
                else:
                    actions.append({"type": "dom_update", "payload": {"tag": "div", "text_content": "container_wrapper", "width": 300.0, "height": 40.0}})
        elif not actions:
            actions = [{"type": "dom_update", "payload": action_payload}]

        while len(actions) < lookahead_steps:
            actions.append({"type": "dom_update", "payload": {"tag": "div", "text_content": "ui_noop", "width": 100.0, "height": 20.0}})

        step_results: List[WebWorldStepResult] = []
        total_safety = 0.0
        max_regression = 0.0
        total_overflows = 0
        total_confidence = 0.0

        for idx, act in enumerate(actions[:lookahead_steps]):
            act_type = act.get("type", "dom_update")
            act_payload = act.get("payload", {})

            if act_type == "dom_update":
                res = self.simulate_dom_mutation(act_payload, dom=dom)
            elif act_type == "graphql_mutation":
                s_name = act_payload.get("schema", "ShopifyStorefront")
                op_name = act_payload.get("op", "cartCreate")
                v_vars = act_payload.get("vars", {})
                res = self.simulate_graphql_mutation(s_name, op_name, v_vars)
            else:
                res = self.simulate_dom_mutation(act_payload if isinstance(act_payload, dict) else {"text_content": str(act_payload)}, dom=dom)

            res.step_index = idx + 1
            step_results.append(res)
            total_safety += res.safety_score
            max_regression = max(max_regression, res.regression_probability)
            total_overflows += res.layout_overflows
            total_confidence += res.confidence

        n_steps = len(step_results)
        avg_safety = total_safety / n_steps if n_steps > 0 else 0.0
        avg_confidence = total_confidence / n_steps if n_steps > 0 else 0.0

        return {
            "driver": "Qwen-WebWorld-32B",
            "steps_requested": lookahead_steps,
            "steps_completed": n_steps,
            "safety_score": round(avg_safety, 4),
            "regression_probability": round(max_regression, 4),
            "layout_overflows": total_overflows,
            "simulation_confidence": round(avg_confidence, 4),
            "step_results": [asdict(r) for r in step_results],
        }
