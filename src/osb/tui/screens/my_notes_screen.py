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
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
        Binding("G", "list_bottom", "Bottom", show=False),
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
        from osb.importer.structure import format_ref

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
                label = format_ref(ann.verse_ref)
                preview = ann.body[:50] + "…" if len(ann.body) > 50 else ann.body
                item = ListItem(Label(f"  {label}  {preview}"))
                item._data = {"type": "annotation", "verse_ref": ann.verse_ref, "body": ann.body}  # type: ignore
                lv.append(item)

        if bookmarks:
            lv.append(ListItem(Label("── Bookmarks ──")))
            for bm in bookmarks:
                label = format_ref(bm.verse_ref)
                item = ListItem(Label(f"  {label}  {bm.label or ''}"))
                item._data = {"type": "bookmark", "verse_ref": bm.verse_ref}  # type: ignore
                lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        data = getattr(event.item, "_data", None)
        if not data:
            return
        md = self.query_one("#notes-detail", Markdown)
        from osb.importer.structure import format_ref
        label = format_ref(data["verse_ref"])
        if data["type"] == "annotation":
            md.update(f"**{label}**\n\n{data['body']}")
        elif data["type"] == "bookmark":
            from osb.db.queries import get_verse
            verse = get_verse(self.conn, data["verse_ref"])
            text = verse.text if verse else ""
            md.update(f"**{label}** ♦\n\n{text}")

    def action_list_down(self) -> None:
        self.query_one("#notes-list", ListView).action_cursor_down()

    def action_list_up(self) -> None:
        self.query_one("#notes-list", ListView).action_cursor_up()

    def action_list_bottom(self) -> None:
        lv = self.query_one("#notes-list", ListView)
        if lv._nodes:
            lv.index = len(lv._nodes) - 1

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

        from osb.importer.structure import format_ref

        if annotations:
            lines.append("## Annotations")
            for ann in annotations:
                lines.append(f"### {format_ref(ann.verse_ref)}")
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
                extra_label = f" — {bm.label}" if bm.label else ""
                lines.append(f"- **{format_ref(bm.verse_ref)}**{extra_label}: {text}")
            lines.append("")

        from osb.config import APP_DIR

        out_path = APP_DIR / f"osb-notes-{date.today()}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines))

        md = self.query_one("#notes-detail", Markdown)
        md.update(f"Exported to:\n\n`{out_path}`")
