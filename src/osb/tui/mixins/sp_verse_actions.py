"""ScripturePane verse mutation actions mixin."""

from __future__ import annotations

import subprocess

from osb.db import queries


class SpVerseActionsMixin:
    """Verse highlight, bookmark, annotation, copy, collection actions for ScripturePane."""

    def action_annotate(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            self.app.screen.action_annotate(ref)

    def action_cycle_highlight(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            new_color = queries.cycle_highlight(self.conn, ref)
            block = self._blocks.get(ref)
            if block:
                block.highlight_color = new_color

    def action_bookmark(self) -> None:
        ref = self.focused_verse_ref
        if ref:
            added = queries.toggle_bookmark(self.conn, ref)
            block = self._blocks.get(ref)
            if block:
                block.has_bookmark = added

    def action_crossrefs(self) -> None:
        if not self._chapter_ref or not self._verse_refs:
            return
        verse_ref = self._verse_refs[self._focused_idx]
        xrefs = queries.get_cross_refs(self.conn, verse_ref)
        if not xrefs:
            self.app.notify("No cross-references for this verse", timeout=2)
            return
        from osb.tui.screens.crossref_screen import CrossRefScreen
        from osb.tui.screens.main_screen import MainScreen

        def callback(ref: str | None) -> None:
            if ref is not None:
                self.app.query_one(MainScreen)._navigate_to_verse(ref)

        self.app.push_screen(CrossRefScreen(self.conn, verse_ref), callback)

    def action_copy_verse(self) -> None:
        ref = self.focused_verse_ref
        if not ref:
            return
        v = queries.get_verse(self.conn, ref)
        if not v:
            return
        parts = ref.split("-")
        book = queries.get_book(self.conn, parts[0])
        book_name = book.name if book else parts[0]
        ch_num = parts[1] if len(parts) > 1 else "?"
        v_num = parts[2] if len(parts) > 2 else "?"
        text = f"{book_name} {ch_num}:{v_num} — {v.text}"
        try:
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            self.app.notify("Verse copied", timeout=2)
        except Exception:
            self.app.notify("Copy failed (pbcopy not available)", timeout=2)

    def action_add_to_collection(self) -> None:
        ref = self.focused_verse_ref
        if not ref:
            return
        from osb.tui.screens.add_to_collection_screen import AddToCollectionScreen

        def callback(collection_id: int | None) -> None:
            if collection_id is not None:
                queries.add_verse_to_collection(self.conn, collection_id, ref)
                self.app.notify("Added to collection", timeout=2)
                for screen in self.app.screen_stack:
                    try:
                        rp = screen.query_one("#right-pane")
                        rp._update_collections_tab_label()
                        rp.refresh_collections_view()
                        break
                    except Exception:
                        continue

        self.app.push_screen(AddToCollectionScreen(ref, self.conn), callback)

    def action_toggle_complete(self) -> None:
        if not self._chapter_ref:
            return
        from osb.tui.widgets.scripture_pane import ScripturePane
        if queries.is_chapter_complete(self.conn, self._chapter_ref):
            queries.unmark_chapter_complete(self.conn, self._chapter_ref)
            self.app.notify("Chapter unmarked", timeout=2)
        else:
            queries.mark_chapter_complete(self.conn, self._chapter_ref)
            self.app.notify("Chapter marked complete ✓", timeout=2)
        self.post_message(ScripturePane.ChapterCompletionChanged(self._chapter_ref))
