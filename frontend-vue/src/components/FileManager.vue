<template>
  <div id="file-manager" class="page">
    <div class="page-header">
      <h2>文件管理</h2>
      <div class="page-actions">
        <button id="refresh-files-btn" class="btn btn-secondary" @click="refreshFiles">刷新</button>
        <button id="create-file-btn" class="btn btn-primary" @click="createNewFile">新建文件</button>
        <button id="upload-file-btn" class="btn btn-primary" @click="uploadFile">上传文件</button>
        <button 
          id="delete-file-btn" 
          class="btn btn-danger" 
          :disabled="selectedFiles.length === 0"
          @click="deleteSelectedFiles"
        >删除</button>
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
              :class="{ 'active': currentPath === dir.path }"
              @click="navigateToDirectory(dir.path)"
            >
              {{ dir.name }}
            </li>
          </ul>
        </div>
        <div class="sidebar-section">
          <h3>当前路径</h3>
          <div id="current-path" class="current-path">{{ currentPath }}</div>
        </div>
      </div>
      
      <!-- 右侧文件内容区域 -->
      <div class="file-content">
        <!-- 文件列表视图 -->
        <div id="file-browser" class="file-view" :class="{ 'active': activeView === 'browser' }">
          <div class="file-toolbar">
            <div class="search-box">
              <input 
                type="text" 
                id="file-search" 
                placeholder="搜索文件名..."
                v-model="searchQuery"
                @input="onSearch"
              >
              <button id="file-search-btn" class="btn btn-primary" @click="onSearch">搜索</button>
            </div>
          </div>
          <div class="table-container">
            <table id="files-table" class="data-table">
              <thead>
                <tr>
                  <th>
                    <input 
                      type="checkbox" 
                      id="select-all-files"
                      v-model="selectAll"
                      @change="toggleSelectAll"
                    >
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
                <tr v-else-if="filteredFiles.length === 0">
                  <td colspan="7" class="no-data">没有找到文件</td>
                </tr>
                <!-- 父目录 -->
                <tr v-if="currentPath !== '/'" class="file-row directory">
                  <td></td>
                  <td @click="navigateToParent">
                    <span class="file-icon">📁</span>
                    <span class="file-name">..</span>
                  </td>
                  <td>目录</td>
                  <td>-</td>
                  <td>-</td>
                  <td>-</td>
                  <td></td>
                </tr>
                <!-- 文件列表 -->
                <tr 
                  v-for="file in filteredFiles" 
                  :key="file.name"
                  class="file-row"
                  :class="{ 'directory': file.type === 'directory' }"
                >
                  <td>
                    <input 
                      type="checkbox" 
                      :value="file.name"
                      v-model="selectedFiles"
                    >
                  </td>
                  <td @click="file.type === 'directory' ? navigateToDirectory(file.path) : editFile(file)">
                    <span class="file-icon">{{ file.type === 'directory' ? '📁' : getFileIcon(file.name) }}</span>
                    <span class="file-name">{{ file.name }}</span>
                  </td>
                  <td>{{ file.type === 'directory' ? '目录' : getFileType(file.name) }}</td>
                  <td>{{ formatFileSize(file.size) }}</td>
                  <td>{{ formatDate(file.mtime) }}</td>
                  <td>{{ file.permissions }}</td>
                  <td>
                    <div class="action-buttons">
                      <button 
                        class="btn btn-secondary btn-sm"
                        @click="viewFilePermissions(file)"
                      >权限</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- 文件编辑视图 -->
        <div id="file-editor" class="file-view" :class="{ 'active': activeView === 'editor' }">
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <button id="back-to-browser-btn" class="btn btn-secondary" @click="showBrowserView">返回</button>
              <span id="editing-file-name" class="file-name">{{ editingFile?.name || '' }}</span>
            </div>
            <div class="toolbar-right">
              <button id="save-file-btn" class="btn btn-primary" @click="saveFile">保存</button>
              <button id="revert-file-btn" class="btn btn-secondary" @click="revertFile">撤销</button>
              <div class="dropdown">
                <button id="version-history-btn" class="btn btn-secondary">版本历史</button>
                <div id="version-dropdown" class="dropdown-content">
                  <!-- 版本历史将通过JavaScript动态加载 -->
                </div>
              </div>
            </div>
          </div>
          <div class="editor-container">
            <textarea id="file-content-editor" class="file-editor" v-model="fileContent"></textarea>
          </div>
        </div>
        
        <!-- 文件权限视图 -->
        <div id="file-permissions-view" class="file-view" :class="{ 'active': activeView === 'permissions' }">
          <div class="permissions-header">
            <button id="back-to-browser-from-permissions-btn" class="btn btn-secondary" @click="showBrowserView">返回</button>
            <h3 id="permissions-file-name">{{ permissionsFile?.name || '' }}</h3>
          </div>
          <div class="permissions-content" id="permissions-details">
            <!-- 文件权限详情将通过JavaScript动态加载 -->
            <div v-if="permissionsFile" class="permissions-form">
              <div class="form-group">
                <label>权限</label>
                <input type="text" v-model="permissionsFile.permissions">
              </div>
              <div class="form-actions">
                <button class="btn btn-primary">保存权限</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileManager',
  data() {
    return {
      whitelistDirs: [
        { name: '根目录', path: '/' },
        { name: '网站根目录', path: '/var/www' },
        { name: '配置文件', path: '/etc' }
      ],
      currentPath: '/',
      files: [
        { name: 'test.txt', type: 'file', size: 1024, mtime: '2026-01-01T10:00:00', permissions: 'rw-r--r--', path: '/test.txt' },
        { name: 'docs', type: 'directory', size: 0, mtime: '2026-01-01T09:30:00', permissions: 'rwxr-xr-x', path: '/docs' },
        { name: 'config.ini', type: 'file', size: 512, mtime: '2026-01-01T11:00:00', permissions: 'rw-r--r--', path: '/config.ini' }
      ],
      filteredFiles: [],
      searchQuery: '',
      selectedFiles: [],
      selectAll: false,
      loading: false,
      // 视图状态
      activeView: 'browser', // browser, editor, permissions
      editingFile: null,
      fileContent: '',
      permissionsFile: null
    }
  },
  methods: {
    // 视图切换
    showBrowserView() {
      this.activeView = 'browser'
      this.editingFile = null
      this.permissionsFile = null
    },
    
    // 文件操作
    navigateToDirectory(path) {
      this.currentPath = path
      this.refreshFiles()
    },
    
    navigateToParent() {
      const pathParts = this.currentPath.split('/').filter(Boolean)
      pathParts.pop()
      this.currentPath = pathParts.length > 0 ? '/' + pathParts.join('/') : '/'
      this.refreshFiles()
    },
    
    refreshFiles() {
      this.loading = true
      // 模拟API请求
      setTimeout(() => {
        this.filteredFiles = [...this.files]
        this.loading = false
      }, 500)
    },
    
    onSearch() {
      if (!this.searchQuery.trim()) {
        this.filteredFiles = [...this.files]
      } else {
        const query = this.searchQuery.toLowerCase()
        this.filteredFiles = this.files.filter(file => 
          file.name.toLowerCase().includes(query)
        )
      }
    },
    
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedFiles = this.filteredFiles.map(file => file.name)
      } else {
        this.selectedFiles = []
      }
    },
    
    // 文件操作
    createNewFile() {
      console.log('新建文件')
    },
    
    uploadFile() {
      console.log('上传文件')
    },
    
    deleteSelectedFiles() {
      console.log('删除文件:', this.selectedFiles)
    },
    
    editFile(file) {
      this.editingFile = file
      this.fileContent = '文件内容...'
      this.activeView = 'editor'
    },
    
    saveFile() {
      console.log('保存文件:', this.editingFile?.name)
    },
    
    revertFile() {
      console.log('撤销修改')
    },
    
    viewFilePermissions(file) {
      this.permissionsFile = file
      this.activeView = 'permissions'
    },
    
    // 辅助方法
    getFileIcon(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      const iconMap = {
        'txt': '📄',
        'md': '📝',
        'js': '📜',
        'css': '🎨',
        'html': '🌐',
        'json': '🔧',
        'py': '🐍',
        'java': '☕',
        'cpp': '++',
        'c': '📊',
        'h': '📁',
        'php': '🐘',
        'sql': '🗄️',
        'xml': '📄',
        'yaml': '📄',
        'yml': '📄',
        'config': '⚙️',
        'ini': '⚙️',
        'log': '📋',
        'pdf': '📄',
        'doc': '📄',
        'docx': '📄',
        'xls': '📊',
        'xlsx': '📊',
        'ppt': '📊',
        'pptx': '📊',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️',
        'gif': '🖼️',
        'svg': '🖼️',
        'mp3': '🎵',
        'wav': '🎵',
        'mp4': '🎬',
        'avi': '🎬',
        'mov': '🎬'
      }
      return iconMap[ext] || '📄'
    },
    
    getFileType(filename) {
      const ext = filename.split('.').pop().toLowerCase()
      if (['txt', 'md', 'doc', 'docx'].includes(ext)) return '文本文件'
      if (['js', 'css', 'html', 'json', 'py', 'java', 'cpp', 'c', 'h', 'php', 'sql'].includes(ext)) return '代码文件'
      if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)) return '图片文件'
      if (['mp3', 'wav'].includes(ext)) return '音频文件'
      if (['mp4', 'avi', 'mov'].includes(ext)) return '视频文件'
      if (['pdf'].includes(ext)) return 'PDF文件'
      if (['xls', 'xlsx'].includes(ext)) return 'Excel文件'
      if (['ppt', 'pptx'].includes(ext)) return 'PPT文件'
      if (['zip', 'rar', 'tar', 'gz'].includes(ext)) return '压缩文件'
      return '其他文件'
    },
    
    formatFileSize(size) {
      if (size === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(size) / Math.log(k))
      return parseFloat((size / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    
    formatDate(dateString) {
      const date = new Date(dateString)
      return date.toLocaleString()
    }
  },
  mounted() {
    this.refreshFiles()
  }
}
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

/* iOS 26 文件工具栏 */
.file-toolbar {
  padding: var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-quaternary);
}

