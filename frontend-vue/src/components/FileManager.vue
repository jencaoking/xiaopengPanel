<template>
  <div id="file-manager" class="page">
    <div class="page-header">
      <h2>文件管理</h2>
      <div class="page-actions">
        <button id="refresh-files-btn" class="btn btn-secondary" @click="refreshFiles">刷新</button>
        <button id="create-dir-btn" class="btn btn-secondary" @click="openCreateModal('directory')">新建目录</button>
        <button id="create-file-btn" class="btn btn-primary" @click="openCreateModal('file')">新建文件</button>
        <button id="upload-file-btn" class="btn btn-primary" @click="openUploadModal">上传文件</button>
        <button
          id="delete-file-btn"
          class="btn btn-danger"
          :disabled="selectedPaths.length === 0"
          @click="confirmBatchDelete"
        >删除</button>
        <button
          id="compress-btn"
          class="btn btn-secondary"
          :disabled="selectedPaths.length === 0"
          @click="openCompressModal"
        >压缩</button>
      </div>
    </div>

    <div class="file-manager-container">
      <!-- 左侧目录树 -->
      <div class="file-sidebar">
        <div class="sidebar-section">
          <h3>白名单目录</h3>
          <ul id="whitelist-dirs" class="dir-list">
            <li
              v-for="dir in whitelistDirs"
              :key="dir.path"
              class="dir-item"
              :class="{ active: currentPath === dir.path }"
              @click="navigateToDirectory(dir.path)"
            >
              {{ dir.name }}
            </li>
          </ul>
        </div>
        <div class="sidebar-section">
          <h3>当前路径</h3>
          <div id="current-path" class="current-path">{{ currentPath || '未选择' }}</div>
        </div>
      </div>

      <!-- 右侧文件内容区域 -->
      <div class="file-content">
        <!-- 文件列表视图 -->
        <div id="file-browser" class="file-view" :class="{ active: activeView === 'browser' }">
          <div class="file-toolbar">
            <!-- 面包屑导航 -->
            <div class="breadcrumb">
              <span class="breadcrumb-item" @click="navigateToRoot">根</span>
              <template v-for="(crumb, idx) in breadcrumbs" :key="idx">
                <span class="breadcrumb-sep">/</span>
                <span class="breadcrumb-item" @click="navigateToDirectory(crumb.path)">{{ crumb.name }}</span>
              </template>
            </div>
            <div class="search-box">
              <input
                type="text"
                id="file-search"
                placeholder="递归搜索文件名..."
                v-model="searchQuery"
                @keyup.enter="doSearch"
              >
              <button id="file-search-btn" class="btn btn-primary" @click="doSearch">搜索</button>
              <button v-if="searchResults" class="btn btn-secondary" @click="clearSearch">清除</button>
            </div>
          </div>

          <!-- 搜索结果视图 -->
          <div v-if="searchResults" class="search-results-panel">
            <div class="search-results-header">
              搜索 “{{ searchResults.query }}” 共找到 {{ searchResults.total }} 个结果
              <span v-if="searchResults.truncated" class="truncate-tip">（已截断）</span>
            </div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>名称</th><th>类型</th><th>大小</th><th>修改时间</th><th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in searchResults.results" :key="item.path" class="file-row">
                    <td @click="item.is_dir ? navigateToDirectory(item.path) : openFile(item)">
                      <span class="file-icon">{{ item.is_dir ? '📁' : getFileIcon(item.name) }}</span>
                      <span class="file-name">{{ item.name }}</span>
                    </td>
                    <td>{{ item.is_dir ? '目录' : getFileType(item.name) }}</td>
                    <td>{{ formatFileSize(item.size) }}</td>
                    <td>{{ formatDate(item.modified_at) }}</td>
                    <td><span class="file-path-hint">{{ item.path }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 文件列表 -->
          <div v-else class="table-container">
            <table id="files-table" class="data-table">
              <thead>
                <tr>
                  <th>
                    <input type="checkbox" id="select-all-files" v-model="selectAll" @change="toggleSelectAll">
                  </th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>大小</th>
                  <th>修改时间</th>
                  <th>权限</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading" class="loading-row">
                  <td colspan="7" class="loading">加载中...</td>
                </tr>
                <tr v-else-if="allEntries.length === 0">
                  <td colspan="7" class="no-data">没有找到文件</td>
                </tr>
                <!-- 父目录 -->
                <tr v-if="canGoUp && !loading" class="file-row directory" @click="navigateToParent">
                  <td></td>
                  <td>
                    <span class="file-icon">📁</span>
                    <span class="file-name">..</span>
                  </td>
                  <td>目录</td><td>-</td><td>-</td><td>-</td><td></td>
                </tr>
                <!-- 文件列表 -->
                <tr
                  v-for="entry in allEntries"
                  :key="entry.path"
                  class="file-row"
                  :class="{ directory: entry.is_dir }"
                >
                  <td @click.stop>
                    <input type="checkbox" :value="entry.path" v-model="selectedPaths">
                  </td>
                  <td @click="entry.is_dir ? navigateToDirectory(entry.path) : openFile(entry)">
                    <span class="file-icon">{{ entry.is_dir ? '📁' : getFileIcon(entry.name) }}</span>
                    <span class="file-name">{{ entry.name }}</span>
                  </td>
                  <td>{{ entry.is_dir ? '目录' : getFileType(entry.name) }}</td>
                  <td>
                    <span class="size-cell" @click="entry.is_dir ? loadDirSize(entry) : null">
                      {{ formatFileSize(entry.size) }}
                      <span v-if="entry.is_dir" class="size-hint">（点击计算）</span>
                      <span v-if="dirSizeCache[entry.path]" class="dir-size-total">
                        共 {{ formatFileSize(dirSizeCache[entry.path].size) }} / {{ dirSizeCache[entry.path].file_count }} 文件
                      </span>
                    </span>
                  </td>
                  <td>{{ formatDate(entry.modified_at) }}</td>
                  <td>{{ entry.permissions }}</td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn btn-secondary btn-sm" @click="openRenameModal(entry)">重命名</button>
                      <button class="btn btn-secondary btn-sm" @click="openMoveCopyModal(entry, 'move')">移动</button>
                      <button class="btn btn-secondary btn-sm" @click="openMoveCopyModal(entry, 'copy')">复制</button>
                      <button class="btn btn-secondary btn-sm" @click="viewFilePermissions(entry)">权限</button>
                      <button class="btn btn-secondary btn-sm" @click="showHash(entry)">校验</button>
                      <button class="btn btn-secondary btn-sm" @click="downloadFile(entry)" v-if="!entry.is_dir">下载</button>
                      <button
                        v-if="!entry.is_dir && isArchive(entry.name)"
                        class="btn btn-secondary btn-sm"
                        @click="openExtractModal(entry)"
                      >解压</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 文件编辑视图 -->
        <div id="file-editor" class="file-view" :class="{ active: activeView === 'editor' }">
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <button id="back-to-browser-btn" class="btn btn-secondary" @click="showBrowserView">返回</button>
              <span id="editing-file-name" class="file-name">{{ editingFile?.name || '' }}</span>
            </div>
            <div class="toolbar-right">
              <button id="save-file-btn" class="btn btn-primary" @click="saveFile">保存</button>
              <button id="revert-file-btn" class="btn btn-secondary" @click="revertFile">撤销</button>
              <div class="dropdown">
                <button id="version-history-btn" class="btn btn-secondary" @click="toggleVersionDropdown">版本历史</button>
                <div v-if="showVersionDropdown" class="dropdown-content show">
                  <div v-if="versionsLoading" class="dropdown-loading">加载中...</div>
                  <div v-else-if="versions.length === 0" class="dropdown-empty">暂无历史版本</div>
                  <div
                    v-for="ver in versions"
                    :key="ver.version"
                    class="version-item"
                  >
                    <div class="version-info">
                      <div class="version-time">{{ formatDate(ver.created_at) }}</div>
                      <div class="version-user">{{ ver.username || '未知' }}</div>
                    </div>
                    <div class="version-actions">
                      <button class="btn btn-secondary btn-sm" @click="viewVersionDiff(ver)">对比</button>
                      <button class="btn btn-primary btn-sm" @click="restoreVersion(ver)">恢复</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="editor-container">
            <textarea id="file-content-editor" class="file-editor" v-model="fileContent"></textarea>
          </div>
        </div>

        <!-- 文件权限视图 -->
        <div id="file-permissions-view" class="file-view" :class="{ active: activeView === 'permissions' }">
          <div class="permissions-header">
            <button id="back-to-browser-from-permissions-btn" class="btn btn-secondary" @click="showBrowserView">返回</button>
            <h3 id="permissions-file-name">{{ permissionsFile?.name || '' }}</h3>
          </div>
          <div class="permissions-content" id="permissions-details">
            <div v-if="permissionsFile" class="permissions-form">
              <div class="form-group">
                <label>权限字符串</label>
                <input type="text" v-model="permissionsFile.permissions" readonly>
              </div>
              <div class="perm-grid" v-if="permissionsFile.permissions_detail">
                <div class="perm-block" v-for="(perm, role) in permissionsFile.permissions_detail" :key="role">
                  <div class="perm-role">{{ roleLabel(role) }}</div>
                  <div class="perm-flags">
                    <span :class="{ on: perm.read }">读</span>
                    <span :class="{ on: perm.write }">写</span>
                    <span :class="{ on: perm.execute }">执行</span>
                  </div>
                </div>
              </div>
              <div class="perm-meta">
                <div>所有者 UID：{{ permissionsFile.owner }}</div>
                <div>所属组 GID：{{ permissionsFile.group }}</div>
                <div>Inode：{{ permissionsFile.inode }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 版本差异视图 -->
        <div id="file-diff-view" class="file-view" :class="{ active: activeView === 'diff' }">
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <button class="btn btn-secondary" @click="showEditorView">返回编辑</button>
              <span class="file-name">版本差异：v{{ diffVersion }}</span>
            </div>
          </div>
          <div class="diff-container">
            <pre class="diff-output">{{ diffContent || '无差异' }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- 通用模态框：新建文件/目录 -->
    <div v-if="modal.create" class="modal-overlay" @click.self="closeModal('create')">
      <div class="modal-card">
        <h3>{{ createType === 'directory' ? '新建目录' : '新建文件' }}</h3>
        <div class="form-group">
          <label>{{ createType === 'directory' ? '目录名' : '文件名' }}</label>
          <input type="text" v-model="createName" :placeholder="createType === 'directory' ? 'new_dir' : 'example.txt'">
          <div class="form-hint">将在当前目录创建：{{ createTargetPath }}</div>
        </div>
        <div class="form-group" v-if="createType === 'file'">
          <label>初始内容（可选）</label>
          <textarea v-model="createContent" rows="4"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('create')">取消</button>
          <button class="btn btn-primary" @click="submitCreate">确定</button>
        </div>
      </div>
    </div>

    <!-- 重命名模态框 -->
    <div v-if="modal.rename" class="modal-overlay" @click.self="closeModal('rename')">
      <div class="modal-card">
        <h3>重命名</h3>
        <div class="form-group">
          <label>新名称</label>
          <input type="text" v-model="renameValue">
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('rename')">取消</button>
          <button class="btn btn-primary" @click="submitRename">确定</button>
        </div>
      </div>
    </div>

    <!-- 移动/复制模态框 -->
    <div v-if="modal.moveCopy" class="modal-overlay" @click.self="closeModal('moveCopy')">
      <div class="modal-card">
        <h3>{{ moveCopyMode === 'move' ? '移动到' : '复制到' }}</h3>
        <div class="form-group">
          <label>源：{{ moveCopyEntry?.name }}</label>
          <label>目标目录路径</label>
          <input type="text" v-model="moveCopyTarget" placeholder="目标目录绝对路径">
          <div class="form-hint">可从白名单目录中复制路径</div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('moveCopy')">取消</button>
          <button class="btn btn-primary" @click="submitMoveCopy">{{ moveCopyMode === 'move' ? '移动' : '复制' }}</button>
        </div>
      </div>
    </div>

    <!-- 压缩模态框 -->
    <div v-if="modal.compress" class="modal-overlay" @click.self="closeModal('compress')">
      <div class="modal-card">
        <h3>压缩所选项目</h3>
        <div class="form-group">
          <label>已选 {{ selectedPaths.length }} 项</label>
          <label>压缩包路径（含文件名）</label>
          <input type="text" v-model="compressTarget" placeholder="例如 archive.zip / archive.tar.gz">
          <div class="form-hint">支持格式：zip, tar, tar.gz, tgz, bz2</div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('compress')">取消</button>
          <button class="btn btn-primary" @click="submitCompress">压缩</button>
        </div>
      </div>
    </div>

    <!-- 解压模态框 -->
    <div v-if="modal.extract" class="modal-overlay" @click.self="closeModal('extract')">
      <div class="modal-card">
        <h3>解压 {{ extractEntry?.name }}</h3>
        <div class="form-group">
          <label>解压到目录</label>
          <input type="text" v-model="extractTarget" placeholder="目标目录绝对路径">
          <div class="form-hint">将自动创建目标目录</div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('extract')">取消</button>
          <button class="btn btn-primary" @click="submitExtract">解压</button>
        </div>
      </div>
    </div>

    <!-- 校验和模态框 -->
    <div v-if="modal.hash" class="modal-overlay" @click.self="closeModal('hash')">
      <div class="modal-card">
        <h3>文件校验和 — {{ hashEntry?.name }}</h3>
        <div class="form-group">
          <label>算法</label>
          <select v-model="hashAlgorithm" @change="loadHash">
            <option value="md5">MD5</option>
            <option value="sha1">SHA-1</option>
            <option value="sha256">SHA-256</option>
          </select>
        </div>
        <div class="form-group">
          <label>哈希值</label>
          <div class="hash-value">{{ hashValue || '计算中...' }}</div>
          <button v-if="hashValue" class="btn btn-secondary btn-sm" @click="copyHash">复制</button>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('hash')">关闭</button>
        </div>
      </div>
    </div>

    <!-- 上传模态框 -->
    <div v-if="modal.upload" class="modal-overlay" @click.self="closeUploadModal">
      <div class="modal-card modal-wide">
        <h3>上传文件</h3>
        <div v-if="!uploadId" class="form-group">
          <label>选择文件</label>
          <input type="file" ref="fileInput" @change="onFileSelected">
          <div v-if="selectedUploadFile" class="form-hint">
            {{ selectedUploadFile.name }} ({{ formatFileSize(selectedUploadFile.size) }})
          </div>
        </div>
        <div v-if="uploadId" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <div class="progress-text">
            {{ uploadProgress }}% · {{ uploadReceivedChunks }}/{{ uploadTotalChunks }} 分块
            <span v-if="uploadResumed" class="resumed-tip">（断点续传）</span>
          </div>
          <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeUploadModal">{{ uploadId && uploadProgress >= 100 ? '完成' : '取消' }}</button>
          <button v-if="!uploadId" class="btn btn-primary" :disabled="!selectedUploadFile || uploading" @click="startUpload">
            {{ uploading ? '准备中...' : '开始上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <div v-if="modal.confirm" class="modal-overlay" @click.self="closeModal('confirm')">
      <div class="modal-card">
        <h3>{{ confirmTitle }}</h3>
        <p class="confirm-text">{{ confirmMessage }}</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeModal('confirm')">取消</button>
          <button class="btn btn-danger" @click="confirmAction">确定</button>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useStore } from 'vuex'

const store = useStore()
const fileInput = ref(null)

// ========== 状态 ==========
const whitelistDirs = ref([])
const currentPath = ref('')
const directories = ref([])
const files = ref([])
const loading = ref(false)
const selectedPaths = ref([])
const searchQuery = ref('')
const searchResults = ref(null)
const dirSizeCache = reactive({})

const activeView = ref('browser') // browser | editor | permissions | diff
const editingFile = ref(null)
const fileContent = ref('')
const originalContent = ref('')
const permissionsFile = ref(null)

// 版本控制
const showVersionDropdown = ref(false)
const versions = ref([])
const versionsLoading = ref(false)
const diffContent = ref('')
const diffVersion = ref(null)

// 模态框
const modal = reactive({
  create: false, rename: false, moveCopy: false, compress: false,
  extract: false, hash: false, upload: false, confirm: false
})
const createType = ref('file')
const createName = ref('')
const createContent = ref('')
const renameValue = ref('')
const renameTarget = ref(null)
const moveCopyMode = ref('move')
const moveCopyEntry = ref(null)
const moveCopyTarget = ref('')
const compressTarget = ref('')
const extractEntry = ref(null)
const extractTarget = ref('')
const hashEntry = ref(null)
const hashAlgorithm = ref('sha256')
const hashValue = ref('')

// 确认框
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmCallback = ref(null)

// 上传
const selectedUploadFile = ref(null)
const uploadId = ref('')
const uploadProgress = ref(0)
const uploadTotalChunks = ref(0)
const uploadReceivedChunks = ref(0)
const uploading = ref(false)
const uploadError = ref('')
const uploadResumed = ref(false)
const CHUNK_SIZE = ref(1024 * 1024) // 默认 1MB，会被 init 接口返回值覆盖

// Toast
const toast = reactive({ show: false, type: 'info', message: '', timer: null })

// ========== 计算属性 ==========
const allEntries = computed(() => [...directories.value, ...files.value])

const selectAll = computed({
  get: () => allEntries.value.length > 0 && allEntries.value.every(e => selectedPaths.value.includes(e.path)),
  set: () => {}
})

const canGoUp = computed(() => {
  if (!currentPath.value) return false
  // 不能超出白名单根目录
  return whitelistDirs.value.some(d => currentPath.value !== d.path && currentPath.value.startsWith(d.path))
})

const breadcrumbs = computed(() => {
  if (!currentPath.value) return []
  const parts = currentPath.value.replace(/\\/g, '/').split('/').filter(Boolean)
  const crumbs = []
  let acc = ''
  for (const p of parts) {
    acc = acc ? acc + '/' + p : p
    crumbs.push({ name: p, path: acc === currentPath.value.replace(/\\/g, '/').replace(/\/$/, '') ? currentPath.value : acc })
  }
  return crumbs
})

const createTargetPath = computed(() => {
  if (!currentPath.value || !createName.value) return ''
  return joinPath(currentPath.value, createName.value)
})

// ========== API 封装 ==========
const authHeaders = () => ({
  'Authorization': `Bearer ${store.state.token}`,
  'Content-Type': 'application/json'
})

async function api(url, options = {}) {
  const res = await fetch(url, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } })
  let data
  try { data = await res.json() } catch { data = { status: 'error', message: `HTTP ${res.status}` } }
  return data
}

// ========== 工具方法 ==========
function joinPath(base, name) {
  const sep = base.includes('\\') && !base.includes('/') ? '\\' : '/'
  return base.replace(/[\\/]+$/, '') + sep + name
}

function showToast(message, type = 'info') {
  toast.message = message
  toast.type = type
  toast.show = true
  if (toast.timer) clearTimeout(toast.timer)
  toast.timer = setTimeout(() => { toast.show = false }, 3000)
}

function closeModal(name) {
  modal[name] = false
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  const iconMap = {
    txt: '📄', md: '📝', js: '📜', css: '🎨', html: '🌐', json: '🔧', py: '🐍',
    java: '☕', php: '🐘', sql: '🗄️', xml: '📄', yaml: '📄', yml: '📄',
    config: '⚙️', ini: '⚙️', log: '📋', pdf: '📄', doc: '📄', docx: '📄',
    xls: '📊', xlsx: '📊', ppt: '📊', pptx: '📊', jpg: '🖼️', jpeg: '🖼️',
    png: '🖼️', gif: '🖼️', svg: '🖼️', mp3: '🎵', wav: '🎵', mp4: '🎬',
    avi: '🎬', mov: '🎬', zip: '🗜️', tar: '🗜️', gz: '🗜️', bz2: '🗜️'
  }
  return iconMap[ext] || '📄'
}

function getFileType(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  if (['zip', 'tar', 'gz', 'tgz', 'bz2'].includes(ext)) return '压缩文件'
  if (['txt', 'md', 'doc', 'docx'].includes(ext)) return '文本文件'
  if (['js', 'css', 'html', 'json', 'py', 'java', 'cpp', 'c', 'h', 'php', 'sql'].includes(ext)) return '代码文件'
  if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)) return '图片文件'
  if (['mp3', 'wav'].includes(ext)) return '音频文件'
  if (['mp4', 'avi', 'mov'].includes(ext)) return '视频文件'
  return '其他文件'
}

