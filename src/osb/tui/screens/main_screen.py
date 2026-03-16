"""MainScreen — 3-pane orchestrator."""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Input, Label

from osb.db import queries
from osb.importer.lectionary import get_primary_reading
from osb.tui.screens.daily_screen import DailyScreen
from osb.tui.screens.my_notes_screen import MyNotesScreen
from osb.tui.screens.search_screen import SearchScreen
from osb.tui.widgets.app_header import AppHeader
from osb.tui.widgets.book_tree import BookTree
from osb.tui.widgets.quit_modal import QuitModal
from osb.tui.widgets.right_pane import RightPane
from osb.tui.widgets.scripture_pane import ScripturePane


class MainScreen(Screen):
    """Primary 3-pane reading screen."""

    BINDINGS = [
        Binding("t", "toggle_sidebar", "Sidebar"),
        Binding("/", "search", "Search"),
        Binding("N", "notes", "Notes"),
        Binding("L", "lectionary", "Lectionary"),
        Binding("q", "quit_app", "Quit"),
        Binding("T", "toggle_theme", "Theme", show=False),
        Binding("h", "focus_scripture", "Scripture", show=False),
        Binding("l", "focus_right", "Commentary/Chat", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._sidebar_visible = False
        self._current_chapter_ref: str | None = None

    def compose(self) -> ComposeResult:
        yield AppHeader()

        # 3-pane horizontal layout
        with Horizontal(id="main-layout"):
            yield BookTree(self.conn, id="sidebar", classes="hidden")
            yield ScripturePane(self.conn, id="scripture-pane")
            yield RightPane(self.conn, id="right-pane")

        yield Footer()

    def on_mount(self) -> None:
        self._restore_session()
        self.call_after_refresh(lambda: self.query_one("#scripture-pane", ScripturePane).focus())

    def _restore_session(self) -> None:
        last_ref = queries.get_session(self.conn, "last_verse_ref", "")
        if last_ref:
            parts = last_ref.split("-")
            if len(parts) >= 2:
                ch_ref = "-".join(parts[:2])
                self._load_chapter(ch_ref, focus_verse_ref=last_ref)
                return

        # Default: Genesis 1
        self._load_chapter("GEN-1")

    def _load_chapter(self, chapter_ref: str, focus_verse_ref: str | None = None) -> None:
        self._current_chapter_ref = chapter_ref
        try:
            sp = self.query_one("#scripture-pane", ScripturePane)
            sp.load_chapter(chapter_ref, focus_verse_ref)
        except Exception:
            pass
        try:
            rp = self.query_one("#right-pane", RightPane)
            rp.load_chapter(chapter_ref)
        except Exception:
            pass
        self._update_header(chapter_ref)
        # Save session
        queries.set_session(self.conn, "last_chapter_ref", chapter_ref)

    def _update_header(self, chapter_ref: str) -> None:
        ch = queries.get_chapter(self.conn, chapter_ref)
        if not ch:
            return
        book = queries.get_book(self.conn, ch.book_ref)
        book_name = book.name if book else ch.book_ref
        complete = queries.is_chapter_complete(self.conn, chapter_ref)
        complete_str = " ✓" if complete else ""
        lectionary_ref = get_primary_reading(date.today())
        lectionary_str = f"Today: {lectionary_ref}" if lectionary_ref else ""

        try:
            header = self.query_one(AppHeader)
            header.update_title(f"{book_name} {ch.number}{complete_str}")
            header.update_lectionary(lectionary_str)
        except Exception:
            pass

    # ── Navigation from BookTree ──────────────────────────────────────────────

    def on_book_tree_chapter_selected(self, event: BookTree.ChapterSelected) -> None:
        self._load_chapter(event.chapter_ref)

    # ── Verse focus ───────────────────────────────────────────────────────────

    def on_scripture_pane_verse_focused(self, event: ScripturePane.VerseFocused) -> None:
        queries.set_session(self.conn, "last_verse_ref", event.verse_ref)
        try:
            rp = self.query_one("#right-pane", RightPane)
            rp.update_verse(event.verse_ref)
        except Exception:
            pass

    # ── Chapter navigation from ScripturePane ────────────────────────────────

    def on_scripture_pane_chapter_change_requested(
        self, event: ScripturePane.ChapterChangeRequested
    ) -> None:
        if not self._current_chapter_ref:
            return
        ch = queries.get_chapter(self.conn, self._current_chapter_ref)
        if not ch:
            return
        chapters = queries.get_chapters_for_book(self.conn, ch.book_ref)
        idx = next((i for i, c in enumerate(chapters) if c.ref == self._current_chapter_ref), None)
        if idx is None:
            return
        new_idx = idx + event.direction
        if 0 <= new_idx < len(chapters):
            self._load_chapter(chapters[new_idx].ref)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        self._sidebar_visible = not self._sidebar_visible
        try:
            sidebar = self.query_one("#sidebar", BookTree)
            if self._sidebar_visible:
                sidebar.remove_class("hidden")
                ref = self._current_chapter_ref
                if ref:
                    self.call_after_refresh(
                        lambda r=ref: sidebar.navigate_to_chapter(r)
                    )
                self.call_after_refresh(sidebar.focus)
            else:
                sidebar.add_class("hidden")
                self.call_after_refresh(
                    lambda: self.query_one("#scripture-pane", ScripturePane).focus()
                )
        except Exception:
            pass

    def action_search(self) -> None:
        def on_result(verse_ref: str | None) -> None:
            if verse_ref:
                self._navigate_to_verse(verse_ref)

        self.app.push_screen(SearchScreen(self.conn), on_result)

    def action_notes(self) -> None:
        self.app.push_screen(MyNotesScreen(self.conn))

    def action_lectionary(self) -> None:
        ref = get_primary_reading(date.today())
        if ref:
            self._navigate_to_verse(ref)

    def action_toggle_theme(self) -> None:
        screen = self.app.screen
        if screen.has_class("sepia"):
            screen.remove_class("sepia")
        else:
            screen.add_class("sepia")

    def action_quit_app(self) -> None:
        def _on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.app.exit()

        self.app.push_screen(QuitModal(), _on_confirm)

    def action_focus_scripture(self) -> None:
        try:
            self.query_one("#scripture-pane", ScripturePane).focus()
        except Exception:
            pass

    def action_focus_right(self) -> None:
        try:
            self.query_one("#right-pane", RightPane).focus()
        except Exception:
            pass

    def action_annotate(self, verse_ref: str) -> None:
        try:
            rp = self.query_one("#right-pane", RightPane)
            rp.focus_notes_editor()
        except Exception:
            pass

    def action_goto_reference(self) -> None:
        """Show goto-reference input dialog."""
        # Simple implementation: reuse search screen
        self.action_search()

    def _navigate_to_verse(self, verse_ref: str) -> None:
        """Navigate to a verse ref like 'GEN-1-1' or 'MAT-5-1'."""
        parts = verse_ref.split("-")
        if len(parts) < 2:
            return
        ch_ref = "-".join(parts[:2])
        if ch_ref != self._current_chapter_ref:
            self._load_chapter(ch_ref, focus_verse_ref=verse_ref)
        else:
            try:
                sp = self.query_one("#scripture-pane", ScripturePane)
                sp.focus_verse(verse_ref)
            except Exception:
                pass

    def show_daily_if_needed(self) -> None:
        """Show the daily lectionary overlay if this is the first launch today."""
        last_date = queries.get_session(self.conn, "last_session_date", "")
        today_str = date.today().isoformat()
        if last_date != today_str:
            queries.set_session(self.conn, "last_session_date", today_str)
            verse_count = queries.get_verse_count(self.conn)
            if verse_count > 0:
                def on_result(verse_ref: str | None) -> None:
                    if verse_ref:
                        self._navigate_to_verse(verse_ref)

                self.app.push_screen(DailyScreen(), on_result)
