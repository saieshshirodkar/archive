export const CATEGORIES = [
  { id: 'books', label: 'Books', singular: 'Book' },
  { id: 'animanga', label: 'Animanga', singular: 'Animanga' },
  { id: 'movies', label: 'Movies', singular: 'Movie' },
  { id: 'shows', label: 'Shows', singular: 'Show' }
]

export const CATEGORY_IDS = CATEGORIES.map((c) => c.id)

export const CATEGORY_BY_ID = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]))

export const EAGER_LOAD_COUNT = 8
export const SKELETON_COUNT = 5
export const SWITCH_MS = 160
export const SWITCH_FROM = 0.4