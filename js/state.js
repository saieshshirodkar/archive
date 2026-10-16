import { getSavedCategory } from './storage.js'

export const entries = new Map()

export const state = {
  category: getSavedCategory(),
  items: null,
  status: 'loading'
}