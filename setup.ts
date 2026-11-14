import { access, mkdir, rm, symlink } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join } from 'node:path'

const GLOBAL = join(homedir(), '.bun/install/global/node_modules')
const ROOT = import.meta.dir
const PACKAGES = ['cf', 'wrangler']
const BINS: Record<string, string> = {
  cf: 'cf/bin/cf',
  wrangler: 'wrangler/bin/wrangler.js',
}

try {
  await access(GLOBAL)
} catch {
  console.error(`missing ${GLOBAL}\nrun: bun add -g cf wrangler`)
  process.exit(1)
}

await rm(`${ROOT}/node_modules`, { recursive: true, force: true })
await mkdir(`${ROOT}/node_modules/.bin`, { recursive: true })

for (const pkg of PACKAGES) {
  await symlink(join(GLOBAL, pkg), `${ROOT}/node_modules/${pkg}`)
}
for (const [name, rel] of Object.entries(BINS)) {
  const target = join(GLOBAL, rel)
  try {
    await access(target)
  } catch {
    console.error(`missing ${target}\nrun: bun add -g cf wrangler`)
    process.exit(1)
  }
  await symlink(target, `${ROOT}/node_modules/.bin/${name}`)
}

console.log('linked cf + wrangler from the global bun install')
