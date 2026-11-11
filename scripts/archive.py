from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COVERS_DIR = ROOT / "assets" / "covers"
TZ = ZoneInfo("Asia/Kolkata")

CATEGORIES: dict[str, dict] = {
    "books": {
        "folder": "books",
        "keys": [
            "id",
            "title",
            "author",
            "rating_text",
            "cover_url",
            "year",
            "width",
            "height",
        ],
    },
    "animanga": {
        "folder": "anime",
        "keys": [
            "id",
            "title",
            "author",
            "rating_text",
            "cover_url",
            "year",
            "width",
            "height",
        ],
    },
    "movies": {
        "folder": "movies",
        "keys": [
            "id",
            "title",
            "year",
            "date_watched",
            "rating_text",
            "cover_url",
            "width",
            "height",
        ],
    },
    "shows": {
        "folder": "shows",
        "keys": ["id", "title", "rating_text", "cover_url", "year", "width", "height"],
    },
}
CATEGORY_IDS = tuple(CATEGORIES)


def category_ids() -> list[str]:
    return list(CATEGORY_IDS)


def data_path(category: str) -> Path:
    return DATA_DIR / f"{category}.json"


def covers_dir(category: str) -> Path:
    return COVERS_DIR / CATEGORIES[category]["folder"]


def cover_path(category: str, filename: str) -> Path:
    return covers_dir(category) / filename


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def notice(message: str) -> None:
    print(f"note: {message}", file=sys.stderr)


def describe(entry: dict) -> str:
    bits = [f"{entry['id']:>4}", f"{entry['rating_text']:<8}", entry["title"]]
    if entry.get("author"):
        bits.append(f"by {entry['author']}")
    if entry.get("year") is not None:
        bits.append(f"({entry['year']})")
    if entry.get("date_watched"):
        bits.append(entry["date_watched"])
    return "  ".join(bits)


def listing(entries: Iterable[dict]) -> str:
    return "\n".join("  " + describe(e) for e in entries)


def today() -> str:
    return datetime.now(TZ).strftime("%d-%m-%Y")


def parse_watched(value: str) -> list[int]:
    try:
        d = datetime.strptime(str(value), "%d-%m-%Y")
    except (TypeError, ValueError):
        raise ValueError(f"bad date {value!r}, expected DD-MM-YYYY") from None
    return [d.year, d.month, d.day]


def format_watched(value: str) -> str:
    y, m, d = parse_watched(value)
    return f"{d:02d}-{m:02d}-{y:04d}"


def normalise_rating(value: str) -> str:
    text = str(value).strip()
    if "/" in text:
        num, _, den = text.partition("/")
        if den != "10":
            raise ValueError(f"ratings are out of 10, got {value!r}")
        text = num
    try:
        n = float(text)
    except ValueError:
        raise ValueError(f"bad rating {value!r}") from None
    if not 0 <= n <= 10:
        raise ValueError(f"rating out of range: {value!r}")
    return f"{int(n) if n.is_integer() else f'{n:g}'}/10"


def slugify(title: str) -> str:
    spaced = "".join(
        c if c.isalnum() else "-" if c in " -_" else "" for c in title.lower()
    )
    return re.sub(r"-{2,}", "-", spaced).strip("-")


def load(category: str) -> list[dict]:
    with open(data_path(category), encoding="utf-8") as fh:
        return json.load(fh)


def normalise(category: str, entries: list[dict]) -> list[dict]:
    keys = CATEGORIES[category]["keys"]
    payload = [k for k in keys if k != "id"]
    out = []
    for i, entry in enumerate(entries, 1):
        missing = [k for k in payload if k not in entry]
        if missing:
            raise KeyError(f"{category} entry missing {missing}: {entry}")
        out.append({"id": i, **{k: entry[k] for k in payload}})
    return out


def save(category: str, entries: list[dict]) -> None:
    entries = normalise(category, entries)
    problems = validate_entries(category, entries) + validate_covers(category, entries)
    if problems:
        raise AssertionError(
            f"{category}.json not written, validation failed:\n  "
            + "\n  ".join(problems)
        )
    path = data_path(category)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def find(entries: list[dict], needle: str) -> list[int]:
    n = needle.lower()
    return [i for i, e in enumerate(entries) if n in e["title"].lower()]


