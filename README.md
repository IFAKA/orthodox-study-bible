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
- **Daily Lectionary**: Built-in tracking for the Menaion and Paschal cycles (Julian calendar).
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
| `m` | cycle highlight color |
| `b` | bookmark verse |
| `a` | toggle Commentary / Chat tab |
| `L` | today's lectionary readings |
| `N` | My Notes (all annotations + bookmarks) |
| `T` | toggle Dark / Sepia theme |
| `E` | export annotations to Markdown |
| `q` | quit / close modal |

---

## 🤖 AI Chat (Optional)

Enhance your study with local AI. Install [Ollama](https://ollama.ai) and pull your preferred model:

```bash
ollama serve
ollama pull llama3.2
```

Switch to the **Chat** tab in the app with `a`. All conversations remain on your machine.

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
