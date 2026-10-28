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
      :options="options"
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
      <span class="status-item status-item-clickable" title="缩进方式（点击切换）" @click="toggleIndent">
        {{ indentLabel }}
      </span>
      <span class="status-item status-item-right">{{ languageLabel }}</span>
    </div>
  </div>
</template>

<script>
import { VueMonacoEditor, loader } from '@guolao/vue-monaco-editor'
import { registerQasmLanguage } from './qasm-language'
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
      default: () => ({
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
        bracketPairColorization: { enabled: true }
      })
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
      // Indent settings (mirror options)
      indentSpaces: this.options.insertSpaces !== false,
      indentSize: this.options.tabSize || 4,
      _disposers: []
    }
  },
  computed: {
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
  beforeUnmount() {
    this._disposeListeners()
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
      this.editorInstance = editor
      this._attachListeners(editor)
      this._refreshDocStats()
      this._refreshCursor(editor)
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
        editor.onDidChangeModelContent(() => this._refreshDocStats()),
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
    toggleIndent() {
      if (!this.editorInstance) return
      const model = this.editorInstance.getModel()
      if (!model) return
      this.indentSpaces = !this.indentSpaces
      model.updateOptions({
        insertSpaces: this.indentSpaces,
        tabSize: this.indentSize
      })
    },
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
