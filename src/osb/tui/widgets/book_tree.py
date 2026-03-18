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

    class _Tree(ChordMixin, Tree):
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

        def action_expand_or_select(self) -> None:
            """l/enter: expand node, or select chapter."""
            node = self.cursor_node
            if node is None:
                return
            data = node.data
            if data and data.get("type") == "chapter":
                self.post_message(BookTree.ChapterSelected(data["ref"]))
            elif not node.is_expanded:
                node.expand()
            else:
                self.action_cursor_down()

        def action_collapse_or_parent(self) -> None:
            """h: collapse expanded node, or jump to parent."""
            node = self.cursor_node
            if node is None:
                return
            if node.is_expanded and node.children:
                node.collapse()
            elif node.parent and node.parent is not self.root:
                parent = node.parent
                self.select_node(parent)
                self.scroll_to_node(parent)

        def action_toggle_node(self) -> None:
            """space/o: toggle expand/collapse."""
            node = self.cursor_node
            if node is None:
                return
            if node.is_expanded:
                node.collapse()
            else:
                node.expand()

        def on_key(self, event) -> None:
            if self.handle_chord(event):
                return

        def _dispatch_single(self, key: str) -> None:
            """Single g with no second key → go to top (preserves old g behaviour)."""
            if key == "g":
                self.action_goto_top()

        def action_goto_first_verse(self) -> None:
            self.action_goto_top()

        def action_last_verse(self) -> None:
            self._consume_vim_count()  # count not meaningful in tree
            self.action_goto_bottom()

        def action_goto_top(self) -> None:
            """g: jump to first item."""
            if self.root.children:
                first = self.root.children[0]
                self.select_node(first)
                self.scroll_to_node(first)

        def action_goto_bottom(self) -> None:
            """G: jump to last visible item."""
            last = self._last_visible_node()
            if last:
                self.select_node(last)
                self.scroll_to_node(last)

        def _last_visible_node(self) -> TreeNode | None:
            """Return the deepest last-child in the currently expanded tree."""
            def _walk(node: TreeNode) -> TreeNode:
                if node.is_expanded and node.children:
                    return _walk(list(node.children)[-1])
                return node

            children = list(self.root.children)
            if children:
                return _walk(children[-1])
            return None

        def action_close_sidebar(self) -> None:
            try:
                self.screen.action_toggle_sidebar()
            except Exception:
                pass

        def mark_chapter_chat(self, chapter_ref: str, has_chat: bool) -> None:
            """Add or remove the ◆ chat indicator on a chapter node."""
            node = self._chapter_nodes.get(chapter_ref)
            if not node:
                return
            if has_chat:
                self._chapters_with_chat.add(chapter_ref)
            else:
                self._chapters_with_chat.discard(chapter_ref)
            data = node.data
            if data:
                base = data.get("base_label", data["ref"])
                node.set_label(base + (" ◆" if has_chat else ""))

        def highlight_chapter(self, chapter_ref: str) -> None:
            """Scroll to and select the node for the given chapter."""
            node = self._chapter_nodes.get(chapter_ref)
            if node:
                self.select_node(node)
                self.scroll_to_node(node)

        def navigate_to_chapter(self, chapter_ref: str) -> None:
            """Expand the tree to chapter_ref and select it."""
            book_ref = chapter_ref.split("-")[0]
            for testament_node in self.root.children:
                for book_node in testament_node.children:
                    if book_node.data and book_node.data.get("ref") == book_ref:
                        if not book_node.data.get("loaded"):
                            self._load_chapters(book_node, book_ref)
                            book_node.data["loaded"] = True
                        testament_node.expand()
                        book_node.expand()
                        self.call_after_refresh(
                            lambda ref=chapter_ref: self.highlight_chapter(ref)
                        )
                        return

        def navigate_to_book(self, book_ref: str) -> None:
            """Select and scroll to the book node, expand it."""
            for testament_node in self.root.children:
                for book_node in testament_node.children:
                    if book_node.data and book_node.data.get("ref") == book_ref:
                        testament_node.expand()

                        def _select(n: TreeNode = book_node) -> None:
                            self.select_node(n)
                            self.scroll_to_node(n)
                            n.expand()

                        self.call_after_refresh(_select)
                        return

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
