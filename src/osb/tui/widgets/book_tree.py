"""BookTree — sidebar tree widget for navigating books and chapters."""

from __future__ import annotations

import sqlite3
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from osb.db.queries import get_all_books, get_chapters_for_book, get_chapters_with_chat


class BookTree(Tree):
    """Tree widget listing Orthodox canon books with lazy chapter loading."""

    BINDINGS = [
        Binding("j", "cursor_down", "Next", show=False),
        Binding("k", "cursor_up", "Prev", show=False),
        Binding("escape", "close_sidebar", "Close", show=True),
    ]

    class ChapterSelected(Message):
        """Posted when user selects a chapter."""

        def __init__(self, chapter_ref: str) -> None:
            super().__init__()
            self.chapter_ref = chapter_ref

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__("Books", **kwargs)
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
            self.post_message(self.ChapterSelected(data["ref"]))

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
