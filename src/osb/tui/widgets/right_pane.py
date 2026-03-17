"""RightPane — TabbedContent with Commentary and Chat tabs."""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import threading
import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Input, Label, Markdown, Static, TabbedContent, TabPane, TextArea

from osb import config
from osb.db import queries
from osb.importer.structure import normalize_book_name
from osb.tui.widgets.book_tree import BookTree


def _parse_refs(text: str, conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return deduplicated list of (verse_ref, display_label) extracted from AI response text."""
    pattern = re.compile(
        r'(?<!\w)(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(\d+)(?:-\d+)?(?!\d)'
    )
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        book_raw, chapter, verse = m.group(1).strip(), m.group(2), m.group(3)
        abbrev = normalize_book_name(book_raw)
        if not abbrev:
            continue
        verse_ref = f"{abbrev}-{chapter}-{verse}"
        if verse_ref in seen:
            continue
        if queries.get_verse(conn, verse_ref) is None:
            continue
        seen.add(verse_ref)
        results.append((verse_ref, f"{book_raw.title()} {chapter}:{verse}"))
    return results


class _ChatInput(Input):
    """Chat input — escape/submit handled by RightPane (priority binding)."""

    BINDINGS = [Binding("enter", "submit", "Send", show=True)]


class _NotesEditor(TextArea):
    """TextArea for editing verse annotations — escape handled by RightPane (priority binding)."""


_AI_HEADER = "[bold dim]◆ AI[/]"


class RightPane(Widget):
    """Right pane with Commentary and Chat tabs."""

    can_focus = True

    BINDINGS = [
        Binding("a", "toggle_tab", "Tab", show=True),
        Binding("escape", "escape_pane", "Back", show=True, priority=True),
        Binding("i", "focus_input", "Type", show=True),
        Binding("j", "scroll_down", "↓", show=False),
        Binding("k", "scroll_up", "↑", show=False),
        Binding("r", "browse_refs", "Refs", show=True),
        Binding("y", "copy_last_response", "Copy", show=True),
        Binding("C", "clear_chat", "Clear chat", show=True),
        Binding("d", "toggle_debug", "Debug", show=False),
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
        self._last_messages: list[dict] = []
        self._last_response: str = ""
        self._last_refs: list[tuple[str, str]] = []
        self._save_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with TabbedContent(id="right-tabs"):
            with TabPane("Commentary", id="tab-commentary"):
                yield Markdown("", id="commentary-text")
            with TabPane("Chat", id="tab-chat"):
                yield Static("[dim]● checking ollama…[/]", id="ollama-status")
                with VerticalScroll(id="chat-history"):
                    pass  # messages mounted dynamically
                yield Static("", id="debug-panel", classes="debug-panel")
                yield _ChatInput(
                    placeholder="Ask about this passage…",
                    id="chat-input",
                )
            with TabPane("Notes", id="tab-notes"):
                yield Label("", id="notes-verse-label")
                yield _NotesEditor("", id="notes-editor", language="markdown")

    def on_mount(self) -> None:
        self._check_ollama()

    def action_escape_pane(self) -> None:
        """Escape from any child input/editor back to RightPane, then to scripture pane."""
        focused = self.app.focused
        focused_id = getattr(focused, "id", None)
        if focused_id in ("chat-input", "notes-editor"):
            # Step 1: leave the editor/input, land on RightPane
            self.focus()
        else:
            # Step 2 (or direct): RightPane → scripture pane
            try:
                self.app.query_one("#scripture-pane").focus()
            except Exception:
                pass

    def action_focus_input(self) -> None:
        """Focus the active tab's input widget."""
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            if tabs.active == "tab-chat":
                self.query_one("#chat-input", Input).focus()
            elif tabs.active == "tab-notes":
                self.query_one("#notes-editor", _NotesEditor).focus()
        except Exception:
            pass

    def action_toggle_debug(self) -> None:
        """Toggle the debug panel showing the last prompt sent to the model."""
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

    def action_scroll_down(self) -> None:
        self._scroll_active(down=True)

    def action_scroll_up(self) -> None:
        self._scroll_active(down=False)

    def _scroll_active(self, down: bool) -> None:
        method = "scroll_down" if down else "scroll_up"
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
            if active == "tab-chat":
                getattr(self.query_one("#chat-history", VerticalScroll), method)(animate=False)
            elif active == "tab-commentary":
                getattr(self.query_one("#commentary-text", Markdown), method)(animate=False)
        except Exception:
            pass

    def action_copy_last_response(self) -> None:
        if not self._last_response:
            self.app.notify("No AI response to copy", severity="warning")
            return
        try:
            subprocess.run(["pbcopy"], input=self._last_response.encode(), check=True)
            self.app.notify("Copied to clipboard", timeout=2)
        except Exception as e:
            self.app.notify(f"Copy failed: {e}", severity="error")

    def action_browse_refs(self) -> None:
        if not self._last_refs:
            self.app.notify("No references in last response", severity="warning")
            return
        from osb.tui.screens.chat_refs_screen import ChatRefScreen
        from osb.tui.screens.main_screen import MainScreen

        def callback(ref: str | None) -> None:
            if ref:
                for screen in self.app.screen_stack:
                    if isinstance(screen, MainScreen):
                        screen._navigate_to_verse(ref)
                        break

        self.app.push_screen(ChatRefScreen(self._last_refs), callback)

    def action_clear_chat(self) -> None:
        if not self._current_chapter_ref:
            return
        queries.delete_chat_history(self.conn, self._current_chapter_ref)
        self._update_tree_chat_indicator(self._current_chapter_ref, has_chat=False)
        self._last_response = ""
        self._last_messages = []
        self._last_refs = []
        self._streaming = False
        self._streaming_widget = None
        self._accumulated_response = ""
        try:
            self.query_one("#chat-history", VerticalScroll).remove_children()
        except Exception:
            pass
        self.app.notify("Chat cleared", timeout=2)

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

    # ── Commentary ────────────────────────────────────────────────────────────

    def update_verse(self, verse_ref: str) -> None:
        self._current_verse_ref = verse_ref
        parts = verse_ref.split("-")
        if len(parts) >= 2:
            self._current_chapter_ref = "-".join(parts[:2])
        self._render_commentary(verse_ref)
        self._load_note(verse_ref)

    def _load_note(self, verse_ref: str) -> None:
        try:
            ann = queries.get_annotation(self.conn, verse_ref)
            editor = self.query_one("#notes-editor", _NotesEditor)
            editor.load_text(ann.body if ann else "")
            self.query_one("#notes-verse-label", Label).update(verse_ref)
        except Exception:
            pass

    def _save_current_note(self) -> None:
        if not self._current_verse_ref:
            return
        try:
            editor = self.query_one("#notes-editor", _NotesEditor)
            queries.save_annotation(self.conn, self._current_verse_ref, editor.text)
        except Exception:
            pass

    def focus_notes_editor(self) -> None:
        """Switch to Notes tab and focus the editor."""
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            tabs.active = "tab-notes"
            self.call_after_refresh(lambda: self.query_one("#notes-editor", _NotesEditor).focus())
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "notes-editor":
            if self._save_timer:
                self._save_timer.stop()
            self._save_timer = self.set_timer(0.8, self._save_current_note)

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

        self._last_messages = messages
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
                    timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
                ) as resp:
                    for line in resp.iter_lines():
                        if not line:
                            continue
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
        if event.response:
            self._last_response = event.response
            if event.chapter_ref:
                queries.append_chat_message(self.conn, event.chapter_ref, "assistant", event.response)
                self._update_tree_chat_indicator(event.chapter_ref, has_chat=True)
            self._last_refs = _parse_refs(event.response, self.conn)
        self._finish_stream_widget(event.response)

    # ── Chat message widget helpers ───────────────────────────────────────────

    def _append_message(self, role: str, content: str) -> None:
        """Mount a single message widget into the chat history."""
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            if role == "user":
                text = f"[bold gold1]▶ You[/]\n{content}"
            else:
                text = f"{_AI_HEADER}\n{content}"
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
                f"{_AI_HEADER}\n▋",
                classes="chat-msg chat-assistant",
            )
            container.mount(self._streaming_widget)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _update_stream_widget(self, text: str) -> None:
        """Update the in-progress AI response widget."""
        if self._streaming_widget:
            self._streaming_widget.update(f"{_AI_HEADER}\n{text}▋")
            try:
                self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)
            except Exception:
                pass

    def _finish_stream_widget(self, text: str) -> None:
        """Finalize the AI response widget (remove cursor)."""
        if self._streaming_widget:
            if text:
                hint = ""
                if self._last_refs:
                    n = len(self._last_refs)
                    hint = f"\n[dim]↳ {n} {'reference' if n == 1 else 'references'} · r to browse[/]"
                self._streaming_widget.update(f"{_AI_HEADER}\n{text}{hint}")
            else:
                # No response received — remove the dangling cursor widget
                try:
                    self._streaming_widget.remove()
                except Exception:
                    pass
            self._streaming_widget = None

    def _rebuild_chat_history(self) -> None:
        """Clear and rebuild all chat message widgets from DB."""
        if not self._current_chapter_ref:
            return
        self._last_refs = []
        self._last_response = ""
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            container.remove_children()
            self._streaming_widget = None
            history = queries.get_chat_history(self.conn, self._current_chapter_ref)
            if not history:
                return
            # Mount all but the last assistant message normally
            last_assistant_idx = None
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] == "assistant":
                    last_assistant_idx = i
                    break
            for i, msg in enumerate(history):
                if i == last_assistant_idx:
                    # Restore refs and hint for the last assistant response
                    content = msg["content"]
                    self._last_response = content
                    self._last_refs = _parse_refs(content, self.conn)
                    hint = ""
                    if self._last_refs:
                        n = len(self._last_refs)
                        hint = f"\n[dim]↳ {n} {'reference' if n == 1 else 'references'} · r to browse[/]"
                    widget = Static(
                        f"{_AI_HEADER}\n{content}{hint}",
                        classes="chat-msg chat-assistant",
                    )
                    container.mount(widget)
                else:
                    self._append_message(msg["role"], msg["content"])
            container.scroll_end(animate=False)
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
            f"Stay grounded in the provided context. Do not give pastoral advice. Be clear, not academic. "
            f"When citing scripture, use standard format: 'Book Chapter:Verse' (e.g., 'Gen 1:1', '1 Cor 3:16', 'Ps 22:3').\n\n"
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

    def _update_tree_chat_indicator(self, chapter_ref: str, has_chat: bool) -> None:
        try:
            self.app.query_one("#sidebar", BookTree).mark_chapter_chat(chapter_ref, has_chat)
        except Exception:
            pass

    def load_chapter(self, chapter_ref: str) -> None:
        """Called when user navigates to a new chapter."""
        if chapter_ref != self._current_chapter_ref:
            self._current_chapter_ref = chapter_ref
            self._streaming = False
            self._streaming_widget = None
            self._accumulated_response = ""
            self._rebuild_chat_history()

    def on_tabbed_content_tab_changed(self, event: TabbedContent.TabChanged) -> None:
        def _focus_then_refresh() -> None:
            self.focus()
            self.refresh_bindings()
        self.call_after_refresh(_focus_then_refresh)

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        try:
            active = self.query_one("#right-tabs", TabbedContent).active
        except Exception:
            return True
        # chat-only actions — hide from footer entirely when not on chat tab
        if action in {"copy_last_response", "clear_chat", "toggle_debug", "browse_refs"}:
            return True if active == "tab-chat" else None
        # chat + notes (has a text input to focus)
        if action == "focus_input":
            return True if active in ("tab-chat", "tab-notes") else None
        # scroll only on tabs that have scrollable content
        if action in {"scroll_down", "scroll_up"}:
            return True if active in ("tab-chat", "tab-commentary") else None
        return True

    def action_toggle_tab(self) -> None:
        try:
            tabs = self.query_one("#right-tabs", TabbedContent)
            order = ["tab-commentary", "tab-chat", "tab-notes"]
            active = tabs.active
            idx = order.index(active) if active in order else 0
            tabs.active = order[(idx + 1) % len(order)]
        except Exception:
            pass
