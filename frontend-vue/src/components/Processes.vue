<template>
  <div id="processes" class="page">
    <div class="page-header">
      <h2>进程管理</h2>
      <div class="page-actions">
        <div class="search-box">
          <input 
            type="text" 
            id="process-search" 
            placeholder="搜索进程名称、PID或命令..."
            v-model="searchQuery"
            @input="onSearch"
          >
          <button id="search-btn" class="btn btn-primary" @click="onSearch">搜索</button>
          <button id="clear-search-btn" class="btn btn-secondary" @click="clearSearch">清空</button>
        </div>
        <div class="batch-actions" style="margin-left: 20px;">
          <button 
            id="batch-kill-btn" 
            class="btn btn-danger" 
            :disabled="selectedProcesses.length === 0"
            @click="batchKillProcesses"
          >批量结束</button>
          <button id="refresh-processes-btn" class="btn btn-secondary" @click="refreshProcesses">刷新</button>
        </div>
      </div>
    </div>
    <div class="table-container">
      <table id="processes-table" class="data-table">
        <thead>
          <tr>
            <th>
              <input 
                type="checkbox" 
                id="select-all-processes"
                v-model="selectAll"
                @change="toggleSelectAll"
              >
            </th>
            <th 
              data-sort="pid" 
              class="sortable"
              @click="sortBy('pid')"
            >
              PID 
              <span class="sort-indicator">{{ getSortIndicator('pid') }}</span>
            </th>
            <th 
              data-sort="name" 
              class="sortable"
              @click="sortBy('name')"
            >
              名称 
              <span class="sort-indicator">{{ getSortIndicator('name') }}</span>
            </th>
            <th 
              data-sort="cpu_percent" 
              class="sortable"
              @click="sortBy('cpu_percent')"
            >
              CPU% 
              <span class="sort-indicator">{{ getSortIndicator('cpu_percent') }}</span>
            </th>
            <th 
              data-sort="memory_percent" 
              class="sortable"
              @click="sortBy('memory_percent')"
            >
              内存% 
              <span class="sort-indicator">{{ getSortIndicator('memory_percent') }}</span>
            </th>
            <th 
              data-sort="create_time" 
              class="sortable"
              @click="sortBy('create_time')"
            >
              启动时间 
              <span class="sort-indicator">{{ getSortIndicator('create_time') }}</span>
            </th>
            <th>状态</th>
            <th>用户名</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="loading-row">
            <td colspan="9" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="filteredProcesses.length === 0">
            <td colspan="9" class="no-data">没有找到匹配的进程</td>
          </tr>
          <tr 
            v-for="process in filteredProcesses" 
            :key="process.pid"
            class="process-row"
          >
            <td>
              <input 
                type="checkbox" 
                :value="process.pid"
                v-model="selectedProcesses"
              >
            </td>
            <td>{{ process.pid }}</td>
            <td>{{ process.name }}</td>
            <td>{{ process.cpu_percent }}%</td>
            <td>{{ process.memory_percent }}%</td>
            <td>{{ formatDate(process.create_time) }}</td>
            <td>
              <span :class="['status-badge', `status-${process.status.toLowerCase()}`]">
                {{ process.status }}
              </span>
            </td>
            <td>{{ process.username }}</td>
            <td>
              <div class="action-buttons">
                <button 
                  class="btn btn-danger btn-sm"
                  @click="killProcess(process.pid)"
                >结束</button>
                <button 
                  class="btn btn-secondary btn-sm"
                  @click="viewProcessDetails(process)"
                >详情</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 进程详情模态框 -->
    <div v-if="showDetails" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>进程详情</h3>
          <button class="close-btn" @click="showDetails = false">&times;</button>
        </div>
        <div class="modal-body" v-if="selectedProcess">
          <div class="info-grid">
            <div class="info-item">
              <label>PID</label>
              <span>{{ selectedProcess.pid }}</span>
            </div>
            <div class="info-item">
              <label>名称</label>
              <span>{{ selectedProcess.name }}</span>
            </div>
            <div class="info-item">
              <label>命令</label>
              <span>{{ selectedProcess.command }}</span>
            </div>
            <div class="info-item">
              <label>CPU使用率</label>
              <span>{{ selectedProcess.cpu_percent }}%</span>
            </div>
            <div class="info-item">
              <label>内存使用率</label>
              <span>{{ selectedProcess.memory_percent }}%</span>
            </div>
            <div class="info-item">
              <label>内存使用量</label>
              <span>{{ formatBytes(selectedProcess.memory_used) }}</span>
            </div>
            <div class="info-item">
              <label>状态</label>
              <span>{{ selectedProcess.status }}</span>
            </div>
            <div class="info-item">
              <label>用户名</label>
              <span>{{ selectedProcess.username }}</span>
            </div>
            <div class="info-item">
              <label>启动时间</label>
              <span>{{ formatDate(selectedProcess.create_time) }}</span>
            </div>
            <div class="info-item">
              <label>父进程PID</label>
              <span>{{ selectedProcess.ppid }}</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showDetails = false">关闭</button>
          <button 
            class="btn btn-danger" 
            @click="killProcess(selectedProcess.pid)"
          >结束进程</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Processes',
  data() {
    return {
      processes: [],
      filteredProcesses: [],
      searchQuery: '',
      selectedProcesses: [],
      selectAll: false,
      loading: false,
      sortKey: 'pid',
      sortOrder: 'asc',
      showDetails: false,
      selectedProcess: null,
      // 模拟数据
      mockProcesses: [
        { pid: 1234, name: 'chrome.exe', cpu_percent: 12.5, memory_percent: 8.2, create_time: '2026-01-01T10:00:00', status: 'Running', username: 'admin', command: 'chrome.exe --user-data-dir=...', memory_used: 134217728, ppid: 1000 },
        { pid: 5678, name: 'node.exe', cpu_percent: 8.3, memory_percent: 12.1, create_time: '2026-01-01T11:30:00', status: 'Running', username: 'admin', command: 'node server.js', memory_used: 201326592, ppid: 1000 },
        { pid: 9012, name: 'python.exe', cpu_percent: 25.7, memory_percent: 15.3, create_time: '2026-01-01T12:15:00', status: 'Running', username: 'admin', command: 'python app.py', memory_used: 251658240, ppid: 1000 },
        { pid: 3456, name: 'explorer.exe', cpu_percent: 3.2, memory_percent: 4.8, create_time: '2026-01-01T09:00:00', status: 'Running', username: 'admin', command: 'explorer.exe', memory_used: 80530636, ppid: 1000 },
        { pid: 7890, name: 'svchost.exe', cpu_percent: 1.5, memory_percent: 2.1, create_time: '2026-01-01T08:45:00', status: 'Running', username: 'system', command: 'svchost.exe -k netsvcs', memory_used: 34603008, ppid: 4 }
      ]
    }
  },
  mounted() {
    this.fetchProcesses()
    // 定期刷新进程列表
    this.refreshInterval = setInterval(() => {
      this.fetchProcesses()
    }, 10000)
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    fetchProcesses() {
      this.loading = true
      // 构建API请求URL
      let url = '/api/processes?sort_by=' + this.sortKey + '&sort_order=' + this.sortOrder
      if (this.searchQuery.trim()) {
        url += '&search=' + encodeURIComponent(this.searchQuery.trim())
      }
      
      // 使用Vuex store中的apiRequest action，自动包含token认证
      this.$store.dispatch('apiRequest', {
        url: url,
        method: 'GET'
      })
        .then(data => {
          if (data.status === 'success') {
            // 处理后端返回的进程数据，确保与前端组件期望的结构匹配
            this.processes = (data.processes || []).map(process => ({
              ...process,
              // 将full_command映射到command，后端使用full_command，前端使用command
              command: process.full_command || '',
              // 添加前端期望但后端没有返回的字段，使用默认值
              memory_used: 0,
              ppid: 0
            }))
            this.filteredProcesses = [...this.processes]
          } else {
            console.error('获取进程列表失败:', data.message)
            this.processes = []
            this.filteredProcesses = []
          }
          this.loading = false
        })
        .catch(error => {
          console.error('获取进程列表失败:', error.message || error)
          this.processes = []
          this.filteredProcesses = []
          this.loading = false
        })
    },
    refreshProcesses() {
      this.fetchProcesses()
    },
    onSearch() {
      // 直接调用fetchProcesses，API会处理搜索
      this.fetchProcesses()
    },
    clearSearch() {
      this.searchQuery = ''
      this.fetchProcesses()
    },
    sortBy(key) {
      if (this.sortKey === key) {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc'
      } else {
        this.sortKey = key
        this.sortOrder = 'asc'
      }
      this.fetchProcesses() // 让API处理排序
    },
    sortProcesses() {
      // 前端排序作为备用
      this.filteredProcesses.sort((a, b) => {
        let aVal = a[this.sortKey]
        let bVal = b[this.sortKey]
        
        // 处理数字比较
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return this.sortOrder === 'asc' ? aVal - bVal : bVal - aVal
        }
        
        // 处理字符串比较
        aVal = String(aVal).toLowerCase()
        bVal = String(bVal).toLowerCase()
        
        if (aVal < bVal) {
          return this.sortOrder === 'asc' ? -1 : 1
        }
        if (aVal > bVal) {
          return this.sortOrder === 'asc' ? 1 : -1
        }
        return 0
      })
    },
    getSortIndicator(key) {
      if (this.sortKey !== key) return ''
      return this.sortOrder === 'asc' ? '↑' : '↓'
    },
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedProcesses = this.filteredProcesses.map(p => p.pid)
      } else {
        this.selectedProcesses = []
      }
    },
    killProcess(pid) {
      // 结束进程
      this.$store.dispatch('apiRequest', {
        url: `/api/processes/${pid}/kill`,
        method: 'POST'
      })
        .then(data => {
          if (data.status === 'success') {
            // 更新本地数据
            this.processes = this.processes.filter(p => p.pid !== pid)
            this.filteredProcesses = this.filteredProcesses.filter(p => p.pid !== pid)
            this.selectedProcesses = this.selectedProcesses.filter(id => id !== pid)
            if (this.showDetails && this.selectedProcess && this.selectedProcess.pid === pid) {
              this.showDetails = false
            }
          } else {
            console.error('结束进程失败:', data.message)
            alert('结束进程失败: ' + data.message)
          }
        })
        .catch(error => {
          console.error('结束进程失败:', error)
          alert('结束进程失败: ' + error.message)
        })
    },
    batchKillProcesses() {
      if (this.selectedProcesses.length === 0) return
      
      // 批量结束进程
      this.$store.dispatch('apiRequest', {
        url: `/api/processes/batch/kill`,
        method: 'POST',
        body: JSON.stringify({ pids: this.selectedProcesses })
      })
        .then(data => {
          if (data.status === 'success') {
            // 刷新进程列表
            this.fetchProcesses()
            this.selectedProcesses = []
            this.selectAll = false
          } else {
            console.error('批量结束进程失败:', data.message)
            alert('批量结束进程失败: ' + data.message)
          }
        })
        .catch(error => {
          console.error('批量结束进程失败:', error)
          alert('批量结束进程失败: ' + error.message)
        })
    },
    viewProcessDetails(process) {
      this.selectedProcess = process
      this.showDetails = true
    },
    formatDate(dateString) {
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    formatBytes(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
  },
  watch: {
    // 当过滤后的进程列表变化时，检查全选状态
    filteredProcesses() {
      this.selectAll = this.selectedProcesses.length === this.filteredProcesses.length && this.filteredProcesses.length > 0
    }
  }
}
</script>