.file-toolbar .search-box {
  display: flex;
  gap: var(--ios-space-2);
}

.file-toolbar input {
  flex: 1;
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-bg-primary);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.file-toolbar input:focus {
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.file-toolbar input::placeholder {
  color: var(--ios-label-tertiary);
}

/* iOS 26 表格容器 */
.table-container {
  flex: 1;
  overflow: auto;
  padding: var(--ios-space-2);
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table th {
  padding: var(--ios-space-3) var(--ios-space-4);
  text-align: left;
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  background: var(--ios-bg-secondary);
  border-bottom: 0.5px solid var(--ios-separator);
  white-space: nowrap;
}

.data-table th:first-child {
  border-radius: var(--ios-radius-lg) 0 0 0;
}

.data-table th:last-child {
  border-radius: 0 var(--ios-radius-lg) 0 0;
}

.data-table td {
  padding: var(--ios-space-3) var(--ios-space-4);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  border-bottom: 0.5px solid var(--ios-separator);
  vertical-align: middle;
}

.data-table td:first-child {
  border-radius: var(--ios-radius-lg);
}

.data-table td:last-child {
  border-radius: var(--ios-radius-lg);
}

/* iOS 26 文件行 */
.file-row {
  cursor: pointer;
  transition: all var(--ios-transition-fast);
}

.file-row:hover {
  background: var(--ios-fill-quaternary);
}

.file-row:active {
  background: var(--ios-fill-tertiary);
}

.file-row.directory {
  font-weight: var(--ios-weight-medium);
}

.file-icon {
  margin-right: var(--ios-space-2);
  font-size: var(--ios-text-body);
}

.file-name {
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
}

/* iOS 26 复选框 */
.data-table input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--ios-blue);
  cursor: pointer;
}