def exact(entries: list[dict], title: str) -> int | None:
    t = title.lower()
    for i, e in enumerate(entries):
        if e["title"].lower() == t:
            return i
    return None


def index_of(entries: list[dict], title: str) -> int:
    hits = [i for i, e in enumerate(entries) if e["title"].lower() == title.lower()]
    if len(hits) != 1:
        raise LookupError(f"expected one entry titled {title!r}, found {len(hits)}")
    return hits[0]


def resolve_index(entries: list[dict], needle: str, strict: bool = False) -> int | None:
    if strict:
        return exact(entries, needle)
    hits = find(entries, needle)
    return hits[0] if len(hits) == 1 else None


def report_no_match(
    entries: list[dict], needle: str, category: str, label: str, strict: bool
) -> None:
    hits = find(entries, needle)
    if strict:
        if not hits:
            print(
                f"error: nothing in {category} is titled exactly {needle!r}.",
                file=sys.stderr,
            )
            return
        print(
            f"error: no entry titled exactly {needle!r}; did you mean:", file=sys.stderr
        )
    elif not hits:
        print(f"error: nothing in {category} matches {needle!r}.", file=sys.stderr)
        return
    else:
        print(
            f"error: {len(hits)} matches for {label} {needle!r}, be more specific or use --exact:",
            file=sys.stderr,
        )
    for i in hits:
        print("  " + describe(entries[i]), file=sys.stderr)


def move(entries: list[dict], index: int, to: int) -> list[dict]:
    """Move the entry at `index` so that it ends up at final 0-based index `to`."""
    if not 0 <= index < len(entries):
        raise IndexError(f"index {index} out of range for {len(entries)} entries")
    to = max(0, min(to, len(entries) - 1))
    if to == index:
        return entries
    entry = entries.pop(index)
    entries.insert(to, entry)
    return entries


def validate_entries(category: str, entries: list[dict]) -> list[str]:
    problems: list[str] = []
    keys = CATEGORIES[category]["keys"]
    ids = [e["id"] for e in entries]
    if ids != list(range(1, len(entries) + 1)):
        problems.append(f"ids not sequential: {ids}")
    for e in entries:
        if list(e) != keys:
            problems.append(f"id {e.get('id')}: schema drift, got {list(e)}")
    owners: dict[str, list[int]] = {}
    for e in entries:
        owners.setdefault(e["cover_url"], []).append(e["id"])
    for url, ids_using in owners.items():
        if len(ids_using) > 1:
            problems.append(f"duplicate cover_url {url} used by ids {ids_using}")
    for e in entries:
        if e.get("width") is not None and e["width"] != 400:
            problems.append(f"id {e['id']}: cover width {e['width']}, expected 400")
        num, _, den = e["rating_text"].rpartition("/")
        if den != "10":
            problems.append(f"id {e['id']}: bad rating {e['rating_text']!r}")
            continue
        try:
            v = float(num)
        except ValueError:
            problems.append(f"id {e['id']}: bad rating {e['rating_text']!r}")
            continue
        if not 0 <= v <= 10:
            problems.append(f"id {e['id']}: rating out of range {e['rating_text']!r}")
    if category == "movies":
        dates = [parse_watched(e["date_watched"]) for e in entries]
        if dates != sorted(dates):
            problems.append("movies not sorted by date_watched oldest-first")
    return problems


def validate_covers(category: str, entries: list[dict]) -> list[str]:
    problems: list[str] = []
    folder = covers_dir(category)
    if not folder.is_dir():
        return [f"cover folder missing: {folder}"]
    on_disk = {p.name for p in folder.iterdir() if p.is_file()}
    referenced = {e["cover_url"].rsplit("/", 1)[-1] for e in entries}
    for o in sorted(referenced - on_disk):
        problems.append(f"referenced cover not on disk: {o}")
    for u in sorted(on_disk - referenced):
        problems.append(f"cover on disk but unused: {u}")
    for e in entries:
        if not (ROOT / e["cover_url"]).exists():
            problems.append(f"id {e['id']}: missing file {e['cover_url']}")
    return problems


def validate(category: str) -> list[str]:
    entries = load(category)
    return validate_entries(category, entries) + validate_covers(category, entries)


def validate_all() -> dict[str, list[str]]:
    return {c: validate(c) for c in CATEGORY_IDS}