function isArchive(filename) {
  const lower = filename.toLowerCase()
  return ['.zip', '.tar', '.tar.gz', '.tgz', '.gz', '.bz2'].some(ext => lower.endsWith(ext))
}

function formatFileSize(size) {
  if (size == null) return '-'
  if (size === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(size) / Math.log(k))
  return parseFloat((size / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleString()
}

function roleLabel(role) {
  return { user: '所有者', group: '用户组', other: '其他' }[role] || role
}

// ========== 目录加载 ==========
async function loadWhitelistDirs() {
  const data = await api('/api/file-manager/whitelist-dirs')
  if (data.status === 'success') {
    whitelistDirs.value = data.dirs || []
    if (whitelistDirs.value.length > 0 && !currentPath.value) {
      navigateToDirectory(whitelistDirs.value[0].path)
    }
  } else {
    showToast(data.message || '加载白名单目录失败', 'error')
  }
}

async function refreshFiles() {
  if (!currentPath.value) {
    await loadWhitelistDirs()
    return
  }
  loading.value = true
  selectedPaths.value = []
  searchResults.value = null
  const data = await api(`/api/file-manager/directory?path=${encodeURIComponent(currentPath.value)}`)
  loading.value = false
  if (data.status === 'success') {
    directories.value = data.directories || []
    files.value = data.files || []
  } else {
    directories.value = []
    files.value = []
    showToast(data.message || '加载目录失败', 'error')
  }
}

function navigateToDirectory(path) {
  if (currentPath.value === path) return
  currentPath.value = path
  refreshFiles()
}

function navigateToRoot() {
  if (whitelistDirs.value.length > 0) {
    navigateToDirectory(whitelistDirs.value[0].path)
  }
}

function navigateToParent() {
  if (!canGoUp.value) return
  const parent = currentPath.value.replace(/[\\/][^\\/]+[\\/]?$/, '')
  // 找到所属白名单根
  const root = whitelistDirs.value.find(d => currentPath.value.startsWith(d.path))
  if (root && (parent === root.path || parent.startsWith(root.path))) {
    navigateToDirectory(parent || root.path)
  } else if (root) {
    navigateToDirectory(root.path)
  }
}

function showBrowserView() {
  activeView.value = 'browser'
  editingFile.value = null
  permissionsFile.value = null
  showVersionDropdown.value = false
}

function showEditorView() {
  activeView.value = 'editor'
}

// ========== 选择 ==========
function toggleSelectAll() {
  if (selectAll.value) {
    selectedPaths.value = []
  } else {
    selectedPaths.value = allEntries.value.map(e => e.path)
  }
}

// ========== 搜索 ==========
async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) {
    clearSearch()
    return
  }
  if (!currentPath.value) {
    showToast('请先选择目录', 'error')
    return
  }
  loading.value = true
  const data = await api(`/api/file-manager/search?path=${encodeURIComponent(currentPath.value)}&query=${encodeURIComponent(q)}`)
  loading.value = false
  if (data.status === 'success') {
    searchResults.value = data
  } else {
    showToast(data.message || '搜索失败', 'error')
  }
}

