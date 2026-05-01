<template>
  <div id="sites" class="page">
    <div class="page-header">
      <h2>站点管理</h2>
      <div class="page-actions">
        <button id="add-site-btn" class="btn btn-primary" @click="addNewSite">添加站点</button>
        <button id="refresh-sites-btn" class="btn btn-secondary" @click="refreshSites">刷新</button>
        <button 
          id="batch-delete-sites-btn" 
          class="btn btn-danger" 
          :disabled="selectedSites.length === 0"
          @click="batchDeleteSites"
        >批量删除</button>
      </div>
    </div>
    
    <!-- 站点列表视图 -->
    <div id="sites-list-view" class="site-view" :class="{ active: activeView === 'list' }">
      <div class="site-toolbar">
        <div class="search-box">
          <input 
            type="text" 
            id="site-search" 
            placeholder="搜索站点名称、目录..."
            v-model="searchQuery"
            @input="onSearch"
          >
          <button id="site-search-btn" class="btn btn-primary" @click="onSearch">搜索</button>
          <button id="site-filter-btn" class="btn btn-secondary" @click="toggleFilter">筛选</button>
          <button id="clear-site-filter-btn" class="btn btn-secondary" @click="clearFilter">清空筛选</button>
        </div>
        <div class="site-filters" v-if="showFilter" style="margin-top: 10px;">
          <label>状态筛选：</label>
          <select id="site-status-filter" v-model="statusFilter">
            <option value="">全部</option>
            <option value="running">运行中</option>
            <option value="stopped">已停止</option>
            <option value="pending">待处理</option>
            <option value="error">错误</option>
          </select>
          <label style="margin-left: 10px;">Web服务器：</label>
          <select id="site-web-server-filter" v-model="webServerFilter">
            <option value="">全部</option>
            <option value="nginx">Nginx</option>
            <option value="apache">Apache</option>
          </select>
        </div>
      </div>
      <div class="table-container">
        <table id="sites-table" class="data-table">
          <thead>
            <tr>
              <th>
                <input 
                  type="checkbox" 
                  id="select-all-sites"
                  v-model="selectAll"
                  @change="toggleSelectAll"
                >
              </th>
              <th>站点名称</th>
              <th>状态</th>
              <th>Web服务器</th>
              <th>PHP版本</th>
              <th>根目录</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="loading-row">
              <td colspan="8" class="loading">加载中...</td>
            </tr>
            <tr v-else-if="filteredSites.length === 0">
              <td colspan="8" class="no-data">没有找到站点</td>
            </tr>
            <tr 
              v-for="site in filteredSites" 
              :key="site.id"
              class="site-row"
            >
              <td>
                <input 
                  type="checkbox" 
                  :value="site.id"
                  v-model="selectedSites"
                >
              </td>
              <td>{{ site.name }}</td>
              <td>
                <span :class="['status-badge', `status-${site.status.toLowerCase()}`]">
                  {{ site.status }}
                </span>
              </td>
              <td>{{ site.webServer }}</td>
              <td>{{ site.phpVersion }}</td>
              <td>{{ site.rootDir }}</td>
              <td>{{ formatDate(site.createdAt) }}</td>
              <td>
                <div class="action-buttons">
                  <button 
                    class="btn btn-primary btn-sm"
                    @click="viewSiteDetails(site)"
                  >详情</button>
                  <button 
                    class="btn btn-secondary btn-sm"
                    @click="editSite(site)"
                  >编辑</button>
                  <button 
                    class="btn btn-danger btn-sm"
                    @click="deleteSite(site.id)"
                  >删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- 站点详情视图 -->
    <div id="site-details-view" class="site-view" :class="{ active: activeView === 'details' }">
      <div class="site-details-header">
        <button id="back-to-sites-btn" class="btn btn-secondary" @click="showListView">返回站点列表</button>
        <h3 id="site-details-name">{{ selectedSite?.name || '' }}</h3>
      </div>
      
      <div class="site-details-content" v-if="selectedSite">
        <!-- 站点基本信息 -->
        <div class="section">
          <h4>基本信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <label>站点ID</label>
              <span id="site-detail-id">{{ selectedSite.id }}</span>
            </div>
            <div class="info-item">
              <label>状态</label>
              <span id="site-detail-status">{{ selectedSite.status }}</span>
              <select 
                id="site-detail-status-select" 
                style="margin-left: 10px;"
                v-model="selectedSite.status"
              >
                <option value="running">运行中</option>
                <option value="stopped">已停止</option>
              </select>
              <button 
                id="update-site-status-btn" 
                class="btn btn-primary" 
                style="margin-left: 5px;"
                @click="updateSiteStatus"
              >更新</button>
            </div>
            <div class="info-item">
              <label>Web服务器</label>
              <span id="site-detail-web-server">{{ selectedSite.webServer }}</span>
            </div>
            <div class="info-item">
              <label>PHP版本</label>
              <span id="site-detail-php-version">{{ selectedSite.phpVersion }}</span>
            </div>
            <div class="info-item">
              <label>根目录</label>
              <span id="site-detail-root-dir">{{ selectedSite.rootDir }}</span>
            </div>
            <div class="info-item">
              <label>创建时间</label>
              <span id="site-detail-created-at">{{ formatDate(selectedSite.createdAt) }}</span>
            </div>
            <div class="info-item">
              <label>更新时间</label>
              <span id="site-detail-updated-at">{{ formatDate(selectedSite.updatedAt) }}</span>
            </div>
          </div>
          <button id="edit-site-btn" class="btn btn-primary" style="margin-top: 10px;">编辑站点信息</button>
        </div>
        
        <!-- 域名绑定 -->
        <div class="section">
          <div class="section-header">
            <h4>域名绑定</h4>
            <button id="add-domain-btn" class="btn btn-primary">添加域名</button>
          </div>
          <div class="table-container">
            <table id="domains-table" class="data-table">
              <thead>
                <tr>
                  <th>域名</th>
                  <th>状态</th>
                  <th>SSL状态</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(domain, index) in selectedSite.domains" :key="index">
                  <td>{{ domain.name }}</td>
                  <td>{{ domain.status }}</td>
                  <td>{{ domain.sslStatus }}</td>
                  <td>{{ formatDate(domain.createdAt) }}</td>
                  <td>
                    <button class="btn btn-danger btn-sm">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- 站点目录管理 -->
        <div class="section">
          <div class="section-header">
            <h4>站点目录</h4>
            <button id="open-site-dir-btn" class="btn btn-primary">打开目录</button>
          </div>
          <div id="site-directory-view">
            <!-- 站点目录将通过JavaScript动态加载 -->
            <div class="directory-content">
              <p>站点目录内容...</p>
            </div>
          </div>
        </div>
        
        <!-- 站点日志 -->
        <div class="section">
          <div class="section-header">
            <h4>站点日志</h4>
            <button id="view-site-logs-btn" class="btn btn-primary">查看日志</button>
          </div>
          <div id="site-logs-view" style="margin-top: 10px;">
            <div class="log-type-selector">
              <label>日志类型：</label>
              <select id="site-log-type" v-model="logType">
                <option value="access">访问日志</option>
                <option value="error">错误日志</option>
              </select>
              <button id="refresh-site-logs-btn" class="btn btn-secondary">刷新</button>
            </div>
            <div 
              class="log-content" 
              id="site-log-content" 
              style="margin-top: 10px; height: 300px; overflow-y: auto; background-color: #f5f5f5; padding: 10px; border-radius: 5px;"
            >
              {{ logContent }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Sites',
  data() {
    return {
      sites: [
        {
          id: 1,
          name: 'example.com',
          status: 'Running',
          webServer: 'Nginx',
          phpVersion: '7.4',
          rootDir: '/var/www/example.com',
          createdAt: '2026-01-01T10:00:00',
          updatedAt: '2026-01-01T10:00:00',
          domains: [
            {
              name: 'example.com',
              status: 'Active',
              sslStatus: 'Enabled',
              createdAt: '2026-01-01T10:00:00'
            },
            {
              name: 'www.example.com',
              status: 'Active',
              sslStatus: 'Enabled',
              createdAt: '2026-01-01T10:00:00'
            }
          ]
        },
        {
          id: 2,
          name: 'test.com',
          status: 'Stopped',
          webServer: 'Apache',
          phpVersion: '8.0',
          rootDir: '/var/www/test.com',
          createdAt: '2026-01-01T11:00:00',
          updatedAt: '2026-01-01T11:00:00',
          domains: [
            {
              name: 'test.com',
              status: 'Active',
              sslStatus: 'Disabled',
              createdAt: '2026-01-01T11:00:00'
            }
          ]
        }
      ],
      filteredSites: [],
      selectedSites: [],
      selectAll: false,
      searchQuery: '',
      showFilter: false,
      statusFilter: '',
      webServerFilter: '',
      loading: false,
      // 视图状态
      activeView: 'list', // list, details
      selectedSite: null,
      // 日志相关
      logType: 'access',
      logContent: '日志内容...'
    }
  },
  methods: {
    // 视图切换
    showListView() {
      this.activeView = 'list'
      this.selectedSite = null
    },
    
    // 站点操作
    refreshSites() {
      this.loading = true
      // 模拟API请求
      setTimeout(() => {
        this.filteredSites = [...this.sites]
        this.loading = false
      }, 500)
    },
    
    onSearch() {
      this.applyFilters()
    },
    
    toggleFilter() {
      this.showFilter = !this.showFilter
    },
    
    clearFilter() {
      this.statusFilter = ''
      this.webServerFilter = ''
      this.applyFilters()
    },
    
    applyFilters() {
      let result = [...this.sites]
      
      // 搜索过滤
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase()
        result = result.filter(site => 
          site.name.toLowerCase().includes(query) ||
          site.rootDir.toLowerCase().includes(query)
        )
      }
      
      // 状态过滤
      if (this.statusFilter) {
        result = result.filter(site => site.status.toLowerCase() === this.statusFilter.toLowerCase())
      }
      
      // Web服务器过滤
      if (this.webServerFilter) {
        result = result.filter(site => site.webServer.toLowerCase() === this.webServerFilter.toLowerCase())
      }
      
      this.filteredSites = result
    },
    
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedSites = this.filteredSites.map(site => site.id)
      } else {
        this.selectedSites = []
      }
    },
    
    // 站点操作
    addNewSite() {
      console.log('添加站点')
    },
    
    viewSiteDetails(site) {
      this.selectedSite = site
      this.activeView = 'details'
    },
    
    editSite(site) {
      console.log('编辑站点:', site.id)
    },
    
    deleteSite(id) {
      if (confirm(`确定要删除站点 ${this.sites.find(s => s.id === id)?.name} 吗？`)) {
        this.sites = this.sites.filter(site => site.id !== id)
        this.filteredSites = this.filteredSites.filter(site => site.id !== id)
        this.selectedSites = this.selectedSites.filter(siteId => siteId !== id)
      }
    },
    
    batchDeleteSites() {
      console.log('批量删除站点:', this.selectedSites)
    },
    
    updateSiteStatus() {
      console.log('更新站点状态')
    },
    
    // 辅助方法
    formatDate(dateString) {
      const date = new Date(dateString)
      return date.toLocaleString()
    }
  },
  mounted() {
    this.refreshSites()
  }
}
</script>

<style scoped>
/* 站点视图切换 */
.site-view {
  display: none;
}

.site-view.active {
  display: block;
}

/* 站点工具栏 */
.site-toolbar {
  margin-bottom: 20px;
}

/* 状态徽章 */
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.status-running {
  background-color: #d4edda;
  color: #155724;
}

.status-stopped {
  background-color: #f8d7da;
  color: #721c24;
}

.status-pending {
  background-color: #fff3cd;
  color: #856404;
}

.status-error {
  background-color: #f8d7da;
  color: #721c24;
}

/* 站点详情 */
.site-details-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.site-details-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h4 {
  margin: 0;
  font-size: 16px;
  color: #2c3e50;
}

/* 日志视图 */
.log-type-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.log-content {
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  white-space: pre-wrap;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .page-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .search-box {
    flex-wrap: wrap;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .btn-sm {
    width: 100%;
  }
}
</style>