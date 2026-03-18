"""HelpScreen — keybinding reference overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Static

_HELP_TEXT = """\
[bold yellow]Navigation[/]
  j / k          Next / previous verse
  J / K          Previous / next chapter
  gg / gG        First / last verse
  space          Page down
  ctrl+d / u     Half page down / up

[bold yellow]Actions[/]
  b              Bookmark verse
  m              Cycle highlight color
  o              Annotate verse
  x              Cross-references
  y              Copy verse to clipboard
  C              Toggle chapter complete
  a              Add to collection

[bold yellow]Panes & Navigation[/]
  t              Toggle book tree sidebar
  l              Toggle commentary / chat pane
  h              Focus scripture (from any pane)
  :Book Ch:V     Go to verse  (e.g.  :Gen 3:5)
  :q             Quit
  /              Search in current chapter
  F              Search entire Bible

[bold yellow]App[/]
  N              My notes
  L              Daily lectionary
  p              Progress tracker
  T              Toggle theme (dark / sepia)
  ?              This help screen
  g?             Glossary
  q              Quit
"""


class HelpScreen(ModalScreen):
    """Keybinding reference. Dismiss with Escape or ?."""

    BINDINGS = [
        Binding("escape", "dismiss", show=False),
        Binding("?", "dismiss", show=False),
        Binding("q", "dismiss", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Static(id="help-dialog"):
            yield Label("[bold]Keyboard Reference[/bold]", id="help-title")
            yield Static(_HELP_TEXT, id="help-body")
