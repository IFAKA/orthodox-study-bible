"""ImportScreen — first-run EPUB import with progress bar."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, ProgressBar

from osb.db.queries import get_verse_count
from osb.importer.epub_parser import ParseError, run_import
from osb.tui.widgets.app_header import AppHeader


class ImportScreen(Screen):
    """Full-screen import UI.

    Posts ImportComplete when done.
    """

    BINDINGS = [Binding("q", "quit_app", "Quit")]

    class ImportComplete(Message):
        def __init__(self, sha256: str, warnings: list[str]) -> None:
            super().__init__()
            self.sha256 = sha256
            self.warnings = warnings

    class ImportFailed(Message):
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    def __init__(self, conn: sqlite3.Connection, epub_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self.epub_path = epub_path

    def compose(self) -> ComposeResult:
        yield AppHeader(title="Orthodox Study Bible — Importing")
        with Vertical(id="import-dialog"):
            yield Label(f"Importing: {self.epub_path.name}", id="import-status")
            yield ProgressBar(total=100, id="import-progress", show_eta=False)
            yield Label("", id="import-warnings")
            yield Button("Cancel", id="cancel-btn", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self._start_import()
        self.query_one("#cancel-btn", Button).focus()

    def _start_import(self) -> None:
        def worker():
            def progress_cb(current: int, total: int, message: str) -> None:
                if total > 0:
                    pct = int(current / total * 100)
                    self.app.call_from_thread(self._update_progress, pct, message)

            try:
                sha256, warnings = run_import(
                    self.epub_path,
                    self.conn,
                    progress_cb=progress_cb,
                )
                from datetime import datetime
                self.conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                    ("epub_sha256", sha256),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                    ("import_date", datetime.now().isoformat()),
                )
                self.conn.commit()
                self.app.call_from_thread(
                    self.post_message,
                    self.ImportComplete(sha256, warnings),
                )
            except ParseError as e:
                self.app.call_from_thread(
                    self.post_message,
                    self.ImportFailed(str(e)),
                )
            except Exception as e:
                self.app.call_from_thread(
                    self.post_message,
                    self.ImportFailed(f"Unexpected error: {e}"),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, pct: int, message: str) -> None:
        try:
            bar = self.query_one("#import-progress", ProgressBar)
            bar.progress = pct
            status = self.query_one("#import-status", Label)
            status.update(message[:80])
        except Exception:
            pass

    def on_import_screen_import_complete(self, event: ImportComplete) -> None:
        try:
            bar = self.query_one("#import-progress", ProgressBar)
            bar.progress = 100
            warn_label = self.query_one("#import-warnings", Label)
            if event.warnings:
                warn_label.update("Warnings:\n" + "\n".join(event.warnings[:10]))
            else:
                warn_label.update("Import complete!")
        except Exception:
            pass
        self.app.post_message(event)

    def on_import_screen_import_failed(self, event: ImportFailed) -> None:
        try:
            status = self.query_one("#import-status", Label)
            status.update(f"ERROR: {event.error}")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.exit()

    def action_quit_app(self) -> None:
        self.app.exit()
