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
        <button class="open-tab-btn" @click="openFileBrowser" :title="$t('editor.openFile')">
          <svg viewBox="0 0 24 24" width="16" height="16"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" fill="currentColor"/></svg>
        </button>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="openFileBrowser">
          <svg viewBox="0 0 24 24"><path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z" fill="currentColor"/></svg>
          {{ $t('editor.openFile') }}
        </button>
        <button class="btn btn-secondary" @click="saveCurrentFile" :disabled="!activeFile">
          <svg viewBox="0 0 24 24"><path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z" fill="currentColor"/></svg>
          {{ $t('common.save') }}
        </button>
        <button class="btn btn-secondary" @click="triggerFind" :disabled="!activeFile">
          <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="currentColor"/></svg>
          {{ $t('editor.find') }}
        </button>
        <button class="btn btn-secondary" @click="triggerReplace" :disabled="!activeFile">
          <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0020 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 004 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z" fill="currentColor"/></svg>
          {{ $t('editor.replace') }}
        </button>
        <button class="btn btn-secondary" @click="formatDocument" :disabled="!activeFile">
          <svg viewBox="0 0 24 24"><path d="M3 5h18v2H3V5zm0 6h12v2H3v-2zm0 6h18v2H3v-2zm14-6l4 4-4 4v-3h-6v-2h6v-3z" fill="currentColor"/></svg>
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
              v-for="(item, idx) in fileOutline"
              :key="idx"
              class="outline-item"
              @click="goToLine(item.line)"
            >
              <span class="outline-icon" :class="item.type">{{ item.type === 'function' ? 'ƒ' : item.type === 'class' ? 'C' : 'H' }}</span>
              <span class="outline-name">{{ item.name }}</span>
              <span class="outline-line">:{{ item.line }}</span>
            </div>
            <div v-if="activeFile && fileOutline.length === 0" class="outline-empty">
              {{ $t('editor.noOutline') }}
            </div>
          </div>
        </div>
      </div>

      <div class="main-editor">
        <div class="monaco-container" ref="monacoContainer"></div>
        <div v-if="!activeFile" class="no-file-open">
          <div class="no-file-content">
            <svg viewBox="0 0 24 24" width="48" height="48"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z" fill="currentColor" opacity="0.4"/></svg>
            <p>{{ $t('editor.noFileOpen') }}</p>
            <button class="btn btn-primary" @click="openFileBrowser">{{ $t('editor.openFile') }}</button>
          </div>
        </div>
      </div>
    </div>

    <div class="editor-footer">
      <div class="footer-left">
        <span v-if="activeFile">{{ activeFile.language }}</span>
        <span v-if="activeFile">UTF-8</span>
        <span v-if="activeFile">Ln {{ currentLine }}, Col {{ currentColumn }}</span>
        <span v-if="activeFile">{{ selectionInfo }}</span>
      </div>
      <div class="footer-right">
        <span v-if="activeFile?.modified">{{ $t('editor.modified') }}</span>
        <span v-if="autoSaveIndicator" class="autosave-status">{{ autoSaveIndicator }}</span>
      </div>
    </div>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="settings-modal" @click.self="showSettings = false">
      <div class="modal-content">
        <h3>{{ $t('editor.settings') }}</h3>
        <div class="settings-form">
          <div class="form-group">
            <label>{{ $t('editor.theme') }}</label>
            <select v-model="editorSettings.theme">
              <option value="xiaopeng-dark">xiaopeng Dark</option>
              <option value="vs-dark">VS Dark</option>
              <option value="vs">VS Light</option>
              <option value="hc-black">High Contrast Black</option>
            </select>
          </div>
          <div class="form-group">
            <label>{{ $t('editor.fontSize') }}</label>
            <input type="number" v-model.number="editorSettings.fontSize" min="10" max="32" />
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
              <input type="checkbox" v-model="editorSettings.insertSpaces" />
              {{ $t('editor.insertSpaces') }}
            </label>
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
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.bracketPairColorization" />
              {{ $t('editor.bracketColorization') }}
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.highlightActiveLine" />
              {{ $t('editor.activeLine') }}
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.showInvisibles" />
              {{ $t('editor.showInvisibles') }}
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.scrollBeyondLastLine" />
              {{ $t('editor.scrollBeyondLastLine') }}
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editorSettings.autoSave" />
              {{ $t('editor.autoSave') }}
            </label>
          </div>
          <div class="form-group" v-if="editorSettings.autoSave">
            <label>{{ $t('editor.autoSaveDelay') }}</label>
            <input type="number" v-model.number="editorSettings.autoSaveDelay" min="500" max="10000" step="500" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="saveSettings">{{ $t('common.save') }}</button>
          <button class="btn btn-secondary" @click="showSettings = false">{{ $t('common.close') }}</button>
        </div>
      </div>
    </div>

    <!-- File Browser Modal -->
    <div v-if="showFileBrowser" class="settings-modal" @click.self="showFileBrowser = false">
      <div class="modal-content file-browser">
        <h3>{{ $t('editor.openFile') }}</h3>
        <div class="breadcrumb">
          <span
            v-for="(crumb, idx) in breadcrumbs"
            :key="idx"
            class="breadcrumb-item"
            @click="browseTo(crumb.path)"
          >{{ crumb.name }}<span v-if="idx < breadcrumbs.length - 1" class="breadcrumb-sep">/</span></span>
        </div>
        <div class="file-browser-list">
          <div v-if="browserLoading" class="browser-loading">{{ $t('common.loading') }}</div>
          <template v-else>
            <div v-if="currentBrowserParent" class="browser-item dir-item" @click="browseTo(currentBrowserParent)">
              <span class="browser-icon">📁</span>
              <span class="browser-name">..</span>
            </div>
            <div
              v-for="dir in browserDirectories"
              :key="dir.path"
              class="browser-item dir-item"
              @click="browseTo(dir.path)"
            >
              <span class="browser-icon">📁</span>
              <span class="browser-name">{{ dir.name }}</span>
            </div>
            <div
              v-for="file in browserFiles"
              :key="file.path"
              class="browser-item file-item"
              @click="openFileFromBrowser(file)"
            >
              <span class="browser-icon">{{ getFileIcon(file.name) }}</span>
              <span class="browser-name">{{ file.name }}</span>
              <span class="browser-size">{{ formatFileSize(file.size) }}</span>
            </div>
            <div v-if="browserDirectories.length === 0 && browserFiles.length === 0 && !currentBrowserParent" class="browser-empty">
              {{ $t('editor.noFilesInDir') }}
            </div>
          </template>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showFileBrowser = false">{{ $t('common.close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

