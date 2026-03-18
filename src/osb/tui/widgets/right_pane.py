"""RightPane — tabbed Commentary / Chat / Notes / Collections."""

from __future__ import annotations

import sqlite3

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView, Markdown, Static, TabbedContent, TabPane

from osb.tui.mixins.chord_handler import ChordMixin
from osb.tui.mixins.rp_chat import RpChatMixin, _ChatInput, _NotesEditor
from osb.tui.mixins.rp_chat_history import RpChatHistoryMixin
from osb.tui.mixins.rp_collections import RpCollectionsMixin
from osb.tui.mixins.rp_collections_render import RpCollectionsRenderMixin
from osb.tui.mixins.rp_notes import RpNotesMixin
from osb.tui.widgets.rp_messages import OllamaChunk, OllamaError, StreamingDone
from osb.tui.widgets.rp_navigation import RpNavigationMixin
from osb.tui.widgets.rp_visibility import check_action_visibility


class RightPane(ChordMixin, Widget, RpChatMixin, RpChatHistoryMixin, RpNotesMixin, RpCollectionsMixin, RpCollectionsRenderMixin, RpNavigationMixin):
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
        # Set chat as default active tab
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            tabs.active = "tab-chat"
        except Exception:
            pass

    # ── Navigation ────────────────────────────────────────────────────────────

    def on_key(self, event) -> None:
        focused_id = getattr(self.app.focused, "id", None)
        if focused_id in ("chat-input", "notes-editor", "collections-add-input"):
            return
        if self.handle_chord(event):
            return

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
        return check_action_visibility(self, action, parameters)
