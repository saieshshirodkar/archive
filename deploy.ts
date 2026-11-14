import { cp, mkdir, rm } from 'node:fs/promises'
import { spawn } from 'node:child_process'

const ROOT = import.meta.dir
const DIST = `${ROOT}/dist`
const FILES = ['index.html', 'app.css', 'app.js', 'favicon.svg']
const DIRS = ['data', 'assets']

await rm(DIST, { recursive: true, force: true })
await mkdir(DIST, { recursive: true })

for (const file of FILES) {
  await cp(`${ROOT}/${file}`, `${DIST}/${file}`)
}
for (const dir of DIRS) {
  await cp(`${ROOT}/${dir}`, `${DIST}/${dir}`, { recursive: true })
}
await cp(`${ROOT}/_headers`, `${DIST}/_headers`)

const args = process.argv.slice(2)
const child = spawn('cf', ['deploy', ...args], { stdio: 'inherit', cwd: ROOT })

child.on('exit', (code) => process.exit(code ?? 1))
