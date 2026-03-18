"""Command parsing and handling for MainScreen colon commands."""

import re

from osb.db import queries


def handle_command(screen, cmd: str) -> None:
    """Dispatch a colon command. Supported: q, and verse refs like 'Gen 3:5'."""
    if cmd == "q":
        screen.action_quit_app()
        return

    match = re.match(
        r'^([1-3]?\s*[A-Za-z]+\.?\s*)?(\d+)(?:[:\s](\d+))?$',
        cmd.strip()
    )
    if match:
        book_part = (match.group(1) or "").strip().rstrip(".")
        chapter_num = int(match.group(2))
        verse_num = int(match.group(3)) if match.group(3) else 1

        if book_part:
            books = queries.get_all_books(screen.conn)
            book_ref = None
            book_part_lower = book_part.lower()
            for book in books:
                if (book.name.lower().startswith(book_part_lower) or
                        book.ref.lower().startswith(book_part_lower)):
                    book_ref = book.ref
                    break
            if book_ref is None:
                screen._status_error(f"Unknown book: {book_part}")
                return
        else:
            if screen._current_chapter_ref:
                book_ref = screen._current_chapter_ref.split("-")[0]
            else:
                screen._status_error("No current book")
                return

        chapter_ref = f"{book_ref}-{chapter_num}"
        verse_ref = f"{book_ref}-{chapter_num}-{verse_num}"
        screen._load_chapter(chapter_ref, focus_verse_ref=verse_ref)
        from osb.tui.widgets.scripture_pane import ScripturePane
        screen.query_one("#scripture-pane", ScripturePane).focus()
    else:
        screen._status_error(f"Unknown command: {cmd}")
