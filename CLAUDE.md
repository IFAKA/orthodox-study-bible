# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
uv run osb

# Run with flags
uv run osb --reimport     # Force re-parse EPUB (keeps annotations)
uv run osb --reset        # Clear personal data, keep scripture
uv run osb --uninstall    # Remove all app data

# Run tests (requires the-orthodox-study-bible.epub at project root)
pytest tests/test_parser.py

# Install globally
uv tool install .
```

Tests are auto-skipped if the EPUB file is absent. There is no lint/format config.

## Architecture

An offline TUI application for studying the Orthodox Study Bible. Parses a user-provided EPUB into SQLite, then renders a 3-pane terminal reader with commentary, annotations, bookmarks, highlights, lectionary, and optional Ollama AI chat.

**Startup flow:** `__main__.py` → find EPUB → open DB → `run_migrations()` → `SplashScreen` → check verse count → `ImportScreen` (first run) or `MainScreen`.

**3-pane layout in `MainScreen`:**
- Left: `BookTree` — book/chapter navigation
- Center: `ScripturePane` — verse blocks with vim-style j/k/J/K navigation
- Right: `RightPane` — tabbed Commentary / Chat (Ollama) / Notes

**Key module groups:**

| Group | Path | Purpose |
|-------|------|---------|
| DB | `src/osb/db/` | `schema.py` (DDL + KNOWN_VERSE_COUNTS), `migrations.py`, `queries.py` (40+ typed query functions) |
| Importer | `src/osb/importer/` | `epub_parser.py` (EPUB → SQLite), `structure.py` (76-book canon), `lectionary.py` (Julian Pascha + Menaion/Paschal cycle) |
| TUI | `src/osb/tui/` | `app.py` (root), `screens/`, `widgets/`, `mixins/`, `styles/` |

**State persistence:**
- User data (annotations, bookmarks, highlights, chat) written to SQLite immediately on mutation
- Session state (last verse/chapter ref) stored in `session` key-value table
- Widget communication via Textual messages (e.g., `VerseFocused`, `ChapterChangeRequested`)

## Key Technical Details

**EPUB parsing:** Verse IDs extracted from `<sup>` elements with pattern `{BookCode}_vchap{ch}-{v}`. Book codes mapped via `EPUB_CODE_TO_ABBREV` in `epub_parser.py`. Uses LXX versification (differs from Protestant counts).

**Verse text** lives in CSS classes: `chapter1`, `rindent`, `olstyle`, `psalm2`.
**Commentary** lives in: `p.tx`, `p.tx1`, `p.bookstarttxt`, `p.sub1`.

**FTS search:** SQLite FTS5 with fallback to rapidfuzz fuzzy matching.

**Vim chords:** `ChordMixin` in `mixins/chord_handler.py` implements `gg` / `gG` / `gr` with 500ms timeout.

**Background tasks:** Use `@work(thread=True)` from Textual for search, import, and Ollama streaming.

**Database path:** `~/Library/Application Support/osb/osb.db` on macOS (via platformdirs).

**Ollama:** Optional, `http://localhost:11434`, model `llama3.2:3b`, graceful degradation if unavailable.

**Themes:** Dark + Sepia, CSS-based via `tui/styles/themes.tcss`, toggled dynamically.
