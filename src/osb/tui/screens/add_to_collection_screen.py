"""AddToCollectionScreen — modal picker for adding a verse to a collection."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from osb.db import queries


class AddToCollectionScreen(ModalScreen[int | None]):
    """Shows existing collections + option to create new.

    Dismisses with collection_id (int) or None to cancel.
    """

    DEFAULT_CSS = """
    AddToCollectionScreen {
        align: center middle;
    }
    #addcol-dialog {
        width: 60%;
        height: auto;
        max-height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #addcol-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #addcol-list {
        height: auto;
        max-height: 15;
    }
    #addcol-new-input {
        width: 1fr;
        margin-top: 1;
        display: none;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_none", "Close"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
        Binding("enter", "select", "Add", show=True),
        Binding("n", "new_collection", "New", show=True),
    ]

    def __init__(self, verse_ref: str, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self._verse_ref = verse_ref
        self.conn = conn
        self._creating_new = False

    def compose(self) -> ComposeResult:
        with Vertical(id="addcol-dialog"):
            yield Label(f"Add {self._verse_ref} to collection", id="addcol-title")
            yield ListView(id="addcol-list")
            yield Input(placeholder="New collection name…", id="addcol-new-input")

    def on_mount(self) -> None:
        self._populate_list()

    def _populate_list(self) -> None:
        lv = self.query_one("#addcol-list", ListView)
        lv.clear()
        collections = queries.get_all_collections(self.conn)
        if collections:
            for col in collections:
                count = queries.get_collection_item_count(self.conn, col.id)
                item = ListItem(Label(f"  {col.name}  ({count})"))
                item._collection_id = col.id  # type: ignore[attr-defined]
                lv.append(item)
        new_item = ListItem(Label("  ＋ New collection"))
        new_item._collection_id = None  # type: ignore[attr-defined]
        lv.append(new_item)

    def action_list_down(self) -> None:
        self.query_one("#addcol-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#addcol-list", ListView).action_cursor_up()

    def action_new_collection(self) -> None:
        self._show_new_input()

    def _show_new_input(self) -> None:
        self._creating_new = True
        inp = self.query_one("#addcol-new-input", Input)
        inp.display = True
        inp.focus()

    def action_select(self) -> None:
        if self._creating_new:
            return  # handled by input submitted
        lv = self.query_one("#addcol-list", ListView)
        if lv.highlighted_child is None:
            return
        col_id = getattr(lv.highlighted_child, "_collection_id", None)
        if col_id is None:
            # "＋ New collection" selected
            self._show_new_input()
        else:
            self.dismiss(col_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "addcol-new-input":
            return
        name = event.value.strip()
        if not name:
            self.dismiss(None)
            return
        col_id = queries.create_collection(self.conn, name)
        self.dismiss(col_id)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        col_id = getattr(event.item, "_collection_id", None)
        if col_id is None:
            self._show_new_input()
        else:
            self.dismiss(col_id)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape" and self._creating_new:
            inp = self.query_one("#addcol-new-input", Input)
            inp.display = False
            self._creating_new = False
            self.query_one("#addcol-list", ListView).focus()
            event.stop()
