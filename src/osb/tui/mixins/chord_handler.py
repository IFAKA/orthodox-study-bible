"""ChordMixin: state machine for multi-key sequences (gg, gr, etc.).

Usage:
    class MyWidget(ChordMixin, Widget):
        def on_key(self, event: Key) -> None:
            if self.handle_chord(event):
                return
            # handle single-key bindings here
"""

from __future__ import annotations

from textual.widget import Widget

CHORD_TIMEOUT_MS = 500


class ChordMixin:
    """Mixin providing chord-key handling for Textual widgets.

    Subclasses must also inherit from Widget (or a subclass of it).
    """

    _pending_chord_key: str | None = None
    _chord_timer = None
    _vim_count: int = 0
    _vim_count_digits: str = ""

    def handle_chord(self, event) -> bool:
        """Process a key event for chord sequences.

        Returns True if the key was consumed as part of a chord (do not
        process further). Returns False if not part of a chord.
        """
        key = event.key

        # Absorb digit prefixes for vim count (e.g. 5G, 10G).
        # "0" is only a digit here when a count is already started (e.g. 10, 20).
        if key.isdigit() and (key != "0" or self._vim_count_digits):
            self._vim_count_digits += key
            self._vim_count = int(self._vim_count_digits)
            event.stop()
            return True

        if self._pending_chord_key is not None:
            first = self._pending_chord_key
            self._cancel_chord_timer()
            self._pending_chord_key = None
            if self._dispatch_chord(first, key):
                event.stop()
                return True
            # First key wasn't part of a chord — dispatch it alone, then
            # continue to process this key as a fresh keypress.
            self._dispatch_single(first)
            return False

        if key in self._chord_first_keys():
            self._pending_chord_key = key
            self._chord_timer = (self if hasattr(self, "set_timer") else None)
            if self._chord_timer is not None:
                self.set_timer(
                    CHORD_TIMEOUT_MS / 1000.0,
                    self._chord_timeout,
                    name="chord_timeout",
                )
            event.stop()
            return True

        # Key was not consumed — discard any stale count prefix.
        self._consume_vim_count()
        return False

    def _consume_vim_count(self, default: int = 0) -> int:
        """Return the accumulated vim count and reset it.

        Returns `default` if no count was typed.
        Always resets the count buffer.
        """
        n = self._vim_count if self._vim_count > 0 else default
        self._vim_count = 0
        self._vim_count_digits = ""
        return n

    def _chord_first_keys(self) -> set[str]:
        """Keys that could be the start of a chord. Override to extend."""
        return {"g"}

    def _dispatch_chord(self, first: str, second: str) -> bool:
        """Dispatch a completed chord. Return True if handled."""
        if first == "g" and second == "g":
            self.action_goto_first_verse()
            return True
        if first == "g" and second == "?":
            self.screen.action_glossary()
            return True
        return False

    def _dispatch_single(self, key: str) -> None:
        """Called when a chord first-key times out without a second key."""
        pass  # subclasses can implement g=go-to-line etc.

    def _cancel_chord_timer(self) -> None:
        self._chord_timer = None

    def _chord_timeout(self) -> None:
        """Called after CHORD_TIMEOUT_MS if no second key was pressed."""
        if self._pending_chord_key is not None:
            first = self._pending_chord_key
            self._pending_chord_key = None
            self._chord_timer = None
            self._dispatch_single(first)

    # ── Actions to override ──────────────────────────────────────────────────

    def action_goto_first_verse(self) -> None:
        """Jump to first verse of current chapter. Override in widget."""

    def action_last_verse(self) -> None:
        """Jump to last verse of current chapter. Override in widget."""
