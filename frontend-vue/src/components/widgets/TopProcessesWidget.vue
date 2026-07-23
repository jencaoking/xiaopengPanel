<template>
  <div class="top-processes-widget">
    <div class="processes-header">
      <div class="sort-controls">
        <button 
          v-for="sort in sortOptions" 
          :key="sort.value"
          :class="['sort-btn', { active: sortBy === sort.value }]"
          @click="sortBy = sort.value"
        >{{ sort.label }}</button>
      </div>
    </div>
    <div class="processes-list">
      <div v-for="proc in processes" :key="proc.pid" class="process-item" @click="showProcessDetail(proc)">
        <div class="process-info">
          <span class="process-name">{{ proc.name }}</span>
          <span class="process-pid">PID: {{ proc.pid }}</span>
        </div>
        <div class="process-metrics">
          <div class="metric">
            <span class="metric-label">CPU</span>
            <span class="metric-value" :class="getMetricClass(proc.cpu_percent)">{{ proc.cpu_percent.toFixed(1) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">MEM</span>
            <span class="metric-value" :class="getMetricClass(proc.memory_percent)">{{ proc.memory_percent.toFixed(1) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">IO</span>
            <span class="metric-value">{{ formatBytes(proc.io_read_bytes + proc.io_write_bytes) }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-if="selectedProcess" class="process-detail-modal" @click.self="selectedProcess = null">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ selectedProcess.name }}</h3>
          <button class="close-btn" @click="selectedProcess = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="detail-row">
            <span class="detail-label">PID</span>
            <span class="detail-value">{{ selectedProcess.pid }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">User</span>
            <span class="detail-value">{{ selectedProcess.username }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Command</span>
            <span class="detail-value code">{{ selectedProcess.cmdline || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">CPU</span>
            <span class="detail-value">{{ selectedProcess.cpu_percent.toFixed(1) }}%</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Memory</span>
            <span class="detail-value">{{ selectedProcess.memory_percent.toFixed(1) }}%</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">IO Read</span>
            <span class="detail-value">{{ formatBytes(selectedProcess.io_read_bytes) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">IO Write</span>
            <span class="detail-value">{{ formatBytes(selectedProcess.io_write_bytes) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'TopProcessesWidget',
  props: {
    data: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const sortBy = ref('cpu')
    const selectedProcess = ref(null)
    
    const sortOptions = [
      { label: 'CPU', value: 'cpu' },
      { label: 'Memory', value: 'memory' },
      { label: 'IO', value: 'io' }
    ]
    
    const processes = computed(() => {
      const list = [...(props.data || [])]
      if (sortBy.value === 'cpu') {
        list.sort((a, b) => (b.cpu_percent || 0) - (a.cpu_percent || 0))
      } else if (sortBy.value === 'memory') {
        list.sort((a, b) => (b.memory_percent || 0) - (a.memory_percent || 0))
      } else if (sortBy.value === 'io') {
        list.sort((a, b) => ((b.io_read_bytes || 0) + (b.io_write_bytes || 0)) - ((a.io_read_bytes || 0) + (a.io_write_bytes || 0)))
      }
      return list.slice(0, 10)
    })
    
    const getMetricClass = (value) => {
      if (value >= 80) return 'danger'
      if (value >= 50) return 'warning'
      return 'normal'
    }
    
    const formatBytes = (bytes) => {
      if (!bytes || bytes <= 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }
    
    const showProcessDetail = (proc) => {
      selectedProcess.value = proc
    }
    
    return {
      sortBy,
      sortOptions,
      processes,
      selectedProcess,
      getMetricClass,
      formatBytes,
      showProcessDetail
    }
  }
}
</script>

<style scoped>
.top-processes-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.processes-header {
  margin-bottom: var(--spacing-3);
}

.sort-controls {
  display: flex;
  gap: var(--spacing-1);
}

.sort-btn {
  padding: var(--spacing-1) var(--spacing-3);
  border: none;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.sort-btn:hover {
  color: var(--text-primary);
}

.sort-btn.active {
  background: var(--primary-500);
  color: white;
}

.processes-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.process-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.process-item:hover {
  background: var(--bg-secondary);
  transform: translateX(4px);
}

.process-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.process-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.process-pid {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.process-metrics {
  display: flex;
  gap: var(--spacing-4);
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.metric-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.metric-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.metric-value.warning { color: var(--warning-600); }
.metric-value.danger { color: var(--danger-600); }

.process-detail-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--text-primary);
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-xl);
  cursor: pointer;
  border-radius: var(--radius-md);
}

.close-btn:hover {
  background: var(--bg-secondary);
}

.modal-body {
  padding: var(--spacing-4);
  overflow-y: auto;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--border-color);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.detail-value {
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.detail-value.code {
  font-family: monospace;
  font-size: var(--font-size-xs);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
