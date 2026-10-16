import { entries, state } from './state.js'
import { render } from './renderer.js'
import { updateHeader } from './header.js'
import { updateIndicator } from './indicator.js'

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

export async function loadCategory() {
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
  if (mine !== token) return

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

export function preloadCategory(id) {
  load(id).catch(() => {})
}