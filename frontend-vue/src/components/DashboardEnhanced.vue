<template>
  <div class="dashboard-enhanced">
    <div class="dashboard-header">
      <div class="header-left">
        <h2>{{ $t('dashboard.welcome') }}</h2>
        <span class="current-time">{{ currentTime }}</span>
      </div>
      <div class="header-right">
        <div class="time-range-selector">
          <button 
            v-for="period in timeRanges" 
            :key="period.value"
            :class="['period-btn', { active: selectedTimeRange === period.value }]"
            @click="selectedTimeRange = period.value"
          >{{ period.label }}</button>
        </div>
        <button class="btn btn-secondary" @click="refreshAllData" :disabled="isRefreshing">
          <svg class="icon" :class="{ spinning: isRefreshing }" viewBox="0 0 24 24">
            <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/>
          </svg>
          {{ $t('common.refresh') }}
        </button>
        <button class="btn btn-primary" @click="exportData">
          <svg class="icon" viewBox="0 0 24 24">
            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="currentColor"/>
          </svg>
          {{ $t('common.export') }}
        </button>
        <button class="btn btn-icon" @click="toggleEditMode" :class="{ active: editMode }">
          <svg viewBox="0 0 24 24">
            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="widgets-container" ref="widgetsContainer">
      <div 
        v-for="widget in visibleWidgets" 
        :key="widget.id"
        :class="['widget', { editing: editMode }]"
        :style="getWidgetStyle(widget)"
        @mousedown="startDrag($event, widget)"
      >
        <div class="widget-header">
          <h3 class="widget-title">
            <component :is="getWidgetIcon(widget.id)" class="widget-icon" />
            {{ getWidgetTitle(widget.id) }}
          </h3>
          <div class="widget-actions" v-if="editMode">
            <button class="action-btn" @click="toggleWidgetVisibility(widget.id)">
              <svg viewBox="0 0 24 24">
                <path v-if="widget.visible" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" fill="currentColor"/>
                <path v-else d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z" fill="currentColor"/>
              </svg>
            </button>
            <button class="action-btn" @click="removeWidget(widget.id)">
              <svg viewBox="0 0 24 24">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="widget-content">
          <component 
            :is="getWidgetComponent(widget.id)" 
            :data="widgetData[widget.id]"
            :time-range="selectedTimeRange"
            @refresh="refreshWidget(widget.id)"
          />
        </div>
        <div class="resize-handle" v-if="editMode" @mousedown.stop="startResize($event, widget)"></div>
      </div>
    </div>

    <div class="widget-palette" v-if="editMode">
      <h4>{{ $t('dashboard.addWidget') }}</h4>
      <div class="palette-items">
        <button 
          v-for="widgetType in availableWidgetTypes" 
          :key="widgetType.id"
          class="palette-item"
          @click="addWidget(widgetType.id)"
        >
          <component :is="widgetType.icon" />
          <span>{{ widgetType.title }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, shallowRef, markRaw } from 'vue'
import { useStore } from 'vuex'
import { useI18n } from 'vue-i18n'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

import CpuWidget from './widgets/CpuWidget.vue'
import MemoryWidget from './widgets/MemoryWidget.vue'
import DiskWidget from './widgets/DiskWidget.vue'
import NetworkWidget from './widgets/NetworkWidget.vue'
import TopProcessesWidget from './widgets/TopProcessesWidget.vue'
import NetworkChartWidget from './widgets/NetworkChartWidget.vue'
import DiskIoChartWidget from './widgets/DiskIoChartWidget.vue'
import HistoryChartWidget from './widgets/HistoryChartWidget.vue'

