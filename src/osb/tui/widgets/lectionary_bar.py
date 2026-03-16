"""LectionaryBar — footer widget showing today's primary lectionary reading."""

from __future__ import annotations

from datetime import date

from textual.widget import Widget
from textual.widgets import Label

from osb.importer.lectionary import get_primary_reading


class LectionaryBar(Widget):
    """One-line footer showing today's lectionary reading ref."""

    DEFAULT_CSS = """
    LectionaryBar {
        height: 1;
        dock: bottom;
        layout: horizontal;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def compose(self):
        ref = get_primary_reading(date.today())
        if ref:
            yield Label(f"Today: {ref}", id="lectionary-label")
        else:
            yield Label("", id="lectionary-label")

    def get_reading_ref(self) -> str | None:
        return get_primary_reading(date.today())
