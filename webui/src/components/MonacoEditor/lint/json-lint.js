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
 * JSON syntax checker using the built-in ``JSON.parse``.
 *
 * Why not delegate to monaco's built-in JSON language service?
 * Because we import ``monaco-editor/esm/vs/editor/editor.api`` (the
 * lean entry point) to keep the bundle size down, and that entry
 * does NOT register the JSON language contribution. Pulling it in
 * would force a worker download on first use, which is overkill for
 * a simple "is this valid JSON?" check.
 *
 * ``JSON.parse`` throws a ``SyntaxError`` whose ``message`` often
 * contains a character offset (in V8 / Chromium). Firefox's message
 * format is different but still contains a position hint. We extract
 * what we can; when no position is available, we highlight the
 * first line as a fallback so the user always sees *something*.
 *
 * Output shape matches Monaco's ``setModelMarkers`` format.
 *
 * @param {string} text - JSON source
 * @returns {Array<object>} markers
 */
export function lintJson(text) {
  if (typeof text !== 'string') return []
  if (!text.trim()) {
    return [{
      severity: 'warning',
      message: 'JSON file is empty',
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: 1,
      endColumn: 2
    }]
  }
  let parsed
  try {
    parsed = JSON.parse(text)
  } catch (e) {
    const marker = {
      severity: 'error',
      message: e.message || 'Invalid JSON',
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: 1,
      endColumn: 2
    }
    // V8 / Chromium message: "... at position 123" or
    // "... at line 4 column 5 of the JSON data"
    const posMatch = /position\s+(\d+)/.exec(e.message)
    if (posMatch) {
      const offset = parseInt(posMatch[1], 10)
      const { line, column } = offsetToPosition(text, offset)
      marker.startLineNumber = line
      marker.startColumn = column
      marker.endLineNumber = line
      marker.endColumn = column + 1
      return [marker]
    }
    const lineColMatch = /line\s+(\d+)\s+column\s+(\d+)/.exec(e.message)
    if (lineColMatch) {
      marker.startLineNumber = parseInt(lineColMatch[1], 10)
      marker.startColumn = parseInt(lineColMatch[2], 10) + 1
      marker.endLineNumber = marker.startLineNumber
      marker.endColumn = marker.startColumn + 1
      return [marker]
    }
    // Fallback: highlight the first non-whitespace character so the
    // user always sees a marker somewhere.
    const m = /\S/.exec(text)
    if (m) {
      const { line, column } = offsetToPosition(text, m.index)
      marker.startLineNumber = line
      marker.startColumn = column
      marker.endLineNumber = line
      marker.endColumn = column + 1
    }
    return [marker]
  }

  // ---- Semantic check: numeric matrix --------------------------
  // The qubo workflow expects JSON to be a 2-D array of numbers
  // (a square QUBO matrix). Walk the parsed value and flag any
  // non-numeric leaf. We deliberately do NOT recurse into nested
  // objects — QUBO matrices are arrays of arrays of numbers.
  return findNonNumericLeaves(parsed, text)
}

/**
 * Walk the parsed JSON value, expecting arrays of arrays of numbers.
 * Returns a list of markers for any leaf that is not a finite number.
 *
 * Position resolution strategy: for each non-numeric leaf we compute
 * a *fuzzy* position by re-serializing the leaf to JSON and locating
 * its first occurrence in the source. This is approximate (the same
 * value may appear multiple times) but is good enough for the
 * common case where each cell value is unique. For ambiguous values
 * (e.g. the same string "abc" repeated), all occurrences would be
 * equally valid candidates, so we just point at the first one.
 *
 * @param {*} value - the parsed JSON value
 * @param {string} text - the original source text
 * @returns {Array<object>} markers
 */
function findNonNumericLeaves(value, text) {
  const markers = []
  // The top-level shape must be an array of arrays of numbers.
  // Anything else (object, scalar, array of objects, ...) is an error.
  if (!Array.isArray(value)) {
    markers.push({
      severity: 'error',
      message: `Top-level JSON value must be a 2-D array of numbers (got ${describeType(value)})`,
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: 1,
      endColumn: 2
    })
    return markers
  }
  value.forEach((row, rowIdx) => {
    if (!Array.isArray(row)) {
      const pos = findValuePosition(text, row, rowIdx)
      markers.push({
        severity: 'error',
        message: `Row ${rowIdx + 1} must be an array of numbers (got ${describeType(row)})`,
        startLineNumber: pos.line,
        startColumn: pos.column,
        endLineNumber: pos.line,
        endColumn: pos.column + 1
      })
      return
    }
    row.forEach((cell, colIdx) => {
      if (typeof cell !== 'number' || !Number.isFinite(cell)) {
        const pos = findValuePosition(text, cell, rowIdx, colIdx)
        markers.push({
          severity: 'error',
          message: `Cell [${rowIdx + 1}][${colIdx + 1}] must be a finite number (got ${describeType(cell)}: ${JSON.stringify(cell)})`,
          startLineNumber: pos.line,
          startColumn: pos.column,
          endLineNumber: pos.line,
          endColumn: pos.column + Math.max(1, String(JSON.stringify(cell)).length)
        })
      }
    })
  })
  return markers
}

/**
 * Locate a value in the original JSON source. We serialize the
 * value with JSON.stringify and look it up. This is heuristic but
 * works well for unique leaf values.
 *
 * @param {string} text - source
 * @param {*} value - the value to find
 * @param {number} [hintRow] - 0-based row index for context (unused)
 * @param {number} [hintCol] - 0-based column index for context (unused)
 * @returns {{line: number, column: number}}
 */
function findValuePosition(text, value, hintRow, hintCol) {
  const needle = JSON.stringify(value)
  if (typeof needle === 'string' && needle.length > 0) {
    const idx = text.indexOf(needle)
    if (idx >= 0) {
      return offsetToPosition(text, idx)
    }
  }
  return { line: 1, column: 1 }
}

/**
 * Human-readable type name for error messages.
 */
function describeType(v) {
  if (v === null) return 'null'
  if (Array.isArray(v)) return 'array'
  return typeof v
}

/**
 * Compute the 1-based (line, column) for a 0-based character offset
 * into a text buffer.
 *
 * @param {string} text
 * @param {number} offset - 0-based character offset
 * @returns {{line: number, column: number}}
 */
function offsetToPosition(text, offset) {
  if (offset <= 0) return { line: 1, column: 1 }
  let line = 1
  let column = 1
  for (let i = 0; i < offset && i < text.length; i++) {
    if (text[i] === '\n') {
      line += 1
      column = 1
    } else {
      column += 1
    }
  }
  return { line, column }
}
