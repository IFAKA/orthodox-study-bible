"""Action visibility logic for RightPane."""

from textual.widgets import TabbedContent


def check_action_visibility(pane, action: str, parameters: tuple) -> bool | None:
    """Determine if an action should be visible/enabled in the footer."""
    try:
        active = pane.query_one("#right-tabs", TabbedContent).active
    except Exception:
        return True

    on_col = active == "tab-collections"
    in_detail = on_col and pane._collections_view == "detail"
    in_list = on_col and pane._collections_view == "list"

    if action in {"copy_last_response", "clear_chat", "toggle_debug", "browse_refs"}:
        return True if active == "tab-chat" else None
    if action == "focus_input":
        return True if active in ("tab-chat", "tab-notes") else None
    if action in {"scroll_down", "scroll_up"}:
        return True if active in ("tab-chat", "tab-commentary", "tab-collections") else None
    if action == "toggle_tab":
        return None if in_detail else True
    if action == "col_select":
        return True if on_col else None
    if action in {"col_move_down", "col_move_up"}:
        return True if in_detail else None
    if action == "col_new":
        return True if in_list else None
    if action == "col_add_verse":
        return True if in_detail else None
    if action == "col_remove":
        return True if in_detail else None
    if action == "col_rename":
        return True if on_col else None
    if action == "col_delete":
        return True if in_list else None
    if action == "col_save_temp":
        return True if pane._temp_refs is not None else None
    if action == "col_go_chat":
        return True if in_detail else None
    return True
