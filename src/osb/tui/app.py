"""OrthodoxStudyApp — Textual root application."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from textual.app import App, ComposeResult

from osb.tui.screens.download_screen import DownloadScreen
from osb.tui.screens.import_screen import ImportScreen
from osb.tui.screens.main_screen import MainScreen
from osb.tui.screens.splash_screen import SplashScreen


class OrthodoxStudyApp(App):
    """Root Textual application for the Orthodox Study Bible reader."""

    CSS_PATH = [
        Path(__file__).parent / "styles" / "main.tcss",
        Path(__file__).parent / "styles" / "themes.tcss",
    ]
    TITLE = "Orthodox Study Bible"

    def __init__(self, conn: sqlite3.Connection, epub_path: Path | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self.epub_path = epub_path

    def on_mount(self) -> None:
        self.push_screen(SplashScreen(), self._after_splash)

    def _after_splash(self, _result=None) -> None:
        from osb.db.queries import get_verse_count

        verse_count = get_verse_count(self.conn)
        if verse_count == 0:
            if self.epub_path and self.epub_path.exists():
                self.push_screen(ImportScreen(self.conn, self.epub_path))
            else:
                self.push_screen(DownloadScreen(self.conn))
        else:
            self._show_main()

    def _show_main(self) -> None:
        main = MainScreen(self.conn)
        self.push_screen(main)
        # Show daily lectionary overlay if first launch today
        self.call_after_refresh(main.show_daily_if_needed)

    def on_import_screen_import_complete(self, event: ImportScreen.ImportComplete) -> None:
        # Pop the import screen and show main
        self.pop_screen()
        self._show_main()

    def on_download_screen_download_complete(self, _event: DownloadScreen.DownloadComplete) -> None:
        from osb.config import DB_PATH
        from osb.db.migrations import run_migrations
        from osb.db.schema import open_db

        self.pop_screen()
        self.conn = open_db(DB_PATH)
        run_migrations(self.conn)
        self._show_main()

