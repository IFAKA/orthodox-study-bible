"""Navigation actions for RightPane."""

from textual.widgets import TabbedContent

from osb.tui.widgets.rp_scroll import scroll_active, scroll_active_edge, scroll_to_percentage


class RpNavigationMixin:
    """Navigation and scrolling actions for RightPane."""

    def action_escape_pane(self) -> None:
        focused_id = getattr(self.app.focused, "id", None)
        if focused_id == "collections-add-input":
            self._hide_add_bar()
            self.focus()
            return
        if focused_id in ("chat-input", "notes-editor"):
            self.focus()
            return
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
        except Exception:
            active = ""
        if active == "tab-collections" and self._collections_view == "detail":
            self._collections_view = "list"
            self._awaiting_delete_confirm = False
            self._render_collections_list()
        else:
            self._awaiting_delete_confirm = False
            try:
                self.app.query_one("#scripture-pane").focus()
            except Exception:
                pass

    def action_focus_input(self) -> None:
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            if tabs.active == "tab-chat":
                from osb.tui.mixins.rp_chat import _ChatInput
                self.query_one("#chat-input", _ChatInput).focus()
            elif tabs.active == "tab-notes":
                from osb.tui.mixins.rp_chat import _NotesEditor
                self.query_one("#notes-editor", _NotesEditor).focus()
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        scroll_active(self, down=True)

    def action_scroll_up(self) -> None:
        scroll_active(self, down=False)

    def action_goto_first_verse(self) -> None:
        n = self._consume_vim_count()
        if n > 0:
            scroll_to_percentage(self, n)
        else:
            scroll_active_edge(self, end=False)

    def action_last_verse(self) -> None:
        n = self._consume_vim_count()
        if n > 0:
            scroll_to_percentage(self, n)
        else:
            scroll_active_edge(self, end=True)

    _TAB_ORDER = ["tab-commentary", "tab-chat", "tab-notes", "tab-collections"]

    def show_tab(self, tab_id: str) -> None:
        """Switch directly to a named right-pane tab."""
        try:
            self.query_one("#right-tabs", TabbedContent).active = tab_id
        except Exception:
            pass

    def cycle_tab(self, step: int = 1) -> None:
        """Move to the previous/next right-pane tab (step -1/+1)."""
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            order = self._TAB_ORDER
            idx = order.index(tabs.active) if tabs.active in order else 0
            tabs.active = order[(idx + step) % len(order)]
        except Exception:
            pass

    def action_toggle_tab(self) -> None:
        self.cycle_tab(1)
