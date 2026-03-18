"""BookTree — sidebar tree widget for navigating books and chapters."""

from __future__ import annotations

import sqlite3
from textual.binding import Binding
from osb.tui.mixins.chord_handler import ChordMixin
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.app import ComposeResult
from textual.widget import Widget

from osb.db.queries import get_all_books, get_chapters_for_book, get_chapters_with_chat
from osb.tui.widgets.book_tree_navigation import (
    last_visible_node, navigate_to_chapter, navigate_to_book,
    highlight_chapter, mark_chapter_chat
)
from osb.tui.widgets.book_tree_actions import BookTreeActionsMixin


class BookTree(Widget):
    """Container widget: filter modal + inner Tree for book/chapter navigation."""

    can_focus = False

    BINDINGS = [
        Binding("slash", "open_search", show=False),
        Binding("escape", "handle_escape", show=False, priority=True),
    ]

    class ChapterSelected(Message):
        """Posted when user selects a chapter."""

        def __init__(self, chapter_ref: str) -> None:
            super().__init__()
            self.chapter_ref = chapter_ref

    class _Tree(BookTreeActionsMixin, ChordMixin, Tree):
        """Inner tree — all book/chapter navigation logic."""

        BINDINGS = [
            Binding("j", "cursor_down", "↓", show=False),
            Binding("k", "cursor_up", "↑", show=False),
            Binding("l", "expand_or_select", "Open", show=True),
            Binding("h", "collapse_or_parent", "Back", show=True),
            Binding("enter", "expand_or_select", "Select", show=False),
            Binding("space", "toggle_node", "Toggle", show=False),
            Binding("o", "toggle_node", "Toggle", show=False),
            Binding("G", "goto_bottom", "Bottom", show=True),
            Binding("q", "close_sidebar", "Close", show=False),
        ]

        def __init__(self, label: str, conn: sqlite3.Connection, **kwargs) -> None:
            super().__init__(label, **kwargs)
            self.conn = conn
            self._chapter_nodes: dict[str, TreeNode] = {}
            self._chapters_with_chat: set[str] = set()

        def on_mount(self) -> None:
            self._chapters_with_chat = get_chapters_with_chat(self.conn)
            self._load_books()

        def _load_books(self) -> None:
            books = get_all_books(self.conn)
            testament_nodes: dict[str, TreeNode] = {}

            for book in books:
                t = book.testament
                if t not in testament_nodes:
                    label = {"OT": "Old Testament", "NT": "New Testament", "DC": "Deuterocanon"}.get(t, t)
                    testament_nodes[t] = self.root.add(label, expand=False)

                testament_nodes[t].add(book.name, expand=False, data={"type": "book", "ref": book.ref})

            self.root.expand()

        def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
            node = event.node
            data = node.data
            if data and data.get("type") == "book" and not data.get("loaded"):
                self._load_chapters(node, data["ref"])
                data["loaded"] = True

        def _load_chapters(self, book_node: TreeNode, book_ref: str) -> None:
            chapters = get_chapters_for_book(self.conn, book_ref)
            for ch in chapters:
                base = f"Chapter {ch.number}"
                label = base + (" ◆" if ch.ref in self._chapters_with_chat else "")
                ch_node = book_node.add_leaf(
                    label,
                    data={"type": "chapter", "ref": ch.ref, "base_label": base},
                )
                self._chapter_nodes[ch.ref] = ch_node

        def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
            data = event.node.data
            if data and data.get("type") == "chapter":
                self.post_message(BookTree.ChapterSelected(data["ref"]))

        def on_key(self, event) -> None:
            if self.handle_chord(event):
                return

        def _dispatch_single(self, key: str) -> None:
            """Single g with no second key → go to top (preserves old g behaviour)."""
            if key == "g":
                self.action_goto_top()

        def mark_chapter_chat(self, chapter_ref: str, has_chat: bool) -> None:
            """Add or remove the ◆ chat indicator on a chapter node."""
            mark_chapter_chat(self._chapter_nodes, self._chapters_with_chat, chapter_ref, has_chat)

        def highlight_chapter(self, chapter_ref: str) -> None:
            """Scroll to and select the node for the given chapter."""
            highlight_chapter(self, self._chapter_nodes, chapter_ref)

        def navigate_to_chapter(self, chapter_ref: str) -> None:
            """Expand the tree to chapter_ref and select it."""
            navigate_to_chapter(self, chapter_ref, self.root, self._load_chapters)

        def navigate_to_book(self, book_ref: str) -> None:
            """Select and scroll to the book node, expand it."""
            navigate_to_book(self, book_ref, self.root)

    # ── BookTree public API ──────────────────────────────────────────

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn

    def compose(self) -> ComposeResult:
        yield BookTree._Tree("Books", self.conn)

    @property
    def _tree(self) -> _Tree:
        return self.query_one(BookTree._Tree)

    def focus(self, scroll_visible: bool = True) -> "BookTree":
        self._tree.focus(scroll_visible)
        return self

    # Delegation
    def navigate_to_chapter(self, chapter_ref: str) -> None:
        self._tree.navigate_to_chapter(chapter_ref)

    def mark_chapter_chat(self, chapter_ref: str, has_chat: bool) -> None:
        self._tree.mark_chapter_chat(chapter_ref, has_chat)

    # ── Search ───────────────────────────────────────────────────────

    def action_open_search(self) -> None:
        from osb.tui.screens.book_search_screen import BookSearchScreen

        def on_result(book_ref: str | None) -> None:
            if book_ref:
                self._tree.navigate_to_book(book_ref)
            self._tree.focus()

        self.app.push_screen(BookSearchScreen(self.conn), on_result)

    def action_handle_escape(self) -> None:
        try:
            self.screen.action_toggle_sidebar()
        except Exception:
            pass
