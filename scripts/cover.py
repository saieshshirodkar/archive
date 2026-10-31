#!/usr/bin/env python3
"""Download, resize, and store cover images.

This is the whole cover pipeline that used to be a ``curl`` + ``magick``
one-liner: fetch with a browser user agent, auto-orient, resize to 400px wide,
encode webp at quality 80, verify the result, and write it into the category's
cover folder. ``add.py --cover-url`` calls into this module, so both entry
points produce byte-identical covers.

Examples
--------
    python3 scripts/cover.py --cat movies --title "The Birthday Gift" \\
        --url "https://m.media-amazon.com/images/M/....jpg"

    python3 scripts/cover.py --cat books --title "Dune" --file /tmp/dune.jpg

    python3 scripts/cover.py --cat shows --title "Carrie" --url "..." --force

    python3 scripts/cover.py --audit
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import archive as A

WIDTH = 400
QUALITY = 80
MAX_BYTES = 30 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def image_magick() -> list[str]:
    """Return the ImageMagick command prefix, accepting the IM6 fallback."""
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise SystemExit("error: ImageMagick not found (install magick or convert)")


def identify() -> list[str]:
    """Return the identify command prefix, accepting the IM6 fallback."""
    if shutil.which("magick"):
        return ["magick", "identify"]
    if shutil.which("identify"):
        return ["identify"]
    raise SystemExit("error: ImageMagick identify not found")


def dimension(path: Path) -> tuple[int, int]:
    """Width and height of an image, via identify."""
    result = subprocess.run(
        identify() + ["-format", "%w %h", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"error: cannot read {path}: {result.stderr.strip()}")
    width, height = result.stdout.split()
    return int(width), int(height)


def download(url: str, dest: Path) -> None:
    """Fetch a URL to dest with the user agent the CDNs expect."""
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
    except Exception as exc:
        raise SystemExit(f"error: download failed: {exc}")
    if not data:
        raise SystemExit(f"error: empty response from {url}")
    if len(data) > MAX_BYTES:
        raise SystemExit(f"error: image larger than {MAX_BYTES // 1024 // 1024} MB: {url}")
    dest.write_bytes(data)


def convert(source: Path, target: Path) -> None:
    """Resize to 400px wide and encode webp at quality 80."""
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        image_magick()
        + [
            str(source),
            "-auto-orient",
            "-resize",
            f"{WIDTH}x",
            "-quality",
            str(QUALITY),
            str(target),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        target.unlink(missing_ok=True)
        raise SystemExit(f"error: conversion failed: {result.stderr.strip()}")


def install(
    category: str,
    stem: str,
    url: str | None = None,
    source: str | None = None,
    force: bool = False,
) -> Path:
    """Produce ``covers/<folder>/<stem>.webp`` and return its path.

    Exactly one of url or source must be given. Existing covers are never
    overwritten without ``force``: re-encoding a cover from a downscaled copy
    is lossy, and the repo does not regenerate covers by accident.
    """
    target = A.covers_dir(category) / f"{stem}.webp"
    if target.exists() and not force:
        raise SystemExit(
            f"error: {target} already exists; pass --force to replace it"
        )
    if bool(url) == bool(source):
        raise SystemExit("error: pass exactly one of --url or --file")

    with tempfile.TemporaryDirectory() as tmp:
        if url:
            downloaded = Path(tmp) / "source"
            download(url, downloaded)
            origin = downloaded
        else:
            origin = Path(source)
            if not origin.is_file():
                raise SystemExit(f"error: source image not found: {origin}")

        convert(origin, target)

    width, height = dimension(target)
    if width != WIDTH:
        target.unlink(missing_ok=True)
        raise SystemExit(f"error: expected width {WIDTH}, got {width}")
    return target


def audit(category: str | None = None) -> int:
    """Report covers that are the wrong width, format, or unexpectedly large."""
    categories = [category] if category else A.category_ids()
    problems = 0
    for cat in categories:
        folder = A.covers_dir(cat)
        files = sorted(p for p in folder.iterdir() if p.is_file())
        total = sum(p.stat().st_size for p in files)
        print(f"{cat}: {len(files)} covers, {total / 1024 / 1024:.1f} MB")
        for path in files:
            width, height = dimension(path)
            size = path.stat().st_size
            odd = path.suffix != ".webp" or width != WIDTH
            big = size > 200 * 1024
            if odd or big:
                problems += 1
                reason = "wrong size/format" if odd else "over 200 KB"
                print(f"  {reason}: {path.name}  {width}x{height}  {size // 1024} KB")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Fetch and resize cover images.")
    parser.add_argument("--cat", choices=A.category_ids(), help="category")
    parser.add_argument("--title", help="entry title, for the default slug")
    parser.add_argument("--slug", help="override the derived filename stem")
    parser.add_argument("--url", help="remote image URL")
    parser.add_argument("--file", help="local image already on disk")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing cover"
    )
    parser.add_argument(
        "--audit", action="store_true", help="check covers without writing"
    )
    args = parser.parse_args(argv)

    if args.audit:
        return audit(args.cat)
    if not args.cat:
        print("error: pass --cat, or --audit.", file=sys.stderr)
        return 1
    stem = args.slug or (A.slugify(args.title) if args.title else None)
    if not stem:
        print("error: pass --title or --slug.", file=sys.stderr)
        return 1

    target = install(
        args.cat, stem, url=args.url, source=args.file, force=args.force
    )
    width, height = dimension(target)
    size = target.stat().st_size
    print(f"cover: {target.relative_to(A.ROOT)}  {width}x{height}  {size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
