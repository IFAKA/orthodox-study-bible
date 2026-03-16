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
        Binding("j", "cursor_down", "↓", show=True),
        Binding("k", "cursor_up", "↑", show=True),
        Binding("l", "expand_or_select", "Open", show=True),
        Binding("h", "collapse_or_parent", "Back", show=True),
        Binding("enter", "expand_or_select", "Select", show=False),
        Binding("space", "toggle_node", "Toggle", show=False),
        Binding("o", "toggle_node", "Toggle", show=False),
        Binding("g", "goto_top", "Top", show=True),
        Binding("G", "goto_bottom", "Bottom", show=True),
        Binding("escape", "close_sidebar", "Close", show=True),
        Binding("q", "close_sidebar", "Close", show=False),
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

    def action_expand_or_select(self) -> None:
        """l/enter: expand node, or select chapter."""
        node = self.cursor_node
        if node is None:
            return
        data = node.data
        if data and data.get("type") == "chapter":
            self.post_message(self.ChapterSelected(data["ref"]))
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
        """Expand the tree to chapter_ref and select it (open at current position)."""
        book_ref = chapter_ref.split("-")[0]
        for testament_node in self.root.children:
            for book_node in testament_node.children:
                if book_node.data and book_node.data.get("ref") == book_ref:
                    # Load chapters directly if not yet lazy-loaded
                    if not book_node.data.get("loaded"):
                        self._load_chapters(book_node, book_ref)
                        book_node.data["loaded"] = True
                    testament_node.expand()
                    book_node.expand()
                    # After layout refresh, select + scroll to the chapter node
                    self.call_after_refresh(
                        lambda ref=chapter_ref: self.highlight_chapter(ref)
                    )
                    return
