#!/usr/bin/env python3
"""Download, resize, and store cover images.

This is the cover pipeline that used to be a ``curl`` + ``magick`` one-liner:
fetch with a browser user agent, auto-orient, resize to 400px wide, encode webp
at quality 80, verify the resulting width, and write the file into the
category's cover folder. ``add.py --cover-url`` calls :func:`install`, so both
entry points produce byte-identical covers.

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
MAX_STORED_BYTES = 200 * 1024
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class CoverError(Exception):
    """A cover could not be produced.

    Raised instead of exiting so the CLI can print the message in the shared
    ``error:`` form and add.py can fail an add without taking the interpreter
    down mid-command.
    """


# --- ImageMagick ------------------------------------------------------------


def image_magick() -> list[str]:
    """Return the ImageMagick command prefix, accepting the IM6 fallback."""
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise CoverError("ImageMagick not found (install magick or convert)")


def identify_tool() -> list[str]:
    """Return the identify command prefix, accepting the IM6 fallback."""
    if shutil.which("magick"):
        return ["magick", "identify"]
    if shutil.which("identify"):
        return ["identify"]
    raise CoverError("ImageMagick identify not found")


def dimension(path: Path) -> tuple[int, int]:
    """Width and height of an image, via identify."""
    result = subprocess.run(
        identify_tool() + ["-format", "%w %h", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CoverError(f"cannot read {path}: {result.stderr.strip()}")
    fields = result.stdout.split()
    if len(fields) != 2:
        raise CoverError(f"cannot parse size of {path}: {result.stdout.strip()!r}")
    return int(fields[0]), int(fields[1])


# --- Fetch and encode -------------------------------------------------------


def download(url: str, dest: Path) -> Path:
    """Fetch a URL into ``dest`` with the user agent the CDNs expect."""
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
    except Exception as exc:
        raise CoverError(f"download failed: {exc}") from exc
    if not data:
        raise CoverError(f"empty response from {url}")
    if len(data) > MAX_BYTES:
        raise CoverError(f"image larger than {MAX_BYTES // 1024 // 1024} MB: {url}")
    dest.write_bytes(data)
    return dest


def resize(source: Path, target: Path) -> Path:
    """Resize to 400px wide, encode webp q80, and verify the width.

    The width check is the part that matters: ImageMagick exits 0 even when it
    wrote something unexpected, and a wrong-width cover is invisible until it
    renders blurry. A failed check deletes the file rather than leaving it.
    """
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
        check=False,
    )
    if result.returncode != 0:
        target.unlink(missing_ok=True)
        raise CoverError(f"conversion failed: {result.stderr.strip()}")
    width, _ = dimension(target)
    if width != WIDTH:
        target.unlink(missing_ok=True)
        raise CoverError(f"expected width {WIDTH}, got {width}")
    return target


def resolve_source(url: str | None, source: str | None, workdir: Path) -> Path:
    """Return the local image to convert, downloading it when given a URL."""
    if bool(url) == bool(source):
        raise CoverError("pass exactly one of --url or --file")
    if url:
        return download(url, workdir / "source")
    origin = Path(source).expanduser()
    if not origin.is_file():
        raise CoverError(f"source image not found: {origin}")
    return origin


def install(
    category: str,
    stem: str,
    url: str | None = None,
    source: str | None = None,
    force: bool = False,
) -> Path:
    """Produce ``covers/<folder>/<stem>.webp`` and return its path.

    Existing covers are never overwritten without ``force``: re-encoding from
    an already-downscaled copy is lossy, so the repo does not regenerate covers
    by accident.
    """
    target = A.cover_path(category, f"{stem}.webp")
    if target.exists() and not force:
        raise CoverError(f"{target} already exists; pass --force to replace it")

    with tempfile.TemporaryDirectory() as tmp:
        origin = resolve_source(url, source, Path(tmp))
        resize(origin, target)
    return target


# --- Audit ------------------------------------------------------------------


def audit(category: str | None = None) -> int:
    """Report covers that are the wrong width, format, or unexpectedly large."""
    problems = 0
    for cat in [category] if category else A.category_ids():
        folder = A.covers_dir(cat)
        files = sorted(path for path in folder.iterdir() if path.is_file())
        total = sum(path.stat().st_size for path in files)
        print(f"{cat}: {len(files)} covers, {total / 1024 / 1024:.1f} MB")
        for path in files:
            width, height = dimension(path)
            size = path.stat().st_size
            if path.suffix != ".webp" or width != WIDTH:
                problems += 1
                print(
                    f"  wrong size/format: {path.name}  "
                    f"{width}x{height}  {size // 1024} KB"
                )
            elif size > MAX_STORED_BYTES:
                problems += 1
                print(
                    f"  over 200 KB: {path.name}  {width}x{height}  {size // 1024} KB"
                )
    return 1 if problems else 0


# --- CLI --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
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
    return parser


def run(args: argparse.Namespace) -> int:
    try:
        if args.audit:
            return audit(args.cat)
        if not args.cat:
            return A.fail("pass --cat, or --audit.")
        stem = args.slug or (A.slugify(args.title) if args.title else "")
        if not stem:
            return A.fail("pass --title or --slug.")

        target = install(
            args.cat, stem, url=args.url, source=args.file, force=args.force
        )
        width, height = dimension(target)
        size = target.stat().st_size
        print(
            f"cover: {target.relative_to(A.ROOT)}  {width}x{height}  {size // 1024} KB"
        )
        return 0
    except CoverError as exc:
        return A.fail(str(exc))


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
