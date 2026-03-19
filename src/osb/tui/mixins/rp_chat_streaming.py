"""Ollama streaming logic for chat."""

import json
import re
import threading

import httpx

from osb import config
from osb.db import queries
from osb.tui.mixins.rp_chat_utils import parse_refs


class RpChatStreamingMixin:
    """Ollama streaming logic for RightPane."""

    def _send_chat(self, question: str) -> None:
        if self._streaming:
            return

        # Check Ollama availability in background
        def verify_and_send():
            try:
                httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2.0)
                self._ollama_available = True
                self.app.call_from_thread(self._update_ollama_status, True)
                # Ollama is available, proceed with sending
                self.app.call_from_thread(self._send_chat_to_ollama, question)
            except Exception:
                self._ollama_available = False
                self.app.call_from_thread(self._update_ollama_status, False)
                self.app.call_from_thread(
                    self._append_message,
                    "assistant",
                    f"[red]✗ Ollama not available[/]\nCan't connect to {config.OLLAMA_BASE_URL}\n[dim]Tip: Start Ollama with `ollama serve`[/]"
                )

        threading.Thread(target=verify_and_send, daemon=True).start()

    def _send_chat_to_ollama(self, question: str) -> None:
        """Actually send the chat (after Ollama is verified available)."""
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
                    timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
                ) as resp:
                    if resp.status_code == 404:
                        raise RuntimeError(f"Model '{config.OLLAMA_MODEL}' not found. Run: ollama pull {config.OLLAMA_MODEL}")
                    if resp.status_code >= 400:
                        raise RuntimeError(f"Ollama error (code {resp.status_code})")

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
            except httpx.TimeoutException as e:
                self.app.call_from_thread(
                    self.post_message,
                    self.OllamaError(f"Timeout waiting for Ollama response (30s). Is it running?")
                )
            except Exception as e:
                self.app.call_from_thread(self.post_message, self.OllamaError(str(e)))

        threading.Thread(target=stream_worker, daemon=True).start()

    def on_right_pane_ollama_chunk(self, event) -> None:
        self._accumulated_response += event.text
        self._update_stream_widget(self._accumulated_response)
        # Reset loading timeout since we got a response
        self._last_chunk_time = __import__('time').time()

    def on_right_pane_ollama_error(self, event) -> None:
        self._streaming = False
        self._finish_stream_widget("")
        error_msg = event.error
        if "Timeout" in error_msg or "timeout" in error_msg:
            self._append_message("assistant", f"[red]✗ Timeout[/]\n{error_msg}\n[dim]Tip: Is Ollama running? Try: `ollama serve`[/]")
        elif "not found" in error_msg.lower():
            self._append_message("assistant", f"[red]✗ Model not found[/]\n{error_msg}\n[dim]Tip: {error_msg.split('Run:')[-1].strip() if 'Run:' in error_msg else 'Download the model first.'}[/]")
        elif "Connection" in error_msg or "connect" in error_msg.lower():
            self._append_message("assistant", f"[red]✗ Can't connect to Ollama[/]\n{error_msg}\n[dim]Tip: Start Ollama with `ollama serve`[/]")
        else:
            self._append_message("assistant", f"[red]✗ Error[/]\n{error_msg}")

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

        self._temp_name = f"{prefix} · (generating...)" if prefix else "(generating...)"
        self.app.call_from_thread(self._refresh_temp_name_display)

        def worker():
            try:
                resp = httpx.post(
                    f"{config.OLLAMA_BASE_URL}/api/generate",
                    json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Ollama error (code {resp.status_code})")
                title = resp.json().get("response", "").strip()
                title = re.sub(r'[*_`#\[\]"\']', "", title).strip()
                title = title.strip('.-')
                if title and len(title) > 1:
                    self._temp_name = f"{prefix} · {title}" if prefix else title
                    self.app.call_from_thread(self._refresh_temp_name_display)
                else:
                    self._temp_name = prefix
                    self.app.call_from_thread(self._refresh_temp_name_display)
            except Exception:
                self._temp_name = prefix
                self.app.call_from_thread(self._refresh_temp_name_display)

        threading.Thread(target=worker, daemon=True).start()
