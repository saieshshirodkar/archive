#!/usr/bin/env python3
"""Remove an entry and its cover.

Renumbering is automatic: every save recomputes ids from the list position.
The cover file goes with the entry because an unreferenced file on disk is a
validation error, and leaving it behind accumulates orphan images.

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remove an entry.")
    parser.add_argument("--cat", required=True, choices=A.category_ids())
    parser.add_argument("--title", required=True, help="substring match is fine")
    parser.add_argument(
        "--exact",
        action="store_true",
        help="require a whole-title match; needed for short titles",
    )
    return parser


def stash(cover: Path) -> Path:
    """Move a cover into a fresh temp directory and return its new path.

    save() refuses to run while an unreferenced file sits in the cover folder,
    so the image has to leave before the write, not after it.
    """
    directory = Path(tempfile.mkdtemp(prefix="archive-remove-"))
    stashed = directory / cover.name
    shutil.move(cover, stashed)
    return stashed


def run(args: argparse.Namespace) -> int:
    entries = A.load(args.cat)
    index = A.resolve_index(entries, args.title, strict=args.exact)
    if index is None:
        A.report_no_match(entries, args.title, args.cat, "--title", args.exact)
        return 1

    entry = entries.pop(index)
    cover = A.ROOT / entry["cover_url"]
    stashed = stash(cover) if cover.is_file() else None

    # Restore the cover if the write fails, so a rejected save cannot point the
    # remaining entries at a file that is no longer there.
    try:
        A.save(args.cat, entries)
    except Exception:
        if stashed is not None:
            shutil.move(stashed, cover)
        raise
    finally:
        if stashed is not None:
            shutil.rmtree(stashed.parent, ignore_errors=True)

    deleted = f", deleted {entry['cover_url']}" if stashed is not None else ""
    fresh = A.load(args.cat)
    print("removed:")
    print(A.listing([entry]))
    print(f"  {args.cat} now has {len(fresh)} entries{deleted}")
    return 0


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
