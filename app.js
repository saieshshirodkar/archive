const CATEGORIES = [
  { id: 'books', label: 'Books', singular: 'Book' },
  { id: 'animanga', label: 'Animanga', singular: 'Animanga' },
  { id: 'movies', label: 'Movies', singular: 'Movie' },
  { id: 'shows', label: 'Shows', singular: 'Show' }
]

const CATEGORY_IDS = CATEGORIES.map((c) => c.id)

const CATEGORY_BY_ID = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]))

const EAGER_LOAD_COUNT = 4
const SKELETON_COUNT = 8
const SWITCH_MS = 160
const SWITCH_FROM = 0.4


const KEY = 'selectedCategory'
const IDS = new Set(CATEGORY_IDS)

function getSavedCategory() {
  try {
    const saved = localStorage.getItem(KEY)
    return IDS.has(saved) ? saved : CATEGORY_IDS[0]
  } catch {
    return CATEGORY_IDS[0]
  }
}

function saveCategory(id) {
  try {
    localStorage.setItem(KEY, id)
  } catch {}
}


const entries = new Map()

const state = {
  category: getSavedCategory(),
  items: null,
  status: 'loading'
}

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

let ui = null

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ESCAPES[c])
}

const REDUCE_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)')

function reduceMotion() {
  return REDUCE_MOTION.matches
}

function statsText() {
  const cat = CATEGORY_BY_ID[state.category]
  const data = entries.get(state.category)
  if (!data) return state.status === 'error' ? '\u2014' : state.status === 'ready' ? `0 ${cat.label}` : '\u2026'
  return `${data.length} ${data.length === 1 ? cat.singular : cat.label}`
}

function select(id) {
  if (id === state.category) return
  state.category = id
  saveCategory(id)
  loadCategory()
}

function onKeydown(e) {
  const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key]
  const atEnd = { Home: 0, End: CATEGORIES.length - 1 }[e.key]
  if (step === undefined && atEnd === undefined) return

  e.preventDefault()
  const from = CATEGORIES.findIndex((c) => c.id === state.category)
  const next = atEnd !== undefined ? atEnd : (from + step + CATEGORIES.length) % CATEGORIES.length
  select(CATEGORIES[next].id)
  ui.buttons[next].focus()
}

function createHeader() {
  const header = document.createElement('header')
  header.className = 'header'

  const tabs = CATEGORIES.map(
    (c) => `<button type="button" role="tab" id="tab-${c.id}" aria-controls="panel" class="tab-btn" data-cat="${c.id}" tabindex="-1">${c.label}</button>`
  ).join('')

  header.innerHTML = `
    <div class="container">
      <nav class="nav">
        <h1 class="logo">Archive</h1>
        <div class="tabs" role="tablist" aria-label="Category">
          <span class="tab-indicator" aria-hidden="true"></span>
          ${tabs}
        </div>
        <span class="stats" aria-live="polite"></span>
      </nav>
    </div>`

  ui = {
    root: header.querySelector('.tabs'),
    buttons: [...header.querySelectorAll('.tab-btn')],
    indicator: header.querySelector('.tab-indicator'),
    stats: header.querySelector('.stats')
  }

  ui.root.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab-btn')
    if (btn) select(btn.dataset.cat)
  })
  ui.root.addEventListener('keydown', onKeydown)

  syncHeader()
  return header
}

function syncHeader() {
  if (!ui) return
  for (const btn of ui.buttons) {
    const active = btn.dataset.cat === state.category
    btn.classList.toggle('active', active)
    btn.tabIndex = active ? 0 : -1
    btn.setAttribute('aria-selected', String(active))
  }
  ui.stats.textContent = statsText()
}

function activeTab() {
  return ui?.buttons.find((b) => b.classList.contains('active'))
}

