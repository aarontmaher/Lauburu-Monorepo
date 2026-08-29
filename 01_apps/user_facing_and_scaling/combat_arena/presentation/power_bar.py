"""
120 FPS Compute Power Bar Widget & Renderer.
============================================
Subsystem: 01_apps/user_facing_and_scaling/combat_arena/presentation/power_bar.py
"""

from rich.text import Text

def render_power_bar(ratio: float, width: int = 40) -> Text:
    """
    Renders high-refresh animated power bar from -1.0 (Red Dominance) to +1.0 (Blue Dominance).
    """
    clamped = max(min(ratio, 1.0), -1.0)
    norm = (clamped + 1.0) / 2.0  # 0.0 to 1.0
    red_len = int(norm * width)
    blue_len = width - red_len

    t = Text()
    t.append("🔴 RED ", style="bold red")
    t.append("█" * red_len, style="red")
    t.append("▌", style="bold yellow")
    t.append("█" * blue_len, style="blue")
    t.append(" BLUE 🔵", style="bold blue")
    return t