function clearSearch() {
  searchResults.value = null
  searchQuery.value = ''
}

// ========== 目录大小 ==========
async function loadDirSize(entry) {
  if (dirSizeCache[entry.path]) return
  const data = await api(`/api/file-manager/directory-size?path=${encodeURIComponent(entry.path)}`)
  if (data.status === 'success') {
    dirSizeCache[entry.path] = { size: data.size, file_count: data.file_count, dir_count: data.dir_count }
  } else {
    showToast(data.message || '计算目录大小失败', 'error')
  }
}

// ========== 创建 ==========
function openCreateModal(type) {
  if (!currentPath.value) {
    showToast('请先选择目录', 'error')
    return
  }
  createType.value = type
  createName.value = ''
  createContent.value = ''
  modal.create = true
}

async function submitCreate() {
  if (!createName.value.trim()) {
    showToast('名称不能为空', 'error')
    return
  }
  const target = joinPath(currentPath.value, createName.value.trim())
  if (createType.value === 'directory') {
    const data = await api('/api/file-manager/directory', {
      method: 'POST',
      body: JSON.stringify({ file_path: target })
    })
    if (data.status === 'success') {
      showToast('目录创建成功', 'success')
      closeModal('create')
      refreshFiles()
    } else {
      showToast(data.message || '创建失败', 'error')
    }
  } else {
    const data = await api('/api/file-manager/file', {
      method: 'POST',
      body: JSON.stringify({ file_path: target, content: createContent.value })
    })
    if (data.status === 'success') {
      showToast('文件创建成功', 'success')
      closeModal('create')
      refreshFiles()
    } else {
      showToast(data.message || '创建失败', 'error')
    }
  }
}

