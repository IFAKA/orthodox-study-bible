"""SearchScreen — fuzzy modal search."""

from __future__ import annotations

import sqlite3

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView


class SearchScreen(ModalScreen[str | None]):
    """FTS modal. Dismisses with verse_ref on selection, None on cancel."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("j", "list_down", "Down", show=False),
        Binding("k", "list_up", "Up", show=False),
    ]

    def __init__(self, conn: sqlite3.Connection, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conn = conn
        self._results: list[dict] = []
        self._debounce_timer = None
        self._last_query: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog", classes="modal-dialog"):
            yield Label("Search Scripture", id="search-title", classes="modal-title")
            yield Input(placeholder="Search…", id="search-input")
            yield Label("", id="search-status")
            yield ListView(id="search-results")
            yield Label("Type to search · Tab/↓ to results · Enter select · Esc close", id="search-help")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        if self._debounce_timer:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(0.3, lambda: self._do_search(event.value))

    def _do_search(self, query: str) -> None:
        query = query.strip()
        self._last_query = query
        if len(query) < 2:
            self._clear_results()
            self._set_status("")
            return
        self._set_status("Searching…")
        self._fetch_results(query)

    @work(thread=True)
    def _fetch_results(self, query: str) -> None:
        from osb.db.queries import fuzzy_search_verses
        try:
            results = fuzzy_search_verses(self.conn, query)
        except Exception:
            results = []
        self.app.call_from_thread(self._on_results, query, results)

    def _on_results(self, query: str, results: list[dict]) -> None:
        if query != self._last_query:
            return  # stale result, a newer search is in flight
        self._results = results
        self._set_status("No results found." if not results else "")
        self._render_results()

    def _set_status(self, text: str) -> None:
        try:
            self.query_one("#search-status", Label).update(text)
        except Exception:
            pass

    def _clear_results(self) -> None:
        self._results = []
        try:
            lv = self.query_one("#search-results", ListView)
            lv.clear()
        except Exception:
            pass

    @staticmethod
    def _make_snippet(text: str, query: str, width: int = 55) -> "Text":
        import re
        from rapidfuzz import fuzz
        from rich.text import Text

        query_words = [w for w in re.sub(r"[^\w\s]", "", query.lower()).split() if len(w) >= 2]

        def _word_matches(w: str) -> bool:
            clean = re.sub(r"[^\w]", "", w.lower())
            return bool(clean) and any(fuzz.ratio(qw, clean) >= 70 for qw in query_words)

        # Find char position of first matching word to center the window
        best_pos = 0
        char_pos = 0
        for word in text.split():
            if _word_matches(word):
                best_pos = char_pos
                break
            char_pos += len(word) + 1

        start = max(0, best_pos - 10)
        end = min(len(text), start + width)
        window = text[start:end]

        prefix = Text("…") if start > 0 else Text("")
        suffix = Text("…") if end < len(text) else Text("")

        result = Text()
        first = True
        for word in window.split(" "):
            if not first:
                result.append(" ")
            first = False
            if _word_matches(word):
                result.append(word, style="bold yellow")
            else:
                result.append(word)

        return prefix + result + suffix

    def _render_results(self) -> None:
        from osb.importer.structure import format_ref
        from rich.text import Text
        try:
            lv = self.query_one("#search-results", ListView)
            lv.clear()
            for r in self._results[:50]:
                ref = r["ref"]
                verse_text = r.get("text", "")
                snippet = self._make_snippet(verse_text, self._last_query)
                ref_part = Text(f"{format_ref(ref):20} ")
                item = ListItem(
                    Label(ref_part + snippet),
                    id=f"sr-{ref.replace('-', '_')}",
                )
                item._verse_ref = ref  # type: ignore[attr-defined]
                lv.append(item)
            lv.scroll_home(animate=False)
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        ref = getattr(event.item, "_verse_ref", None)
        if ref:
            self.dismiss(ref)

    def action_list_down(self) -> None:
        try:
            self.query_one("#search-results", ListView).action_cursor_down()
        except Exception:
            pass

    def action_list_up(self) -> None:
        try:
            self.query_one("#search-results", ListView).action_cursor_up()
        except Exception:
            pass

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        try:
            lv = self.query_one("#search-results", ListView)
            highlighted = lv.highlighted_child
            if highlighted:
                ref = getattr(highlighted, "_verse_ref", None)
                if ref:
                    self.dismiss(ref)
        except Exception:
            pass
