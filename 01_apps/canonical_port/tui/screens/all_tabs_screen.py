from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Grid
from textual.widgets import Header, Footer

try:
    from views.network_view import NetworkView
    from views.hardware_view import HardwareView
    from views.biometrics_view import BiometricsView
    from views.ai_inference_view import AiInferenceView
    from views.training_view import TrainingView
    from views.governance_view import GovernanceView
    from views.tooling_view import ToolingView
    from views.optimization_view import OptimizationView
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
except ImportError:
    from tui.views.network_view import NetworkView
    from tui.views.hardware_view import HardwareView
    from tui.views.biometrics_view import BiometricsView
    from tui.views.ai_inference_view import AiInferenceView
    from tui.views.training_view import TrainingView
    from tui.views.governance_view import GovernanceView
    from tui.views.tooling_view import ToolingView
    from tui.views.optimization_view import OptimizationView
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar

class AllTabsGridScreen(Screen):
    """A screen that shows all the main views side-by-side in a large grid."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back to Tabs")
    ]
    
    DEFAULT_CSS = """
    AllTabsGridScreen {
        background: #0b111c;
    }
    #all-tabs-grid {
        grid-size: 3 3;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: 1fr 1fr 1fr;
        grid-gutter: 1;
        width: 100%;
        height: 100%;
        margin: 1;
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
        yield PinnedTabNavBar()
        with Grid(id="all-tabs-grid"):
            # We omit AGI Term to save space, rendering the 8 major monitoring views
            yield NetworkView(classes="grid-cell")
            yield HardwareView(classes="grid-cell")
            yield BiometricsView(classes="grid-cell")
            yield AiInferenceView(classes="grid-cell")
            yield TrainingView(classes="grid-cell")
            yield GovernanceView(classes="grid-cell")
            yield ToolingView(classes="grid-cell")
            yield OptimizationView(classes="grid-cell")
        yield Footer()

    def on_mount(self):
        nav = self.query_one(PinnedTabNavBar)
        if nav:
            # Setting it to something that isn't highlighted, or a custom string
            nav.set_active_screen("all_tabs")
            
    def refresh_views(self):
        for child in self.query(".grid-cell"):
            if hasattr(child, "refresh_data"):
                child.refresh_data()