// ========== 删除 ==========
function confirmBatchDelete() {
  if (selectedPaths.value.length === 0) return
  openConfirm('批量删除', `确认删除所选 ${selectedPaths.value.length} 项？此操作不可撤销。`, async () => {
    const data = await api('/api/file-manager/batch-delete', {
      method: 'POST',
      body: JSON.stringify({ paths: selectedPaths.value })
    })
    if (data.status === 'success' || data.status === 'partial') {
      showToast(data.message, data.status === 'partial' ? 'error' : 'success')
      selectedPaths.value = []
      refreshFiles()
    } else {
      showToast(data.message || '删除失败', 'error')
    }
  })
}

function openConfirm(title, message, callback) {
  confirmTitle.value = title
  confirmMessage.value = message
  confirmCallback.value = callback
  modal.confirm = true
}

function confirmAction() {
  if (confirmCallback.value) confirmCallback.value()
  closeModal('confirm')
}

// ========== 读取/编辑 ==========
async function openFile(entry) {
  editingFile.value = entry
  activeView.value = 'editor'
  fileContent.value = ''
  originalContent.value = ''
  const data = await api(`/api/file-manager/file/read?path=${encodeURIComponent(entry.path)}`)
  if (data.status === 'success') {
    fileContent.value = data.content
    originalContent.value = data.content
  } else {
    showToast(data.message || '读取文件失败', 'error')
  }
}