/* iOS 26 操作按钮 */
.action-buttons {
  display: flex;
  gap: var(--ios-space-2);
}

/* iOS 26 编辑器工具栏 */
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-quaternary);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
}

.editor-toolbar .file-name {
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
}

/* iOS 26 编辑器容器 */
.editor-container {
  flex: 1;
  padding: var(--ios-space-4);
  overflow: hidden;
}

.file-editor {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: var(--ios-radius-xl);
  padding: var(--ios-space-4);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption1);
  line-height: 1.6;
  resize: none;
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.file-editor:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

/* iOS 26 权限视图 */
.permissions-header {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-4);
  border-bottom: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-quaternary);
}

.permissions-header h3 {
  margin: 0;
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

.permissions-content {
  flex: 1;
  padding: var(--ios-space-5);
  overflow: auto;
}

.permissions-form {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-5);
  max-width: 400px;
}

.permissions-form .form-group {
  margin-bottom: 0;
}

.permissions-form label {
  display: block;
  margin-bottom: var(--ios-space-2);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.permissions-form input {
  width: 100%;
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-body);
  color: var(--ios-label-primary);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.permissions-form input:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

/* 加载和空状态 */
.loading-row td,
.no-data {
  text-align: center;
  padding: var(--ios-space-8);
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-subhead);
}

/* iOS 26 下拉菜单 */
.dropdown {
  position: relative;
}

.dropdown-content {
  position: absolute;
  top: calc(100% + var(--ios-space-2));
  right: 0;
  min-width: 180px;
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-xl);
  padding: var(--ios-space-2);
  z-index: var(--ios-z-dropdown);
  border: 0.5px solid var(--ios-separator);
  display: none;
}

.dropdown:hover .dropdown-content {
  display: block;
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
  background: #d63029;
}

.btn-sm {
  padding: var(--ios-space-1) var(--ios-space-3);
  font-size: var(--ios-text-caption1);
  border-radius: var(--ios-radius-md);
}

/* iOS 26 响应式调整 */
@media (max-width: 1024px) {
  .file-sidebar {
    width: 220px;
  }
}

@media (max-width: 768px) {
  .file-manager-container {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 220px);
  }
  
  .file-sidebar {
    width: 100%;
  }
  
  .editor-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--ios-space-3);
  }
  
  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }
  
  .toolbar-right {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
  
  .file-editor {
    min-height: 400px;
  }
  
  .data-table {
    font-size: var(--ios-text-caption1);
  }
  
  .data-table th,
  .data-table td {
    padding: var(--ios-space-2) var(--ios-space-3);
  }
}

@media (max-width: 480px) {
  .file-toolbar .search-box {
    flex-direction: column;
  }
  
  .file-toolbar .search-box .btn {
    width: 100%;
  }
}
</style>