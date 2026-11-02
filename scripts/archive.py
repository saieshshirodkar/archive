"""Shared helpers for the archive CLI tools.

Every script in this folder imports from here, so the rules about key order,
cover paths, ordering and validation live in one place instead of being
copy-pasted eight times.

The rules this module enforces:

* ``id`` is always the 1-indexed array position, renumbered after every write.
* Each category has a fixed key order; every write re-projects entries through
  :func:`normalise`, so a stray field cannot creep in.
* ``assets/covers/anime/`` holds animanga covers (not ``animanga/``).
* Covers are 400px-wide webp, and the folder always matches the category.

Nothing here prints to stdout except :func:`describe` and :func:`listing`; the
CLI scripts own their own success output.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Paths ------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COVERS_DIR = ROOT / "assets" / "covers"

# Every date in the archive is IST. The system clock is frequently UTC, and a
# silent UTC-vs-IST mix-up has produced wrong entries before, so nothing here
# is allowed to call datetime.now() without an explicit zone.
TZ = ZoneInfo("Asia/Kolkata")

# --- Categories -------------------------------------------------------------

# ``folder`` is the directory under assets/covers that holds this category's
# covers. It matches the id everywhere except animanga, which predates the
# rename from "animanga" to "anime" on disk. This mapping is the most common
# source of broken cover paths, so it is never hardcoded at a call site.
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
        # shows have neither author nor date_watched: many creators, and no
        # single watch date to record
        "keys": ["id", "title", "rating_text", "cover_url", "year"],
    },
}

# Tab order, matching js/config.js CATEGORIES.
CATEGORY_IDS = tuple(CATEGORIES)


def category_ids() -> list[str]:
    """Category ids in tab order."""
    return list(CATEGORY_IDS)


def data_path(category: str) -> Path:
    """Path to ``data/<category>.json``."""
    return DATA_DIR / f"{category}.json"


def covers_dir(category: str) -> Path:
    """Covers directory for a category, following the animanga mapping."""
    return COVERS_DIR / CATEGORIES[category]["folder"]


def cover_path(category: str, filename: str) -> Path:
    """Path to one cover file inside a category's cover folder."""
    return covers_dir(category) / filename


# --- Terminal output --------------------------------------------------------

RATING_WIDTH = 8


def fail(message: str) -> int:
    """Print ``error: <message>`` to stderr and return an exit code of 1.

    Returning the code lets call sites read as ``return A.fail(...)`` instead
    of a print followed by a bare ``return 1``.
    """
    print(f"error: {message}", file=sys.stderr)
    return 1


def notice(message: str) -> None:
    """Print ``note: <message>`` to stderr. Used for non-fatal caveats."""
    print(f"note: {message}", file=sys.stderr)


def describe(entry: dict) -> str:
    """One-line human summary: id, rating, title, author, year, watch date."""
    rating = entry["rating_text"] or "TBR"
    bits = [f"{entry['id']:>4}", f"{rating:<{RATING_WIDTH}}", entry["title"]]
    # author is absent for movies and shows by design
    if entry.get("author"):
        bits.append(f"by {entry['author']}")
    if entry.get("year") is not None:
        bits.append(f"({entry['year']})")
    # movies are the only category with a watch date
    if entry.get("date_watched"):
        bits.append(entry["date_watched"])
    return "  ".join(bits)


def listing(entries: Iterable[dict]) -> str:
    """Describe entries one per line, indented to match the CLI style."""
    return "\n".join("  " + describe(entry) for entry in entries)


# --- Dates and ratings ------------------------------------------------------


def today() -> str:
    """Today in IST as ``DD-MM-YYYY``, the format ``date_watched`` uses."""
    return datetime.now(TZ).strftime("%d-%m-%Y")


def parse_watched(value: str) -> list[int]:
    """Convert ``DD-MM-YYYY`` into a sortable ``[Y, M, D]`` list.

    ``strptime`` is what rejects impossible dates: a digit-only check accepted
    "99-99-2026", which then sorted as if it were real.
    """
    try:
        parsed = datetime.strptime(str(value), "%d-%m-%Y")
    except (TypeError, ValueError):
        raise ValueError(f"bad date {value!r}, expected DD-MM-YYYY") from None
    return [parsed.year, parsed.month, parsed.day]


