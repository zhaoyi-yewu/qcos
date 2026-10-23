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
  <vue-monaco-editor
    :value="value"
    :language="language"
    :theme="theme"
    :options="options"
    :path="modelPath"
    @change="onChange"
    @mount="onMount"
  />
</template>

<script>
import { VueMonacoEditor, loader } from '@guolao/vue-monaco-editor'
import { registerQasmLanguage } from './qasm-language'
// Use editor.api instead of monaco-editor to avoid loading all built-in language
// contributions (e.g. markdown findSectionHeaders.js which uses RegExp 'd' flag
// not supported by older MS Edge browsers)
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'

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
    }
  },
  emits: ['change', 'mount'],
  methods: {
    onChange(value, event) {
      this.$emit('change', value, event)
    },
    onMount(editor, monaco) {
      this.$emit('mount', editor, monaco)
    },
    getEditor() {
      return this.$refs.vueMonacoEditor
    },
    focus() {
      const child = this.$children && this.$children[0]
      if (child && child.getEditor) {
        child.getEditor().focus()
      }
    }
  }
}
</script>

<style scoped>
:deep(.monaco-editor) {
  width: 100%;
  height: 100%;
}
</style>
