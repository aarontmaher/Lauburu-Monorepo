"""
Canonical Port TUI - Braille & Sub-Pixel Waveform Graphic Widget
Version: 1.0.0-CANONICAL

Delivers ultra-dense, 60/120 FPS high-resolution terminal charting using
2x4 sub-pixel Braille Unicode patterns (U+2800 .. U+28FF) for:
- 512Hz Movesense Pan-Tompkins ECG Waveforms
- DFA-alpha1 Zone 2 Fractal Scaling Trends
- Local AI Model Token Generation Throughput (tok/s)
- 10Gbps Thunderbolt 4 Sub-Millisecond Latency Histograms
"""

from typing import List, Optional, Tuple
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive


def render_braille_chart(
    values: List[float],
    width: int = 60,
    height: int = 8,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    color: str = "#00ffcc",
    fill: bool = False
) -> Text:
    """
    Converts a list of floating-point values into an ultra-dense Braille canvas.
    Each terminal cell represents 2 horizontal pixels by 4 vertical pixels.
    """
    if not values or width <= 0 or height <= 0:
        return Text("No data stream", style="dim italic")

    # Resample values to fit pixel width (2 pixels per terminal character column)
    pixel_width = width * 2
    pixel_height = height * 4

    # Min/Max normalization
    actual_min = min_val if min_val is not None else min(values)
    actual_max = max_val if max_val is not None else max(values)
    if actual_max == actual_min:
        actual_max += 1.0

    # Resample
    if len(values) >= pixel_width:
        step = len(values) / pixel_width
        sampled = [values[int(i * step)] for i in range(pixel_width)]
    else:
        # Interpolate / pad
        ratio = (len(values) - 1) / max(1, pixel_width - 1)
        sampled = []
        for i in range(pixel_width):
            idx = i * ratio
            i0 = int(idx)
            i1 = min(len(values) - 1, i0 + 1)
            frac = idx - i0
            val = values[i0] * (1.0 - frac) + values[i1] * frac
            sampled.append(val)

    # 2D Bit Grid for Braille [height*4][width*2]
    grid = [[0 for _ in range(pixel_width)] for _ in range(pixel_height)]

    for x, val in enumerate(sampled):
        # Normalize to [0, pixel_height - 1]
        norm = (val - actual_min) / (actual_max - actual_min)
        norm = max(0.0, min(1.0, norm))
        y = int(norm * (pixel_height - 1))
        # Invert y for terminal coordinates (0 is top)
        grid_y = (pixel_height - 1) - y

        if 0 <= grid_y < pixel_height:
            grid[grid_y][x] = 1
            if fill:
                for fy in range(grid_y, pixel_height):
                    grid[fy][x] = 1

    # Braille Dot Map offsets:
    # dot 1: (0,0) = 0x1, dot 4: (1,0) = 0x8
    # dot 2: (0,1) = 0x2, dot 5: (1,1) = 0x10
    # dot 3: (0,2) = 0x4, dot 6: (1,2) = 0x20
    # dot 7: (0,3) = 0x40, dot 8: (1,3) = 0x80
    BRAILLE_MAP = [
        [(0, 0, 0x1), (1, 0, 0x8)],
        [(0, 1, 0x2), (1, 1, 0x10)],
        [(0, 2, 0x4), (1, 2, 0x20)],
        [(0, 3, 0x40), (1, 3, 0x80)]
    ]

    out_lines: List[str] = []
    for cy in range(height):
        line_chars: List[str] = []
        for cx in range(width):
            char_code = 0x2800  # Base Braille blank
            for r in range(4):
                gy = cy * 4 + r
                for c in range(2):
                    gx = cx * 2 + c
                    if gy < pixel_height and gx < pixel_width and grid[gy][gx]:
                        char_code |= BRAILLE_MAP[r][c][2]
            line_chars.append(chr(char_code))
        out_lines.append("".join(line_chars))

    result = Text()
    for i, line in enumerate(out_lines):
        result.append(line, style=color)
        if i < len(out_lines) - 1:
            result.append("\n")

    return result


class BrailleWaveformWidget(Widget):
    """
    Textual Widget that renders live reactive sub-pixel Braille waveforms.
    """

    DEFAULT_CSS = """
    BrailleWaveformWidget {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: #070b12;
        border: solid #1e293b;
    }
    """

    data_stream = reactive([])
    title = reactive("Live Telemetry Stream")
    accent_color = reactive("#00ffcc")

    def __init__(
        self,
        title: str = "Live Telemetry Stream",
        accent_color: str = "#00ffcc",
        height_cells: int = 6,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.accent_color = accent_color
        self.height_cells = height_cells
        self.min_val = min_val
        self.max_val = max_val

    def render(self) -> Text:
        w = max(20, self.size.width - 4)
        chart = render_braille_chart(
            self.data_stream,
            width=w,
            height=self.height_cells,
            min_val=self.min_val,
            max_val=self.max_val,
            color=self.accent_color
        )
        header = Text(f"─── {self.title} ", style=f"bold {self.accent_color}")
        if self.data_stream:
            latest = self.data_stream[-1]
            header.append(f"[{latest:.2f}]", style="bold #ffffff")
        header.append(" ───\n", style=f"bold {self.accent_color}")
        return header + chart
