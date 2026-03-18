"""Navigation utilities for BookTree._Tree."""

from textual.widgets.tree import TreeNode


def last_visible_node(root: TreeNode) -> TreeNode | None:
    """Return the deepest last-child in the currently expanded tree."""
    def _walk(node: TreeNode) -> TreeNode:
        if node.is_expanded and node.children:
            return _walk(list(node.children)[-1])
        return node

    children = list(root.children)
    if children:
        return _walk(children[-1])
    return None


def navigate_to_chapter(tree, chapter_ref: str, root: TreeNode, load_chapters_fn) -> None:
    """Expand the tree to chapter_ref and select it."""
    book_ref = chapter_ref.split("-")[0]
    for testament_node in root.children:
        for book_node in testament_node.children:
            if book_node.data and book_node.data.get("ref") == book_ref:
                if not book_node.data.get("loaded"):
                    load_chapters_fn(book_node, book_ref)
                    book_node.data["loaded"] = True
                testament_node.expand()
                book_node.expand()
                tree.call_after_refresh(
                    lambda ref=chapter_ref: tree.highlight_chapter(ref)
                )
                return


def navigate_to_book(tree, book_ref: str, root: TreeNode) -> None:
    """Select and scroll to the book node, expand it."""
    for testament_node in root.children:
        for book_node in testament_node.children:
            if book_node.data and book_node.data.get("ref") == book_ref:
                testament_node.expand()

                def _select(n: TreeNode = book_node) -> None:
                    tree.select_node(n)
                    tree.scroll_to_node(n)
                    n.expand()

                tree.call_after_refresh(_select)
                return


def highlight_chapter(tree, chapter_nodes: dict, chapter_ref: str) -> None:
    """Scroll to and select the node for the given chapter."""
    node = chapter_nodes.get(chapter_ref)
    if node:
        tree.select_node(node)
        tree.scroll_to_node(node)


def mark_chapter_chat(chapter_nodes: dict, chapters_with_chat: set, chapter_ref: str, has_chat: bool) -> None:
    """Add or remove the ◆ chat indicator on a chapter node."""
    node = chapter_nodes.get(chapter_ref)
    if not node:
        return
    if has_chat:
        chapters_with_chat.add(chapter_ref)
    else:
        chapters_with_chat.discard(chapter_ref)
    data = node.data
    if data:
        base = data.get("base_label", data["ref"])
        node.set_label(base + (" ◆" if has_chat else ""))
