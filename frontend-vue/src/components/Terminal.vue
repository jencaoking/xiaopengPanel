<template>
  <div class="terminal-page">
    <div class="terminal-header">
      <div class="tabs-container">
        <div 
          v-for="tab in tabs" 
          :key="tab.id"
          :class="['tab', { active: activeTabId === tab.id }]"
          @click="switchTab(tab.id)"
        >
          <span class="tab-icon">
            <svg viewBox="0 0 24 24"><path d="M20 19V7H4v12h16m0-16a2 2 0 012 2v14a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h16M7.5 13h2v2h-2v-2m0-4h2v2h-2V9m4 4h2v2h-2v-2m0-4h2v2h-2V9m4 4h2v2h-2v-2m0-4h2v2h-2V9z" fill="currentColor"/></svg>
          </span>
          <span class="tab-name" v-if="!tab.editing" @dblclick="startRename(tab)">{{ tab.name }}</span>
          <input 
            v-else 
            v-model="tab.name" 
            @blur="tab.editing = false"
            @keyup.enter="tab.editing = false"
            class="tab-name-input"
            ref="renameInput"
          />
          <button class="tab-close" @click.stop="closeTab(tab.id)">&times;</button>
        </div>
        <button class="add-tab-btn" @click="addNewTab" title="New Terminal">
          <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" fill="currentColor"/></svg>
        </button>
      </div>
      <div class="header-actions">
        <select v-model="selectedShell" class="shell-select">
          <option v-for="shell in availableShells" :key="shell.path" :value="shell.path">{{ shell.name }}</option>
        </select>
        <button class="btn btn-secondary" @click="showHistory = !showHistory">
          <svg viewBox="0 0 24 24"><path d="M13 3a9 9 0 00-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0013 21a9 9 0 000-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" fill="currentColor"/></svg>
          {{ $t('terminal.history') }}
        </button>
      </div>
    </div>
    
    <div class="terminal-body">
      <div v-for="tab in tabs" :key="tab.id" v-show="activeTabId === tab.id" class="terminal-instance" :ref="el => setTerminalRef(tab.id, el)">
        <div class="terminal-output" :ref="el => setOutputRef(tab.id, el)">
          <div v-for="(line, idx) in tab.output" :key="idx" class="output-line" v-html="formatOutput(line)"></div>
        </div>
      </div>
    </div>
    
    <div class="terminal-input-area">
      <span class="prompt">{{ currentPrompt }}</span>
      <input 
        v-model="currentCommand"
        @keyup.enter="executeCommand"
        @keyup.up="navigateHistory(-1)"
        @keyup.down="navigateHistory(1)"
        @keydown.tab.prevent="autoComplete"
        class="terminal-input"
        ref="commandInput"
        placeholder=""
      />
    </div>
    
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
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'

