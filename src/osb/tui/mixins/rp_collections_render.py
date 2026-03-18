"""Collections tab rendering + input helpers mixin for RightPane."""

from __future__ import annotations

import re

from textual.widgets import Input, Label, ListItem, ListView, Static, TabbedContent

from osb.db import queries
from osb.importer.structure import normalize_book_name


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
            li = ListItem(Label(f"{col.name}  [dim]({count})[/]"))
            li._is_temp = False
            li._collection_id = col.id
            li._col_name = col.name
            lv.append(li)

        if not has_temp and not cols:
            lv.append(ListItem(Label("[dim]  No collections yet.[/]")))

        if has_temp or cols:
            lv.index = 0

        hint_parts = ["↵ open", "n new", "r rename", "d delete"]
        if has_temp:
            hint_parts.append("s save")
        hints.update("[dim]" + "  ·  ".join(hint_parts) + "[/]")
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
        header.update(f"[dim]Collections /[/] {self._active_collection_name}  [dim]{total}[/]")
        header.add_class("col-header-detail")
        hints.update("[dim]↵ jump  ·  a add  ·  x remove  ·  J/K reorder  ·  r rename  ·  Esc ← list[/]")
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

    def _generate_collection_name(self, chapter_ref: str, response: str) -> str:
        parts = chapter_ref.split("-")
        if len(parts) >= 2:
            book = queries.get_book(self.conn, parts[0])
            book_name = book.name if book else parts[0]
            prefix = f"{book_name} {parts[1]}"
        else:
            prefix = chapter_ref
        clean = re.sub(r'[*_`#\[\]]', '', response)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > 40:
            clean = clean[:40].rsplit(' ', 1)[0]
        return f"{prefix} · {clean}" if clean else prefix

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
        m = re.match(r'^\s*(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(\d+)\s*$', text.strip())
        if not m:
            return None
        book_raw, chapter, verse = m.group(1).strip(), m.group(2), m.group(3)
        abbrev = normalize_book_name(book_raw)
        if not abbrev:
            return None
        verse_ref = f"{abbrev}-{chapter}-{verse}"
        return verse_ref if queries.get_verse(self.conn, verse_ref) is not None else None

    # ── Input submitted ───────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            question = event.value.strip()
            if question and self._current_chapter_ref:
                event.input.clear()
                self._send_chat(question)
            return

        if event.input.id != "collections-add-input":
            return

        value = event.value.strip()
        mode = self._col_input_mode
        self._hide_add_bar()
        self.focus()
        if not value:
            return

        if mode == "new":
            queries.create_collection(self.conn, value)
            self._update_collections_tab_label()
            self._render_collections_list()
            self.app.notify(f"Created '{value}'", timeout=2)

        elif mode == "rename":
            if self._active_collection_id is not None:
                queries.rename_collection(self.conn, self._active_collection_id, value)
                self._active_collection_name = value
                self._render_collection_detail()
                self._update_collections_tab_label()

        elif mode == "rename_list":
            col_id = self._rename_list_col_id()
            if col_id is not None:
                queries.rename_collection(self.conn, col_id, value)
                self._render_collections_list()
                self._update_collections_tab_label()

        elif mode == "add_verse":
            ref = self._parse_verse_input(value)
            if ref:
                if self._active_collection_id is not None:
                    queries.add_verse_to_collection(self.conn, self._active_collection_id, ref)
                    self._render_collection_detail()
                    self.app.notify("Verse added", timeout=2)
            else:
                self.app.notify(f"Verse not found: {value}", severity="warning", timeout=3)

        elif mode == "save_temp":
            if self._temp_refs:
                col_id = queries.create_collection(self.conn, value)
                for verse_ref, _ in self._temp_refs:
                    queries.add_verse_to_collection(self.conn, col_id, verse_ref)
                self._temp_refs = None
                self._temp_name = ""
                self._render_collections_list()
                self._update_collections_tab_label()
                self.app.notify(f"Saved as '{value}'", timeout=2)
