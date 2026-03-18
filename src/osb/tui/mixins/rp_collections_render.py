"""Collections tab rendering + input helpers mixin for RightPane."""

from __future__ import annotations

from textual.widgets import Input, Label, ListItem, ListView, Static, TabbedContent

from osb.db import queries
from osb.tui.mixins.rp_collections_utils import (
    build_collection_label, build_detail_header, build_detail_hints,
    build_list_hints, make_chapter_prefix, parse_verse_input
)


class RpCollectionsRenderMixin:
    """Rendering, add-bar, and input handling for Collections tab."""

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_collections_list(self) -> None:
        try:
            lv = self.query_one("#collections-list", ListView)
            header = self.query_one("#collections-header", Static)
            hints = self.query_one("#collections-hints", Static)
        except Exception:
            return

        has_temp = self._temp_refs is not None
        cols = queries.get_all_collections(self.conn)

        header.update("Collections")
        header.remove_class("col-header-detail")
        lv.clear()

        if has_temp:
            n = len(self._temp_refs)
            li = ListItem(Label(f"[italic]~ {self._temp_name or 'Unsaved'}[/]  [dim]({n} refs)  unsaved[/]"))
            li._is_temp = True
            li._collection_id = None
            li._col_name = ""
            lv.append(li)

        for col in cols:
            count = queries.get_collection_item_count(self.conn, col.id)
            li = ListItem(Label(build_collection_label(col.name, count)))
            li._is_temp = False
            li._collection_id = col.id
            li._col_name = col.name
            lv.append(li)

        if not has_temp and not cols:
            lv.append(ListItem(Label("[dim]  No collections yet.[/]")))

        if has_temp or cols:
            lv.index = 0

        hints.update(build_list_hints(has_temp))
        self._update_collections_tab_label()

    def _render_collection_detail(self) -> None:
        if self._active_collection_id is None:
            return
        try:
            lv = self.query_one("#collections-list", ListView)
            header = self.query_one("#collections-header", Static)
            hints = self.query_one("#collections-hints", Static)
        except Exception:
            return

        items = queries.get_collection_items(self.conn, self._active_collection_id)
        total = len(items)
        header.update(build_detail_header(self._active_collection_name, total))
        header.add_class("col-header-detail")
        hints.update(build_detail_hints())
        lv.clear()

        if total == 0:
            lv.append(ListItem(Label("[dim]  Empty collection. Press a to add a verse.[/]")))
            return

        for item, verse in items:
            snippet = verse.text[:45].rstrip()
            if len(verse.text) > 45:
                snippet += "…"
            visited = " [dim]✓[/]" if verse.ref in self._visited_refs else ""
            li = ListItem(Label(f"[dim]{verse.ref}[/dim]{visited}  {snippet}"))
            li._verse_ref = verse.ref
            li._is_temp = False
            li._collection_id = None
            lv.append(li)

        lv.index = 0

    def refresh_collections_view(self) -> None:
        try:
            if self.query_one("#right-tabs", TabbedContent).active != "tab-collections":
                return
        except Exception:
            return
        if self._collections_view == "detail" and self._active_collection_id is not None:
            self._render_collection_detail()
        else:
            self._render_collections_list()

    def _update_collections_tab_label(self) -> None:
        n = len(queries.get_all_collections(self.conn))
        if self._temp_refs:
            n += 1
        label = f"Collections ({n})" if n else "Collections"
        try:
            tab = self.query_one("#right-tabs", TabbedContent).get_tab("tab-collections")
            tab.label = label
        except Exception:
            pass

    def _make_chapter_prefix(self, chapter_ref: str) -> str:
        return make_chapter_prefix(self.conn, chapter_ref)

    def _refresh_temp_name_display(self) -> None:
        self._update_collections_tab_label()
        try:
            if self.query_one("#right-tabs", TabbedContent).active == "tab-collections":
                self._render_collections_list()
        except Exception:
            pass

    # ── Add-bar ───────────────────────────────────────────────────────────────

    def _show_add_bar(self, mode: str, prefix: str, initial: str) -> None:
        self._col_input_mode = mode
        try:
            self.query_one("#collections-add-bar").remove_class("hidden")
            self.query_one("#collections-add-prefix", Label).update(prefix)
            inp = self.query_one("#collections-add-input", Input)
            inp.value = initial
            inp.placeholder = "" if initial else ("e.g. Gen 1:1" if mode == "add_verse" else "Collection name…")
            self.call_after_refresh(inp.focus)
        except Exception:
            pass

    def _hide_add_bar(self) -> None:
        self._col_input_mode = ""
        try:
            self.query_one("#collections-add-bar").add_class("hidden")
        except Exception:
            pass

    def _parse_verse_input(self, text: str) -> str | None:
        return parse_verse_input(self.conn, text)
