import { CATEGORY_IDS } from './config.js'

const KEY = 'selectedCategory'
const IDS = new Set(CATEGORY_IDS)

export function getSavedCategory() {
  try {
    const saved = localStorage.getItem(KEY)
    return IDS.has(saved) ? saved : CATEGORY_IDS[0]
  } catch {
    return CATEGORY_IDS[0]
  }
}

export function saveCategory(id) {
  try {
    localStorage.setItem(KEY, id)
  } catch {}
}