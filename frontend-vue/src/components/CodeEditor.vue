<template>
  <div class="code-editor-page">
    <div class="editor-header">
      <div class="file-tabs">
        <div 
          v-for="file in openFiles" 
          :key="file.path"
          :class="['file-tab', { active: activeFile?.path === file.path, modified: file.modified }]"
          @click="switchFile(file)"
        >
          <span class="file-icon" :class="getFileIconClass(file.name)">{{ getFileIcon(file.name) }}</span>
          <span class="file-name">{{ file.name }}</span>
          <span v-if="file.modified" class="modified-indicator">●</span>
          <button class="close-tab" @click.stop="closeFile(file)">&times;</button>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="saveCurrentFile" :disabled="!activeFile">
          <svg viewBox="0 0 24 24"><path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z" fill="currentColor"/></svg>
          {{ $t('common.save') }}
        </button>
        <button class="btn btn-secondary" @click="showSearchPanel = !showSearchPanel">
          <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="currentColor"/></svg>
          {{ $t('editor.find') }}
        </button>
        <button class="btn btn-secondary" @click="showReplacePanel = !showReplacePanel">
          <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0020 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 004 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z" fill="currentColor"/></svg>
          {{ $t('editor.replace') }}
        </button>
        <button class="btn btn-secondary" @click="showSettings = !showSettings">
          <svg viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L5.04 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/></svg>
        </button>
      </div>
    </div>
    
    <div class="editor-body">
      <div class="sidebar">
        <div class="sidebar-section">
          <h4>{{ $t('editor.outline') }}</h4>
          <div class="outline-list">
            <div 
              v-for="item in fileOutline" 
              :key="item.name"
              class="outline-item"
              @click="goToLine(item.line)"
            >
              <span class="outline-icon">{{ item.type === 'function' ? 'ƒ' : 'C' }}</span>
              <span class="outline-name">{{ item.name }}</span>
              <span class="outline-line">:{{ item.line }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="main-editor">
        <div v-if="showSearchPanel || showReplacePanel" class="search-replace-panel">
          <div class="search-row">
            <input 
              v-model="searchQuery" 
              :placeholder="$t('editor.searchPlaceholder')"
              class="search-input"
              @input="performSearch"
            />
            <label class="checkbox-label">
              <input type="checkbox" v-model="searchCaseSensitive" @change="performSearch" />
              Aa
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="searchWholeWord" @change="performSearch" />
              W
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="searchRegex" @change="performSearch" />
              .*
            </label>
            <span class="search-count" v-if="searchResults.length">
              {{ currentSearchIndex + 1 }} / {{ searchResults.length }}
            </span>
          </div>
          <div v-if="showReplacePanel" class="replace-row">
            <input 
              v-model="replaceQuery" 
              :placeholder="$t('editor.replacePlaceholder')"
              class="search-input"
            />
            <button class="btn btn-sm btn-secondary" @click="replaceNext">{{ $t('editor.replace') }}</button>
            <button class="btn btn-sm btn-secondary" @click="replaceAll">{{ $t('editor.replaceAll') }}</button>
          </div>
          <button class="close-panel" @click="showSearchPanel = false; showReplacePanel = false">&times;</button>
        </div>
        
        <div class="editor-container" v-if="activeFile">
          <div class="line-numbers">
            <div v-for="n in lineCount" :key="n" class="line-number" :class="{ active: n === currentLine }">{{ n }}</div>
          </div>
          <textarea 
            ref="editor"
            v-model="activeFile.content"
            class="code-textarea"
            :class="`language-${activeFile.language}`"
            @input="onContentChange"
            @scroll="syncScroll"
            @keydown="handleKeydown"
            @click="updateCurrentLine"
            @keyup="updateCurrentLine"
            spellcheck="false"
          ></textarea>
          <div class="syntax-highlight" v-html="highlightedCode" ref="highlightLayer"></div>
        </div>
        <div v-else class="no-file-open">
          <p>{{ $t('editor.noFileOpen') }}</p>
        </div>
        
        <div v-if="completions.length > 0" class="completion-panel" :style="completionStyle">
          <div 
            v-for="(item, idx) in completions" 
            :key="item.text"
            :class="['completion-item', { selected: idx === selectedCompletion }]"
            @click="applyCompletion(item)"
          >
            <span class="completion-type" :class="item.type">{{ item.type[0] }}</span>
            <span class="completion-text">{{ item.text }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="editor-footer">
      <div class="footer-left">
        <span v-if="activeFile">{{ activeFile.language }}</span>
        <span v-if="activeFile">UTF-8</span>
        <span v-if="activeFile">Ln {{ currentLine }}, Col {{ currentColumn }}</span>
      </div>
      <div class="footer-right">
        <span v-if="activeFile?.modified">{{ $t('editor.modified') }}</span>
      </div>
    </div>
    
    <div v-if="showSettings" class="settings-modal" @click.self="showSettings = false">
      <div class="modal-content">
        <h3>{{ $t('editor.settings') }}</h3>
        <div class="settings-form">
          <div class="form-group">
            <label>{{ $t('editor.fontSize') }}</label>
            <input type="number" v-model.number="editorSettings.fontSize" min="10" max="24" />
          </div>
          <div class="form-group">
            <label>{{ $t('editor.tabSize') }}</label>
            <select v-model.number="editorSettings.tabSize">
              <option :value="2">2</option>
              <option :value="4">4</option>
              <option :value="8">8</option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.wordWrap" />
              {{ $t('editor.wordWrap') }}
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.minimap" />
              {{ $t('editor.minimap') }}
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="saveSettings">{{ $t('common.save') }}</button>
          <button class="btn btn-secondary" @click="showSettings = false">{{ $t('common.close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'

export default {
  name: 'CodeEditor',
  setup() {
    const store = useStore()
    const { t } = useI18n()
    
    const openFiles = ref([])
    const activeFile = ref(null)
    const editor = ref(null)
    const highlightLayer = ref(null)
    
    const showSearchPanel = ref(false)
    const showReplacePanel = ref(false)
    const showSettings = ref(false)
    
    const searchQuery = ref('')
    const replaceQuery = ref('')
    const searchCaseSensitive = ref(false)
    const searchWholeWord = ref(false)
    const searchRegex = ref(false)
    const searchResults = ref([])
    const currentSearchIndex = ref(0)
    
    const currentLine = ref(1)
    const currentColumn = ref(1)
    
    const completions = ref([])
    const selectedCompletion = ref(0)
    const completionStyle = ref({ top: '0px', left: '0px' })
    
    const fileOutline = ref([])
    
    const editorSettings = ref({
      fontSize: 14,
      tabSize: 4,
      wordWrap: true,
      minimap: true,
      theme: 'vs-dark'
    })
    
    const lineCount = computed(() => {
      if (!activeFile.value?.content) return 1
      return activeFile.value.content.split('\n').length
    })
    
    const highlightedCode = ref('')
    let highlightTimeout = null
    
    const updateHighlight = () => {
      if (!activeFile.value?.content) {
        highlightedCode.value = ''
        return
      }
      // 使用 requestAnimationFrame 和防抖优化性能
      if (highlightTimeout) cancelAnimationFrame(highlightTimeout)
      highlightTimeout = requestAnimationFrame(() => {
        highlightedCode.value = applySyntaxHighlighting(activeFile.value.content, activeFile.value.language)
      })
    }
    
    watch(() => activeFile.value?.content, updateHighlight, { flush: 'post' })
    watch(() => activeFile.value?.language, updateHighlight)
    
    const languageKeywords = {
      javascript: ['const', 'let', 'var', 'function', 'class', 'if', 'else', 'for', 'while', 'return', 'import', 'export', 'async', 'await', 'try', 'catch', 'throw', 'new', 'this', 'true', 'false', 'null', 'undefined'],
      python: ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'return', 'import', 'from', 'as', 'try', 'except', 'finally', 'raise', 'with', 'lambda', 'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is'],
      html: ['html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'button', 'script', 'style', 'link', 'meta'],
      css: ['color', 'background', 'margin', 'padding', 'border', 'width', 'height', 'display', 'position', 'top', 'left', 'right', 'bottom', 'flex', 'grid', 'font', 'text'],
      sql: ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TABLE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'ON', 'AND', 'OR', 'NOT', 'ORDER', 'BY', 'GROUP', 'HAVING']
    }
    
    const applySyntaxHighlighting = (code, language) => {
      let highlighted = escapeHtml(code)
      
      const keywords = languageKeywords[language] || []
      keywords.forEach(keyword => {
        const regex = new RegExp(`\\b(${keyword})\\b`, 'g')
        highlighted = highlighted.replace(regex, '<span class="keyword">$1</span>')
      })
      
      highlighted = highlighted.replace(/(["'`])(?:(?!\1)[^\\]|\\.)*?\1/g, '<span class="string">$&</span>')
      highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="number">$1</span>')
      highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, '<span class="comment">$1</span>')
      highlighted = highlighted.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>')
      
      return highlighted
    }
    
    const escapeHtml = (text) => {
      return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    }
    
    const getFileIcon = (filename) => {
      const ext = filename.split('.').pop().toLowerCase()
      const icons = {
        js: 'JS', jsx: 'JS', ts: 'TS', tsx: 'TS',
        py: 'PY', java: 'JV', html: 'H', css: 'C',
        json: '{ }', md: 'MD', txt: 'T', sql: 'DB',
        vue: 'V', sh: 'SH', yml: 'Y', yaml: 'Y'
      }
      return icons[ext] || 'F'
    }
    
    const getFileIconClass = (filename) => {
      const ext = filename.split('.').pop().toLowerCase()
      const classes = {
        js: 'icon-js', jsx: 'icon-js', ts: 'icon-ts', tsx: 'icon-ts',
        py: 'icon-py', html: 'icon-html', css: 'icon-css',
        json: 'icon-json', md: 'icon-md', sql: 'icon-sql', vue: 'icon-vue'
      }
      return classes[ext] || 'icon-default'
    }
    
    const switchFile = (file) => {
      activeFile.value = file
      fetchOutline(file.content, file.language)
    }
    
    const closeFile = (file) => {
      const idx = openFiles.value.findIndex(f => f.path === file.path)
      if (idx > -1) {
        openFiles.value.splice(idx, 1)
        if (activeFile.value?.path === file.path) {
          activeFile.value = openFiles.value[Math.max(0, idx - 1)] || null
        }
      }
    }
    
    const onContentChange = () => {
      if (activeFile.value) {
        activeFile.value.modified = true
        updateCurrentLine()
      }
    }
    
    const handleKeydown = (e) => {
      if (e.key === 'Tab') {
        e.preventDefault()
        const start = editor.value.selectionStart
        const end = editor.value.selectionEnd
        const spaces = ' '.repeat(editorSettings.value.tabSize)
        activeFile.value.content = activeFile.value.content.substring(0, start) + spaces + activeFile.value.content.substring(end)
        nextTick(() => {
          editor.value.selectionStart = editor.value.selectionEnd = start + editorSettings.value.tabSize
        })
      }
      
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 's') {
          e.preventDefault()
          saveCurrentFile()
        } else if (e.key === 'f') {
          e.preventDefault()
          showSearchPanel.value = true
        } else if (e.key === 'h') {
          e.preventDefault()
          showReplacePanel.value = true
        } else if (e.key === ' ') {
          e.preventDefault()
          fetchCompletions()
        }
      }
      
      if (completions.value.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault()
          selectedCompletion.value = Math.min(selectedCompletion.value + 1, completions.value.length - 1)
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          selectedCompletion.value = Math.max(selectedCompletion.value - 1, 0)
        } else if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault()
          applyCompletion(completions.value[selectedCompletion.value])
        } else if (e.key === 'Escape') {
          completions.value = []
        }
      }
    }
    
    const updateCurrentLine = () => {
      if (!editor.value) return
      const text = editor.value.value.substring(0, editor.value.selectionStart)
      const lines = text.split('\n')
      currentLine.value = lines.length
      currentColumn.value = lines[lines.length - 1].length + 1
    }
    
    const syncScroll = () => {
      if (highlightLayer.value && editor.value) {
        highlightLayer.value.scrollTop = editor.value.scrollTop
        highlightLayer.value.scrollLeft = editor.value.scrollLeft
      }
    }
    
    const performSearch = async () => {
      if (!searchQuery.value || !activeFile.value) {
        searchResults.value = []
        return
      }
      
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/search', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: activeFile.value.content,
            query: searchQuery.value,
            case_sensitive: searchCaseSensitive.value,
            whole_word: searchWholeWord.value,
            regex: searchRegex.value
          })
        })
        searchResults.value = await res.json()
        currentSearchIndex.value = 0
      } catch (e) {
        console.error('Search failed:', e)
      }
    }
    
    const replaceNext = async () => {
      if (!searchQuery.value || !replaceQuery.value || !activeFile.value) return
      
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/replace', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: activeFile.value.content,
            search: searchQuery.value,
            replace: replaceQuery.value,
            case_sensitive: searchCaseSensitive.value,
            whole_word: searchWholeWord.value,
            regex: searchRegex.value
          })
        })
        const result = await res.json()
        if (result.content) {
          activeFile.value.content = result.content
          activeFile.value.modified = true
          performSearch()
        }
      } catch (e) {
        console.error('Replace failed:', e)
      }
    }
    
    const replaceAll = async () => {
      if (!searchQuery.value || !replaceQuery.value || !activeFile.value) return
      
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/replace', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: activeFile.value.content,
            search: searchQuery.value,
            replace: replaceQuery.value,
            case_sensitive: searchCaseSensitive.value,
            whole_word: searchWholeWord.value,
            regex: searchRegex.value
          })
        })
        const result = await res.json()
        if (result.content) {
          activeFile.value.content = result.content
          activeFile.value.modified = true
          performSearch()
        }
      } catch (e) {
        console.error('Replace all failed:', e)
      }
    }
    
    const fetchCompletions = async () => {
      if (!activeFile.value || !editor.value) return
      
      const cursorPos = editor.value.selectionStart
      
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/completions', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: activeFile.value.content,
            filename: activeFile.value.name,
            cursor_position: cursorPos
          })
        })
        completions.value = await res.json()
        selectedCompletion.value = 0
        
        const rect = editor.value.getBoundingClientRect()
        const lineHeight = editorSettings.value.fontSize * 1.5
        const lines = activeFile.value.content.substring(0, cursorPos).split('\n')
        const top = (lines.length - 1) * lineHeight - editor.value.scrollTop
        const left = (lines[lines.length - 1].length * 8) - editor.value.scrollLeft
        
        completionStyle.value = {
          top: `${Math.min(top + 30, rect.height - 200)}px`,
          left: `${Math.min(left, rect.width - 250)}px`
        }
      } catch (e) {
        console.error('Failed to fetch completions:', e)
      }
    }
    
    const applyCompletion = (item) => {
      if (!editor.value || !activeFile.value) return
      
      const cursorPos = editor.value.selectionStart
      const textBefore = activeFile.value.content.substring(0, cursorPos)
      const wordMatch = textBefore.match(/([a-zA-Z_][a-zA-Z0-9_]*)$/)
      const wordStart = wordMatch ? cursorPos - wordMatch[1].length : cursorPos
      
      activeFile.value.content = 
        activeFile.value.content.substring(0, wordStart) + 
        item.text + 
        activeFile.value.content.substring(cursorPos)
      
      nextTick(() => {
        editor.value.selectionStart = editor.value.selectionEnd = wordStart + item.text.length
        editor.value.focus()
      })
      
      completions.value = []
    }
    
    const fetchOutline = async (content, language) => {
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/outline', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, language })
        })
        fileOutline.value = await res.json()
      } catch (e) {
        fileOutline.value = []
      }
    }
    
    const goToLine = (lineNum) => {
      if (!editor.value || !activeFile.value) return
      const lines = activeFile.value.content.split('\n')
      let pos = 0
      for (let i = 0; i < lineNum - 1 && i < lines.length; i++) {
        pos += lines[i].length + 1
      }
      editor.value.focus()
      editor.value.setSelectionRange(pos, pos)
      currentLine.value = lineNum
    }
    
    const saveCurrentFile = async () => {
      if (!activeFile.value) return
      
      try {
        const token = store.state.token
        await fetch('/api/file-manager/file/write', {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_path: activeFile.value.path,
            content: activeFile.value.content
          })
        })
        activeFile.value.modified = false
      } catch (e) {
        console.error('Save failed:', e)
      }
    }
    
    const saveSettings = async () => {
      try {
        const token = store.state.token
        await fetch('/api/editor/settings', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(editorSettings.value)
        })
        showSettings.value = false
      } catch (e) {
        console.error('Failed to save settings:', e)
      }
    }
    
    const loadSettings = async () => {
      try {
        const token = store.state.token
        const res = await fetch('/api/editor/settings', { headers: { 'Authorization': `Bearer ${token}` } })
        const settings = await res.json()
        Object.assign(editorSettings.value, settings)
      } catch (e) {}
    }
    
    onMounted(() => {
      loadSettings()
    })
    
    return {
      openFiles,
      activeFile,
      editor,
      highlightLayer,
      showSearchPanel,
      showReplacePanel,
      showSettings,
      searchQuery,
      replaceQuery,
      searchCaseSensitive,
      searchWholeWord,
      searchRegex,
      searchResults,
      currentSearchIndex,
      currentLine,
      currentColumn,
      completions,
      selectedCompletion,
      completionStyle,
      fileOutline,
      editorSettings,
      lineCount,
      highlightedCode,
      getFileIcon,
      getFileIconClass,
      switchFile,
      closeFile,
      onContentChange,
      handleKeydown,
      updateCurrentLine,
      syncScroll,
      performSearch,
      replaceNext,
      replaceAll,
      applyCompletion,
      goToLine,
      saveCurrentFile,
      saveSettings
    }
  }
}
</script>

