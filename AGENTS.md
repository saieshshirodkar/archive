# Archive — saiesh-archive

Personal media catalog for books, animanga, movies, and TV shows. Vanilla HTML/CSS/JS, no framework, deployed on Cloudflare Workers (static assets).

**This file is mostly about the data workflow.** Most requests are "add this" or "rate this". Read Workflow before touching `data/`.

## Stack

- Vanilla HTML + CSS + JS, one CSS file + one JS file, no build step for the site itself
- Google Fonts: Geist + Geist Mono
- Python dev via `uv` (`pyproject.toml`, dev dep `ruff`), venv at `.venv/`
- Deployed on Cloudflare Workers static assets via the `cf` CLI (beta)

## Layout

```
/
├── index.html              # Entry: preloads + app.css + app.js
├── AGENTS.md               # This file
├── app.css                 # All styles in one file, tokens first
├── app.js                  # All JS in one file, no modules
├── favicon.svg             # plain SVG glyph for the tab
├── deploy.ts               # bun script: stages dist/ then runs `cf deploy`
├── _headers                # cache headers for assets/data/app files
├── cloudflare.config.ts    # cf project config (worker name, compat date)
├── wrangler.config.ts      # assetsDirectory: ./dist (cf delegates the build to wrangler)
├── package.json + bun.lock # bun project, dev deps: cf + wrangler
├── data/                   # books.json, animanga.json, movies.json, shows.json
├── assets/covers/          # books/, anime/, movies/, shows/ — 400px webp q80
├── scripts/                # archive.py + add/check/cover/query/rate/remove/reorder
├── tests/                  # unittest suite for scripts/ (stdlib only)
├── pyproject.toml          # uv project, dev = ruff
└── uv.lock
```

`dist/`, `.cloudflare/` and `.wrangler/` are build output and gitignored.

## Frontend (`app.css`, `app.js`)

Single files, no imports. Bundle order in `app.js` is dependency order: config → storage → state → utils → header → cards → renderer → indicator → data → main. Imports/exports stripped at bundle time; don't reintroduce per-file modules.

Keep these behaviors:

- **Race guard:** `token` in `loadCategory()`; every `await` followed by `if (mine !== token) return`.
- **Boot:** render header/grid once, `loadCategory()`, then `preloadCategory()` for all other ids on idle. Cached tab switch must check `entries.get()` before touching DOM (no skeleton flash).
- **Switch:** 160ms opacity ramp only (`.4→1`). No translate, stagger, or fade-out. Skipped entirely under `prefers-reduced-motion` (check `REDUCE_MOTION`, not just CSS).
- **Render:** `buildCardsHTML()` single string into `grid.innerHTML` once. No per-card `appendChild`, no entrance animation, no scroll anchoring. `scroll-behavior:auto; overflow-anchor:none;`, `history.scrollRestoration='manual'`, scroll to top on switch.
- **Images:** first 4 eager (`decoding=sync`, `fetchpriority=high`), rest lazy/async. One delegated capture-phase `error` listener on grid. Covers fill the grid column: `display:block; width:100%` with `aspect-ratio:2/3` + `object-fit:cover` (crop to 2:3). Every `<img>` carries `width`/`height` from its entry so layout reserves space.
- **Fetch priority:** the visible tab loads at `priority: 'high'`; idle preloads of the other three use `'low'` so background fetches don't compete with what the user is looking at.
- **States:** loading (skeleton + `aria-busy="true"`), empty (`No books yet.`), error (`role="alert"`, message, focused Retry button that re-fetches). `aria-busy` must be set to `"false"` on the error path too, or the panel stays busy forever.
- **Tilt:** `tiltFor()` derives `--r` from a hash of id+title, so it is stable across renders. Do not go back to `Math.random()` per render, or the whole grid reshuffles its tilt on every tab switch.
- **Tabs:** ARIA tablist, roving tabindex, indicator via `getBoundingClientRect()`, first placement transition-free, re-measure on resize/orientationchange/fonts-ready. Stats from `entries`, hidden ≤640px. Rounded corners (`--radius-pill:9999px`), back-to-top button is circular (`9999px`).
- **CSS:** `:root` owns all responsive values; `@media (max-width:640px)` overrides tokens only (except hiding `.stats` and clipping `.logo` ≤640px). Grid breakpoints 1100px→3 cols, 820px→2 cols; tilt halves ≤540px; `--tab-px:10px` ≤360px. `.book-card, .skeleton-card` share one flex rule. New responsive value = token + override, not new selector.
- **Media query order:** descending by breakpoint (1100 → 820 → 640 → 540 → 360). With `max-width` queries the narrowest must come last or its `:root` overrides get beaten by the wider block.
- **State containers:** `.empty-state`, `.error-state`, `.loading-state` need `grid-column: 1 / -1`, or they get trapped in the first grid column.
- **Mobile:** html 112.5%→100%, tab height 44px minimum. Keep `viewport-fit=cover`, `env()` with `0px` fallback, horizontal padding in `.container` only, `overflow-wrap:break-word` + `minmax(0,1fr)`. The `<h1>` stays in the accessibility tree on mobile via clip, not `display:none`.

