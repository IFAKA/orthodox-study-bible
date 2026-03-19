"""Simple chat logic for Ollama."""

import re
import threading

import httpx

from osb import config
from osb.db import queries
from osb.tui.mixins.rp_chat_utils import parse_refs


class RpChatStreamingMixin:
    """Simplified Ollama chat logic for RightPane."""

    def _send_chat(self, question: str) -> None:
        if self._streaming:
            return

        self._streaming = True
        self._append_message("user", question)
        self._start_stream_widget()

        def chat_worker():
            chapter_ref = self._current_chapter_ref
            verse_ref = self._current_verse_ref
            full_response = ""

            try:
                # Save user message
                queries.append_chat_message(self.conn, chapter_ref, "user", question)

                # Get context
                verse_text = ""
                commentary_text = ""
                if verse_ref:
                    v = queries.get_verse(self.conn, verse_ref)
                    if v:
                        verse_text = v.text
                if chapter_ref:
                    notes = queries.get_all_commentary_for_chapter(self.conn, chapter_ref)
                    commentary_text = " ".join(n.note_text for n in notes[:3])[:500]

                # Build messages
                history = queries.get_chat_history(self.conn, chapter_ref)
                messages = self._build_messages(history, verse_ref, verse_text, commentary_text)

                # Stream response from Ollama
                with httpx.stream(
                    "POST",
                    f"{config.OLLAMA_BASE_URL}/api/chat",
                    json={"model": config.OLLAMA_MODEL, "messages": messages, "stream": True},
                    timeout=90.0,
                ) as response:
                    if response.status_code == 200:
                        for line in response.iter_text():
                            if not line.strip():
                                continue
                            try:
                                chunk = __import__("json").loads(line)
                                text = chunk.get("message", {}).get("content", "")
                                if text:
                                    full_response += text
                                    self.app.call_from_thread(self._update_stream_widget, full_response)
                            except Exception:
                                pass

                        if full_response:
                            # Save to DB
                            queries.append_chat_message(self.conn, chapter_ref, "assistant", full_response)
                            self._last_response = full_response
                            self._last_refs = parse_refs(full_response, self.conn)

                            # Update chat indicator
                            if chapter_ref:
                                self._update_tree_chat_indicator(chapter_ref, has_chat=True)

                            # Finish display
                            self.app.call_from_thread(self._finish_stream_widget, full_response)

                            # Generate collection name if refs found
                            if self._last_refs:
                                self._temp_refs = list(self._last_refs)
                                self._temp_name = self._make_chapter_prefix(chapter_ref or "")
                                self._update_collections_tab_label()
                                self._generate_collection_name_async(chapter_ref or "", full_response)
                        else:
                            self.app.call_from_thread(self._finish_stream_widget, "[yellow]No response[/]")
                    else:
                        self.app.call_from_thread(self._finish_stream_widget, f"[red]Error {response.status_code}[/]")

            except httpx.TimeoutException:
                self.app.call_from_thread(
                    self._finish_stream_widget,
                    "[red]Timeout — Ollama took too long[/]\n[dim]Is it running? Try: ollama serve[/]"
                )
            except Exception as e:
                error_msg = str(e)
                if "Connection" in error_msg or "connect" in error_msg.lower():
                    msg = "[red]Can't connect to Ollama[/]\n[dim]Start with: ollama serve[/]"
                else:
                    msg = f"[red]Error: {error_msg}[/]"
                self.app.call_from_thread(self._finish_stream_widget, msg)
            finally:
                self._streaming = False

        threading.Thread(target=chat_worker, daemon=True).start()

    def _generate_collection_name_async(self, chapter_ref: str, response: str) -> None:
        """Generate a title for a scripture collection."""
        def worker():
            try:
                prefix = self._make_chapter_prefix(chapter_ref)
                ref_labels = ", ".join(label for _, label in (self._temp_refs or [])[:6])
                prompt = (
                    f"Generate a short 2-4 word title for a scripture collection. "
                    f"Collection includes: {ref_labels}\n\n"
                    f"Respond with ONLY the title — no punctuation, no quotes, no explanation."
                )

                resp = httpx.post(
                    f"{config.OLLAMA_BASE_URL}/api/generate",
                    json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    title = resp.json().get("response", "").strip()
                    title = re.sub(r'[*_`#\[\]"\']', "", title).strip()
                    title = title.strip('.-')
                    if title and len(title) > 1:
                        self._temp_name = f"{prefix} · {title}" if prefix else title
                    else:
                        self._temp_name = prefix
                    self.app.call_from_thread(self._refresh_temp_name_display)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()
