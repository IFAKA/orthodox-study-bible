"""RightPane — tabbed Commentary / Chat / Notes / Collections."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView, Markdown, Static, TabbedContent, TabPane

from osb.tui.mixins.chord_handler import ChordMixin
from osb.tui.mixins.rp_chat import RpChatMixin, _ChatInput, _NotesEditor
from osb.tui.mixins.rp_chat_history import RpChatHistoryMixin
from osb.tui.mixins.rp_collections import RpCollectionsMixin
from osb.tui.mixins.rp_collections_render import RpCollectionsRenderMixin
from osb.tui.mixins.rp_notes import RpNotesMixin


class RightPane(ChordMixin, Widget, RpChatMixin, RpChatHistoryMixin, RpNotesMixin, RpCollectionsMixin, RpCollectionsRenderMixin):
    """Right pane with Commentary, Chat, Notes, and Collections tabs."""

    can_focus = True

    BINDINGS = [
        Binding("a", "toggle_tab", "Tab", show=True),
        Binding("escape", "escape_pane", "Back", show=True, priority=True),
        Binding("i", "focus_input", "Type", show=True),
        Binding("j", "scroll_down", "↓", show=False),
        Binding("k", "scroll_up", "↑", show=False),
        Binding("G", "last_verse", "Bottom", show=False),
        Binding("r", "browse_refs", "Refs", show=True),
        Binding("y", "copy_last_response", "Copy", show=True),
        Binding("C", "clear_chat", "Clear chat", show=True),
        Binding("d", "toggle_debug", "Debug", show=False),
        # Collections
        Binding("enter", "col_select", "Open/Jump", show=True),
        Binding("J", "col_move_down", "Move down", show=False),
        Binding("K", "col_move_up", "Move up", show=False),
        Binding("n", "col_new", "New", show=True),
        Binding("a", "col_add_verse", "Add verse", show=True),
        Binding("x", "col_remove", "Remove", show=True),
        Binding("r", "col_rename", "Rename", show=True),
        Binding("d", "col_delete", "Delete", show=True),
        Binding("s", "col_save_temp", "Save", show=True),
        Binding("c", "col_go_chat", "Chat", show=False),
    ]

    TAB_BINDINGS = {
        "tab-commentary": ["j", "k", "a"],
        "tab-chat": ["j", "k", "a", "i", "y", "C", "r"],
        "tab-notes": ["j", "k", "a", "i"],
        "tab-collections": ["j", "k", "n", "a", "r", "x", "J", "K", "s"],
    }

    class OllamaChunk(Message):
        def __init__(self, text: str, chapter_ref: str) -> None:
            super().__init__()
            self.text = text
            self.chapter_ref = chapter_ref

    class OllamaError(Message):
        def __init__(self, error: str) -> None:
            super().__init__()
            self.error = error

    class StreamingDone(Message):
        def __init__(self, chapter_ref: str, response: str) -> None:
            super().__init__()
            self.chapter_ref = chapter_ref
            self.response = response

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._current_verse_ref: str | None = None
        self._current_chapter_ref: str | None = None
        self._ollama_available: bool = False
        self._streaming: bool = False
        self._accumulated_response: str = ""
        self._streaming_widget: Static | None = None
        self._last_messages: list[dict] = []
        self._last_response: str = ""
        self._last_refs: list[tuple[str, str]] = []
        self._save_timer: Timer | None = None
        # Collections state
        self._collections_view: str = "list"
        self._active_collection_id: int | None = None
        self._active_collection_name: str = ""
        self._temp_refs: list[tuple[str, str]] | None = None
        self._temp_name: str = ""
        self._visited_refs: set[str] = set()
        self._col_input_mode: str = ""
        self._awaiting_delete_confirm: bool = False

    def compose(self) -> ComposeResult:
        with TabbedContent(id="right-tabs"):
            with TabPane("Commentary", id="tab-commentary"):
                yield Markdown("", id="commentary-text")
            with TabPane("Chat", id="tab-chat"):
                yield Static("[dim]● checking ollama…[/]", id="ollama-status")
                with VerticalScroll(id="chat-history"):
                    pass
                yield Static("", id="debug-panel", classes="debug-panel")
                yield _ChatInput(placeholder="Ask about this passage…", id="chat-input")
            with TabPane("Notes", id="tab-notes"):
                yield Label("", id="notes-verse-label")
                yield _NotesEditor("", id="notes-editor", language="markdown")
            with TabPane("Collections", id="tab-collections"):
                yield Static("Collections", id="collections-header")
                yield Static("", id="collections-hints")
                yield ListView(id="collections-list")
                with Horizontal(id="collections-add-bar", classes="hidden"):
                    yield Label("", id="collections-add-prefix")
                    yield Input(id="collections-add-input", placeholder="")

    def on_mount(self) -> None:
        self._check_ollama()

    # ── Navigation ────────────────────────────────────────────────────────────

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
                self.query_one("#chat-input", Input).focus()
            elif tabs.active == "tab-notes":
                self.query_one("#notes-editor", _NotesEditor).focus()
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        self._scroll_active(down=True)

    def action_scroll_up(self) -> None:
        self._scroll_active(down=False)

    def _scroll_active(self, down: bool) -> None:
        method = "scroll_down" if down else "scroll_up"
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
            if active == "tab-chat":
                getattr(self.query_one("#chat-history", VerticalScroll), method)(animate=True, easing="out_cubic")
            elif active == "tab-commentary":
                getattr(self.query_one("#commentary-text", Markdown), method)(animate=True, easing="out_cubic")
            elif active == "tab-collections":
                lv = self.query_one("#collections-list", ListView)
                lv.action_cursor_down() if down else lv.action_cursor_up()
        except Exception:
            pass

    def _scroll_active_edge(self, end: bool) -> None:
        method = "scroll_end" if end else "scroll_home"
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
            if active == "tab-chat":
                getattr(self.query_one("#chat-history", VerticalScroll), method)(animate=True)
            elif active == "tab-commentary":
                getattr(self.query_one("#commentary-text", Markdown), method)(animate=True)
        except Exception:
            pass

    def _scroll_to_percentage(self, percent: int) -> None:
        """Scroll to N% through the active pane (1-100)."""
        percent = max(1, min(percent, 100))
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
            if active == "tab-chat":
                widget = self.query_one("#chat-history", VerticalScroll)
            elif active == "tab-commentary":
                widget = self.query_one("#commentary-text", Markdown)
            else:
                return

            # Calculate scroll position based on content height
            scrollable_region = widget.scrollable_content_region
            if scrollable_region.height > 0:
                max_scroll = max(0, scrollable_region.height - widget.container_size.height)
                target_y = int(max_scroll * percent / 100)
                widget.scroll_to(0, target_y, animate=True, duration=0.3, easing="out_cubic")
        except Exception:
            pass

    def on_key(self, event) -> None:
        focused_id = getattr(self.app.focused, "id", None)
        if focused_id in ("chat-input", "notes-editor", "collections-add-input"):
            return
        if self.handle_chord(event):
            return

    def action_goto_first_verse(self) -> None:
        self._scroll_active_edge(end=False)

    def action_last_verse(self) -> None:
        n = self._consume_vim_count()
        if n > 0:
            # [N]G: jump to N% of the way through content
            self._scroll_to_percentage(n)
        else:
            # G: jump to end
            self._scroll_active_edge(end=True)

    def action_toggle_tab(self) -> None:
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            order = ["tab-commentary", "tab-chat", "tab-notes", "tab-collections"]
            active = tabs.active
            idx = order.index(active) if active in order else 0
            tabs.active = order[(idx + 1) % len(order)]
        except Exception:
            pass

    # ── Chapter / verse updates ───────────────────────────────────────────────

    def load_chapter(self, chapter_ref: str) -> None:
        if chapter_ref != self._current_chapter_ref:
            self._current_chapter_ref = chapter_ref
            self._streaming = False
            self._streaming_widget = None
            self._accumulated_response = ""
            self._temp_refs = None
            self._temp_name = ""
            self._update_collections_tab_label()
            self._rebuild_chat_history()

    # ── Tab change ────────────────────────────────────────────────────────────

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        def _render_collections() -> None:
            if self._collections_view == "detail" and self._active_collection_id is not None:
                self._render_collection_detail()
            else:
                self._collections_view = "list"
                self._render_collections_list()

        if event.pane.id == "tab-collections":
            self.call_after_refresh(_render_collections)

        def _focus_and_refresh() -> None:
            self.focus()
            self.call_after_refresh(self.refresh_bindings)

        self.call_after_refresh(_focus_and_refresh)

    # ── check_action (footer visibility) ─────────────────────────────────────

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
        except Exception:
            return True

        on_col = active == "tab-collections"
        in_detail = on_col and self._collections_view == "detail"
        in_list = on_col and self._collections_view == "list"

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
            return True if self._temp_refs is not None else None
        if action == "col_go_chat":
            return True if in_detail else None
        return True
