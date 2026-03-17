"""GlossaryScreen — searchable Orthodox terminology glossary."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Input, Label, ListItem, ListView, Markdown

from osb.db import queries
from osb.tui.widgets.app_header import AppHeader


class GlossaryScreen(Screen):
    """Searchable glossary of Orthodox/patristic terms."""

    BINDINGS = [
        Binding("q", "close", "Back"),
        Binding("escape", "close", "Back"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn

    def compose(self) -> ComposeResult:
        yield AppHeader(title="Glossary")
        yield Input(placeholder="Search terms…", id="glossary-search")
        yield ListView(id="glossary-list")
        yield Markdown("", id="glossary-detail")
        yield Footer()

    def on_mount(self) -> None:
        self._load_results("")
        self.query_one("#glossary-search", Input).focus()

    def _load_results(self, query: str) -> None:
        lv = self.query_one("#glossary-list", ListView)
        lv.clear()
        if query.strip():
            results = queries.search_glossary(self.conn, query)
        else:
            # Show all terms when no query
            try:
                rows = self.conn.execute(
                    "SELECT term, definition FROM glossary ORDER BY term LIMIT 100"
                ).fetchall()
                results = [dict(r) for r in rows]
            except Exception:
                results = []

        if not results:
            empty_msg = (
                "No glossary entries found — re-import the EPUB if your "
                "version includes a glossary."
            )
            lv.append(ListItem(Label(empty_msg)))
            return

        for r in results:
            item = ListItem(Label(r["term"]))
            item._term = r["term"]  # type: ignore[attr-defined]
            item._definition = r["definition"]  # type: ignore[attr-defined]
            lv.append(item)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "glossary-search":
            self._load_results(event.value)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        term = getattr(event.item, "_term", None)
        definition = getattr(event.item, "_definition", None)
        if term and definition:
            md = self.query_one("#glossary-detail", Markdown)
            md.update(f"**{term}**\n\n{definition}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        term = getattr(event.item, "_term", None)
        definition = getattr(event.item, "_definition", None)
        if term and definition:
            md = self.query_one("#glossary-detail", Markdown)
            md.update(f"**{term}**\n\n{definition}")

    def action_list_down(self) -> None:
        self.query_one("#glossary-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#glossary-list", ListView).action_cursor_up()

    def action_close(self) -> None:
        self.app.pop_screen()
