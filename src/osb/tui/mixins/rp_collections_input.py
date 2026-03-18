"""Input handling for collections tab."""

from textual.widgets import Input

from osb.db import queries


class RpCollectionsInputMixin:
    """Input submission handler for collections tab."""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle text input submission in collections."""
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
