"""MainScreen — 3-pane orchestrator."""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Input, Label

from osb.db import queries
from osb.importer.lectionary import get_primary_feast
from osb.tui.screens.daily_screen import DailyScreen
from osb.tui.screens.glossary_screen import GlossaryScreen
from osb.tui.screens.help_screen import HelpScreen
from osb.tui.screens.my_notes_screen import MyNotesScreen
from osb.tui.screens.progress_screen import ProgressScreen
from osb.tui.screens.search_screen import SearchScreen
from osb.tui.widgets.app_header import AppHeader
from osb.tui.widgets.book_tree import BookTree
from osb.tui.widgets.quit_modal import QuitModal
from osb.tui.widgets.right_pane import RightPane
from osb.tui.widgets.scripture_pane import ScripturePane
from osb.tui.widgets.status_bar import StatusBar


class MainScreen(Screen):
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
        yield AppHeader()

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
            header = self.query_one(AppHeader)
            header.update_title(f"{book_name} {ch.number}{complete_str}")
            header.update_lectionary(self._lectionary_str)
        except Exception:
            pass
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
        feast = get_primary_feast(date.today())
        if feast:
            self._navigate_to_verse(feast[0])

    def action_progress(self) -> None:
        def on_result(ref: str | None) -> None:
            if ref:
                self._navigate_to_verse(ref)

        self.app.push_screen(ProgressScreen(self.conn), on_result)

    def action_glossary(self) -> None:
        self.app.push_screen(GlossaryScreen(self.conn))

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_theme(self) -> None:
        screen = self.app.screen
        if screen.has_class("sepia"):
            screen.remove_class("sepia")
        else:
            screen.add_class("sepia")

    def action_quit_app(self) -> None:
        def _on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.app.fade_and_exit()

        self.app.push_screen(QuitModal(), _on_confirm)

    def action_focus_scripture(self) -> None:
        self._vim_mode = "NORMAL"
        try:
            self.query_one(StatusBar).update_mode("NORMAL")
        except Exception:
            pass
        try:
            self.query_one("#scripture-pane", ScripturePane).focus()
        except Exception:
            pass

    def action_toggle_right(self) -> None:
        rp = self.query_one("#right-pane", RightPane)
        self._right_pane_visible = not self._right_pane_visible
        if self._right_pane_visible:
            self._vim_mode = "RIGHT"
            try:
                self.query_one(StatusBar).update_mode("RIGHT")
            except Exception:
                pass
            rp.remove_class("hidden")
            rp.focus()
        else:
            self._vim_mode = "NORMAL"
            try:
                self.query_one(StatusBar).update_mode("NORMAL")
            except Exception:
                pass
            rp.add_class("hidden")
            self.query_one("#scripture-pane", ScripturePane).focus()

    def action_command_mode(self) -> None:
        self._vim_mode = "COMMAND"
        try:
            sb = self.query_one(StatusBar)
            sb.update_mode("COMMAND")
            sb.enter_command_mode()
        except Exception:
            pass

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

    def _handle_command(self, cmd: str) -> None:
        """Dispatch a colon command. Supported: q, and verse refs like 'Gen 3:5'."""
        if cmd == "q":
            self.action_quit_app()
            return

        # Try to parse as a verse reference: "Book Chapter:Verse" or "Book Chapter Verse"
        # Uses the same DB lookup as the search system
        import re
        # Pattern: optional book name, required chapter, optional verse
        # Examples: "Gen 3:5", "Genesis 3 5", "3:5" (current book), "Ps 50"
        match = re.match(
            r'^([1-3]?\s*[A-Za-z]+\.?\s*)?(\d+)(?:[:\s](\d+))?$',
            cmd.strip()
        )
        if match:
            book_part = (match.group(1) or "").strip().rstrip(".")
            chapter_num = int(match.group(2))
            verse_num = int(match.group(3)) if match.group(3) else 1

            if book_part:
                # Resolve book name to ref using DB
                from osb.db import queries as q
                books = q.get_all_books(self.conn)
                book_ref = None
                book_part_lower = book_part.lower()
                for book in books:
                    if (book.name.lower().startswith(book_part_lower) or
                            book.ref.lower().startswith(book_part_lower)):
                        book_ref = book.ref
                        break
                if book_ref is None:
                    self._status_error(f"Unknown book: {book_part}")
                    return
            else:
                # No book given — use current book
                if self._current_chapter_ref:
                    book_ref = self._current_chapter_ref.split("-")[0]
                else:
                    self._status_error("No current book")
                    return

            chapter_ref = f"{book_ref}-{chapter_num}"
            verse_ref = f"{book_ref}-{chapter_num}-{verse_num}"
            self._load_chapter(chapter_ref, focus_verse_ref=verse_ref)
            self.query_one("#scripture-pane", ScripturePane).focus()
        else:
            self._status_error(f"Unknown command: {cmd}")

    def _status_error(self, msg: str) -> None:
        """Flash an error message in the status bar ref area."""
        try:
            sb = self.query_one(StatusBar)
            sb.update_ref(f"[red]{msg}[/red]")
            self.set_timer(2.0, lambda: sb.update_ref(""))
        except Exception:
            pass

    def action_annotate(self, verse_ref: str) -> None:
        try:
            rp = self.query_one("#right-pane", RightPane)
            rp.focus_notes_editor()
        except Exception:
            pass

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
