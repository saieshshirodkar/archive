# Archive — saiesh-archive

Personal media catalog for books, animanga, movies, and TV shows. Vanilla HTML/CSS/JS, no framework, deployed on Vercel.

**This file is mostly about the data workflow.** 90% of requests here are "add this movie/book/anime/show" or "rate this". Read the Workflow section before touching `data/`.

Current counts: books 75 (49 rated + 26 TBR) · animanga 118 (all rated) · movies 82 (81 rated + 1 unrated) · shows 62 (all rated). 337 covers, ~14MB total.

## Stack

- Vanilla HTML + CSS + JS (native ES modules — `type="module"`, no bundler)
- Google Fonts: Geist + Geist Mono
- No build step — nothing shipped beyond static assets
- Deployed on Vercel (static)

## Project Structure

```
/
├── index.html              # Entry point (7 CSS links + js/main.js, preload hints)
├── AGENTS.md               # This file
├── css/
│   ├── tokens.css          # Every design value, incl. all responsive tokens
│   ├── base.css            # Reset, html, body, focus ring, container, scrollbar
│   ├── header.css          # Header, nav, pill tabs, stats badge
│   ├── cards.css           # Card grid (shared w/ skeleton), covers, badges, titles
│   ├── legendary.css       # 10/10 gold badge + cover aura
│   ├── skeleton.css        # Skeleton + error + loading states
│   └── responsive.css      # Token overrides for ≤640px + reduced-motion
├── js/
│   ├── config.js           # CATEGORIES (source of truth), image/switch constants
│   ├── storage.js          # LocalStorage helpers (selectedCategory)
│   ├── state.js            # Shared state + `entries` cache map
│   ├── utils.js            # escapeHtml (regex)
│   ├── header.js           # Header build, ARIA tablist, stats, element accessors
│   ├── cards.js            # buildCardsHTML / buildSkeletonHTML string builders
│   ├── renderer.js         # DOM assembly, delegated img error, switch animation
│   ├── data.js             # loadCategory, preloadCategory, race guard
│   ├── indicator.js        # Tab pill indicator (resize + orientation)
│   └── main.js             # Bootstrap / wiring
├── data/
│   ├── books.json          # Book entries
│   ├── animanga.json       # Anime/manga entries
│   ├── movies.json         # Movie entries
│   └── shows.json          # TV show entries (no author, no date_watched)
├── assets/
│   └── covers/             # 268 covers, ~10.3MB total
│       ├── books/          # Book covers (.webp, 400px wide, q80)
│       ├── anime/          # Anime/manga covers — NOTE: folder is `anime`, not `animanga`
│       ├── movies/         # Movie posters (.webp, 400px wide, q80)
│       └── shows/          # TV show posters (.webp, 400px wide, q80)
└── .vercel/                # Vercel config (gitignored)
```

## Workflow

### The short version

```bash
# 1. search metadata (never guess)
websearch "<title> release year author"

# 2. download + resize cover (400px webp q80)
curl -sL -A "Mozilla/5.0" -o /tmp/opencode/cover.jpg "<url>" && \
  magick /tmp/opencode/cover.jpg -resize 400x -quality 80 assets/covers/<cat>/<slug>.webp && \
  identify assets/covers/<cat>/<slug>.webp && file /tmp/opencode/cover.jpg

# 3. insert into data/<cat>.json at the right position + renumber (one python -c)
# 4. validate ids
python3 -c "import json; d=json.load(open('data/<cat>.json')); assert [e['id'] for e in d]==list(range(1,len(d)+1)), 'ids not sequential'; print('OK', len(d))"

# 5. deploy only when the user says deploy
vp
```

Steps 3 + 4 are always one combined `python3 -c` that inserts, renumbers, dumps, and asserts in a single run. Do not split it across multiple invocations — a half-applied insert leaves ids inconsistent.

### The validation assert (use this verbatim, it has caught real bugs)

