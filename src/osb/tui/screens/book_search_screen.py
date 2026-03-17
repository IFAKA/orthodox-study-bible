"""BookSearchScreen — modal for quickly jumping to a book in the sidebar."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from osb.db.queries import get_all_books


class BookSearchScreen(ModalScreen[str | None]):
    """Modal that filters books by name and returns the selected book ref."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._all_books: list = []

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog", classes="modal-dialog"):
            yield Label("Go to Book", id="search-title", classes="modal-title")
            yield Input(placeholder="Filter books…", id="book-search-input")
            yield ListView(id="book-search-results")
            yield Label("Type to filter · j/k or ↑/↓ to navigate · Enter select · Esc close", id="search-help")

    def on_mount(self) -> None:
        self._all_books = get_all_books(self.conn)
        self._render_books(self._all_books)
        self.query_one("#book-search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        if query:
            matches = [b for b in self._all_books if query in b.name.lower()]
        else:
            matches = self._all_books
        self._render_books(matches)

    def _render_books(self, books: list) -> None:
        lv = self.query_one("#book-search-results", ListView)
        lv.clear()
        for book in books:
            item = ListItem(Label(book.name))
            item._book_ref = book.ref  # type: ignore[attr-defined]
            lv.append(item)
        lv.scroll_home(animate=False)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        ref = getattr(event.item, "_book_ref", None)
        if ref:
            self.dismiss(ref)

    def action_list_down(self) -> None:
        self.query_one("#book-search-results", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#book-search-results", ListView).action_cursor_up()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        lv = self.query_one("#book-search-results", ListView)
        highlighted = lv.highlighted_child
        if highlighted:
            ref = getattr(highlighted, "_book_ref", None)
            if ref:
                self.dismiss(ref)
