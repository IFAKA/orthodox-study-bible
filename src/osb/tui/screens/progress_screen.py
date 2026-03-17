"""ProgressScreen — per-book reading progress overview."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView

from osb.db import queries
from osb.tui.widgets.app_header import AppHeader


def _ascii_bar(done: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "░" * width
    filled = round(done / total * width)
    return "█" * filled + "░" * (width - filled)


class ProgressScreen(Screen):
    """Full-screen per-book reading progress.

    Dismisses with verse_ref to navigate to, or None.
    """

    BINDINGS = [
        Binding("q", "dismiss_none", "Back"),
        Binding("escape", "dismiss_none", "Back"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
        Binding("enter", "select", "Go to book", show=True),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn

    def compose(self) -> ComposeResult:
        yield AppHeader(title="Reading Progress")
        yield ListView(id="progress-list")
        yield Footer()

    def on_mount(self) -> None:
        self._load_items()
        self.query_one("#progress-list", ListView).focus()

    def _load_items(self) -> None:
        lv = self.query_one("#progress-list", ListView)
        lv.clear()

        books = queries.get_all_books_progress(self.conn)
        if not books:
            lv.append(ListItem(Label("No data — import the EPUB first.")))
            return

        current_testament = None
        TESTAMENT_LABELS = {
            "OT": "── Old Testament ──",
            "DC": "── Deuterocanon ──",
            "NT": "── New Testament ──",
        }
        ORDER = ["OT", "DC", "NT"]

        for testament in ORDER:
            section = [b for b in books if b["testament"] == testament]
            if not section:
                continue
            # Testament separator (non-selectable)
            sep = ListItem(Label(TESTAMENT_LABELS[testament]))
            sep._book_ref = None  # type: ignore[attr-defined]
            sep.disabled = True
            lv.append(sep)

            for b in section:
                done = b["done"]
                total = b["total"]
                pct = round(done / total * 100) if total else 0
                bar = _ascii_bar(done, total)
                check = "✓ " if done == total and total > 0 else "  "
                label = f"{check}{b['name']:<22} {done:>3}/{total:<3}  {bar} {pct:>3}%"
                item = ListItem(Label(label))
                item._book_ref = b["ref"]  # type: ignore[attr-defined]
                lv.append(item)

    def action_list_down(self) -> None:
        self.query_one("#progress-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#progress-list", ListView).action_cursor_up()

    def action_select(self) -> None:
        lv = self.query_one("#progress-list", ListView)
        if lv.highlighted_child is None:
            return
        book_ref = getattr(lv.highlighted_child, "_book_ref", None)
        if not book_ref:
            return
        ch_ref = queries.get_first_incomplete_chapter(self.conn, book_ref)
        if not ch_ref:
            return
        verse = queries.get_first_verse_of_chapter(self.conn, ch_ref)
        self.dismiss(verse.ref if verse else None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.action_select()
