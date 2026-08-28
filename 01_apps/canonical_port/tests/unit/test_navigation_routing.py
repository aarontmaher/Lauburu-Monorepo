"""
Unit Tests: Unified Navigation & Routing System (Feature 2 & M3/M4 Ground-Up Hierarchy)
Verifies route transitions, sidebar state, deep linking, ground-up stability ordering, and layout routing contracts.
Derived from ORIGINAL_REQUEST.md §Acceptance Criteria and PROJECT.md §1 & §M3-M4.
"""

import pytest
from typing import Dict, List, Optional

class NavigationStateMachine:
    """
    Reference implementation of the navigation state machine matching TypeScript contract.
    Organized strictly in ground-up stability hierarchy (Layers 0 through 6 + Optimization Shells).
    """
    VALID_ROUTES = [
        # 0. Bare-Metal Networking (Primary)
        "network-metrics",
        # 1. Hardware & Nodes
        "hardware-nodes",
        # 2. Medical Biometrics & DSP
        "biometrics-dsp",
        # 3. Local AI Inference
        "ai-inference",
        # 4. Local AI Training & Games
        "training-lora",
        "training-games",
        "training-metrics",
        "training-traces",
        # 5. Master AGI Governance & Leaderboard
        "governance",
        "leaderboard",
        # 6. Tooling & Commerce
        "tooling-commerce",
        # Optimization Shells
        "optimization-hardware",
        "optimization-software",
        "optimization-internet",
        "optimization-storage"
    ]
    
    ROUTE_METADATA = {
        "network-metrics": {"title": "Bare-Metal Networking", "category": "network", "layer": 0, "badge": "PRIMARY"},
        "hardware-nodes": {"title": "Hardware & Nodes", "category": "hardware", "layer": 1, "badge": "7 NODES"},
        "biometrics-dsp": {"title": "Medical Biometrics & DSP", "category": "biometrics", "layer": 2, "badge": "512Hz ECG"},
        "ai-inference": {"title": "Local AI Inference Mesh", "category": "inference", "layer": 3, "badge": "RPC :50052"},
        "training-lora": {"title": "LoRA Distillation Monitor", "category": "training", "layer": 4, "badge": "24/7 SFT"},
        "training-games": {"title": "Implemented Games Arena", "category": "training", "layer": 4, "badge": "13-FFA"},
        "training-metrics": {"title": "Structural AST Metrics", "category": "training", "layer": 4, "badge": "3.29M LOC"},
        "training-traces": {"title": "Execution Action Traces", "category": "training", "layer": 4, "badge": "LEDGER"},
        "governance": {"title": "Master AGI Governance", "category": "governance", "layer": 5, "badge": ">0.98 ACCORD"},
        "leaderboard": {"title": "Swarm ELO Leaderboard", "category": "leaderboard", "layer": 5, "badge": "TOP 10"},
        "tooling-commerce": {"title": "Tooling & Commerce Hub", "category": "tooling", "layer": 6, "badge": "12 MCP"},
        "optimization-hardware": {"title": "Hardware Sentinel HUD", "category": "optimization", "layer": 1, "badge": "PORT 18802"},
        "optimization-software": {"title": "Software & ASan", "category": "optimization", "layer": 4, "badge": "COMPILER"},
        "optimization-internet": {"title": "Internet & Multi-WAN", "category": "optimization", "layer": 0, "badge": "10-ROUTE"},
        "optimization-storage": {"title": "Storage & Tri-Vault", "category": "optimization", "layer": 1, "badge": "DFS SYNC"}
    }

    def __init__(self, initial_route: str = "governance"):
        if initial_route not in self.VALID_ROUTES:
            raise ValueError(f"Invalid route: {initial_route}")
        self.active_route = initial_route
        self.is_sidebar_collapsed = False
        self.history: List[str] = [initial_route]
        self.active_params: Dict[str, str] = {}

    def set_active_route(self, route: str, params: Optional[Dict[str, str]] = None) -> bool:
        if route not in self.VALID_ROUTES:
            return False
        self.active_route = route
        self.history.append(route)
        self.active_params = params or {}
        return True

    def toggle_sidebar(self) -> bool:
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        return self.is_sidebar_collapsed

    def go_back(self) -> Optional[str]:
        if len(self.history) > 1:
            self.history.pop()
            self.active_route = self.history[-1]
            return self.active_route
        return None

    def get_route_category(self) -> str:
        return self.ROUTE_METADATA.get(self.active_route, {}).get("category", "unknown")

    def get_route_title(self) -> str:
        return self.ROUTE_METADATA.get(self.active_route, {}).get("title", "")

    def get_route_layer(self) -> int:
        return self.ROUTE_METADATA.get(self.active_route, {}).get("layer", 0)


