<template>
  <div class="terminal-page" :class="{ 'is-fullscreen': fullscreen }">
    <!-- 标签栏 -->
    <div class="terminal-header">
      <div class="tabs-container">
        <div
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab', { active: activeTabId === tab.id }]"
          @click="switchTab(tab.id)"
        >
          <span :class="['tab-status-dot', tab.status]" :title="tab.status"></span>
          <span v-if="!tab.editing" class="tab-name" @dblclick="startRename(tab)">{{ tab.name }}</span>
          <input
            v-else
            v-model="tab.name"
            @blur="tab.editing = false"
            @keyup.enter="tab.editing = false"
            @keyup.esc="tab.editing = false"
            class="tab-name-input"
          />
          <button class="tab-close" @click.stop="closeTab(tab.id)" :title="$t('terminal.closeTab')">
            <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/></svg>
          </button>
        </div>
        <button class="add-tab-btn" @click="addNewTab" :title="$t('terminal.newTab')">
          <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" fill="currentColor"/></svg>
        </button>
      </div>

      <div class="header-actions">
        <select v-model="selectedShell" class="shell-select" :title="$t('terminal.selectShell')">
          <option v-for="shell in availableShells" :key="shell.path" :value="shell.path">{{ shell.name }}</option>
        </select>
        <button class="icon-btn" @click="zoomOut" :title="$t('terminal.zoomOut')">A-</button>
        <span class="font-size-label">{{ fontSize }}px</span>
        <button class="icon-btn" @click="zoomIn" :title="$t('terminal.zoomIn')">A+</button>
        <button class="icon-btn" @click="toggleFullscreen" :title="$t('terminal.fullscreen')">
          <svg v-if="!fullscreen" viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" fill="currentColor"/></svg>
          <svg v-else viewBox="0 0 24 24"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" fill="currentColor"/></svg>
        </button>
        <button class="icon-btn" :class="{ active: showSearch }" @click="toggleSearch" :title="$t('common.search')">
          <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27a6.5 6.5 0 001.48-5.34c-.47-2.78-2.79-5-5.59-5.34a6.505 6.505 0 00-7.27 7.27c.34 2.8 2.56 5.12 5.34 5.59a6.5 6.5 0 005.34-1.48l.27.28v.79l4.25 4.25c.41.41 1.08.41 1.49 0 .41-.41.41-1.08 0-1.49L15.5 14zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="currentColor"/></svg>
        </button>
        <button class="icon-btn" :class="{ active: showHistory }" @click="showHistory = !showHistory" :title="$t('terminal.history')">
          <svg viewBox="0 0 24 24"><path d="M13 3a9 9 0 00-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0013 21a9 9 0 000-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" fill="currentColor"/></svg>
        </button>
      </div>
    </div>

    <!-- 终端实例容器 -->
    <div class="terminal-body">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        v-show="activeTabId === tab.id"
        :ref="el => setTerminalRef(tab.id, el)"
        class="terminal-instance"
      ></div>
    </div>

    <!-- 终端内搜索条 -->
    <div v-if="showSearch" class="search-bar">
      <input
        v-model="searchQuery"
        :placeholder="$t('common.search')"
        class="search-input"
        @keyup.enter="doSearchNext"
        @keyup.esc="showSearch = false"
        ref="searchInputRef"
      />
      <button class="icon-btn btn-sm" @click="doSearchPrev" title="↑">↑</button>
      <button class="icon-btn btn-sm" @click="doSearchNext" title="↓">↓</button>
      <button class="icon-btn btn-sm" @click="showSearch = false" title="×">×</button>
    </div>

    <!-- 命令历史面板 -->
    <div v-if="showHistory" class="history-panel">
      <div class="history-header">
        <h3>{{ $t('terminal.commandHistory') }}</h3>
        <input v-model="historySearch" :placeholder="$t('common.search')" class="history-search" />
        <button class="btn btn-danger btn-sm" @click="clearHistory">{{ $t('common.clear') }}</button>
      </div>
      <div class="history-list">
        <div
          v-for="(item, idx) in filteredHistory"
          :key="idx"
          class="history-item"
          @click="useHistoryCommand(item.command)"
        >
          <span class="history-time">{{ formatTime(item.timestamp) }}</span>
          <span class="history-command">{{ item.command }}</span>
        </div>
        <div v-if="filteredHistory.length === 0" class="history-empty">{{ $t('terminal.noHistory') }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useStore } from 'vuex'