export default {
  name: 'DashboardEnhanced',
  components: {
    CpuWidget,
    MemoryWidget,
    DiskWidget,
    NetworkWidget,
    TopProcessesWidget,
    NetworkChartWidget,
    DiskIoChartWidget,
    HistoryChartWidget
  },
  setup() {
    const store = useStore()
    const { t } = useI18n()
    
    const currentTime = ref('')
    const isRefreshing = ref(false)
    const editMode = ref(false)
    const selectedTimeRange = ref('1h')
    const widgetsContainer = ref(null)
    
    const widgets = ref([])
    const widgetData = ref({})
    
    const timeRanges = [
      { label: '1h', value: '1h' },
      { label: '6h', value: '6h' },
      { label: '24h', value: '24h' },
      { label: '7d', value: '7d' },
      { label: '30d', value: '30d' }
    ]
    
    const widgetComponents = {
      cpu: 'CpuWidget',
      memory: 'MemoryWidget',
      disk: 'DiskWidget',
      network: 'NetworkWidget',
      top_processes: 'TopProcessesWidget',
      network_chart: 'NetworkChartWidget',
      disk_io_chart: 'DiskIoChartWidget',
      history_chart: 'HistoryChartWidget'
    }
    
    const widgetTitles = computed(() => ({
      cpu: 'CPU',
      memory: t('common.memoryUsage'),
      disk: t('common.diskUsage'),
      network: t('common.networkTraffic'),
      top_processes: t('dashboard.topProcesses'),
      network_chart: t('dashboard.networkChart'),
      disk_io_chart: t('dashboard.diskIoChart'),
      history_chart: t('dashboard.historyChart')
    }))
    
    const availableWidgetTypes = computed(() => {
      const existingIds = widgets.value.map(w => w.id)
      return [
        { id: 'cpu', title: 'CPU', icon: 'CpuIcon' },
        { id: 'memory', title: t('common.memoryUsage'), icon: 'MemoryIcon' },
        { id: 'disk', title: t('common.diskUsage'), icon: 'DiskIcon' },
        { id: 'network', title: t('common.networkTraffic'), icon: 'NetworkIcon' },
        { id: 'top_processes', title: t('dashboard.topProcesses'), icon: 'ProcessIcon' },
        { id: 'network_chart', title: t('dashboard.networkChart'), icon: 'ChartIcon' },
        { id: 'disk_io_chart', title: t('dashboard.diskIoChart'), icon: 'ChartIcon' },
        { id: 'history_chart', title: t('dashboard.historyChart'), icon: 'ChartIcon' }
      ].filter(w => !existingIds.includes(w.id))
    })
    
    const visibleWidgets = computed(() => widgets.value.filter(w => w.visible))
    
    let updateInterval = null
    let timeInterval = null
    
    const updateTime = () => {
      currentTime.value = new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        weekday: 'short'
      })
    }
    
    const fetchWidgetLayout = async () => {
      try {
        const token = store.state.token
        const response = await fetch('/api/dashboard/widgets/layout', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        const layout = await response.json()
        if (layout.widgets) {
          widgets.value = layout.widgets
        } else {
          widgets.value = getDefaultWidgets()
        }
      } catch (error) {
        console.error('Failed to fetch widget layout:', error)
        widgets.value = getDefaultWidgets()
      }
    }
    
    const saveWidgetLayout = async () => {
      try {
        const token = store.state.token
        await fetch('/api/dashboard/widgets/layout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ widgets: widgets.value, columns: 12 })
        })
      } catch (error) {
        console.error('Failed to save widget layout:', error)
      }
    }
    
    const getDefaultWidgets = () => [
      { id: 'cpu', x: 0, y: 0, w: 6, h: 4, visible: true },
      { id: 'memory', x: 6, y: 0, w: 6, h: 4, visible: true },
      { id: 'disk', x: 0, y: 4, w: 6, h: 4, visible: true },
      { id: 'network', x: 6, y: 4, w: 6, h: 4, visible: true },
      { id: 'top_processes', x: 0, y: 8, w: 12, h: 6, visible: true },
      { id: 'network_chart', x: 0, y: 14, w: 6, h: 5, visible: true },
      { id: 'disk_io_chart', x: 6, y: 14, w: 6, h: 5, visible: true }
    ]
    
    const getWidgetStyle = (widget) => {
      const containerWidth = widgetsContainer.value?.clientWidth || 1200
      const colWidth = containerWidth / 12
      const rowHeight = 80
      
      return {
        position: 'absolute',
        left: `${widget.x * colWidth}px`,
        top: `${widget.y * rowHeight}px`,
        width: `${widget.w * colWidth}px`,
        height: `${widget.h * rowHeight}px`
      }
    }
    
    const getWidgetComponent = (widgetId) => {
      return widgetComponents[widgetId] || 'div'
    }
    
    const getWidgetTitle = (widgetId) => {
      return widgetTitles.value[widgetId] || widgetId
    }
    
    const getWidgetIcon = (widgetId) => {
      return 'div'
    }
    
    const toggleEditMode = () => {
      editMode.value = !editMode.value
      if (!editMode.value) {
        saveWidgetLayout()
      }
    }
    
    const toggleWidgetVisibility = (widgetId) => {
      const widget = widgets.value.find(w => w.id === widgetId)
      if (widget) {
        widget.visible = !widget.visible
      }
    }
    
    const removeWidget = (widgetId) => {
      widgets.value = widgets.value.filter(w => w.id !== widgetId)
    }
    
    const addWidget = (widgetId) => {
      const existingPositions = widgets.value.map(w => ({ x: w.x, y: w.y, w: w.w, h: w.h }))
      let y = 0
      let x = 0
      
      for (const pos of existingPositions) {
        if (pos.y + pos.h > y) {
          y = pos.y + pos.h
        }
      }
      
      widgets.value.push({
        id: widgetId,
        x: 0,
        y: y,
        w: 6,
        h: 4,
        visible: true
      })
    }
    
    let dragState = null
    let resizeState = null
    
    const startDrag = (event, widget) => {
      if (!editMode.value) return
      
      const container = widgetsContainer.value
      const rect = container.getBoundingClientRect()
      
      dragState = {
        widget,
        startX: event.clientX,
        startY: event.clientY,
        originalX: widget.x,
        originalY: widget.y,
        containerLeft: rect.left,
        containerTop: rect.top,
        colWidth: rect.width / 12,
        rowHeight: 80
      }
      
      document.addEventListener('mousemove', onDrag)
      document.addEventListener('mouseup', stopDrag)
    }
    
    const onDrag = (event) => {
      if (!dragState) return
      
      const deltaX = event.clientX - dragState.startX
      const deltaY = event.clientY - dragState.startY
      
      const newCol = Math.round(deltaX / dragState.colWidth)
      const newRow = Math.round(deltaY / dragState.rowHeight)
      
      dragState.widget.x = Math.max(0, Math.min(12 - dragState.widget.w, dragState.originalX + newCol))
      dragState.widget.y = Math.max(0, dragState.originalY + newRow)
    }
    
    const stopDrag = () => {
      dragState = null
      document.removeEventListener('mousemove', onDrag)
      document.removeEventListener('mouseup', stopDrag)
    }
    
    const startResize = (event, widget) => {
      const container = widgetsContainer.value
      const rect = container.getBoundingClientRect()
      
      resizeState = {
        widget,
        startX: event.clientX,
        startY: event.clientY,
        originalW: widget.w,
        originalH: widget.h,
        colWidth: rect.width / 12,
        rowHeight: 80
      }
      
      document.addEventListener('mousemove', onResize)
      document.addEventListener('mouseup', stopResize)
    }
    
    const onResize = (event) => {
      if (!resizeState) return
      
      const deltaX = event.clientX - resizeState.startX
      const deltaY = event.clientY - resizeState.startY
      
      const newCols = Math.round(deltaX / resizeState.colWidth)
      const newRows = Math.round(deltaY / resizeState.rowHeight)
      
      resizeState.widget.w = Math.max(2, Math.min(12, resizeState.originalW + newCols))
      resizeState.widget.h = Math.max(2, resizeState.originalH + newRows)
    }
    
    const stopResize = () => {
      resizeState = null
      document.removeEventListener('mousemove', onResize)
      document.removeEventListener('mouseup', stopResize)
    }
    
    const fetchAllData = async () => {
      const token = store.state.token
      
      try {
        const [realtimeRes, topProcessesRes, networkHistoryRes, diskIoHistoryRes] = await Promise.all([
          fetch('/api/monitor/realtime', { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch('/api/monitor/top-processes?limit=10', { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`/api/monitor/network/traffic/history?time_range=${selectedTimeRange.value}`, { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch(`/api/monitor/disk-io/history?time_range=${selectedTimeRange.value}`, { headers: { 'Authorization': `Bearer ${token}` } })
        ])
        
        const realtime = await realtimeRes.json()
        const topProcesses = await topProcessesRes.json()
        const networkHistory = await networkHistoryRes.json()
        const diskIoHistory = await diskIoHistoryRes.json()
        
        widgetData.value = {
          cpu: realtime.cpu,
          memory: realtime.memory,
          disk: realtime.disk_io,
          network: realtime.network,
          top_processes: topProcesses,
          network_chart: networkHistory,
          disk_io_chart: diskIoHistory,
          history_chart: {
            cpu: realtime.cpu,
            memory: realtime.memory
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error)
      }
    }
    
    const refreshWidget = async (widgetId) => {
      await fetchAllData()
    }
    
    const refreshAllData = async () => {
      isRefreshing.value = true
      await fetchAllData()
      setTimeout(() => {
        isRefreshing.value = false
      }, 500)
    }
    
    const exportData = async () => {
      try {
        const token = store.state.token
        const response = await fetch('/api/monitor/export', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            metric_types: ['cpu', 'memory', 'network_sent', 'network_recv', 'disk_read', 'disk_write'],
            time_range: selectedTimeRange.value,
            format: 'json'
          })
        })
        
        const data = await response.json()
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `metrics_export_${new Date().toISOString().slice(0, 10)}.json`
        a.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        console.error('Failed to export data:', error)
      }
    }
    
    onMounted(() => {
      updateTime()
      timeInterval = setInterval(updateTime, 1000)
      
      fetchWidgetLayout()
      fetchAllData()
      
      updateInterval = setInterval(fetchAllData, 5000)
      
      window.addEventListener('resize', () => {
        if (widgetsContainer.value) {
          widgetsContainer.value.style.height = 'auto'
        }
      })
    })
    
    onUnmounted(() => {
      if (updateInterval) clearInterval(updateInterval)
      if (timeInterval) clearInterval(timeInterval)
    })
    
    return {
      currentTime,
      isRefreshing,
      editMode,
      selectedTimeRange,
      widgets,
      widgetData,
      timeRanges,
      availableWidgetTypes,
      visibleWidgets,
      widgetsContainer,
      getWidgetStyle,
      getWidgetComponent,
      getWidgetTitle,
      getWidgetIcon,
      toggleEditMode,
      toggleWidgetVisibility,
      removeWidget,
      addWidget,
      startDrag,
      startResize,
      refreshAllData,
      refreshWidget,
      exportData
    }
  }
}
</script>

<style scoped>
.dashboard-enhanced {
  padding: var(--spacing-6);
  max-width: 1600px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--ios-glass-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border-radius: var(--radius-xl);
  border: 1px solid var(--ios-glass-border);
  box-shadow: var(--ios-card-shadow), inset 0 1px 0 0 var(--ios-glass-highlight);
  transition: var(--ios-theme-transition);
}

.header-left h2 {
  margin: 0;
  font-size: var(--font-size-xl);
  color: var(--text-primary);
}

.current-time {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.time-range-selector {
  display: flex;
  gap: var(--spacing-1);
  background: var(--bg-tertiary);
  padding: var(--spacing-1);
  border-radius: var(--radius-lg);
}

.period-btn {
  padding: var(--spacing-2) var(--spacing-3);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.period-btn:hover {
  color: var(--text-primary);
}

.period-btn.active {
  background: var(--primary-500);
  color: white;
}

.widgets-container {
  position: relative;
  min-height: 600px;
}

.widget {
  background: var(--ios-card-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border-radius: var(--radius-xl);
  border: 1px solid var(--ios-glass-border);
  box-shadow: var(--ios-card-shadow), inset 0 1px 0 0 var(--ios-glass-highlight);
  overflow: hidden;
  transition: box-shadow var(--duration-normal) var(--ease-out),
              background var(--ios-transition-normal);
}

.widget:hover {
  box-shadow: var(--ios-card-hover-shadow);
  background: var(--ios-glass-bg-hover);
}

.widget.editing {
  cursor: move;
  border: 2px dashed var(--primary-400);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.widget-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.widget-icon {
  width: 18px;
  height: 18px;
}

.widget-actions {
  display: flex;
  gap: var(--spacing-1);
}

.action-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.widget-content {
  padding: var(--spacing-4);
  height: calc(100% - 48px);
  overflow: auto;
}

.resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 20px;
  height: 20px;
  cursor: se-resize;
  background: linear-gradient(135deg, transparent 50%, var(--primary-400) 50%);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.widget.editing .resize-handle {
  opacity: 1;
}

.widget-palette {
  position: fixed;
  bottom: var(--spacing-6);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: var(--spacing-4);
  box-shadow: var(--shadow-xl);
  z-index: 100;
}

.widget-palette h4 {
  margin: 0 0 var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.palette-items {
  display: flex;
  gap: var(--spacing-2);
}

.palette-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-3);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.palette-item:hover {
  border-color: var(--primary-500);
  background: var(--primary-50);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-lg);
  border: none;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-primary {
  background: var(--primary-500);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-600);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-icon {
  width: 40px;
  height: 40px;
  padding: 0;
  justify-content: center;
  background: transparent;
  color: var(--text-secondary);
}

.btn-icon:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-icon.active {
  background: var(--primary-500);
  color: white;
}

.icon {
  width: 18px;
  height: 18px;
}

.icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .dashboard-enhanced {
    padding: var(--spacing-4);
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: var(--spacing-4);
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .time-range-selector {
    overflow-x: auto;
  }
}
</style>
