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
 * CSV syntax checker backed by PapaParse.
 *
 * PapaParse surfaces two distinct error channels:
 *
 *   - ``results.errors`` — array of parse errors with ``row`` (the
 *     row index where the error was detected) and ``cursor`` (the
 *     character offset within the whole input). We convert these to
 *     1-based line/column for Monaco.
 *   - ``results.meta`` — meta info, notably ``meta.fields`` which is
 *     ``null`` when the header row could not be parsed.
 *
 * Additionally, we check that every row has the same number of fields
 * as the header. PapaParse already does this internally and reports
 * "TooManyFields" / "TooFewFields" errors with the row index, which
 * is the most useful signal for the user.
 *
 * Output shape matches Monaco's ``setModelMarkers`` format.
 *
 * @param {string} text - CSV source
 * @returns {Array<object>} markers
 */

import Papa from 'papaparse'

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

/**
 * Lint CSV source. Never throws; returns an empty array on clean
 * input and a list of markers on errors.
 *
 * @param {string} text
 * @returns {Array<object>}
 */
export function lintCsv(text) {
  if (typeof text !== 'string') return []
  if (!text.trim()) {
    return [{
      severity: 'warning',
      message: 'CSV file is empty',
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: 1,
      endColumn: 2
    }]
  }
  const results = Papa.parse(text, {
    // We deliberately do NOT enable header:true — PapaParse's header
    // mode requires a header row, but the user may be editing a
    // headerless CSV. Field-count consistency is checked manually
    // below so it works in both modes.
    skipEmptyLines: false,
    dynamicTyping: false
  })

  const markers = []
  const errors = (results && results.errors) || []
  for (const err of errors) {
    // err.shape: { type, code, message, row?, index? }
    // ``row`` is 0-based row number; ``index`` is the character offset
    // in the input where the error was detected. ``row`` may be
    // undefined for quoting errors that hit EOF.
    let line = 1
    let column = 1
    if (typeof err.row === 'number') {
      line = err.row + 1
      column = 1
    }
    if (typeof err.index === 'number') {
      const pos = offsetToPosition(text, err.index)
      // Prefer the cursor position for Quoting errors (more precise);
      // for field-count errors the row start is more useful.
      if (err.code === 'UndetectableDelimiter' || err.code === 'MissingQuotes') {
        line = pos.line
        column = pos.column
      }
    }
    markers.push({
      severity: err.type === 'Delimiter' ? 'warning' : 'error',
      message: `[csv ${err.code}] ${err.message}`,
      startLineNumber: line,
      startColumn: column,
      endLineNumber: line,
      endColumn: column + 1
    })
  }

  // Manual field-count consistency check. PapaParse only reports
  // TooManyFields / TooFewFields in header mode; in non-header mode
  // (which we use to support headerless CSVs) it stays silent, so we
  // compare every row's length to the first row's.
  const rows = (results && results.data) || []
  if (Array.isArray(rows) && rows.length > 1) {
    const expected = Array.isArray(rows[0]) ? rows[0].length : 0
    if (expected > 0) {
      for (let i = 1; i < rows.length; i++) {
        const row = rows[i]
        if (!Array.isArray(row)) continue
        // Skip a trailing all-empty row (typical trailing newline)
        const isAllEmpty = row.every(cell => cell === '' || cell === null || cell === undefined)
        if (isAllEmpty && i === rows.length - 1) continue
        if (row.length !== expected) {
          markers.push({
            severity: 'error',
            message: `Row ${i + 1} has ${row.length} field(s); expected ${expected} to match row 1`,
            startLineNumber: i + 1,
            startColumn: 1,
            endLineNumber: i + 1,
            endColumn: 2
          })
        }
      }
    }
  }

  // Numeric cell check: every non-empty cell must parse as a finite
  // number. We walk the parsed rows and emit a marker per offending
  // cell. Note PapaParse returns strings; we treat a cell as numeric
  // if `Number(cell)` is finite and the trimmed string is non-empty.
  if (Array.isArray(rows)) {
    for (let r = 0; r < rows.length; r++) {
      const row = rows[r]
      if (!Array.isArray(row)) continue
      // Skip a trailing all-empty row
      const isAllEmpty = row.every(cell => cell === '' || cell === null || cell === undefined)
      if (isAllEmpty && r === rows.length - 1) continue
      for (let c = 0; c < row.length; c++) {
        const cell = row[c]
        if (typeof cell !== 'string') continue
        const trimmed = cell.trim()
        if (trimmed === '') continue  // empty cells are tolerated (sparse rows)
        const num = Number(trimmed)
        if (!Number.isFinite(num)) {
          // Find the cell in the original source to give a precise
          // column position. The source line is ``r + 1`` (1-based);
          // we scan that line for the cell text.
          const lineText = getLineText(text, r + 1)
          const colPos = findCellInLine(lineText, trimmed, c)
          markers.push({
            severity: 'error',
            message: `Cell [${r + 1}][${c + 1}] must be a number (got "${trimmed}")`,
            startLineNumber: r + 1,
            startColumn: colPos.column,
            endLineNumber: r + 1,
            endColumn: colPos.column + Math.max(1, trimmed.length)
          })
        }
      }
    }
  }

  // Sort by position so the problems panel is stable
  markers.sort((a, b) =>
    (a.startLineNumber - b.startLineNumber) ||
    (a.startColumn - b.startColumn)
  )
  return markers
}

/**
 * Extract the text of a single line from a multi-line string.
 *
 * @param {string} text
 * @param {number} lineNumber - 1-based
 * @returns {string}
 */
function getLineText(text, lineNumber) {
  const lines = text.split(/\r?\n/)
  if (lineNumber < 1 || lineNumber > lines.length) return ''
  return lines[lineNumber - 1]
}

/**
 * Locate the c-th occurrence of ``cellText`` within ``lineText``.
 * Falls back to (column=1) when the cell cannot be located.
 *
 * @param {string} lineText
 * @param {string} cellText
 * @param {number} columnIndex - 0-based cell index in the row
 * @returns {{column: number}}
 */
function findCellInLine(lineText, cellText, columnIndex) {
  if (!lineText || !cellText) return { column: 1 }
  // Walk through the line splitting by ',' to find the START column
  // of the cell at `columnIndex`. This is more reliable than
  // `indexOf` because the same cell text may repeat within a row.
  let cursor = 0
  for (let i = 0; i < columnIndex; i++) {
    const comma = lineText.indexOf(',', cursor)
    if (comma === -1) return { column: 1 }
    cursor = comma + 1
  }
  // Skip leading whitespace so the marker points at the cell content
  while (cursor < lineText.length && lineText[cursor] === ' ') {
    cursor += 1
  }
  return { column: cursor + 1 }
}
