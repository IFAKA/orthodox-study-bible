# Orthodox Study Bible

A fully offline TUI app for studying the Orthodox Study Bible. Built with Python + Textual.

![dark theme screenshot placeholder](https://placehold.co/800x400/1a1a1a/c9a84c?text=Orthodox+Study+Bible+TUI)

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
