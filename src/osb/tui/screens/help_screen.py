"""HelpScreen — grouped keybinding reference overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static

# The canonical keybinding reference, grouped for display. Keep in sync with
# the BINDINGS in MainScreen / ScripturePane / RightPane.
KEYMAP_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Text Navigation", [
        ("/", "Search"),
        ("j or ↓", "Next verse"),
        ("k or ↑", "Prev verse"),
        ("J or Shift+↓", "Next chapter"),
        ("K or Shift+↑", "Prev chapter"),
        ("space", "Page down"),
        ("ctrl+d", "Half page"),
        ("ctrl+u", "Half page"),
    ]),
    ("Interactions", [
        ("b", "Bookmark"),
        ("h", "Highlight"),
        ("o", "Annotate"),
        ("x", "Cross-reference"),
        ("y", "Copy"),
        ("C", "Mark Complete"),
        ("a", "Add to collection"),
        ("P", "Progress"),
    ]),
    ("App Navigation", [
        ("t", "Table of Contents"),
        ("f", "Find"),
        ("L", "Lectionary"),
        ("p", "Toggle panel"),
        ("?", "Help"),
        ("q", "Quit"),
    ]),
    ("Panel Functions", [
        ("m", "Commentary"),
        ("c", "Chat"),
        ("n", "Notes"),
        ("l", "Collections"),
        ("[ ]", "Navigate panel"),
    ]),
    ("Settings", [
        ("T", "Theme"),
    ]),
]


def build_keymap_text() -> str:
    """Render KEYMAP_GROUPS as aligned, grouped Textual markup."""
    key_width = max(
        len(keys) for _, rows in KEYMAP_GROUPS for keys, _ in rows
    )
    lines: list[str] = []
    for group, rows in KEYMAP_GROUPS:
        if lines:
            lines.append("")
        lines.append(f"[bold $accent]{group}[/]")
        for keys, desc in rows:
            # Pad for alignment first, then escape '[' so keys like "[ ]"
            # render literally instead of being parsed as markup.
            padded = f"{keys:<{key_width}}".replace("[", r"\[")
            lines.append(f"  {padded}   {desc}")
    return "\n".join(lines)


def build_help_text(widget_bindings: list, app_bindings: list) -> str:
    """Back-compat shim — the help now shows one comprehensive reference."""
    return build_keymap_text()


class HelpScreen(ModalScreen):
    """Keybinding reference. Dismiss with Escape, ? or q; scroll with j/k."""

    BINDINGS = [
        Binding("escape", "dismiss", show=False),
        Binding("question_mark", "dismiss", show=False),
        Binding("q", "dismiss", show=False),
        Binding("j", "scroll_down", show=False),
        Binding("k", "scroll_up", show=False),
    ]

    def __init__(self, title: str = "Keybindings", text: str | None = None) -> None:
        super().__init__()
        self._title = title
        self._text = text if text is not None else build_keymap_text()

    def compose(self) -> ComposeResult:
        # VerticalScroll is focusable, so the reference scrolls when it
        # overflows the dialog height.
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