import { io } from 'socket.io-client'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { SearchAddon } from '@xterm/addon-search'
import { WebglAddon } from '@xterm/addon-webgl'
import { ClipboardAddon } from '@xterm/addon-clipboard'
import '@xterm/xterm/css/xterm.css'

let tabIdSeq = 0
const nextTabId = () => ++tabIdSeq

// 终端配色（One Dark 风格）
const DARK_THEME = {
  background: '#1e1e1e',
  foreground: '#d4d4d4',
  cursor: '#d4d4d4',
  cursorAccent: '#1e1e1e',
  selectionBackground: 'rgba(255,255,255,0.18)',
  black: '#000000',
  red: '#e06c75',
  green: '#98c379',
  yellow: '#e5c07b',
  blue: '#61afef',
  magenta: '#c678dd',
  cyan: '#56b6c2',
  white: '#d4d4d4',
  brightBlack: '#5c6370',
  brightRed: '#e06c75',
  brightGreen: '#98c379',
  brightYellow: '#e5c07b',
  brightBlue: '#61afef',
  brightMagenta: '#c678dd',
  brightCyan: '#56b6c2',
  brightWhite: '#ffffff'
}

const LIGHT_THEME = {
  background: '#ffffff',
  foreground: '#333333',
  cursor: '#333333',
  cursorAccent: '#ffffff',
  selectionBackground: 'rgba(0,0,0,0.15)',
  black: '#000000',
  red: '#c0392b',
  green: '#27ae60',
  yellow: '#b7791f',
  blue: '#2563eb',
  magenta: '#7c3aed',
  cyan: '#0891b2',
  white: '#333333',
  brightBlack: '#666666',
  brightRed: '#dc2626',
  brightGreen: '#16a34a',
  brightYellow: '#ca8a04',
  brightBlue: '#2563eb',
  brightMagenta: '#9333ea',
  brightCyan: '#0e7490',
  brightWhite: '#000000'
}