export default {
  name: 'Terminal',
  setup() {
    const store = useStore()
    const { t } = useI18n()
    
    const tabs = ref([{ id: 1, name: 'Terminal 1', output: [], socket: null, editing: false }])
    const activeTabId = ref(1)
    const currentCommand = ref('')
    const currentPrompt = ref('$ ')
    const selectedShell = ref('/bin/bash')
    const availableShells = ref([{ path: '/bin/bash', name: 'bash' }])
    const showHistory = ref(false)
    const historySearch = ref('')
    const commandHistory = ref([])
    const historyIndex = ref(-1)
    const commandInput = ref(null)
    
    const terminalRefs = ref({})
    const outputRefs = ref({})
    
    const setTerminalRef = (id, el) => { if (el) terminalRefs.value[id] = el }
    const setOutputRef = (id, el) => { if (el) outputRefs.value[id] = el }
    
    const filteredHistory = computed(() => {
      if (!historySearch.value) return commandHistory.value
      const query = historySearch.value.toLowerCase()
      return commandHistory.value.filter(item => item.command.toLowerCase().includes(query))
    })
    
    const addNewTab = () => {
      const newId = Math.max(...tabs.value.map(t => t.id)) + 1
      tabs.value.push({ id: newId, name: `Terminal ${newId}`, output: [], socket: null, editing: false })
      activeTabId.value = newId
    }
    
    const switchTab = (id) => {
      activeTabId.value = id
      nextTick(() => commandInput.value?.focus())
    }
    
    const closeTab = (id) => {
      if (tabs.value.length <= 1) return
      const idx = tabs.value.findIndex(t => t.id === id)
      tabs.value.splice(idx, 1)
      if (activeTabId.value === id) {
        activeTabId.value = tabs.value[Math.max(0, idx - 1)].id
      }
    }
    
    const startRename = (tab) => {
      tab.editing = true
      nextTick(() => document.querySelector('.tab-name-input')?.focus())
    }
    
    const executeCommand = async () => {
      const cmd = currentCommand.value.trim()
      if (!cmd) return
      
      const activeTab = tabs.value.find(t => t.id === activeTabId.value)
      if (!activeTab) return
      
      activeTab.output.push({ type: 'input', text: `${currentPrompt.value}${cmd}` })
      
      commandHistory.value.unshift({ command: cmd, timestamp: new Date().toISOString() })
      if (commandHistory.value.length > 500) commandHistory.value.pop()
      historyIndex.value = -1
      
      try {
        const token = store.state.token
        await fetch('/api/terminal/history', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd })
        })
      } catch (e) {}
      
      if (cmd === 'clear') {
        activeTab.output = []
      } else {
        activeTab.output.push({ type: 'output', text: `$ ${cmd}: command executed` })
      }
      
      currentCommand.value = ''
      scrollToBottom()
    }
    
    const navigateHistory = (direction) => {
      const newIndex = historyIndex.value + direction
      if (newIndex >= -1 && newIndex < commandHistory.value.length) {
        historyIndex.value = newIndex
        currentCommand.value = newIndex >= 0 ? commandHistory.value[newIndex].command : ''
      }
    }
    
    const autoComplete = async () => {
      const partial = currentCommand.value
      if (!partial) return
      
      try {
        const token = store.state.token
        const res = await fetch(`/api/terminal/suggestions?partial=${encodeURIComponent(partial)}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const suggestions = await res.json()
        if (suggestions.length > 0) {
          currentCommand.value = suggestions[0].command
        }
      } catch (e) {}
    }
    
    const useHistoryCommand = (cmd) => {
      currentCommand.value = cmd
      showHistory.value = false
      commandInput.value?.focus()
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
    
    const formatOutput = (line) => {
      if (line.type === 'input') {
        return `<span class="input-line">${escapeHtml(line.text)}</span>`
      }
      return escapeHtml(line.text)
    }
    
    const escapeHtml = (text) => {
      return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    }
    
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    
    const scrollToBottom = () => {
      nextTick(() => {
        const output = outputRefs.value[activeTabId.value]
        if (output) output.scrollTop = output.scrollHeight
      })
    }
    
    const fetchShells = async () => {
      try {
        const token = store.state.token
        const res = await fetch('/api/terminal/shells', { headers: { 'Authorization': `Bearer ${token}` } })
        const shells = await res.json()
        if (shells.length > 0) {
          availableShells.value = shells
          selectedShell.value = shells[0].path
        }
      } catch (e) {}
    }
    
    const fetchHistory = async () => {
      try {
        const token = store.state.token
        const res = await fetch('/api/terminal/history', { headers: { 'Authorization': `Bearer ${token}` } })
        commandHistory.value = await res.json()
      } catch (e) {}
    }
    
    onMounted(() => {
      fetchShells()
      fetchHistory()
      commandInput.value?.focus()
    })
    
    return {
      tabs,
      activeTabId,
      currentCommand,
      currentPrompt,
      selectedShell,
      availableShells,
      showHistory,
      historySearch,
      commandHistory,
      historyIndex,
      commandInput,
      filteredHistory,
      setTerminalRef,
      setOutputRef,
      addNewTab,
      switchTab,
      closeTab,
      startRename,
      executeCommand,
      navigateHistory,
      autoComplete,
      useHistoryCommand,
      clearHistory,
      formatOutput,
      formatTime
    }
  }
}
</script>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.tabs-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  overflow-x: auto;
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
}

.tab:hover { background: var(--bg-secondary); }
.tab.active { background: var(--primary-500); color: white; }

.tab-icon svg { width: 14px; height: 14px; }
.tab-name { font-size: var(--font-size-sm); }
.tab-name-input { 
  width: 80px; 
  padding: 2px 4px; 
  border: none; 
  background: transparent; 
  color: inherit;
  font-size: var(--font-size-sm);
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
}
.tab-close:hover { opacity: 1; background: rgba(255,255,255,0.2); }

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
}
.add-tab-btn:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.add-tab-btn svg { width: 18px; height: 18px; }

.header-actions { display: flex; gap: var(--spacing-2); }
.shell-select { 
  padding: var(--spacing-1) var(--spacing-2); 
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.terminal-body { flex: 1; overflow: hidden; }
.terminal-instance { height: 100%; }
.terminal-output {
  height: 100%;
  padding: var(--spacing-4);
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  background: #1e1e1e;
  color: #d4d4d4;
}

.output-line { white-space: pre-wrap; word-break: break-all; }
.input-line { color: #4ec9b0; }

.terminal-input-area {
  display: flex;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-4);
  background: #252526;
  border-top: 1px solid #3c3c3c;
}

.prompt { 
  color: #4ec9b0; 
  font-family: 'Consolas', 'Monaco', monospace;
  margin-right: var(--spacing-2);
}

.terminal-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: var(--font-size-sm);
  outline: none;
}

.history-panel {
  position: absolute;
  right: var(--spacing-4);
  bottom: 60px;
  width: 400px;
  max-height: 300px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  overflow: hidden;
}

.history-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  border-bottom: 1px solid var(--border-color);
}

.history-header h3 { margin: 0; font-size: var(--font-size-sm); flex: 1; }
.history-search { 
  padding: var(--spacing-1) var(--spacing-2); 
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-xs);
}

.history-list { 
  max-height: 240px; 
  overflow-y: auto; 
  padding: var(--spacing-2);
}

.history-item {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.history-item:hover { background: var(--bg-tertiary); }
.history-time { font-size: var(--font-size-xs); color: var(--text-tertiary); min-width: 50px; }
.history-command { font-family: monospace; font-size: var(--font-size-xs); color: var(--text-primary); }

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
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }
.btn-secondary:hover { background: var(--bg-secondary); }
.btn-danger { background: var(--danger-500); color: white; }
.btn-danger:hover { background: var(--danger-600); }
.btn-sm { padding: var(--spacing-1) var(--spacing-2); font-size: var(--font-size-xs); }
</style>
