# scripts/ — archive CLI

Python helpers for the data in `../data/*.json`. They exist so the ordering
rules, key order, and cover-path rules live in one place instead of being
retype into every command.

## Scripts

| script | does |
|---|---|
| `archive.py` | shared library — categories, key order, dates, slugs, load/save, validation. Not run directly. |
| `add.py` | add an entry to any category, optionally fetching its cover |
| `cover.py` | download and resize covers, or audit the ones on disk |
| `rate.py` | rate an entry in place, move it with `--position`, or set a movie's date |
| `reorder.py` | move, rename, or bulk-sort entries |
| `remove.py` | delete an entry and its cover, then renumber |
| `query.py` | read-only: dates, find, top, latest, show |
| `check.py` | validate all four categories |

## Quick start

```bash
cd scripts

python3 check.py                       # validate everything
python3 query.py date                  # today in IST, DD-MM-YYYY
python3 query.py find neverland        # search all categories
python3 query.py top 10                # highest rated
python3 query.py latest 5              # newest by id

python3 add.py --cat books --title "Dune" --author "Frank Herbert" \
    --year 1965 --rating 9.5
python3 add.py --cat movies --title "The Birthday Gift" --year 2026 \
    --cover-url "https://m.media-amazon.com/images/M/....jpg"
python3 cover.py --cat books --title "Dune" --file /tmp/dune.jpg
python3 cover.py --cat shows --title "Carrie" --url "https://..." --force
python3 cover.py --audit                # wrong widths, formats, oversized files
python3 rate.py --cat books --title "little life" --rating 8.8
python3 rate.py --cat animanga --title "Baki" --rating 4 --exact
python3 rate.py --cat movies --title "Atonement" --rating 9 --date 03-03-2021
python3 reorder.py --cat shows --title "Raakh" --before "Superstore"
python3 reorder.py --cat books --sort rating --descending
python3 remove.py --cat animanga --title "Vagabond"
```

Every write validates before reporting success, so `check.py` after a batch is
belt-and-braces rather than the only safety net.

## Picking an entry

Title matching is a substring search by default, so `housemaid is watching`
finds the book. That is also where the ambiguity comes from: `Baki` matches
three entries, and no shorter needle separates them, since it is a prefix of
all three.

`--exact` demands a whole-title match and is the fix for those cases. It
exists on `rate.py` and `reorder.py`, and it covers `--before`/`--after`
anchors as well as `--title`:

```bash
python3 rate.py --cat animanga --title "Baki" --rating 4 --exact
```

An ambiguous title is always an error; the candidates get listed so the right
one can be named. Under `--exact` they print as near-misses instead, which is
usually what was meant. The decision itself lives in one place,
`archive.resolve_index()`, so the tools do not each reimplement it.

## Rules encoded here

**Categories and key order** — `archive.py:CATEGORIES` is the single source of
truth. `animanga` stores its covers under `assets/covers/anime/`, which is the
one folder that doesn't match its id. `movies` carries `date_watched` and has
no `author`; `shows` has neither, because a show has multiple creators and no
single watch date.

**Position** — `id` is always the 1-indexed array position, recomputed from the
list on every save by `normalise()`. Never trusted from the previous state.

- movies sort by `date_watched`, oldest first. Missing `--date` means today IST.
- books, animanga and shows append in insertion order.
- shows within the rated block are insertion order only. `reorder.py --sort`
  can impose a canonical order if you want one.
- movies take no positional moves, because their position is derived from the
  watch date. `rate.py --cat movies --date DD-MM-YYYY` sets that date and
  re-sorts. `reorder.py --position/--before/--after` refuses movies outright
  rather than writing a list that breaks the ordering invariant.

**Moving** — `archive.move()` takes the index the entry sits at and the index
it should end up at, in the array *after* the move. `reorder.py` turns a
`--before`/`--after` anchor into that target index via `anchor_target()`, which
accounts for the anchor shifting when the moved entry came from before it.

