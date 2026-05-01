<template>
  <div class="history-chart-widget">
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, shallowRef } from 'vue'
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
    
    const initChart = () => {
      if (!chartCanvas.value) return
      
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
            y: { display: true, beginAtZero: true, max: 100, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { font: { size: 10 }, callback: (v) => v + '%' } }
          }
        }
      })
    }
    
    onMounted(() => setTimeout(initChart, 100))
    
    onUnmounted(() => {
      if (chartInstance.value) chartInstance.value.destroy()
    })
    
    return { chartCanvas }
  }
}
</script>

<style scoped>
.history-chart-widget { height: 100%; }
.chart-container { height: 100%; }
</style>
