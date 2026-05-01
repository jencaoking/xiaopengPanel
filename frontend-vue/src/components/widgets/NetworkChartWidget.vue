<template>
  <div class="network-chart-widget">
    <div class="chart-container" ref="chartContainer">
      <canvas ref="chartCanvas"></canvas>
    </div>
    <div class="traffic-summary">
      <div class="summary-item upload">
        <svg viewBox="0 0 24 24" class="summary-icon">
          <path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z" fill="currentColor"/>
        </svg>
        <div class="summary-info">
          <span class="summary-label">{{ $t('dashboard.upload') }}</span>
          <span class="summary-value">{{ formatSpeed(currentUpload) }}</span>
        </div>
      </div>
      <div class="summary-item download">
        <svg viewBox="0 0 24 24" class="summary-icon">
          <path d="M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z" fill="currentColor"/>
        </svg>
        <div class="summary-info">
          <span class="summary-label">{{ $t('dashboard.download') }}</span>
          <span class="summary-value">{{ formatSpeed(currentDownload) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export default {
  name: 'NetworkChartWidget',
  props: {
    data: {
      type: Object,
      default: () => ({})
    },
    timeRange: {
      type: String,
      default: '1h'
    }
  },
  setup(props) {
    const chartContainer = ref(null)
    const chartCanvas = ref(null)
    const chartInstance = shallowRef(null)
    
    const currentUpload = computed(() => props.data?.current?.upload_speed || 0)
    const currentDownload = computed(() => props.data?.current?.download_speed || 0)
    
    const uploadHistory = computed(() => props.data?.upload || [])
    const downloadHistory = computed(() => props.data?.download || [])
    
    const formatSpeed = (bytesPerSec) => {
      if (bytesPerSec === 0) return '0 B/s'
      const k = 1024
      const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s']
      const i = Math.floor(Math.log(bytesPerSec) / Math.log(k))
      return parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    const initChart = () => {
      if (!chartCanvas.value) return
      
      const ctx = chartCanvas.value.getContext('2d')
      
      chartInstance.value = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Upload',
              data: [],
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 0
            },
            {
              label: 'Download',
              data: [],
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            intersect: false,
            mode: 'index'
          },
          plugins: {
            legend: {
              display: true,
              position: 'top',
              align: 'end',
              labels: {
                boxWidth: 12,
                padding: 8,
                font: { size: 11 }
              }
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  return `${context.dataset.label}: ${formatSpeed(context.raw)}`
                }
              }
            }
          },
          scales: {
            x: {
              display: true,
              grid: { display: false },
              ticks: { font: { size: 10 }, maxTicksLimit: 6 }
            },
            y: {
              display: true,
              beginAtZero: true,
              grid: { color: 'rgba(0,0,0,0.05)' },
              ticks: {
                font: { size: 10 },
                callback: (value) => formatSpeed(value)
              }
            }
          }
        }
      })
    }
    
    const updateChart = () => {
      if (!chartInstance.value) return
      
      const uploadData = uploadHistory.value
      const downloadData = downloadHistory.value
      
      const labels = uploadData.map(item => {
        const date = new Date(item.timestamp)
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })
      
      chartInstance.value.data.labels = labels
      chartInstance.value.data.datasets[0].data = uploadData.map(item => item.value)
      chartInstance.value.data.datasets[1].data = downloadData.map(item => item.value)
      chartInstance.value.update('none')
    }
    
    watch(() => props.data, updateChart, { deep: true })
    
    onMounted(() => {
      setTimeout(initChart, 100)
    })
    
    onUnmounted(() => {
      if (chartInstance.value) {
        chartInstance.value.destroy()
      }
    })
    
    return {
      chartContainer,
      chartCanvas,
      currentUpload,
      currentDownload,
      formatSpeed
    }
  }
}
</script>

<style scoped>
.network-chart-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.traffic-summary {
  display: flex;
  gap: var(--spacing-4);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-color);
  margin-top: var(--spacing-3);
}

.summary-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2);
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
}

.summary-icon {
  width: 24px;
  height: 24px;
}

.summary-item.upload .summary-icon {
  color: var(--primary-500);
}

.summary-item.download .summary-icon {
  color: var(--success-500);
}

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.summary-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}
</style>
