# scripts/ — archive CLI

Python helpers for the data in `../data/*.json`. They exist so the ordering
rules, key order, and cover-path rules live in one place instead of being
retype into every command.

## Scripts

| script | does |
|---|---|
| `archive.py` | shared library — categories, key order, dates, load/save, validation. Not run directly. |
| `add.py` | add an entry to any category |
| `rate.py` | rate an entry; moves TBR→rated, or in-place if already rated |
| `reorder.py` | move, rename, or bulk-sort entries |
| `query.py` | read-only: dates, find, top, latest, tbr, show |
| `check.py` | validate all four categories |

## Quick start

```bash
cd scripts

python3 check.py                       # validate everything
python3 query.py date                  # today in IST, DD-MM-YYYY
python3 query.py find neverland        # search all categories
python3 query.py top 10                # highest rated
python3 query.py latest 5              # newest rated by id
python3 query.py tbr --cat books       # what's unrated

python3 add.py --cat books --title "Dune" --author "Frank Herbert" \
    --year 1965 --rating 9.5
python3 rate.py --cat books --title "little life" --rating 8.8
python3 reorder.py --cat shows --title "Raakh" --before "Superstore"
python3 reorder.py --cat books --sort rating --descending
```

Every write validates before reporting success, so `check.py` after a batch is
belt-and-braces rather than the only safety net.

## Rules encoded here

**Categories and key order** — `archive.py:CATEGORIES` is the single source of
truth. `animanga` stores its covers under `assets/covers/anime/`, which is the
one folder that doesn't match its id. `movies` carries `date_watched` and has
no `author`; `shows` has neither, because a show has multiple creators and no
single watch date.

**Position** — `id` is always the 1-indexed array position, recomputed from the
list on every save by `normalise()`. Never trusted from the previous state.

- movies sort by `date_watched`, oldest first. Missing `--date` means today IST.
- books, animanga and shows keep rated entries first, TBR block last. A new
  rated entry lands after the last rated one; a new unrated entry goes at the end.
- shows within the rated block are insertion order only. `reorder.py --sort`
  can impose a canonical order if you want one.

**Dates** — everything is IST via `zoneinfo.ZoneInfo("Asia/Kolkata")`. Nothing
here calls `datetime.now()` without an explicit zone, because the system clock
is usually UTC and that mismatch has silently produced wrong entries.

**Ratings** — stored as `X/10` or `X.Y/10`. `normalise_rating()` accepts bare
numbers (`8`, `8.5`) and rejects things like `7/5`, which is a different
habit and would otherwise be silently misread.

## Validation

`validate()` returns a list of problems; empty means valid. The checks each
correspond to a bug that actually happened here:

- ids sequential from 1 — a split insert leaves them inconsistent
- exact key set *and* key order — schema drift
- referenced covers vs files on disk — catches a wrong path and an orphan file
- no duplicate `cover_url` — this caught Fearless pointing at `fearful.webp`,
  which rendered two different books as one image
- movies sorted by date; TBR block contiguous elsewhere. The `False in flags`
  guard matters: `list.index` raises when everything is rated, which looks
  like corruption but isn't.
- rating format and range

## Notes

- Comments are deliberate here, unlike `js/`, where AGENTS.md forbids them.
- `add.py` refuses to add an entry whose cover file is absent, so a bad slug
  fails loudly instead of rendering a grey box.
- These scripts do not touch the covers themselves. Download and resize with
  the `curl` + `magick` one-liner from AGENTS.md first, then run `add.py`.
- Deploy is still manual: `vp` (or `vercel --prod` when the alias isn't
  available in a non-interactive shell).