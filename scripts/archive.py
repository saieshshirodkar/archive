"""Shared helpers for the archive CLI tools.

Every tool in scripts/ imports from here so that the rules about key order,
cover paths and validation live in exactly one place instead of being
copy-pasted into each script.

The canonical rules this module enforces:

* ``id`` is always the 1-indexed array position, renumbered after every write.
* The key order of each category is fixed; every write re-projects entries
  through :func:`normalise` so a stray field cannot creep in.
* ``assets/covers/anime/`` holds animanga covers (not ``animanga/``).
* Covers are 400px-wide webp; the cover folder must match the category.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Paths ------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COVERS_DIR = ROOT / "assets" / "covers"

# Every date in the archive is IST. The system clock is frequently UTC, and a
# silent UTC-vs-IST mix-up has produced wrong entries before, so nothing in
# this repo is allowed to call datetime.now() without an explicit zone.
TZ = ZoneInfo("Asia/Kolkata")

# --- Category definitions ---------------------------------------------------

# folder: the directory under assets/covers that holds this category's covers.
# It matches the id for every category except animanga, which predates the
# rename from "animanga" to "anime" on disk. This mapping is the single most
# common source of broken cover paths, so it is never hardcoded at a call site.
CATEGORIES: dict[str, dict] = {
    "books": {
        "folder": "books",
        "keys": ["id", "title", "author", "rating_text", "cover_url", "year"],
    },
    "animanga": {
        "folder": "anime",
        "keys": ["id", "title", "author", "rating_text", "cover_url", "year"],
    },
    "movies": {
        "folder": "movies",
        # key order differs: movies carry date_watched and have no author
        "keys": ["id", "title", "year", "date_watched", "rating_text", "cover_url"],
    },
    "shows": {
        "folder": "shows",
        # shows have neither author nor date_watched (multiple creators, and
        # there is no per-episode watch date to record)
        "keys": ["id", "title", "rating_text", "cover_url", "year"],
    },
}


def category_ids() -> list[str]:
    """Category ids in tab order, matching js/config.js CATEGORIES."""
    return ["books", "animanga", "movies", "shows"]


def covers_dir(category: str) -> Path:
    """Return the covers directory for a category id."""
    return COVERS_DIR / CATEGORIES[category]["folder"]


# --- Date handling ----------------------------------------------------------


def today() -> str:
    """Today's date in IST as ``DD-MM-YYYY``.

    This is the format ``date_watched`` uses in movies.json.
    """
    return datetime.now(TZ).strftime("%d-%m-%Y")


def normalise_rating(value: str) -> str:
    """Turn user input like ``8`` or ``8.5`` into the stored ``"8/10"`` form.

    Accepts an already-suffixed value ("8.5/10") and normalises it back, so
    this is safe to run on anything the user types. The user writes "7/5"
    meaning 7.5 out of 10, which is a different habit from ours, so a value
    like "7/5" is rejected rather than silently misread.
    """
    text = str(value).strip()
    if "/" in text:
        left, _, right = text.partition("/")
        if right != "10":
            raise ValueError(f"ratings are out of 10, got {value!r}")
        text = left
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"bad rating {value!r}")
    if not 0 <= number <= 10:
        raise ValueError(f"rating out of range: {value!r}")
    # keep one decimal only when the user typed one
    rendered = text if "." in text else str(int(number))
    return f"{rendered}/10"


def parse_watched(value: str) -> list[int]:
    """Convert ``DD-MM-YYYY`` into a sortable ``[Y, M, D]`` list.

    movies.json is sorted by watch date with these keys. Reversing the split
    components and mapping to int is what turns "03-08-2026" into
    ``[2026, 8, 3]``, which sorts correctly as a list.
    """
    parts = value.split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"bad date {value!r}, expected DD-MM-YYYY")
    return [int(x) for x in reversed(parts)]


# --- Load / save ------------------------------------------------------------


def data_path(category: str) -> Path:
    return DATA_DIR / f"{category}.json"


def load(category: str) -> list[dict]:
    """Load a category's entries from disk."""
    with open(data_path(category), encoding="utf-8") as fh:
        return json.load(fh)


def normalise(category: str, entries: list[dict]) -> list[dict]:
    """Renumber ids from 1 and force the category's key order.

    Call this after every mutation. It is the reason ids can never drift: the
    id is recomputed from the list position rather than trusted from the
    previous state.
    """
    keys = CATEGORIES[category]["keys"]
    out = []
    for index, entry in enumerate(entries, start=1):
        missing = [k for k in keys if k != "id" and k not in entry]
        if missing:
            raise KeyError(f"{category} entry missing {missing}: {entry}")
        ordered = {"id": index}
        for key in keys:
            if key != "id":
                ordered[key] = entry[key]
        out.append(ordered)
    return out


