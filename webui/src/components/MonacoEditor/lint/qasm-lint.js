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
 * Lightweight syntax checker for OpenQASM 2.0 and 3.0.
 *
 * This is NOT a full parser — the goal is fast, local feedback in the
 * editor, not bit-perfect spec compliance. It catches the common
 * mistakes a user actually makes while editing:
 *
 *   - Missing / malformed ``OPENQASM <version>;`` header
 *   - Unbalanced ``()`` / ``[]`` / ``{}``
 *   - Unterminated string literals and block comments
 *   - Statements that are missing a trailing ``;``
 *   - ``qreg`` / ``creg`` declarations without a size
 *   - Unknown top-level keywords
 *   - Version-specific keyword misuse (e.g. ``qubit`` in 2.0,
 *     ``qreg`` in 3.0 is allowed but flagged as legacy)
 *
 * The checker is purely line-oriented with a tiny character-level
 * scanner for strings / comments / brackets, so it stays under ~300
 * lines and runs in O(N) over the source.
 *
 * Output shape matches what Monaco's ``setModelMarkers`` expects:
 *
 *   {
 *     severity: 'error' | 'warning',
 *     message: string,
 *     startLineNumber: number, // 1-based
 *     startColumn: number,     // 1-based
 *     endLineNumber: number,
 *     endColumn: number
 *   }
 */

/** Versions recognized by the checker. */
export const QASM_VERSION = {
  V2: '2.0',
  V3: '3.0',
  UNKNOWN: 'unknown'
}

/** Keywords valid in OpenQASM 2.0 only. */
const V2_ONLY_KEYWORDS = new Set(['qreg', 'creg', 'opaque'])

/** Keywords valid in OpenQASM 3.0 only (commonly misused in 2.0). */
const V3_ONLY_KEYWORDS = new Set([
  'qubit', 'bit', 'int', 'uint', 'float', 'bool', 'complex', 'angle',
  'array', 'let', 'def', 'defcal', 'defcalgrammar', 'cal', 'extern',
  'box', 'switch', 'case', 'default', 'while', 'for', 'in', 'return',
  'break', 'continue', 'pragma', 'input', 'output', 'const', 'sizeof',
  'delay', 'stretch', 'durationof', 'gphase'
])

/** Top-level keywords valid in BOTH versions (no arg checking here). */
const COMMON_KEYWORDS = new Set([
  'OPENQASM', 'include', 'gate', 'measure', 'reset', 'if', 'barrier'
])

/**
 * Detect the OpenQASM version declared by the source.
 *
 * The header line is ``OPENQASM <major>.<minor>;``. We accept any
 * ``2.x`` as 2.0 and any ``3.x`` as 3.0 (minor versions don't change
 * the keyword set we check).
 *
 * @param {string} text - source code
 * @returns {{version: string, headerLine: number, headerError: object|null}}
 */
export function detectQasmVersion(text) {
  const lines = text.split(/\r?\n/)
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]
    const trimmed = raw.trim()
    // Skip blank lines and comments at the top of the file
    if (!trimmed || trimmed.startsWith('//')) continue
    // First non-trivial line must be the OPENQASM header
    const m = trimmed.match(/^OPENQASM\s+(\d+)\.(\d+)\s*;?\s*$/i)
    if (m) {
      const major = parseInt(m[1], 10)
      const line = i + 1
      if (!/;$/.test(trimmed)) {
        return {
          version: major === 2 ? QASM_VERSION.V2 : major === 3 ? QASM_VERSION.V3 : QASM_VERSION.UNKNOWN,
          headerLine: line,
          headerError: {
            severity: 'error',
            message: 'OPENQASM header must end with ";"',
            startLineNumber: line,
            startColumn: raw.length,
            endLineNumber: line,
            endColumn: raw.length + 1
          }
        }
      }
      return {
        version: major === 2 ? QASM_VERSION.V2 : major === 3 ? QASM_VERSION.V3 : QASM_VERSION.UNKNOWN,
        headerLine: line,
        headerError: null
      }
    }
    // First non-comment line is NOT a header — report and bail out
    const line = i + 1
    return {
      version: QASM_VERSION.UNKNOWN,
      headerLine: line,
      headerError: {
        severity: 'error',
        message: `Expected "OPENQASM 2.0;" or "OPENQASM 3.0;" header, got: ${trimmed.slice(0, 40)}`,
        startLineNumber: line,
        startColumn: Math.max(1, raw.indexOf(trimmed) + 1),
        endLineNumber: line,
        endColumn: raw.length + 1
      }
    }
  }
  return {
    version: QASM_VERSION.UNKNOWN,
    headerLine: 1,
    headerError: {
      severity: 'error',
      message: 'File is empty; expected "OPENQASM 2.0;" or "OPENQASM 3.0;" header',
      startLineNumber: 1,
      startColumn: 1,
      endLineNumber: 1,
      endColumn: 2
    }
  }
}

/**
 * Scan the source for unbalanced brackets / unterminated strings and
 * comments. Returns a list of markers; the position reported is the
 * OPEN bracket (so the user can jump straight to the unclosed one).
 *
 * @param {string} text
 * @returns {Array<object>}
 */
