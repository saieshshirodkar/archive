#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

import archive as A
import cover

AUTHORED = ("books", "animanga")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Add an entry.")
    p.add_argument("--cat", required=True, choices=A.category_ids())
    p.add_argument("--title", required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--rating", required=True, help='like "8" or "8.5"')
    p.add_argument("--author", default=None, help="books and animanga only")
    p.add_argument(
        "--date", default=None, help="movies only, DD-MM-YYYY; defaults to today IST"
    )
    p.add_argument("--slug", default=None)
    p.add_argument(
        "--cover", default=None, help="existing filename in the cover folder"
    )
    p.add_argument("--cover-url", default=None, help="download cover if no file yet")
    return p


def build_entry(args: argparse.Namespace, rating: str, cover_url: str) -> dict:
    entry = {"title": args.title, "rating_text": rating, "cover_url": cover_url}
    if args.cat in AUTHORED:
        if not args.author:
            raise ValueError(f"{args.cat} entries require --author.")
        entry["author"] = args.author
    elif args.cat == "movies":
        if args.date:
            A.parse_watched(args.date)
        entry["date_watched"] = A.format_watched(args.date or A.today())
    elif args.author:
        A.notice("shows take no --author, ignoring.")
    entry["year"] = args.year
    return entry


def ensure_cover(args: argparse.Namespace, filename: str) -> bool:
    path = A.cover_path(args.cat, filename)
    if path.exists():
        if args.cover_url:
            A.notice(f"cover already exists, not downloading: {path}")
        return True
    if not args.cover_url:
        A.fail(f"cover not found: {path}; pass --cover-url or --cover")
        return False
    try:
        cover.install(args.cat, path.stem, url=args.cover_url)
    except cover.CoverError as exc:
        A.fail(str(exc))
        return False
    return True


def insert(category: str, entries: list[dict], entry: dict) -> None:
    if category == "movies":
        entries.append(entry)
        entries.sort(key=lambda e: A.parse_watched(e["date_watched"]))
    else:
        entries.append(entry)


def run(args: argparse.Namespace) -> int:
    try:
        rating = A.normalise_rating(args.rating)
    except ValueError as exc:
        return A.fail(str(exc))
    stem = args.slug or A.slugify(args.title)
    filename = args.cover or f"{stem}.webp"
    cover_url = f"assets/covers/{A.CATEGORIES[args.cat]['folder']}/{filename}"
    entries = A.load(args.cat)
    if A.exact(entries, args.title) is not None:
        return A.fail(f"{args.title!r} already exists in {args.cat}.")
    owner = next((e["id"] for e in entries if e["cover_url"] == cover_url), None)
    if owner is not None:
        return A.fail(f"{filename} is already the cover for id {owner} in {args.cat}.")
    try:
        entry = build_entry(args, rating, cover_url)
    except ValueError as exc:
        return A.fail(str(exc))
    path = A.cover_path(args.cat, filename)
    pre_existing = path.exists()
    if not ensure_cover(args, filename):
        return 1
    w, h = cover.dimension(path)
    entry["width"], entry["height"] = w, h
    insert(args.cat, entries, entry)
    try:
        A.save(args.cat, entries)
    except Exception:
        if not pre_existing:
            path.unlink(missing_ok=True)
        raise
    fresh = A.load(args.cat)
    print("added:")
    print(A.listing([fresh[A.index_of(fresh, args.title)]]))
    print(f"  {args.cat} now has {len(fresh)} entries")
    return 0


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
