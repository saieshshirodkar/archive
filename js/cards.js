import { escapeHtml } from './utils.js'
import { EAGER_LOAD_COUNT } from './config.js'

export function buildSkeletonHTML(count) {
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

export function buildCardsHTML(items) {
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