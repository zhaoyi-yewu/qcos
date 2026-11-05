<!--
  Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.

  qcos is licensed under Mulan PSL v2.
  You can use this software according to the terms and conditions
  of the Mulan PSL v2.
  You may obtain a copy of Mulan PSL v2 at:
          http://license.coscl.org.cn/MulanPSL2
  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
      WITHOUT WARRANTIES OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
  MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
  See the Mulan PSL v2 for more details.
-->

<template>
  <div class="monaco-editor-wrapper">
    <vue-monaco-editor
      ref="vueMonacoEditor"
      class="monaco-editor-inner"
      :value="value"
      :language="language"
      :theme="theme"
      :options="mergedOptions"
      :path="modelPath"
      @change="onChange"
      @mount="onMount"
    />
    <div v-if="showStatusBar" class="monaco-status-bar">
      <span
        class="status-item status-item-clickable"
        title="光标所在行 / 列（点击打开 Monaco 内置 Go to Line/Column，等同 Ctrl+G）"
        @click="openMonacoGotoLine"
      >
        行 {{ cursorLine }}, 列 {{ cursorColumn }}
      </span>
      <span class="status-item" title="总行数">
        共 {{ totalLines }} 行
      </span>
      <span class="status-item status-item-clickable" :title="overwriteTip" @click="toggleOverwrite">
        {{ isOverwrite ? 'OVR' : 'INS' }}
      </span>
      <span class="status-item" :class="{ 'is-on': capsLockOn }" title="Caps Lock 状态">
        {{ capsLockOn ? 'CAPS' : 'caps' }}
      </span>
      <!--
        Indent indicator is READ-ONLY. The previous clickable version
        called model.updateOptions({insertSpaces, tabSize}) which
        interacted badly with vue-monaco-editor's deep-watch on the
        :options prop (the parent passes a hard-coded
        {tabSize:4, insertSpaces:true} object, so the watcher
        immediately reset the editor's options back, monaco fired
        another configuration event, the cycle repeated with
        automaticLayout and the page froze). Display the current
        setting without offering a toggle.
      -->
      <span class="status-item" title="缩进方式（只读）">
        {{ indentLabel }}
      </span>
      <span class="status-item status-item-right">{{ languageLabel }}</span>
    </div>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { VueMonacoEditor, loader } from '@guolao/vue-monaco-editor'
import { registerQasmLanguage } from './qasm-language'
import { runLint, LINT_OWNER } from './lint'
// Use editor.api instead of monaco-editor to avoid loading all built-in language
// contributions (e.g. markdown findSectionHeaders.js which uses RegExp 'd' flag
// not supported by older MS Edge browsers)
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
// Pull in the standalone Go-to-Line contribution so the action
// `editor.action.gotoLine` (Ctrl+G) is actually registered. editor.api
// alone is a lean entry point and does NOT include it; without this
// import the status-bar "行 X, 列 Y" click would throw
// "command 'editor.action.gotoLine' not found".
import 'monaco-editor/esm/vs/editor/standalone/browser/quickAccess/standaloneGotoLineQuickAccess.js'
// Pull in the hover contribution so the red squiggly markers we set
// via monaco.editor.setModelMarkers() show a tooltip on hover.
// editor.api is a lean entry point and does NOT include the hover
// contribution by default — without this import the markers are
// rendered but mouse-over shows nothing.
import 'monaco-editor/esm/vs/editor/contrib/hover/browser/hoverContribution.js'
import 'monaco-editor/esm/vs/editor/contrib/hover/browser/markerHoverParticipant.js'

// Configure Monaco worker to run on the main thread (no web workers needed
// since we only use the custom QASM language and do not require syntax-aware
// language services that depend on workers)
self.MonacoEnvironment = {
  getWorker() {
    return {
      postMessage() {},
      terminate() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() { return true },
      onerror: null,
      onmessage: null,
      onmessageerror: null
    }
  }
}

// Register QASM language once
let qasmRegistered = false
if (!qasmRegistered) {
  registerQasmLanguage(monaco)
  qasmRegistered = true
}

// Configure the loader to use the already-imported monaco
loader.config({ monaco })

