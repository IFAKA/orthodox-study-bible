"""Collections tab actions mixin for RightPane."""

from __future__ import annotations

from textual.widgets import ListItem, ListView

from osb.db import queries


class RpCollectionsMixin:
    """Collection navigation + mutation actions for RightPane."""

    def on_key(self, event) -> None:
        if self._awaiting_delete_confirm:
            if event.key == "y":
                self._do_col_delete()
                self._awaiting_delete_confirm = False
                event.stop()
            elif event.key in ("n", "escape"):
                self._awaiting_delete_confirm = False
                self.app.notify("Cancelled", timeout=1)
                event.stop()

    # ── Cursor helpers ────────────────────────────────────────────────────────

    def _col_current_item(self) -> ListItem | None:
        try:
            return self.query_one("#collections-list", ListView).highlighted_child
        except Exception:
            return None

    def _col_current_index(self) -> int:
        try:
            return self.query_one("#collections-list", ListView).index or 0
        except Exception:
            return 0

    # ── Select / open ─────────────────────────────────────────────────────────

    def action_col_select(self) -> None:
        if self._collections_view == "list":
            self._col_open_or_save()
        else:
            self._col_jump_to_verse()

    def _col_open_or_save(self) -> None:
        item = self._col_current_item()
        if item is None:
            return
        if getattr(item, "_is_temp", False):
            self._show_add_bar("save_temp", "Save as: ", self._temp_name)
            return
        col_id = getattr(item, "_collection_id", None)
        col_name = getattr(item, "_col_name", "")
        if col_id is None:
            return
        self._active_collection_id = col_id
        self._active_collection_name = col_name
        self._collections_view = "detail"
        self._visited_refs = set()
        self._render_collection_detail()

    def _col_jump_to_verse(self) -> None:
        if self._active_collection_id is None:
            return
        item = self._col_current_item()
        idx = self._col_current_index()
        if item is None:
            return
        verse_ref = getattr(item, "_verse_ref", None)
        if verse_ref is None:
            return
        self._visited_refs.add(verse_ref)
        self._render_collection_detail()
        try:
            lv = self.query_one("#collections-list", ListView)
            lv.index = min(idx, len(list(lv.children)) - 1)
        except Exception:
            pass
        from osb.tui.screens.main_screen import MainScreen
        for screen in self.app.screen_stack:
            if isinstance(screen, MainScreen):
                screen._navigate_to_verse(verse_ref)
                break

    # ── Add / remove / rename / delete ───────────────────────────────────────

    def action_col_new(self) -> None:
        self._show_add_bar("new", "Name: ", "")

    def action_col_add_verse(self) -> None:
        self._show_add_bar("add_verse", "Add: ", "")

    def action_col_remove(self) -> None:
        if self._active_collection_id is None:
            return
        item = self._col_current_item()
        idx = self._col_current_index()
        if item is None:
            return
        verse_ref = getattr(item, "_verse_ref", None)
        if verse_ref is None:
            return
        queries.remove_verse_from_collection(self.conn, self._active_collection_id, verse_ref)
        self._visited_refs.discard(verse_ref)
        self._render_collection_detail()
        try:
            lv = self.query_one("#collections-list", ListView)
            children = list(lv.children)
            if children:
                lv.index = max(0, min(idx - 1, len(children) - 1))
        except Exception:
            pass
        self.app.notify("Verse removed", timeout=2)

    def action_col_rename(self) -> None:
        if self._collections_view == "detail" and self._active_collection_id is not None:
            self._show_add_bar("rename", "Rename: ", self._active_collection_name)
        elif self._collections_view == "list":
            item = self._col_current_item()
            if item is None:
                return
            if getattr(item, "_is_temp", False):
                self._show_add_bar("save_temp", "Save as: ", self._temp_name)
            else:
                self._show_add_bar("rename_list", "Rename: ", getattr(item, "_col_name", ""))

    def _rename_list_col_id(self) -> int | None:
        item = self._col_current_item()
        return getattr(item, "_collection_id", None) if item else None

    def action_col_delete(self) -> None:
        item = self._col_current_item()
        if item is None:
            return
        if getattr(item, "_is_temp", False):
            self._temp_refs = None
            self._temp_name = ""
            self._render_collections_list()
            self._update_collections_tab_label()
            self.app.notify("Unsaved collection discarded", timeout=2)
            return
        col_name = getattr(item, "_col_name", "?")
        self._awaiting_delete_confirm = True
        self.app.notify(f"Delete '{col_name}'? Press y to confirm", timeout=4)

    def _do_col_delete(self) -> None:
        item = self._col_current_item()
        idx = self._col_current_index()
        if item is None:
            return
        col_id = getattr(item, "_collection_id", None)
        col_name = getattr(item, "_col_name", "?")
        if col_id is None:
            return
        queries.delete_collection(self.conn, col_id)
        self._render_collections_list()
        self._update_collections_tab_label()
        try:
            lv = self.query_one("#collections-list", ListView)
            children = list(lv.children)
            if children:
                lv.index = max(0, min(idx - 1, len(children) - 1))
        except Exception:
            pass
        self.app.notify(f"Deleted '{col_name}'", timeout=2)

    # ── Save temp ─────────────────────────────────────────────────────────────

    def action_col_save_temp(self) -> None:
        if self._temp_refs is None:
            return
        try:
            from textual.widgets import TabbedContent
            tabs = self.query_one("#right-tabs", TabbedContent)
            if tabs.active != "tab-collections":
                self._collections_view = "list"
                tabs.active = "tab-collections"
                self.call_after_refresh(
                    lambda: self._show_add_bar("save_temp", "Save as: ", self._temp_name)
                )
                return
        except Exception:
            pass
        self._show_add_bar("save_temp", "Save as: ", self._temp_name)

    # ── Reorder ───────────────────────────────────────────────────────────────

    def action_col_move_down(self) -> None:
        self._col_reorder(+1)

    def action_col_move_up(self) -> None:
        self._col_reorder(-1)

    def _col_reorder(self, direction: int) -> None:
        if self._active_collection_id is None:
            return
        item = self._col_current_item()
        idx = self._col_current_index()
        if item is None:
            return
        verse_ref = getattr(item, "_verse_ref", None)
        if verse_ref is None:
            return
        items = queries.get_collection_items(self.conn, self._active_collection_id)
        new_idx = max(0, min(idx + direction, len(items) - 1))
        queries.reorder_item(self.conn, self._active_collection_id, verse_ref, direction)
        self._render_collection_detail()
        try:
            lv = self.query_one("#collections-list", ListView)
            lv.index = min(new_idx, len(list(lv.children)) - 1)
        except Exception:
            pass

    # ── Tab switch ────────────────────────────────────────────────────────────

    def action_col_go_chat(self) -> None:
        try:
            from textual.widgets import TabbedContent
            self.query_one("#right-tabs", TabbedContent).active = "tab-chat"
        except Exception:
            pass
