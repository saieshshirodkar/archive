# Archive — saiesh-archive

Personal media catalog for books, animanga, movies, and TV shows. Vanilla HTML/CSS/JS, no framework, deployed on Vercel.

**This file is mostly about the data workflow.** Most requests are "add this" or "rate this". Read Workflow before touching `data/`.

## Stack

- Vanilla HTML + CSS + JS, one CSS file + one JS file, no build step
- Google Fonts: Geist + Geist Mono
- Python dev via `uv` (`pyproject.toml`, dev dep `ruff`), venv at `.venv/`
- Deployed on Vercel (static)

## Layout

```
/
├── index.html              # Entry: preloads + css/app.css + js/app.js
├── AGENTS.md               # This file
├── css/app.css             # All styles in one file, tokens first
├── js/app.js               # All JS in one file, no modules
├── data/                   # books.json, animanga.json, movies.json, shows.json
├── assets/covers/          # books/, anime/, movies/, shows/ — 400px webp q80
├── scripts/                # archive.py + add/check/cover/query/rate/remove/reorder
├── pyproject.toml          # uv project, dev = ruff
└── uv.lock
```

## Frontend (`css/app.css`, `js/app.js`)

Single files, no imports. Bundle order in `js/app.js` is dependency order: config → storage → state → utils → header → cards → renderer → indicator → data → main. Imports/exports stripped at bundle time; don't reintroduce per-file modules.

Keep these behaviors:

- **Race guard:** `token` in `loadCategory()`; every `await` followed by `if (mine !== token) return`.
- **Boot:** render header/grid once, `loadCategory()`, then `preloadCategory()` for all ids in parallel. Cached tab switch must check `entries.get()` before touching DOM (no skeleton flash).
- **Switch:** 160ms opacity ramp only (`.4→1`). No translate, stagger, or fade-out.
- **Render:** `buildCardsHTML()` single string into `grid.innerHTML` once. No per-card `appendChild`, no entrance animation, no scroll anchoring. `scroll-behavior:auto; overflow-anchor:none;`, `history.scrollRestoration='manual'`, scroll to top on switch.
- **Images:** first 8 eager (`decoding=sync`, `fetchpriority=high`), rest lazy/async. One delegated capture-phase `error` listener on grid. Covers: 2/3 box, `display:block; width/height:100%; object-fit:cover; object-position:center`, no hover scale (border brighten only).
- **Tabs:** ARIA tablist, roving tabindex, pill via `getBoundingClientRect()`, first placement transition-free, re-measure on resize/orientationchange/fonts-ready. Stats from `entries`, hidden ≤640px.
- **CSS:** `:root` owns all responsive values; `@media (max-width:640px)` overrides tokens only, never re-declares `.book-card`/`.container`. `.book-card, .skeleton-card` share one grid rule. New responsive value = token + override, not new selector.
- **Mobile:** html 112.5%→100%, tab height 44px minimum, cover 76px, index 26px. Keep `viewport-fit=cover`, `env()` with `0px` fallback, horizontal padding in `.container` only, `overflow-wrap:break-word` + `minmax(0,1fr)`.

## Data rules

- `id` = 1-indexed array position. Every write renumbers via `normalise()`. Never trust old ids.
- Key order fixed per category:
  - books/animanga: `id, title, author, rating_text, cover_url, year`
  - movies: `id, title, year, date_watched, rating_text, cover_url`
  - shows: `id, title, rating_text, cover_url, year` (never `author`, never `date_watched`)
- `rating_text` always `X/10` or `X.Y/10`. **No TBR.** Empty rating is invalid now.
- `date_watched` movies only, `DD-MM-YYYY`, decides `isMovie` in renderer.
- `cover_url` relative path. Animanga lives in `assets/covers/anime/`, not `animanga/`. Always `400px` wide webp q80, `cover.py` verifies width.
- Ordering: movies sorted by `date_watched` oldest first; books/animanga/shows append in insertion order. Shows order is user-placed, don't sort.

## Workflow

```bash
websearch "<title> release year author"   # never guess title/author/year

uv run python scripts/add.py --cat <cat> --title "<title>" --year <year> \
    --rating <8|8.5> [--author "<author>"] [--cover-url "<url>"]
uv run python scripts/check.py
# deploy only when asked: vercel --prod
```

