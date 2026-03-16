"""QuitModal — confirmation dialog before exiting the app."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitModal(ModalScreen[bool]):
    """Ask the user to confirm before quitting.

    Returns True if the user confirms, False (or None) to cancel.
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n,escape", "cancel", "No"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-dialog"):
            yield Label("Quit Orthodox Study Bible?", id="quit-title")
            yield Label("Any unsaved changes will be lost.", id="quit-body")
            with Horizontal(id="quit-buttons"):
                yield Button("Yes, quit  [y]", id="quit-yes", variant="error")
                yield Button("Cancel  [n]", id="quit-no", variant="default")

    def on_mount(self) -> None:
        self.query_one("#quit-no", Button).focus()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-yes":
            self.action_confirm()
        elif event.button.id == "quit-no":
            self.action_cancel()
