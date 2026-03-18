"""ScripturePane in-chapter search mixin."""

from __future__ import annotations

from textual.widgets import Input


class SpSearchMixin:
    """In-chapter search (/) for ScripturePane."""

    def action_start_search(self) -> None:
        self._search_mode = True
        try:
            self.query_one("#sp-search-bar").remove_class("hidden")
            self.call_after_refresh(lambda: self.query_one("#sp-search-input", Input).focus())
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "sp-search-input":
            self._apply_search_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "sp-search-input":
            if self._match_refs:
                self._match_idx = 0
                self._set_focus_idx(self._verse_refs.index(self._match_refs[0]))
            self.focus()

    def _is_search_focused(self) -> bool:
        try:
            return self.query_one("#sp-search-input", Input).has_focus
        except Exception:
            return False

    def _apply_search_filter(self, query: str) -> None:
        from rich.text import Text
        from textual.widgets import Label as TLabel
        self._match_refs = []
        if not query:
            for ref, block in self._blocks.items():
                block.remove_class("search-match")
                block.remove_class("search-dim")
                block.remove_class("search-current")
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(block.verse_text)
                except Exception:
                    pass
            return
        q = query.lower()
        for ref, block in self._blocks.items():
            text = block.verse_text
            if q in text.lower():
                rich = Text()
                lower_text = text.lower()
                pos = 0
                while True:
                    idx = lower_text.find(q, pos)
                    if idx == -1:
                        rich.append(text[pos:])
                        break
                    rich.append(text[pos:idx])
                    rich.append(text[idx:idx + len(q)], style="bold yellow on #3a3000")
                    pos = idx + len(q)
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(rich)
                except Exception:
                    pass
                block.add_class("search-match")
                block.remove_class("search-dim")
                self._match_refs.append(ref)
            else:
                try:
                    block.query_one(f"#vtext-{ref}", TLabel).update(text)
                except Exception:
                    pass
                block.remove_class("search-match")
                block.add_class("search-dim")
        self._match_idx = 0
        self._update_search_current()

    def _update_search_current(self) -> None:
        for block in self._blocks.values():
            block.remove_class("search-current")
        if self._match_refs:
            block = self._blocks.get(self._match_refs[self._match_idx])
            if block:
                block.add_class("search-current")

    def _next_match(self) -> None:
        if not self._match_refs:
            return
        self._match_idx = (self._match_idx + 1) % len(self._match_refs)
        self._update_search_current()
        self._set_focus_idx(self._verse_refs.index(self._match_refs[self._match_idx]))

    def _prev_match(self) -> None:
        if not self._match_refs:
            return
        self._match_idx = (self._match_idx - 1) % len(self._match_refs)
        self._update_search_current()
        self._set_focus_idx(self._verse_refs.index(self._match_refs[self._match_idx]))

    def _clear_search(self) -> None:
        from textual.widgets import Label as TLabel
        self._search_mode = False
        self._match_refs = []
        self._match_idx = 0
        for ref, block in self._blocks.items():
            block.remove_class("search-match")
            block.remove_class("search-dim")
            block.remove_class("search-current")
            try:
                block.query_one(f"#vtext-{ref}", TLabel).update(block.verse_text)
            except Exception:
                pass
        try:
            self.query_one("#sp-search-bar").add_class("hidden")
            self.query_one("#sp-search-input", Input).clear()
        except Exception:
            pass
        self.focus()