def normalise_rating(value: str) -> str:
    """Turn ``8`` or ``8.5`` into the stored ``"8/10"`` form.

    Also accepts an already-suffixed ``"8.5/10"``. The user writes "7/5"
    meaning 7.5 out of 10, which is a different habit, so anything with a
    denominator other than 10 is rejected rather than silently misread.
    """
    text = str(value).strip()
    if "/" in text:
        numerator, _, denominator = text.partition("/")
        if denominator != "10":
            raise ValueError(f"ratings are out of 10, got {value!r}")
        text = numerator
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"bad rating {value!r}") from None
    if not 0 <= number <= 10:
        raise ValueError(f"rating out of range: {value!r}")
    # keep a decimal only when the user typed one
    rendered = str(int(number)) if number.is_integer() else f"{number:g}"
    return f"{rendered}/10"


# --- Slugs ------------------------------------------------------------------


def slugify(title: str) -> str:
    """Kebab-case a title for a cover filename.

    Apostrophes and other punctuation are dropped rather than encoded, because
    that is how the existing filenames were built: ``Takopi's`` -> ``takopis``,
    ``Bastard!!`` -> ``bastard``. Spaces, hyphens and underscores collapse into
    a single kebab separator. Lives here so add.py and cover.py derive the same
    filename from the same title.
    """
    spaced = "".join(
        ch if ch.isalnum() else "-" if ch in " -_" else "" for ch in title.lower()
    )
    return re.sub(r"-{2,}", "-", spaced).strip("-")


# --- Load and save ----------------------------------------------------------


def load(category: str) -> list[dict]:
    """Load a category's entries from disk."""
    with open(data_path(category), encoding="utf-8") as fh:
        return json.load(fh)


def normalise(category: str, entries: list[dict]) -> list[dict]:
    """Renumber ids from 1 and force the category's key order.

    Called after every mutation. This is why ids can never drift: the id is
    recomputed from the list position rather than trusted from the previous
    state.
    """
    keys = CATEGORIES[category]["keys"]
    payload = [key for key in keys if key != "id"]
    normalised = []
    for index, entry in enumerate(entries, start=1):
        missing = [key for key in payload if key not in entry]
        if missing:
            raise KeyError(f"{category} entry missing {missing}: {entry}")
        normalised.append({"id": index, **{key: entry[key] for key in payload}})
    return normalised


