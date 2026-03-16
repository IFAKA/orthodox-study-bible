"""VerseBlock widget — renders a single verse with highlight and annotation glyph."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class VerseBlock(Widget):
    """A single verse line in the ScripturePane.

    CSS classes added dynamically: focused, hl-yellow, hl-green, hl-blue, hl-pink
    """

    DEFAULT_CSS = """
    VerseBlock {
        layout: horizontal;
        height: auto;
    }
    """

    focused: reactive[bool] = reactive(False)
    highlight_color: reactive[str | None] = reactive(None)
    has_annotation: reactive[bool] = reactive(False)
    has_bookmark: reactive[bool] = reactive(False)

    def __init__(
        self,
        verse_ref: str,
        verse_num: int,
        text: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.verse_ref = verse_ref
        self.verse_num = verse_num
        self.verse_text = text

    def compose(self) -> ComposeResult:
        yield Label(f"{self.verse_num:>2} ", classes="verse-num", id=f"vnum-{self.verse_ref}")
        yield Label(self.verse_text, classes="verse-text", id=f"vtext-{self.verse_ref}")
        yield Label("", classes="verse-glyph", id=f"vglyph-{self.verse_ref}")

    def watch_focused(self, focused: bool) -> None:
        self.set_class(focused, "focused")

    def watch_highlight_color(self, color: str | None) -> None:
        for c in ["hl-yellow", "hl-green", "hl-blue", "hl-pink"]:
            self.remove_class(c)
        if color:
            self.add_class(f"hl-{color}")

    def watch_has_annotation(self, has: bool) -> None:
        self._update_glyph()

    def watch_has_bookmark(self, has: bool) -> None:
        self._update_glyph()

    def _update_glyph(self) -> None:
        glyph = ""
        if self.has_bookmark:
            glyph = "♦"
        elif self.has_annotation:
            glyph = "*"
        try:
            self.query_one(f"#vglyph-{self.verse_ref}", Label).update(glyph)
        except Exception:
            pass

    def update_state(
        self,
        highlight_color: str | None = None,
        has_annotation: bool = False,
        has_bookmark: bool = False,
    ) -> None:
        self.highlight_color = highlight_color
        self.has_annotation = has_annotation
        self.has_bookmark = has_bookmark
