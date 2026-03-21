"""Collections queries."""

import sqlite3
from typing import Optional

from osb.models import Collection, CollectionItem, Verse


def get_all_collections(conn: sqlite3.Connection) -> list[Collection]:
    rows = conn.execute(
        "SELECT id, name, created_at, updated_at FROM collections ORDER BY updated_at DESC"
    ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection(conn: sqlite3.Connection, collection_id: int) -> Optional[Collection]:
    row = conn.execute(
        "SELECT id, name, created_at, updated_at FROM collections WHERE id=?", (collection_id,)
    ).fetchone()
    return Collection(**dict(row)) if row else None


def create_collection(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute("INSERT INTO collections(name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def rename_collection(conn: sqlite3.Connection, collection_id: int, name: str) -> None:
    conn.execute(
        "UPDATE collections SET name=?, updated_at=datetime('now') WHERE id=?",
        (name, collection_id),
    )
    conn.commit()


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> None:
    conn.execute("DELETE FROM collections WHERE id=?", (collection_id,))
    conn.commit()


def get_collection_items(
    conn: sqlite3.Connection, collection_id: int
) -> list[tuple[CollectionItem, Verse]]:
    rows = conn.execute(
        """SELECT ci.id, ci.collection_id, ci.verse_ref, ci.position,
                  v.ref, v.chapter_ref, v.number, v.text
           FROM collection_items ci
           JOIN verses v ON v.ref = ci.verse_ref
           WHERE ci.collection_id=?
           ORDER BY ci.position, ci.id""",
        (collection_id,),
    ).fetchall()
    result = []
    for r in rows:
        item = CollectionItem(
            id=r["id"],
            collection_id=r["collection_id"],
            verse_ref=r["verse_ref"],
            position=r["position"],
        )
        verse = Verse(
            ref=r["ref"],
            chapter_ref=r["chapter_ref"],
            number=r["number"],
            text=r["text"],
        )
        result.append((item, verse))
    return result


def add_verse_to_collection(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str
) -> None:
    row = conn.execute(
        "SELECT MAX(position) FROM collection_items WHERE collection_id=?", (collection_id,)
    ).fetchone()
    next_pos = (row[0] or 0) + 1
    conn.execute(
        "INSERT OR IGNORE INTO collection_items(collection_id, verse_ref, position) VALUES (?, ?, ?)",
        (collection_id, verse_ref, next_pos),
    )
    conn.execute(
        "UPDATE collections SET updated_at=datetime('now') WHERE id=?", (collection_id,)
    )
    conn.commit()


def remove_verse_from_collection(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str
) -> None:
    conn.execute(
        "DELETE FROM collection_items WHERE collection_id=? AND verse_ref=?",
        (collection_id, verse_ref),
    )
    conn.commit()


def reorder_item(
    conn: sqlite3.Connection, collection_id: int, verse_ref: str, direction: int
) -> None:
    """Swap position with adjacent item. direction: +1 = down, -1 = up."""
    rows = conn.execute(
        "SELECT id, verse_ref, position FROM collection_items WHERE collection_id=? ORDER BY position, id",
        (collection_id,),
    ).fetchall()
    refs = [r["verse_ref"] for r in rows]
    if verse_ref not in refs:
        return
    idx = refs.index(verse_ref)
    swap_idx = idx + direction
    if swap_idx < 0 or swap_idx >= len(rows):
        return
    pos_a = rows[idx]["position"]
    pos_b = rows[swap_idx]["position"]
    if pos_a == pos_b:
        pos_b = pos_a + 1
    conn.execute(
        "UPDATE collection_items SET position=? WHERE id=?", (pos_b, rows[idx]["id"])
    )
    conn.execute(
        "UPDATE collection_items SET position=? WHERE id=?", (pos_a, rows[swap_idx]["id"])
    )
    conn.commit()


def get_collections_for_verse(conn: sqlite3.Connection, verse_ref: str) -> list[Collection]:
    rows = conn.execute(
        """SELECT c.id, c.name, c.created_at, c.updated_at
           FROM collections c
           JOIN collection_items ci ON ci.collection_id = c.id
           WHERE ci.verse_ref=?
           ORDER BY c.updated_at DESC""",
        (verse_ref,),
    ).fetchall()
    return [Collection(**dict(r)) for r in rows]


def get_collection_item_count(conn: sqlite3.Connection, collection_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM collection_items WHERE collection_id=?", (collection_id,)
    ).fetchone()
    return row[0] if row else 0
