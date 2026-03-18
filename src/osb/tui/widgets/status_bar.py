"""StatusBar — vim-style status line with optional command input."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label


class StatusBar(Widget):
    """Vim-style status line. Shows mode, current ref, lectionary, and progress.
    Also doubles as the command input when command mode is active.
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        layout: horizontal;
        background: $surface;
    }
    """

    class CommandSubmitted(Message):
        """Posted when user submits a command (Enter pressed)."""
        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    class CommandCancelled(Message):
        """Posted when user cancels command mode (Escape pressed)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._command_mode: bool = False

    def compose(self) -> ComposeResult:
        yield Label("NORMAL", id="status-mode")
        yield Label("", id="status-ref")
        yield Label("", id="status-progress")
        yield Label(":", id="status-cmd-prefix", classes="hidden")
        yield Input(id="status-cmd-input", placeholder="", classes="hidden")

    def update_mode(self, mode: str) -> None:
        try:
            self.query_one("#status-mode", Label).update(mode)
        except Exception:
            pass

    def update_ref(self, ref: str) -> None:
        try:
            self.query_one("#status-ref", Label).update(ref)
        except Exception:
            pass

    def update_progress(self, text: str) -> None:
        try:
            self.query_one("#status-progress", Label).update(text)
        except Exception:
            pass

    def enter_command_mode(self) -> None:
        """Switch to command input mode."""
        self._command_mode = True
        self.query_one("#status-mode", Label).add_class("hidden")
        self.query_one("#status-ref", Label).add_class("hidden")
        self.query_one("#status-progress", Label).add_class("hidden")
        self.query_one("#status-cmd-prefix", Label).remove_class("hidden")
        inp = self.query_one("#status-cmd-input", Input)
        inp.remove_class("hidden")
        inp.clear()
        inp.focus()

    def exit_command_mode(self) -> None:
        """Restore normal display."""
        self._command_mode = False
        self.query_one("#status-mode", Label).remove_class("hidden")
        self.query_one("#status-ref", Label).remove_class("hidden")
        self.query_one("#status-progress", Label).remove_class("hidden")
        self.query_one("#status-cmd-prefix", Label).add_class("hidden")
        inp = self.query_one("#status-cmd-input", Input)
        inp.add_class("hidden")
        inp.clear()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "status-cmd-input":
            cmd = event.value.strip()
            self.exit_command_mode()
            if cmd:
                self.post_message(self.CommandSubmitted(cmd))

    def on_input_key(self, event) -> None:
        # Escape cancels command mode
        pass

    def on_key(self, event) -> None:
        if self._command_mode and event.key == "escape":
            event.stop()
            self.exit_command_mode()
            self.post_message(self.CommandCancelled())
