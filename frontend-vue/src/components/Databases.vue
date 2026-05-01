<template>
  <div id="databases" class="page">
    <div class="page-header">
      <h2>数据库管理</h2>
    </div>
    
    <!-- 数据库管理导航 -->
    <div class="db-nav-tabs">
      <button 
        class="db-tab" 
        :class="{ active: activeTab === 'db-configs' }"
        @click="activeTab = 'db-configs'"
      >连接配置</button>
      <button 
        class="db-tab" 
        :class="{ active: activeTab === 'db-manager' }"
        @click="activeTab = 'db-manager'"
      >数据库管理</button>
      <button 
        class="db-tab" 
        :class="{ active: activeTab === 'db-backups' }"
        @click="activeTab = 'db-backups'"
      >备份恢复</button>
      <button 
        class="db-tab" 
        :class="{ active: activeTab === 'db-monitor' }"
        @click="activeTab = 'db-monitor'"
      >性能监控</button>
    </div>
    
    <!-- 连接配置页面 -->
    <div id="db-configs" class="db-tab-content" v-if="activeTab === 'db-configs'">
      <div class="page-actions">
        <button id="add-db-config-btn" class="btn btn-primary" @click="addDbConfig">添加数据库配置</button>
        <button id="refresh-db-configs-btn" class="btn btn-secondary" @click="refreshDbConfigs">刷新</button>
      </div>
      <div class="table-container">
        <table id="db-configs-table" class="data-table">
          <thead>
            <tr>
              <th>配置ID</th>
              <th>数据库类型</th>
              <th>主机</th>
              <th>端口</th>
              <th>用户名</th>
              <th>描述</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="loading-row">
              <td colspan="8" class="loading">加载中...</td>
            </tr>
            <tr v-else-if="dbConfigs.length === 0">
              <td colspan="8" class="no-data">没有找到数据库配置</td>
            </tr>
            <tr 
              v-for="config in dbConfigs" 
              :key="config.id"
              class="config-row"
            >
              <td>{{ config.id }}</td>
              <td>{{ config.type }}</td>
              <td>{{ config.host }}</td>
              <td>{{ config.port }}</td>
              <td>{{ config.username }}</td>
              <td>{{ config.description }}</td>
              <td>
                <span :class="['status-badge', `status-${config.status.toLowerCase()}`]">
                  {{ config.status }}
                </span>
              </td>
              <td>
                <div class="action-buttons">
                  <button 
                    class="btn btn-secondary btn-sm"
                    @click="editDbConfig(config)"
                  >编辑</button>
                  <button 
                    class="btn btn-danger btn-sm"
                    @click="deleteDbConfig(config.id)"
                  >删除</button>
                  <button 
                    class="btn btn-success btn-sm"
                    v-if="config.status === 'Inactive'"
                    @click="testDbConnection(config)"
                  >测试连接</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- 数据库管理页面 -->
    <div id="db-manager" class="db-tab-content" v-if="activeTab === 'db-manager'">
      <div class="db-manager-container">
        <div class="db-selector">
          <div class="form-group">
            <label for="db-config-select">选择数据库配置</label>
            <select id="db-config-select" v-model="selectedDbConfig">
              <option value="">-- 选择配置 --</option>
              <option 
                v-for="config in dbConfigs" 
                :key="config.id"
                :value="config.id"
              >
                {{ config.description }} ({{ config.type }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label for="database-select">选择数据库</label>
            <select id="database-select" :disabled="!selectedDbConfig">
              <option value="">-- 选择数据库 --</option>
              <option 
                v-for="db in databases" 
                :key="db.name"
                :value="db.name"
              >
                {{ db.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label for="table-select">选择表</label>
            <select id="table-select" :disabled="!selectedDbConfig">
              <option value="">-- 选择表 --</option>
              <option 
                v-for="table in tables" 
                :key="table.name"
                :value="table.name"
              >
                {{ table.name }}
              </option>
            </select>
          </div>
        </div>
        
        <!-- SQL查询编辑器 -->
        <div class="sql-editor-container">
          <div class="editor-header">
            <h3>SQL查询编辑器</h3>
            <div class="editor-actions">
              <button id="execute-sql-btn" class="btn btn-primary" @click="executeSql">执行查询</button>
              <button id="clear-sql-btn" class="btn btn-secondary" @click="clearSql">清空</button>
              <select id="result-limit" v-model="resultLimit">
                <option value="100">显示100行</option>
                <option value="500">显示500行</option>
                <option value="1000">显示1000行</option>
                <option value="all">显示所有行</option>
              </select>
            </div>
          </div>
          <div class="editor-body">
            <textarea 
              id="sql-editor" 
              placeholder="在此输入SQL查询..."
              v-model="sqlQuery"
            ></textarea>
          </div>
          <div class="editor-footer">
            <div id="query-status" class="query-status">就绪</div>
          </div>
        </div>
        
        <!-- 查询结果 -->
        <div class="query-results">
          <div class="results-header">
            <h3>查询结果</h3>
            <div id="query-stats" class="query-stats">{{ queryStats }}</div>
          </div>
          <div id="results-container" class="results-container">
            <!-- 查询结果将通过JavaScript动态加载 -->
            <div v-if="queryResults.length > 0" class="results-table">
              <table class="data-table">
                <thead>
                  <tr>
                    <th v-for="column in resultColumns" :key="column">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in queryResults" :key="index">
                    <td v-for="column in resultColumns" :key="column">{{ row[column] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else-if="sqlQuery" class="no-data">没有查询结果</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 备份恢复页面 -->
    <div id="db-backups" class="db-tab-content" v-if="activeTab === 'db-backups'">
      <div class="backup-nav-tabs">
        <button 
          class="backup-tab" 
          :class="{ active: backupTab === 'backup-configs' }"
          @click="backupTab = 'backup-configs'"
        >备份配置</button>
        <button 
          class="backup-tab" 
          :class="{ active: backupTab === 'backup-history' }"
          @click="backupTab = 'backup-history'"
        >备份历史</button>
      </div>
      
      <!-- 备份配置 -->
      <div id="backup-configs" class="backup-tab-content" v-if="backupTab === 'backup-configs'">
        <div class="page-actions">
          <button id="add-backup-config-btn" class="btn btn-primary" @click="addBackupConfig">添加备份配置</button>
          <button id="refresh-backup-configs-btn" class="btn btn-secondary" @click="refreshBackupConfigs">刷新</button>
        </div>
        <div class="table-container">
          <table id="backup-configs-table" class="data-table">
            <thead>
              <tr>
                <th>配置ID</th>
                <th>数据库</th>
                <th>备份类型</th>
                <th>调度</th>
                <th>保留天数</th>
                <th>压缩</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading" class="loading-row">
                <td colspan="8" class="loading">加载中...</td>
              </tr>
              <tr v-else-if="backupConfigs.length === 0">
                <td colspan="8" class="no-data">没有找到备份配置</td>
              </tr>
              <tr 
                v-for="config in backupConfigs" 
                :key="config.id"
                class="backup-config-row"
              >
                <td>{{ config.id }}</td>
                <td>{{ config.database }}</td>
                <td>{{ config.type }}</td>
                <td>{{ config.schedule }}</td>
                <td>{{ config.retention }}</td>
                <td>{{ config.compression ? '是' : '否' }}</td>
                <td>
                  <span :class="['status-badge', `status-${config.status.toLowerCase()}`]">
                    {{ config.status }}
                  </span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button 
                      class="btn btn-secondary btn-sm"
                      @click="editBackupConfig(config)"
                    >编辑</button>
                    <button 
                      class="btn btn-danger btn-sm"
                      @click="deleteBackupConfig(config.id)"
                    >删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- 备份历史 -->
      <div id="backup-history" class="backup-tab-content" v-if="backupTab === 'backup-history'">
        <div class="backup-history-filters">
          <div class="form-group">
            <label for="backup-db-config-select">数据库配置</label>
            <select id="backup-db-config-select">
              <option value="">-- 所有配置 --</option>
              <!-- 数据库配置将通过JavaScript动态加载 -->
            </select>
          </div>
          <div class="form-group">
            <label for="backup-db-name-select">数据库</label>
            <select id="backup-db-name-select">
              <!-- 数据库列表将通过JavaScript动态加载 -->
            </select>
          </div>
        </div>
        <!-- 备份历史表格 -->
        <div class="table-container">
          <table id="backup-history-table" class="data-table">
            <thead>
              <tr>
                <th>备份ID</th>
                <th>数据库</th>
                <th>类型</th>
                <th>大小</th>
                <th>时间</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading" class="loading-row">
                <td colspan="7" class="loading">加载中...</td>
              </tr>
              <tr v-else-if="backupHistory.length === 0">
                <td colspan="7" class="no-data">没有备份历史</td>
              </tr>
              <tr 
                v-for="backup in backupHistory" 
                :key="backup.id"
                class="backup-history-row"
              >
                <td>{{ backup.id }}</td>
                <td>{{ backup.database }}</td>
                <td>{{ backup.type }}</td>
                <td>{{ backup.size }}</td>
                <td>{{ backup.time }}</td>
                <td>
                  <span :class="['status-badge', `status-${backup.status.toLowerCase()}`]">
                    {{ backup.status }}
                  </span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button 
                      class="btn btn-secondary btn-sm"
                      @click="restoreBackup(backup.id)"
                    >恢复</button>
                    <button 
                      class="btn btn-danger btn-sm"
                      @click="deleteBackup(backup.id)"
                    >删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- 性能监控页面 -->
    <div id="db-monitor" class="db-tab-content" v-if="activeTab === 'db-monitor'">
      <div class="monitor-section">
        <h3>数据库性能监控</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <h4>连接数</h4>
            <div class="stat-value">{{ dbStats.connections }}</div>
          </div>
          <div class="stat-card">
            <h4>查询/秒</h4>
            <div class="stat-value">{{ dbStats.queriesPerSecond }}</div>
          </div>
          <div class="stat-card">
            <h4>慢查询</h4>
            <div class="stat-value">{{ dbStats.slowQueries }}</div>
          </div>
          <div class="stat-card">
            <h4>缓存命中率</h4>
            <div class="stat-value">{{ dbStats.cacheHitRate }}%</div>
          </div>
        </div>
      </div>
      <!-- 慢查询列表 -->
      <div class="section">
        <h4>慢查询日志</h4>
        <div class="table-container">
          <table id="slow-queries-table" class="data-table">
            <thead>
              <tr>
                <th>耗时(ms)</th>
                <th>时间</th>
                <th>查询</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="query in slowQueries" :key="query.id">
                <td>{{ query.time }}</td>
                <td>{{ query.timestamp }}</td>
                <td class="query-text">{{ query.query }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Databases',
  data() {
    return {
      // 标签页状态
      activeTab: 'db-configs',
      backupTab: 'backup-configs',
      
      // 数据库配置
      dbConfigs: [
        {
          id: 1,
          type: 'MySQL',
          host: 'localhost',
          port: 3306,
          username: 'root',
          description: '本地MySQL数据库',
          status: 'Active'
        },
        {
          id: 2,
          type: 'SQL Server',
          host: '192.168.1.100',
          port: 1433,
          username: 'sa',
          description: '远程SQL Server数据库',
          status: 'Inactive'
        }
      ],
      
      // 数据库和表
      databases: [
        { name: 'mysql' },
        { name: 'test_db' },
        { name: 'wordpress' }
      ],
      tables: [
        { name: 'users' },
        { name: 'posts' },
        { name: 'comments' }
      ],
      
      // SQL查询相关
      selectedDbConfig: '',
      sqlQuery: '',
      resultLimit: '100',
      queryResults: [],
      resultColumns: [],
      queryStats: '',
      
      // 备份配置
      backupConfigs: [
        {
          id: 1,
          database: 'test_db',
          type: 'Full',
          schedule: '0 0 * * *',
          retention: 7,
          compression: true,
          status: 'Active'
        }
      ],
      
      // 备份历史
      backupHistory: [
        {
          id: 1,
          database: 'test_db',
          type: 'Full',
          size: '10.5 MB',
          time: '2026-01-01 00:00:00',
          status: 'Success'
        },
        {
          id: 2,
          database: 'test_db',
          type: 'Incremental',
          size: '2.3 MB',
          time: '2026-01-01 12:00:00',
          status: 'Success'
        }
      ],
      
      // 数据库性能监控
      dbStats: {
        connections: 12,
        queriesPerSecond: 45,
        slowQueries: 2,
        cacheHitRate: 98
      },
      slowQueries: [
        {
          id: 1,
          time: 1500,
          timestamp: '2026-01-01 10:00:00',
          query: 'SELECT * FROM users WHERE age > 30'
        },
        {
          id: 2,
          time: 800,
          timestamp: '2026-01-01 10:05:00',
          query: 'UPDATE posts SET views = views + 1 WHERE id = 123'
        }
      ],
      
      // 加载状态
      loading: false
    }
  },
  methods: {
    // 数据库配置操作
    refreshDbConfigs() {
      console.log('刷新数据库配置')
    },
    
    addDbConfig() {
      console.log('添加数据库配置')
    },
    
    editDbConfig(config) {
      console.log('编辑数据库配置:', config.id)
    },
    
    deleteDbConfig(id) {
      console.log('删除数据库配置:', id)
    },
    
    testDbConnection(config) {
      console.log('测试数据库连接:', config.id)
    },
    
    // SQL查询操作
    executeSql() {
      console.log('执行SQL:', this.sqlQuery)
      // 模拟查询结果
      this.resultColumns = ['id', 'name', 'email']
      this.queryResults = [
        { id: 1, name: 'admin', email: 'admin@example.com' },
        { id: 2, name: 'user1', email: 'user1@example.com' },
        { id: 3, name: 'user2', email: 'user2@example.com' }
      ]
      this.queryStats = `共 ${this.queryResults.length} 行，耗时 0.123 秒`
    },
    
    clearSql() {
      this.sqlQuery = ''
      this.queryResults = []
      this.resultColumns = []
      this.queryStats = ''
    },
    
    // 备份配置操作
    refreshBackupConfigs() {
      console.log('刷新备份配置')
    },
    
    addBackupConfig() {
      console.log('添加备份配置')
    },
    
    editBackupConfig(config) {
      console.log('编辑备份配置:', config.id)
    },
    
    deleteBackupConfig(id) {
      console.log('删除备份配置:', id)
    },
    
    // 备份历史操作
    restoreBackup(id) {
      console.log('恢复备份:', id)
    },
    
    deleteBackup(id) {
      console.log('删除备份:', id)
    }
  }
}
</script>

<style scoped>
/* iOS 26 数据库管理页面 */
#databases {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-5);
}

/* iOS 26 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  margin: 0;
  font-size: var(--ios-text-large-title);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  letter-spacing: var(--ios-tracking-tight);
}

.page-actions {
  display: flex;
  gap: var(--ios-space-2);
}

/* iOS 26 按钮系统 */
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

.btn-success {
  background: var(--ios-green);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #2db84e;
}

.btn-sm {
  padding: var(--ios-space-1) var(--ios-space-3);
  font-size: var(--ios-text-caption1);
  border-radius: var(--ios-radius-md);
}

/* iOS 26 标签页导航 */
.db-nav-tabs,
.backup-nav-tabs {
  display: flex;
  gap: var(--ios-space-2);
  padding: var(--ios-space-1);
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-lg);
}

.db-tab,
.backup-tab {
  padding: var(--ios-space-2) var(--ios-space-4);
  border: none;
  background: transparent;
  border-radius: var(--ios-radius-md);
  cursor: pointer;
  font-family: var(--ios-font-family);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
  transition: all var(--ios-transition-fast);
}

.db-tab:hover,
.backup-tab:hover {
  color: var(--ios-label-primary);
}

.db-tab:active,
.backup-tab:active {
  transform: scale(0.98);
}

.db-tab.active,
.backup-tab.active {
  background: var(--ios-bg-primary);
  color: var(--ios-label-primary);
  box-shadow: var(--ios-shadow-sm);
}

.db-tab-content,
.backup-tab-content {
  display: block;
}

/* iOS 26 表格容器 */
.table-container {
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  overflow: hidden;
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
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.data-table td {
  padding: var(--ios-space-3) var(--ios-space-4);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  border-bottom: 0.5px solid var(--ios-separator);
  vertical-align: middle;
}

.data-table tbody tr {
  transition: background var(--ios-transition-fast);
}

.data-table tbody tr:hover {
  background: var(--ios-fill-quaternary);
}

.data-table tbody tr:active {
  background: var(--ios-fill-tertiary);
}

/* iOS 26 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--ios-space-1) var(--ios-space-3);
  font-size: var(--ios-text-caption2);
  font-weight: var(--ios-weight-semibold);
  border-radius: var(--ios-radius-full);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.status-active {
  background: rgba(52, 199, 89, 0.15);
  color: var(--ios-green);
}

.status-inactive {
  background: rgba(142, 142, 147, 0.15);
  color: var(--ios-gray-1);
}

.status-success {
  background: rgba(52, 199, 89, 0.15);
  color: var(--ios-green);
}

.status-error {
  background: rgba(255, 59, 48, 0.15);
  color: var(--ios-red);
}

/* iOS 26 操作按钮组 */
.action-buttons {
  display: flex;
  gap: var(--ios-space-2);
}

/* iOS 26 数据库选择器 */
.db-selector {
  display: flex;
  gap: var(--ios-space-4);
  padding: var(--ios-space-5);
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-2);
  min-width: 180px;
}

.form-group label {
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.form-group select,
.form-group input {
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-family: var(--ios-font-family);
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.form-group select:focus,
.form-group input:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.form-group select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* iOS 26 SQL编辑器 */
.sql-editor-container {
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  overflow: hidden;
}

.editor-header,
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border-bottom: 0.5px solid var(--ios-separator);
}

.editor-header h3,
.results-header h3,
.monitor-section h3 {
  margin: 0;
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
}

.editor-actions select {
  padding: var(--ios-space-2) var(--ios-space-3);
  background: var(--ios-bg-primary);
  border: none;
  border-radius: var(--ios-radius-md);
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-primary);
  outline: none;
}

.editor-body {
  padding: var(--ios-space-4);
}

#sql-editor {
  width: 100%;
  height: 200px;
  padding: var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-xl);
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption1);
  line-height: 1.6;
  color: var(--ios-label-primary);
  resize: vertical;
  outline: none;
  transition: all var(--ios-transition-fast);
}

#sql-editor:focus {
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

#sql-editor::placeholder {
  color: var(--ios-label-tertiary);
}