// Monaco Web Worker 配置（Vite 环境）
self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker()
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
  }
}

// 文件扩展名 → Monaco 语言 ID 映射
const EXTENSION_TO_LANGUAGE = {
  js: 'javascript', jsx: 'javascript', mjs: 'javascript', cjs: 'javascript',
  ts: 'typescript', tsx: 'typescript',
  py: 'python', pyw: 'python', pyi: 'python',
  html: 'html', htm: 'html', xhtml: 'html',
  css: 'css', scss: 'scss', less: 'less',
  json: 'json', jsonc: 'json',
  md: 'markdown', markdown: 'markdown',
  sql: 'sql',
  vue: 'html',
  sh: 'shell', bash: 'shell', zsh: 'shell',
  yml: 'yaml', yaml: 'yaml',
  xml: 'xml', svg: 'xml',
  java: 'java',
  c: 'c', h: 'c',
  cpp: 'cpp', cc: 'cpp', cxx: 'cpp', hpp: 'cpp',
  go: 'go',
  rs: 'rust',
  php: 'php',
  rb: 'ruby',
  swift: 'swift',
  kt: 'kotlin', kts: 'kotlin',
  bat: 'bat', cmd: 'bat',
  ini: 'ini', conf: 'ini',
  dockerfile: 'dockerfile',
}

// 后端补全类型 → Monaco CompletionItemKind
const COMPLETION_KIND_MAP = {
  keyword: monaco.languages.CompletionItemKind.Keyword,
  builtin: monaco.languages.CompletionItemKind.Function,
  variable: monaco.languages.CompletionItemKind.Variable,
  method: monaco.languages.CompletionItemKind.Method,
}

// 后端支持的语言（用于注册补全提供器）
const BACKEND_LANGUAGES = [
  'javascript', 'typescript', 'python', 'java', 'html',
  'css', 'json', 'yaml', 'sql', 'shell', 'xml', 'markdown'
]

function getMonacoLanguage(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  return EXTENSION_TO_LANGUAGE[ext] || 'plaintext'
}

