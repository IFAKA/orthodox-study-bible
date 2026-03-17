# Orthodox Study Bible

A fully offline TUI app for studying the Orthodox Study Bible. Built with Python + Textual.

![dark theme screenshot placeholder](https://github.com/user-attachments/assets/af3cadd5-ec3e-4c24-be60-04090d966d3b)


## Features

- Full scripture text from the OSB (78 books, 35,945 verses)
- Commentary and cross-references per verse
- Full-text search (FTS5)
- Personal annotations, highlights, and bookmarks
- Daily lectionary (Menaion + Paschal cycle, Julian calendar)
- Optional local AI chat via Ollama (streams, no cloud)
- Sepia theme, Markdown export, reading progress
- Vim-style keybindings, fully keyboard-driven

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Your own copy of the Orthodox Study Bible EPUB (not included)

## Setup

```bash
git clone https://github.com/IFAKA/orthodox-study-bible
cd orthodox-study-bible

# Place your EPUB in the project root or data/
cp /path/to/the-orthodox-study-bible.epub .

# Install and run (first launch imports the EPUB automatically)
uv run osb
```

Or install globally:

```bash
uv tool install .
osb
```

The first run shows an import screen (~30–60 seconds). After that, it goes straight to the reader.

## Keybindings

| Key | Action |
|-----|--------|
| `j` / `k` | next / previous verse |
| `J` / `K` | next / previous chapter |
| `h` / `l` | focus left / right pane |
| `g` `g` | first verse of chapter |
| `G` | last verse of chapter |
| `t` | toggle book tree sidebar |
| `/` | search |
| `o` | edit annotation for focused verse |
| `m` | cycle highlight color (yellow → green → blue → pink → off) |
| `b` | bookmark verse |
| `a` | toggle Commentary / Chat tab |
| `L` | jump to today's lectionary reading |
| `N` | My Notes (all annotations + bookmarks) |
| `T` | toggle dark / sepia theme |
| `E` | export annotations to Markdown |
| `q` | quit / close modal |

## Developer: verifying features

After setup, use these steps to manually verify every major feature:

**Navigation**
- `j` / `k` — move between verses; commentary updates in right pane
- `J` / `K` — jump between chapters; book tree selection follows
- `g g` — jump to first verse of chapter
- `G` — jump to last verse of chapter
- `h` / `l` — shift focus between BookTree ↔ ScripturePane ↔ RightPane

**Search**
- `/` — open search, type a word (e.g. `mercy`), `Enter` to jump, `Escape` to cancel

**Annotations & highlights**
- `o` — open annotation editor on focused verse, type a note, save
- `m` — cycle highlight color on focused verse (yellow → green → blue → pink → off)
- `b` — bookmark focused verse

**My Notes screen**
- `N` — open Notes screen showing all annotations and bookmarks; `Escape` to return

**Lectionary**
- `L` — open today's lectionary modal (shows readings if it's a feast day, otherwise "No specific readings found for today" — this is correct for non-feast days)

**Tabs**
- `a` — toggle Commentary ↔ Chat tab in right pane

**Theme**
- `T` — toggle dark ↔ sepia theme

**Export**
- `E` — export all annotations to a Markdown file (check terminal output for path)

**Sidebar**
- `t` — toggle BookTree sidebar visibility

**Quit modal**
- `q` — open quit confirmation; `y` to quit, `n` / `Escape` to cancel

**CLI flags**
```bash
uv run osb --reimport     # re-parse EPUB (keeps notes/bookmarks)
uv run osb --reset        # wipe personal data, keep scripture
uv run osb --db-path      # print DB file path
uv run osb --uninstall    # remove all app data
```

**Tests** (requires EPUB at project root)
```bash
pytest tests/test_parser.py
```

## AI Chat (optional)

Install and run [Ollama](https://ollama.ai), then switch to the Chat tab with `a`. The app works fully without it.

```bash
ollama serve
ollama pull llama3.2  # or whichever model you prefer
```

Change the model in `src/osb/config.py` (`OLLAMA_MODEL`).

## Data location

- macOS: `~/Library/Application Support/osb/osb.db`
- Linux: `$XDG_DATA_HOME/osb/osb.db`

## Useful commands

```bash
osb --reimport          # re-parse EPUB, keeps your annotations/bookmarks
osb --reset             # clear personal data, keep scripture
osb --uninstall         # remove all app data
osb --db-path           # print the DB path
```

## Uninstall

```bash
osb --uninstall         # removes app data
uv tool uninstall orthodox-study-bible  # removes the command
```

## License

Personal use. The Orthodox Study Bible text is copyright St. Athanasius Orthodox Academy.