.editor-footer {
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border-top: 0.5px solid var(--ios-separator);
}

.query-status {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
}

/* iOS 26 查询结果 */
.query-results {
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  overflow: hidden;
}

.query-stats {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
}

.results-container {
  padding: var(--ios-space-4);
  max-height: 400px;
  overflow: auto;
}

.query-text {
  font-family: var(--ios-font-mono);
  font-size: var(--ios-text-caption2);
  line-height: 1.5;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* iOS 26 性能监控 */
.monitor-section {
  background: var(--ios-card-bg);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-card-shadow);
  padding: var(--ios-space-5);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--ios-space-4);
}

.stat-card {
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-xl);
  padding: var(--ios-space-4);
  text-align: center;
  transition: all var(--ios-transition-fast);
}

.stat-card:hover {
  background: var(--ios-fill-tertiary);
}

.stat-card h4 {
  margin: 0 0 var(--ios-space-2);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  font-size: var(--ios-text-large-title);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
}

.section {
  margin-top: var(--ios-space-5);
}

.section h4 {
  margin: 0 0 var(--ios-space-4);
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

/* 加载和空状态 */
.loading-row td,
.no-data {
  text-align: center;
  padding: var(--ios-space-8);
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-subhead);
}

/* 备份历史筛选器 */
.backup-history-filters {
  display: flex;
  gap: var(--ios-space-4);
  margin-bottom: var(--ios-space-4);
  padding: var(--ios-space-4);
  background: var(--ios-card-bg);
  border-radius: var(--ios-radius-xl);
}

/* iOS 26 响应式调整 */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .db-selector {
    flex-direction: column;
    gap: var(--ios-space-3);
  }
  
  .form-group {
    min-width: 100%;
  }
  
  .editor-header,
  .results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--ios-space-3);
  }
  
  .editor-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .db-nav-tabs,
  .backup-nav-tabs {
    flex-wrap: wrap;
  }
  
  .db-tab,
  .backup-tab {
    flex: 1;
    text-align: center;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .backup-history-filters {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--ios-space-3);
  }
  
  .page-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .page-actions .btn {
    flex: 1;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: var(--ios-space-1);
  }
  
  .action-buttons .btn {
    width: 100%;
  }
}
</style>