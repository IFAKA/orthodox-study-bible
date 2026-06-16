"""Daily lectionary overlay — calendar picker + readings from orthocal.info."""

from __future__ import annotations

import sqlite3
import threading
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from osb.importer import lectionary

_CAL_LABELS = {"gregorian": "New Calendar", "julian": "Old Calendar (Julian)"}


class CalendarSelectModal(ModalScreen[str | None]):
    """Pick which calendar to use before showing the daily readings.

    Dismisses with "gregorian", "julian", or None if cancelled.
    """

    BINDINGS = [
        Binding("escape,q", "dismiss_none", "Cancel"),
        Binding("n", "pick_gregorian", "New Calendar"),
        Binding("j", "pick_julian", "Julian"),
    ]

    def __init__(self, current: str = "gregorian", **kwargs) -> None:
        super().__init__(**kwargs)
        self._current = current if current in _CAL_LABELS else "gregorian"

    def compose(self) -> ComposeResult:
        with Vertical(id="calendar-dialog", classes="modal-dialog"):
            yield Label("Daily Readings — choose calendar", classes="modal-title")
            with Horizontal(id="calendar-buttons"):
                yield Button("New Calendar  [n]", id="cal-gregorian", variant="primary")
                yield Button("Julian  [j]", id="cal-julian")

    def on_mount(self) -> None:
        # Focus the user's last choice so Enter repeats it.
        btn_id = "cal-julian" if self._current == "julian" else "cal-gregorian"
        try:
            self.query_one(f"#{btn_id}", Button).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss("julian" if event.button.id == "cal-julian" else "gregorian")

    def action_pick_gregorian(self) -> None:
        self.dismiss("gregorian")

    def action_pick_julian(self) -> None:
        self.dismiss("julian")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)


class DailyScreen(ModalScreen[str | None]):
    """Shows today's lectionary readings for the chosen calendar.

    Readings are fetched (and cached) from orthocal.info on a worker thread.
    Dismisses with a verse_ref to navigate to, or None to stay put.
    """

    BINDINGS = [
        Binding("escape,q", "dismiss_none", "Close"),
        Binding("g", "goto", "Go to first reading"),
    ]

    def __init__(self, conn: sqlite3.Connection, calendar: str = "gregorian", **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self.calendar = calendar if calendar in _CAL_LABELS else "gregorian"
        self._goto_ref: str | None = None

    def compose(self) -> ComposeResult:
        today = date.today().strftime("%A, %B %-d")
        cal_label = _CAL_LABELS[self.calendar]
        with Vertical(id="daily-dialog", classes="modal-dialog"):
            yield Label(f"Today's Readings — {today}  ·  {cal_label}",
                        id="daily-title", classes="modal-title")
            yield Label("⟳ Loading readings…", id="daily-readings")
            with Horizontal(id="daily-buttons"):
                yield Button("Go to first reading  [g]", id="goto-btn", variant="primary")
                yield Button("Close  [q]", id="close-btn")

    def on_mount(self) -> None:
        # Disable goto until we know there's something to go to.
        try:
            self.query_one("#goto-btn", Button).disabled = True
            self.query_one("#close-btn", Button).focus()
        except Exception:
            pass
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        data = lectionary.get_readings(self.conn, date.today(), self.calendar)
        self.app.call_from_thread(self._render_readings, data)

    def _render_readings(self, data: dict | None) -> None:
        try:
            label = self.query_one("#daily-readings", Label)
            goto_btn = self.query_one("#goto-btn", Button)
        except Exception:
            return

        if data is None:
            label.update(
                "Couldn't load today's readings.\n"
                "[dim]Connect to the internet once to cache them, then they "
                "work offline.[/]"
            )
            return

        readings = data.get("readings") or []
        lines: list[str] = []

        title = data.get("title")
        if title:
            lines.append(f"[bold]{title}[/]")

        fast = data.get("fast") or ""
        fast_note = data.get("fast_note") or ""
        fast_line = " · ".join(part for part in (fast, fast_note) if part)
        if fast_line:
            lines.append(f"[dim]Fast: {fast_line}[/]")

        if readings:
            if lines:
                lines.append("")
            for r in readings:
                source = r.get("source") or "Reading"
                display = r.get("display") or ""
                lines.append(f"[bold]{source}:[/] {display}")
            # First reading with a navigable ref becomes the goto target.
            self._goto_ref = next((r["ref"] for r in readings if r.get("ref")), None)
        else:
            lines.append("")
            lines.append("No appointed readings for today.")

        label.update("\n".join(lines))

        if self._goto_ref:
            goto_btn.disabled = False
            goto_btn.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "goto-btn":
            self.action_goto()
        else:
            self.dismiss(None)

    def action_goto(self) -> None:
        if self._goto_ref:
            self.dismiss(self._goto_ref)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