def test_navigation_initial_state(canonical_routes):
    nav = NavigationStateMachine(initial_route="governance")
    assert nav.active_route == "governance"
    assert nav.is_sidebar_collapsed is False
    assert len(nav.history) == 1
    assert nav.get_route_category() == "governance"
    assert nav.get_route_title() == "Master AGI Governance"


def test_all_canonical_routes_valid(canonical_routes):
    nav = NavigationStateMachine()
    for route in canonical_routes:
        assert nav.set_active_route(route) is True
        assert nav.active_route == route
        assert nav.get_route_title() != ""


def test_ground_up_layers_routes_enumeration():
    """Verify all 7 ground-up stability layer routes exist and have valid metadata."""
    nav = NavigationStateMachine()
    ground_up_routes = [
        ("network-metrics", 0, "network"),
        ("hardware-nodes", 1, "hardware"),
        ("biometrics-dsp", 2, "biometrics"),
        ("ai-inference", 3, "inference"),
        ("training-lora", 4, "training"),
        ("governance", 5, "governance"),
        ("tooling-commerce", 6, "tooling")
    ]
    for route, expected_layer, expected_cat in ground_up_routes:
        assert nav.set_active_route(route) is True
        assert nav.get_route_layer() == expected_layer
        assert nav.get_route_category() == expected_cat


def test_network_metrics_route_category_and_metadata():
    nav = NavigationStateMachine()
    assert nav.set_active_route("network-metrics") is True
    assert nav.get_route_category() == "network"
    assert nav.get_route_layer() == 0
    assert nav.get_route_title() == "Bare-Metal Networking"


def test_sidebar_toggle_state():
    nav = NavigationStateMachine()
    assert nav.is_sidebar_collapsed is False
    state1 = nav.toggle_sidebar()
    assert state1 is True
    assert nav.is_sidebar_collapsed is True
    state2 = nav.toggle_sidebar()
    assert state2 is False
    assert nav.is_sidebar_collapsed is False


def test_navigation_history_and_back():
    nav = NavigationStateMachine()
    nav.set_active_route("optimization-hardware")
    nav.set_active_route("training-lora")
    nav.set_active_route("training-games")
    assert nav.active_route == "training-games"
    assert len(nav.history) == 4

    prev = nav.go_back()
    assert prev == "training-lora"
    assert nav.active_route == "training-lora"

    prev2 = nav.go_back()
    assert prev2 == "optimization-hardware"
    assert nav.active_route == "optimization-hardware"

    prev3 = nav.go_back()
    assert prev3 == "governance"
    assert nav.active_route == "governance"

    # Cannot go back past initial
    prev_none = nav.go_back()
    assert prev_none is None
    assert nav.active_route == "governance"


def test_optimization_routes_category_clustering():
    nav = NavigationStateMachine()
    opt_routes = [
        "optimization-hardware",
        "optimization-software",
        "optimization-internet",
        "optimization-storage"
    ]
    for r in opt_routes:
        nav.set_active_route(r)
        assert nav.get_route_category() == "optimization"


def test_training_routes_category_clustering():
    nav = NavigationStateMachine()
    training_routes = [
        "training-lora",
        "training-games",
        "training-metrics",
        "training-traces"
    ]
    for r in training_routes:
        nav.set_active_route(r)
        assert nav.get_route_category() == "training"


def test_invalid_route_rejection():
    nav = NavigationStateMachine()
    assert nav.set_active_route("nonexistent-route") is False
    assert nav.active_route == "governance"
    assert nav.set_active_route("admin/hack") is False
    assert nav.set_active_route("") is False


def test_route_deep_linking_params():
    nav = NavigationStateMachine()
    nav.set_active_route("training-games", {"model": "kimi_tandem", "arena": "ffa"})
    assert nav.active_route == "training-games"
    assert nav.active_params.get("model") == "kimi_tandem"
    assert nav.active_params.get("arena") == "ffa"


def test_cycle_all_routes_without_state_corruption(canonical_routes):
    nav = NavigationStateMachine()
    for _ in range(3):
        for route in canonical_routes:
            assert nav.set_active_route(route) is True
            assert nav.active_route == route
    assert len(nav.history) == 34
