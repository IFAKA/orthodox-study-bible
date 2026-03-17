"""ChatRefScreen — modal for navigating scripture refs found in an AI response."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


class ChatRefScreen(ModalScreen[str | None]):
    """Shows scripture references parsed from the last AI response.

    Dismisses with target verse_ref (str) or None to cancel.
    """

    DEFAULT_CSS = """
    ChatRefScreen {
        align: center middle;
    }
    #chatref-dialog {
        width: 60%;
        height: auto;
        max-height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #chatref-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #chatref-list {
        height: auto;
        max-height: 20;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_none", "Close"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
        Binding("enter", "select", "Jump", show=True),
    ]

    def __init__(self, refs: list[tuple[str, str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._refs = refs  # list of (verse_ref, display_label)

    def compose(self) -> ComposeResult:
        count = len(self._refs)
        title = f"References in response ({count})" if count else "References in response"
        with Vertical(id="chatref-dialog"):
            yield Label(title, id="chatref-title")
            yield ListView(id="chatref-list")

    def on_mount(self) -> None:
        lv = self.query_one("#chatref-list", ListView)
        if self._refs:
            for verse_ref, display_label in self._refs:
                item = ListItem(Label(f"→ {display_label}"))
                item._verse_ref = verse_ref  # type: ignore[attr-defined]
                lv.append(item)
        else:
            lv.append(ListItem(Label("No references found.")))

    def action_list_down(self) -> None:
        self.query_one("#chatref-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#chatref-list", ListView).action_cursor_up()

    def action_select(self) -> None:
        lv = self.query_one("#chatref-list", ListView)
        if lv.highlighted_child is None:
            return
        verse_ref = getattr(lv.highlighted_child, "_verse_ref", None)
        self.dismiss(verse_ref)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        verse_ref = getattr(event.item, "_verse_ref", None)
        self.dismiss(verse_ref)
