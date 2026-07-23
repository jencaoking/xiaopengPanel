<template>
  <div class="temp-widget">
    <div v-if="!data || data.available === false || !sensors.length" class="temp-unavailable">
      <svg viewBox="0 0 24 24" class="empty-icon">
        <path d="M15 13V5c0-1.66-1.34-3-3-3S9 3.34 9 5v8c-1.21.91-2 2.37-2 4 0 2.76 2.24 5 5 5s5-2.24 5-5c0-1.63-.79-3.09-2-4zm-4-8c0-.55.45-1 1-1s1 .45 1 1h-1v1h1v2h-1v1h1v2h-2V5z" fill="currentColor"/>
      </svg>
      <span class="empty-text">{{ $t('dashboard.tempUnavailable') }}</span>
    </div>
    <div v-else class="temp-list">
      <div v-for="(sensor, idx) in sensors" :key="idx" class="temp-item">
        <div class="temp-header">
          <span class="temp-label" :title="sensor.sensor + ' / ' + sensor.label">{{ sensor.label }}</span>
          <span class="temp-value" :class="getTempClass(sensor.current)">
            {{ (sensor.current || 0).toFixed(1) }}°C
          </span>
        </div>
        <div class="temp-bar">
          <div class="temp-fill" :style="{ width: getTempPercent(sensor) }" :class="getTempClass(sensor.current)"></div>
        </div>
        <div class="temp-limits" v-if="sensor.high || sensor.critical">
          <span v-if="sensor.high">{{ $t('dashboard.high') }}: {{ sensor.high.toFixed(0) }}°C</span>
          <span v-if="sensor.critical" class="critical">{{ $t('dashboard.critical') }}: {{ sensor.critical.toFixed(0) }}°C</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'TemperatureWidget',
  props: { data: { type: Object, default: () => ({}) } },
  setup(props) {
    const sensors = computed(() => props.data?.sensors || [])

    const getTempClass = (t) => {
      const v = t || 0
      if (v >= 85) return 'danger'
      if (v >= 70) return 'warning'
      return 'normal'
    }

    const getTempPercent = (sensor) => {
      const v = sensor.current || 0
      const max = sensor.critical || sensor.high || 100
      return `${Math.min(100, (v / max) * 100)}%`
    }

    return { sensors, getTempClass, getTempPercent }
  }
}
</script>

<style scoped>
.temp-widget { height: 100%; overflow-y: auto; }
.temp-unavailable {
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
.temp-list { display: flex; flex-direction: column; gap: var(--spacing-3); }
.temp-item { padding: var(--spacing-3); background: var(--bg-tertiary); border-radius: var(--radius-lg); }
.temp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-2); gap: var(--spacing-2); }
.temp-label { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-value { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); flex-shrink: 0; }
.temp-value.normal { color: var(--success-600); }
.temp-value.warning { color: var(--warning-600); }
.temp-value.danger { color: var(--danger-600); }
.temp-bar { height: 6px; background: var(--bg-secondary); border-radius: var(--radius-full); overflow: hidden; margin-bottom: var(--spacing-1); }
.temp-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.3s ease; }
.temp-fill.normal { background: var(--success-500); }
.temp-fill.warning { background: var(--warning-500); }
.temp-fill.danger { background: var(--danger-500); }
.temp-limits { display: flex; justify-content: space-between; font-size: var(--font-size-xs); color: var(--text-tertiary); }
.temp-limits .critical { color: var(--danger-500); }
</style>
