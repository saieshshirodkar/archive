#!/usr/bin/env python3
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
MAX_STORED = 200 * 1024
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class CoverError(Exception):
    pass


def magick() -> list[str]:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    raise CoverError("ImageMagick not found")


def identify() -> list[str]:
    if shutil.which("magick"):
        return ["magick", "identify"]
    if shutil.which("identify"):
        return ["identify"]
    raise CoverError("ImageMagick identify not found")


def dimension(path: Path) -> tuple[int, int]:
    r = subprocess.run(
        identify() + ["-format", "%w %h", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise CoverError(f"cannot read {path}: {r.stderr.strip()}")
    w, h = r.stdout.split()
    return int(w), int(h)


def download(url: str, dest: Path) -> Path:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "image/*,*/*"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(MAX_BYTES + 1)
    except Exception as exc:
        raise CoverError(f"download failed: {exc}") from exc
    if not data:
        raise CoverError(f"empty response from {url}")
    if len(data) > MAX_BYTES:
        raise CoverError(f"image larger than {MAX_BYTES // 1024 // 1024} MB: {url}")
    dest.write_bytes(data)
    return dest


def resize(src: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        magick()
        + [
            str(src),
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
    if r.returncode != 0:
        target.unlink(missing_ok=True)
        raise CoverError(f"conversion failed: {r.stderr.strip()}")
    w, _ = dimension(target)
    if w != WIDTH:
        target.unlink(missing_ok=True)
        raise CoverError(f"expected width {WIDTH}, got {w}")
    return target


def source(url: str | None, local: str | None, tmp: Path) -> Path:
    if bool(url) == bool(local):
        raise CoverError("pass exactly one of --url or --file")
    if url:
        return download(url, tmp / "source")
    origin = Path(local).expanduser()
    if not origin.is_file():
        raise CoverError(f"source image not found: {origin}")
    return origin


def install(
    cat: str,
    stem: str,
    url: str | None = None,
    local: str | None = None,
    force: bool = False,
) -> Path:
    target = A.cover_path(cat, f"{stem}.webp")
    if target.exists() and not force:
        raise CoverError(f"{target} already exists; pass --force to replace it")
    with tempfile.TemporaryDirectory() as td:
        resize(source(url, local, Path(td)), target)
    return target


def audit(cat: str | None = None) -> int:
    bad = 0
    for c in [cat] if cat else A.category_ids():
        files = sorted(p for p in A.covers_dir(c).iterdir() if p.is_file())
        total = sum(p.stat().st_size for p in files)
        print(f"{c}: {len(files)} covers, {total / 1024 / 1024:.1f} MB")
        for p in files:
            w, h = dimension(p)
            size = p.stat().st_size
            if p.suffix != ".webp" or w != WIDTH:
                bad += 1
                print(f"  wrong size/format: {p.name}  {w}x{h}  {size // 1024} KB")
            elif size > MAX_STORED:
                bad += 1
                print(f"  over 200 KB: {p.name}  {w}x{h}  {size // 1024} KB")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch and resize covers.")
    p.add_argument("--cat", choices=A.category_ids())
    p.add_argument("--title")
    p.add_argument("--slug")
    p.add_argument("--url")
    p.add_argument("--file")
    p.add_argument("--force", action="store_true")
    p.add_argument("--audit", action="store_true")
    return p


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
            args.cat, stem, url=args.url, local=args.file, force=args.force
        )
        w, h = dimension(target)
        print(
            f"cover: {target.relative_to(A.ROOT)}  {w}x{h}  {target.stat().st_size // 1024} KB"
        )
        return 0
    except CoverError as exc:
        return A.fail(str(exc))


def main(argv: list[str]) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