function scanBalance(text) {
  const markers = []
  const stack = []
  const lines = text.split(/\r?\n/)
  let inBlockComment = false
  let blockCommentStart = null
  let inString = false
  let stringStart = null
  let stringQuote = null

  const OPEN = { '(': ')', '[': ']', '{': '}' }
  const CLOSE = new Set([')', ']', '}'])

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx]
    let i = 0
    while (i < line.length) {
      const ch = line[i]
      const next = i + 1 < line.length ? line[i + 1] : ''

      if (inBlockComment) {
        if (ch === '*' && next === '/') {
          inBlockComment = false
          blockCommentStart = null
          i += 2
          continue
        }
        i++
        continue
      }
      if (inString) {
        if (ch === '\\') {
          i += 2
          continue
        }
        if (ch === stringQuote) {
          inString = false
          stringStart = null
          stringQuote = null
        }
        i++
        continue
      }

      // Line comment swallows the rest of the line
      if (ch === '/' && next === '/') break
      if (ch === '/' && next === '*') {
        inBlockComment = true
        blockCommentStart = { line: lineIdx + 1, col: i + 1 }
        i += 2
        continue
      }
      if (ch === '"' || ch === '\'') {
        inString = true
        stringQuote = ch
        stringStart = { line: lineIdx + 1, col: i + 1 }
        i++
        continue
      }
      if (OPEN[ch]) {
        stack.push({ ch, line: lineIdx + 1, col: i + 1 })
        i++
        continue
      }
      if (CLOSE.has(ch)) {
        const top = stack[stack.length - 1]
        if (!top || OPEN[top.ch] !== ch) {
          markers.push({
            severity: 'error',
            message: `Unmatched closing "${ch}"`,
            startLineNumber: lineIdx + 1,
            startColumn: i + 1,
            endLineNumber: lineIdx + 1,
            endColumn: i + 2
          })
        } else {
          stack.pop()
        }
        i++
        continue
      }
      i++
    }
    // Newline implicitly closes a string (QASM does not allow multi-line strings)
    if (inString) {
      markers.push({
        severity: 'error',
        message: `Unterminated string literal (opened with ${stringQuote})`,
        startLineNumber: stringStart.line,
        startColumn: stringStart.col,
        endLineNumber: stringStart.line,
        endColumn: stringStart.col + 1
      })
      inString = false
      stringStart = null
      stringQuote = null
    }
  }
  if (inBlockComment && blockCommentStart) {
    markers.push({
      severity: 'error',
      message: 'Unterminated block comment',
      startLineNumber: blockCommentStart.line,
      startColumn: blockCommentStart.col,
      endLineNumber: blockCommentStart.line,
      endColumn: blockCommentStart.col + 2
    })
  }
  // Any still-open bracket is reported at its OPEN position
  for (const open of stack) {
    markers.push({
      severity: 'error',
      message: `Unclosed "${open.ch}"`,
      startLineNumber: open.line,
      startColumn: open.col,
      endLineNumber: open.line,
      endColumn: open.col + 1
    })
  }
  return markers
}

/**
 * Line-oriented statement checks: missing trailing ';', keyword misuse
 * per version, qreg/creg without a size.
 *
 * @param {string} text
 * @param {string} version - one of QASM_VERSION
 * @param {number} headerLine - 1-based line number of the OPENQASM header
 * @returns {Array<object>}
 */
