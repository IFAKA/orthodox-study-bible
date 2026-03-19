"""Commentary + Notes mixin for RightPane."""

from __future__ import annotations

from textual.timer import Timer
from textual.widgets import Label, Markdown

from osb.db import queries


class RpNotesMixin:
    """Notes editor + commentary rendering for RightPane."""

    def update_verse(self, verse_ref: str) -> None:
        self._current_verse_ref = verse_ref
        parts = verse_ref.split("-")
        if len(parts) >= 2:
            self._current_chapter_ref = "-".join(parts[:2])
        self._render_commentary(verse_ref)
        self._load_note(verse_ref)

    def _load_note(self, verse_ref: str) -> None:
        try:
            from osb.tui.mixins.rp_chat import _NotesEditor
            ann = queries.get_annotation(self.conn, verse_ref)
            self.query_one("#notes-editor", _NotesEditor).load_text(ann.body if ann else "")
            self.query_one("#notes-verse-label", Label).update(verse_ref)
        except Exception:
            pass

    def _save_current_note(self) -> None:
        if not self._current_verse_ref:
            return
        try:
            from osb.tui.mixins.rp_chat import _NotesEditor
            editor = self.query_one("#notes-editor", _NotesEditor)
            queries.save_annotation(self.conn, self._current_verse_ref, editor.text)
        except Exception:
            pass

    def focus_notes_editor(self) -> None:
        try:
            from osb.tui.mixins.rp_chat import _NotesEditor
            from textual.widgets import TabbedContent
            tabs = self.query_one("#right-tabs", TabbedContent)
            tabs.active = "tab-notes"
            self.call_after_refresh(lambda: self.query_one("#notes-editor", _NotesEditor).focus())
        except Exception:
            pass

    def on_text_area_changed(self, event) -> None:
        if event.text_area.id == "notes-editor":
            if self._save_timer:
                self._save_timer.stop()
            self._save_timer = self.set_timer(0.8, self._save_current_note)

    def _render_commentary(self, verse_ref: str) -> None:
        notes = queries.get_commentary_for_verse(self.conn, verse_ref)
        xrefs = queries.get_cross_refs(self.conn, verse_ref)
        lines = []
        has_commentary = bool(notes)
        if notes:
            for note in notes:
                lines.append(note.note_text)
                lines.append("")
        else:
            lines.append("*No commentary for this verse.*")
        if xrefs:
            lines.append("---")
            lines.append("**Cross-references:**")
            for xr in xrefs:
                if xr["to_ref"]:
                    lines.append(f"→ {xr['to_ref_text']} ({xr['to_ref']})")
                else:
                    lines.append(f"→ {xr['to_ref_text']}")
        try:
            self.query_one("#commentary-text", Markdown).update("\n".join(lines))
            self._update_commentary_tab_indicator(has_commentary)
        except Exception:
            pass

    def _update_commentary_tab_indicator(self, has_commentary: bool) -> None:
        """Update Commentary tab label with indicator if commentary exists."""
        try:
            from textual.widgets import TabPane, TabbedContent
            pane = self.query_one("#tab-commentary", TabPane)
            pane.label = ("● Commentary" if has_commentary else "Commentary")
            # Refresh the TabbedContent to display the updated label in real time
            tabs = self.query_one("#right-tabs", TabbedContent)
            tabs.refresh()
        except Exception:
            pass