```bash
python3 -c "
import json, os
c='<cat>'; folder='anime' if c=='animanga' else c
d=json.load(open(f'data/{c}.json'))
order={'books':['id','title','author','rating_text','cover_url','year'],
       'animanga':['id','title','author','rating_text','cover_url','year'],
       'movies':['id','title','year','date_watched','rating_text','cover_url'],
       'shows':['id','title','rating_text','cover_url','year']}[c]
assert [e['id'] for e in d]==list(range(1,len(d)+1)), 'ids not sequential'
for e in d: assert list(e)==order, f'schema drift: {list(e)}'
assert {e['cover_url'].split('/')[-1] for e in d}==set(os.listdir(f'assets/covers/{folder}')), 'cover count mismatch'
seen={}
for e in d: seen.setdefault(e['cover_url'],[]).append(e['id'])
assert not {k:v for k,v in seen.items() if len(v)>1}, 'duplicate cover_url'
assert all(os.path.exists(e['cover_url']) for e in d), 'missing cover on disk'
f=[bool(e['rating_text']) for e in d]
if c=='movies':
    k=lambda e:[int(x) for x in reversed(e['date_watched'].split('-'))]
    assert [k(e) for e in d]==sorted(k(e) for e in d), 'not sorted by date_watched'
else:
    assert (not any(f[f.index(False):])) if False in f else True, 'TBR block not contiguous'
print(f'{c}: {len(d)} OK')
"
```

Notes on that block, all learned the hard way:

- **`if False in f` guard is mandatory.** A TBR-contiguity check written as `f[f.index(False):]` throws `ValueError: list.index(x): not in list` when *every* entry is rated. It looks like a data corruption when it isn't — the file is already written by then.
- **Key order is asserted, not just key presence.** Every write re-projects entries through `[{k: e[k] for k in order}]`; `list(e) == order` is what catches a new field sneaking in.
- **Duplicate `cover_url` detection is not optional.** The Fearless/Fearful mixup (id 58 pointing at `fearful.webp`) passed every other check and rendered two different books with the same image. Assert the set of used filenames equals the set of files in the folder — that catches both a dup reference *and* an orphan file on disk.
- **`cover_url` folder must match**, per the category's folder name (`anime` for animanga, otherwise the id).

### Adding a new movie / book / anime / show

