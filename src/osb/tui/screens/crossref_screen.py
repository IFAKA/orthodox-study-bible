"""CrossRefScreen — compact modal for cross-reference navigation."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView

from osb.db import queries


class CrossRefScreen(ModalScreen[str | None]):
    """Shows cross-references for a verse and lets the user jump to one.

    Dismisses with target verse_ref (str) or None to cancel.
    """

    DEFAULT_CSS = """
    CrossRefScreen {
        align: center middle;
    }
    #xref-dialog {
        width: 60%;
        height: auto;
        max-height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #xref-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #xref-list {
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

    def __init__(
        self, conn: sqlite3.Connection, verse_ref: str, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self.verse_ref = verse_ref
        self._xrefs: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="xref-dialog"):
            yield Label(f"Cross-references: {self.verse_ref}", id="xref-title")
            yield ListView(id="xref-list")

    def on_mount(self) -> None:
        self._xrefs = [
            r for r in queries.get_cross_refs(self.conn, self.verse_ref)
            if r.get("to_ref")
        ]
        lv = self.query_one("#xref-list", ListView)
        if self._xrefs:
            for xr in self._xrefs:
                item = ListItem(Label(f"→ {xr['to_ref_text']}"))
                item._to_ref = xr["to_ref"]  # type: ignore[attr-defined]
                lv.append(item)
        else:
            lv.append(ListItem(Label("No navigable cross-references.")))

    def action_list_down(self) -> None:
        self.query_one("#xref-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#xref-list", ListView).action_cursor_up()

    def action_select(self) -> None:
        lv = self.query_one("#xref-list", ListView)
        if lv.highlighted_child is None:
            return
        to_ref = getattr(lv.highlighted_child, "_to_ref", None)
        self.dismiss(to_ref)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        to_ref = getattr(event.item, "_to_ref", None)
        self.dismiss(to_ref)
