const CATEGORIES = [
  { id: 'books', label: 'Books', singular: 'Book' },
  { id: 'animanga', label: 'Animanga', singular: 'Animanga' },
  { id: 'movies', label: 'Movies', singular: 'Movie' },
  { id: 'shows', label: 'Shows', singular: 'Show' }
]

const CATEGORY_IDS = CATEGORIES.map((c) => c.id)

const CATEGORY_BY_ID = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]))

const EAGER_LOAD_COUNT = 8
const SKELETON_COUNT = 5
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

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ESCAPES[c])
}




let onSelect = null
let ui = null

function onTabChange(handler) {
  onSelect = handler
}

function statsText() {
  const cat = CATEGORY_BY_ID[state.category]
  const data = entries.get(state.category)
  if (!data) return state.status === 'ready' ? `0 ${cat.label}` : '\u2026'
  return `${data.length} ${data.length === 1 ? cat.singular : cat.label}`
}

function select(id) {
  if (id === state.category) return
  state.category = id
  saveCategory(id)
  if (onSelect) onSelect(id)
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

function updateHeader() {
  syncHeader()
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

function tabTrack() {
  return ui?.root
}

function indicatorEl() {
  return ui?.indicator
}



function buildSkeletonHTML(count) {
  let html = ''
  for (let i = 0; i < count; i++) {
    html +=
      '<div class="skeleton-card">' +
      '<div class="skeleton-text" style="width:16px;height:12px"></div>' +
      '<div class="skeleton-cover"></div>' +
      '<div class="skeleton-body">' +
      '<div class="skeleton-text" style="width:48px;height:18px"></div>' +
      '<div class="skeleton-text" style="width:75%;height:22px"></div>' +
      '<div class="skeleton-text" style="width:40%;height:14px"></div>' +
      '</div>' +
      '</div>'
  }
  return html
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
    else if (!rating && !isMovie) cls += ' is-tbr'

    let badge = ''
    if (rating) badge = `<span class="rating-text">${escapeHtml(rating)}</span>`
    else if (!isMovie) badge = '<span class="rating-text tbr">TBR</span>'

    const year = item.year != null ? `<span class="movie-year">(${item.year})</span>` : ''
    const meta = isMovie ? escapeHtml(item.date_watched) : item.author ? `by ${escapeHtml(item.author)}` : ''
    const cover = escapeHtml(item.cover_url)
    const title = escapeHtml(item.title)

    html +=
      `<article class="${cls}">` +
      `<div class="book-index">${String(i + 1).padStart(2, '0')}</div>` +
      '<div class="book-cover-container">' +
      `<img class="book-cover" src="${cover}" alt="${title}"` +
      (eager ? ' decoding="sync" fetchpriority="high"' : ' loading="lazy" decoding="async"') +
      '></div>' +
      '<div class="book-content">' +
      badge +
      `<h2 class="book-title">${title}${year}</h2>` +
      `<div class="book-author">${meta}</div>` +
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
      img.parentElement.innerHTML = '<div class="error-placeholder">\u2014</div>'
    },
    true
  )
  main.appendChild(grid)
}

function render() {
  if (!grid) build()
  updateHeader()
  grid.setAttribute('aria-labelledby', `tab-${state.category}`)

  if (state.status === 'error') {
    grid.innerHTML = `<div class="loading-state">Failed to load ${escapeHtml(state.category)}.</div>`
    return
  }

  if (state.items == null) {
    grid.innerHTML = buildSkeletonHTML(SKELETON_COUNT)
    return
  }

  grid.innerHTML = buildCardsHTML(state.items)

  if (!painted) {
    painted = true
    return
  }

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
  const track = tabTrack()
  const pill = indicatorEl()
  const active = activeTab()
  if (!track || !pill || !active) return null

  const trackBox = track.getBoundingClientRect()
  const activeBox = active.getBoundingClientRect()
  return {
    pill,
    width: activeBox.width,
    offset: activeBox.left - trackBox.left
  }
}

function updateIndicator() {
  const m = measure()
  if (!m) return

  if (!observer && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => updateIndicator())
    observer.observe(tabTrack())
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

function load(id) {
  const ready = entries.get(id)
  if (ready) return Promise.resolve(ready)

  let p = pending.get(id)
  if (!p) {
    p = fetch(`data/${id}.json`, { priority: 'high' })
      .then((res) => res.json())
      .then((data) => {
        entries.set(id, data)
        pending.delete(id)
        updateHeader()
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
  load(id).catch(() => {})
}






if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

onTabChange(loadCategory)
render()
updateIndicator()
loadCategory()

for (const id of CATEGORY_IDS) preloadCategory(id)
