"""MainScreen — 3-pane orchestrator."""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen

from osb.db import queries
from osb.importer.lectionary import get_primary_feast
from osb.tui.screens.help_screen import HelpScreen
from osb.tui.screens.main_screen_actions import MainScreenActionsMixin
from osb.tui.screens.main_screen_context import build_context_help, get_focus_context
from osb.tui.widgets.book_tree import BookTree
from osb.tui.widgets.right_pane import RightPane
from osb.tui.widgets.scripture_pane import ScripturePane
from osb.tui.widgets.status_bar import StatusBar


class MainScreen(MainScreenActionsMixin, Screen):
    """Primary 3-pane reading screen."""

    BINDINGS = [
        Binding("t", "toggle_sidebar", "Sidebar"),
        Binding("F", "search", "Search"),
        Binding("N", "notes", "Notes"),
        Binding("L", "lectionary", "Lectionary"),
        Binding("p", "progress", "Progress"),
        Binding("?", "help", "Help"),
        Binding("colon", "command_mode", show=False),
        Binding("q", "quit_app", "Quit"),
        Binding("T", "toggle_theme", "Theme", show=False),
        Binding("h", "focus_scripture", "Scripture", show=False),
        Binding("l", "toggle_right", "Commentary", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._sidebar_visible = False
        self._right_pane_visible: bool = False
        self._current_chapter_ref: str | None = None
        self._lectionary_str: str = ""
        self._vim_mode: str = "NORMAL"

    def compose(self) -> ComposeResult:
        # 3-pane horizontal layout
        with Horizontal(id="main-layout"):
            yield BookTree(self.conn, id="sidebar", classes="hidden")
            yield ScripturePane(self.conn, id="scripture-pane")
            yield RightPane(self.conn, id="right-pane", classes="hidden")

        yield StatusBar()

    def on_mount(self) -> None:
        self._restore_session()
        feast = get_primary_feast(date.today())
        if feast:
            ref, name = feast
            self._lectionary_str = f"Today: {name} · {ref}" if name else f"Today: {ref}"
        self._update_progress()
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

        try:
            sb = self.query_one(StatusBar)
            book_name_short = book_name.split()[0] if book_name else ""
            sb.update_ref(f"{book_name} {ch.number}")
        except Exception:
            pass

    def _update_progress(self) -> None:
        done, total = queries.get_total_progress(self.conn)
        try:
            sb = self.query_one(StatusBar)
            sb.update_progress(f"{done}/{total}")
        except Exception:
            pass

    # ── Navigation from BookTree ──────────────────────────────────────────────

    def on_book_tree_chapter_selected(self, event: BookTree.ChapterSelected) -> None:
        if event.chapter_ref != self._current_chapter_ref:
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

    def on_scripture_pane_chapter_completion_changed(
        self, event: ScripturePane.ChapterCompletionChanged
    ) -> None:
        self._update_header(event.chapter_ref)
        self._update_progress()


    def on_status_bar_command_submitted(self, event: StatusBar.CommandSubmitted) -> None:
        cmd = event.command.strip()
        self._vim_mode = "NORMAL"
        try:
            self.query_one(StatusBar).update_mode("NORMAL")
        except Exception:
            pass
        self._handle_command(cmd)

    def on_status_bar_command_cancelled(self, event: StatusBar.CommandCancelled) -> None:
        self._vim_mode = "NORMAL"
        try:
            self.query_one(StatusBar).update_mode("NORMAL")
        except Exception:
            pass
        self.query_one("#scripture-pane", ScripturePane).focus()

    def _get_focus_context(self) -> str:
        return get_focus_context(self.app)

    def _build_context_help(self, context: str) -> tuple[str, str]:
        return build_context_help(context, MainScreen.BINDINGS)
