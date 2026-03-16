"""Dev tool: inspect HTML class names in the EPUB to guide parser development.

Usage:
    python -m osb.importer.epub_inspector data/osb.epub
"""

import sys
from collections import Counter
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub


def inspect_epub(epub_path: Path) -> None:
    print(f"Inspecting: {epub_path}")
    try:
        book = epub.read_epub(str(epub_path), options={"ignore_ncx": True})
    except Exception as e:
        print(f"ERROR reading EPUB: {e}")
        print("EPUB may be DRM-protected. Try removing DRM or using a DRM-free edition.")
        return

    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    print(f"Total HTML items: {len(items)}")

    # Pick a sample of items spread across the book
    sample_indices = [0, len(items) // 5, len(items) // 3, len(items) // 2,
                      2 * len(items) // 3, len(items) - 1]
    sample_items = [items[i] for i in sample_indices if i < len(items)]

    all_classes: Counter = Counter()
    tag_class_examples: dict[str, list[str]] = {}

    print("\n" + "=" * 60)
    for item in sample_items:
        content = item.get_content()
        if len(content) < 100:
            print(f"  [SKIP - too short] {item.get_name()}")
            continue

        soup = BeautifulSoup(content, "lxml")
        print(f"\n--- {item.get_name()} ({len(content)} bytes) ---")

        # Gather all class attributes
        for tag in soup.find_all(True):
            classes = tag.get("class", [])
            if isinstance(classes, str):
                classes = [classes]
            for cls in classes:
                all_classes[cls] += 1
                key = f"{tag.name}.{cls}"
                if key not in tag_class_examples:
                    text = tag.get_text()[:80].replace("\n", " ").strip()
                    tag_class_examples[key] = text

        # Show a structural preview
        body = soup.find("body")
        if body:
            children = list(body.children)
            top_tags = [
                c for c in children
                if hasattr(c, "name") and c.name
            ][:20]
            for tag in top_tags:
                cls = " ".join(tag.get("class", []))
                text = tag.get_text()[:60].replace("\n", " ").strip()
                print(f"  <{tag.name} class='{cls}'> {text!r}")

    print("\n" + "=" * 60)
    print("TOP CSS CLASSES ACROSS SAMPLE:")
    for cls, count in all_classes.most_common(40):
        example = ""
        for key, ex in tag_class_examples.items():
            if key.endswith(f".{cls}"):
                tag_part = key.split('.')[0]
                ex_short = ex[:50]
                example = f"  e.g. <{tag_part}> {ex_short!r}"
                break
        print(f"  {count:4d}x  .{cls}{example}")

    print("\n" + "=" * 60)
    print("FULL TAG.CLASS INDEX:")
    for key in sorted(tag_class_examples):
        val = tag_class_examples[key][:60]
        print(f"  {key}: {val!r}")

    # Show all item names for structural overview
    print("\n" + "=" * 60)
    print("ALL DOCUMENT ITEMS (first 30):")
    for item in items[:30]:
        name = item.get_name()
        size = len(item.get_content())
        print(f"  {name}  ({size} bytes)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m osb.importer.epub_inspector <path/to/osb.epub>")
        sys.exit(1)
    inspect_epub(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
