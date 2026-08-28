"""
Canonical Port TUI - Architecture Graph Data Models
Version: 1.0.0-CANONICAL
Dataclass models representing the Obsidian Vault Architecture Graph:
- WikilinkRef: Directed references with aliases, section anchors, and source metadata.
- VaultFeature: Architectural capabilities and component features extracted from markdown.
- VaultNode: Comprehensive representation of an architecture document node.
- ArchitectureGraph: In-memory directed dependency graph with traversal, querying, and SCC algorithms.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any


@dataclass
class WikilinkRef:
    """
    Represents an Obsidian Wikilink reference [[target|alias#anchor]].
    """
    target_id: str
    raw_target: str = ""
    alias: Optional[str] = None
    anchor: Optional[str] = None
    source_file: str = ""
    line_number: int = 0

    def __post_init__(self):
        if not self.raw_target:
            self.raw_target = self.target_id

    @property
    def display_text(self) -> str:
        """Returns the human-facing display label for the link."""
        if self.alias:
            return self.alias
        if self.anchor:
            return f"{self.target_id}#{self.anchor}"
        return self.target_id


@dataclass
class VaultFeature:
    """
    Represents an extracted architectural feature or subsystem capability.
    """
    name: str
    description: str = ""
    section: str = ""
    line_number: int = 0


@dataclass
class VaultNode:
    """
    Represents an individual Obsidian Architecture Node in the knowledge graph.
    """
    id: str
    file_path: Path
    title: str
    category: str = "Uncategorized"
    tags: List[str] = field(default_factory=list)
    updated: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    features: List[VaultFeature] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    raw_content: str = ""
    out_links: List[WikilinkRef] = field(default_factory=list)
    in_links: List[str] = field(default_factory=list)
    in_degree: int = 0
    out_degree: int = 0

    def has_tag(self, tag: str) -> bool:
        """Case-insensitive tag membership check."""
        clean_tag = tag.strip().lstrip("#").lower()
        return any(t.lower() == clean_tag for t in self.tags)

    def matches_query(self, query: str) -> bool:
        """
        Case-insensitive search matching against id, title, category, tags, features, and content.
        """
        if not query:
            return True
        q = query.lower().strip()
        if q in self.id.lower():
            return True
        if q in self.title.lower():
            return True
        if q in self.category.lower():
            return True
        if any(q in t.lower() for t in self.tags):
            return True
        if any(q in f.name.lower() or q in f.description.lower() for f in self.features):
            return True
        if any(q in h.lower() for h in self.headings):
            return True
        if q in self.raw_content.lower():
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert VaultNode to serialized dictionary representation."""
        return {
            "id": self.id,
            "file_path": str(self.file_path),
            "title": self.title,
            "category": self.category,
            "tags": list(self.tags),
            "updated": self.updated,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "features_count": len(self.features),
            "out_links": [link.target_id for link in self.out_links],
            "in_links": list(self.in_links),
        }


@dataclass
class ArchitectureGraph:
    """
    In-Memory Directed Architecture Graph indexing Obsidian vault documents.
    """
    nodes: Dict[str, VaultNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (source_id, target_id)
    dangling_links: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)

    def add_node(self, node: VaultNode) -> None:
        """Registers a node in the graph."""
        self.nodes[node.id] = node
        if node.category:
            self.categories.add(node.category)

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Adds a directed edge from source_id to target_id and updates degrees."""
        if (source_id, target_id) not in self.edges:
            self.edges.append((source_id, target_id))
        if source_id in self.nodes:
            self.nodes[source_id].out_degree = len(self.get_out_edges(source_id))
        if target_id in self.nodes:
            self.nodes[target_id].in_degree = len(self.get_in_edges(target_id))

    def get_node(self, node_id: str) -> Optional[VaultNode]:
        """Look up a node by its identifier."""
        return self.nodes.get(node_id)

    def get_out_edges(self, node_id: str) -> List[str]:
        """Returns list of target node IDs pointed to by node_id."""
        return [dst for src, dst in self.edges if src == node_id]

    def get_in_edges(self, node_id: str) -> List[str]:
        """Returns list of source node IDs that point to node_id."""
        return [src for src, dst in self.edges if dst == node_id]

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[VaultNode]:
        """
        Returns neighbor VaultNode objects based on direction ('out', 'in', 'both').
        """
        result_ids: Set[str] = set()
        if direction in ("out", "both"):
            result_ids.update(self.get_out_edges(node_id))
        if direction in ("in", "both"):
            result_ids.update(self.get_in_edges(node_id))
        return [self.nodes[nid] for nid in result_ids if nid in self.nodes]

    def filter_nodes(
        self,
        category: Optional[str] = None,
        query: str = "",
        tags: Optional[List[str]] = None
    ) -> List[VaultNode]:
        """
        Filters graph nodes by optional category, text query, and tags.
        """
        results: List[VaultNode] = []
        clean_cat = category.strip().lower() if category and category != "All" else None

        for node in self.nodes.values():
            if clean_cat and node.category.lower() != clean_cat:
                continue
            if tags and not all(node.has_tag(t) for t in tags):
                continue
            if query and not node.matches_query(query):
                continue
            results.append(node)

        return results

    def search(self, query: str) -> List[VaultNode]:
        """Convenience query search across all nodes."""
        return self.filter_nodes(query=query)

    def get_category_distribution(self) -> Dict[str, int]:
        """Returns map of category name to count of nodes."""
        dist: Dict[str, int] = {}
        for node in self.nodes.values():
            cat = node.category or "Uncategorized"
            dist[cat] = dist.get(cat, 0) + 1
        return dist

    def get_metrics(self) -> Dict[str, Any]:
        """Computes comprehensive graph topology metrics."""
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        avg_in_degree = (total_edges / total_nodes) if total_nodes > 0 else 0.0
        avg_out_degree = avg_in_degree
        density = (total_edges / (total_nodes * (total_nodes - 1))) if total_nodes > 1 else 0.0

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "dangling_links_count": len(self.dangling_links),
            "categories_count": len(self.categories),
            "category_distribution": self.get_category_distribution(),
            "avg_degree": round(avg_in_degree, 2),
            "density": round(density, 4),
            "cycles_count": len(self.find_cycles()),
        }

    def get_subgraph(self, node_ids: Set[str]) -> "ArchitectureGraph":
        """Constructs an induced subgraph containing only the given node IDs."""
        subgraph = ArchitectureGraph()
        for nid in node_ids:
            if nid in self.nodes:
                subgraph.add_node(self.nodes[nid])

        for src, dst in self.edges:
            if src in node_ids and dst in node_ids:
                subgraph.add_edge(src, dst)

        return subgraph

    def find_sccs(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
        """
        Tarjan's strongly connected components algorithm for cycle detection.
        Returns list of SCCs (each is a list of node IDs).
        """
        nodes_to_check = set(self.nodes.keys()) if node_subset is None else (node_subset & set(self.nodes.keys()))
        
        index_counter = 0
        stack: List[str] = []
        indices: Dict[str, int] = {}
        lowlinks: Dict[str, int] = {}
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(v: str) -> None:
            nonlocal index_counter
            indices[v] = index_counter
            lowlinks[v] = index_counter
            index_counter += 1
            stack.append(v)
            on_stack.add(v)

            # Consider successors of v within nodes_to_check
            for w in self.get_out_edges(v):
                if w not in nodes_to_check:
                    continue
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            # If v is a root node, pop the stack and generate an SCC
            if lowlinks[v] == indices[v]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for node_id in sorted(nodes_to_check):
            if node_id not in indices:
                strongconnect(node_id)

        return sccs

    def find_cycles(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
        """
        Finds cyclic components (SCCs with size > 1 or self-loops).
        """
        sccs = self.find_sccs(node_subset=node_subset)
        cycles: List[List[str]] = []
        for scc in sccs:
            if len(scc) > 1:
                cycles.append(sorted(scc))
            elif len(scc) == 1:
                node = scc[0]
                if node in self.get_out_edges(node):
                    cycles.append([node])
        return cycles

    def get_stratified_layers(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
        """
        Computes Sugiyama topological layers. Cycles are isolated and placed in appropriate strata.
        """
        active_nodes = set(self.nodes.keys()) if node_subset is None else (node_subset & set(self.nodes.keys()))
        if not active_nodes:
            return []

        # Compute in-degree within the active subgraph (ignoring back-edges from cycles)
        cycles = self.find_cycles(node_subset=active_nodes)
        cycle_edges: Set[Tuple[str, str]] = set()
        for cyc in cycles:
            cyc_set = set(cyc)
            for u in cyc:
                for v in self.get_out_edges(u):
                    if v in cyc_set:
                        cycle_edges.add((u, v))

        # Kahn-style topological layering with longest path
        in_degree: Dict[str, int] = {nid: 0 for nid in active_nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in active_nodes}

        for src, dst in self.edges:
            if src in active_nodes and dst in active_nodes:
                # If it's a back-edge within a cycle, skip to prevent infinite cycles
                if (src, dst) in cycle_edges and src > dst:
                    continue
                adj[src].append(dst)
                in_degree[dst] += 1

        layers: List[List[str]] = []
        current_layer = [nid for nid in active_nodes if in_degree[nid] == 0]
        if not current_layer:
            # If everything is in a cycle, fallback to picking lowest degree nodes
            min_deg = min(in_degree.values())
            current_layer = [nid for nid, deg in in_degree.items() if deg == min_deg]

        visited: Set[str] = set()

        while current_layer:
            layers.append(sorted(current_layer))
            visited.update(current_layer)
            next_layer: List[str] = []

            for node in current_layer:
                for neighbor in adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] <= 0 and neighbor not in visited and neighbor not in next_layer:
                        next_layer.append(neighbor)

            # Check if there are remaining unvisited nodes when queue empties
            if not next_layer:
                remaining = [nid for nid in active_nodes if nid not in visited]
                if remaining:
                    min_deg = min(in_degree[nid] for nid in remaining)
                    next_layer = [nid for nid in remaining if in_degree[nid] == min_deg]

            current_layer = next_layer

        return layers

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire graph to serializable dictionary."""
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": self.edges,
            "dangling_links": list(self.dangling_links),
            "metrics": self.get_metrics(),
        }