`--rating` is required. `--author` required for books/animanga. `--date` movies only, defaults to today IST. `--slug` for disambiguation. Covers always user-supplied URL, never hunt yourself.

- Movies year = theatrical. Animanga = anime first broadcast if aired else serialization. Books = publication. Shows = first-season premiere, no author.
- Rating an entry: `uv run python scripts/rate.py --cat <cat> --title "<title>" --rating <n> [--exact] [--position <id>]`. In place by default; `--position` moves. Find is case-insensitive substring; add `--exact` for short titles (`Baki`, `Bastard`).
- Read-only: `uv run python scripts/query.py find|top|latest|show`. Always search all four categories before saying missing. `latest` = highest ids, not array tail (same thing now, but keep meaning).
- IST today: `uv run python scripts/query.py date`. Never use UTC/system date. Explicit user date always wins.
- MangaDex UUID URLs: `api.mangadex.org/manga/<uuid>?includes[]=author&includes[]=artist` for canonical title/year when web search fails.
- Validate: `uv run python scripts/check.py` runs same checks as `save()` (ids sequential, key order, cover set equality both ways, dup `cover_url`, rating parse, movies sorted).

## Scripts

Run from repo root with `uv run`. `archive.py` is shared lib (not executed directly).

| script | use |
|---|---|
| `archive.py` | paths, load/save, lookup, move, validate |
| `add.py` | add one entry + cover |
| `check.py` | validate all four |
| `cover.py` | install cover / `--audit` |
| `query.py` | `date/find/top/latest/show` |
| `rate.py` | rate in place / `--position` |
| `reorder.py` | move / rename / `--sort` (not movies) |
| `remove.py` | delete entry + cover |

Ruff: `uv run ruff check scripts/` + `uv run ruff format --check scripts/` must pass (line length 88, rules E4/E7/E9/F/UP/EXE).

## Gotchas

- Covers: always browser UA `-A "Mozilla/5.0"` (gstatic, amazon, penguin, district, storyblok, redd.it reject otherwise). Extension lies sometimes, `file` tells truth. Amazon `_V1_FMjpg_UX1000_` and `_V1_` both work. gstatic thumbnails ~452x678, Wikipedia ~238x370 still upscale to 400. Strip `?utm_source=...` on wikimedia. Read the cover when user title is a guess, then search to confirm author/year. Poster brand can mislead platform (`Sapne vs Everyone` mX = Prime), disambiguate same-title by year/network.
- Slugs kebab-cased, `'`/`!`/`:` dropped, spaces→`-`. Variants get suffix only when needed (`baki-2018`, `tokyo-ghoul-re`).
- Titles: user spellings often wrong, web search wins, fix silently + one line note. Collisions: `Bastard`/`Bastard!!`, `Baki` variants, `Tokyo Ghoul` vs `Tokyo Ghoul:re`, `Dragon Ball` variants. Some titles are films not manga, check category first. Adaptations separate entries (`Verity` book + film).
- Rating `7/5` means `7.5/10`. Ratings out of 10 only.
- Deploy = Vercel only (`vercel --prod`, never `--scope`). Confirm `▲ Aliased https://saiesh-archive.vercel.app` or `"status":"ok"` JSON and stop. Don't curl live URL, don't grep output (JSON form has no Aliased line). `Not authorized` on first try is transient, retry once. Push/commit need own words ("push", "commit"), never implied by deploy. Data edits never auto-deploy.
- User checks UI in browser. No headless/jsdom layout checks. `node --check js/app.js` and `check.py` are enough.
- Never `pkill -f` a pattern in your own command. Capture `$!`, `kill $PID`.
- No comments in JS/CSS code. Scripts: minimal comments only when needed, code should read clearly.
- `.env.local` holds Vercel token, gitignored, never commit/share.
- No favicon, no service worker, no grain. Brand is plain `Archive`.
- Covers render at 120px/76px but stored 400px. User declined 240px resize (12-10-2026). Don't shrink again.
- `user-select:none` is intentional.

## Commands

```bash
vercel --prod                                                              # deploy
uv run python scripts/check.py                                             # validate data
uv run python scripts/query.py date                                        # IST today
uv run ruff check scripts/ && uv run ruff format --check scripts/          # lint
node --check js/app.js                                                     # syntax
python3 -m http.server 8000                                                # dev server
```

Prod: https://saiesh-archive.vercel.app · Legacy: https://saiesh-archive.surge.sh