function scanStatements(text, version, headerLine) {
  const markers = []
  const lines = text.split(/\r?\n/)
  // Track whether we're inside a multi-line gate/def block ({}); such
  // blocks exempt their contents from the trailing-semicolon rule.
  let braceDepth = 0
  let inBlockComment = false

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const lineNo = i + 1

    // Skip block comments when looking for code
    let code = ''
    let j = 0
    while (j < line.length) {
      const ch = line[j]
      const next = j + 1 < line.length ? line[j + 1] : ''
      if (inBlockComment) {
        if (ch === '*' && next === '/') {
          inBlockComment = false
          j += 2
          continue
        }
        j++
        continue
      }
      if (ch === '/' && next === '*') {
        inBlockComment = true
        j += 2
        continue
      }
      if (ch === '/' && next === '/') break
      code += ch
      j++
    }
    const trimmed = code.trim()
    // Skip blank / pure-comment / preprocessor-style lines
    if (!trimmed) continue
    if (lineNo === headerLine) continue

    // Track brace depth so we know whether we're inside a block
    const opens = (trimmed.match(/\{/g) || []).length
    const closes = (trimmed.match(/\}/g) || []).length
    const prevBraceDepth = braceDepth
    braceDepth += opens - closes

    // Lines that legitimately do not end with ';':
    //   - pure "{" or "}" lines
    //   - gate/def/cal/defcal declarations that OPEN a block
    //   - control-flow headers (if/for/while/switch) followed by "("
    //   - lines that are themselves only a closing "}" or "};"
    const opensBlock = /\{\s*$/.test(trimmed)
    const closesBlockOnly = /^\}\s*;?\s*$/.test(trimmed)
    const isControlHeader = /^(if|for|while|switch)\s*\(/.test(trimmed) && opensBlock
    const isBlockHeader = /^(gate|opaque|def|defcal|cal)\b/.test(trimmed) && opensBlock

    // qreg / creg without size: "qreg q;" or "qreg q" (no [N])
    const qregMatch = trimmed.match(/^(qreg|qbit|qubit|creg|bit)\s+([A-Za-z_]\w*)\s*;?\s*$/)
    if (qregMatch) {
      const kw = qregMatch[1]
      if (kw === 'qreg' || kw === 'creg') {
        markers.push({
          severity: 'error',
          message: `${kw} declaration must specify a size, e.g. "${kw} ${qregMatch[2]}[4];"`,
          startLineNumber: lineNo,
          startColumn: Math.max(1, line.indexOf(kw) + 1),
          endLineNumber: lineNo,
          endColumn: line.length + 1
        })
      } else if (kw === 'qubit' || kw === 'bit') {
        // QASM3 "qubit q;" is actually OK (single qubit), but we hint
        // at the more explicit form. Lower severity: warning.
        markers.push({
          severity: 'warning',
          message: `Consider "${kw} ${qregMatch[2]}[1];" or "${kw}[1] ${qregMatch[2]};" for clarity`,
          startLineNumber: lineNo,
          startColumn: Math.max(1, line.indexOf(kw) + 1),
          endLineNumber: lineNo,
          endColumn: line.length + 1
        })
      }
      continue
    }

    // Version-specific keyword misuse
    const kwMatch = trimmed.match(/^([A-Za-z_]\w*)\b/)
    if (kwMatch) {
      const kw = kwMatch[1]
      if (version === QASM_VERSION.V2 && V3_ONLY_KEYWORDS.has(kw)) {
        markers.push({
          severity: 'error',
          message: `"${kw}" is OpenQASM 3.0 only; the file header declares 2.0`,
          startLineNumber: lineNo,
          startColumn: Math.max(1, line.indexOf(kw) + 1),
          endLineNumber: lineNo,
          endColumn: Math.max(1, line.indexOf(kw) + 1) + kw.length
        })
        continue
      }
      if (version === QASM_VERSION.V3 && V2_ONLY_KEYWORDS.has(kw)) {
        markers.push({
          severity: 'warning',
          message: `"${kw}" is legacy OpenQASM 2.0 syntax; in 3.0 prefer "${kw === 'qreg' ? 'qubit[N] name' : kw === 'creg' ? 'bit[N] name' : 'extern'}"`,
          startLineNumber: lineNo,
          startColumn: Math.max(1, line.indexOf(kw) + 1),
          endLineNumber: lineNo,
          endColumn: Math.max(1, line.indexOf(kw) + 1) + kw.length
        })
      }
      // Unknown top-level keyword (only flag at depth 0 to avoid
      // false positives inside gate bodies / def bodies).
      if (
        prevBraceDepth === 0 &&
        !COMMON_KEYWORDS.has(kw) &&
        !V2_ONLY_KEYWORDS.has(kw) &&
        !V3_ONLY_KEYWORDS.has(kw) &&
        !/^[a-z_]\w*\s*(\([^)]*\))?\s+\w+/.test(trimmed) // gate-call form
      ) {
        markers.push({
          severity: 'warning',
          message: `Unrecognized top-level keyword "${kw}"`,
          startLineNumber: lineNo,
          startColumn: Math.max(1, line.indexOf(kw) + 1),
          endLineNumber: lineNo,
          endColumn: Math.max(1, line.indexOf(kw) + 1) + kw.length
        })
      }
    }

    // Trailing-semicolon check (only when we're not inside a block)
    if (
      prevBraceDepth === 0 &&
      !opensBlock &&
      !closesBlockOnly &&
      !isControlHeader &&
      !isBlockHeader &&
      !/;\s*$/.test(trimmed)
    ) {
      markers.push({
        severity: 'error',
        message: 'Statement is missing a trailing ";"',
        startLineNumber: lineNo,
        startColumn: line.length,
        endLineNumber: lineNo,
        endColumn: line.length + 1
      })
    }
  }
  return markers
}

/**
 * Run the full QASM lint pass.
 *
 * @param {string} text - source code
 * @returns {Array<object>} markers suitable for setModelMarkers
 */
export function lintQasm(text) {
  if (typeof text !== 'string') return []
  const { version, headerLine, headerError } = detectQasmVersion(text)
  const markers = []
  if (headerError) markers.push(headerError)
  // If we couldn't even find a header, the rest of the file is
  // probably garbage; still run the balance check because unterminated
  // strings/comments are useful signals.
  markers.push(...scanBalance(text))
  if (version !== QASM_VERSION.UNKNOWN && !headerError) {
    markers.push(...scanStatements(text, version, headerLine))
  }
  // Sort by position so the problems panel is stable
  markers.sort((a, b) =>
    (a.startLineNumber - b.startLineNumber) ||
    (a.startColumn - b.startColumn)
  )
  return markers
}
