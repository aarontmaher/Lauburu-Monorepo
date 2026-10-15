from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Button
from textual.widget import Widget
from textual.message import Message

class KeyboardKey(Button):
    def __init__(self, key_val: str, label: str = None, **kwargs):
        super().__init__(label or key_val, **kwargs)
        self.key_val = key_val

class VirtualKeyboard(Widget):
    DEFAULT_CSS = """
    VirtualKeyboard {
        dock: bottom;
        height: 14;
        background: $panel;
        border-top: solid $primary;
        display: none;
    }
    VirtualKeyboard.-visible {
        display: block;
    }
    VirtualKeyboard.-visible {
        display: block;
    }
    .kbd-row {
        layout: horizontal;
        height: 3;
        align: center middle;
    }
    KeyboardKey {
        min-width: 5;
        height: 3;
        margin: 0 1;
    }
    KeyboardKey.key-space {
        min-width: 30;
    }
    KeyboardKey.key-backspace, KeyboardKey.key-enter {
        min-width: 10;
        background: $accent;
    }
    """

    class KeyPressed(Message):
        def __init__(self, key: str) -> None:
            self.key = key
            super().__init__()

    def compose(self) -> ComposeResult:
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "backspace"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "enter"],
            ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/"],
            ["space"]
        ]
        
        with Vertical():
            for row in rows:
                with Horizontal(classes="kbd-row"):
                    for key in row:
                        if key == "backspace":
                            yield KeyboardKey(key, "⌫", classes="kbd-special key-backspace")
                        elif key == "enter":
                            yield KeyboardKey(key, "⏎", classes="kbd-special key-enter")
                        elif key == "space":
                            yield KeyboardKey(key, "␣", classes="kbd-special key-space")
                        else:
                            yield KeyboardKey(key)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        print(f"VirtualKeyboard button pressed: {event.button}")
        if isinstance(event.button, KeyboardKey):
            event.stop()
            self.post_message(self.KeyPressed(event.button.key_val))
            
    def toggle_visibility(self) -> None:
        if self.has_class("-visible"):
            self.remove_class("-visible")
        else:
            self.add_class("-visible")