async function saveFile() {
  if (!editingFile.value) return
  const data = await api('/api/file-manager/file/write', {
    method: 'PUT',
    body: JSON.stringify({ file_path: editingFile.value.path, content: fileContent.value })
  })
  if (data.status === 'success') {
    showToast('保存成功', 'success')
    originalContent.value = fileContent.value
  } else {
    showToast(data.message || '保存失败', 'error')
  }
}

function revertFile() {
  fileContent.value = originalContent.value
  showToast('已撤销至最近保存的内容', 'info')
}

// ========== 重命名 ==========
function openRenameModal(entry) {
  renameTarget.value = entry
  renameValue.value = entry.name
  modal.rename = true
}

async function submitRename() {
  if (!renameValue.value.trim()) {
    showToast('名称不能为空', 'error')
    return
  }
  const data = await api('/api/file-manager/rename', {
    method: 'POST',
    body: JSON.stringify({ file_path: renameTarget.value.path, new_name: renameValue.value.trim() })
  })
  if (data.status === 'success') {
    showToast('重命名成功', 'success')
    closeModal('rename')
    refreshFiles()
  } else {
    showToast(data.message || '重命名失败', 'error')
  }
}

// ========== 移动/复制 ==========
function openMoveCopyModal(entry, mode) {
  moveCopyEntry.value = entry
  moveCopyMode.value = mode
  moveCopyTarget.value = currentPath.value
  modal.moveCopy = true
}

async function submitMoveCopy() {
  if (!moveCopyTarget.value.trim()) {
    showToast('目标目录不能为空', 'error')
    return
  }
  const url = moveCopyMode.value === 'move' ? '/api/file-manager/move' : '/api/file-manager/copy'
  const data = await api(url, {
    method: 'POST',
    body: JSON.stringify({ src_path: moveCopyEntry.value.path, dst_dir: moveCopyTarget.value.trim() })
  })
  if (data.status === 'success') {
    showToast(moveCopyMode.value === 'move' ? '移动成功' : '复制成功', 'success')
    closeModal('moveCopy')
    refreshFiles()
  } else {
    showToast(data.message || '操作失败', 'error')
  }
}

// ========== 压缩/解压 ==========
function openCompressModal() {
  if (selectedPaths.value.length === 0) return
  compressTarget.value = joinPath(currentPath.value, 'archive.zip')
  modal.compress = true
}

async function submitCompress() {
  if (!compressTarget.value.trim()) {
    showToast('压缩包路径不能为空', 'error')
    return
  }
  const data = await api('/api/file-manager/archive/create', {
    method: 'POST',
    body: JSON.stringify({ src_paths: selectedPaths.value, archive_path: compressTarget.value.trim() })
  })
  if (data.status === 'success') {
    showToast('压缩成功', 'success')
    closeModal('compress')
    selectedPaths.value = []
    refreshFiles()
  } else {
    showToast(data.message || '压缩失败', 'error')
  }
}

