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
 * Register OpenQASM language (syntax highlighting) with Monaco Editor.
 * Supports both OpenQASM 2.0 and 3.0 keywords.
 *
 * @param {typeof import('monaco-editor')} monaco - The monaco editor instance
 */
export function registerQasmLanguage(monaco) {
  // Guard against double registration
  const langs = monaco.languages.getLanguages()
  if (langs.some(l => l.id === 'qasm')) {
    return
  }

  monaco.languages.register({ id: 'qasm' })

  // Define QASM language tokenizer
  monaco.languages.setMonarchTokensProvider('qasm', {
    defaultToken: '',
    tokenPostfix: '.qasm',

    keywords: [
      // OpenQASM 2.0
      'OPENQASM', 'include', 'qreg', 'creg', 'gate', 'opaque',
      'measure', 'reset', 'if', 'barrier',
      // OpenQASM 3.0 additions
      'def', 'cal', 'defcal', 'defcalgrammar', 'extern',
      'array', 'let', 'box', 'switch', 'case', 'default',
      'while', 'for', 'in', 'return', 'break', 'continue',
      'pragma', 'input', 'output', 'const', 'sizeof',
      'delay', 'stretch', 'durationof', 'gphase', 'grayns',
      'int', 'uint', 'float', 'bool', 'complex', 'angle',
      'bit', 'qubit'
    ],

    typeKeywords: [
      'int', 'uint', 'float', 'bool', 'complex', 'angle',
      'bit', 'qubit', 'qreg', 'creg'
    ],

    operators: [
      '=', '>', '<', '!', '~', '?', ':',
      '==', '<=', '>=', '!=', '&&', '||', '++', '--',
      '+', '-', '*', '/', '&', '|', '^', '%', '<<', '>>',
      '+=', '-=', '*=', '/=', '&=', '|=', '^=', '%=', '<<=', '>>=',
      '->'
    ],

    symbols: /[=><!~?:&|+\-*/^%]+/,

    escapes: /\\(?:[abfnrtv\\"']|x[0-9A-Fa-f]{1,4}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})/,

    tokenizer: {
      root: [
        // Comments
        [/\/\/.*$/, 'comment'],
        [/\/\*/, 'comment', '@comment'],

        // Preprocessor / version directives
        [/(OPENQASM)(\s*)(\d+\.\d+)/, ['keyword', 'white', 'number']],
        [/(include)(\s+)("[\w.]+")/, ['keyword', 'white', 'string']],
        [/defcalgrammar(\s+)("[^"]*")/, ['keyword', 'white', 'string']],

        // Pragmas
        [/pragma(\s+)(\w+)/, ['keyword', 'white', 'identifier']],

        // Built-in gates (common)
        [/\b(CX|cx|U3|u3|U2|u2|U1|u1|U|u|CX|cx|id|x|y|z|h|s|sdg|t|tdg|rx|ry|rz|p|swap|cx|ccx|cswap|ch|cz|cy|crz|cu1|cu3|i)\b/, 'keyword'],

        // Keywords
        [/[a-zA-Z_$][\w$]*/, {
          cases: {
            '@keywords': 'keyword',
            '@typeKeywords': 'keyword',
            '@default': 'identifier'
          }
        }],

        // Numbers (including angle brackets for timing)
        [/\d+\.\d+([eE][+-]?\d+)?[a-zA-Z]*/, 'number'],
        [/\.\d+([eE][+-]?\d+)?[a-zA-Z]*/, 'number'],
        [/0[xX][0-9a-fA-F]+/, 'number'],
        [/\d+[a-zA-Z]*/, 'number'],
        [/\d+/, 'number'],

        // Strings
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],

        // Delimiters
        [/[{}()\[\]]/, '@brackets'],
        [/[;,]/, 'delimiter'],

        // Operators
        [/@symbols/, {
          cases: {
            '@operators': 'operator',
            '@default': ''
          }
        }],

        // Whitespace
        [/\s+/, 'white']
      ],

      comment: [
        [/[^/*]+/, 'comment'],
        [/\*\//, 'comment', '@pop'],
        [/[/*]/, 'comment']
      ],

      string: [
        [/[^\\"]+/, 'string'],
        [/@escapes/, 'string.escape'],
        [/\\./, 'string.escape.invalid'],
        [/"/, 'string', '@pop']
      ]
    }
  })

  // Define language configuration (brackets, comments, auto-closing)
  monaco.languages.setLanguageConfiguration('qasm', {
    comments: {
      lineComment: '//',
      blockComment: ['/*', '*/']
    },
    brackets: [
      ['{', '}'],
      ['[', ']'],
      ['(', ')']
    ],
    autoClosingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"', notIn: ['string', 'comment'] },
      { open: "'", close: "'", notIn: ['string', 'comment'] }
    ],
    surroundingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"' },
      { open: "'", close: "'" }
    ]
  })

  // Register a dark theme for QASM
  monaco.editor.defineTheme('qasm-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: '569CD6' },
      { token: 'number', foreground: 'B5CEA8' },
      { token: 'string', foreground: 'CE9178' },
      { token: 'identifier', foreground: '9CDCFE' },
      { token: 'operator', foreground: 'D4D4D4' },
      { token: 'delimiter', foreground: 'D4D4D4' }
    ],
    colors: {
      'editor.background': '#1E1E1E'
    }
  })

  // Register a light theme for QASM
  monaco.editor.defineTheme('qasm-light', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6A7D8E', fontStyle: 'italic' },
      { token: 'keyword', foreground: '0000FF' },
      { token: 'number', foreground: '098658' },
      { token: 'string', foreground: 'A31515' },
      { token: 'identifier', foreground: '001080' },
      { token: 'operator', foreground: '000000' },
      { token: 'delimiter', foreground: '000000' }
    ],
    colors: {
      'editor.background': '#FFFFFF'
    }
  })
}
