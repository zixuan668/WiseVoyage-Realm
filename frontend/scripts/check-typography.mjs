import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const extensions = new Set(['.vue', '.scss', '.css', '.ts', '.js'])
const violations = []
let checked = 0

async function checkFile(file) {
  const minimum = { px: 18, rpx: 32, rem: 1, em: 1 }
  checked++
  const source = await readFile(file, 'utf8')
  const declarations = /(?:font-size(?:-[a-z-]+)?|--tab-label-size|(?<![\w-])font)\s*:\s*[^;{}\n]+/g
  for (const declaration of source.matchAll(declarations)) {
    const value = declaration[0]
    // clamp() sets an explicit lower bound; its viewport-dependent middle term
    // is not a fixed font size. Check the first argument only.
    const inspected = value.includes('clamp(') ? value.split(',')[0] : value
    for (const size of inspected.matchAll(/(?<![\w.])(\d*\.?\d+)(px|rpx|rem|em)\b/g)) {
      if (Number(size[1]) > 0 && Number(size[1]) < minimum[size[2]]) {
        report(file, source, declaration.index, value)
      }
    }
  }
  for (const size of source.matchAll(/fontSize\s*:\s*(\d+(?:\.\d+)?)(?![\w.])/g)) {
    if (Number(size[1]) > 0 && Number(size[1]) < minimum.px) report(file, source, size.index, size[0])
  }
}

function report(file, source, index, value) {
  const line = source.slice(0, index).split('\n').length
  violations.push(`${path.relative(project, file)}:${line}: ${value.trim()}`)
}

async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (['tests', '__tests__', 'node_modules', 'static', 'dist', 'unpackage'].includes(entry.name)) continue
    const file = path.join(directory, entry.name)
    if (entry.isDirectory()) await walk(file)
    else if (extensions.has(path.extname(file))) await checkFile(file)
  }
}

// The App retains its original per-component sizes. The large-text rule is Web-only.
for (const directory of ['frontend/src']) {
  await walk(path.join(project, directory))
}
if (violations.length) {
  console.error('Web text must be at least 18px:\n' + violations.join('\n'))
  process.exitCode = 1
} else console.log(`Typography check passed (${checked} source files).`)
