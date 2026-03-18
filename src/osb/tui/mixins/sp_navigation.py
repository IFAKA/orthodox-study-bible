"""ScripturePane navigation + scroll mixin."""

from __future__ import annotations

import time


class SpNavigationMixin:
    """Verse/chapter navigation and scroll helpers for ScripturePane."""

    _SCROLLOFF = 4       # rows of context to keep above/below focused verse
    _ACCEL_WINDOW = 0.20  # seconds — keypresses within this window accumulate acceleration

    def action_next_verse(self) -> None:
        step = self._accel_step(+1)
        new_idx = self._focused_idx + step
        if new_idx < len(self._verse_refs):
            self._set_focus_idx(new_idx)
        else:
            self.post_message(self.ChapterChangeRequested(+1))

    def action_prev_verse(self) -> None:
        step = self._accel_step(-1)
        new_idx = self._focused_idx - step
        if new_idx >= 0:
            self._set_focus_idx(new_idx)
        else:
            self.post_message(self.ChapterChangeRequested(-1))

    def action_next_chapter(self) -> None:
        self.post_message(self.ChapterChangeRequested(+1))

    def action_prev_chapter(self) -> None:
        self.post_message(self.ChapterChangeRequested(-1))

    def action_goto_first_verse(self) -> None:
        if self._verse_refs:
            self._set_focus_idx(0)

    def action_last_verse(self) -> None:
        if self._verse_refs:
            self._set_focus_idx(len(self._verse_refs) - 1)

    def action_goto_reference(self) -> None:
        self.screen.action_goto_reference()

    def action_page_down(self) -> None:
        self.scroll_page_down()

    def action_half_page_down(self) -> None:
        self.scroll_down(self.size.height // 2)

    def action_half_page_up(self) -> None:
        self.scroll_up(self.size.height // 2)

    def _set_focus_idx(self, idx: int) -> None:
        if self._verse_refs and 0 <= self._focused_idx < len(self._verse_refs):
            old_block = self._blocks.get(self._verse_refs[self._focused_idx])
            if old_block:
                old_block.focused = False

        self._focused_idx = idx

        if self._verse_refs and 0 <= idx < len(self._verse_refs):
            new_ref = self._verse_refs[idx]
            new_block = self._blocks.get(new_ref)
            if new_block:
                new_block.focused = True
                self._scroll_to_focused(new_block)
            self.post_message(self.VerseFocused(new_ref))

    def _accel_step(self, direction: int) -> int:
        """Return step size; grows the longer j/k is held."""
        now = time.monotonic()
        if now - self._last_nav_time < self._ACCEL_WINDOW and direction == self._last_nav_dir:
            self._accel_count = min(self._accel_count + 1, 24)
        else:
            self._accel_count = 0
        self._last_nav_time = now
        self._last_nav_dir = direction
        c = self._accel_count
        if c < 6:  return 1
        if c < 12: return 3
        if c < 18: return 6
        return 12

    def _scroll_to_focused(self, block) -> None:
        """Scroll with vim-style scrolloff."""
        try:
            region = block.virtual_region
        except Exception:
            block.scroll_visible(animate=True)
            return
        viewport_h = self.scrollable_content_region.height
        current_y = self.scroll_y
        want_above = region.y - self._SCROLLOFF
        want_below = region.y + region.height + self._SCROLLOFF - viewport_h
        fast = self._accel_count >= 6
        if current_y > want_above:
            self.scroll_to(0, max(0, want_above), animate=not fast, duration=0.2, easing="out_cubic")
        elif current_y < want_below:
            self.scroll_to(0, want_below, animate=not fast, duration=0.2, easing="out_cubic")
