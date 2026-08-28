#!/usr/bin/env python3
"""
OPML Grappling MindMap Parser & Tree Generator
==============================================
Parses .opml mindmaps from data/opml_maps/ into structured positional trees,
techniques, biomechanical notes, and transition edges for the AI Game Arena
and 3D Spatial Kinematics Suite.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OPML_DIR = WORKSPACE_ROOT / "data" / "opml_maps"


class OPMLGrapplingParser:
    def __init__(self, opml_path: Path = None):
        self.locked_path = OPML_DIR / "canonical_final_copy_mindmap.opml.locked"
        self.final_copy_path = OPML_DIR / "final_copy_grappling_mindmap.opml"
        self.opml_path = opml_path or (self.locked_path if self.locked_path.exists() else self.final_copy_path)

    def parse_mindmap(self) -> Dict[str, Any]:
        if not self.opml_path.exists():
            # Fallback to final copy or any OPML in directory
            if self.final_copy_path.exists():
                self.opml_path = self.final_copy_path
            else:
                opml_files = list(OPML_DIR.glob("*.opml*"))
                if opml_files:
                    self.opml_path = opml_files[0]
                else:
                    return {"error": "No OPML files found in data/opml_maps/"}

        try:
            tree = ET.parse(self.opml_path)
            root = tree.getroot()
            body = root.find("body")
            if body is None:
                return {"error": "Invalid OPML: missing body tag"}

            title_elem = root.find("head/title")
            map_title = title_elem.text if title_elem is not None else "Grappling MindMap"

            nodes = []
            techniques = []
            positions = set()

            for top_outline in body.findall("outline"):
                self._extract_outlines_recursive(top_outline, None, nodes, techniques, positions)

            return {
                "title": map_title,
                "file_path": str(self.opml_path),
                "total_nodes": len(nodes),
                "total_techniques": len(techniques),
                "unique_positions": list(positions),
                "tree": nodes,
                "flat_techniques": techniques
            }
        except Exception as e:
            return {"error": f"Failed to parse OPML: {str(e)}"}

    def _extract_outlines_recursive(self, elem, parent_id: str, nodes: List[Dict[str, Any]], techniques: List[Dict[str, Any]], positions: set):
        text = elem.get("text", "Unknown")
        note = elem.get("_note", "")
        url = elem.get("url", "")
        node_id = text.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").replace("&", "and")

        children = elem.findall("outline")
        is_leaf = len(children) == 0

        node_data = {
            "id": node_id,
            "title": text,
            "note": note,
            "url": url,
            "parent_id": parent_id,
            "is_technique": is_leaf,
            "children": []
        }

        if is_leaf:
            # Technique leaf
            tech_record = {
                "id": node_id,
                "name": text,
                "position": parent_id or "General",
                "note": note,
                "url": url,
                "difficulty": round(random_or_deterministic_difficulty(text), 1)
            }
            techniques.append(tech_record)
        else:
            positions.add(text)

        for child in children:
            self._extract_outlines_recursive(child, node_id, node_data["children"], techniques, positions)

        nodes.append(node_data)


def random_or_deterministic_difficulty(name: str) -> float:
    # Deterministic hash score between 7.0 and 9.8
    h = sum(ord(c) for c in name)
    return 7.0 + (h % 28) / 10.0


if __name__ == "__main__":
    parser = OPMLGrapplingParser()
    res = parser.parse_mindmap()
    print(f"Parsed OPML: {res.get('title')}")
    print(f"Total Nodes: {res.get('total_nodes')}, Techniques: {res.get('total_techniques')}")
    print(f"Unique Positions: {len(res.get('unique_positions', []))}")
