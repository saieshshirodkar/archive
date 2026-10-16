import { CATEGORIES, CATEGORY_BY_ID } from './config.js'
import { state, entries } from './state.js'
import { saveCategory } from './storage.js'

let onSelect = null
let ui = null

export function onTabChange(handler) {
  onSelect = handler
}

function statsText() {
  const data = entries.get(state.category)
  if (!data) return state.status === 'ready' ? '0' : '\u2026'
  const cat = CATEGORY_BY_ID[state.category]
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

export function createHeader() {
  const header = document.createElement('header')
  header.className = 'header'

  const tabs = CATEGORIES.map(
    (c) => `<button type="button" role="tab" id="tab-${c.id}" aria-controls="panel" class="tab-btn" data-cat="${c.id}" tabindex="-1">${c.label}</button>`
  ).join('')

  header.innerHTML = `
    <div class="container">
      <nav class="nav">
        <span class="logo">Archive</span>
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

export function updateHeader() {
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

export function activeTab() {
  return ui?.buttons.find((b) => b.classList.contains('active'))
}

export function tabTrack() {
  return ui?.root
}

export function indicatorEl() {
  return ui?.indicator
}