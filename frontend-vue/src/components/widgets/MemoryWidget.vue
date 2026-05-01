<template>
  <div class="memory-widget">
    <div class="memory-visual">
      <div class="memory-ring">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" class="ring-bg"/>
          <circle 
            cx="50" cy="50" r="45" 
            class="ring-progress"
            :style="{ strokeDashoffset: 283 - (283 * memoryPercent) / 100 }"
            :class="usageClass"
          />
        </svg>
        <div class="ring-text">
          <span class="ring-value">{{ memoryPercent.toFixed(1) }}%</span>
          <span class="ring-label">{{ $t('common.used') }}</span>
        </div>
      </div>
      <div class="memory-stats">
        <div class="mem-stat">
          <span class="mem-label">{{ $t('common.total') }}</span>
          <span class="mem-value">{{ formatBytes(memoryTotal) }}</span>
        </div>
        <div class="mem-stat">
          <span class="mem-label">{{ $t('common.used') }}</span>
          <span class="mem-value">{{ formatBytes(memoryUsed) }}</span>
        </div>
        <div class="mem-stat">
          <span class="mem-label">{{ $t('common.available') }}</span>
          <span class="mem-value">{{ formatBytes(memoryAvailable) }}</span>
        </div>
        <div class="mem-stat" v-if="memoryCached">
          <span class="mem-label">Cached</span>
          <span class="mem-value">{{ formatBytes(memoryCached) }}</span>
        </div>
      </div>
    </div>
    <div class="memory-bar">
      <div class="bar-labels">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" :style="{ width: `${memoryPercent}%` }" :class="usageClass"></div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'MemoryWidget',
  props: {
    data: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    const memoryPercent = computed(() => props.data?.percent || 0)
    const memoryTotal = computed(() => props.data?.total || 0)
    const memoryUsed = computed(() => props.data?.used || 0)
    const memoryAvailable = computed(() => props.data?.available || 0)
    const memoryCached = computed(() => props.data?.cached || 0)
    
    const usageClass = computed(() => {
      const percent = memoryPercent.value
      if (percent >= 90) return 'danger'
      if (percent >= 70) return 'warning'
      return 'normal'
    })
    
    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    return {
      memoryPercent,
      memoryTotal,
      memoryUsed,
      memoryAvailable,
      memoryCached,
      usageClass,
      formatBytes
    }
  }
}
</script>

<style scoped>
.memory-widget {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  height: 100%;
}

.memory-visual {
  display: flex;
  align-items: center;
  gap: var(--spacing-6);
}

.memory-ring {
  position: relative;
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}

.memory-ring svg {
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

.ring-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.ring-value {
  display: block;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.ring-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.memory-stats {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.mem-stat {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-1) 0;
  border-bottom: 1px solid var(--border-color);
}

.mem-stat:last-child {
  border-bottom: none;
}

.mem-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.mem-value {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.memory-bar {
  margin-top: auto;
}

.bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-1);
}

.bar-track {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.bar-fill.normal { background: linear-gradient(90deg, var(--success-500), var(--success-400)); }
.bar-fill.warning { background: linear-gradient(90deg, var(--warning-500), var(--warning-400)); }
.bar-fill.danger { background: linear-gradient(90deg, var(--danger-500), var(--danger-400)); }
</style>
