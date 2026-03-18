"""Action handlers for MainScreen."""

from datetime import date

from osb.db import queries
from osb.tui.screens.main_screen_commands import handle_command
from osb.importer.lectionary import get_primary_feast
from osb.tui.screens.daily_screen import DailyScreen
from osb.tui.screens.glossary_screen import GlossaryScreen
from osb.tui.screens.help_screen import HelpScreen
from osb.tui.screens.my_notes_screen import MyNotesScreen
from osb.tui.screens.progress_screen import ProgressScreen
from osb.tui.screens.search_screen import SearchScreen
from osb.tui.widgets.book_tree import BookTree
from osb.tui.widgets.quit_modal import QuitModal
from osb.tui.widgets.right_pane import RightPane
from osb.tui.widgets.scripture_pane import ScripturePane
from osb.tui.widgets.status_bar import StatusBar


class MainScreenActionsMixin:
    """Action handlers for MainScreen."""

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
        context = self._get_focus_context()
        title, text = self._build_context_help(context)
        self.app.push_screen(HelpScreen(title, text))

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

    def _handle_command(self, cmd: str) -> None:
        """Dispatch a colon command. Supported: q, and verse refs like 'Gen 3:5'."""
        handle_command(self, cmd)

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
