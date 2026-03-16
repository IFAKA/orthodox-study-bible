"""SearchScreen — FTS5 modal search."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView


class SearchScreen(ModalScreen[str | None]):
    """FTS modal. Dismisses with verse_ref on selection, None on cancel."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._results: list[dict] = []
        self._debounce_timer = None

    def compose(self) -> ComposeResult:
        yield Label("Search Scripture", id="search-title")
        yield Input(placeholder="Search…", id="search-input")
        yield ListView(id="search-results")
        yield Label("↑↓ navigate · Enter select · Esc close", id="search-help")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        if self._debounce_timer:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(0.3, lambda: self._do_search(event.value))

    def _do_search(self, query: str) -> None:
        from osb.db.queries import search_verses
        query = query.strip()
        if len(query) < 2:
            self._clear_results()
            return
        try:
            self._results = search_verses(self.conn, query)
        except Exception:
            self._results = []
        self._render_results()

    def _clear_results(self) -> None:
        self._results = []
        try:
            lv = self.query_one("#search-results", ListView)
            lv.clear()
        except Exception:
            pass

    def _render_results(self) -> None:
        try:
            lv = self.query_one("#search-results", ListView)
            lv.clear()
            for r in self._results[:50]:
                ref = r["ref"]
                snippet = r.get("snippet", "")
                item = ListItem(
                    Label(f"{ref:15} {snippet[:60]}"),
                    id=f"sr-{ref.replace('-', '_')}",
                )
                item._verse_ref = ref  # type: ignore[attr-defined]
                lv.append(item)
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        ref = getattr(event.item, "_verse_ref", None)
        if ref:
            self.dismiss(ref)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        try:
            lv = self.query_one("#search-results", ListView)
            highlighted = lv.highlighted_child
            if highlighted:
                ref = getattr(highlighted, "_verse_ref", None)
                if ref:
                    self.dismiss(ref)
        except Exception:
            pass
