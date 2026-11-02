#!/usr/bin/env python3
"""Add an entry to any archive category.

Every add takes the same path: load, check the title is not already present,
build the entry, make sure its cover exists, insert at the position the
category's ordering rule demands, renumber, validate.

Position rules:

* movies  sort by date_watched, oldest first, so append then re-sort. A
          missing --date means today in IST.
* others  rated entries first in insertion order, then the TBR block. A new
          rated entry lands after the last rated one; a new unrated entry goes
          at the very end.

Examples
--------
    python3 scripts/add.py --cat books --title "Dune" --author "Frank Herbert" \\
        --year 1965 --rating 9.5

    python3 scripts/add.py --cat shows --title "Severance" --year 2022

    python3 scripts/add.py --cat movies --title "Dune" --year 2021 --rating 8 \\
        --cover-url "https://m.media-amazon.com/images/M/....jpg"
"""

from __future__ import annotations

import argparse
import sys

import archive as A
import cover

AUTHORED = ("books", "animanga")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add an entry to the archive.")
    parser.add_argument(
        "--cat", required=True, choices=A.category_ids(), help="category"
    )
    parser.add_argument(
        "--title", required=True, help="exact title as it should appear"
    )
    parser.add_argument(
        "--year", type=int, required=True, help="release/publication year"
    )
    parser.add_argument(
        "--rating",
        default=None,
        help='rating like "8" or "8.5"; omit for TBR. Stored as X/10.',
    )
    parser.add_argument("--author", default=None, help="books and animanga only")
    parser.add_argument(
        "--date",
        default=None,
        help="movies only, DD-MM-YYYY. Defaults to today in IST.",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="cover filename stem. Defaults to a kebab-cased title.",
    )
    parser.add_argument(
        "--cover",
        default=None,
        help="existing cover filename inside the category's cover folder. "
        "Omit to derive it from the slug.",
    )
    parser.add_argument(
        "--cover-url",
        default=None,
        help="download and resize a cover from this URL when the slug has no "
        "cover on disk yet. Existing covers are left alone; use cover.py "
        "--force to replace one.",
    )
    return parser


def build_entry(args: argparse.Namespace, rating: str, cover_url: str) -> dict:
    """Assemble the entry dict, or raise ValueError on a broken category rule.

    Building happens before any cover is fetched, so a rejected flag cannot
    leave a freshly downloaded image behind as an orphan file.
    """
    entry: dict = {
        "title": args.title,
        "rating_text": rating,
        "cover_url": cover_url,
    }

    # author and date_watched are category-specific. Shows deliberately have
    # neither: a show has many creators and no single watch date.
    if args.cat in AUTHORED:
        if not args.author:
            raise ValueError(f"{args.cat} entries require --author.")
        entry["author"] = args.author
    elif args.cat == "movies":
        if args.date:
            A.parse_watched(args.date)
        entry["date_watched"] = args.date or A.today()
    elif args.author:
        A.notice("shows take no --author, ignoring.")

    # normalise() reorders the keys, so assignment order here does not matter
    entry["year"] = args.year
    return entry


def ensure_cover(args: argparse.Namespace, filename: str) -> bool:
    """Make sure the entry's cover is on disk, downloading it if asked to.

    A missing cover renders as a grey box, so it is a hard error rather than a
    warning. With --cover-url the fetch happens in this same command, so a
    half-added entry cannot reference an image that never arrived.
    """
    path = A.cover_path(args.cat, filename)
    if path.exists():
        if args.cover_url:
            A.notice(f"cover already exists, not downloading: {path}")
        return True
    if not args.cover_url:
        A.fail(
            f"cover not found: {path}\n"
            f"       pass --cover-url to fetch it, or download and resize it "
            f"first, or pass --cover with the correct filename."
        )
        return False
    try:
        cover.install(args.cat, path.stem, url=args.cover_url)
    except cover.CoverError as exc:
        A.fail(str(exc))
        return False
    return True


def insert(category: str, entries: list[dict], entry: dict) -> None:
    """Place a new entry according to the category's ordering rule."""
    if category == "movies":
        entries.append(entry)
        entries.sort(key=lambda item: A.parse_watched(item["date_watched"]))
    elif entry["rating_text"]:
        entries.insert(A.last_rated_index(entries) + 1, entry)
    else:
        entries.append(entry)


def duplicate_note(
    category: str, entries: list[dict], args: argparse.Namespace
) -> bool:
    """Reject a title that already exists, or note a near miss.

    A rated entry, and any movie, must not duplicate an exact title. A new TBR
    entry only gets a note: near-misses are normal here (Baki vs Baki Hanma,
    the Verity novel vs the Verity film), and the user may well be adding the
    second work with the same name.
    """
    hits = A.find(entries, args.title)
    if category == "movies" or args.rating is not None:
        if A.exact(entries, args.title) is not None:
            A.fail(f"{args.title!r} already exists in {category}.")
            return True
    elif hits:
        print(f"note: possible existing match for {args.title!r}:", file=sys.stderr)
        print(A.listing(entries[i] for i in hits), file=sys.stderr)
    return False


def run(args: argparse.Namespace) -> int:
    try:
        rating = "" if args.rating is None else A.normalise_rating(args.rating)
    except ValueError as exc:
        return A.fail(str(exc))

    stem = args.slug or A.slugify(args.title)
    filename = args.cover or f"{stem}.webp"
    cover_url = f"assets/covers/{A.CATEGORIES[args.cat]['folder']}/{filename}"
    entries = A.load(args.cat)

    if duplicate_note(args.cat, entries, args):
        return 1

    # One cover per entry. Reusing a filename renders two titles with the same
    # image, and save() only catches it after the write, which would leave a
    # duplicate in the JSON for the next command to trip over.
    owner = next(
        (entry["id"] for entry in entries if entry["cover_url"] == cover_url), None
    )
    if owner is not None:
        return A.fail(
            f"{filename} is already the cover for id {owner} in {args.cat}; "
            f"pass --slug or --cover with a different filename."
        )

    try:
        entry = build_entry(args, rating, cover_url)
    except ValueError as exc:
        return A.fail(str(exc))
    if not ensure_cover(args, filename):
        return 1

    insert(args.cat, entries, entry)
    A.save(args.cat, entries)

    fresh = A.load(args.cat)
    index = A.exact(fresh, args.title)
    print("added:")
    print(A.listing([fresh[index]]))
    print(f"  {args.cat} now has {len(fresh)} entries")
    return 0


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
