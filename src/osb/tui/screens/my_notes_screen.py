"""MyNotesScreen — all annotations and bookmarks grouped by book."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Label, ListItem, ListView, Markdown

from osb.tui.widgets.app_header import AppHeader


class MyNotesScreen(Screen):
    """Screen showing all annotations and bookmarks."""

    BINDINGS = [
        Binding("q", "close", "Back"),
        Binding("escape", "close", "Back"),
        Binding("e", "export", "Export"),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn

    def compose(self) -> ComposeResult:
        yield AppHeader(title="My Notes & Bookmarks")
        with Horizontal(id="notes-layout"):
            yield ListView(id="notes-list")
            yield Markdown("Select an item to view", id="notes-detail")
        yield Footer()

    def on_mount(self) -> None:
        self._load_items()
        self.query_one("#notes-list", ListView).focus()

    def _load_items(self) -> None:
        from osb.db.queries import get_all_annotations, get_all_bookmarks

        lv = self.query_one("#notes-list", ListView)
        lv.clear()

        annotations = get_all_annotations(self.conn)
        bookmarks = get_all_bookmarks(self.conn)

        if not annotations and not bookmarks:
            lv.append(ListItem(Label("No notes or bookmarks yet.")))
            return

        if annotations:
            lv.append(ListItem(Label("── Annotations ──")))
            for ann in annotations:
                item = ListItem(
                    Label(f"  {ann.verse_ref}  {ann.body[:50]}…" if len(ann.body) > 50 else f"  {ann.verse_ref}  {ann.body}")
                )
                item._data = {"type": "annotation", "verse_ref": ann.verse_ref, "body": ann.body}  # type: ignore
                lv.append(item)

        if bookmarks:
            lv.append(ListItem(Label("── Bookmarks ──")))
            for bm in bookmarks:
                item = ListItem(Label(f"  {bm.verse_ref}  {bm.label or ''}"))
                item._data = {"type": "bookmark", "verse_ref": bm.verse_ref}  # type: ignore
                lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        data = getattr(event.item, "_data", None)
        if not data:
            return
        md = self.query_one("#notes-detail", Markdown)
        if data["type"] == "annotation":
            md.update(f"**{data['verse_ref']}**\n\n{data['body']}")
        elif data["type"] == "bookmark":
            from osb.db.queries import get_verse
            verse = get_verse(self.conn, data["verse_ref"])
            text = verse.text if verse else ""
            md.update(f"**{data['verse_ref']}** ♦\n\n{text}")

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_export(self) -> None:
        self._export_markdown()

    def _export_markdown(self) -> None:
        from datetime import date

        from osb.db.queries import get_all_annotations, get_all_bookmarks, get_verse

        annotations = get_all_annotations(self.conn)
        bookmarks = get_all_bookmarks(self.conn)

        lines = [f"# OSB Study Notes — {date.today()}", ""]

        if annotations:
            lines.append("## Annotations")
            for ann in annotations:
                lines.append(f"### {ann.verse_ref}")
                verse = get_verse(self.conn, ann.verse_ref)
                if verse:
                    lines.append(f"> {verse.text}")
                    lines.append("")
                lines.append(ann.body)
                lines.append("")

        if bookmarks:
            lines.append("## Bookmarks")
            for bm in bookmarks:
                verse = get_verse(self.conn, bm.verse_ref)
                text = verse.text if verse else ""
                label = f" — {bm.label}" if bm.label else ""
                lines.append(f"- **{bm.verse_ref}**{label}: {text}")
            lines.append("")

        from osb.config import APP_DIR

        out_path = APP_DIR / f"osb-notes-{date.today()}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines))

        md = self.query_one("#notes-detail", Markdown)
        md.update(f"Exported to:\n\n`{out_path}`")