### Design reasons

Dials: `ENERGY 2 / RHYTHM 2 / MOTION 1` (lavender cover grid, per-card tilt, hover + fade only).

- Lavender + Geist = Catppuccin-style minimal, lets covers carry the color.
- Geist Mono for index/rating/dates = metadata reads as data, not decoration.
- Gold only on 10/10 = one accent for the one thing worth flagging.
- Pill tabs = simple chrome, circular back-to-top only.
- Hairline separators stay quiet behind covers; text contrast is AA.
- Lucide chevron-up = single 20px stroke icon, relevance is "scroll to top".
- Per-card tilt = calm random rotate with no drift, halved on small screens.

## Data rules

- `id` = 1-indexed array position. Every write renumbers via `normalise()`. Never trust old ids.
- Key order fixed per category:
  - books/animanga: `id, title, author, rating_text, cover_url, year, width, height`
  - movies: `id, title, year, date_watched, rating_text, cover_url, width, height`
  - shows: `id, title, rating_text, cover_url, year, width, height` (never `author`, never `date_watched`)
- `rating_text` always `X/10` or `X.Y/10`. **No TBR.** Empty rating is invalid now.
- `date_watched` movies only, `DD-MM-YYYY`, decides `isMovie` in renderer. Written through `format_watched()`, so `1-2-2020` lands as `01-02-2020`.
- Titles are unique per category. `add.py` refuses a duplicate and `reorder.py --rename` refuses a target that already exists.
- `cover_url` relative path. Animanga lives in `assets/covers/anime/`, not `animanga/`. Always `400px` wide webp q80, `cover.py` verifies width.
- Ordering: movies sorted by `date_watched` oldest first; books/animanga/shows append in insertion order. Shows order is user-placed, don't sort.

## Workflow

```bash
websearch "<title> release year author"   # never guess title/author/year

uv run python scripts/add.py --cat <cat> --title "<title>" --year <year> \
    --rating <8|8.5> [--author "<author>"] [--cover-url "<url>"]
uv run python scripts/check.py
# deploy only when asked: bun deploy.ts
```

`--rating` is required. `--author` required for books/animanga. `--date` movies only, defaults to today IST. `--slug` for disambiguation. Covers always user-supplied URL, never hunt yourself.

- Movies year = theatrical. Animanga = anime first broadcast if aired else serialization. Books = publication. Shows = first-season premiere, no author.
- Rating an entry: `uv run python scripts/rate.py --cat <cat> --title "<title>" --rating <n> [--exact] [--position <id>]`. In place by default; `--position` moves. Find is case-insensitive substring; add `--exact` for short titles (`Baki`, `Bastard`).
- Movies are ordered by `date_watched`, so they take no positional moves. `rate.py --cat movies --date DD-MM-YYYY` sets the watch date and re-sorts. `reorder.py --position/--before/--after` refuses movies for the same reason.
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
| `rate.py` | rate in place / `--position` / `--date` (movies) |
| `reorder.py` | move / rename / `--sort` (not movies) |
| `remove.py` | delete entry + cover |

`save()` validates **before** writing, then writes through a temp file and `os.replace()`. A failed validation never reaches disk, so a bad command can't leave the repo broken.

Ruff: `uv run ruff check scripts/ tests/` + `uv run ruff format --check scripts/ tests/` must pass (line length 88, rules E4/E7/E9/F/UP/EXE).

## Tests

`tests/test_archive.py`, stdlib `unittest`, no network. Run it after touching anything in `scripts/`:

```bash
uv run python -m unittest discover -s tests
```

Covers `move()` in both directions, the `--before`/`--after` anchor math, `normalise()`, rating/date/slug parsing, every `validate_entries()` rule, `save()` atomicity, and the CLI behaviour of `add`/`rate`/`reorder` (including the refusals). The CLI tests redirect `archive.ROOT`/`DATA_DIR`/`COVERS_DIR` at a temp dir, so they never touch the real `data/`.

## Gotchas

