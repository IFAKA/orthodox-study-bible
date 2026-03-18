"""ScripturePane — main reading pane with keyboard navigation and verse focus."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label

from osb.db import queries
from osb.db.queries import (
    get_annotated_verse_refs_for_chapter,
    get_bookmarked_verse_refs_for_chapter,
    get_verse_refs_with_crossrefs_for_chapter,
)
from osb.tui.mixins.chord_handler import ChordMixin
from osb.tui.mixins.sp_navigation import SpNavigationMixin
from osb.tui.mixins.sp_search import SpSearchMixin
from osb.tui.mixins.sp_verse_actions import SpVerseActionsMixin
from osb.tui.widgets.verse_block import VerseBlock


class ScripturePane(ChordMixin, SpNavigationMixin, SpSearchMixin, SpVerseActionsMixin, Widget):
    """Left pane rendering chapter verses with keyboard navigation."""

    can_focus = True

    BINDINGS = [
        Binding("/", "start_search", "Find", show=True),
        Binding("j", "next_verse", "Next verse", show=True),
        Binding("k", "prev_verse", "Prev verse", show=True),
        Binding("J", "prev_chapter", "Prev chapter", show=True),
        Binding("K", "next_chapter", "Next chapter", show=True),
        Binding("b", "bookmark", "Bookmark", show=True),
        Binding("m", "cycle_highlight", "Highlight", show=True),
        Binding("o", "annotate", "Annotate", show=True),
        Binding("x", "crossrefs", "Cross-refs", show=True),
        Binding("y", "copy_verse", "Copy", show=True),
        Binding("C", "toggle_complete", "Complete", show=True),
        Binding("a", "add_to_collection", "Add to collection", show=False),
        Binding("G", "last_verse", "Last verse", show=False),
        Binding("space", "page_down", "Page down", show=False),
        Binding("ctrl+d", "half_page_down", "Half page", show=False),
        Binding("ctrl+u", "half_page_up", "Half page up", show=False),
    ]

    class VerseFocused(Message):
        def __init__(self, verse_ref: str) -> None:
            super().__init__()
            self.verse_ref = verse_ref

    class ChapterChangeRequested(Message):
        def __init__(self, direction: int) -> None:
            super().__init__()
            self.direction = direction

    class ChapterCompletionChanged(Message):
        def __init__(self, chapter_ref: str) -> None:
            super().__init__()
            self.chapter_ref = chapter_ref

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._chapter_ref: str | None = None
        self._verse_refs: list[str] = []
        self._focused_idx: int = 0
        self._blocks: dict[str, VerseBlock] = {}
        self._search_mode: bool = False
        self._match_refs: list[str] = []
        self._match_idx: int = 0
        self._accel_count: int = 0
        self._last_nav_time: float = 0.0
        self._last_nav_dir: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="sp-search-bar", classes="hidden"):
            yield Label("/", id="sp-search-prefix")
            yield Input(id="sp-search-input", placeholder="")
            yield Label("  n/N · Esc", id="sp-search-help")

    # ── Public API ────────────────────────────────────────────────────────────

    def load_chapter(self, chapter_ref: str, focus_verse_ref: str | None = None) -> None:
        self._chapter_ref = chapter_ref
        self._verse_refs = []
        self._blocks = {}
        self._focused_idx = 0
        for block in self.query(VerseBlock):
            block.remove()
        self._search_mode = False
        self._match_refs = []
        self._match_idx = 0
        try:
            self.query_one("#sp-search-bar").add_class("hidden")
            self.query_one("#sp-search-input", Input).clear()
        except Exception:
            pass
        self._render_chapter(focus_verse_ref)

    def _render_chapter(self, focus_verse_ref: str | None = None) -> None:
        if not self._chapter_ref:
            return
        verses = queries.get_verses_for_chapter(self.conn, self._chapter_ref)
        highlights = queries.get_highlights_for_chapter(self.conn, self._chapter_ref)
        annotations = get_annotated_verse_refs_for_chapter(self.conn, self._chapter_ref)
        bookmarks_set = get_bookmarked_verse_refs_for_chapter(self.conn, self._chapter_ref)
        crossrefs_set = get_verse_refs_with_crossrefs_for_chapter(self.conn, self._chapter_ref)

        blocks: list[VerseBlock] = []
        for v in verses:
            block = VerseBlock(verse_ref=v.ref, verse_num=v.number, text=v.text, id=f"vb-{v.ref}")
            block.update_state(
                highlight_color=highlights.get(v.ref),
                has_annotation=v.ref in annotations,
                has_bookmark=v.ref in bookmarks_set,
                has_crossref=v.ref in crossrefs_set,
            )
            self._verse_refs.append(v.ref)
            self._blocks[v.ref] = block
            blocks.append(block)

        if blocks:
            self.mount(*blocks)

        if focus_verse_ref and focus_verse_ref in self._blocks:
            self._set_focus_idx(self._verse_refs.index(focus_verse_ref))
        elif self._verse_refs:
            self._set_focus_idx(0)

    @property
    def focused_verse_ref(self) -> str | None:
        if self._verse_refs and 0 <= self._focused_idx < len(self._verse_refs):
            return self._verse_refs[self._focused_idx]
        return None

    def focus_verse(self, verse_ref: str) -> None:
        if verse_ref in self._blocks:
            self._set_focus_idx(self._verse_refs.index(verse_ref))

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def on_focus(self) -> None:
        self.add_class("active-pane")

    def on_blur(self) -> None:
        self.remove_class("active-pane")

    def on_key(self, event) -> None:
        if self._search_mode and not self._is_search_focused():
            if event.key in ("escape", "enter"):
                self._clear_search()
                event.stop()
                return
            if event.key == "n":
                self._next_match()
                event.stop()
                return
            elif event.key == "N":
                self._prev_match()
                event.stop()
                return
        if event.key == "escape" and self._search_mode:
            self._clear_search()
            event.stop()
            return
        if self.handle_chord(event):
            return

    def refresh_verse_state(self, verse_ref: str) -> None:
        block = self._blocks.get(verse_ref)
        if not block:
            return
        hl = queries.get_highlight(self.conn, verse_ref)
        ann = queries.get_annotation(self.conn, verse_ref)
        bm = queries.get_bookmark(self.conn, verse_ref)
        block.update_state(
            highlight_color=hl.color if hl else None,
            has_annotation=ann is not None,
            has_bookmark=bm is not None,
        )
