"""DownloadScreen — first-run DB download with progress bar."""

from __future__ import annotations

import gzip
import hashlib
import sqlite3
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, ProgressBar

from osb.config import DB_PATH, DB_RELEASE_SHA256, DB_RELEASE_URL
from osb.tui.widgets.app_header import AppHeader
from osb.tui.widgets.quit_modal import QuitModal


class DownloadScreen(Screen):
    """Full-screen DB download UI shown on first run (no EPUB, no local DB).

    Posts DownloadComplete when the DB has been placed at DB_PATH.
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
    ]

    class DownloadComplete(Message):
        pass

    class DownloadFailed(Message):
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn

    def compose(self) -> ComposeResult:
        yield AppHeader(title="Orthodox Study Bible — Setup")
        with Vertical(id="import-dialog"):
            yield Label("Setting up Orthodox Study Bible", id="import-status")
            yield ProgressBar(total=100, id="import-progress", show_eta=False)
            yield Label(
                "Downloading scripture database… This happens once.\n"
                "The app works fully offline after this.",
                id="import-warnings",
            )
            yield Button("Cancel", id="cancel-btn", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self._start_download()
        self.query_one("#cancel-btn", Button).focus()

    def _start_download(self) -> None:
        def worker() -> None:
            try:
                import httpx
            except ImportError:
                self.app.call_from_thread(
                    self.post_message,
                    self.DownloadFailed("httpx is not installed"),
                )
                return

            tmp_gz = DB_PATH.with_suffix(".db.gz.tmp")
            tmp_db = DB_PATH.with_suffix(".db.new")

            try:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)

                # --- Stream download ---
                self.app.call_from_thread(
                    self._update_progress, 0, "Connecting…"
                )
                with httpx.stream("GET", DB_RELEASE_URL, follow_redirects=True, timeout=60) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    h = hashlib.sha256()

                    with open(tmp_gz, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            h.update(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = min(int(downloaded / total * 95), 95)
                                mb_done = downloaded / 1024 / 1024
                                mb_total = total / 1024 / 1024
                                self.app.call_from_thread(
                                    self._update_progress,
                                    pct,
                                    f"Downloading… {mb_done:.1f} MB / {mb_total:.1f} MB",
                                )
                            else:
                                mb_done = downloaded / 1024 / 1024
                                self.app.call_from_thread(
                                    self._update_progress,
                                    0,
                                    f"Downloading… {mb_done:.1f} MB",
                                )

                # --- Integrity check ---
                digest = h.hexdigest()
                if DB_RELEASE_SHA256 and digest != DB_RELEASE_SHA256:
                    raise ValueError(
                        f"SHA256 mismatch.\nExpected: {DB_RELEASE_SHA256}\nGot:      {digest}"
                    )

                # --- Decompress ---
                self.app.call_from_thread(
                    self._update_progress, 96, "Decompressing…"
                )
                with gzip.open(tmp_gz, "rb") as f_in, open(tmp_db, "wb") as f_out:
                    while True:
                        block = f_in.read(65536)
                        if not block:
                            break
                        f_out.write(block)

                # --- Swap in the new DB ---
                self.app.call_from_thread(
                    self._update_progress, 99, "Finalizing…"
                )
                self.conn.close()
                if DB_PATH.exists():
                    DB_PATH.unlink()
                tmp_db.rename(DB_PATH)
                tmp_gz.unlink(missing_ok=True)

                self.app.call_from_thread(
                    self._update_progress, 100, "Complete!"
                )
                self.app.call_from_thread(
                    self.post_message, self.DownloadComplete()
                )

            except Exception as e:
                tmp_gz.unlink(missing_ok=True)
                tmp_db.unlink(missing_ok=True)
                self.app.call_from_thread(
                    self.post_message, self.DownloadFailed(str(e))
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

    def on_download_screen_download_complete(self, _event: DownloadComplete) -> None:
        try:
            bar = self.query_one("#import-progress", ProgressBar)
            bar.progress = 100
            label = self.query_one("#import-warnings", Label)
            label.update("Download complete! Opening…")
        except Exception:
            pass
        self.app.post_message(_event)

    def on_download_screen_download_failed(self, event: DownloadFailed) -> None:
        try:
            status = self.query_one("#import-status", Label)
            status.update(f"ERROR: {event.error}")
            btn = self.query_one("#cancel-btn", Button)
            btn.label = "Quit"
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.action_quit_app()

    def action_quit_app(self) -> None:
        def _on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.app.exit()

        self.app.push_screen(QuitModal(), _on_confirm)
