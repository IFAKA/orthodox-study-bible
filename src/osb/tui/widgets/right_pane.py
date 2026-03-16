"""RightPane — TabbedContent with Commentary and Chat tabs."""

from __future__ import annotations

import sqlite3
import threading
from typing import TYPE_CHECKING

import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Markdown, Static, TabbedContent, TabPane

from osb import config
from osb.db import queries

if TYPE_CHECKING:
    pass


class RightPane(Widget):
    """Right pane with Commentary and Chat tabs."""

    can_focus = True

    BINDINGS = [
        Binding("a", "toggle_tab", "Commentary/Chat", show=True),
        Binding("ctrl+t", "toggle_tab", "Switch Tab", show=False),
        Binding("escape", "escape_pane", "Back", show=False),
    ]

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

    def compose(self) -> ComposeResult:
        with TabbedContent(id="right-tabs"):
            with TabPane("Commentary", id="tab-commentary"):
                yield Markdown("", id="commentary-text")
            with TabPane("Chat", id="tab-chat"):
                with VerticalScroll(id="chat-history"):
                    pass  # messages mounted dynamically
                yield Input(
                    placeholder="Ask about this passage… (Enter to send)",
                    id="chat-input",
                )

    def on_mount(self) -> None:
        self._check_ollama()

    def on_focus(self) -> None:
        """Delegate focus to chat input when on Chat tab; stay focused for Commentary."""
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            if tabs.active == "tab-chat":
                self.query_one("#chat-input", Input).focus()
            # Commentary: Markdown is not focusable — RightPane retains focus.
        except Exception:
            pass

    def action_escape_pane(self) -> None:
        """Return focus to scripture pane."""
        try:
            self.app.query_one("#scripture-pane").focus()
        except Exception:
            pass

    def _check_ollama(self) -> None:
        def check():
            try:
                httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2.0)
                self._ollama_available = True
            except Exception:
                self._ollama_available = False
                self.app.call_from_thread(self._show_ollama_unavailable)

        threading.Thread(target=check, daemon=True).start()

    def _show_ollama_unavailable(self) -> None:
        self._append_message("assistant", "Ollama not running — start with `ollama serve`")

    # ── Commentary ────────────────────────────────────────────────────────────

    def update_verse(self, verse_ref: str) -> None:
        self._current_verse_ref = verse_ref
        parts = verse_ref.split("-")
        if len(parts) >= 2:
            self._current_chapter_ref = "-".join(parts[:2])
        self._render_commentary(verse_ref)

    def _render_commentary(self, verse_ref: str) -> None:
        notes = queries.get_commentary_for_verse(self.conn, verse_ref)
        xrefs = queries.get_cross_refs(self.conn, verse_ref)

        lines = []
        if notes:
            for note in notes:
                lines.append(note.note_text)
                lines.append("")
        else:
            lines.append("*No commentary for this verse.*")

        if xrefs:
            lines.append("---")
            lines.append("**Cross-references:**")
            for xr in xrefs:
                if xr["to_ref"]:
                    lines.append(f"→ {xr['to_ref_text']} ({xr['to_ref']})")
                else:
                    lines.append(f"→ {xr['to_ref_text']}")

        try:
            md = self.query_one("#commentary-text", Markdown)
            md.update("\n".join(lines))
        except Exception:
            pass

    # ── Chat ──────────────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        question = event.value.strip()
        if not question or not self._current_chapter_ref:
            return
        event.input.clear()
        self._send_chat(question)

    def _send_chat(self, question: str) -> None:
        if not self._ollama_available:
            self._append_message("assistant", "Ollama not available. Start with `ollama serve`.")
            return
        if self._streaming:
            return

        chapter_ref = self._current_chapter_ref
        verse_ref = self._current_verse_ref

        verse_text = ""
        commentary_text = ""
        if verse_ref:
            v = queries.get_verse(self.conn, verse_ref)
            if v:
                verse_text = v.text
        if chapter_ref:
            notes = queries.get_all_commentary_for_chapter(self.conn, chapter_ref)
            commentary_text = " ".join(n.note_text for n in notes[:3])[:500]

        queries.append_chat_message(self.conn, chapter_ref, "user", question)
        self._append_message("user", question)

        history = queries.get_chat_history(self.conn, chapter_ref)
        messages = self._build_messages(history, verse_ref, verse_text, commentary_text)

        self._streaming = True
        self._accumulated_response = ""
        self._start_stream_widget()

        def stream_worker():
            try:
                with httpx.stream(
                    "POST",
                    f"{config.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": config.OLLAMA_MODEL,
                        "messages": messages,
                        "stream": True,
                    },
                    timeout=60.0,
                ) as resp:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        import json
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            self.app.call_from_thread(
                                self.post_message,
                                self.OllamaChunk(chunk, chapter_ref),
                            )
                        if data.get("done"):
                            self.app.call_from_thread(
                                self.post_message,
                                self.StreamingDone(chapter_ref, self._accumulated_response),
                            )
                            break
            except Exception as e:
                self.app.call_from_thread(
                    self.post_message,
                    self.OllamaError(str(e)),
                )

        threading.Thread(target=stream_worker, daemon=True).start()

    def on_right_pane_ollama_chunk(self, event: "RightPane.OllamaChunk") -> None:
        self._accumulated_response += event.text
        self._update_stream_widget(self._accumulated_response)

    def on_right_pane_ollama_error(self, event: "RightPane.OllamaError") -> None:
        self._streaming = False
        self._finish_stream_widget("")
        self._append_message("assistant", f"Error: {event.error}")

    def on_right_pane_streaming_done(self, event: "RightPane.StreamingDone") -> None:
        self._streaming = False
        if event.response and event.chapter_ref:
            queries.append_chat_message(self.conn, event.chapter_ref, "assistant", event.response)
        self._finish_stream_widget(event.response)

    # ── Chat message widget helpers ───────────────────────────────────────────

    def _append_message(self, role: str, content: str) -> None:
        """Mount a single message widget into the chat history."""
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            if role == "user":
                text = f"[bold gold1]▶ You[/]\n{content}"
            else:
                text = f"[bold dim]◆ AI[/]\n{content}"
            widget = Static(text, classes=f"chat-msg chat-{role}")
            container.mount(widget)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _start_stream_widget(self) -> None:
        """Mount the in-progress AI response widget."""
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            self._streaming_widget = Static(
                "[bold dim]◆ AI[/]\n▋",
                classes="chat-msg chat-assistant",
            )
            container.mount(self._streaming_widget)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _update_stream_widget(self, text: str) -> None:
        """Update the in-progress AI response widget."""
        if self._streaming_widget:
            self._streaming_widget.update(f"[bold dim]◆ AI[/]\n{text}▋")
            try:
                self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)
            except Exception:
                pass

    def _finish_stream_widget(self, text: str) -> None:
        """Finalize the AI response widget (remove cursor)."""
        if self._streaming_widget:
            if text:
                self._streaming_widget.update(f"[bold dim]◆ AI[/]\n{text}")
            self._streaming_widget = None

    def _rebuild_chat_history(self) -> None:
        """Clear and rebuild all chat message widgets from DB."""
        if not self._current_chapter_ref:
            return
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            container.remove_children()
            self._streaming_widget = None
            history = queries.get_chat_history(self.conn, self._current_chapter_ref)
            for msg in history:
                self._append_message(msg["role"], msg["content"])
        except Exception:
            pass

    def _build_messages(
        self,
        history: list[dict],
        verse_ref: str | None,
        verse_text: str,
        commentary_text: str,
    ) -> list[dict]:
        book_chapter = verse_ref.rsplit("-", 1)[0].replace("-", " ") if verse_ref else "this chapter"
        system_prompt = (
            f"You are a scholarly assistant for Orthodox Christian scripture study. "
            f"The user is reading the Orthodox Study Bible ({config.JURISDICTION}). "
            f"Answer questions about the text, historical context, biblical geography, "
            f"theological terms, and patristic interpretation. "
            f"Stay grounded in the provided context. Do not give pastoral advice. Be clear, not academic.\n\n"
            f"Passage: {book_chapter}\n"
            f"Text: {verse_text}\n"
            f"OSB notes: {commentary_text}"
        )

        messages = [{"role": "system", "content": system_prompt}]

        window: list[dict] = []
        token_count = len(system_prompt.split()) * 1.3
        for msg in reversed(history[-20:]):
            msg_tokens = len(msg["content"].split()) * 1.3
            if token_count + msg_tokens > config.MAX_CONTEXT_TOKENS:
                break
            window.insert(0, {"role": msg["role"], "content": msg["content"]})
            token_count += msg_tokens

        messages.extend(window)
        return messages

    def load_chapter(self, chapter_ref: str) -> None:
        """Called when user navigates to a new chapter."""
        if chapter_ref != self._current_chapter_ref:
            self._current_chapter_ref = chapter_ref
            self._streaming = False
            self._streaming_widget = None
            self._accumulated_response = ""
            self._rebuild_chat_history()

    def on_tabbed_content_tab_changed(self, event: TabbedContent.TabChanged) -> None:
        if event.tab_pane.id == "tab-chat":
            try:
                self.query_one("#chat-input", Input).focus()
            except Exception:
                pass
        else:
            self.focus()

    def action_toggle_tab(self) -> None:
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            active = tabs.active
            if active == "tab-commentary":
                tabs.active = "tab-chat"
            else:
                tabs.active = "tab-commentary"
        except Exception:
            pass
