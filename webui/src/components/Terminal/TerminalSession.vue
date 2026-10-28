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
  <div ref="terminalRef" class="terminal-session" />
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { SearchAddon } from '@xterm/addon-search'
import '@xterm/xterm/css/xterm.css'

import { createTerminalSocket, getTerminalToken } from '@/api/terminal'
import { useTerminalStore } from '@/store/modules/terminal'

defineOptions({ name: 'TerminalSession' })

const props = defineProps({
  // local session id (front-end generated); NOT the backend session_id
  sessionId: {
    type: String,
    required: true
  },
  // whether this session's tab is currently active
  active: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['session-open', 'session-close', 'session-error'])

const terminalRef = ref(null)
const terminalStore = useTerminalStore()

let term = null
let fitAddon = null
let socket = null
let resizeObserver = null
let exited = false

// reactive theme applied to xterm
const themeConfig = computed(() => terminalStore.currentTheme.theme)

function sendResize() {
  if (!term || !socket) return
  socket.send({ type: 'resize', cols: term.cols, rows: term.rows })
}

function handleMessage(msg) {
  if (!msg || !term) return
  switch (msg.type) {
    case 'auth_ok':
      exited = false
      terminalStore.updateSession(props.sessionId, {
        sessionId: msg.session_id || '',
        connected: true
      })
      emit('session-open', msg)
      break
    case 'auth_fail':
      term.write(`\r\n[auth failed: ${msg.reason || 'unknown'}]\r\n`)
      terminalStore.updateSession(props.sessionId, { connected: false })
      emit('session-error', msg)
      break
    case 'output':
      term.write(msg.data || '')
      terminalStore.setHasForegroundOutput(true)
      break
    case 'exit':
      exited = true
      term.write(`\r\n[process exited: ${msg.code !== undefined ? msg.code : '?'}]\r\n`)
      terminalStore.updateSession(props.sessionId, { connected: false })
      emit('session-close', msg)
      break
    case 'error':
      term.write(`\r\n[error: ${msg.message || 'unknown'}]\r\n`)
      emit('session-error', msg)
      break
    case 'pong':
      // heartbeat response; nothing to do
      break
    default:
      break
  }
}

function connect() {
  const token = getTerminalToken()
  if (!token) {
    if (term) {
      term.write('\r\n[no auth token, please login first]\r\n')
    }
    return
  }
  socket = createTerminalSocket({
    cols: term ? term.cols : 80,
    rows: term ? term.rows : 24,
    token,
    onMessage: handleMessage,
    onClose: (ev, info) => {
      if (!info || !info.willReconnect) {
        terminalStore.updateSession(props.sessionId, { connected: false })
        if (term && !exited) {
          term.write('\r\n[disconnected]\r\n')
        }
        emit('session-close', { code: ev && ev.code })
      } else if (term) {
        term.write(`\r\n[reconnecting, attempt ${info.attempt}...]\r\n`)
      }
    },
    onError: () => {
      // surfaced via onclose; keep silent here to avoid duplicate logs
    }
  })
}

onMounted(() => {
  term = new Terminal({
    cursorBlink: true,
    fontFamily: 'Menlo, Consolas, monospace',
    fontSize: 14,
    scrollback: 5000,
    theme: themeConfig.value
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.loadAddon(new SearchAddon())
  term.open(terminalRef.value)
  fitAddon.fit()

  term.onData((data) => {
    if (exited) return
    if (socket && socket.isOpen()) {
      socket.send({ type: 'input', data })
    }
  })

  connect()

  resizeObserver = new ResizeObserver(() => {
    if (!term || !fitAddon) return
    try {
      fitAddon.fit()
      sendResize()
    } catch (e) {
      // ignore fit errors when the container is hidden
    }
  })
  if (terminalRef.value) {
    resizeObserver.observe(terminalRef.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    try {
      resizeObserver.disconnect()
    } catch (e) { /* ignore */ }
    resizeObserver = null
  }
  if (socket) {
    try {
      socket.send({ type: 'close', reason: 'dialog closed' })
    } catch (e) { /* ignore */ }
    socket.close()
    socket = null
  }
  if (term) {
    try {
      term.dispose()
    } catch (e) { /* ignore */ }
    term = null
  }
  fitAddon = null
})

// react to theme changes without reconnecting
watch(themeConfig, (newTheme) => {
  if (term && newTheme) {
    term.options.theme = { ...newTheme }
  }
}, { deep: true })

function fit() {
  if (fitAddon && term) {
    try {
      fitAddon.fit()
      sendResize()
    } catch (e) { /* ignore */ }
  }
}

function focus() {
  if (term) {
    term.focus()
  }
}

defineExpose({ fit, focus })
</script>

<style lang="scss" scoped>
.terminal-session {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
