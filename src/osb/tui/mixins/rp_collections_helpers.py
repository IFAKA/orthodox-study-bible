"""Helper utilities for collections handling."""

from textual.widgets import ListItem, ListView


def get_current_item(right_pane) -> ListItem | None:
    """Get the currently highlighted list item from collections-list."""
    try:
        return right_pane.query_one("#collections-list", ListView).highlighted_child
    except Exception:
        return None


def get_current_index(right_pane) -> int:
    """Get the current index in the collections-list."""
    try:
        return right_pane.query_one("#collections-list", ListView).index or 0
    except Exception:
        return 0


def set_list_index(right_pane, index: int) -> None:
    """Set the index in the collections-list, clamping to valid range."""
    try:
        lv = right_pane.query_one("#collections-list", ListView)
        children = list(lv.children)
        if children:
            lv.index = max(0, min(index, len(children) - 1))
    except Exception:
        pass
