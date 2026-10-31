#!/usr/bin/env python3
"""Remove an entry and its cover.

Renumbering is automatic: every save recomputes ids from the list position.
The cover file is deleted with the entry because an unreferenced file on disk
is a validation error, and leaving it behind accumulates orphan images.

Examples
--------
    python3 scripts/remove.py --cat animanga --title "Vagabond"
    python3 scripts/remove.py --cat shows --title "Raakh" --exact
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import archive as A


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Remove an entry.")
    parser.add_argument("--cat", required=True, choices=A.category_ids())
    parser.add_argument("--title", required=True, help="substring match is fine")
    parser.add_argument(
        "--exact",
        action="store_true",
        help="require a whole-title match; needed for short titles",
    )
    args = parser.parse_args(argv)

    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1

    entry = entries.pop(index)
    cover = A.ROOT / entry["cover_url"]
    note = ""

    # Move the cover aside before saving. save() validates that every file on
    # disk is referenced, so deleting after the write would fail its orphan
    # check. Restoring on failure keeps a bad write from pointing an entry at
    # a file that is no longer there.
    stash_dir: Path | None = None
    stash: Path | None = None
    if cover.is_file():
        stash_dir = Path(tempfile.mkdtemp(prefix="archive-remove-"))
        stash = stash_dir / cover.name
        shutil.move(cover, stash)

    try:
        A.save(args.cat, entries)
    except Exception:
        if stash and stash.exists():
            shutil.move(stash, cover)
        raise
    else:
        if stash:
            stash.unlink()
            note = f", deleted {entry['cover_url']}"
    finally:
        if stash_dir:
            shutil.rmtree(stash_dir, ignore_errors=True)

    fresh = A.load(args.cat)
    print("removed:")
    print("  " + A.describe(entry))
    print(f"  {args.cat} now has {len(fresh)} entries{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
