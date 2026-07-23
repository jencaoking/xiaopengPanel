<template>
  <div class="alerts-widget">
    <div class="alerts-header-row">
      <div class="alerts-summary">
        <span class="summary-badge" :class="{ active: activeCount > 0 }">
          {{ $t('dashboard.activeAlerts') }}: {{ activeCount }}
        </span>
      </div>
      <div class="alerts-filter">
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          :class="['filter-btn', { active: selectedStatus === opt.value }]"
          @click="selectedStatus = opt.value"
        >{{ opt.label }}</button>
      </div>
    </div>

    <div v-if="filteredAlerts.length === 0" class="alerts-empty">
      <svg viewBox="0 0 24 24" class="empty-icon">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="currentColor"/>
      </svg>
      <span class="empty-text">{{ $t('dashboard.noAlerts') }}</span>
    </div>

    <div v-else class="alerts-list">
      <div v-for="alert in filteredAlerts" :key="alert.id" class="alert-item" :class="alert.status">
        <div class="alert-main">
          <span class="alert-icon">
            <svg viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" fill="currentColor"/></svg>
          </span>
          <div class="alert-body">
            <div class="alert-title">
              <span class="alert-metric">{{ formatMetric(alert.metric_name) }}</span>
              <span class="alert-type" :class="alert.alert_type">{{ alert.alert_type === 'above' ? '↑' : '↓' }}</span>
            </div>
            <div class="alert-desc">
              {{ alert.current_value.toFixed(1) }} / {{ alert.threshold_value.toFixed(1) }}
              <span v-if="alert.message" class="alert-message">— {{ alert.message }}</span>
            </div>
            <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
          </div>
        </div>
        <button
          v-if="alert.status === 'active'"
          class="resolve-btn"
          @click="$emit('resolve', alert.id)"
        >{{ $t('dashboard.resolve') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

export default {
  name: 'AlertsWidget',
  props: {
    data: { type: Object, default: () => ({}) }
  },
  emits: ['resolve'],
  setup(props) {
    const { t } = useI18n()
    const selectedStatus = ref('active')

    const alerts = computed(() => props.data?.alerts || [])
    const activeCount = computed(() => props.data?.active_count ?? alerts.value.filter(a => a.status === 'active').length)

    const statusOptions = computed(() => [
      { label: t('dashboard.active'), value: 'active' },
      { label: t('dashboard.resolved'), value: 'resolved' },
      { label: t('common.all') || 'All', value: 'all' }
    ])

    const filteredAlerts = computed(() => {
      if (selectedStatus.value === 'all') return alerts.value
      return alerts.value.filter(a => a.status === selectedStatus.value)
    })

    const metricLabels = computed(() => ({
      cpu: t('common.cpuUsage'),
      memory: t('common.memoryUsage'),
      swap: 'Swap',
      load: t('common.loadAverage'),
      disk_read: t('dashboard.readSpeed'),
      disk_write: t('dashboard.writeSpeed'),
      network_sent: t('dashboard.upload'),
      network_recv: t('dashboard.download'),
      disk_response_time: 'Disk Latency',
      temperature: t('dashboard.temperature'),
      gpu: 'GPU'
    }))

    const formatMetric = (name) => metricLabels.value[name] || name

    const formatTime = (ts) => {
      if (!ts) return ''
      try {
        return new Date(ts).toLocaleString('zh-CN', {
          month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
        })
      } catch {
        return ts
      }
    }

    return { selectedStatus, alerts, activeCount, statusOptions, filteredAlerts, formatMetric, formatTime }
  }
}
</script>

<style scoped>
.alerts-widget { height: 100%; display: flex; flex-direction: column; gap: var(--spacing-2); }
.alerts-header-row { display: flex; justify-content: space-between; align-items: center; gap: var(--spacing-2); flex-wrap: wrap; }
.summary-badge {
  font-size: var(--font-size-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}
.summary-badge.active { background: rgba(220, 38, 38, 0.15); color: var(--danger-500); }
.alerts-filter { display: flex; gap: 2px; background: var(--bg-tertiary); border-radius: var(--radius-full); padding: 2px; }
.filter-btn {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.2s;
}
.filter-btn.active { background: var(--bg-primary); color: var(--text-primary); }
.alerts-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  color: var(--text-tertiary);
}
.empty-icon { width: 36px; height: 36px; color: var(--success-500); opacity: 0.7; }
.empty-text { font-size: var(--font-size-sm); }
.alerts-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: var(--spacing-2); }
.alert-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  border-left: 3px solid var(--danger-500);
}
.alert-item.resolved { border-left-color: var(--success-500); opacity: 0.65; }
.alert-main { display: flex; gap: var(--spacing-2); align-items: flex-start; min-width: 0; flex: 1; }
.alert-icon { flex-shrink: 0; width: 18px; height: 18px; color: var(--danger-500); margin-top: 2px; }
.alert-item.resolved .alert-icon { color: var(--success-500); }
.alert-icon svg { width: 100%; height: 100%; }
.alert-body { min-width: 0; flex: 1; }
.alert-title { display: flex; align-items: center; gap: var(--spacing-1); }
.alert-metric { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--text-primary); }
.alert-type { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); }
.alert-type.above { color: var(--danger-500); }
.alert-type.below { color: var(--warning-500); }
.alert-desc { font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: 2px; }
.alert-message { color: var(--text-tertiary); }
.alert-time { font-size: 10px; color: var(--text-tertiary); margin-top: 2px; }
.resolve-btn {
  border: 1px solid var(--success-500);
  background: transparent;
  color: var(--success-600);
  font-size: var(--font-size-xs);
  padding: 4px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;
}
.resolve-btn:hover { background: var(--success-500); color: white; }
</style>
