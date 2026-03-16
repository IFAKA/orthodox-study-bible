"""Common Header widget for all screens."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Label, Static


class AppHeader(Static):
    """Header widget with title and optional lectionary info."""

    def __init__(self, title: str = "Orthodox Study Bible", **kwargs) -> None:
        super().__init__(id="app-header", **kwargs)
        self.title_text = title

    def compose(self) -> ComposeResult:
        yield Label(self.title_text, id="header-title")
        yield Label("", id="header-lectionary")

    def update_title(self, title: str) -> None:
        self.title_text = title
        try:
            self.query_one("#header-title", Label).update(title)
        except Exception:
            pass

    def update_lectionary(self, info: str) -> None:
        try:
            self.query_one("#header-lectionary", Label).update(info)
        except Exception:
            pass
