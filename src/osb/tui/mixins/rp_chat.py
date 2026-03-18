"""Chat + Ollama mixin for RightPane."""

from __future__ import annotations

import sqlite3

import httpx
from textual.widgets import Input, Static

from osb import config
from osb.db import queries
from osb.tui.mixins.rp_chat_streaming import RpChatStreamingMixin
from osb.tui.mixins.rp_chat_ui import _ChatInput, _NotesEditor
from osb.tui.widgets.book_tree import BookTree

_AI_HEADER = "[bold dim]◆ AI[/]"


class RpChatMixin(RpChatStreamingMixin):
    """Ollama chat logic for RightPane."""

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _check_ollama(self) -> None:
        def check():
            try:
                httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2.0)
                self._ollama_available = True
                self.app.call_from_thread(self._update_ollama_status, True)
            except Exception:
                self._ollama_available = False
                self.app.call_from_thread(self._update_ollama_status, False)

        threading.Thread(target=check, daemon=True).start()

    def _update_ollama_status(self, available: bool) -> None:
        try:
            widget = self.query_one("#ollama-status", Static)
            if available:
                widget.update(f"[green]● [/][dim]ollama · {config.OLLAMA_MODEL}[/]")
            else:
                widget.update("[red]● [/][dim]ollama offline — run `ollama serve`[/]")
        except Exception:
            pass
        if not available:
            self._append_message("assistant", "Ollama not running — start with `ollama serve`")

    def _update_tree_chat_indicator(self, chapter_ref: str, has_chat: bool) -> None:
        try:
            self.app.query_one("#sidebar", BookTree).mark_chapter_chat(chapter_ref, has_chat)
        except Exception:
            pass

    # ── Chat tab actions ──────────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        if not self._current_chapter_ref:
            return
        queries.delete_chat_history(self.conn, self._current_chapter_ref)
        self._update_tree_chat_indicator(self._current_chapter_ref, has_chat=False)
        self._last_response = ""
        self._last_messages = []
        self._last_refs = []
        self._temp_refs = None
        self._temp_name = ""
        self._streaming = False
        self._streaming_widget = None
        self._accumulated_response = ""

        # Clear chat history display
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            container.remove_children()
        except Exception:
            pass

        # Clear input field
        try:
            chat_input = self.query_one("#chat-input", Input)
            chat_input.value = ""
        except Exception:
            pass

        # Rebuild chat history to show empty state
        self._rebuild_chat_history()

        self._update_collections_tab_label()
        try:
            from textual.widgets import TabbedContent
            if self.query_one("#right-tabs", TabbedContent).active == "tab-collections":
                self._render_collections_list()
        except Exception:
            pass
        self.app.notify("Chat cleared", timeout=2)

    def action_copy_last_response(self) -> None:
        if not self._last_response:
            self.app.notify("No AI response to copy", severity="warning")
            return
        try:
            import subprocess
            subprocess.run(["pbcopy"], input=self._last_response.encode(), check=True)
            self.app.notify("Copied to clipboard", timeout=2)
        except Exception as e:
            self.app.notify(f"Copy failed: {e}", severity="error")

    def action_toggle_debug(self) -> None:
        try:
            panel = self.query_one("#debug-panel", Static)
            if not panel.display and self._last_messages:
                lines = []
                for msg in self._last_messages:
                    role = msg["role"].upper()
                    content = msg["content"][:300] + ("…" if len(msg["content"]) > 300 else "")
                    lines.append(f"[bold]{role}[/]\n{content}")
                panel.update("\n[dim]─[/]\n".join(lines))
                panel.display = True
            else:
                panel.display = False
        except Exception:
            pass

    def action_browse_refs(self) -> None:
        if not self._last_refs:
            self.app.notify("No references in last response", severity="warning")
            return
        try:
            from textual.widgets import TabbedContent
            tabs = self.query_one("#right-tabs", TabbedContent)
            self._collections_view = "list"
            tabs.active = "tab-collections"
        except Exception:
            pass