- Covers: always browser UA `-A "Mozilla/5.0"` (gstatic, amazon, penguin, district, storyblok, redd.it reject otherwise). Extension lies sometimes, `file` tells truth. Amazon `_V1_FMjpg_UX1000_` and `_V1_` both work. gstatic thumbnails ~452x678, Wikipedia ~238x370 still upscale to 400. Strip `?utm_source=...` on wikimedia. Read the cover when user title is a guess, then search to confirm author/year. Poster brand can mislead platform (`Sapne vs Everyone` mX = Prime), disambiguate same-title by year/network.
- Slugs kebab-cased, `'`/`!`/`:` dropped, spaces→`-`. Variants get suffix only when needed (`baki-2018`, `tokyo-ghoul-re`).
- Titles: user spellings often wrong, web search wins, fix silently + one line note. Collisions: `Bastard`/`Bastard!!`, `Baki` variants, `Tokyo Ghoul` vs `Tokyo Ghoul:re`, `Dragon Ball` variants. Some titles are films not manga, check category first. Adaptations separate entries (`Verity` book + film).
- Rating `7/5` is rejected; ratings are out of 10 only. `normalise_rating()` takes bare numbers (`8`, `8.5`) and stores `X/10`.
- Deploy = Cloudflare Workers only (`bun deploy.ts`). Confirm the `https://saiesh-archive.shirodkarsrk.workers.dev` line and `◆ Deploy complete`, then stop. Push/commit need own words ("push", "commit"), never implied by deploy. Data edits never auto-deploy.
- `cf` is a beta CLI (1.0.0-beta.x) and its flags can move. `deploy.ts` is the only thing that talks to it, so a breaking change touches one file. `wrangler deploy` still works as a fallback, the generated configs are wrangler-compatible. One CLI per project: don't add a `wrangler.jsonc`, `cf` refuses to run in a project that has one.
- `node_modules/` is symlinks into `~/.bun/install/global/node_modules`, not a real install: `cf` and `wrangler` package dirs, plus `node_modules/.bin/{cf,wrangler}` pointing at each package's own `bin/` entry (the global `.bin/` has neither, so don't symlink from there). `cf/config` has to be resolvable from `cloudflare.config.ts` and cf has to see wrangler declared in `package.json`, but a real `bun install` pulls 197M of workerd/miniflare binaries this project never runs. Use `bun run setup` to relink after a clone. Never run a bare `bun install` here.
- `bun add -g cf wrangler` installs both CLIs globally. `cf` delegates the actual asset upload to wrangler, so both are needed. The global tree is shared with bun's package cache, so the bytes exist once on disk.
- `deploy.ts` stages `dist/` from an explicit file list before deploying. Never point `assets.directory` at the repo root. A `.assetsignore` in the assets dir *replaces* wrangler's built-in ignore list instead of adding to it, so a root assets dir silently publishes `.git`, `.env.local` and `scripts/`. The staging dir makes that impossible.
- `cf auth login` uses OAuth device flow by default and stores creds in `~/.config/cloudflare/`. `cf auth whoami` shows the account and scopes. `cf` and wrangler are both installed globally with bun (cf delegates the asset upload to wrangler).
- Cache policy lives in `_headers`: `data/*.json` is `no-store` so edits show up on the next load, and `assets/` is `max-age=300, must-revalidate` so a `cover.py --force` replacement lands within five minutes. Never add `immutable` or long `stale-while-revalidate` to either — that is what forced hard refreshes. `app.js` also fetches data with `cache: 'no-store'` as a second line of defense. Workers defaults every asset to `max-age=0, must-revalidate`, so unmatched files still revalidate.
- Cloudflare serves HTTP/3 by default (`alt-svc: h3=":443"`), Vercel did not. Static asset requests are free and unmetered, the 100k/day Workers quota only counts requests that run Worker code, and this project has no script.
- User checks UI in browser. `node --check app.js` and `check.py` are enough for a quick pass. A headless browser run is a useful supplement for the states that are awkward to reach by hand (failed fetch, empty category, arrow-key traversal), but it is not a substitute for the user's own look at the page.
- Never `pkill -f` a pattern in your own command. Capture `$!`, `kill $PID`.
- No comments in JS/CSS code. Scripts: minimal comments only when needed, code should read clearly.
- `.env.local` holds a legacy Vercel token, gitignored, never commit/share. Cloudflare creds live in `~/.config/cloudflare/`, outside the repo. `deploy.ts` stages an explicit file list, so nothing secret can reach `dist/`.
- Brand is plain `Archive` (`favicon.svg` glyph only, no service worker, no grain).
- Covers are stored 400px wide webp q80, rendered at grid-column width (cropped to 2:3 via object-fit). User declined 240px resize (12-10-2026). Don't shrink again.
- `user-select:none` is global (`*`), intentional.

## Commands

```bash
bun run setup                                                             # relink cf + wrangler from the global bun install
bun deploy.ts                                                                 # deploy
bun deploy.ts --dry-run                                                      # build + checks, no upload
uv run python scripts/check.py                                             # validate data
uv run python scripts/query.py date                                        # IST today
uv run python -m unittest discover -s tests                                # test scripts/
uv run ruff check scripts/ tests/ && uv run ruff format --check scripts/ tests/   # lint
node --check app.js                                                     # syntax
python3 -m http.server 8000                                                # dev server
```

Prod: https://saiesh-archive.shirodkarsrk.workers.dev · Legacy: https://saiesh-archive.surge.sh
