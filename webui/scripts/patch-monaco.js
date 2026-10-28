/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

/**
 * Post-install patch: replace Monaco's built-in findSectionHeaders.js with our
 * Edge-compatible version (no RegExp 'd' flag).
 *
 * Why this is needed:
 *   - Monaco 0.52.x ships findSectionHeaders.js with `new RegExp(..., 'd')`
 *     which is not supported by older Microsoft Edge versions and causes a
 *     SyntaxError at runtime when the editor's folding feature initialises.
 *   - The file is imported via a *relative* path inside editorSimpleWorker.js
 *     (`import { findSectionHeaders } from './findSectionHeaders.js'`), so
 *     Vite's resolve.alias cannot intercept it. We must overwrite the file
 *     on disk after `npm install`.
 *
 * Idempotent: safe to run multiple times; the source patch file is treated
 * as the single source of truth.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const SRC = path.resolve(__dirname, '../patches/findSectionHeaders.js')
const DEST = path.resolve(
  __dirname,
  '../node_modules/monaco-editor/esm/vs/editor/common/services/findSectionHeaders.js'
)

function main() {
  if (!fs.existsSync(SRC)) {
    console.error(`[patch-monaco] source patch not found: ${SRC}`)
    process.exit(1)
  }
  if (!fs.existsSync(DEST)) {
    // Monaco not installed yet (e.g. --no-optional or production install that
    // pruned it). Don't fail the whole install; just skip the patch.
    console.warn(`[patch-monaco] target file not found, skipping: ${DEST}`)
    return
  }
  const src = fs.readFileSync(SRC, 'utf-8')
  const dst = fs.readFileSync(DEST, 'utf-8')
  if (src === dst) {
    console.log('[patch-monaco] already up to date')
    return
  }
  fs.writeFileSync(DEST, src, 'utf-8')
  console.log(`[patch-monaco] patched: ${DEST}`)
}

main()
