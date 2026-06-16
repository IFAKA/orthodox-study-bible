# Orthodox Study Bible TUI

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-000000.svg)](https://textual.textualize.io/)

A modern, offline-first Terminal User Interface (TUI) for studying the **Orthodox Study Bible (OSB)**. Built with Python and the [Textual](https://textual.textualize.io/) framework, it combines traditional scripture study with modern features like local AI assistance and full-text search.

![dark theme screenshot placeholder](https://github.com/user-attachments/assets/af3cadd5-ec3e-4c24-be60-04090d966d3b)

---

## 📖 Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Setup & Installation](#setup--installation)
- [Keybindings](#keybindings)
- [Concepts](#concepts)
- [AI Chat (Optional)](#ai-chat-optional)
- [Developer Guide](#developer-guide)
- [SEO & AI Optimization](#seo--ai-optimization)
- [License](#license)

---

![commentary](https://github.com/user-attachments/assets/3571ab38-7702-452d-98e1-d27f1b4288ed)

![chat](https://github.com/user-attachments/assets/37c614ca-8b97-4fc1-8f7f-a2fe34660476)

![notes](https://github.com/user-attachments/assets/471dbc4d-d44a-49e6-b3ad-146d6a217213)

![search](https://github.com/user-attachments/assets/12848dc3-6819-438f-89f5-a2ac8e30e0c7)

![searchinline](https://github.com/user-attachments/assets/383a81e9-afcc-4c89-a07e-90f1f2f48769)

## ✨ Features

- **Full Scripture Text**: Complete 78-book canon of the OSB (35,945 verses).
- **Commentary & Cross-References**: Integrated study notes available instantly for every verse.
- **Full-Text Search (FTS5)**: Blazing fast search across all books and commentary.
- **Personal Study Tools**: Add annotations, bookmarks, and color-coded highlights.
- **Daily Lectionary**: Today's readings (Menaion and Paschal cycles, Julian calendar) shown automatically on first launch each day.
- **Local AI Chat**: Stream theological inquiries directly through [Ollama](https://ollama.ai) (100% private, no cloud).
- **Modern UI**: Dark and Sepia themes, responsive layout, and Vim-style navigation.
- **Markdown Export**: Export your personal notes and study progress to Markdown.

---

## 🛠 Requirements

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** (highly recommended) or pip.
- **Orthodox Study Bible EPUB**: You must provide your own legally acquired copy of the OSB EPUB.

---

## 🚀 Setup & Installation

### One-Command Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/IFAKA/orthodox-study-bible/main/install.sh | sh
osb
```

The scripture database is downloaded automatically on first launch (~15 MB, one time only). The app works fully offline after that.

### Manual Install

```bash
uv tool install git+https://github.com/IFAKA/orthodox-study-bible
osb
```

### From Source (with EPUB)

```bash
git clone https://github.com/IFAKA/orthodox-study-bible
cd orthodox-study-bible
cp /path/to/the-orthodox-study-bible.epub .
uv run osb
```

---

## ⌨️ Keybindings

OSB is modal: which keys are active depends on which pane has focus. The app opens with the **Scripture** pane focused. Press `l` to move into the right pane, `h` (or `Esc`) to come back, and `t` to toggle the sidebar.

### Global (available anywhere)

| Key | Action |
|-----|--------|
| `t` | toggle the book-tree sidebar |
| `F` | full-text search |
| `N` | open **My Notes** (all annotations & bookmarks) |
| `p` | reading-progress overview |
| `L` | jump to today's primary feast reading (if any) |
| `?` | context help |
| `T` | toggle Dark / Sepia theme |
| `:` | command mode (e.g. type `Gen 3:5` to jump there) |
| `q` | quit (or close the current modal) |

### Scripture pane (reading)

| Key | Action |
|-----|--------|
| `j` / `k` | next / previous verse |
| `J` / `K` | previous / next chapter |
| `g` `g` | first verse of the chapter |
| `G` / `g` `G` | last verse of the chapter |
| `g` `?` | open the glossary |
| `space` | page down |
| `ctrl+d` / `ctrl+u` | half-page down / up |
| `/` | find within the reader |
| `o` | add or edit an annotation on the focused verse |
| `m` | cycle highlight color on the verse |
| `b` | bookmark the verse |
| `x` | show cross-references |
| `y` | copy the verse text |
| `C` | mark the chapter read (progress) |
| `a` | add the verse to a collection |
| `l` | open / focus the right pane |

### Right pane (Commentary · Chat · Notes · Collections)

Press `l` from the reader to focus this pane.

| Key | Action |
|-----|--------|
| `a` | cycle tabs: Commentary → Chat → Notes → Collections |
| `i` | focus the chat input (type a question) |
| `j` / `k` | scroll down / up |
| `r` | browse references from the last chat reply |
| `y` | copy the last AI response |
| `C` | clear the chat for this chapter |
| `Esc` / `h` | return focus to the scripture pane |

In the **Collections** tab: `enter` open · `n` new · `a` add current verse · `x` remove · `r` rename · `d` delete · `s` save · `J` / `K` reorder.

### Sidebar (book tree)

Press `t` to toggle, then navigate:

| Key | Action |
|-----|--------|
| `j` / `k` | move down / up |
| `l` / `enter` | open book / select chapter |
| `h` | collapse / go to parent |
| `space` / `o` | expand or collapse a node |
| `G` | jump to bottom |
| `/` | search · `q` / `Esc` close sidebar |

### My Notes screen (`N`)

| Key | Action |
|-----|--------|
| `e` | export annotations & bookmarks to Markdown |

---

## 📚 Concepts

OSB keeps several kinds of personal study data, each stored separately:

- **Bookmark** (`b`) — a single flagged verse you want to return to.
- **Annotation** (`o`) — a personal text note attached to one verse.
- **Highlight** (`m`) — a color marking on a verse; press `m` to cycle through the available colors.
- **Collection** (`a`) — a **named, ordered list of verses**, like a playlist or themed study set (e.g. "Verses on mercy"). Build one manually by pressing `a` on verses, or let the AI chat assemble one automatically from the scripture references it cites in a reply. Manage collections in the right pane's **Collections** tab. (This is *not* the same as bookmarks — a bookmark is one flagged verse; a collection is a curated, reorderable group.)
- **Lectionary** — the Orthodox cycle of daily readings (Julian calendar; Menaion and Paschal cycles). Today's readings appear automatically the first time you open the app each day; `L` jumps the reader to today's primary feast reading when there is one.

---

## 🤖 AI Chat (Optional)

Enhance your study with local AI. Install [Ollama](https://ollama.ai) and pull your preferred model:

```bash
ollama serve
ollama pull llama3.2
```

In the app, press `l` to focus the right pane, then `a` to cycle to the **Chat** tab (Commentary → Chat). Press `i` to type a question. All conversations remain on your machine.

---

## 👨‍💻 Developer Guide

### Verifying Features
- Run `uv run osb --reimport` to test the EPUB parser.
- Run `uv run osb --reset` to wipe local data while keeping scripture.
- Check `uv run osb --db-path` for the SQLite file location.

### Running Tests
Ensure an OSB EPUB is present in the root directory:
```bash
uv run pytest tests/test_parser.py
```

---

## 🔍 SEO & AI Optimization

This project is optimized for both search engines and AI agents.
- **Structured Metadata**: Defined in `pyproject.toml`.
- **AI Context**: See [llms.txt](llms.txt) for a technical summary optimized for Large Language Models.
- **Social Preview**: [Instructions for adding a repository social image](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/configuring-a-social-preview-for-your-repository).

---

## 📜 License

- **Code**: MIT License (see [LICENSE](LICENSE)).
- **Content**: The Orthodox Study Bible text is copyright © St. Athanasius Orthodox Academy. This software is a tool for personal study and does not distribute copyrighted text.

---

Built with ❤️ for the Orthodox community.
