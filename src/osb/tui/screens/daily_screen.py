"""DailyScreen — startup lectionary overlay."""

from __future__ import annotations

import sqlite3
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from osb.importer.lectionary import get_daily_readings


class DailyScreen(ModalScreen[str | None]):
    """Shows today's lectionary readings on first launch of the day.

    Dismisses with verse_ref to navigate to, or None to stay at last position.
    """

    BINDINGS = [
        Binding("escape,q", "dismiss_none", "Close"),
        Binding("g", "goto", "Go to first reading"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._readings = get_daily_readings(date.today())

    def compose(self) -> ComposeResult:
        today = date.today().strftime("%A, %B %-d")
        with Vertical(id="daily-dialog", classes="modal-dialog"):
            yield Label(f"Today's Readings — {today}", id="daily-title", classes="modal-title")
            yield Label("", id="daily-readings")
            with Horizontal(id="daily-buttons"):
                yield Button("Go to first reading  [g]", id="goto-btn", variant="primary")
                yield Button("Close  [q]", id="close-btn")

    def on_mount(self) -> None:
        label = self.query_one("#daily-readings", Label)
        goto_btn = self.query_one("#goto-btn", Button)
        if self._readings:
            feast_names = {r["feast_name"] for r in self._readings if r.get("feast_name")}
            feast_line = f"  {' · '.join(sorted(feast_names))}\n" if feast_names else ""
            lines = [feast_line] if feast_line else []
            for r in self._readings:
                lines.append(f"{r['service'].capitalize()}: {r['reading_ref']} ({r['source']})")
            label.update("\n".join(lines))
            goto_btn.focus()
        else:
            label.update("No specific readings found for today.")
            goto_btn.disabled = True
            self.query_one("#close-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "goto-btn":
            self.action_goto()
        else:
            self.dismiss(None)

    def action_goto(self) -> None:
        if self._readings:
            self.dismiss(self._readings[0]["reading_ref"])

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
