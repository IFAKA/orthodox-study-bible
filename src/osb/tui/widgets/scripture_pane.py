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
from osb.db.queries import get_annotated_verse_refs_for_chapter, get_bookmarked_verse_refs_for_chapter
from osb.tui.mixins.chord_handler import ChordMixin
from osb.tui.widgets.verse_block import VerseBlock


class ScripturePane(ChordMixin, Widget):
    """Left pane rendering chapter verses with keyboard navigation.

    Emits VerseFocused when the focused verse changes.
    """

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
        def __init__(self, direction: int) -> None:  # +1 or -1
            super().__init__()
            self.direction = direction

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
        # Remove only VerseBlocks so the search bar is preserved
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

        blocks: list[VerseBlock] = []
        for v in verses:
            block = VerseBlock(
                verse_ref=v.ref,
                verse_num=v.number,
                text=v.text,
                id=f"vb-{v.ref}",
            )
            block.update_state(
                highlight_color=highlights.get(v.ref),
                has_annotation=v.ref in annotations,
                has_bookmark=v.ref in bookmarks_set,
            )
            self._verse_refs.append(v.ref)
            self._blocks[v.ref] = block
            blocks.append(block)

        if blocks:
            self.mount(*blocks)

        if focus_verse_ref and focus_verse_ref in self._blocks:
            idx = self._verse_refs.index(focus_verse_ref)
            self._set_focus_idx(idx)
        elif self._verse_refs:
            self._set_focus_idx(0)

    @property
    def focused_verse_ref(self) -> str | None:
        if self._verse_refs and 0 <= self._focused_idx < len(self._verse_refs):
            return self._verse_refs[self._focused_idx]
        return None

    def focus_verse(self, verse_ref: str) -> None:
        if verse_ref in self._blocks:
            idx = self._verse_refs.index(verse_ref)
            self._set_focus_idx(idx)

    # ── Keyboard handling ─────────────────────────────────────────────────────

    def on_focus(self) -> None:
        self.add_class("active-pane")

    def on_blur(self) -> None:
        self.remove_class("active-pane")

    def on_key(self, event) -> None:
        if event.key == "escape" and self._search_mode:
            self._clear_search()
            event.stop()
            return
        if self._search_mode and not self._is_search_focused():
            if event.key == "n":
                self._next_match()
                event.stop()
                return
            elif event.key == "N":
                self._prev_match()
                event.stop()
                return
        if self.handle_chord(event):
            return

    def action_next_verse(self) -> None:
        if self._focused_idx < len(self._verse_refs) - 1:
            self._set_focus_idx(self._focused_idx + 1)
        else:
            self.post_message(self.ChapterChangeRequested(+1))

    def action_prev_verse(self) -> None:
        if self._focused_idx > 0:
            self._set_focus_idx(self._focused_idx - 1)
        else:
            self.post_message(self.ChapterChangeRequested(-1))

    def action_next_chapter(self) -> None:
        self.post_message(self.ChapterChangeRequested(+1))

    def action_prev_chapter(self) -> None:
        self.post_message(self.ChapterChangeRequested(-1))

    def action_goto_first_verse(self) -> None:
        if self._verse_refs:
            self._set_focus_idx(0)

    def action_last_verse(self) -> None:
        if self._verse_refs:
            self._set_focus_idx(len(self._verse_refs) - 1)

    def action_goto_reference(self) -> None:
        self.screen.action_goto_reference()

    def action_page_down(self) -> None:
        self.scroll_page_down()

    def action_half_page_down(self) -> None:
        self.scroll_down(self.size.height // 2)

    def action_half_page_up(self) -> None:
        self.scroll_up(self.size.height // 2)

    def action_annotate(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            self.app.screen.action_annotate(ref)

    def action_cycle_highlight(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            new_color = queries.cycle_highlight(self.conn, ref)
            block = self._blocks.get(ref)
            if block:
                block.highlight_color = new_color

    def action_bookmark(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            added = queries.toggle_bookmark(self.conn, ref)
            block = self._blocks.get(ref)
            if block:
                block.has_bookmark = added

    def action_start_search(self) -> None:
        self._search_mode = True
        try:
            self.query_one("#sp-search-bar").remove_class("hidden")
            self.call_after_refresh(lambda: self.query_one("#sp-search-input", Input).focus())
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "sp-search-input":
            self._apply_search_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "sp-search-input":
            if self._match_refs:
                self._match_idx = 0
                self._set_focus_idx(self._verse_refs.index(self._match_refs[0]))
            self.focus()

    def _is_search_focused(self) -> bool:
        try:
            return self.query_one("#sp-search-input", Input).has_focus
        except Exception:
            return False

    def _apply_search_filter(self, query: str) -> None:
        from rich.text import Text
        from textual.widgets import Label as TLabel
        self._match_refs = []
        if not query:
            for ref, block in self._blocks.items():
                block.remove_class("search-match")
                block.remove_class("search-dim")
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(block.verse_text)
                except Exception:
                    pass
            return
        q = query.lower()
        for ref, block in self._blocks.items():
            text = block.verse_text
            if q in text.lower():
                # Build Rich text with highlighted matches
                rich = Text()
                lower_text = text.lower()
                pos = 0
                while True:
                    idx = lower_text.find(q, pos)
                    if idx == -1:
                        rich.append(text[pos:])
                        break
                    rich.append(text[pos:idx])
                    rich.append(text[idx:idx + len(q)], style="bold yellow on #3a3000")
                    pos = idx + len(q)
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(rich)
                except Exception:
                    pass
                block.add_class("search-match")
                block.remove_class("search-dim")
                self._match_refs.append(ref)
            else:
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(text)
                except Exception:
                    pass
                block.remove_class("search-match")
                block.add_class("search-dim")
        self._match_idx = 0

    def _next_match(self) -> None:
        if not self._match_refs:
            return
        self._match_idx = (self._match_idx + 1) % len(self._match_refs)
        self._set_focus_idx(self._verse_refs.index(self._match_refs[self._match_idx]))

    def _prev_match(self) -> None:
        if not self._match_refs:
            return
        self._match_idx = (self._match_idx - 1) % len(self._match_refs)
        self._set_focus_idx(self._verse_refs.index(self._match_refs[self._match_idx]))

    def _clear_search(self) -> None:
        from textual.widgets import Label as TLabel
        self._search_mode = False
        self._match_refs = []
        self._match_idx = 0
        for ref, block in self._blocks.items():
            block.remove_class("search-match")
            block.remove_class("search-dim")
            try:
                block.query_one(f"#vtext-{ref}", TLabel).update(block.verse_text)
            except Exception:
                pass
        try:
            self.query_one("#sp-search-bar").add_class("hidden")
            self.query_one("#sp-search-input", Input).clear()
        except Exception:
            pass
        self.focus()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _set_focus_idx(self, idx: int) -> None:
        # Unfocus old
        if self._verse_refs and 0 <= self._focused_idx < len(self._verse_refs):
            old_ref = self._verse_refs[self._focused_idx]
            old_block = self._blocks.get(old_ref)
            if old_block:
                old_block.focused = False

        self._focused_idx = idx

        if self._verse_refs and 0 <= idx < len(self._verse_refs):
            new_ref = self._verse_refs[idx]
            new_block = self._blocks.get(new_ref)
            if new_block:
                new_block.focused = True
                new_block.scroll_visible()
            self.post_message(self.VerseFocused(new_ref))

    def refresh_verse_state(self, verse_ref: str) -> None:
        """Refresh a single verse block's decoration state."""
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