**Dates** — everything is IST via `zoneinfo.ZoneInfo("Asia/Kolkata")`. Nothing
here calls `datetime.now()` without an explicit zone, because the system clock
is usually UTC and that mismatch has silently produced wrong entries.
`parse_watched()` uses `strptime`, so impossible dates like `99-99-2026` are
rejected instead of sorting as if they were real.

**Ratings** — stored as `X/10` or `X.Y/10`. `normalise_rating()` accepts bare
numbers (`8`, `8.5`) and rejects things like `7/5`, which is a different
habit and would otherwise be silently misread.

**Titles** — unique within a category. `add.py` refuses a title that is already
there, and `reorder.py --rename` refuses to rename an entry onto a title that
another entry already holds. Without that guard a rename could leave two
entries that no longer resolve by name, and the reported id could point at the
wrong one.

**Covers** — `cover.py` is the one place that writes images. It downloads with
a browser user agent (several CDNs reject anything else), auto-orients, resizes
to 400px wide, encodes webp at quality 80, and verifies the width before
reporting success. `add.py --cover-url` calls the same `cover.install()`, so
both commands produce identical files.

- Filenames come from `archive.slugify()`: kebab-case, apostrophes and other
  punctuation dropped (`Takopi's` → `takopis`, `Bastard!!` → `bastard`).
  Disambiguating suffixes (`baki-2018`, `tokyo-ghoul-re`) are passed with
  `--slug`.
- Existing covers are never replaced without `--force`, because re-encoding a
  downscaled copy is lossy and the repo does not regenerate covers by accident.
- The target folder is `covers_dir()`, so animanga lands in `anime/` every
  time rather than only when someone remembers the mapping.
- `--audit` reports anything that is not 400px wide, not webp, or over 200 KB.
  It does not duplicate `validate()`'s reference checks; `check.py` owns those.

## Validation

`validate()` returns a list of problems; empty means valid. It is split into
`validate_entries()` (the list itself) and `validate_covers()` (the files on
disk), so a list can be checked before anything is written. The checks each
correspond to a bug that actually happened here:

- ids sequential from 1 — a split insert leaves them inconsistent
- exact key set *and* key order — schema drift
- referenced covers vs files on disk — catches a wrong path and an orphan file
- no duplicate `cover_url` — this caught Fearless pointing at `fearful.webp`,
  which rendered two different books as one image
- movies sorted by date
- rating format and range

`save()` runs both halves of the validation *before* it opens the data file,
then writes through a temporary file and `os.replace()`. A command that would
have produced invalid data therefore fails with the file untouched, instead of
leaving a broken `data/*.json` behind and raising afterwards.

## Tests

```bash
python3 -m unittest discover -s tests
```

`tests/test_archive.py` covers the parsing helpers, every validation rule,
`move()` in both directions, the `--before`/`--after` anchor arithmetic, and
the `add`/`rate`/`reorder` command behaviour. The command tests point
`archive.ROOT` at a temporary directory, so they never read or write the real
`data/`.

## Notes

- Sorting is one ascending key plus `reverse=True`. Nothing negates a sort
  value, which is what silently broke `--sort title --descending` — there is
  no `-"abc"`.
- Comments are deliberate here, unlike `js/`, where AGENTS.md forbids them.
- `add.py` refuses to add an entry whose cover file is absent, so a bad slug
  fails loudly instead of rendering a grey box. It also rejects a filename
  another entry already uses, and does so before the write: `validate()` would
  only catch the duplicate afterwards, leaving the bad entry on disk.
- `remove.py` moves the cover aside before saving, then deletes it. `save()`
  rejects unreferenced files on disk, so deleting afterwards would fail its
  own validation; the stash is restored if the write raises.
- Deploy is still manual: `vp` (or `vercel --prod` when the alias isn't
  available in a non-interactive shell).