export default {
  name: 'Terminal',
  setup() {
    const store = useStore()

    const tabs = ref([])
    const activeTabId = ref(null)
    const selectedShell = ref('/bin/bash')
    const availableShells = ref([{ path: '/bin/bash', name: 'bash' }])
    const showHistory = ref(false)
    const showSearch = ref(false)
    const historySearch = ref('')
    const searchQuery = ref('')
    const commandHistory = ref([])
    const fullscreen = ref(false)
    const fontSize = ref(14)

    const terminalRefs = ref({})
    const searchInputRef = ref(null)

    let heartbeatTimer = null
    let resizeObserver = null

    const isDark = computed(() => store.state.theme === 'dark')
    const getTheme = () => isDark.value ? DARK_THEME : LIGHT_THEME

    const filteredHistory = computed(() => {
      if (!historySearch.value) return commandHistory.value
      const q = historySearch.value.toLowerCase()
      return commandHistory.value.filter(it => it.command.toLowerCase().includes(q))
    })

    // ============== xterm 实例与 socket 创建 ==============

    const createTerminalInstance = (tab) => {
      const container = terminalRefs.value[tab.id]
      if (!container) return

      const term = new Terminal({
        cursorBlink: true,
        cursorStyle: 'bar',
        fontSize: fontSize.value,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, Monaco, 'Courier New', monospace",
        theme: getTheme(),
        allowProposedApi: true,
        scrollback: 10000,
        convertEol: false,
        macOptionIsMeta: true,
        windowsMode: false
      })

      // 插件
      const fitAddon = new FitAddon()
      term.loadAddon(fitAddon)
      term.loadAddon(new WebLinksAddon((event, uri) => {
        if (uri) window.open(uri, '_blank', 'noopener')
      }))
      const searchAddon = new SearchAddon()
      term.loadAddon(searchAddon)
      try {
        term.loadAddon(new WebglAddon())
      } catch (e) {
        console.warn('[terminal] WebGL addon failed, using canvas renderer', e)
      }
      try {
        term.loadAddon(new ClipboardAddon())
      } catch (e) {
        console.warn('[terminal] Clipboard addon failed', e)
      }

      term.open(container)
      try { fitAddon.fit() } catch (e) {}

      tab.term = term
      tab.fitAddon = fitAddon
      tab.searchAddon = searchAddon
      tab.inputBuffer = ''

      // 输入：转发到 PTY，并积累命令缓冲用于历史记录
      term.onData(data => {
        if (tab.socket && tab.socket.connected) {
          tab.socket.emit('terminal_input', { data })
        }
        accumulateInput(tab, data)
      })

      // resize 同步
      term.onResize(({ cols, rows }) => {
        if (tab.socket && tab.socket.connected) {
          tab.socket.emit('terminal_resize', { cols, rows })
        }
      })

      term.focus()
    }

    // 简单的命令缓冲：仅用于历史记录（shell 自己处理 ↑/↓ 浏览）
    const accumulateInput = (tab, data) => {
      if (data === '\r') {
        const cmd = tab.inputBuffer.trim()
        if (cmd) {
          // 避免重复保存相同命令（如点击历史面板后回车）
          const lastCmd = commandHistory.value[0] && commandHistory.value[0].command
          if (cmd !== lastCmd) saveCommandToHistory(cmd)
        }
        tab.inputBuffer = ''
      } else if (data === '\x03' || data === '\x04' || data === '\x15') {
        // Ctrl+C / Ctrl+D / Ctrl+U
        tab.inputBuffer = ''
      } else if (data === '\x7f' || data === '\b') {
        // Backspace
        tab.inputBuffer = tab.inputBuffer.slice(0, -1)
      } else if (data.length === 1 && data.charCodeAt(0) >= 32 && data.charCodeAt(0) < 127) {
        tab.inputBuffer += data
      }
      // 忽略多字节/控制序列（↑↓ 等不会污染缓冲）
    }

    const createSocket = (tab) => {
      const token = store.state.token
      if (!token) {
        if (tab.term) {
          tab.term.writeln('\r\n\x1b[31m[Error: No auth token, please login first]\x1b[0m')
        }
        return null
      }

      const socket = io('/terminal', {
        path: '/socket.io',
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
      })

      socket.on('connect', () => {
        tab.status = 'connecting'
        const cols = tab.term ? tab.term.cols : 80
        const rows = tab.term ? tab.term.rows : 24
        socket.emit('create_session', {
          token,
          shell: selectedShell.value,
          cols, rows
        })
      })

      socket.on('session_created', () => {
        tab.status = 'connected'
        if (tab.term) tab.term.focus()
      })

      socket.on('terminal_output', (data) => {
        if (tab.term && data && data.data) {
          tab.term.write(data.data)
        }
      })

      socket.on('session_closed', (data) => {
        tab.status = 'disconnected'
        if (tab.term) {
          const reason = (data && data.reason) ? data.reason : 'closed'
          tab.term.writeln(`\r\n\x1b[31m[Session ${reason}]\x1b[0m`)
        }
      })

      socket.on('terminal_error', (data) => {
        tab.status = 'disconnected'
        if (tab.term) {
          const msg = (data && data.message) ? data.message : 'unknown error'
          tab.term.writeln(`\r\n\x1b[31m[Error: ${msg}]\x1b[0m`)
        }
      })

      socket.on('disconnect', () => {
        tab.status = 'disconnected'
      })

      socket.on('connect_error', (err) => {
        tab.status = 'disconnected'
        if (tab.term) {
          tab.term.writeln(`\r\n\x1b[31m[Connect error: ${err.message}]\x1b[0m`)
        }
      })

      return socket
    }

    // ============== 标签管理 ==============

    const addNewTab = async () => {
      const id = nextTabId()
      const tab = {
        id,
        name: `Terminal ${id}`,
        status: 'connecting',
        editing: false,
        term: null,
        fitAddon: null,
        searchAddon: null,
        socket: null,
        inputBuffer: ''
      }
      tabs.value.push(tab)
      activeTabId.value = id

      await nextTick()
      createTerminalInstance(tab)
      tab.socket = createSocket(tab)
    }

    const switchTab = async (id) => {
      activeTabId.value = id
      await nextTick()
      const tab = tabs.value.find(t => t.id === id)
      if (!tab) return
      if (tab.fitAddon) {
        try { tab.fitAddon.fit() } catch (e) {}
      }
      if (tab.term) tab.term.focus()
    }

    const closeTab = async (id) => {
      const idx = tabs.value.findIndex(t => t.id === id)
      if (idx < 0) return
      const tab = tabs.value[idx]

      if (tab.socket) {
        try { tab.socket.disconnect() } catch (e) {}
        tab.socket = null
      }
      if (tab.term) {
        try { tab.term.dispose() } catch (e) {}
        tab.term = null
      }
      tabs.value.splice(idx, 1)
      delete terminalRefs.value[id]

      if (tabs.value.length === 0) {
        await addNewTab()
        return
      }
      if (activeTabId.value === id) {
        const newActive = tabs.value[Math.min(idx, tabs.value.length - 1)]
        await switchTab(newActive.id)
      }
    }

    const startRename = (tab) => {
      tab.editing = true
      nextTick(() => {
        const el = document.querySelector('.tab-name-input')
        if (el) {
          el.focus()
          el.select()
        }
      })
    }

    // ============== 历史记录 ==============

    const saveCommandToHistory = async (cmd) => {
      commandHistory.value.unshift({
        command: cmd,
        timestamp: new Date().toISOString()
      })
      if (commandHistory.value.length > 500) commandHistory.value.pop()

      try {
        const token = store.state.token
        await fetch('/api/terminal/history', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ command: cmd })
        })
      } catch (e) {}
    }

    const useHistoryCommand = (cmd) => {
      const tab = tabs.value.find(t => t.id === activeTabId.value)
      if (!tab || !tab.socket || !tab.socket.connected) return
      // 把命令作为输入写入 PTY，shell 会回显并执行
      tab.socket.emit('terminal_input', { data: cmd })
      tab.inputBuffer = cmd
      showHistory.value = false
      if (tab.term) tab.term.focus()
    }

    const clearHistory = async () => {
      try {
        const token = store.state.token
        await fetch('/api/terminal/history/clear', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        })
        commandHistory.value = []
      } catch (e) {}
    }

    // ============== 工具：缩放 / 全屏 / 搜索 ==============

    const applyFontSize = () => {
      tabs.value.forEach(tab => {
        if (tab.term) tab.term.options.fontSize = fontSize.value
      })
    }
    const zoomIn = () => { fontSize.value = Math.min(32, fontSize.value + 1); applyFontSize() }
    const zoomOut = () => { fontSize.value = Math.max(8, fontSize.value - 1); applyFontSize() }

    const refitAll = () => {
      tabs.value.forEach(tab => {
        if (tab.fitAddon) {
          try { tab.fitAddon.fit() } catch (e) {}
        }
      })
    }

    const toggleFullscreen = () => {
      fullscreen.value = !fullscreen.value
      nextTick(() => setTimeout(refitAll, 60))
    }

    const toggleSearch = async () => {
      showSearch.value = !showSearch.value
      if (showSearch.value) {
        await nextTick()
        if (searchInputRef.value) searchInputRef.value.focus()
      }
    }

    const doSearchNext = () => {
      const tab = tabs.value.find(t => t.id === activeTabId.value)
      if (!tab || !tab.searchAddon || !searchQuery.value) return
      tab.searchAddon.findNext(searchQuery.value)
    }
    const doSearchPrev = () => {
      const tab = tabs.value.find(t => t.id === activeTabId.value)
      if (!tab || !tab.searchAddon || !searchQuery.value) return
      tab.searchAddon.findPrevious(searchQuery.value)
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('zh-CN', {
        hour: '2-digit', minute: '2-digit'
      })
    }

    // ============== refs ==============

    const setTerminalRef = (id, el) => {
      if (el) terminalRefs.value[id] = el
      else delete terminalRefs.value[id]
    }

    // ============== 主题切换响应 ==============

    watch(isDark, (dark) => {
      tabs.value.forEach(tab => {
        if (tab.term) tab.term.options.theme = dark ? DARK_THEME : LIGHT_THEME
      })
    })

    // ============== 初始化 / 拉取 ==============

    const fetchShells = async () => {
      try {
        const token = store.state.token
        const res = await fetch('/api/terminal/shells', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const shells = await res.json()
        if (Array.isArray(shells) && shells.length > 0) {
          availableShells.value = shells
          selectedShell.value = shells[0].path
        }
      } catch (e) {}
    }

    const fetchHistory = async () => {
      try {
        const token = store.state.token
        const res = await fetch('/api/terminal/history', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const data = await res.json()
        if (Array.isArray(data)) commandHistory.value = data
      } catch (e) {}
    }

    const startHeartbeat = () => {
      // 每 25s ping 一次，配合后端 30 分钟无活动超时
      heartbeatTimer = setInterval(() => {
        tabs.value.forEach(tab => {
          if (tab.socket && tab.socket.connected) {
            tab.socket.emit('ping_session', {})
          }
        })
      }, 25000)
    }

    onMounted(async () => {
      await fetchShells()
      await fetchHistory()
      await addNewTab()
      startHeartbeat()

      // 监听窗口大小变化
      window.addEventListener('resize', refitAll)

      // 监听容器大小变化（侧边栏切换等）
      nextTick(() => {
        const body = document.querySelector('.terminal-body')
        if (body && typeof ResizeObserver !== 'undefined') {
          resizeObserver = new ResizeObserver(() => refitAll())
          resizeObserver.observe(body)
        }
      })
    })

    onUnmounted(() => {
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      window.removeEventListener('resize', refitAll)
      if (resizeObserver) {
        try { resizeObserver.disconnect() } catch (e) {}
        resizeObserver = null
      }
      tabs.value.forEach(tab => {
        if (tab.socket) {
          try { tab.socket.disconnect() } catch (e) {}
        }
        if (tab.term) {
          try { tab.term.dispose() } catch (e) {}
        }
      })
      tabs.value = []
    })

    return {
      tabs, activeTabId, selectedShell, availableShells,
      showHistory, showSearch, historySearch, searchQuery,
      commandHistory, filteredHistory, fullscreen, fontSize,
      searchInputRef,
      setTerminalRef,
      addNewTab, switchTab, closeTab, startRename,
      zoomIn, zoomOut, toggleFullscreen, toggleSearch,
      doSearchNext, doSearchPrev,
      useHistoryCommand, clearHistory,
      formatTime
    }
  }
}
</script>

