"""DailyScreen — startup lectionary overlay."""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from osb.importer.lectionary import get_daily_readings


class DailyScreen(ModalScreen[str | None]):
    """Shows today's lectionary readings on first launch of the day.

    Dismisses with verse_ref to navigate to, or None to stay at last position.
    """

    BINDINGS = [
        Binding("escape", "dismiss_none", "Close"),
        Binding("q", "dismiss_none", "Close"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._readings = get_daily_readings(date.today())

    def compose(self) -> ComposeResult:
        today = date.today().strftime("%A, %B %-d")
        yield Label(f"Today's Readings — {today}", id="daily-title")
        yield Label("", id="daily-readings")
        yield Button("Go to first reading", id="goto-btn", variant="primary")
        yield Button("Close", id="close-btn")

    def on_mount(self) -> None:
        label = self.query_one("#daily-readings", Label)
        if self._readings:
            lines = []
            for r in self._readings:
                lines.append(f"{r['service'].capitalize()}: {r['reading_ref']} ({r['source']})")
            label.update("\n".join(lines))
        else:
            label.update("No specific readings found for today.")
            try:
                btn = self.query_one("#goto-btn", Button)
                btn.disabled = True
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "goto-btn" and self._readings:
            self.dismiss(self._readings[0]["reading_ref"])
        else:
            self.dismiss(None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
