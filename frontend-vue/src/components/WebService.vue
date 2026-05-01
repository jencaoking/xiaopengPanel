<template>
  <div id="web-service" class="page">
    <div class="page-header">
      <h2>Web服务管理</h2>
    </div>
    
    <div class="web-service-container">
      <!-- Web服务状态 -->
      <div class="section">
        <h4>服务状态</h4>
        <div class="web-service-status" id="web-service-status">
          <div class="status-item">
            <label>Nginx状态：</label>
            <span id="nginx-status" :class="['status-badge', `status-${nginxStatus.toLowerCase()}`]">
              {{ nginxStatus }}
            </span>
            <button 
              id="check-nginx-status-btn" 
              class="btn btn-secondary" 
              style="margin-left: 10px;"
              @click="checkNginxStatus"
            >检查状态</button>
          </div>
          <div class="status-item">
            <label>Apache状态：</label>
            <span id="apache-status" :class="['status-badge', `status-${apacheStatus.toLowerCase()}`]">
              {{ apacheStatus }}
            </span>
            <button 
              id="check-apache-status-btn" 
              class="btn btn-secondary" 
              style="margin-left: 10px;"
              @click="checkApacheStatus"
            >检查状态</button>
          </div>
        </div>
      </div>
      
      <!-- Web服务操作 -->
      <div class="section">
        <h4>服务操作</h4>
        <div class="web-service-actions">
          <div class="action-item">
            <h5>Nginx操作</h5>
            <button id="reload-nginx-btn" class="btn btn-primary" @click="reloadNginx">重载Nginx</button>
            <button id="restart-nginx-btn" class="btn btn-warning" @click="restartNginx">重启Nginx</button>
            <button id="start-nginx-btn" class="btn btn-success" @click="startNginx">启动Nginx</button>
            <button id="stop-nginx-btn" class="btn btn-danger" @click="stopNginx">停止Nginx</button>
          </div>
          <div class="action-item" style="margin-top: 15px;">
            <h5>Apache操作</h5>
            <button id="reload-apache-btn" class="btn btn-primary" @click="reloadApache">重载Apache</button>
            <button id="restart-apache-btn" class="btn btn-warning" @click="restartApache">重启Apache</button>
            <button id="start-apache-btn" class="btn btn-success" @click="startApache">启动Apache</button>
            <button id="stop-apache-btn" class="btn btn-danger" @click="stopApache">停止Apache</button>
          </div>
        </div>
      </div>
      
      <!-- 操作日志 -->
      <div class="section">
        <h4>操作日志</h4>
        <div 
          class="web-service-logs" 
          id="web-service-logs" 
          style="height: 300px; overflow-y: auto; background-color: #f5f5f5; padding: 10px; border-radius: 5px;"
        >
          <div v-for="(log, index) in operationLogs" :key="index" class="log-entry">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-action">{{ log.action }}</span>
            <span :class="['log-status', `status-${log.status.toLowerCase()}`]">{{ log.status }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'WebService',
  data() {
    return {
      // 服务状态
      nginxStatus: 'Running',
      apacheStatus: 'Stopped',
      // 操作日志
      operationLogs: [
        {
          time: '2026-01-01 10:00:00',
          action: '重载Nginx',
          status: 'Success'
        },
        {
          time: '2026-01-01 09:30:00',
          action: '启动Apache',
          status: 'Failed'
        },
        {
          time: '2026-01-01 09:00:00',
          action: '重启Nginx',
          status: 'Success'
        }
      ]
    }
  },
  methods: {
    // 状态检查
    checkNginxStatus() {
      console.log('检查Nginx状态')
    },
    
    checkApacheStatus() {
      console.log('检查Apache状态')
    },
    
    // Nginx操作
    reloadNginx() {
      console.log('重载Nginx')
      this.addOperationLog('重载Nginx', 'Success')
    },
    
    restartNginx() {
      console.log('重启Nginx')
      this.addOperationLog('重启Nginx', 'Success')
    },
    
    startNginx() {
      console.log('启动Nginx')
      this.nginxStatus = 'Running'
      this.addOperationLog('启动Nginx', 'Success')
    },
    
    stopNginx() {
      console.log('停止Nginx')
      this.nginxStatus = 'Stopped'
      this.addOperationLog('停止Nginx', 'Success')
    },
    
    // Apache操作
    reloadApache() {
      console.log('重载Apache')
      this.addOperationLog('重载Apache', 'Success')
    },
    
    restartApache() {
      console.log('重启Apache')
      this.addOperationLog('重启Apache', 'Success')
    },
    
    startApache() {
      console.log('启动Apache')
      this.apacheStatus = 'Running'
      this.addOperationLog('启动Apache', 'Success')
    },
    
    stopApache() {
      console.log('停止Apache')
      this.apacheStatus = 'Stopped'
      this.addOperationLog('停止Apache', 'Success')
    },
    
    // 日志操作
    addOperationLog(action, status) {
      const now = new Date()
      const time = now.toLocaleString()
      this.operationLogs.unshift({
        time,
        action,
        status
      })
      
      // 只保留最近50条日志
      if (this.operationLogs.length > 50) {
        this.operationLogs = this.operationLogs.slice(0, 50)
      }
    }
  }
}
</script>

<style scoped>
.web-service-container {
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

.section h4 {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #2c3e50;
}

/* 状态项 */
.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.status-item:last-child {
  margin-bottom: 0;
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

.status-success {
  background-color: #d4edda;
  color: #155724;
}

.status-failed {
  background-color: #f8d7da;
  color: #721c24;
}

/* 操作按钮 */
.web-service-actions {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.action-item h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #2c3e50;
}

.action-item button {
  margin-right: 10px;
  margin-bottom: 10px;
}

/* 操作日志 */
.web-service-logs {
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
}

.log-entry {
  display: flex;
  gap: 15px;
  margin-bottom: 5px;
  padding: 5px 0;
  border-bottom: 1px solid #e0e0e0;
}

.log-time {
  color: #666;
  min-width: 180px;
}

.log-action {
  flex: 1;
  color: #333;
}

.log-status {
  font-weight: 500;
  text-transform: uppercase;
  font-size: 12px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .web-service-actions button {
    width: 100%;
    margin-right: 0;
  }
  
  .log-entry {
    flex-direction: column;
    gap: 5px;
  }
  
  .log-time {
    min-width: auto;
  }
}
</style>