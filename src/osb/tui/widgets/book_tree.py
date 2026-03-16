"""BookTree — sidebar tree widget for navigating books and chapters."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from osb.db.queries import get_all_books, get_chapters_for_book

if TYPE_CHECKING:
    pass


class BookTree(Tree):
    """Tree widget listing Orthodox canon books with lazy chapter loading."""

    class ChapterSelected(Message):
        """Posted when user selects a chapter."""

        def __init__(self, chapter_ref: str) -> None:
            super().__init__()
            self.chapter_ref = chapter_ref

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__("Books", **kwargs)
        self.conn = conn
        self._chapter_nodes: dict[str, TreeNode] = {}
        self._book_nodes: dict[str, TreeNode] = {}

    def on_mount(self) -> None:
        self._load_books()

    def _load_books(self) -> None:
        books = get_all_books(self.conn)
        testament_nodes: dict[str, TreeNode] = {}

        for book in books:
            t = book.testament
            if t not in testament_nodes:
                label = {"OT": "Old Testament", "NT": "New Testament", "DC": "Deuterocanon"}.get(t, t)
                testament_nodes[t] = self.root.add(label, expand=False)

            node = testament_nodes[t].add(book.name, expand=False, data={"type": "book", "ref": book.ref})
            self._book_nodes[book.ref] = node

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
            ch_node = book_node.add_leaf(
                f"Chapter {ch.number}",
                data={"type": "chapter", "ref": ch.ref},
            )
            self._chapter_nodes[ch.ref] = ch_node

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if data and data.get("type") == "chapter":
            self.post_message(self.ChapterSelected(data["ref"]))

    def highlight_chapter(self, chapter_ref: str) -> None:
        """Scroll to and select the node for the given chapter."""
        node = self._chapter_nodes.get(chapter_ref)
        if node:
            self.select_node(node)
            self.scroll_to_node(node)
