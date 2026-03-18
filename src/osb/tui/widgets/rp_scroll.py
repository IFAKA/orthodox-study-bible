"""Scrolling utilities for RightPane."""

from textual.containers import VerticalScroll
from textual.widgets import ListView, Markdown, TabbedContent


def scroll_active(pane, down: bool) -> None:
    """Scroll the active tab up or down."""
    method = "scroll_down" if down else "scroll_up"
    try:
        active = pane.query_one("#right-tabs", TabbedContent).active
        if active == "tab-chat":
            getattr(pane.query_one("#chat-history", VerticalScroll), method)(animate=True, easing="out_cubic")
        elif active == "tab-commentary":
            getattr(pane.query_one("#commentary-text", Markdown), method)(animate=True, easing="out_cubic")
        elif active == "tab-collections":
            lv = pane.query_one("#collections-list", ListView)
            lv.action_cursor_down() if down else lv.action_cursor_up()
    except Exception:
        pass


def scroll_active_edge(pane, end: bool) -> None:
    """Scroll to start (end=False) or end (end=True) of active pane."""
    method = "scroll_end" if end else "scroll_home"
    try:
        active = pane.query_one("#right-tabs", TabbedContent).active
        if active == "tab-chat":
            getattr(pane.query_one("#chat-history", VerticalScroll), method)(animate=True)
        elif active == "tab-commentary":
            getattr(pane.query_one("#commentary-text", Markdown), method)(animate=True)
    except Exception:
        pass


def scroll_to_percentage(pane, percent: int) -> None:
    """Scroll to N% through the active pane (1-100)."""
    percent = max(1, min(percent, 100))
    try:
        active = pane.query_one("#right-tabs", TabbedContent).active
        if active == "tab-chat":
            widget = pane.query_one("#chat-history", VerticalScroll)
        elif active == "tab-commentary":
            widget = pane.query_one("#commentary-text", Markdown)
        else:
            return

        scrollable_region = widget.scrollable_content_region
        if scrollable_region.height > 0:
            max_scroll = max(0, scrollable_region.height - widget.container_size.height)
            target_y = int(max_scroll * percent / 100)
            widget.scroll_to(0, target_y, animate=True, duration=0.3, easing="out_cubic")
    except Exception:
        pass