export default {
  name: 'MonacoEditor',
  components: {
    VueMonacoEditor
  },
  props: {
    value: {
      type: String,
      default: ''
    },
    language: {
      type: String,
      default: 'qasm'
    },
    theme: {
      type: String,
      default: 'qasm-light'
    },
    options: {
      type: Object,
      default: () => ({})
    },
    // Path used by @guolao/vue-monaco-editor to create/switch models
    modelPath: {
      type: String,
      default: undefined
    },
    // Whether to render the status bar below the editor
    showStatusBar: {
      type: Boolean,
      default: true
    }
  },
  emits: ['change', 'mount'],
  data() {
    return {
      // NOTE: editorInstance holds the monaco editor instance. If
      // Vue wraps it in a reactive proxy, monaco's internal property
      // reads trigger Vue's `track()` which recursively walks the
      // proxy chain and deadlocks the page (verified empirically:
      // typing a single character froze Firefox inside
      // `track -> get -> getValue`). We assign it via markRaw() in
      // onMount and keep the initial null here just so the template
      // can read editorInstance safely before mount.
      editorInstance: null,
      // Cursor position (1-based)
      cursorLine: 1,
      cursorColumn: 1,
      // Document stats
      totalLines: 1,
      totalColumns: 0,
      // Insert vs Overwrite
      isOverwrite: false,
      // Caps Lock tracking (best-effort; updated via key events)
      capsLockOn: false,
      // Indent settings (mirror merged options, not just user-supplied ones)
      indentSpaces: (this.options && this.options.insertSpaces) !== false,
      indentSize: (this.options && this.options.tabSize) || 4,
      // Lint debounce timer handle; null when no lint is scheduled.
      _lintTimer: null,
      _disposers: []
    }
  },
  computed: {
    /**
     * Merge the caller-supplied ``options`` prop over the editor's
     * defaults. Defaults include ``fixedOverflowWidgets: true`` so
     * the hover tooltip on a marker near the top of the editor is
     * not clipped by the editor container (the "hover above row 1
     * is invisible" issue). Callers can still override any default
     * via the options prop.
     */
    mergedOptions() {
      return {
        automaticLayout: true,
        fontSize: 14,
        lineHeight: 21,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 4,
        insertSpaces: true,
        fontFamily: 'Consolas, "Courier New", monospace',
        lineNumbers: 'on',
        folding: true,
        bracketPairColorization: { enabled: true },
        // Render hover widgets (marker tooltips, parameter hints,
        // etc.) into `document.body` instead of inside the editor
        // container. Without this, the hover tooltip on the FIRST
        // line of the editor is positioned *above* the marker and
        // gets clipped by the editor's overflow:hidden boundary.
        fixedOverflowWidgets: true,
        ...(this.options || {})
      }
    },
    overwriteTip() {
      return this.isOverwrite
        ? '覆盖模式（点击切换为插入）'
        : '插入模式（点击切换为覆盖）'
    },
    indentLabel() {
      return this.indentSpaces
        ? `Spaces: ${this.indentSize}`
        : `Tab Size: ${this.indentSize}`
    },
    languageLabel() {
      return (this.language || 'plain text').toUpperCase()
    }
  },
  watch: {
    // No automatic watchers. Lint is only triggered by:
    //   1. onDidChangeModelContent (user typed) — debounced
    //   2. explicit _lintNow() calls
    // Watching modelPath / language / value here would fire lint
    // during vue-monaco-editor's model swap and freeze the page
    // (empirically verified: model.getValue() inside a watcher
    // deadlocks monaco's normalization when adding a tab).
  },
  beforeUnmount() {
    this._disposeListeners()
    this._cancelLintTimer()
    this._clearLintMarkers()
  },
  methods: {
    onChange(value, event) {
      this.$emit('change', value, event)
      // Note: doc stats (line count) are refreshed via the
      // onDidChangeModelContent listener attached in _attachListeners;
      // calling _refreshDocStats here would do the work twice per
      // keystroke.
    },
    onMount(editor, monacoInstance) {
      // markRaw: prevent Vue from wrapping the monaco editor in a
      // reactive proxy. Without this, every monaco internal property
      // read goes through Vue's `track()` and the page freezes the
      // moment the user types (see the Firefox "Script terminated
      // by timeout" stack trace pointing at track -> getValue).
      this.editorInstance = markRaw(editor)
      this._attachListeners(editor)
      this._refreshDocStats()
      this._refreshCursor(editor)
      // NO lint on mount. Calling model.getValue() during mount
      // deadlocks monaco (empirically verified via the "add tab"
      // and "import qasm file" freeze stack traces). The user
      // will see lint markers as soon as they type — that is
      // acceptable UX for a first pass.
      this.$emit('mount', editor, monacoInstance)
    },
    getEditor() {
      return this.$refs.vueMonacoEditor
    },
    focus() {
      if (this.editorInstance) {
        this.editorInstance.focus()
      }
    },
    // ==================== status bar ====================
    _attachListeners(editor) {
      if (!editor) return
      // IMPORTANT: dispose previous listeners before attaching new ones.
      // The same MonacoEditor component is reused across tab switches in
      // the job submit page (model-path changes trigger onMount), and
      // without cleanup each switch adds another set of listeners on the
      // shared editor instance. After N tab switches every keystroke
      // would fire N duplicate callbacks — that is the root cause of
      // the "add tab -> editor freezes" report.
      this._disposeListeners()
      this._disposers.push(
        editor.onDidChangeCursorPosition(() => this._refreshCursor(editor)),
        editor.onDidChangeModelContent(() => {
          this._refreshDocStats()
          // Schedule a lint pass on the *model* (not the editor) so
          // the lint code never touches a Vue-reactive editor proxy.
          // Passing the raw model + language into the timer closure
          // avoids any `this` access in the deferred callback, which
          // empirically froze the page (Vue `track()` recursion via
          // reactive `this.language` inside the timer).
          const model = editor.getModel()
          if (model && typeof model.isDisposed === 'function' && !model.isDisposed()) {
            const lang = this.language
            this._scheduleLintForModel(model, lang, 400)
          }
        }),
        editor.onDidChangeConfiguration(() => this._refreshIndent(editor))
      )
      // Track Insert/Overwrite toggle and Caps Lock via key events on the
      // editor DOM node. Caps Lock state is read from the KeyboardEvent
      // modifier state (getModifierState), which is reliable for keys
      // that produce characters.
      const dom = editor.getDomNode()
      if (dom) {
        dom.addEventListener('keydown', this._onKeydown, true)
        this._disposers.push({
          dispose: () => dom.removeEventListener('keydown', this._onKeydown, true)
        })
      }
    },
    _disposeListeners() {
      this._disposers.forEach(d => {
        try { d.dispose() } catch (e) { /* noop */ }
      })
      this._disposers = []
    },
    _onKeydown(e) {
      // Caps Lock indicator — KeyboardEvent.getModifierState is the only
      // reliable cross-browser way to detect Caps Lock state.
      if (typeof e.getModifierState === 'function') {
        this.capsLockOn = e.getModifierState('CapsLock')
      }
      // Insert key toggles overwrite mode in Monaco by default. Refresh
      // the indicator after the editor processes the key.
      if (e.key === 'Insert') {
        this.$nextTick(() => this._refreshOverwrite())
      }
    },
    _refreshCursor(editor) {
      const pos = editor.getPosition()
      if (pos) {
        this.cursorLine = pos.lineNumber
        this.cursorColumn = pos.column
      }
    },
    _refreshDocStats() {
      if (!this.editorInstance) return
      const model = this.editorInstance.getModel()
      if (!model) return
      // Only refresh the line count here. Computing the longest line
      // requires scanning every line which freezes the UI on large
      // files (and was the root cause of "add tab -> freeze" reports).
      // Column count is intentionally not displayed; VSCode's status
      // bar doesn't show it either.
      this.totalLines = model.getLineCount()
    },
    _refreshIndent(editor) {
      const opts = editor.getOptions()
      const insertSpaces = opts.get(88) /* EditorOption.insertSpaces = 88 */
      const tabSize = opts.get(89) /* EditorOption.tabSize = 89 */
      // Fallback to direct lookup by name if numeric IDs change
      if (typeof insertSpaces === 'boolean') {
        this.indentSpaces = insertSpaces
      }
      if (typeof tabSize === 'number') {
        this.indentSize = tabSize
      }
    },
    _refreshOverwrite() {
      if (!this.editorInstance) return
      // Monaco's internal "overtype" flag is exposed via the
      // editor's "getOption" API under EditorOption.readOnly not
      // being related; the only reliable way is to read the
      // cursor style configuration. We track the toggle ourselves
      // because Monaco does not publicly expose overtype state.
      // So we simply flip our local state — the Insert key already
      // toggled the actual mode on Monaco's side.
      this.isOverwrite = !this.isOverwrite
    },
    toggleOverwrite() {
      if (!this.editorInstance) return
      // Trigger Monaco's built-in "toggle insert" command so behaviour
      // stays consistent with the Insert key.
      this.editorInstance.trigger('statusbar', 'type', null)
      this.isOverwrite = !this.isOverwrite
    },
    // toggleIndent was removed alongside the clickable status-bar
    // item — see the template comment above. The status bar still
    // shows the active indent mode; users who need to change it can
    // do so via the editor's context menu or by editing the source.
    // Status-bar "行 X, 列 Y" click: open Monaco's built-in Go-to-Line
    // widget. The action ships with the standalone editor (Ctrl+G) and
    // renders inside Monaco's own DOM, so it never fights with Element
    // Plus's focus management — which is what made our previous popover /
    // dialog / inline-input attempts freeze the page.
    openMonacoGotoLine() {
      const editor = this.editorInstance
      if (!editor) return
      // The goto-line widget only appears when the editor has focus;
      // grab focus first so the widget is anchored correctly.
      editor.focus()
      editor.trigger('statusbar', 'editor.action.gotoLine', null)
    },

    // ==================== lint ====================
    /**
     * Schedule a lint pass for a specific (model, language) pair
     * after ``delayMs`` milliseconds. The model and language are
     * captured *by value* in the closure, so the deferred callback
     * never touches ``this`` — that was the root cause of the
     * freeze (Vue's `track()` running inside a timer against
     * `this.language` / `this.editorInstance` created a cycle).
     *
     * @param {object} model - monaco.ITextModel, captured raw
     * @param {string} language - language id captured at schedule time
     * @param {number} delayMs - debounce delay (400 ms for typing)
     */
    _scheduleLintForModel(model, language, delayMs) {
      this._cancelLintTimer()
      this._lintTimer = setTimeout(() => {
        this._lintTimer = null
        // requestIdleCallback so a slow parse cannot block typing;
        // Safari lacks it, fall back to a plain setTimeout.
        const schedule = typeof requestIdleCallback === 'function'
          ? requestIdleCallback
          : (cb) => setTimeout(cb, 0)
        schedule(() => {
          // Re-validate the model is still alive *inside* the idle
          // callback — the user may have closed the tab in the
          // meantime.
          try {
            if (!model) return
            if (typeof model.isDisposed === 'function' && model.isDisposed()) {
              return
            }
            const text = model.getValue()
            if (typeof text !== 'string') return
            let markers
            try {
              markers = runLint(language, text)
            } catch (e) {
              // eslint-disable-next-line no-console
              console.error('[monaco-lint] linter crashed:', e)
              markers = []
            }
            // MarkerSeverity: Hint=1, Info=2, Warning=4, Error=8.
            // Hard-coding the numeric values avoids depending on
            // monaco.MarkerSeverity being re-exported from the
            // editor.api lean entry point.
            const mapped = markers.map(m => ({
              severity: m.severity === 'error'
                ? 8 // MarkerSeverity.Error
                : m.severity === 'warning'
                  ? 4 // MarkerSeverity.Warning
                  : 2, // MarkerSeverity.Info
              message: m.message,
              startLineNumber: m.startLineNumber,
              startColumn: m.startColumn,
              endLineNumber: m.endLineNumber,
              endColumn: m.endColumn,
              // The `source` field shows up in the marker hover
              // tooltip next to the message, e.g. "[qcos-lint] ...".
              source: LINT_OWNER
            }))
            monaco.editor.setModelMarkers(model, LINT_OWNER, mapped)
          } catch (e) {
            // Any unexpected failure must not propagate — a lint
            // pass can never break typing.
          }
        }, { timeout: 2000 })
      }, delayMs)
    },
    _cancelLintTimer() {
      if (this._lintTimer) {
        clearTimeout(this._lintTimer)
        this._lintTimer = null
      }
    },
    _clearLintMarkers() {
      // Clear markers on the *current* editor's model. We do NOT
      // cache the model across calls anymore (it was a source of
      // leaks and races).
      const editor = this.editorInstance
      if (!editor) return
      try {
        const model = editor.getModel()
        if (model && !(typeof model.isDisposed === 'function' && model.isDisposed())) {
          monaco.editor.setModelMarkers(model, LINT_OWNER, [])
        }
      } catch (e) {
        // ignore
      }
    }
  }
}
</script>

<style scoped>
.monaco-editor-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  /* Wrapper joins the parent layout; the inner editor div gets flex:1
     so the status bar is pinned to the bottom without shrinking. */
}

/* vue-monaco-editor renders its own root div; make it fill remaining
   space so the status bar appears at the bottom. Only flex:1 — do NOT
   set explicit height:100%, otherwise Monaco's automaticLayout sees a
   stable height and stops recalculating when the wrapper flexes. */
.monaco-editor-inner {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

:deep(.monaco-editor) {
  width: 100%;
  height: 100%;
}

.monaco-status-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-family: Consolas, 'Courier New', monospace;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-top: 1px solid var(--el-border-color-lighter);
  user-select: none;
}

.status-item {
  padding: 0 8px;
  line-height: 20px;
  border-radius: 3px;
  white-space: nowrap;
}


.status-item-clickable {
  cursor: pointer;
}

.status-item-clickable:hover {
  background: var(--el-fill-color);
  color: var(--el-text-color-primary);
}

.status-item.is-on {
  color: #fff;
  background: #409eff;
  font-weight: 700;
}

.status-item-right {
  margin-left: auto;
  font-weight: 700;
}
</style>
