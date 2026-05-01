<template>
  <div id="logs" class="page">
    <div class="page-header">
      <h2>日志查看</h2>
    </div>
    <div class="logs-container">
      <div class="logs-sidebar">
        <h3>日志文件</h3>
        <ul id="logs-list" class="logs-list">
          <li 
            v-for="log in logFiles" 
            :key="log.id"
            class="log-item"
            :class="{ 'active': selectedLog === log.id }"
            @click="selectLog(log.id)"
          >
            {{ log.name }}
          </li>
        </ul>
      </div>
      <div class="logs-content">
        <div class="logs-toolbar">
          <div class="toolbar-row">
            <div class="toolbar-group">
              <label for="log-lines">显示行数:</label>
              <input 
                type="number" 
                id="log-lines" 
                min="1" 
                max="1000" 
                value="100"
                v-model="logLines"
              >
              <button id="lines-apply-btn" class="btn btn-secondary" @click="applyLines">应用</button>
            </div>
            <div class="toolbar-group">
              <label for="tail-mode">实时刷新:</label>
              <input type="checkbox" id="tail-mode" v-model="tailMode">
            </div>
          </div>
          <div class="toolbar-row">
            <div class="toolbar-group" style="flex: 1;">
              <input 
                type="text" 
                id="log-search" 
                placeholder="搜索日志..." 
                style="width: 100%;"
                v-model="logSearch"
              >
            </div>
            <div class="toolbar-group">
              <button id="search-btn" class="btn btn-primary" @click="searchLog">搜索</button>
              <button id="refresh-btn" class="btn btn-secondary" @click="refreshLog">刷新</button>
            </div>
          </div>
        </div>
        <div id="log-content" class="log-content">
          <pre v-if="loading" class="loading">加载中...</pre>
          <pre v-else-if="logContent" class="log-text">{{ logContent }}</pre>
          <pre v-else class="no-data">没有日志内容</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Logs',
  data() {
    return {
      logFiles: [
        { id: 1, name: 'app.log' },
        { id: 2, name: 'error.log' },
        { id: 3, name: 'access.log' },
        { id: 4, name: 'system.log' }
      ],
      selectedLog: 1,
      logContent: '',
      logLines: 100,
      tailMode: false,
      logSearch: '',
      loading: false
    }
  },
  methods: {
    selectLog(logId) {
      this.selectedLog = logId
      this.loadLogContent()
    },
    loadLogContent() {
      this.loading = true
      // 模拟API请求
      setTimeout(() => {
        this.logContent = `日志文件 ${this.logFiles.find(l => l.id === this.selectedLog)?.name} 的内容...\n` + 
                          '2026-01-01 10:00:00 INFO: 系统启动\n' +
                          '2026-01-01 10:05:00 ERROR: 数据库连接失败\n' +
                          '2026-01-01 10:10:00 INFO: 用户 admin 登录\n' +
                          '2026-01-01 10:15:00 INFO: 服务 nginx 启动\n' +
                          '2026-01-01 10:20:00 WARNING: 内存使用率超过阈值\n'
        this.loading = false
      }, 500)
    },
    applyLines() {
      this.loadLogContent()
    },
    searchLog() {
      console.log('搜索日志:', this.logSearch)
      // 搜索逻辑
    },
    refreshLog() {
      this.loadLogContent()
    }
  },
  mounted() {
    this.loadLogContent()
  }
}
</script>

<style scoped>
.logs-container {
  display: flex;
  gap: 20px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.logs-sidebar {
  width: 250px;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.logs-sidebar h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #2c3e50;
}

.logs-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.log-item {
  padding: 10px;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 5px;
  transition: background-color 0.2s;
}

.log-item:hover {
  background-color: #e9ecef;
}

.log-item.active {
  background-color: #3498db;
  color: white;
}

.logs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.logs-toolbar {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.toolbar-row:last-child {
  margin-bottom: 0;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-content {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  flex: 1;
  overflow: hidden;
}

.log-text {
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  max-height: 500px;
  overflow-y: auto;
}

.no-data {
  text-align: center;
  color: #666;
  font-style: italic;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .logs-container {
    flex-direction: column;
  }
  
  .logs-sidebar {
    width: 100%;
  }
  
  .toolbar-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .toolbar-group {
    width: 100%;
  }
}
</style>