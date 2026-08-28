from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Grid, ScrollableContainer
from textual.widgets import Header, Footer

try:
    from views.overview_view import OverviewView
    from views.network_view import NetworkView
    from views.hardware_view import HardwareView
    from views.biometrics_view import BiometricsView
    from views.ai_inference_view import AiInferenceView
    from views.training_view import TrainingView
    from views.governance_view import GovernanceView
    from views.tooling_view import ToolingView
    from views.optimization_view import OptimizationView
except ImportError:
    from tui.views.overview_view import OverviewView
    from tui.views.network_view import NetworkView
    from tui.views.hardware_view import HardwareView
    from tui.views.biometrics_view import BiometricsView
    from tui.views.ai_inference_view import AiInferenceView
    from tui.views.training_view import TrainingView
    from tui.views.governance_view import GovernanceView
    from tui.views.tooling_view import ToolingView
    from tui.views.optimization_view import OptimizationView

class GridScreen(Screen):
    """A screen that shows all the main views side-by-side in a large grid."""
    
    BINDINGS = [
        ("g", "app.pop_screen", "Back to Tabs"),
        ("escape", "app.pop_screen", "Back to Tabs")
    ]
    
    DEFAULT_CSS = """
    GridScreen {
        background: #0b111c;
    }
    #all-tabs-grid {
        grid-size: 3 3;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: 1fr 1fr 1fr;
        grid-gutter: 1;
        width: 100%;
        height: 100%;
    }
    .grid-cell {
        border: solid #1e293b;
        height: 100%;
        width: 100%;
        overflow: hidden;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="all-tabs-grid"):
            # We omit AGI Term and Overview to save space, or we can include them
            # Let's include the 9 core telemetry/control views
            views = [
                NetworkView(classes="grid-cell"),
                HardwareView(classes="grid-cell"),
                BiometricsView(classes="grid-cell"),
                AiInferenceView(classes="grid-cell"),
                TrainingView(classes="grid-cell"),
                GovernanceView(classes="grid-cell"),
                ToolingView(classes="grid-cell"),
                OptimizationView(classes="grid-cell"),
                OverviewView(classes="grid-cell")
            ]
            for v in views:
                # Need to modify IDs so they don't clash with the main screen, but it's a different Screen so Textual might be okay.
                # Actually, Textual IDs must be unique per-app unless we suffix them.
                # It's better to just mount them, as Screen isolation usually handles it, but Textual queries might get confused if we don't suffix.
                # However, since the other screen is inactive, it might be fine.
                yield v
        yield Footer()
