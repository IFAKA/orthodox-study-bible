"""AnnotationModal — modal screen for editing verse annotations."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


class AnnotationModal(ModalScreen[str | None]):
    """Modal for editing an annotation for a specific verse.

    Returns the new annotation text (str) on save, or None on cancel.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, verse_ref: str, existing_text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.verse_ref = verse_ref
        self.existing_text = existing_text

    def compose(self) -> ComposeResult:
        yield Label(f"Annotation: {self.verse_ref}", id="annotation-ref")
        yield TextArea(self.existing_text, id="annotation-editor", language="markdown")
        yield Label("Ctrl+S save · Esc cancel", id="annotation-help")

    def action_save(self) -> None:
        editor = self.query_one("#annotation-editor", TextArea)
        self.dismiss(editor.text)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