function openExtractModal(entry) {
  extractEntry.value = entry
  extractTarget.value = joinPath(currentPath.value, entry.name.replace(/\.(zip|tar\.gz|tgz|tar|gz|bz2)$/i, ''))
  modal.extract = true
}

async function submitExtract() {
  if (!extractTarget.value.trim()) {
    showToast('目标目录不能为空', 'error')
    return
  }
  const data = await api('/api/file-manager/archive/extract', {
    method: 'POST',
    body: JSON.stringify({ archive_path: extractEntry.value.path, target_dir: extractTarget.value.trim() })
  })
  if (data.status === 'success') {
    showToast('解压成功', 'success')
    closeModal('extract')
    refreshFiles()
  } else {
    showToast(data.message || '解压失败', 'error')
  }
}

// ========== 校验和 ==========
async function showHash(entry) {
  hashEntry.value = entry
  hashAlgorithm.value = 'sha256'
  hashValue.value = ''
  modal.hash = true
  await loadHash()
}

async function loadHash() {
  if (!hashEntry.value) return
  hashValue.value = ''
  const data = await api(`/api/file-manager/file/hash?path=${encodeURIComponent(hashEntry.value.path)}&algorithm=${hashAlgorithm.value}`)
  if (data.status === 'success') {
    hashValue.value = data.hash
  } else {
    hashValue.value = '计算失败：' + (data.message || '未知错误')
  }
}

async function copyHash() {
  try {
    await navigator.clipboard.writeText(hashValue.value)
    showToast('已复制到剪贴板', 'success')
  } catch {
    showToast('复制失败', 'error')
  }
}

// ========== 权限 ==========
async function viewFilePermissions(entry) {
  permissionsFile.value = entry
  activeView.value = 'permissions'
  const data = await api(`/api/file-manager/file/permissions?path=${encodeURIComponent(entry.path)}`)
  if (data.status === 'success') {
    permissionsFile.value = { ...entry, ...data }
  } else {
    showToast(data.message || '获取权限失败', 'error')
  }
}

