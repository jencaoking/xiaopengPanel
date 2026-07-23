<template>
  <div class="gpu-widget">
    <div v-if="!data || data.available === false" class="gpu-unavailable">
      <svg viewBox="0 0 24 24" class="empty-icon">
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zm-7-2h5v-2h-5v2zm-3.77-1.89L9.5 14.5l-1.27-1.27-1.42 1.41L9.5 17.18l3.69-3.69-1.42-1.41z" fill="currentColor"/>
      </svg>
      <span class="empty-text">{{ $t('dashboard.gpuUnavailable') }}</span>
    </div>
    <div v-else class="gpu-list">
      <div v-for="gpu in devices" :key="gpu.index" class="gpu-item">
        <div class="gpu-header">
          <span class="gpu-name" :title="gpu.name">{{ gpu.name }}</span>
          <span class="gpu-util" :class="getUtilClass(gpu.gpu_utilization)">{{ (gpu.gpu_utilization || 0).toFixed(0) }}%</span>
        </div>
        <div class="gpu-bar">
          <div class="gpu-fill" :style="{ width: `${gpu.gpu_utilization || 0}%` }" :class="getUtilClass(gpu.gpu_utilization)"></div>
        </div>
        <div class="gpu-details">
          <div class="detail-row">
            <span class="detail-label">{{ $t('dashboard.gpuMemory') }}</span>
            <span class="detail-value">{{ formatBytes(gpu.memory_used) }} / {{ formatBytes(gpu.memory_total) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('dashboard.temperature') }}</span>
            <span class="detail-value" :class="getTempClass(gpu.temperature)">{{ (gpu.temperature || 0).toFixed(0) }}°C</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('dashboard.power') }}</span>
            <span class="detail-value">{{ (gpu.power_draw || 0).toFixed(1) }} W</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'GpuWidget',
  props: { data: { type: Object, default: () => ({}) } },
  setup(props) {
    const devices = computed(() => props.data?.devices || [])

    const getUtilClass = (val) => {
      const v = val || 0
      if (v >= 95) return 'danger'
      if (v >= 80) return 'warning'
      return 'normal'
    }

    const getTempClass = (t) => {
      const v = t || 0
      if (v >= 85) return 'danger'
      if (v >= 75) return 'warning'
      return 'normal'
    }

    const formatBytes = (bytes) => {
      if (!bytes || bytes <= 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

    return { devices, getUtilClass, getTempClass, formatBytes }
  }
}
</script>

<style scoped>
.gpu-widget { height: 100%; overflow-y: auto; }
.gpu-unavailable {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  color: var(--text-tertiary);
}
.empty-icon { width: 40px; height: 40px; opacity: 0.5; }
.empty-text { font-size: var(--font-size-sm); }
.gpu-list { display: flex; flex-direction: column; gap: var(--spacing-4); }
.gpu-item { padding: var(--spacing-3); background: var(--bg-tertiary); border-radius: var(--radius-lg); }
.gpu-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-2); gap: var(--spacing-2); }
.gpu-name { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gpu-util { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); flex-shrink: 0; }
.gpu-util.normal { color: var(--success-600); }
.gpu-util.warning { color: var(--warning-600); }
.gpu-util.danger { color: var(--danger-600); }
.gpu-bar { height: 6px; background: var(--bg-secondary); border-radius: var(--radius-full); overflow: hidden; margin-bottom: var(--spacing-3); }
.gpu-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.3s ease; }
.gpu-fill.normal { background: var(--success-500); }
.gpu-fill.warning { background: var(--warning-500); }
.gpu-fill.danger { background: var(--danger-500); }
.gpu-details { display: flex; flex-direction: column; gap: var(--spacing-1); }
.detail-row { display: flex; justify-content: space-between; font-size: var(--font-size-xs); }
.detail-label { color: var(--text-tertiary); }
.detail-value { color: var(--text-secondary); font-weight: var(--font-weight-medium); }
.detail-value.danger { color: var(--danger-600); }
.detail-value.warning { color: var(--warning-600); }
</style>
