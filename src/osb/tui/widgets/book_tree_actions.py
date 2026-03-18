"""Action handlers for BookTree._Tree widget."""

from osb.tui.widgets.book_tree_navigation import last_visible_node


class BookTreeActionsMixin:
    """Action methods for BookTree._Tree navigation."""

    def action_expand_or_select(self) -> None:
        """l/enter: expand node, or select chapter."""
        from osb.tui.widgets.book_tree import BookTree
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

    def action_goto_top(self) -> None:
        """g: jump to first item."""
        if self.root.children:
            first = self.root.children[0]
            self.select_node(first)
            self.scroll_to_node(first)

    def action_goto_bottom(self) -> None:
        """G: jump to last visible item."""
        last = last_visible_node(self.root)
        if last:
            self.select_node(last)
            self.scroll_to_node(last)

    def action_goto_first_verse(self) -> None:
        """gg: jump to first item (consumes vim count)."""
        self._consume_vim_count()
        self.action_goto_top()

    def action_last_verse(self) -> None:
        """G: jump to last visible item (consumes vim count)."""
        self._consume_vim_count()
        self.action_goto_bottom()

    def action_close_sidebar(self) -> None:
        """q: close sidebar."""
        try:
            self.screen.action_toggle_sidebar()
        except Exception:
            pass
