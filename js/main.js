import { render } from './renderer.js'
import { updateIndicator } from './indicator.js'
import { loadCategory, preloadCategory } from './data.js'
import { onTabChange } from './header.js'
import { CATEGORY_IDS } from './config.js'

if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

onTabChange(loadCategory)
render()
updateIndicator()
loadCategory()

for (const id of CATEGORY_IDS) preloadCategory(id)