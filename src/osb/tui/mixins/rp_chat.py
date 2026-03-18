"""Chat + Ollama mixin for RightPane."""

from __future__ import annotations

import json
import re
import sqlite3
import threading

import httpx
from textual.binding import Binding
from textual.widgets import Input, Static, TextArea

from osb import config
from osb.db import queries
from osb.importer.structure import normalize_book_name
from osb.tui.widgets.book_tree import BookTree

_AI_HEADER = "[bold dim]◆ AI[/]"


class _ChatInput(Input):
    BINDINGS = [Binding("enter", "submit", "Send", show=True)]


class _NotesEditor(TextArea):
    pass


def parse_refs(text: str, conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return deduplicated (verse_ref, display_label) list extracted from AI text."""
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


class RpChatMixin:
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

    # ── Sending ───────────────────────────────────────────────────────────────

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
                    json={"model": config.OLLAMA_MODEL, "messages": messages, "stream": True},
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
                                self.post_message, self.OllamaChunk(chunk, chapter_ref)
                            )
                        if data.get("done"):
                            self.app.call_from_thread(
                                self.post_message,
                                self.StreamingDone(chapter_ref, self._accumulated_response),
                            )
                            break
            except Exception as e:
                self.app.call_from_thread(self.post_message, self.OllamaError(str(e)))

        threading.Thread(target=stream_worker, daemon=True).start()

    # ── Message event handlers ────────────────────────────────────────────────

    def on_right_pane_ollama_chunk(self, event) -> None:
        self._accumulated_response += event.text
        self._update_stream_widget(self._accumulated_response)

    def on_right_pane_ollama_error(self, event) -> None:
        self._streaming = False
        self._finish_stream_widget("")
        self._append_message("assistant", f"Error: {event.error}")

    def on_right_pane_streaming_done(self, event) -> None:
        self._streaming = False
        if event.response:
            self._last_response = event.response
            if event.chapter_ref:
                queries.append_chat_message(self.conn, event.chapter_ref, "assistant", event.response)
                self._update_tree_chat_indicator(event.chapter_ref, has_chat=True)
            self._last_refs = parse_refs(event.response, self.conn)
            if self._last_refs:
                self._temp_refs = list(self._last_refs)
                self._temp_name = self._make_chapter_prefix(event.chapter_ref or "")
                self._update_collections_tab_label()
                self._generate_collection_name_async(event.chapter_ref or "", event.response)
        self._finish_stream_widget(event.response)

    def _generate_collection_name_async(self, chapter_ref: str, response: str) -> None:
        prefix = self._make_chapter_prefix(chapter_ref)
        ref_labels = ", ".join(label for _, label in (self._temp_refs or [])[:6])
        prompt = (
            f"Generate a short 2-4 word thematic title for a scripture collection based on "
            f"this biblical discussion. The collection includes: {ref_labels}.\n"
            f"Discussion:\n{response[:600]}\n\n"
            f"Respond with ONLY the title — no punctuation, no quotes, no explanation."
        )

        # Show generating state
        self._temp_name = f"{prefix} · (generating...)" if prefix else "(generating...)"
        self.app.call_from_thread(self._refresh_temp_name_display)

        def worker():
            try:
                resp = httpx.post(
                    f"{config.OLLAMA_BASE_URL}/api/generate",
                    json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
                )
                title = resp.json().get("response", "").strip()
                # Clean up the title, but be less aggressive
                title = re.sub(r'[*_`#\[\]"\']', "", title).strip()
                # Remove leading/trailing dots and dashes
                title = title.strip('.-')
                if title and len(title) > 1:  # Ensure meaningful content
                    self._temp_name = f"{prefix} · {title}" if prefix else title
                    self.app.call_from_thread(self._refresh_temp_name_display)
                else:
                    # If generation produced no title, revert to prefix
                    self._temp_name = prefix
                    self.app.call_from_thread(self._refresh_temp_name_display)
            except Exception as e:
                # Revert to prefix on failure
                self._temp_name = prefix
                self.app.call_from_thread(self._refresh_temp_name_display)

        threading.Thread(target=worker, daemon=True).start()

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