<style scoped>
.terminal-page {
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.terminal-page.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  height: 100vh;
  border-radius: 0;
  border: none;
}

/* ============== 标签栏 ============== */
.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  gap: var(--spacing-2);
}

.tabs-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  overflow-x: auto;
  flex: 1;
  min-width: 0;
}

.tabs-container::-webkit-scrollbar {
  height: 4px;
}

.tab {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
  max-width: 180px;
}

.tab:hover { background: var(--bg-secondary); }
.tab.active {
  background: var(--primary-500);
  color: white;
}

.tab-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #888;
}
.tab-status-dot.connecting { background: #e5c07b; animation: pulse 1.2s infinite; }
.tab-status-dot.connected { background: #98c379; }
.tab-status-dot.disconnected { background: #e06c75; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.tab-icon svg,
.tab-close svg {
  width: 14px;
  height: 14px;
}

.tab-name {
  font-size: var(--font-size-sm);
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-name-input {
  width: 80px;
  padding: 2px 4px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: var(--font-size-sm);
  outline: 1px solid rgba(255,255,255,0.3);
  border-radius: var(--radius-sm);
}

.tab-close {
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.6;
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.tab-close:hover {
  opacity: 1;
  background: rgba(255,255,255,0.2);
}

.add-tab-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.add-tab-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.add-tab-btn svg { width: 18px; height: 18px; }

.header-actions {
  display: flex;
  gap: var(--spacing-1);
  align-items: center;
  flex-shrink: 0;
}

.shell-select {
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  transition: all var(--duration-fast) var(--ease-out);
}
.icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.icon-btn.active {
  background: var(--primary-500);
  color: white;
}
.icon-btn svg { width: 16px; height: 16px; }
.icon-btn.btn-sm {
  width: 24px;
  height: 24px;
  font-size: var(--font-size-xs);
}

.font-size-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  min-width: 32px;
  text-align: center;
}

/* ============== 终端主体 ============== */
.terminal-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: #1e1e1e;
}

.terminal-instance {
  width: 100%;
  height: 100%;
  padding: 4px;
  box-sizing: border-box;
}

.terminal-instance :deep(.xterm) {
  height: 100%;
}

.terminal-instance :deep(.xterm-viewport) {
  background-color: #1e1e1e !important;
}

/* ============== 搜索条 ============== */
.search-bar {
  position: absolute;
  top: var(--spacing-2);
  right: var(--spacing-4);
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 50;
}

.search-input {
  width: 200px;
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  outline: none;
}
.search-input:focus {
  border-color: var(--primary-500);
}

/* ============== 历史面板 ============== */
.history-panel {
  position: absolute;
  right: var(--spacing-4);
  bottom: var(--spacing-4);
  width: 420px;
  max-width: calc(100% - var(--spacing-8));
  max-height: 320px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  border-bottom: 1px solid var(--border-color);
}

.history-header h3 {
  margin: 0;
  font-size: var(--font-size-sm);
  flex: 1;
}

.history-search {
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-xs);
  outline: none;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2);
  min-height: 0;
}

.history-item {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.history-item:hover {
  background: var(--bg-tertiary);
}

.history-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  min-width: 50px;
  font-family: monospace;
}

.history-command {
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: var(--font-size-xs);
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
}

.history-empty {
  padding: var(--spacing-4);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-3);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.btn-danger { background: var(--danger-500); color: white; }
.btn-danger:hover { background: var(--danger-600); }
.btn-sm { padding: var(--spacing-1) var(--spacing-2); font-size: var(--font-size-xs); }
</style>
