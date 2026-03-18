"""Chat history widget helpers mixin for RightPane."""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static

from osb import config
from osb.tui.mixins.rp_chat import _AI_HEADER, parse_refs


class RpChatHistoryMixin:
    """Chat message widget rendering and history rebuild for RightPane."""

    def _append_message(self, role: str, content: str) -> None:
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            text = f"[bold gold1]▶ You[/]\n{content}" if role == "user" else f"{_AI_HEADER}\n{content}"
            container.mount(Static(text, classes=f"chat-msg chat-{role}"))
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _start_stream_widget(self) -> None:
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            self._streaming_widget = Static(f"{_AI_HEADER}\n▋", classes="chat-msg chat-assistant")
            container.mount(self._streaming_widget)
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _update_stream_widget(self, text: str) -> None:
        if self._streaming_widget:
            self._streaming_widget.update(f"{_AI_HEADER}\n{text}▋")
            try:
                self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)
            except Exception:
                pass

    def _finish_stream_widget(self, text: str) -> None:
        if self._streaming_widget:
            if text:
                hint = ""
                if self._last_refs:
                    n = len(self._last_refs)
                    hint = f"\n[dim]↳ {n} {'reference' if n == 1 else 'references'} · r browse · s save as collection[/]"
                self._streaming_widget.update(f"{_AI_HEADER}\n{text}{hint}")
            else:
                try:
                    self._streaming_widget.remove()
                except Exception:
                    pass
            self._streaming_widget = None

    def _rebuild_chat_history(self) -> None:
        if not self._current_chapter_ref:
            return
        self._last_refs = []
        self._last_response = ""
        try:
            container = self.query_one("#chat-history", VerticalScroll)
            container.remove_children()
            self._streaming_widget = None
            from osb.db import queries
            history = queries.get_chat_history(self.conn, self._current_chapter_ref)
            if not history:
                return
            last_assistant_idx = next(
                (i for i in range(len(history) - 1, -1, -1) if history[i]["role"] == "assistant"),
                None,
            )
            for i, msg in enumerate(history):
                if i == last_assistant_idx:
                    content = msg["content"]
                    self._last_response = content
                    self._last_refs = parse_refs(content, self.conn)
                    hint = ""
                    if self._last_refs:
                        n = len(self._last_refs)
                        hint = f"\n[dim]↳ {n} {'reference' if n == 1 else 'references'} · r browse · s save as collection[/]"
                    container.mount(Static(
                        f"{_AI_HEADER}\n{content}{hint}", classes="chat-msg chat-assistant"
                    ))
                else:
                    self._append_message(msg["role"], msg["content"])
            container.scroll_end(animate=False)
        except Exception:
            pass

    def _build_messages(self, history, verse_ref, verse_text, commentary_text) -> list[dict]:
        book_chapter = verse_ref.rsplit("-", 1)[0].replace("-", " ") if verse_ref else "this chapter"
        system_prompt = (
            f"You are a scholarly assistant for Orthodox Christian scripture study. "
            f"The user is reading the Orthodox Study Bible ({config.JURISDICTION}). "
            f"Answer questions about the text, historical context, biblical geography, "
            f"theological terms, and patristic interpretation. "
            f"Stay grounded in the provided context. Do not give pastoral advice. Be clear, not academic. "
            f"When citing scripture, use standard format: 'Book Chapter:Verse' (e.g., 'Gen 1:1', '1 Cor 3:16', 'Ps 22:3').\n\n"
            f"Passage: {book_chapter}\nText: {verse_text}\nOSB notes: {commentary_text}"
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