def save(category: str, entries: list[dict]) -> None:
    """Normalise, write with the repo's JSON formatting, then validate.

    The write happens *before* validation on purpose: a half-applied edit is
    worse than a failed assert, so the data is persisted and any problem is
    reported loudly in the same command rather than silently rolled back.
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


# --- Lookups ----------------------------------------------------------------


def find(entries: list[dict], needle: str) -> list[int]:
    """Indices of entries whose title contains ``needle``, case-insensitive.

    Substring matching is deliberate: the user types "housemaid is watching"
    or "djba" and something should turn up, then the match gets confirmed.
    """
    lowered = needle.lower()
    return [i for i, entry in enumerate(entries) if lowered in entry["title"].lower()]


def exact(entries: list[dict], title: str) -> int | None:
    """Index of the entry whose title matches exactly, else None."""
    lowered = title.lower()
    for index, entry in enumerate(entries):
        if entry["title"].lower() == lowered:
            return index
    return None


def resolve_index(entries: list[dict], needle: str, strict: bool = False) -> int | None:
    """Resolve a title to exactly one index, else None.

    The single decision every write command makes before touching an entry.
    None means either "nothing matched" or "more than one matched", because a
    caller cannot act on an ambiguous title without being told the candidates;
    :func:`report_no_match` prints those.

    ``strict`` demands a whole-title match. Short titles cannot be separated
    by shrinking the needle: "Baki" is a substring of both "Baki Hanma" and
    "Baki the Grappler", and "Bastard" is one of "Bastard!!".
    """
    if strict:
        return exact(entries, needle)
    hits = find(entries, needle)
    return hits[0] if len(hits) == 1 else None


def report_no_match(
    entries: list[dict], needle: str, category: str, label: str, strict: bool
) -> None:
    """Explain to stderr why :func:`resolve_index` returned None."""
    hits = find(entries, needle)
    if strict:
        if not hits:
            print(
                f"error: nothing in {category} is titled exactly {needle!r}.",
                file=sys.stderr,
            )
            return
        print(
            f"error: no entry in {category} is titled exactly {needle!r}; "
            f"did you mean one of these?",
            file=sys.stderr,
        )
    elif not hits:
        print(f"error: nothing in {category} matches {needle!r}.", file=sys.stderr)
        return
    else:
        print(
            f"error: {len(hits)} matches for {label} {needle!r}, be more "
            f"specific, or pass --exact to match the whole title:",
            file=sys.stderr,
        )
    for index in hits:
        print("  " + describe(entries[index]), file=sys.stderr)


# --- Ordering ---------------------------------------------------------------


def rated_indices(entries: list[dict]) -> list[int]:
    """Indices of entries that carry a rating."""
    return [i for i, entry in enumerate(entries) if entry["rating_text"]]


def last_rated_index(entries: list[dict], exclude: int | None = None) -> int:
    """Index of the final rated entry, or -1 when nothing is rated.

    ``exclude`` drops one index from consideration. rate.py needs it when the
    entry being moved is already rated: without it the entry counts itself as
    the last rated one, the target equals its current index, and the move
    silently does nothing while the entry stays stranded in the TBR block.
    """
    rated = [i for i in rated_indices(entries) if i != exclude]
    return rated[-1] if rated else -1


def move(entries: list[dict], index: int, to: int) -> list[dict]:
    """Move the entry at ``index`` so it ends up at final position ``to``.

    ``to`` is the destination in the *resulting* list, not the index to insert
    at. Removing the entry first shifts everything below it up by one, so an
    entry moving downward needs its target decremented or it lands a slot too
    low; getting this wrong makes ``--before X`` a no-op when the entry being
    moved already sits above X.

    Mutates and returns ``entries``. Clamped into range so a bad index from a
    caller cannot raise IndexError.
    """
    if not 0 <= index < len(entries):
        raise IndexError(f"index {index} out of range for {len(entries)} entries")
    to = max(0, min(to, len(entries) - 1))
    if to == index:
        return entries
    entry = entries.pop(index)
    # Compensate for the pop shifting every later position up by one.
    entries.insert(to - 1 if index < to else to, entry)
    return entries


# --- Validation -------------------------------------------------------------


def validate(category: str) -> list[str]:
    """Check one category, returning human-readable problems (empty is ok).

    Every check here corresponds to a bug that has actually happened:

    * ids must be 1..N with no gaps (a split insert leaves them inconsistent)
    * key set and key order must match the schema (shows must never grow an
      author or date_watched field)
    * referenced cover filenames must equal the files on disk, which catches
      both a wrong reference and an orphaned file
    * two entries must never share a cover_url (Fearless once pointed at
      fearful.webp, rendering two books as one image)
    * movies must stay sorted by date_watched, oldest first
    * books/animanga/shows must keep the TBR block contiguous at the end
    """
    problems: list[str] = []
    keys = CATEGORIES[category]["keys"]
    entries = load(category)

    ids = [entry["id"] for entry in entries]
    if ids != list(range(1, len(entries) + 1)):
        problems.append(f"ids not sequential: {ids}")

    for entry in entries:
        if list(entry) != keys:
            problems.append(f"id {entry.get('id')}: schema drift, got {list(entry)}")

    folder = covers_dir(category)
    if not folder.is_dir():
        problems.append(f"cover folder missing: {folder}")
    else:
        on_disk = {path.name for path in folder.iterdir() if path.is_file()}
        referenced = {entry["cover_url"].rsplit("/", 1)[-1] for entry in entries}
        for orphan in sorted(referenced - on_disk):
            problems.append(f"referenced cover not on disk: {orphan}")
        for unused in sorted(on_disk - referenced):
            problems.append(f"cover on disk but unused: {unused}")
        for entry in entries:
            if not (ROOT / entry["cover_url"]).exists():
                problems.append(f"id {entry['id']}: missing file {entry['cover_url']}")

    owners: dict[str, list[int]] = {}
    for entry in entries:
        owners.setdefault(entry["cover_url"], []).append(entry["id"])
    for url, ids_using in owners.items():
        if len(ids_using) > 1:
            problems.append(f"duplicate cover_url {url} used by ids {ids_using}")

    for entry in entries:
        rating = entry["rating_text"]
        if not rating:
            continue
        numerator, _, denominator = rating.rpartition("/")
        if denominator != "10":
            problems.append(f"id {entry['id']}: bad rating {rating!r}")
            continue
        try:
            value = float(numerator)
        except ValueError:
            problems.append(f"id {entry['id']}: bad rating {rating!r}")
            continue
        if not 0 <= value <= 10:
            problems.append(f"id {entry['id']}: rating out of range {rating!r}")

    if category == "movies":
        dates = [parse_watched(entry["date_watched"]) for entry in entries]
        if dates != sorted(dates):
            problems.append("movies not sorted by date_watched oldest-first")
    else:
        flags = [bool(entry["rating_text"]) for entry in entries]
        # The `False in flags` guard matters: list.index raises ValueError when
        # every entry is rated, which reads like corruption but is not.
        if False in flags and any(flags[flags.index(False) :]):
            problems.append("TBR block is not contiguous at the end")

    return problems


def validate_all() -> dict[str, list[str]]:
    """Validate every category, keyed by category id."""
    return {category: validate(category) for category in CATEGORY_IDS}