function buildSkeletonHTML(count) {
  let html = '<p class="sr-only" role="status">Loading</p>'
  for (let i = 0; i < count; i++) {
    html +=
      '<div class="skeleton-card">' +
      '<div class="entry-bar"><div class="skeleton-text sk-index"></div><div class="skeleton-text sk-rating"></div></div>' +
      '<div class="skeleton-cover"></div>' +
      '<div class="skeleton-body">' +
      '<div class="skeleton-text sk-title"></div>' +
      '<div class="skeleton-text sk-meta"></div>' +
      '</div>' +
      '</div>'
  }
  return html
}

function tiltFor(entry) {
  const key = `${entry.id}|${entry.title}`
  let h = 2166136261
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (((Math.abs(h) % 51) - 25) / 10).toFixed(1)
}

function buildCardsHTML(items) {
  let html = ''

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    const rating = item.rating_text || ''
    const isMovie = item.date_watched != null
    const eager = i < EAGER_LOAD_COUNT

    let cls = 'book-card'
    if (rating === '10/10') cls += ' is-legendary'

    const badge = rating ? `<span class="rating-text">${escapeHtml(rating)}</span>` : ''
    const num = String(i + 1).padStart(2, '0')
    const year = item.year != null ? `<span class="movie-year">${escapeHtml(item.year)}</span>` : ''
    const meta = isMovie ? escapeHtml(item.date_watched) : item.author ? escapeHtml(item.author) : ''
    const cover = escapeHtml(item.cover_url)
    const title = escapeHtml(item.title)

    html +=
      `<article class="${cls}" style="--r:${tiltFor(item)}deg">` +
      '<div class="entry-bar">' +
      `<span class="serial"><b>${num}</b></span>` +
      badge +
      '</div>' +
      '<div class="book-cover-container">' +
      `<img class="book-cover" src="${cover}" alt="" width="${escapeHtml(item.width)}" height="${escapeHtml(item.height)}"` +
      (eager ? ' decoding="sync" fetchpriority="high"' : ' loading="lazy" decoding="async"') +
      '></div>' +
      '<div class="book-content">' +
      `<h2 class="book-title">${title}</h2>` +
      '<div class="book-author-line">' +
      `<span class="book-author">${meta}</span>` +
      year +
      '</div>' +
      '</div>' +
      '</article>'
  }

  return html
}

const app = document.getElementById('root')

let header = null
let main = null
let grid = null
let switchAnim = null
let painted = false
let toTop = null
let ticking = false

function build() {
  header = createHeader()
  app.appendChild(header)

  main = document.createElement('main')
  main.className = 'container'
  app.appendChild(main)

  grid = document.createElement('section')
  grid.className = 'book-grid'
  grid.id = 'panel'
  grid.setAttribute('role', 'tabpanel')
  grid.addEventListener(
    'error',
    (e) => {
      const img = e.target
      if (!img.classList?.contains('book-cover')) return
      img.parentElement.innerHTML = '<div class="error-placeholder">-</div>'
    },
    true
  )
  main.appendChild(grid)

  toTop = document.createElement('button')
  toTop.type = 'button'
  toTop.className = 'to-top'
  toTop.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m18 15-6-6-6 6"/></svg>'
  toTop.setAttribute('aria-label', 'Back to top')
  toTop.setAttribute('aria-hidden', 'true')
  toTop.tabIndex = -1
  toTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: reduceMotion() ? 'auto' : 'smooth' })
    activeTab()?.focus({ preventScroll: true })
  })
  app.appendChild(toTop)

  const onScroll = () => {
    const show = window.scrollY > 300
    toTop.classList.toggle('is-visible', show)
    toTop.setAttribute('aria-hidden', String(!show))
    toTop.tabIndex = show ? 0 : -1
    ticking = false
  }
  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        ticking = true
        requestAnimationFrame(onScroll)
      }
    },
    { passive: true }
  )
  onScroll()
}