<style scoped>
.code-editor-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--spacing-2);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.file-tabs {
  display: flex;
  overflow-x: auto;
  gap: 2px;
}

.file-tab {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-tertiary);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast) var(--ease-out);
}

.file-tab:hover { background: var(--bg-secondary); }
.file-tab.active { background: var(--bg-primary); border-bottom: 2px solid var(--primary-500); }
.file-tab.modified .file-name { font-style: italic; }

.file-icon { font-size: var(--font-size-xs); font-weight: bold; width: 20px; text-align: center; }
.icon-js { color: #f7df1e; }
.icon-ts { color: #3178c6; }
.icon-py { color: #3776ab; }
.icon-html { color: #e34c26; }
.icon-css { color: #264de4; }
.icon-json { color: #cbcb41; }
.icon-vue { color: #42b883; }

.file-name { font-size: var(--font-size-sm); color: var(--text-primary); }
.modified-indicator { color: var(--warning-500); font-size: 10px; }
.close-tab { 
  width: 16px; height: 16px; 
  border: none; background: transparent; 
  color: var(--text-tertiary); cursor: pointer;
  border-radius: var(--radius-sm);
}
.close-tab:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.header-actions { display: flex; gap: var(--spacing-2); padding: var(--spacing-2); }

.editor-body { flex: 1; display: flex; overflow: hidden; }

.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
}

.sidebar-section { padding: var(--spacing-3); }
.sidebar-section h4 { margin: 0 0 var(--spacing-2); font-size: var(--font-size-xs); color: var(--text-tertiary); text-transform: uppercase; }

.outline-list { display: flex; flex-direction: column; gap: var(--spacing-1); }
.outline-item { 
  display: flex; align-items: center; gap: var(--spacing-2); 
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--font-size-xs);
}
.outline-item:hover { background: var(--bg-tertiary); }
.outline-icon { color: var(--primary-500); font-weight: bold; }
.outline-name { color: var(--text-primary); flex: 1; }
.outline-line { color: var(--text-tertiary); }

.main-editor { flex: 1; display: flex; flex-direction: column; position: relative; }

.search-replace-panel {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-3);
  position: relative;
}

.search-row, .replace-row { display: flex; align-items: center; gap: var(--spacing-2); margin-bottom: var(--spacing-2); }
.search-input { 
  flex: 1; padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}
.checkbox-label { 
  display: flex; align-items: center; gap: var(--spacing-1);
  font-size: var(--font-size-xs); color: var(--text-secondary);
  cursor: pointer;
}
.search-count { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.close-panel { 
  position: absolute; top: var(--spacing-2); right: var(--spacing-2);
  width: 24px; height: 24px; border: none; background: transparent;
  color: var(--text-tertiary); cursor: pointer; font-size: 18px;
}

.editor-container {
  flex: 1; display: flex; position: relative; overflow: hidden;
  background: #1e1e1e;
}

.line-numbers {
  width: 50px; background: #252526;
  padding: var(--spacing-2) 0;
  text-align: right;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  color: #858585;
  user-select: none;
  overflow: hidden;
}

.line-number { padding: 0 var(--spacing-2); }
.line-number.active { color: #c6c6c6; background: #37373d; }

.code-textarea {
  flex: 1; padding: var(--spacing-2);
  background: transparent;
  border: none;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  resize: none;
  outline: none;
  caret-color: #fff;
  white-space: pre;
  overflow: auto;
  position: relative;
  z-index: 1;
}

.syntax-highlight {
  position: absolute;
  top: 0; left: 50px; right: 0; bottom: 0;
  padding: var(--spacing-2);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  white-space: pre;
  overflow: auto;
  pointer-events: none;
  color: transparent;
}

.syntax-highlight :deep(.keyword) { color: #569cd6; }
.syntax-highlight :deep(.string) { color: #ce9178; }
.syntax-highlight :deep(.number) { color: #b5cea8; }
.syntax-highlight :deep(.comment) { color: #6a9955; }

.no-file-open {
  flex: 1; display: flex; align-items: center; justify-content: center;
  color: var(--text-tertiary);
}

.completion-panel {
  position: absolute;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  min-width: 200px;
}

.completion-item {
  display: flex; align-items: center; gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  cursor: pointer;
  font-size: var(--font-size-sm);
}
.completion-item:hover, .completion-item.selected { background: var(--bg-tertiary); }
.completion-type { 
  width: 18px; height: 18px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: bold; color: white;
}
.completion-type.keyword { background: #569cd6; }
.completion-type.builtin { background: #dcdcaa; }
.completion-type.variable { background: #4ec9b0; }
.completion-type.method { background: #c586c0; }
.completion-text { color: var(--text-primary); }

.editor-footer {
  display: flex; justify-content: space-between;
  padding: var(--spacing-1) var(--spacing-4);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.footer-left, .footer-right { display: flex; gap: var(--spacing-4); }

.settings-modal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  padding: var(--spacing-6);
  width: 400px;
}

.modal-content h3 { margin: 0 0 var(--spacing-4); color: var(--text-primary); }

.settings-form { display: flex; flex-direction: column; gap: var(--spacing-4); }
.form-group { display: flex; align-items: center; gap: var(--spacing-3); }
.form-group label { flex: 1; font-size: var(--font-size-sm); color: var(--text-secondary); }
.form-group input[type="number"], .form-group select {
  width: 80px; padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-actions { display: flex; gap: var(--spacing-2); margin-top: var(--spacing-4); justify-content: flex-end; }

.btn {
  display: inline-flex; align-items: center; gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-3);
  border: none; border-radius: var(--radius-md);
  font-size: var(--font-size-sm); cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.btn-primary { background: var(--primary-500); color: white; }
.btn-primary:hover { background: var(--primary-600); }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }
.btn-secondary:hover { background: var(--bg-secondary); }
.btn-sm { padding: var(--spacing-1) var(--spacing-2); font-size: var(--font-size-xs); }
</style>
