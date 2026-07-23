<template>
  <div class="history-chart-widget">
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch, shallowRef, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export default {
  name: 'HistoryChartWidget',
  props: {
    data: { type: Object, default: () => ({}) },
    timeRange: { type: String, default: '1h' }
  },
  setup(props) {
    const chartCanvas = ref(null)
    const chartInstance = shallowRef(null)
    let isUnmounted = false

    const initChart = () => {
      if (!chartCanvas.value || isUnmounted) return

      const ctx = chartCanvas.value.getContext('2d')

      chartInstance.value = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'CPU',
              data: [],
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.4,
              pointRadius: 0
            },
            {
              label: 'Memory',
              data: [],
              borderColor: '#8b5cf6',
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
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
          interaction: { intersect: false, mode: 'index' },
          plugins: {
            legend: { display: true, position: 'top', align: 'end', labels: { boxWidth: 12, padding: 8 } }
          },
          scales: {
            x: { display: true, grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: 8 } },
            y: { display: true, beginAtZero: true, max: 100, grid: { color: 'rgba(128, 128, 128, 0.15)' }, ticks: { font: { size: 10 }, callback: (v) => v + '%' } }
          }
        }
      })

      updateChart()
    }

    const updateChart = () => {
      if (!chartInstance.value || isUnmounted) return

      const cpuHistory = props.data?.cpu || []
      const memHistory = props.data?.memory || []

      // 尝试从 data 中提取历史数据
      const cpuData = Array.isArray(cpuHistory) ? cpuHistory : (cpuHistory?.history || [])
      const memData = Array.isArray(memHistory) ? memHistory : (memHistory?.history || [])

      const labels = cpuData.map((item, i) => {
        const ts = item.timestamp || (memData[i] && memData[i].timestamp)
        if (!ts) return ''
        return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })

      chartInstance.value.data.labels = labels
      chartInstance.value.data.datasets[0].data = cpuData.map(item =>
        typeof item === 'number' ? item : (item.value || item.usage || item.cpu_percent || 0)
      )
      chartInstance.value.data.datasets[1].data = memData.map(item =>
        typeof item === 'number' ? item : (item.value || item.percent || item.memory_percent || 0)
      )
      chartInstance.value.update('none')
    }

    watch(() => props.data, updateChart, { deep: true })

    onMounted(() => {
      nextTick(() => {
        if (!isUnmounted) initChart()
      })
    })

    onUnmounted(() => {
      isUnmounted = true
      if (chartInstance.value) {
        chartInstance.value.destroy()
        chartInstance.value = null
      }
    })

    return { chartCanvas }
  }
}
</script>

<style scoped>
.history-chart-widget { height: 100%; }
.chart-container { height: 100%; }
</style>