1. **Web-search first.** Confirm the exact canonical title, author, and year. Never guess.
   - Movies: theatrical release year.
   - Animanga: anime's first broadcast year if that anime has aired; otherwise manga/manhwa/light-novel serialization year.
   - Books: publication year.
   - Shows: **initial release year** (first season's premiere). No `author` field — shows have multiple creators, so the entry is title + rating only.
   - Covers are **always** provided by the user as a URL. Never go hunting for a cover yourself.
2. **Download + resize the cover** (see short version above). Category folder is `books/`, `anime/`, `movies/`, or `shows/`.
3. **Insert at the correct position** per the ordering rules below, then renumber all ids 1..N.
4. **Validate** ids are sequential.
5. **Deploy only when asked.** Do not auto-deploy after a data edit.

### Ordering rules (the #1 source of bugs)

`id` is **always** the 1-indexed array position. Never append blindly — most additions are inserts that shift everything below them.

- **movies.json** — sorted by `date_watched`, oldest first, id 1. Append then re-sort with `[int(x) for x in reversed(e['date_watched'].split('-'))]` as the key, then renumber.
- **animanga.json** — rated entries (non-empty `rating_text`) first in first-watched order, then the unrated/TBR block.
- **books.json** — rated entries first in read order, then the unrated/TBR block.
- **shows.json** — rated block first, then unrated/TBR block. No `date_watched`, so the movies sort rule does **not** apply. **Within the rated block the order is purely insertion order** — the user places new shows by hand ("put X before Y") and there is no year or rating sort. Do not impose one.

Position for a new rated entry = `max(index where rating_text is not empty) + 1`.

**A hand-placed unrated entry breaks the trailing-TBR rule.** Inserting an unrated show above rated ones (done once with *Malcolm in the Middle*, 16-10-2026) leaves the TBR block non-contiguous. The assert flags it. It resolves itself the moment that entry gets a rating, since the block empties — that is what happened here. Don't reorder to "fix" it mid-request; flag it and let the rating land.

### Rating an existing TBR entry

- Find by `title` (case-insensitive substring is fine, print the match so the user can confirm).
- Set `rating_text`, `remove` from the TBR position, `insert` at `max(rated index) + 1`, renumber.
- **Move-after-last-rated is the default** (user-confirmed 30-09-2026). In-place with no move only when the user explicitly says "just change rating" / "don't move". Never reposition beyond this rule on your own.
- Changing the rating of an **already-rated** entry is in-place only — no move. (`make jjba to 9.7`, `berserk to 9.3`, `re zero to 4/10` are all in-place.)
- Reordering within the rated block: `remove` then `insert` before the reference entry, then renumber.

### Dates

`date_watched` is always `DD-MM-YYYY`.

When the user says "today", "taoday", or gives no date at all for a movie:

```bash
TZ=Asia/Kolkata date +"%d-%m-%Y %H:%M %Z"
```

IST, always. Never use the UTC/system date or a date carried over from an earlier session — those have silently produced wrong entries before.

An explicit date from the user (e.g. `"watched 2nd oct"`, `"09-08-2026"`) always wins.

### Read-only requests

- `find <title>` / `check if X is there` — search **all four** JSONs, print `id`, title, author (if present), year, rating, cover path. Do not edit anything.
- `top 10` / `top 15` / `latest 5 rated` — sort by numeric rating (parse `float(rating_text.split('/')[0])`, never string sort). "Latest rated" means the **top of the rated block** (highest ids among rated), not the tail of the array.
- The TBR block sits at the end of the array, so "last 5 entries" is always unrated — if the user asks for latest and gets TBR titles, they meant the rated block.
- **Always search every category before saying something is missing.** "Is X in here?" means all four files. *The Promised Neverland* was absent from all of them and *Dr. Stone* was sitting unrated in the TBR block at id 102; both looked missing from a single-category glance. Report which file matched.
- MangaDex URLs carry the manga UUID in the path: `mangadex.org/covers/<uuid>/<file>.jpg`. Hit `api.mangadex.org/manga/<uuid>?includes[]=author&includes[]=artist` for the canonical title, year, status and creators. This works when web search returns nothing, which is common for recent and obscure titles.

## Data Model

Books and animanga:

```json
{
  "id": 1,
  "title": "Death Note",
  "author": "Tsugumi Ohba & Takeshi Obata",
  "year": 2006,
  "rating_text": "10/10",
  "cover_url": "assets/covers/anime/death-note.webp"
}
```

Movies:

```json
{
  "id": 1,
  "title": "Balan: The Boy",
  "year": 2026,
  "date_watched": "03-08-2026",
  "rating_text": "9/10",
  "cover_url": "assets/covers/movies/balan-the-boy.webp"
}
```

Shows — **no `author`, no `date_watched`**. Key order is fixed:

```json
{
  "id": 1,
  "title": "Pritam and Pedro",
  "rating_text": "",
  "cover_url": "assets/covers/shows/pritam-and-pedro.webp",
  "year": 2026
}
```

- `id` — 1-indexed position. Matches watch order for animanga.
- `rating_text` — `"X/10"` or `"X.Y/10"`. `""` means unrated/TBR. Movies also use `""` but show **no** badge.
- `year` — release year, rendered after the title as `(2006)`. Optional on books (most books here have it now). Shows always have it.
- `date_watched` — movies only, `DD-MM-YYYY`, rendered as the meta line. Its presence is what marks an entry as a movie. **Shows must never have this key** — `cards.js` uses `date_watched != null` to decide `isMovie`, and a show with that key would render as a film with no badge.
- `author` — books/animanga only. Absent on shows; `cards.js` already falls back to an empty meta line, so no renderer change is needed.
- `cover_url` — relative path. **anime** covers live in `assets/covers/anime/`, not `animanga/`. Shows live in `assets/covers/shows/`.

Rendering rules that depend on these fields:

- `rating_text === "10/10"` → gold badge + cover aura (`is-legendary`). Dynamic, no hardcoded list. Currently: Death Note, One Piece, Naruto Shippuden, Breaking Bad, Dark. Titles are **not** styled differently — the shimmer was removed by request.
- Empty `rating_text` + not a movie → grayscale dimmed cover + `TBR` badge (`is-tbr`). This is how shows behave, same as books/animanga.
- Movies show `(year)` + `DD-MM-YYYY`, and no badge when unrated.
- Shows show `(year)` and an **empty** `.book-author` meta line. The div is still emitted (the three-children contract holds); it just has no text.

## Architecture

### Module Graph

- All `js/*.js` are ES modules. Acyclic: `main → data → renderer → header/cards`, `data → indicator → header`. Tab clicks are wired in `main.js` via `onTabChange(loadCategory)` — never import `data.js` from `header.js` (that creates a cycle).
- `config.js` holds `CATEGORIES` — the single source of truth for ids, labels, and singular nouns. `CATEGORY_IDS` and `CATEGORY_BY_ID` derive from it. Add or rename a category there, nowhere else.
- `state.js` holds `entries` (Map: category id → resolved array) and `state { category, items, status }`. There is deliberately **no** separate `counts` object — derive it as `entries.get(id)?.length`.
- `data.js` holds a `pending` Map of in-flight promises that self-deletes on resolve, since `entries` short-circuits afterwards. One map of resolved data + one of promises; do not add a third.
- `header.js` owns direct element refs and exposes `activeTab()`, `tabTrack()`, `indicatorEl()` so `indicator.js` never has to re-query the document.
- **Race guard**: `token` in `data.js` guards stale async after rapid tab switches. Every `await` in `loadCategory` must be followed by `if (mine !== token) return`.
- **Boot flow**: `main.js` renders once (header + grid), places the pill via `updateIndicator()`, calls `loadCategory()`, then kicks off `preloadCategory()` for every id in `CATEGORY_IDS`. All fetches run in parallel from the same tick.
- **Adding a category** touches three files and nothing else: `js/config.js` (`CATEGORIES`), `index.html` (a `rel="preload"` line), and a new `data/<id>.json` + `assets/covers/<folder>/`. The tab pill, tab memory, race guard, and renderer are all generic — no per-category code exists. If you find yourself adding an `if (category === ...)` branch, the category was added wrong.

### Tab Switch

- **Cached** (always true in practice — everything preloads at boot): synchronous swap inside the click handler. Checks `entries.get()` **before** touching the DOM, so no skeleton frame ever flashes.
- **Uncached**: skeleton → fetch → content.
- Animation is a single 160ms opacity ramp (`.4 → 1`) via the Web Animations API in `renderer.js`. No translate, no stagger, no fade-out.
- Never reintroduce a fade-out-then-wait step. It costs a skeleton flash and the user explicitly asked for fast switches (12-10-2026).

### Rendering & UX

- **Single-pass HTML**: `buildCardsHTML()` returns one string; `renderer.js` assigns it to `grid.innerHTML` once. Never loop with `createElement` + `appendChild` per card.
- **No entrance animation.** Cards exist visible in the DOM on first paint. `js/observer.js` and the IntersectionObserver were deleted by request.
- **Images**: first `EAGER_LOAD_COUNT` (8) get `decoding="sync"` + `fetchpriority="high"`; the rest use native `loading="lazy"` + `decoding="async"`. Sync decode on the eager set is deliberate — it avoids a blank first frame.
- **Image errors** are handled by one delegated `error` listener on the grid in **capture phase** (image `error` does not bubble). Do not attach per-image listeners.
- **Stats badge**: reads from `entries`, so it shows the real count regardless of what's rendered. Hidden at `≤640px`.
- **Scroll reset**: every category load scrolls to top; refresh starts at top (`history.scrollRestoration = 'manual'`). `scroll-behavior` is `auto` and `overflow-anchor: none` on `html` — smooth scrolling and Chrome's scroll anchoring both fought the reset and caused a visible jump when a tall list swapped for a short one. Do not re-add either.
- **Pill indicator**: `getBoundingClientRect()` math in `indicator.js`, re-measured on `resize` and `orientationchange` (100ms). First placement is transition-free via the `placed` flag so the pill paints already on the restored tab — don't re-add a transition there.
- **Tab memory**: `localStorage.selectedCategory`, read in `state.js` at module load. Works automatically.

### CSS architecture

- **`tokens.css` owns every value that changes at a breakpoint.** `responsive.css` overrides tokens inside `:root` — it does **not** re-declare selectors like `.book-card` or `.container`.
- This is the rule that matters most. The old layout re-declared those selectors with hardcoded overrides, which is what caused both the header double-padding bug and the index-column overflow bug. Duplicated responsive values drift.
- `.book-card, .skeleton-card` share one grid rule so the two can never fall out of sync.
- Any new responsive value gets a token in `tokens.css` + an override in the media query. Not a new selector.

### Mobile (≤640px)

- `html` font-size 112.5% → 100%, so all rem sizing scales down automatically.
- Nav centered; logo and stats badge hidden — just the pill.
- Cards compact: `26px 76px minmax(0,1fr)`, cover 76px wide. The index column is 26px because animanga reaches three digits (`112`) and 0.75rem Geist Mono needs ~22px.
- Tab buttons are `min-height: 44px` with `gap: 2px` — Apple HIG and WCAG 2.5.5 both require 44×44px targets. Do not drop below 44.
- **Four tabs now.** `Animanga` is the long one. Estimated pill width ≈294px at `--fs-tab: 0.8rem` and `--tab-px: 14px`. That fits down to a 360px viewport but **overflows at 320px** (288px available). `body` has `overflow-x: hidden`, so on a 320px device the pill gets clipped rather than scrolling. If that ever needs fixing, drop `--tab-px` to `10px` in the `responsive.css` override — do **not** shorten the `Animanga` label or shrink below 44px touch targets.
- Safe-area insets are respected: `viewport-fit=cover` in the viewport meta, `env()` always with a `0px` fallback (a fallbackless `env()` invalidates the whole declaration), and `max()` for a floor on devices without insets.

### Gotchas that cost real debugging time

- **`viewport-fit=cover` is mandatory.** Without it every `env(safe-area-inset-*)` resolves to `0` and all the safe-area CSS is silently dead. If notch handling "stops working", check the meta tag first.
- **Horizontal padding belongs to `.container` only.** `.header` carries `padding-top` for the notch and nothing horizontal — it wraps a `.container` that already pads. Giving `.header` its own horizontal padding double-indents the header relative to the card grid.
- **`.book-content` has exactly three possible children**: optional badge span, `h2.book-title`, `div.book-author`. The badge is omitted entirely when absent (unrated movie) rather than emitted empty, because an empty flex child still contributes a gap.
- `overflow-wrap: break-word` on `.book-title` plus `minmax(0, 1fr)` on the grid — long titles must not force horizontal scroll on narrow screens.

### Performance (do not regress)

- Covers are fetched once, in parallel, at boot, via `rel="preload" as="fetch" crossorigin`. The `crossorigin` attribute is **required** to match `fetch()`'s CORS mode — without it the browser discards the preload and fetches the file twice.
- `content-visibility: auto` + `contain-intrinsic-size` on `.book-card`. The intrinsic size must equal cover height + card padding (228px desktop / 142px mobile) or cards cause a scroll jump as they measure in. Mobile math: cover `76px × 3/2 = 114px` + `--card-pad: 14px × 2 = 28px` → `142px`.
- `scrollbar-gutter: stable` — prevents header/pill shift when the scrollbar appears/disappears between categories.
- Covers are 400px wide but render at 120px desktop / 76px mobile. Regenerating at 240px would cut total weight to ~1/3; **the user declined this on 12-10-2026. Do not resize them again without asking.**
- No Service Worker (deleted — do not re-add).
- No cover hover scale (border-color brighten only — user requested flat).
- Body has `user-select: none` — nothing is selectable by design.

## Gotchas / Caveats

- **Animanga folder mismatch** — data uses `assets/covers/anime/...` but the category is `animanga`. The single most common mistake. Only `animanga` differs from its id; `shows` matches its id and its folder, so it has no such trap.
- **Shows must never get `date_watched` or `author`.** `cards.js` treats `date_watched != null` as "this is a movie" — the entry would render with a date instead of a rating badge gap. When writing a shows entry by hand, use the key order in the Data Model section; `id, title, rating_text, cover_url, year`.
- **Title spelling** — user-typed titles are often wrong (`samarth` → `Sammarth`, `budulum` → `Kudumba`, `drishtiya` → `Drishtiya`, `djba` → `JoJo`). Web-search is the authority. Correct the title and slug silently, then mention it in one line.
- **Title collisions** — `Bastard` (Korean manhwa, Carnby Kim & Youngchan Hwang, 2014) vs `Bastard!!` (manga, Kazushi Hagiwara, 1988) are different works. Same for `Baki`, `Tokyo Ghoul`, `Dragon Ball` series entries, and `Bastard!!`-style punctuation variants. Always disambiguate by author/year.
- **Category check** — some titles are films, not manga (e.g. `Teenage Sex and Death at Camp Miasma` 2026). Web-search before choosing animanga vs movies.
- **Adaptations are separate entries** — `Verity` (Colleen Hoover novel, books id 22) and `Verity` (2026 film, movies id 62) coexist. Same for the `One of Us Is Lying` series, each volume separate.
- **Cover URLs**:
  - Always `-A "Mozilla/5.0"` — required for `encrypted-tbn0.gstatic.com`, `m.media-amazon.com`, `cdn.penguin.co.in`, `cdn.district.in`, `storyblok.com`, `preview.redd.it`, and similar.
  - Some sources serve `.webp` under a `.jpg` name (or vice versa) — `file` tells you the truth, not the extension.
  - Amazon `_V1_FMjpg_UX1000_` and `_V1_` URLs both work.
  - Google `encrypted-tbn0` are low-res thumbnails (452x678 typical) — valid, upscaled to 400px.
  - Tiny sources (238x370 Wikipedia PNGs) must still be upscaled to 400x. Verify with `identify`.
  - Strip `?utm_source=...` from wikimedia URLs.
  - `resizing.flixster.com`, `static.wikia.nocookie.net`, and WordPress `wp-content/uploads` paths all serve fine with just the UA header.
  - **Read the cover when the user's title is a guess.** Bare-URL messages and short hints produce wrong matches constantly: "Then She Was Gone" resolved to Linwood Barclay in search but the cover was Lisa Jewell's; "Better Than the Movies" and "Zanuff the Butcher" had no web footprint at all; "night watching" is one word, `Nightwatching`. Resize to ~280px, read it, then web-search to confirm the author and year.
  - **Poster art can outrank the platform name.** `Sapne vs Everyone` was described as "on Amazon MX" because the cover reads `mX presents`; it is a Prime Video original. Likewise *Raakh* (Prime Video, 2026) collides with an unrelated Marathi series of the same name (Ultra Jhakaas, 2025). Two shows can share a title — disambiguate by year and network.
- **Slugs** — kebab-cased title, special chars stripped. `'` → dropped (`Takopi's Original Sin` → `takopis-original-sin.webp`), `:` dropped (`Spine Island` → `spider-island.webp`), `!` dropped (`Bastard!!` → `bastard.webp`). Disambiguating variants get explicit suffixes: `baki-the-grappler-2001.webp`, `baki-2018.webp`, `tokyo-ghoul-re.webp`, `dragon-ball-z-kai.webp`.
- **Rating format** — always `/10`. `7/5` from the user means `7.5/10`.
- **Deploy** — `vp` (alias for `vercel --prod`, defined in `~/.zshrc` line 53). Plain `vercel --prod` only; **never** add `--scope` (user rejected it). Confirm the `▲ Aliased https://saiesh-archive.vercel.app` line and stop — do NOT curl the live URL afterward, the user tests it themselves.
  - The CLI intermittently prints the deployment as raw JSON with no `Aliased` line. That still means it deployed. Just run `vp` again and read the output rather than grepping for a line that may not be there.
- **Deploy is opt-in** — many data edits are batched and the user says `deploy` when ready. Data edits alone must not trigger a deploy.
- **Deploy means Vercel, not git.** `deploy` / `ploy` / `dep` = `vercel --prod` and nothing else. Never commit, never `git push`, never `git add` on the strength of a deploy request — pushing is a separate opt-in that needs its own words ("push to gh", "ploy to github"). Committing a deploy is not implied by it. Getting this wrong on 16-10-2026: a bare `dep` was answered with a commit and a push, which the user had to correct.
- **Do not grep `vercel` output.** It prints either the `▲ Aliased` line or a raw JSON blob with no such line, and piping it through `grep "Aliased"` discards the second form while making a successful deploy look like a failure. Run it and read the output. A first attempt can also fail with a transient `Not authorized` and succeed on an immediate retry, so check `"status"` before concluding anything went wrong.
- **The user verifies UI in a browser.** Do not spin up headless browsers or jsdom harnesses to check layout — it has no layout engine and gives false confidence. Static checks (brace balance, `node --check`, import graph, output counts against real JSON) are fine; anything requiring computed geometry is not.
- **Never `pkill -f` a pattern that appears in your own command string** — it kills your own shell. Capture `$!` at launch and `kill $PID`.
- **No comments in code** — keep it that way.
- **`.env.local`** contains a Vercel OIDC token. Gitignored; never commit or share it.
- **No favicon**, no grain overlay (both removed by request). Brand is plain "Archive" text.

### User shorthand

`taoday` = today · `ploy` = deploy · `vp` = deploy (zsh alias) · `yh` = yes · `mahwa` = manhwa · `mha` = My Hero Academia · `homoculus` = Homunculus · `drishtiya` = Drishtiya · `juujika` = Juujika no Rokunin · `redo of healer` = Redo of Healer · `djba` = JoJo's Bizarre Adventure · `7/5` = 7.5/10.

Interpret typos, but still web-search to confirm the real title.

## Commands

```bash
vp                                                                                  # Deploy to Vercel
python3 -m http.server 8000                                                        # Dev server, binds all interfaces
curl -sL -A "Mozilla/5.0" -o /tmp/opencode/cover.jpg "<url>" && \
  magick /tmp/opencode/cover.jpg -resize 400x -quality 80 assets/covers/<cat>/<slug>.webp && \
  identify assets/covers/<cat>/<slug>.webp && file /tmp/opencode/cover.jpg         # Cover download + resize
python3 -c "import json; d=json.load(open('data/<cat>.json')); assert [e['id'] for e in d]==list(range(1,len(d)+1)), 'ids not sequential'; print('OK', len(d))"   # Validate
TZ=Asia/Kolkata date +"%d-%m-%Y %H:%M %Z"                                          # IST today
```

## Deploy

`deploy` means Vercel only. It does not mean git — commits and pushes need
their own request. See the Gotchas entry for the correction this cost.

Production URL: https://saiesh-archive.vercel.app
Legacy: https://saiesh-archive.surge.sh