<template>
  <div class="cpu-widget">
    <div class="usage-display">
      <div class="usage-ring">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" class="ring-bg"/>
          <circle 
            cx="50" cy="50" r="45" 
            class="ring-progress"
            :style="{ strokeDashoffset: 283 - (283 * cpuUsage) / 100 }"
            :class="usageClass"
          />
        </svg>
        <div class="usage-text">
          <span class="usage-value">{{ cpuUsage.toFixed(1) }}%</span>
          <span class="usage-label">CPU</span>
        </div>
      </div>
    </div>
    <div class="cores-list">
      <div v-for="(core, idx) in cores" :key="idx" class="core-item">
        <span class="core-label">Core {{ idx + 1 }}</span>
        <div class="core-bar">
          <div class="core-fill" :style="{ width: `${core}%` }" :class="getCoreClass(core)"></div>
        </div>
        <span class="core-value" :class="getCoreClass(core)">{{ core.toFixed(0) }}%</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'CpuWidget',
  props: {
    data: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    const cpuUsage = computed(() => props.data?.usage || 0)
    const cores = computed(() => props.data?.cores || [])
    
    const usageClass = computed(() => {
      const usage = cpuUsage.value
      if (usage >= 90) return 'danger'
      if (usage >= 70) return 'warning'
      return 'normal'
    })
    
    const getCoreClass = (usage) => {
      if (usage >= 90) return 'danger'
      if (usage >= 70) return 'warning'
      return 'normal'
    }
    
    return {
      cpuUsage,
      cores,
      usageClass,
      getCoreClass
    }
  }
}
</script>

<style scoped>
.cpu-widget {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  height: 100%;
}

.usage-display {
  display: flex;
  justify-content: center;
}

.usage-ring {
  position: relative;
  width: 120px;
  height: 120px;
}

.usage-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--bg-tertiary);
  stroke-width: 8;
}

.ring-progress {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.5s ease;
}

.ring-progress.normal { stroke: var(--success-500); }
.ring-progress.warning { stroke: var(--warning-500); }
.ring-progress.danger { stroke: var(--danger-500); }

.usage-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.usage-value {
  display: block;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.usage-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.cores-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  flex: 1;
  overflow-y: auto;
}

.core-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.core-label {
  width: 50px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.core-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.core-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.core-fill.normal { background: var(--success-500); }
.core-fill.warning { background: var(--warning-500); }
.core-fill.danger { background: var(--danger-500); }

.core-value {
  width: 40px;
  font-size: var(--font-size-xs);
  text-align: right;
  font-weight: var(--font-weight-medium);
}

.core-value.normal { color: var(--success-600); }
.core-value.warning { color: var(--warning-600); }
.core-value.danger { color: var(--danger-600); }
</style>
