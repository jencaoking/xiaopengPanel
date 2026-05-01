<template>
  <div class="disk-widget">
    <div class="disk-list">
      <div v-for="disk in disks" :key="disk.device" class="disk-item">
        <div class="disk-header">
          <span class="disk-name">{{ disk.mountpoint }}</span>
          <span class="disk-percent" :class="getUsageClass(disk.usage_percent)">{{ disk.usage_percent.toFixed(1) }}%</span>
        </div>
        <div class="disk-bar">
          <div class="disk-fill" :style="{ width: `${disk.usage_percent}%` }" :class="getUsageClass(disk.usage_percent)"></div>
        </div>
        <div class="disk-info">
          <span>{{ formatBytes(disk.used) }} / {{ formatBytes(disk.total) }}</span>
          <span>{{ disk.file_system }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'DiskWidget',
  props: { data: { type: Object, default: () => ({}) } },
  setup(props) {
    const disks = computed(() => props.data?.partitions || [])
    
    const getUsageClass = (percent) => {
      if (percent >= 90) return 'danger'
      if (percent >= 70) return 'warning'
      return 'normal'
    }
    
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }
    
    return { disks, getUsageClass, formatBytes }
  }
}
</script>

<style scoped>
.disk-widget { height: 100%; overflow-y: auto; }
.disk-list { display: flex; flex-direction: column; gap: var(--spacing-4); }
.disk-item { padding: var(--spacing-2); background: var(--bg-tertiary); border-radius: var(--radius-lg); }
.disk-header { display: flex; justify-content: space-between; margin-bottom: var(--spacing-2); }
.disk-name { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--text-primary); }
.disk-percent { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); }
.disk-percent.normal { color: var(--success-600); }
.disk-percent.warning { color: var(--warning-600); }
.disk-percent.danger { color: var(--danger-600); }
.disk-bar { height: 6px; background: var(--bg-secondary); border-radius: var(--radius-full); overflow: hidden; }
.disk-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.3s ease; }
.disk-fill.normal { background: var(--success-500); }
.disk-fill.warning { background: var(--warning-500); }
.disk-fill.danger { background: var(--danger-500); }
.disk-info { display: flex; justify-content: space-between; margin-top: var(--spacing-1); font-size: var(--font-size-xs); color: var(--text-tertiary); }
</style>
