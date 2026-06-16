"""HelpScreen — keybinding reference overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static


def build_help_text(
    widget_bindings: list,
    app_bindings: list,
) -> str:
    """Render help text from two BINDINGS lists.

    Includes all bindings that have a non-empty description.
    widget_bindings → "Shortcuts" section
    app_bindings    → "App" section
    """
    def _render_section(title: str, bindings: list) -> str:
        lines = [f"[bold yellow]{title}[/]"]
        for b in bindings:
            if b.description:
                lines.append(f"  {b.key_display or b.key:<14} {b.description}")
        lines.append("")
        return "\n".join(lines)

    return (
        _render_section("Shortcuts", widget_bindings)
        + _render_section("App", app_bindings)
    )


class HelpScreen(ModalScreen):
    """Keybinding reference. Dismiss with Escape or ?."""

    BINDINGS = [
        Binding("escape", "dismiss", show=False),
        Binding("?", "dismiss", show=False),
        Binding("q", "dismiss", show=False),
        Binding("j", "scroll_down", show=False),
        Binding("k", "scroll_up", show=False),
    ]

    def __init__(self, title: str, text: str) -> None:
        super().__init__()
        self._title = title
        self._text = text

    def compose(self) -> ComposeResult:
        # VerticalScroll (unlike Static) is focusable, so the help text can be
        # scrolled with the keyboard when it overflows the dialog height.
        with VerticalScroll(id="help-dialog"):
            yield Label(f"[bold]{self._title}[/bold]", id="help-title")
            yield Static(self._text, id="help-body")

    def on_mount(self) -> None:
        try:
            self.query_one("#help-dialog", VerticalScroll).focus()
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        self.query_one("#help-dialog", VerticalScroll).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#help-dialog", VerticalScroll).scroll_up()
