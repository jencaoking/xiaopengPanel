<template>
  <div id="services" class="page">
    <div class="page-header">
      <h2>服务管理</h2>
      <div class="page-actions">
        <button id="refresh-services-btn" class="btn btn-secondary" @click="refreshServices">刷新</button>
      </div>
    </div>
    <div class="table-container">
      <table id="services-table" class="data-table">
        <thead>
          <tr>
            <th>服务名称</th>
            <th>显示名称</th>
            <th>状态</th>
            <th>启动类型</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="loading-row">
            <td colspan="6" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="services.length === 0">
            <td colspan="6" class="no-data">没有找到服务</td>
          </tr>
          <tr 
            v-for="service in services" 
            :key="service.name"
            class="service-row"
          >
            <td>{{ service.name }}</td>
            <td>{{ service.displayName }}</td>
            <td>
              <span :class="['status-badge', `status-${service.status.toLowerCase()}`]">
                {{ service.status }}
              </span>
            </td>
            <td>
              <span :class="['startup-badge', `startup-${service.startupType.toLowerCase()}`]">
                {{ service.startupType }}
              </span>
            </td>
            <td>{{ service.description }}</td>
            <td>
              <div class="action-buttons">
                <button 
                  class="btn btn-primary btn-sm"
                  v-if="service.status === 'Stopped'"
                  @click="startService(service.name)"
                >启动</button>
                <button 
                  class="btn btn-warning btn-sm"
                  v-else
                  @click="stopService(service.name)"
                >停止</button>
                <button 
                  class="btn btn-secondary btn-sm"
                  @click="restartService(service.name)"
                >重启</button>
                <button 
                  class="btn btn-secondary btn-sm"
                  @click="viewServiceDetails(service)"
                >详情</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 服务详情模态框 -->
    <div v-if="showDetails" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>服务详情</h3>
          <button class="close-btn" @click="showDetails = false">&times;</button>
        </div>
        <div class="modal-body" v-if="selectedService">
          <div class="info-grid">
            <div class="info-item">
              <label>服务名称</label>
              <span>{{ selectedService.name }}</span>
            </div>
            <div class="info-item">
              <label>显示名称</label>
              <span>{{ selectedService.displayName }}</span>
            </div>
            <div class="info-item">
              <label>状态</label>
              <span>{{ selectedService.status }}</span>
            </div>
            <div class="info-item">
              <label>启动类型</label>
              <span>{{ selectedService.startupType }}</span>
            </div>
            <div class="info-item">
              <label>描述</label>
              <span>{{ selectedService.description }}</span>
            </div>
            <div class="info-item">
              <label>可执行文件路径</label>
              <span>{{ selectedService.executablePath }}</span>
            </div>
            <div class="info-item">
              <label>服务ID</label>
              <span>{{ selectedService.serviceId }}</span>
            </div>
            <div class="info-item">
              <label>进程ID</label>
              <span>{{ selectedService.pid }}</span>
            </div>
            <div class="info-item">
              <label>登录账号</label>
              <span>{{ selectedService.logonAccount }}</span>
            </div>
            <div class="info-item">
              <label>依赖服务</label>
              <span>{{ selectedService.dependencies.join(', ') || '无' }}</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showDetails = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Services',
  data() {
    return {
      services: [],
      loading: false,
      showDetails: false,
      selectedService: null,
      filterStatus: null,
      sortBy: null,
      // 模拟数据
      mockServices: [
        {
          name: 'Apache2.4',
          displayName: 'Apache HTTP Server',
          status: 'Running',
          startupType: 'Auto',
          description: 'Apache HTTP Server',
          executablePath: 'C:\\Apache24\\bin\\httpd.exe',
          serviceId: '{A4A9F05D-6E3E-4B2E-8A3A-55B20A0E8EB9}',
          pid: 1234,
          logonAccount: 'LocalSystem',
          dependencies: ['tcpip']
        },
        {
          name: 'nginx',
          displayName: 'nginx',
          status: 'Stopped',
          startupType: 'Manual',
          description: 'nginx web server',
          executablePath: 'C:\\nginx\\nginx.exe',
          serviceId: '{B5C8D1E0-2F3A-4C5B-6D7E-8F9A-0B1C2D3E4F5G}',
          pid: null,
          logonAccount: 'LocalSystem',
          dependencies: ['tcpip']
        },
        {
          name: 'MySQL',
          displayName: 'MySQL Database Server',
          status: 'Running',
          startupType: 'Auto',
          description: 'MySQL Database Server',
          executablePath: 'C:\\MySQL\\bin\\mysqld.exe',
          serviceId: '{C6D7E8F9-3G4H-5I6J-7K8L-9M0N1O2P3Q4R}',
          pid: 5678,
          logonAccount: 'LocalSystem',
          dependencies: ['tcpip']
        },
        {
          name: 'Redis',
          displayName: 'Redis Server',
          status: 'Running',
          startupType: 'Manual',
          description: 'Redis in-memory data store',
          executablePath: 'C:\\Redis\\redis-server.exe',
          serviceId: '{D7E8F9A0-4H5I-6J7K-8L9M-0N1O2P3Q4R5S}',
          pid: 9012,
          logonAccount: 'LocalSystem',
          dependencies: []
        },
        {
          name: 'Node.js',
          displayName: 'Node.js Server',
          status: 'Stopped',
          startupType: 'Manual',
          description: 'Node.js application server',
          executablePath: 'C:\\Node.js\\node.exe',
          serviceId: '{E8F9A0B1-5I6J-7K8L-9M0N-1O2P3Q4R5S6T}',
          pid: null,
          logonAccount: 'LocalSystem',
          dependencies: ['tcpip']
        }
      ]
    }
  },
  mounted() {
    this.fetchServices()
    // 定期刷新服务列表
    this.refreshInterval = setInterval(() => {
      this.fetchServices()
    }, 30000) // 30秒刷新一次
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    fetchServices() {
      this.loading = true
      // 构建API请求URL
      let url = '/api/services'
      if (this.filterStatus) {
        url += `?filter=${this.filterStatus}`
      }
      if (this.sortBy) {
        url += `&sort=${this.sortBy}`
      }
      
      // 使用Vuex store中的apiRequest action，自动包含token认证
      this.$store.dispatch('apiRequest', {
        url: url,
        method: 'GET'
      })
        .then(data => {
          if (data.status === 'success') {
            // 处理后端返回的服务数据，确保与前端组件期望的结构匹配
            this.services = (data.services || []).map(service => ({
              // 基础字段映射
              name: service.name || '',
              displayName: service.display_name || service.name || '',
              status: service.status || 'Unknown',
              startupType: service.start_type || service.startupType || 'Unknown',
              description: service.description || '',
              
              // 补充前端期望但后端没有返回的字段，使用默认值
              executablePath: service.executable_path || '',
              serviceId: service.service_id || service.name || '',
              pid: service.pid || null,
              logonAccount: service.logon_account || '',
              dependencies: service.dependencies || []
            }))
          } else {
            console.error('获取服务列表失败:', data.message)
            this.services = []
          }
          this.loading = false
        })
        .catch(error => {
          console.error('获取服务列表失败:', error.message || error)
          this.services = []
          this.loading = false
        })
    },
    refreshServices() {
      this.fetchServices()
    },
    manageService(serviceName, action) {
      // 通用的服务管理方法
      this.$store.dispatch('apiRequest', {
        url: `/api/services/${serviceName}/${action}`,
        method: 'POST'
      })
        .then(data => {
          if (data.status === 'success') {
            // 刷新服务列表
            this.fetchServices()
          } else {
            console.error(`${action}服务失败:`, data.message)
            alert(`${action}服务失败: ${data.message}`)
          }
        })
        .catch(error => {
          console.error(`${action}服务失败:`, error)
          alert(`${action}服务失败: ${error.message}`)
        })
    },
    startService(serviceName) {
      // 启动服务
      this.manageService(serviceName, 'start')
    },
    stopService(serviceName) {
      // 停止服务
      this.manageService(serviceName, 'stop')
    },
    restartService(serviceName) {
      // 重启服务
      this.manageService(serviceName, 'restart')
    },
    viewServiceDetails(service) {
      this.selectedService = service
      this.showDetails = true
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
  border-bottom: 1px solid #e0e0e0;
}

/* 表格样式 */
.table-container {
  overflow-x: auto;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.data-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #495057;
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

/* 启动类型徽章 */
.startup-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.startup-auto {
  background-color: #d1ecf1;
  color: #0c5460;
}

.startup-manual {
  background-color: #fff3cd;
  color: #856404;
}

.startup-disabled {
  background-color: #f8d7da;
  color: #721c24;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 5px;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

/* 加载和无数据状态 */
.loading-row {
  text-align: center;
}

.no-data {
  text-align: center;
  color: #666;
  padding: 20px;
}

/* 模态框样式 */
.modal {
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: white;
  border-radius: 8px;
  width: 80%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }
  
  .btn-sm {
    width: 100%;
  }
  
  .modal-content {
    width: 95%;
    margin: 20px;
  }
}
</style>