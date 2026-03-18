"""Context-aware help building for MainScreen."""

from textual.binding import Binding

from osb.tui.screens.help_screen import build_help_text
from osb.tui.widgets.right_pane import RightPane
from osb.tui.widgets.scripture_pane import ScripturePane


def get_focus_context(app) -> str:
    """Determine current focus context (sidebar, right-pane, or scripture)."""
    node = app.focused
    while node is not None:
        nid = getattr(node, "id", None)
        if nid == "sidebar":
            return "sidebar"
        if nid == "right-pane":
            tabs = None
            try:
                tabs = app.query_one("#right-tabs")
                return getattr(tabs, "active", "tab-commentary")
            except Exception:
                return "tab-commentary"
        if nid == "scripture-pane":
            return "scripture"
        node = getattr(node, "parent", None)
    return "scripture"


def build_context_help(context: str, main_screen_bindings) -> tuple[str, str]:
    """Build context-aware help text based on current focus."""
    app_bindings = list(main_screen_bindings)

    if context == "sidebar":
        sidebar_bindings = [
            Binding("j", "cursor_down", "Move cursor down"),
            Binding("k", "cursor_up", "Move cursor up"),
            Binding("l", "expand_or_select", "Expand / select chapter"),
            Binding("h", "collapse_or_parent", "Collapse / go to parent"),
            Binding("g", "goto_top", "Jump to top"),
            Binding("G", "goto_bottom", "Jump to bottom"),
            Binding("space", "toggle_node", "Toggle expand / collapse"),
        ]
        return "Sidebar — Keyboard Reference", build_help_text(sidebar_bindings, app_bindings)

    if context.startswith("tab-"):
        tab_keys = set(RightPane.TAB_BINDINGS.get(context, []))
        bindings = [b for b in RightPane.BINDINGS if b.key in tab_keys]
        tab_name = context.removeprefix("tab-").capitalize()
        return f"Right Pane — {tab_name}", build_help_text(bindings, app_bindings)

    return "Scripture — Keyboard Reference", build_help_text(
        list(ScripturePane.BINDINGS), app_bindings
    )