// ========== 下载 ==========
async function downloadFile(entry) {
  try {
    const res = await fetch(`/api/file-manager/download?path=${encodeURIComponent(entry.path)}`, {
      headers: { 'Authorization': `Bearer ${store.state.token}` }
    })
    if (!res.ok) {
      showToast('下载失败', 'error')
      return
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = entry.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    showToast('下载失败', 'error')
  }
}

// ========== 版本控制 ==========
async function toggleVersionDropdown() {
  showVersionDropdown.value = !showVersionDropdown.value
  if (showVersionDropdown.value) {
    await loadVersions()
  }
}

async function loadVersions() {
  if (!editingFile.value) return
  versionsLoading.value = true
  const data = await api(`/api/file-manager/file/versions?path=${encodeURIComponent(editingFile.value.path)}`)
  versionsLoading.value = false
  if (data.status === 'success') {
    versions.value = data.versions || []
  } else {
    versions.value = []
  }
}

async function viewVersionDiff(ver) {
  diffVersion.value = ver.version
  diffContent.value = '加载中...'
  activeView.value = 'diff'
  const data = await api(`/api/file-manager/file/version-diff?path=${encodeURIComponent(editingFile.value.path)}&version=${ver.version}`)
  if (data.status === 'success') {
    diffContent.value = data.diff
  } else {
    diffContent.value = '获取差异失败：' + (data.message || '')
  }
}

function openConfirmRestore(ver, callback) {
  openConfirm('恢复版本', `确认将文件恢复到版本 v${ver.version}（${formatDate(ver.created_at)}）？当前内容会先保存为新版本。`, callback)
}

async function restoreVersion(ver) {
  openConfirmRestore(ver, async () => {
    const data = await api('/api/file-manager/file/restore-version', {
      method: 'POST',
      body: JSON.stringify({ file_path: editingFile.value.path, version: ver.version })
    })
    if (data.status === 'success') {
      showToast('版本恢复成功', 'success')
      await openFile(editingFile.value)
    } else {
      showToast(data.message || '恢复失败', 'error')
    }
  })
}

// ========== 上传（分块 + 断点续传） ==========
function openUploadModal() {
  if (!currentPath.value) {
    showToast('请先选择目标目录', 'error')
    return
  }
  selectedUploadFile.value = null
  uploadId.value = ''
  uploadProgress.value = 0
  uploadTotalChunks.value = 0
  uploadReceivedChunks.value = 0
  uploading.value = false
  uploadError.value = ''
  uploadResumed.value = false
  modal.upload = true
}

function closeUploadModal() {
  if (uploadId.value && uploadProgress.value < 100) {
    openConfirm('取消上传', '上传尚未完成，确认取消？已上传分块会保留以支持续传。', () => {
      doCancelUpload()
    })
    return
  }
  doCancelUpload()
}

async function doCancelUpload() {
  if (uploadId.value) {
    await api('/api/file-manager/upload/cancel', {
      method: 'POST',
      body: JSON.stringify({ upload_id: uploadId.value })
    })
  }
  modal.upload = false
}

function onFileSelected(e) {
  const f = e.target.files[0]
  if (f) selectedUploadFile.value = f
}

async function startUpload() {
  if (!selectedUploadFile.value) return
  uploading.value = true
  uploadError.value = ''

  const init = await api('/api/file-manager/upload/init', {
    method: 'POST',
    body: JSON.stringify({
      filename: selectedUploadFile.value.name,
      total_size: selectedUploadFile.value.size,
      target_path: currentPath.value
    })
  })

  if (init.status !== 'success') {
    uploading.value = false
    uploadError.value = init.message || '初始化上传失败'
    return
  }

  uploadId.value = init.upload_id
  uploadTotalChunks.value = init.total_chunks
  CHUNK_SIZE.value = init.chunk_size

  // 断点续传：先查询已接收分块
  const status = await api(`/api/file-manager/upload/status?upload_id=${uploadId.value}`)
  let missing = []
  if (status.status === 'success' && status.missing_chunks && status.missing_chunks.length < init.total_chunks) {
    missing = status.missing_chunks
    if (missing.length < init.total_chunks) {
      uploadResumed.value = true
      uploadReceivedChunks.value = init.total_chunks - missing.length
      uploadProgress.value = Math.round(uploadReceivedChunks.value / init.total_chunks * 100)
    }
  } else {
    missing = Array.from({ length: init.total_chunks }, (_, i) => i)
  }

  // 依次上传缺失分块
  for (const idx of missing) {
    const start = idx * CHUNK_SIZE.value
    const end = Math.min(start + CHUNK_SIZE.value, selectedUploadFile.value.size)
    const chunk = selectedUploadFile.value.slice(start, end)

    const formData = new FormData()
    formData.append('upload_id', uploadId.value)
    formData.append('chunk_index', idx)
    formData.append('chunk', chunk)

    try {
      const res = await fetch('/api/file-manager/upload/chunk', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${store.state.token}` },
        body: formData
      })
      const data = await res.json()
      if (data.status !== 'success') {
        uploadError.value = data.message || '分块上传失败'
        uploading.value = false
        return
      }
      uploadProgress.value = data.progress
      uploadReceivedChunks.value = data.received_chunks
    } catch (err) {
      uploadError.value = '网络错误：' + err.message
      uploading.value = false
      return
    }
  }

  // 完成上传
  const complete = await api('/api/file-manager/upload/complete', {
    method: 'POST',
    body: JSON.stringify({ upload_id: uploadId.value })
  })
  uploading.value = false
  if (complete.status === 'success') {
    showToast('上传成功', 'success')
    uploadProgress.value = 100
    setTimeout(() => {
      modal.upload = false
      refreshFiles()
    }, 800)
  } else {
    uploadError.value = complete.message || '完成上传失败'
  }
}

// ========== 初始化 ==========
onMounted(() => {
  loadWhitelistDirs()
})
</script>

<style scoped>
/* iOS 26 文件管理器容器 */
.file-manager-container {
  display: flex;
  gap: var(--ios-space-5);
  margin-top: var(--ios-space-5);
  height: calc(100vh - 220px);
}

/* iOS 26 侧边栏 */
.file-sidebar {
  width: 260px;
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  overflow: hidden;
}

.sidebar-section {
  padding: var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
}

.sidebar-section:last-child {
  border-bottom: none;
}

.sidebar-section h3 {
  margin: 0 0 var(--ios-space-3);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.dir-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-1);
}

.dir-item {
  padding: var(--ios-space-3) var(--ios-space-4);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  border-radius: var(--ios-radius-lg);
  color: var(--ios-label-secondary);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
}

.dir-item:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.dir-item:active {
  background: var(--ios-fill-tertiary);
  transform: scale(0.98);
}

.dir-item.active {
  background: var(--ios-blue);
  color: white;
}

.current-path {
  background: var(--ios-fill-quaternary);
  padding: var(--ios-space-3);
  border-radius: var(--ios-radius-lg);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption1);
  word-break: break-all;
  color: var(--ios-label-secondary);
}

/* iOS 26 文件内容区 */
.file-content {
  flex: 1;
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.file-view {
  display: none;
  height: 100%;
  flex-direction: column;
}

.file-view.active {
  display: flex;
}

/* 工具栏 */
.file-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-3) var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
  flex-wrap: wrap;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--ios-space-1);
  font-size: var(--ios-text-subhead);
  flex-wrap: wrap;
}

.breadcrumb-item {
  cursor: pointer;
  color: var(--ios-blue);
  padding: 2px 6px;
  border-radius: var(--ios-radius-sm);
  transition: background var(--ios-transition-fast);
}

.breadcrumb-item:hover {
  background: var(--ios-fill-quaternary);
}

.breadcrumb-sep {
  color: var(--ios-label-tertiary);
}

.search-box {
  display: flex;
  gap: var(--ios-space-2);
}

.search-box input {
  padding: var(--ios-space-2) var(--ios-space-3);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  outline: none;
  min-width: 220px;
}

.search-box input:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

/* 表格 */
.table-container {
  flex: 1;
  overflow: auto;
  padding: var(--ios-space-3) var(--ios-space-4);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--ios-text-subhead);
}

.data-table th {
  text-align: left;
  padding: var(--ios-space-3);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 0.5px solid var(--ios-separator);
  position: sticky;
  top: 0;
  background: var(--ios-card-bg);
  z-index: 1;
}

.data-table td {
  padding: var(--ios-space-3);
  border-bottom: 0.5px solid var(--ios-separator);
  color: var(--ios-label-primary);
  vertical-align: middle;
}

.file-row {
  cursor: default;
  transition: background var(--ios-transition-fast);
}

.file-row:hover {
  background: var(--ios-fill-quaternary);
}

.file-row.directory .file-name {
  color: var(--ios-blue);
  font-weight: var(--ios-weight-medium);
}

.file-row td:nth-child(2) {
  cursor: pointer;
}

.file-icon {
  margin-right: var(--ios-space-2);
}

.file-name {
  font-weight: var(--ios-weight-regular);
}

.size-cell {
  cursor: default;
}

.size-hint {
  font-size: var(--ios-text-caption2);
  color: var(--ios-label-tertiary);
  margin-left: var(--ios-space-1);
}

.dir-size-total {
  display: block;
  font-size: var(--ios-text-caption2);
  color: var(--ios-green);
  margin-top: 2px;
}

.action-buttons {
  display: flex;
  gap: var(--ios-space-1);
  flex-wrap: wrap;
}

.btn-sm {
  padding: var(--ios-space-1) var(--ios-space-2);
  font-size: var(--ios-text-caption1);
}

.file-path-hint {
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption2);
  color: var(--ios-label-tertiary);
}

/* 搜索结果面板 */
.search-results-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-results-header {
  padding: var(--ios-space-3) var(--ios-space-4);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  border-bottom: 0.5px solid var(--ios-separator);
}

.truncate-tip {
  color: var(--ios-orange);
  font-size: var(--ios-text-caption1);
}

/* 加载和空状态 */
.loading-row td,
.no-data {
  text-align: center;
  padding: var(--ios-space-8);
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-subhead);
}

/* 编辑器 */
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-space-3) var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
}

.toolbar-left .file-name {
  font-weight: var(--ios-weight-semibold);
}

.editor-container {
  flex: 1;
  padding: var(--ios-space-4);
  overflow: hidden;
}

.file-editor {
  width: 100%;
  height: 100%;
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-lg);
  padding: var(--ios-space-4);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-body);
  color: var(--ios-label-primary);
  resize: none;
  outline: none;
  line-height: 1.6;
}

/* 下拉菜单 */
.dropdown {
  position: relative;
}

.dropdown-content {
  position: absolute;
  top: calc(100% + var(--ios-space-2));
  right: 0;
  min-width: 260px;
  max-height: 360px;
  overflow-y: auto;
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-xl);
  padding: var(--ios-space-2);
  z-index: var(--ios-z-dropdown);
  border: 0.5px solid var(--ios-separator);
}

.dropdown-content.show {
  display: block;
}

.dropdown-loading,
.dropdown-empty {
  padding: var(--ios-space-3);
  text-align: center;
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-caption1);
}

.version-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-space-2) var(--ios-space-3);
  border-radius: var(--ios-radius-lg);
  gap: var(--ios-space-2);
}

.version-item:hover {
  background: var(--ios-fill-quaternary);
}

.version-time {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-primary);
}

.version-user {
  font-size: var(--ios-text-caption2);
  color: var(--ios-label-tertiary);
}

.version-actions {
  display: flex;
  gap: var(--ios-space-1);
}

/* 权限视图 */
.permissions-header {
  display: flex;
  align-items: center;
  gap: var(--ios-space-4);
  padding: var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
}

.permissions-content {
  flex: 1;
  padding: var(--ios-space-5);
  overflow: auto;
}

.permissions-form {
  max-width: 600px;
}

.form-group {
  margin-bottom: var(--ios-space-4);
}

.form-group label {
  display: block;
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  margin-bottom: var(--ios-space-2);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-body);
  color: var(--ios-label-primary);
  outline: none;
  transition: all var(--ios-transition-fast);
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.form-hint {
  font-size: var(--ios-text-caption2);
  color: var(--ios-label-tertiary);
  margin-top: var(--ios-space-1);
}

.perm-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--ios-space-3);
  margin: var(--ios-space-4) 0;
}

.perm-block {
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-lg);
  padding: var(--ios-space-3);
  text-align: center;
}

.perm-role {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  margin-bottom: var(--ios-space-2);
  font-weight: var(--ios-weight-semibold);
}

.perm-flags {
  display: flex;
  justify-content: center;
  gap: var(--ios-space-2);
  font-size: var(--ios-text-caption1);
}

.perm-flags span {
  color: var(--ios-label-tertiary);
}

.perm-flags span.on {
  color: var(--ios-green);
  font-weight: var(--ios-weight-semibold);
}

.perm-meta {
  display: flex;
  gap: var(--ios-space-4);
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  font-family: var(--ios-font-mono);
}

/* 差异视图 */
.diff-container {
  flex: 1;
  padding: var(--ios-space-4);
  overflow: auto;
}

.diff-output {
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-lg);
  padding: var(--ios-space-4);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-primary);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  line-height: 1.6;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--ios-z-modal, 1000);
  padding: var(--ios-space-5);
}

.modal-card {
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-shadow-xl);
  padding: var(--ios-space-5);
  width: 100%;
  max-width: 460px;
  max-height: 85vh;
  overflow-y: auto;
  border: 0.5px solid var(--ios-glass-border);
}

.modal-wide {
  max-width: 560px;
}

.modal-card h3 {
  margin: 0 0 var(--ios-space-4);
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--ios-space-3);
  margin-top: var(--ios-space-5);
}

.confirm-text {
  color: var(--ios-label-secondary);
  font-size: var(--ios-text-body);
  line-height: 1.5;
  margin: 0;
}

/* 上传进度 */
.upload-progress {
  margin: var(--ios-space-3) 0;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--ios-blue);
  border-radius: var(--ios-radius-sm);
  transition: width 0.2s ease;
}

.progress-text {
  margin-top: var(--ios-space-2);
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
}

.resumed-tip {
  color: var(--ios-orange);
  margin-left: var(--ios-space-2);
}

.upload-error {
  margin-top: var(--ios-space-2);
  font-size: var(--ios-text-caption1);
  color: var(--ios-red);
}

/* 校验和 */
.hash-value {
  background: var(--ios-fill-quaternary);
  padding: var(--ios-space-3);
  border-radius: var(--ios-radius-lg);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption1);
  word-break: break-all;
  color: var(--ios-label-primary);
  margin-bottom: var(--ios-space-2);
}

/* Toast */
.toast {
  position: fixed;
  bottom: var(--ios-space-6);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--ios-space-3) var(--ios-space-5);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-xl);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  z-index: 2000;
  max-width: 90vw;
}

.toast.info {
  background: var(--ios-bg-secondary);
  color: var(--ios-label-primary);
  border: 0.5px solid var(--ios-glass-border);
}

.toast.success {
  background: var(--ios-green);
  color: white;
}

.toast.error {
  background: var(--ios-red);
  color: white;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

/* iOS 26 按钮样式覆盖 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-2) var(--ios-space-4);
  font-family: var(--ios-font-family);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  border-radius: var(--ios-radius-lg);
  border: none;
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.btn:active {
  transform: scale(0.97);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.btn-primary {
  background: var(--ios-blue);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0066d6;
}

.btn-secondary {
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--ios-fill-secondary);
}

.btn-danger {
  background: var(--ios-red);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #d70015;
}
</style>