function renderError() {
  const label = CATEGORY_BY_ID[state.category].label.toLowerCase()
  grid.innerHTML =
    '<div class="error-state" role="alert">' +
    `<p class="error-text">Couldn't load ${escapeHtml(label)}. The data file may be missing.</p>` +
    '<button type="button" class="retry-btn">Retry</button>' +
    '</div>'
  const btn = grid.querySelector('.retry-btn')
  btn.addEventListener('click', () => {
    entries.delete(state.category)
    state.items = null
    state.status = 'loading'
    render()
    loadCategory()
  })
  btn.focus()
}

function render() {
  if (!grid) build()
  syncHeader()
  grid.setAttribute('aria-labelledby', `tab-${state.category}`)

  if (state.status === 'error') {
    grid.setAttribute('aria-busy', 'false')
    renderError()
    return
  }

  if (state.items == null) {
    grid.setAttribute('aria-busy', 'true')
    grid.innerHTML = buildSkeletonHTML(SKELETON_COUNT)
    return
  }

  grid.setAttribute('aria-busy', 'false')
  if (state.items.length === 0) {
    const label = CATEGORY_BY_ID[state.category].label.toLowerCase()
    grid.innerHTML = `<div class="empty-state">No ${escapeHtml(label)} yet.</div>`
    return
  }

  grid.innerHTML = buildCardsHTML(state.items)

  if (!painted) {
    painted = true
    return
  }

  if (reduceMotion()) return

  switchAnim?.cancel()
  switchAnim = grid.animate([{ opacity: SWITCH_FROM }, { opacity: 1 }], {
    duration: SWITCH_MS,
    easing: 'ease-out'
  })
}

let frame = 0
let placed = false
let observer = null

function measure() {
  if (!ui) return null
  const active = activeTab()
  if (!active) return null

  const trackBox = ui.root.getBoundingClientRect()
  const activeBox = active.getBoundingClientRect()
  return {
    pill: ui.indicator,
    width: activeBox.width,
    offset: activeBox.left - trackBox.left
  }
}

function updateIndicator() {
  const m = measure()
  if (!m) return

  if (!observer && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => updateIndicator())
    observer.observe(ui.root)
  }

  if (!placed) {
    placed = true
    m.pill.style.transition = 'none'
    m.pill.style.width = `${m.width}px`
    m.pill.style.transform = `translateX(${m.offset}px)`
    void m.pill.offsetWidth
    m.pill.style.transition = ''
    return
  }

  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    m.pill.style.width = `${m.width}px`
    m.pill.style.transform = `translateX(${m.offset}px)`
  })
}

window.addEventListener('resize', () => updateIndicator(), { passive: true })
window.addEventListener('orientationchange', () => setTimeout(updateIndicator, 100), { passive: true })
document.fonts?.ready.then(() => updateIndicator())





let token = 0
const pending = new Map()

function load(id, priority = 'high') {
  const ready = entries.get(id)
  if (ready) return Promise.resolve(ready)

  let p = pending.get(id)
  if (!p) {
    p = fetch(`data/${id}.json`, { priority })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        entries.set(id, data)
        pending.delete(id)
        syncHeader()
        return data
      })
      .catch((err) => {
        pending.delete(id)
        throw err
      })
    pending.set(id, p)
  }
  return p
}

function commit(status) {
  state.status = status
  render()
  window.scrollTo(0, 0)
  updateIndicator()
}

async function loadCategory() {
  const mine = ++token

  const ready = entries.get(state.category)
  if (ready) {
    state.items = ready
    commit('ready')
    return
  }

  state.items = null
  state.status = 'loading'
  render()
  updateIndicator()

  try {
    const data = await load(state.category)
    if (mine !== token) return
    state.items = data
    commit('ready')
  } catch {
    if (mine !== token) return
    commit('error')
  }
}

function preloadCategory(id) {
  load(id, 'low').catch(() => {})
}

if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

render()
updateIndicator()
loadCategory()

const idle = window.requestIdleCallback ? (fn) => window.requestIdleCallback(fn, { timeout: 2000 }) : (fn) => setTimeout(fn, 1500)
idle(() => {
  for (const id of CATEGORY_IDS) {
    if (id !== state.category) preloadCategory(id)
  }
})