// 定义自定义主题（匹配 iOS 26 暗色设计系统）
function defineCustomTheme() {
  monaco.editor.defineTheme('xiaopeng-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: '569cd6' },
      { token: 'string', foreground: 'ce9178' },
      { token: 'number', foreground: 'b5cea8' },
      { token: 'type', foreground: '4ec9b0' },
      { token: 'function', foreground: 'dcdcaa' },
      { token: 'variable', foreground: '9cdcfe' },
      { token: 'tag', foreground: '569cd6' },
      { token: 'attribute.name', foreground: '9cdcfe' },
      { token: 'attribute.value', foreground: 'ce9178' },
    ],
    colors: {
      'editor.background': '#1C1C1E',
      'editor.foreground': '#FFFFFF',
      'editorLineNumber.foreground': '#8E8E93',
      'editorLineNumber.activeForeground': '#FFFFFF',
      'editor.selectionBackground': '#007AFF40',
      'editor.inactiveSelectionBackground': '#007AFF20',
      'editor.lineHighlightBackground': '#2C2C2E',
      'editor.lineHighlightBorder': '#00000000',
      'editorCursor.foreground': '#007AFF',
      'editorIndentGuide.background': '#3A3A3C',
      'editorIndentGuide.activeBackground': '#007AFF',
      'editorGutter.background': '#1C1C1E',
      'editorWidget.background': '#2C2C2E',
      'editorWidget.border': '#48484A',
      'editorSuggestWidget.background': '#2C2C2E',
      'editorSuggestWidget.border': '#48484A',
      'editorSuggestWidget.selectedBackground': '#007AFF40',
      'editorSuggestWidget.highlightForeground': '#007AFF',
      'editorHoverWidget.background': '#2C2C2E',
      'editorHoverWidget.border': '#48484A',
      'minimap.background': '#1C1C1E',
      'scrollbarSlider.background': '#48484A60',
      'scrollbarSlider.hoverBackground': '#48484A90',
      'scrollbarSlider.activeBackground': '#48484ACC',
      'editorBracketMatch.background': '#007AFF30',
      'editorBracketMatch.border': '#007AFF',
      'editor.findMatchBackground': '#FFCC0040',
      'editor.findMatchHighlightBackground': '#FFCC0020',
      'editorOverviewRuler.border': '#00000000',
    }
  })
}

