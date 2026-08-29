"""
OPML MindMap Parser & Spatial Projector.
========================================
Subsystem: 01_apps/user_facing_and_scaling/spatial_grappling_3d/kinematics/opml_tree.py
"""

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from ..core.models import GrapplingNode, BiomechanicalTransition

def parse_opml_tree(opml_path: Path) -> Tuple[List[GrapplingNode], List[BiomechanicalTransition], Dict[str, int]]:
    """
    Parses hierarchical OPML martial arts tree and projects nodes onto
    a cylindrical 10m x 10m tatami 3D coordinate system.
    """
    if not opml_path.exists():
        raise FileNotFoundError(f"OPML MindMap not found at: {opml_path}")

    tree = ET.parse(opml_path)
    root = tree.getroot()
    body = root.find("body")
    if body is None:
        raise ValueError("Malformed OPML: <body> element missing")

    nodes: List[GrapplingNode] = []
    transitions: List[BiomechanicalTransition] = []
    categories_count: Dict[str, int] = {}

    def _recurse(elem: ET.Element, parent_id: str, depth: int):
        text = elem.get("text", "Unknown Node").strip()
        node_id = f"node_{len(nodes)}_{text[:20].lower().replace(' ', '_').replace('/', '_')}"
        
        category = "General"
        z_height = 0.50
        if depth == 1:
            category = text
            if "Wrestling" in text or "Takedown" in text:
                z_height = 1.65
            elif "Guard" in text:
                z_height = 0.40
            elif "Dominant" in text or "Mount" in text:
                z_height = 0.65
            elif "Scramble" in text or "Turtle" in text:
                z_height = 0.85
        elif parent_id != "root":
            category = parent_id.split("_")[1] if "_" in parent_id else "Subsystem"

        categories_count[category] = categories_count.get(category, 0) + 1

        # Calculate cylindrical projection around 10m x 10m Tatami
        theta = (len(nodes) * 0.137) * math.pi * 2.0
        radius = min(1.0 + (depth * 0.45), 4.8)  # Keep within 10m mat (radius <= 5.0m)
        x = round(math.cos(theta) * radius, 3)
        y = round(math.sin(theta) * radius, 3)
        z = round(z_height + (math.sin(depth) * 0.15), 3)

        node = GrapplingNode(
            id=node_id,
            text=text,
            category=category,
            depth=depth,
            parent_id=parent_id,
            x=x,
            y=y,
            z=z,
            has_children=len(elem.findall("outline")) > 0
        )
        nodes.append(node)

        if parent_id != "root":
            transitions.append(BiomechanicalTransition(
                from_node=parent_id,
                to_node=node_id,
                relationship="hierarchical_transition"
            ))

        for child in elem.findall("outline"):
            _recurse(child, parent_id=node_id, depth=depth + 1)

    top_outline = body.find("outline")
    if top_outline is not None:
        _recurse(top_outline, parent_id="root", depth=0)
    else:
        for out in body.findall("outline"):
            _recurse(out, parent_id="root", depth=0)

    return nodes, transitions, categories_count
