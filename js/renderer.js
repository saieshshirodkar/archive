import { state } from './state.js'
import { escapeHtml } from './utils.js'
import { SKELETON_COUNT, SWITCH_MS, SWITCH_FROM } from './config.js'
import { createHeader, updateHeader } from './header.js'
import { buildSkeletonHTML, buildCardsHTML } from './cards.js'

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

export function render() {
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