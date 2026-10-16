import { activeTab, tabTrack, indicatorEl } from './header.js'

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

export function updateIndicator() {
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