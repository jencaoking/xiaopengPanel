<template>
  <div class="disk-io-chart-widget">
    <div class="chart-container" ref="chartContainer">
      <canvas ref="chartCanvas"></canvas>
    </div>
    <div class="io-stats">
      <div class="stat-item">
        <span class="stat-label">{{ $t('dashboard.readSpeed') }}</span>
        <span class="stat-value">{{ formatSpeed(readSpeed) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">{{ $t('dashboard.writeSpeed') }}</span>
        <span class="stat-value">{{ formatSpeed(writeSpeed) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">IOPS {{ $t('dashboard.read') }}</span>
        <span class="stat-value">{{ iopsRead.toFixed(0) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">IOPS {{ $t('dashboard.write') }}</span>
        <span class="stat-value">{{ iopsWrite.toFixed(0) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export default {
  name: 'DiskIoChartWidget',
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
    const chartCanvas = ref(null)
    const chartInstance = shallowRef(null)
    
    const readSpeed = computed(() => props.data?.current?.read_speed || 0)
    const writeSpeed = computed(() => props.data?.current?.write_speed || 0)
    const iopsRead = computed(() => props.data?.current?.iops_read || 0)
    const iopsWrite = computed(() => props.data?.current?.iops_write || 0)
    
    const readHistory = computed(() => props.data?.read_speed || [])
    const writeHistory = computed(() => props.data?.write_speed || [])
    
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
              label: 'Read',
              data: [],
              borderColor: '#8b5cf6',
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 0
            },
            {
              label: 'Write',
              data: [],
              borderColor: '#f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.1)',
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
              labels: { boxWidth: 12, padding: 8, font: { size: 11 } }
            },
            tooltip: {
              callbacks: {
                label: (context) => `${context.dataset.label}: ${formatSpeed(context.raw)}`
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
      
      const readData = readHistory.value
      const writeData = writeHistory.value
      
      const labels = readData.map(item => {
        const date = new Date(item.timestamp)
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })
      
      chartInstance.value.data.labels = labels
      chartInstance.value.data.datasets[0].data = readData.map(item => item.value)
      chartInstance.value.data.datasets[1].data = writeData.map(item => item.value)
      chartInstance.value.update('none')
    }
    
    watch(() => props.data, updateChart, { deep: true })
    
    onMounted(() => setTimeout(initChart, 100))
    
    onUnmounted(() => {
      if (chartInstance.value) chartInstance.value.destroy()
    })
    
    return {
      chartCanvas,
      readSpeed,
      writeSpeed,
      iopsRead,
      iopsWrite,
      formatSpeed
    }
  }
}
</script>

<style scoped>
.disk-io-chart-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.io-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-2);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-color);
  margin-top: var(--spacing-3);
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-1);
}

.stat-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}
</style>