<style scoped>
/* 页面样式 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--glass-border);
}

.page-header h2 {
  margin: 0;
  color: var(--text-primary);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 搜索框样式 */
.search-box {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-box input {
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-border);
  border-radius: var(--border-radius-md);
  font-size: 14px;
  color: var(--text-primary);
  width: 300px;
  transition: var(--transition-smooth);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}

.search-box input:focus {
  outline: none;
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.search-box input::placeholder {
  color: var(--text-muted);
}

/* 批量操作样式 */
.batch-actions {
  display: flex;
  gap: 10px;
}

/* 表格样式 */
.table-container {
  overflow-x: auto;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  border: 1px solid var(--glass-border);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--glass-shadow);
  margin-bottom: 20px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  color: var(--text-primary);
}

.data-table th,
.data-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  transition: var(--transition-smooth);
}

.data-table th {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  transition: var(--transition-smooth);
}

.data-table th:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.data-table tr {
  transition: var(--transition-smooth);
}

.data-table tr:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: translateX(4px);
}

.sort-indicator {
  margin-left: 5px;
  font-size: 12px;
  opacity: 0.5;
  transition: var(--transition-smooth);
}

.data-table th:hover .sort-indicator {
  opacity: 1;
}

.process-row {
  cursor: pointer;
}

/* 状态徽章 */
.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  display: inline-block;
}

.status-running {
  background: rgba(67, 233, 123, 0.2);
  color: #43e97b;
  border: 1px solid rgba(67, 233, 123, 0.3);
}

.status-stopped {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  border: 1px solid rgba(255, 107, 107, 0.3);
}

.status-sleeping {
  background: rgba(149, 157, 165, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(149, 157, 165, 0.3);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 8px;
}

/* 模态框样式 */
.modal {
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  border: 1px solid var(--glass-border);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--glass-shadow);
  width: 80%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.05);
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-muted);
  transition: var(--transition-smooth);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius-sm);
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-body .info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.modal-body .info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.modal-body .info-item label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modal-body .info-item span {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--glass-border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  background: rgba(255, 255, 255, 0.05);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .page-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
    width: 100%;
  }
  
  .search-box {
    width: 100%;
    flex-direction: column;
  }
  
  .search-box input {
    width: 100%;
  }
  
  .batch-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
  
  .batch-actions .btn {
    flex: 1;
  }
  
  .modal-content {
    width: 95%;
    margin: 20px;
  }
  
  .modal-body .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>