def save(category: str, entries: list[dict]) -> None:
    """Normalise, write with the repo's exact JSON formatting, and validate.

    Writing happens *before* validation on purpose: a half-applied insert is
    worse than a failed assert, so the data is persisted and any problem is
    reported loudly rather than silently rolled back. Validation always runs
    immediately after so the failure surfaces in the same command.
    """
    entries = normalise(category, entries)
    with open(data_path(category), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    problems = validate(category)
    if problems:
        raise AssertionError(
            f"{category}.json written but validation failed:\n  "
            + "\n  ".join(problems)
        )


# --- Lookups and movement ---------------------------------------------------


def find(entries: list[dict], needle: str) -> list[int]:
    """Indices of entries whose title contains ``needle`` (case-insensitive).

    Substring matching is deliberate: the user types "housemaid is watching"
    or "djba" and we should find something, then confirm the match rather than
    demand an exact title.
    """
    lowered = needle.lower()
    return [i for i, e in enumerate(entries) if lowered in e["title"].lower()]


def exact(entries: list[dict], title: str) -> int | None:
    """Index of an entry with an exactly matching title, else None."""
    for i, e in enumerate(entries):
        if e["title"].lower() == title.lower():
            return i
    return None


def rated_indices(entries: list[dict]) -> list[int]:
    """Indices of entries with a non-empty rating_text."""
    return [i for i, e in enumerate(entries) if e["rating_text"]]


def last_rated_index(entries: list[dict]) -> int:
    """Index of the final rated entry, or -1 when nothing is rated yet."""
    rated = rated_indices(entries)
    return rated[-1] if rated else -1


def move(entries: list[dict], index: int, to: int) -> list[dict]:
    """Move the entry at ``index`` so it ends up at final position ``to``.

    ``to`` is the destination in the *resulting* list, not the index to insert
    at. Popping the entry first shifts everything below it down by one, so an
    entry moving upward needs its target incremented or it lands one slot too
    high. Getting this wrong makes ``--before X`` a silent no-op when the entry
    being moved already sits above X.

    Does not mutate the input. Clamped into range so an out-of-range index
    from a caller cannot raise IndexError.
    """
    if not 0 <= index < len(entries):
        raise IndexError(f"index {index} out of range for {len(entries)} entries")
    to = max(0, min(to, len(entries) - 1))
    if to == index:
        return list(entries)
    # Adjust for the shift caused by removing the entry.
    if index < to:
        to -= 1
    entry = entries.pop(index)
    entries.insert(to, entry)
    return entries


# --- Validation -------------------------------------------------------------


def validate(category: str) -> list[str]:
    """Check one category. Returns a list of human-readable problems.

    Empty list means valid. Every check here corresponds to a bug that has
    actually happened in this archive:

    * ids must be 1..N with no gaps (a split insert leaves them inconsistent)
    * key set and key order must match the schema (shows must never grow an
      author or date_watched field)
    * the set of referenced cover filenames must equal the files on disk,
      which catches both a wrong reference and an orphaned file
    * two entries must never share a cover_url (this caught Fearless pointing
      at fearful.webp, which rendered two different books as one image)
    * movies must stay sorted by date_watched oldest-first
    * books/animanga/shows must keep the TBR block contiguous at the end
    """
    problems: list[str] = []
    keys = CATEGORIES[category]["keys"]
    entries = load(category)

    # ids sequential from 1
    ids = [e["id"] for e in entries]
    if ids != list(range(1, len(entries) + 1)):
        problems.append(f"ids not sequential: {ids}")

    # schema: key set AND key order
    for e in entries:
        if list(e) != keys:
            problems.append(f"id {e.get('id')}: schema drift, got {list(e)}")

    # covers referenced vs covers on disk
    folder = covers_dir(category)
    if not folder.is_dir():
        problems.append(f"cover folder missing: {folder}")
    else:
        on_disk = {p.name for p in folder.iterdir() if p.is_file()}
        referenced = {e["cover_url"].rsplit("/", 1)[-1] for e in entries}
        for orphan in sorted(referenced - on_disk):
            problems.append(f"referenced cover not on disk: {orphan}")
        for unused in sorted(on_disk - referenced):
            problems.append(f"cover on disk but unused: {unused}")
        for e in entries:
            if not os.path.exists(ROOT / e["cover_url"]):
                problems.append(f"id {e['id']}: missing file {e['cover_url']}")

    # duplicate cover references
    seen: dict[str, list[int]] = {}
    for e in entries:
        seen.setdefault(e["cover_url"], []).append(e["id"])
    for url, owners in seen.items():
        if len(owners) > 1:
            problems.append(f"duplicate cover_url {url} used by ids {owners}")

    # rating format
    for e in entries:
        rating = e["rating_text"]
        if not rating:
            continue
        body = rating.rsplit("/", 1)
        if len(body) != 2 or body[1] != "10":
            problems.append(f"id {e['id']}: bad rating {rating!r}")
        else:
            try:
                value = float(body[0])
            except ValueError:
                problems.append(f"id {e['id']}: bad rating {rating!r}")
                continue
            if not 0 <= value <= 10:
                problems.append(f"id {e['id']}: rating out of range {rating!r}")

    # per-category ordering
    if category == "movies":
        keys_ = [parse_watched(e["date_watched"]) for e in entries]
        if keys_ != sorted(keys_):
            problems.append("movies not sorted by date_watched oldest-first")
    else:
        flags = [bool(e["rating_text"]) for e in entries]
        # The `False in flags` guard matters: list.index raises ValueError when
        # every entry is rated, which reads like data corruption but is not.
        if False in flags and any(flags[flags.index(False):]):
            problems.append("TBR block is not contiguous at the end")

    return problems


def validate_all() -> dict[str, list[str]]:
    """Validate every category. Returns {category: [problems]}."""
    return {c: validate(c) for c in category_ids()}


# --- Terminal formatting ----------------------------------------------------

RATING_WIDTH = 8


def describe(entry: dict) -> str:
    """One-line human summary used by find/top/reorder output."""
    rating = entry["rating_text"] or "TBR"
    bits = [f"{entry['id']:>4}", f"{rating:<{RATING_WIDTH}}", entry["title"]]
    # author is absent for movies and shows by design
    author = entry.get("author")
    if author:
        bits.append(f"by {author}")
    bits.append(f"({entry.get('year')})" if entry.get("year") is not None else "")
    # shows and books/animanga have no watch date; movies always do
    if entry.get("date_watched"):
        bits.append(entry["date_watched"])
    return "  ".join(b for b in bits if b)