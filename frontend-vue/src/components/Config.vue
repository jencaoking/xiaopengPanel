<template>
  <div id="config" class="page">
    <div class="page-header">
      <h2>系统配置</h2>
    </div>
    <div class="config-container">
      <div class="config-section">
        <h3>系统时间</h3>
        <div class="config-item">
          <label>当前时间</label>
          <span id="current-time">{{ currentTime }}</span>
        </div>
        <div class="config-item">
          <label>设置时间</label>
          <input type="datetime-local" id="new-time" v-model="newTime">
          <button id="set-time-btn" class="btn btn-primary" @click="setSystemTime">设置</button>
        </div>
      </div>
      <div class="config-section">
        <h3>网络配置</h3>
        <div id="network-config" class="network-config">
          <div class="network-item" v-for="(network, index) in networks" :key="index">
            <h4>{{ network.name }}</h4>
            <div class="info-grid">
              <div class="info-item">
                <label>IP地址</label>
                <span>{{ network.ip }}</span>
              </div>
              <div class="info-item">
                <label>子网掩码</label>
                <span>{{ network.netmask }}</span>
              </div>
              <div class="info-item">
                <label>网关</label>
                <span>{{ network.gateway }}</span>
              </div>
              <div class="info-item">
                <label>DNS服务器</label>
                <span>{{ network.dns.join(', ') }}</span>
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
  name: 'Config',
  data() {
    return {
      currentTime: '',
      newTime: '',
      networks: [
        {
          name: '以太网',
          ip: '192.168.1.100',
          netmask: '255.255.255.0',
          gateway: '192.168.1.1',
          dns: ['8.8.8.8', '8.8.4.4']
        },
        {
          name: 'WLAN',
          ip: '192.168.1.101',
          netmask: '255.255.255.0',
          gateway: '192.168.1.1',
          dns: ['8.8.8.8', '8.8.4.4']
        }
      ]
    }
  },
  methods: {
    updateCurrentTime() {
      this.currentTime = new Date().toLocaleString()
    },
    setSystemTime() {
      console.log('设置系统时间:', this.newTime)
      // 这里可以添加API调用
    }
  },
  mounted() {
    this.updateCurrentTime()
    // 每秒更新时间
    this.timeInterval = setInterval(() => {
      this.updateCurrentTime()
    }, 1000)
  },
  beforeUnmount() {
    if (this.timeInterval) {
      clearInterval(this.timeInterval)
    }
  }
}
</script>

<style scoped>
.config-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.config-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #2c3e50;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 15px;
}

.config-item label {
  width: 120px;
  font-size: 14px;
  color: #2c3e50;
}

.config-item input {
  padding: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
}

.network-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.network-item {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.network-item h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #2c3e50;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .config-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .config-item label {
    width: 100%;
  }
}
</style>