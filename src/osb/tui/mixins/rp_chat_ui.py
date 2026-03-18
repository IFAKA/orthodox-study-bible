"""Chat input and notes editor widgets."""

from textual.binding import Binding
from textual.widgets import Input, TextArea


class _ChatInput(Input):
    """Chat message input widget."""

    BINDINGS = [Binding("enter", "submit", "Send", show=True)]


class _NotesEditor(TextArea):
    """Notes editor widget."""

    pass
