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
 * Unified lint entry point for the MonacoEditor component.
 *
 * The component calls :func:`runLint` with the current language and
 * source text. This module dispatches to the appropriate language
 * linter and returns markers in the shape expected by
 * ``monaco.editor.setModelMarkers``.
 *
 * Language coverage:
 *
 *   - ``json``: handled by monaco's built-in JSON worker; this
 *     module returns an empty array and lets the worker set its own
 *     markers (with a different owner).
 *   - ``csv``:  papaparse-based checker.
 *   - ``qasm`` / ``qasm2`` / ``qasm3``: hand-written QASM checker
 *     (see ``./qasm-lint.js``).
 *
 * Any other language id yields an empty array.
 */

import { lintQasm, detectQasmVersion, QASM_VERSION } from './qasm-lint.js'
import { lintCsv } from './csv-lint.js'
import { lintJson } from './json-lint.js'

/** Marker owner used for all our custom linters. */
export const LINT_OWNER = 'qcos-lint'

/**
 * Return markers for the given source.
 *
 * @param {string} language - monaco language id ('qasm', 'csv', ...)
 * @param {string} text - source code
 * @returns {Array<object>} markers
 */
export function runLint(language, text) {
  if (typeof text !== 'string') return []
  const lang = (language || '').toLowerCase()
  switch (lang) {
    case 'qasm':
    case 'qasm2':
    case 'qasm3':
      return lintQasm(text)
    case 'csv':
      return lintCsv(text)
    case 'json':
      // We import monaco via the lean editor.api entry point which
      // does NOT register the JSON language contribution, so the
      // built-in worker is not running. Do a local JSON.parse-based
      // check instead — cheap, synchronous, and gives a useful
      // position for the most common syntax errors.
      return lintJson(text)
    default:
      return []
  }
}

/**
 * Detect the QASM major version from source text. Useful when the
 * editor language is the generic ``qasm`` and we want to display
 * which dialect the user is writing.
 *
 * @param {string} text
 * @returns {'2.0' | '3.0' | 'unknown'}
 */
export function detectQasm(text) {
  return detectQasmVersion(text || '').version
}

export { QASM_VERSION }