export default {
  name: 'CodeEditor',
  setup() {
    const store = useStore()
    const { t } = useI18n()

    // ========== 响应式状态 ==========
    const openFiles = ref([])
    const activeFile = ref(null)
    const monacoContainer = ref(null)

    const showSettings = ref(false)
    const showFileBrowser = ref(false)

    const currentLine = ref(1)
    const currentColumn = ref(1)
    const selectionInfo = ref('')
    const autoSaveIndicator = ref('')

    const fileOutline = ref([])

    // 文件浏览器状态
    const browserLoading = ref(false)
    const browserDirectories = ref([])
    const browserFiles = ref([])
    const currentBrowserPath = ref('')
    const whitelistDirs = ref([])

    // 编辑器设置（与后端结构一致）
    const editorSettings = ref({
      theme: 'xiaopeng-dark',
      fontSize: 14,
      fontFamily: "'SF Mono', SFMono-Regular, ui-monospace, Menlo, Monaco, 'Cascadia Code', 'Roboto Mono', monospace",
      tabSize: 4,
      insertSpaces: true,
      wordWrap: true,
      lineNumbers: 'on',
      minimap: true,
      autoSave: true,
      autoSaveDelay: 1000,
      formatOnSave: false,
      bracketPairColorization: true,
      highlightActiveLine: true,
      showInvisibles: false,
      scrollBeyondLastLine: false
    })

    // ========== Monaco 编辑器实例 ==========
    let editor = null
    let models = new Map() // path -> ITextModel
    let contentChangeDisposables = new Map() // path -> IDisposable
    let completionProviders = [] // IDisposable[]
    let cursorDisposable = null
    let saveCommandDisposable = null
    let resizeObserver = null
    let autoSaveTimers = new Map() // path -> timeoutId
    let outlineTimer = null

    // ========== 计算属性 ==========
    const breadcrumbs = computed(() => {
      if (!currentBrowserPath.value) {
        return whitelistDirs.value.map(d => ({ name: d.name || d.path, path: d.path }))
      }
      const parts = currentBrowserPath.value.replace(/\\/g, '/').split('/').filter(Boolean)
      const crumbs = []
      let acc = ''
      // 查找所属的白名单根
      const root = whitelistDirs.value.find(d => {
        return currentBrowserPath.value.replace(/\\/g, '/').startsWith(d.path.replace(/\\/g, '/'))
      })
      if (root) {
        crumbs.push({ name: root.name || root.path, path: root.path })
        const rootParts = root.path.replace(/\\/g, '/').split('/').filter(Boolean)
        parts.slice(rootParts.length).forEach(part => {
          acc = root.path.replace(/\\/g, '/') + '/' + parts.slice(rootParts.length, parts.indexOf(part) + 1).join('/')
          acc = acc.replace(/\//g, '\\')
          crumbs.push({ name: part, path: acc })
        })
      } else {
        parts.forEach((part, idx) => {
          acc = (idx === 0 ? '' : acc) + (idx === 0 && /^[a-zA-Z]:$/.test(part) ? part + '\\' : '/' + part)
          crumbs.push({ name: part, path: idx === 0 ? part + '\\' : acc })
        })
      }
      return crumbs
    })

    const currentBrowserParent = computed(() => {
      if (!currentBrowserPath.value) return null
      // 查找所属白名单根
      const root = whitelistDirs.value.find(d => {
        return currentBrowserPath.value.replace(/\\/g, '/').startsWith(d.path.replace(/\\/g, '/'))
      })
      if (root && currentBrowserPath.value.replace(/\\/g, '/') === root.path.replace(/\\/g, '/')) {
        return null // 已在根目录
      }
      const normalized = currentBrowserPath.value.replace(/\\/g, '/')
      const idx = normalized.lastIndexOf('/')
      if (idx <= 0) return null
      const parent = normalized.substring(0, idx)
      return parent.replace(/\//g, '\\')
    })

    // ========== 工具函数 ==========
    const getFileIcon = (filename) => {
      const ext = filename.split('.').pop().toLowerCase()
      const icons = {
        js: 'JS', jsx: 'JS', ts: 'TS', tsx: 'TS',
        py: 'PY', java: 'JV', html: 'H', css: 'C',
        json: '{ }', md: 'MD', txt: 'T', sql: 'DB',
        vue: 'V', sh: 'SH', yml: 'Y', yaml: 'Y',
        xml: 'X', go: 'GO', rs: 'RS', php: 'PHP',
        cpp: 'C++', c: 'C', rb: 'RB', swift: 'SW',
        kt: 'KT', ini: 'I', conf: 'I', bat: 'BT'
      }
      return icons[ext] || 'F'
    }

    const getFileIconClass = (filename) => {
      const ext = filename.split('.').pop().toLowerCase()
      const classes = {
        js: 'icon-js', jsx: 'icon-js', ts: 'icon-ts', tsx: 'icon-ts',
        py: 'icon-py', html: 'icon-html', css: 'icon-css',
        json: 'icon-json', md: 'icon-md', sql: 'icon-sql', vue: 'icon-vue',
        go: 'icon-go', rs: 'icon-rs', php: 'icon-php', java: 'icon-java'
      }
      return classes[ext] || 'icon-default'
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / 1024 / 1024).toFixed(1) + ' MB'
    }

    const authHeaders = () => ({
      'Authorization': `Bearer ${store.state.token}`,
      'Content-Type': 'application/json'
    })

    // ========== Monaco 编辑器初始化 ==========
    const initEditor = () => {
      defineCustomTheme()
      monaco.editor.setTheme(editorSettings.value.theme || 'xiaopeng-dark')

      editor = monaco.editor.create(monacoContainer.value, {
        theme: editorSettings.value.theme || 'xiaopeng-dark',
        fontSize: editorSettings.value.fontSize,
        fontFamily: editorSettings.value.fontFamily,
        fontLigatures: true,
        tabSize: editorSettings.value.tabSize,
        insertSpaces: editorSettings.value.insertSpaces,
        wordWrap: editorSettings.value.wordWrap ? 'on' : 'off',
        minimap: { enabled: editorSettings.value.minimap },
        lineNumbers: editorSettings.value.lineNumbers || 'on',
        'bracketPairColorization.enabled': editorSettings.value.bracketPairColorization,
        'highlightActiveLine': editorSettings.value.highlightActiveLine,
        renderWhitespace: editorSettings.value.showInvisibles ? 'all' : 'none',
        scrollBeyondLastLine: editorSettings.value.scrollBeyondLastLine,
        automaticLayout: false, // 手动管理 layout
        smoothScrolling: true,
        cursorSmoothCaretAnimation: 'on',
        cursorBlinking: 'smooth',
        renderLineHighlight: editorSettings.value.highlightActiveLine ? 'all' : 'none',
        roundedSelection: true,
        padding: { top: 8, bottom: 8 },
        scrollbar: {
          verticalScrollbarSize: 10,
          horizontalScrollbarSize: 10,
          useShadows: false,
        },
        fixedOverflowWidgets: true,
      })

      // 光标位置变化 → 更新状态栏
      cursorDisposable = editor.onDidChangeCursorPosition(() => {
        updateCursorStatus()
      })

      // 选中区域变化 → 更新选中信息
      editor.onDidChangeCursorSelection(() => {
        updateSelectionStatus()
      })

      // Ctrl/Cmd+S → 保存
      saveCommandDisposable = editor.addCommand(
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
        () => saveCurrentFile()
      )

      // ResizeObserver → 自适应布局
      resizeObserver = new ResizeObserver(() => {
        if (editor) editor.layout()
      })
      resizeObserver.observe(monacoContainer.value)

      // 注册补全提供器
      registerCompletionProviders()
    }

    const updateCursorStatus = () => {
      if (!editor) return
      const pos = editor.getPosition()
      if (pos) {
        currentLine.value = pos.lineNumber
        currentColumn.value = pos.column
      }
    }

    const updateSelectionStatus = () => {
      if (!editor) return
      const selection = editor.getSelection()
      if (selection && !selection.isEmpty()) {
        const lineCount = selection.endLineNumber - selection.startLineNumber + 1
        const charCount = editor.getModel()?.getValueInRange(selection).length || 0
        selectionInfo.value = `${lineCount}L ${charCount}C`
      } else {
        selectionInfo.value = ''
      }
    }

    // ========== 补全提供器（对接后端 /api/editor/completions） ==========
    const registerCompletionProviders = () => {
      BACKEND_LANGUAGES.forEach(lang => {
        const provider = monaco.languages.registerCompletionItemProvider(lang, {
          triggerCharacters: ['.', '_', '$'],
          async provideCompletionItems(model, position) {
            const textUntilPosition = model.getValueInRange({
              startLineNumber: 1,
              startColumn: 1,
              endLineNumber: position.lineNumber,
              endColumn: position.column
            })
            const cursorPosition = textUntilPosition.length
            const word = model.getWordUntilPosition(position)

            try {
              const res = await fetch('/api/editor/completions', {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify({
                  code: model.getValue(),
                  filename: model.uri.path.split('/').pop() || 'untitled',
                  cursor_position: cursorPosition
                })
              })
              if (!res.ok) return { suggestions: [] }
              const completions = await res.json()
              return {
                suggestions: completions.map(c => ({
                  label: c.text,
                  kind: COMPLETION_KIND_MAP[c.type] || monaco.languages.CompletionItemKind.Text,
                  insertText: c.text,
                  detail: c.type,
                  range: {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: word.startColumn,
                    endColumn: word.endColumn
                  }
                }))
              }
            } catch {
              return { suggestions: [] }
            }
          }
        })
        completionProviders.push(provider)
      })
    }

    // ========== 多文件模型管理 ==========
    const getOrCreateModel = (file) => {
      const uri = monaco.Uri.file(file.path)
      let model = models.get(file.path)
      if (!model) {
        model = monaco.editor.createModel(
          file.content || '',
          getMonacoLanguage(file.name),
          uri
        )
        models.set(file.path, model)

        // 监听内容变化
        const disposable = model.onDidChangeContent(() => {
          const f = openFiles.value.find(f => f.path === file.path)
          if (f) {
            f.content = model.getValue()
            const savedContent = f.savedContent || ''
            const modified = model.getValue() !== savedContent
            if (f.modified !== modified) {
              f.modified = modified
            }
            // 自动保存
            if (editorSettings.value.autoSave && modified) {
              scheduleAutoSave(file.path)
            }
            // 防抖更新大纲
            scheduleOutlineUpdate(f)
          }
        })
        contentChangeDisposables.set(file.path, disposable)
      }
      return model
    }

    // ========== 文件操作 ==========
    const openFile = (fileData) => {
      // 检查是否已打开
      const existing = openFiles.value.find(f => f.path === fileData.path)
      if (existing) {
        switchFile(existing)
        return
      }

      const file = {
        path: fileData.path,
        name: fileData.name || fileData.path.split(/[/\\]/).pop(),
        content: fileData.content || '',
        savedContent: fileData.content || '',
        modified: false,
        language: getMonacoLanguage(fileData.name || fileData.path)
      }
      openFiles.value.push(file)
      switchFile(file)
    }

    const switchFile = (file) => {
      if (!editor) return

      // 保存当前文件的光标位置到会话
      if (activeFile.value) {
        saveFileSession(activeFile.value.path)
      }

      activeFile.value = file
      const model = getOrCreateModel(file)
      editor.setModel(model)

      // 恢复光标位置（从会话）
      restoreFileSession(file.path)

      // 更新大纲
      fetchOutline(file.content, file.language)

      nextTick(() => {
        if (editor) {
          editor.layout()
          editor.focus()
        }
      })
    }

    const closeFile = (file) => {
      // 取消自动保存定时器
      const timer = autoSaveTimers.get(file.path)
      if (timer) {
        clearTimeout(timer)
        autoSaveTimers.delete(file.path)
      }

      const idx = openFiles.value.findIndex(f => f.path === file.path)
      if (idx > -1) {
        openFiles.value.splice(idx, 1)
      }

      // 销毁模型
      const model = models.get(file.path)
      if (model) {
        model.dispose()
        models.delete(file.path)
      }
      const disposable = contentChangeDisposables.get(file.path)
      if (disposable) {
        disposable.dispose()
        contentChangeDisposables.delete(file.path)
      }

      // 关闭会话
      closeFileSession(file.path)

      if (activeFile.value?.path === file.path) {
        activeFile.value = openFiles.value[Math.max(0, idx - 1)] || null
        if (activeFile.value) {
          switchFile(activeFile.value)
        } else if (editor) {
          editor.setModel(monaco.editor.createModel('', 'plaintext'))
        }
      }
    }

    const saveCurrentFile = async () => {
      if (!activeFile.value || !editor) return

      try {
        const model = editor.getModel()
        const content = model ? model.getValue() : activeFile.value.content

        await fetch('/api/file-manager/file/write', {
          method: 'PUT',
          headers: authHeaders(),
          body: JSON.stringify({
            file_path: activeFile.value.path,
            content: content
          })
        })

        activeFile.value.modified = false
        activeFile.value.savedContent = content
        autoSaveIndicator.value = t('editor.saved')
        setTimeout(() => { autoSaveIndicator.value = '' }, 2000)
      } catch (e) {
        console.error('Save failed:', e)
        autoSaveIndicator.value = t('editor.saveFailed')
        setTimeout(() => { autoSaveIndicator.value = '' }, 3000)
      }
    }

    const scheduleAutoSave = (filePath) => {
      const existing = autoSaveTimers.get(filePath)
      if (existing) clearTimeout(existing)

      const timer = setTimeout(() => {
        autoSaveTimers.delete(filePath)
        if (activeFile.value?.path === filePath) {
          saveCurrentFile()
        }
      }, editorSettings.value.autoSaveDelay || 1000)

      autoSaveTimers.set(filePath, timer)
    }

    // ========== 大纲（对接后端 /api/editor/outline） ==========
    const fetchOutline = async (content, language) => {
      try {
        const res = await fetch('/api/editor/outline', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ content, language })
        })
        if (res.ok) {
          fileOutline.value = await res.json()
        } else {
          fileOutline.value = []
        }
      } catch {
        fileOutline.value = []
      }
    }

    const scheduleOutlineUpdate = (file) => {
      if (outlineTimer) clearTimeout(outlineTimer)
      outlineTimer = setTimeout(() => {
        if (activeFile.value?.path === file.path) {
          fetchOutline(file.content, file.language)
        }
      }, 800)
    }

    const goToLine = (lineNum) => {
      if (!editor) return
      editor.revealLineInCenter(lineNum)
      editor.setPosition({ lineNumber: lineNum, column: 1 })
      editor.focus()
    }

    // ========== 搜索/替换（使用 Monaco 原生功能） ==========
    const triggerFind = () => {
      if (!editor) return
      const action = editor.getAction('actions.find')
      if (action) action.run()
    }

    const triggerReplace = () => {
      if (!editor) return
      const action = editor.getAction('editor.action.startFindReplaceAction')
      if (action) action.run()
    }

    const formatDocument = () => {
      if (!editor) return
      const action = editor.getAction('editor.action.formatDocument')
      if (action) action.run()
    }

    // ========== 设置（对接后端 /api/editor/settings） ==========
    const applySettings = () => {
      if (!editor) return
      const s = editorSettings.value
      monaco.editor.setTheme(s.theme || 'xiaopeng-dark')
      editor.updateOptions({
        fontSize: s.fontSize,
        fontFamily: s.fontFamily,
        tabSize: s.tabSize,
        insertSpaces: s.insertSpaces,
        wordWrap: s.wordWrap ? 'on' : 'off',
        minimap: { enabled: s.minimap },
        lineNumbers: s.lineNumbers || 'on',
        'bracketPairColorization.enabled': s.bracketPairColorization,
        'highlightActiveLine': s.highlightActiveLine,
        renderWhitespace: s.showInvisibles ? 'all' : 'none',
        scrollBeyondLastLine: s.scrollBeyondLastLine,
        renderLineHighlight: s.highlightActiveLine ? 'all' : 'none',
      })
    }

    const saveSettings = async () => {
      applySettings()
      try {
        await fetch('/api/editor/settings', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(editorSettings.value)
        })
        showSettings.value = false
      } catch (e) {
        console.error('Failed to save settings:', e)
      }
    }

    const loadSettings = async () => {
      try {
        const res = await fetch('/api/editor/settings', { headers: { 'Authorization': `Bearer ${store.state.token}` } })
        if (res.ok) {
          const settings = await res.json()
          Object.assign(editorSettings.value, settings)
        }
      } catch {
        // 使用默认设置
      }
      applySettings()
    }

    // 实时应用设置（当设置面板中值变化时）
    watch(editorSettings, () => {
      applySettings()
    }, { deep: true })

    // ========== 文件会话（对接后端 /api/editor/sessions） ==========
    const saveFileSession = async (filePath) => {
      if (!editor) return
      const model = models.get(filePath)
      if (!model) return
      const pos = editor.getPosition()
      try {
        await fetch('/api/editor/sessions', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({
            path: filePath,
            cursor_line: pos?.lineNumber || 1,
            cursor_column: pos?.column || 1,
            scroll_top: editor.getScrollTop() || 0,
            language: getMonacoLanguage(filePath.split(/[/\\]/).pop())
          })
        })
      } catch {
        // 静默失败
      }
    }

    const restoreFileSession = async (filePath) => {
      try {
        const res = await fetch('/api/editor/sessions', { headers: { 'Authorization': `Bearer ${store.state.token}` } })
        if (!res.ok) return
        const sessions = await res.json()
        const session = sessions.find(s => s.path === filePath)
        if (session && editor) {
          const line = session.cursor_line || 1
          const col = session.cursor_column || 1
          editor.setPosition({ lineNumber: line, column: col })
          if (session.scroll_top) {
            editor.setScrollTop(session.scroll_top)
          }
          editor.revealLineInCenter(line)
        }
      } catch {
        // 静默失败
      }
    }

    const closeFileSession = async (filePath) => {
      try {
        await fetch(`/api/editor/sessions/${encodeURIComponent(filePath)}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${store.state.token}` }
        })
      } catch {
        // 静默失败
      }
    }

    // ========== 文件浏览器 ==========
    const openFileBrowser = async () => {
      showFileBrowser.value = true
      browserLoading.value = true
      try {
        const res = await fetch('/api/file-manager/whitelist-dirs', {
          headers: { 'Authorization': `Bearer ${store.state.token}` }
        })
        if (res.ok) {
          const data = await res.json()
          whitelistDirs.value = data.dirs || []
          // 默认浏览第一个白名单目录
          if (whitelistDirs.value.length > 0) {
            await browseTo(whitelistDirs.value[0].path)
          }
        }
      } catch (e) {
        console.error('Failed to load whitelist dirs:', e)
      } finally {
        browserLoading.value = false
      }
    }

    const browseTo = async (path) => {
      browserLoading.value = true
      currentBrowserPath.value = path
      try {
        const res = await fetch(`/api/file-manager/directory?path=${encodeURIComponent(path)}`, {
          headers: { 'Authorization': `Bearer ${store.state.token}` }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.status === 'success') {
            browserDirectories.value = data.directories || []
            browserFiles.value = data.files || []
          } else {
            browserDirectories.value = []
            browserFiles.value = []
          }
        }
      } catch (e) {
        console.error('Failed to browse directory:', e)
        browserDirectories.value = []
        browserFiles.value = []
      } finally {
        browserLoading.value = false
      }
    }

    const openFileFromBrowser = async (file) => {
      try {
        const res = await fetch(`/api/file-manager/file/read?path=${encodeURIComponent(file.path)}`, {
          headers: { 'Authorization': `Bearer ${store.state.token}` }
        })
        if (res.ok) {
          const data = await res.json()
          if (data.status === 'success') {
            openFile({
              path: file.path,
              name: file.name,
              content: data.content
            })
            showFileBrowser.value = false
          }
        }
      } catch (e) {
        console.error('Failed to read file:', e)
      }
    }

    // ========== 生命周期 ==========
    onMounted(() => {
      initEditor()
      loadSettings()
    })

    onUnmounted(() => {
      // 保存当前文件会话
      if (activeFile.value) {
        saveFileSession(activeFile.value.path)
      }
      // 清理自动保存定时器
      autoSaveTimers.forEach(timer => clearTimeout(timer))
      autoSaveTimers.clear()
      // 清理补全提供器
      completionProviders.forEach(d => d.dispose())
      completionProviders = []
      // 清理内容变化监听
      contentChangeDisposables.forEach(d => d.dispose())
      contentChangeDisposables.clear()
      // 清理模型
      models.forEach(m => m.dispose())
      models.clear()
      // 清理光标监听
      if (cursorDisposable) cursorDisposable.dispose()
      if (saveCommandDisposable) saveCommandDisposable.dispose()
      // 清理 ResizeObserver
      if (resizeObserver) resizeObserver.disconnect()
      // 销毁编辑器
      if (editor) editor.dispose()
      editor = null
      if (outlineTimer) clearTimeout(outlineTimer)
    })

    return {
      openFiles,
      activeFile,
      monacoContainer,
      showSettings,
      showFileBrowser,
      currentLine,
      currentColumn,
      selectionInfo,
      autoSaveIndicator,
      fileOutline,
      editorSettings,
      browserLoading,
      browserDirectories,
      browserFiles,
      breadcrumbs,
      currentBrowserParent,
      getFileIcon,
      getFileIconClass,
      formatFileSize,
      switchFile,
      closeFile,
      saveCurrentFile,
      triggerFind,
      triggerReplace,
      formatDocument,
      goToLine,
      saveSettings,
      openFileBrowser,
      browseTo,
      openFileFromBrowser,
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
  align-items: center;
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
.file-tab.active { background: #1C1C1E; border-bottom: 2px solid var(--primary-500); }
.file-tab.modified .file-name { font-style: italic; }

.open-tab-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}
.open-tab-btn:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.file-icon { font-size: var(--font-size-xs); font-weight: bold; width: 20px; text-align: center; }
.icon-js { color: #f7df1e; }
.icon-ts { color: #3178c6; }
.icon-py { color: #3776ab; }
.icon-html { color: #e34c26; }
.icon-css { color: #264de4; }
.icon-json { color: #cbcb41; }
.icon-vue { color: #42b883; }
.icon-go { color: #00add8; }
.icon-rs { color: #dea584; }
.icon-php { color: #777bb4; }
.icon-java { color: #f89820; }

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
.outline-icon { color: var(--primary-500); font-weight: bold; width: 16px; text-align: center; }
.outline-icon.function { color: #dcdcaa; }
.outline-icon.class { color: #4ec9b0; }
.outline-name { color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.outline-line { color: var(--text-tertiary); }
.outline-empty { font-size: var(--font-size-xs); color: var(--text-tertiary); padding: var(--spacing-1) var(--spacing-2); }

.main-editor { flex: 1; display: flex; flex-direction: column; position: relative; }

.monaco-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.no-file-open {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1C1C1E;
  z-index: 10;
}

.no-file-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-4);
  color: var(--text-tertiary);
}

.no-file-content p { margin: 0; font-size: var(--font-size-subhead); }

.editor-footer {
  display: flex; justify-content: space-between;
  padding: var(--spacing-1) var(--spacing-4);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.footer-left, .footer-right { display: flex; gap: var(--spacing-4); align-items: center; }
.autosave-status { color: var(--success-500); }

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
  width: 440px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h3 { margin: 0 0 var(--spacing-4); color: var(--text-primary); }

.settings-form { display: flex; flex-direction: column; gap: var(--spacing-3); }
.form-group { display: flex; align-items: center; gap: var(--spacing-3); }
.form-group label { flex: 1; font-size: var(--font-size-sm); color: var(--text-secondary); display: flex; align-items: center; gap: var(--spacing-2); }
.form-group input[type="number"], .form-group select {
  width: 100px; padding: var(--spacing-1) var(--spacing-2);
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
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary { background: var(--primary-500); color: white; }
.btn-primary:hover { background: var(--primary-600); }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); }
.btn-secondary:hover { background: var(--bg-secondary); }

/* 文件浏览器样式 */
.file-browser { width: 600px; }

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
  font-size: var(--font-size-sm);
}
.breadcrumb-item { cursor: pointer; color: var(--primary-500); }
.breadcrumb-item:hover { text-decoration: underline; }
.breadcrumb-sep { color: var(--text-tertiary); margin: 0 var(--spacing-1); }

.file-browser-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
}

.browser-loading, .browser-empty {
  padding: var(--spacing-4);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.browser-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  cursor: pointer;
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--border-color);
  transition: background var(--duration-fast) var(--ease-out);
}
.browser-item:last-child { border-bottom: none; }
.browser-item:hover { background: var(--bg-tertiary); }

.browser-icon { width: 20px; text-align: center; font-size: var(--font-size-xs); font-weight: bold; }
.browser-name { flex: 1; color: var(--text-primary); }
.browser-size { color: var(--text-tertiary); font-size: var(--font-size-xs); }
.dir-item .browser-name { color: var(--primary-500); font-weight: 500; }
</style>
