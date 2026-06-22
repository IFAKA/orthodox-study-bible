"""Daily lectionary overlay — calendar picker + readings from orthocal.info."""

from __future__ import annotations

import sqlite3
import threading
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView

from osb.db import queries
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

    def __init__(self, current: str = "gregorian", first_run: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current = current if current in _CAL_LABELS else "gregorian"
        self._first_run = first_run

    def compose(self) -> ComposeResult:
        title = (
            "Welcome — which calendar does your parish follow?"
            if self._first_run
            else "Daily Readings — choose calendar"
        )
        with Vertical(id="calendar-dialog", classes="modal-dialog"):
            yield Label(title, classes="modal-title")
            yield Label(
                "Sets which fixed-feast commemorations are shown. "
                "You can change this any time with [b]L[/].",
                id="calendar-subtitle",
            )
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


class DailyScreen(ModalScreen[list | None]):
    """Daily lectionary readings for a chosen calendar and date.

    Readings are fetched (and cached) from orthocal.info on a worker thread.
    The user can step between days, switch calendar, and pick a reading to
    open. Dismisses with the selected reading's verse refs, or None.
    """

    BINDINGS = [
        Binding("escape,q", "dismiss_none", "Close"),
        Binding("left,[", "prev_day", "Prev day"),
        Binding("right,]", "next_day", "Next day"),
        Binding("c", "toggle_calendar", "Calendar"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, calendar: str = "gregorian", **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self.calendar = calendar if calendar in _CAL_LABELS else "gregorian"
        self._date = date.today()
        self._readings: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="daily-dialog", classes="modal-dialog"):
            yield Label("", id="daily-title", classes="modal-title")
            yield Label("", id="daily-meta")
            yield ListView(id="daily-readings-list")
            yield Label(
                "[dim]\\[ ] prev/next day · c: calendar · j/k: move · enter: open · q: close[/]",
                id="daily-hint",
            )

    def on_mount(self) -> None:
        self._reload()

    # ── Loading / rendering ───────────────────────────────────────────────────

    def _reload(self) -> None:
        self._set_title()
        try:
            self.query_one("#daily-readings-list", ListView).clear()
            self.query_one("#daily-meta", Label).update("⟳ Loading…")
        except Exception:
            pass
        day, calendar = self._date, self.calendar
        threading.Thread(
            target=self._load_worker, args=(day, calendar), daemon=True
        ).start()

    def _load_worker(self, day: date, calendar: str) -> None:
        data = lectionary.get_readings(self.conn, day, calendar)
        self.app.call_from_thread(self._render_readings, day, calendar, data)

    def _set_title(self) -> None:
        try:
            label = self.query_one("#daily-title", Label)
        except Exception:
            return
        when = self._date.strftime("%A, %B %-d, %Y")
        suffix = " · Today" if self._date == date.today() else ""
        label.update(f"{when}  ·  {_CAL_LABELS[self.calendar]}{suffix}")

    def _render_readings(self, day: date, calendar: str, data: dict | None) -> None:
        # Ignore results that arrive after the user moved on.
        if day != self._date or calendar != self.calendar:
            return
        try:
            meta = self.query_one("#daily-meta", Label)
            lv = self.query_one("#daily-readings-list", ListView)
        except Exception:
            return

        lv.clear()
        self._readings = []

        if data is None:
            meta.update(
                "[dim]Couldn't load — connect once to cache this day, then it "
                "works offline.[/]"
            )
            return

        title = data.get("title") or ""
        fast = " · ".join(p for p in (data.get("fast"), data.get("fast_note")) if p)
        meta.update(f"[bold]{title}[/]" + (f"\n[dim]Fast: {fast}[/]" if fast else ""))

        readings = [r for r in (data.get("readings") or []) if (r.get("refs") or r.get("ref"))]
        self._readings = readings
        if not readings:
            meta.update(f"[bold]{title}[/]\n[dim]No appointed readings for this day.[/]")
            return

        for r in readings:
            source = r.get("source") or "Reading"
            display = r.get("display") or ""
            lv.append(ListItem(Label(f"[bold]{source}:[/] {display}")))
        lv.index = 0
        lv.focus()

    # ── Reading selection ─────────────────────────────────────────────────────

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._open_index(event.list_view.index)

    def _open_index(self, idx: int | None) -> None:
        if idx is None or not (0 <= idx < len(self._readings)):
            return
        r = self._readings[idx]
        refs = r.get("refs") or ([r["ref"]] if r.get("ref") else [])
        if refs:
            self.dismiss(refs)

    # ── Navigation ────────────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#daily-readings-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#daily-readings-list", ListView).action_cursor_up()

    def action_prev_day(self) -> None:
        self._date -= timedelta(days=1)
        self._reload()

    def action_next_day(self) -> None:
        self._date += timedelta(days=1)
        self._reload()

    def action_toggle_calendar(self) -> None:
        self.calendar = "julian" if self.calendar == "gregorian" else "gregorian"
        queries.set_session(self.conn, "lectionary_calendar", self.calendar)
        self._reload()

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
