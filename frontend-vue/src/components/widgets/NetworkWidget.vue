<template>
  <div class="network-widget">
    <div class="network-stats">
      <div class="stat-card upload">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24"><path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z" fill="currentColor"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ $t('dashboard.upload') }}</span>
          <span class="stat-value">{{ formatSpeed(uploadSpeed) }}</span>
        </div>
      </div>
      <div class="stat-card download">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24"><path d="M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z" fill="currentColor"/></svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ $t('dashboard.download') }}</span>
          <span class="stat-value">{{ formatSpeed(downloadSpeed) }}</span>
        </div>
      </div>
    </div>
    <div class="network-totals">
      <div class="total-item">
        <span class="total-label">{{ $t('dashboard.totalUpload') }}</span>
        <span class="total-value">{{ formatBytes(totalUpload) }}</span>
      </div>
      <div class="total-item">
        <span class="total-label">{{ $t('dashboard.totalDownload') }}</span>
        <span class="total-value">{{ formatBytes(totalDownload) }}</span>
      </div>
    </div>
    <div class="network-details">
      <div class="detail-item">
        <span>{{ $t('dashboard.packetsSent') }}</span>
        <span>{{ formatNumber(packetsSent) }}</span>
      </div>
      <div class="detail-item">
        <span>{{ $t('dashboard.packetsRecv') }}</span>
        <span>{{ formatNumber(packetsRecv) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'NetworkWidget',
  props: { data: { type: Object, default: () => ({}) } },
  setup(props) {
    const uploadSpeed = computed(() => props.data?.sent_speed || 0)
    const downloadSpeed = computed(() => props.data?.recv_speed || 0)
    const totalUpload = computed(() => props.data?.bytes_sent || 0)
    const totalDownload = computed(() => props.data?.bytes_recv || 0)
    const packetsSent = computed(() => props.data?.packets_sent || 0)
    const packetsRecv = computed(() => props.data?.packets_recv || 0)
    
    const formatSpeed = (bytesPerSec) => {
      if (bytesPerSec === 0) return '0 B/s'
      const k = 1024
      const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s']
      const i = Math.floor(Math.log(bytesPerSec) / Math.log(k))
      return parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    const formatNumber = (num) => {
      if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
      if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
      return num.toString()
    }
    
    return { uploadSpeed, downloadSpeed, totalUpload, totalDownload, packetsSent, packetsRecv, formatSpeed, formatBytes, formatNumber }
  }
}
</script>

<style scoped>
.network-widget { display: flex; flex-direction: column; gap: var(--spacing-4); height: 100%; }
.network-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--spacing-3); }
.stat-card { display: flex; align-items: center; gap: var(--spacing-3); padding: var(--spacing-3); background: var(--bg-tertiary); border-radius: var(--radius-lg); }
.stat-icon { width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; }
.stat-icon svg { width: 20px; height: 20px; }
.stat-card.upload .stat-icon { background: rgba(59, 130, 246, 0.1); color: var(--primary-500); }
.stat-card.download .stat-icon { background: rgba(16, 185, 129, 0.1); color: var(--success-500); }
.stat-content { display: flex; flex-direction: column; }
.stat-label { font-size: var(--font-size-xs); color: var(--text-tertiary); }
.stat-value { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--text-primary); }
.network-totals { display: flex; justify-content: space-around; padding: var(--spacing-3); background: var(--bg-tertiary); border-radius: var(--radius-lg); }
.total-item { text-align: center; }
.total-label { display: block; font-size: var(--font-size-xs); color: var(--text-tertiary); }
.total-value { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--text-primary); }
.network-details { display: flex; justify-content: space-between; font-size: var(--font-size-xs); color: var(--text-tertiary); }
</style>
