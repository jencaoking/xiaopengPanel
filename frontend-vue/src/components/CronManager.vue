<template>
  <div id="cron-manager" class="page cron-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-title">
        <h2>{{ $t('cron.title') }}</h2>
        <p class="page-subtitle">{{ $t('cron.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="fetchTasks" :disabled="loading">
          <svg v-if="loading" class="icon-spin" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
          </svg>
          <span v-else>{{ $t('common.refresh') }}</span>
        </button>
        <button class="btn btn-primary" @click="showAddModal">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          {{ $t('cron.addTask') }}
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-error">
      <svg viewBox="0 0 24 24" width="20" height="20" class="alert-icon">
        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
      </svg>
      <span>{{ error }}</span>
    </div>

    <!-- 状态卡片 -->
    <div class="status-cards">
      <div class="status-card glass-card">
        <div class="card-icon icon-total">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('cron.totalTasks') }}</span>
          <span class="card-value">{{ tasks.length }}</span>
        </div>
      </div>

      <div class="status-card glass-card">
        <div class="card-icon icon-enabled">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('cron.enabledTasks') }}</span>
          <span class="card-value text-success">{{ enabledCount }}</span>
        </div>
      </div>

      <div class="status-card glass-card">
        <div class="card-icon icon-history">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('cron.totalRuns') }}</span>
          <span class="card-value">{{ totalRuns }}</span>
        </div>
      </div>

      <div class="status-card glass-card">
        <div class="card-icon" :class="lastRunSuccess === false ? 'icon-failed' : 'icon-success'">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path v-if="lastRunSuccess" fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            <path v-else fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('cron.lastStatus') }}</span>
          <span class="card-value" :class="lastRunStatusClass">
            {{ lastRunStatusText }}
          </span>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="tasks-section glass-card">
      <div class="section-header">
        <h3 class="section-title">
          <svg viewBox="0 0 24 24" width="18" height="18" class="section-icon">
            <path fill="currentColor" d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
          </svg>
          {{ $t('cron.taskList') }}
        </h3>
      </div>

      <!-- 筛选 -->
      <div class="rules-filter">
        <input
          type="text"
          v-model="searchQuery"
          :placeholder="$t('cron.searchTasks')"
          class="filter-input"
        >
        <select v-model="filterStatus" class="filter-select">
          <option value="">{{ $t('cron.allStatus') }}</option>
          <option value="enabled">{{ $t('cron.enabled') }}</option>
          <option value="disabled">{{ $t('cron.disabled') }}</option>
        </select>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ $t('cron.taskName') }}</th>
              <th>{{ $t('cron.cronExpr') }}</th>
              <th>{{ $t('cron.status') }}</th>
              <th>{{ $t('cron.lastRun') }}</th>
              <th>{{ $t('cron.nextRun') }}</th>
              <th>{{ $t('cron.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && tasks.length === 0">
              <td colspan="6" class="loading">{{ $t('common.loading') }}</td>
            </tr>
            <tr v-else-if="filteredTasks.length === 0">
              <td colspan="6" class="no-data">{{ $t('cron.noTasks') }}</td>
            </tr>
            <tr v-for="task in paginatedTasks" :key="task.task_id">
              <td>
                <div class="task-name">{{ task.name }}</div>
                <div class="task-desc" v-if="task.description">{{ task.description }}</div>
              </td>
              <td>
                <code class="cron-code">{{ task.cron_expr }}</code>
              </td>
              <td>
                <span class="action-badge" :class="task.enabled ? 'badge-enabled' : 'badge-disabled'">
                  {{ task.enabled ? $t('cron.enabled') : $t('cron.disabled') }}
                </span>
                <span v-if="task.last_status" class="status-badge" :class="task.last_status === 'success' ? 'badge-success' : 'badge-failed'">
                  {{ task.last_status === 'success' ? $t('common.success') : $t('common.error') }}
                </span>
              </td>
              <td>
                <span v-if="task.last_run" class="time-cell">{{ formatTime(task.last_run) }}</span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <span v-if="task.next_run && task.enabled" class="time-cell">{{ formatTime(task.next_run) }}</span>
                <span v-else class="text-muted">-</span>
              </td>
              <td>
                <div class="action-buttons">
                  <button
                    class="btn btn-secondary btn-sm"
                    @click="runTask(task)"
                    :disabled="actionLoading || runningTaskId !== null"
                    :title="$t('cron.runNow')"
                  >
                    <svg v-if="runningTaskId === task.task_id" class="icon-spin" viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M8 5v14l11-7z"/>
                    </svg>
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    @click="toggleTask(task)"
                    :disabled="actionLoading"
                    :title="task.enabled ? $t('cron.disable') : $t('cron.enable')"
                  >
                    <svg v-if="task.enabled" viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13H9v10h2z"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
                    </svg>
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    @click="showHistory(task)"
                    :title="$t('cron.history')"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
                    </svg>
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    @click="showEditModal(task)"
                    :title="$t('common.edit')"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                  </button>
                  <button
                    class="btn btn-danger btn-sm"
                    @click="deleteTask(task)"
                    :disabled="actionLoading"
                    :title="$t('common.delete')"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14">
                      <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="filteredTasks.length > pageSize">
        <button class="btn btn-secondary btn-sm" @click="currentPage--" :disabled="currentPage <= 1">
          {{ $t('common.prev') }}
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="btn btn-secondary btn-sm" @click="currentPage++" :disabled="currentPage >= totalPages">
          {{ $t('common.next') }}
        </button>
      </div>
    </div>

    <!-- 添加/编辑任务模态框 -->
    <div class="modal" v-if="showModal" @click="handleModalBackdropClick($event, 'showModal')">
      <div class="modal-content glass-card">
        <div class="modal-header">
          <h3>{{ editingTask ? $t('cron.editTask') : $t('cron.addTask') }}</h3>
          <button class="close-btn" @click="showModal = false">&times;</button>
        </div>
        <form @submit.prevent="saveTask">
          <div class="form-group">
            <label>{{ $t('cron.taskName') }} *</label>
            <input
              type="text"
              v-model="taskForm.name"
              :placeholder="$t('cron.taskNamePlaceholder')"
              required
            >
          </div>
          <div class="form-group">
            <label>{{ $t('cron.command') }} *</label>
            <input
              type="text"
              v-model="taskForm.command"
              :placeholder="$t('cron.commandPlaceholder')"
              required
            >
            <span class="form-hint">{{ $t('cron.commandHint') }}</span>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>{{ $t('cron.cronExpr') }} *</label>
              <input
                type="text"
                v-model="taskForm.cron_expr"
                :placeholder="$t('cron.cronExprPlaceholder')"
                required
                @input="validateCronLive"
              >
              <span class="form-hint" :class="cronValidationClass">
                {{ cronValidationMessage }}
              </span>
            </div>
            <div class="form-group">
              <label>{{ $t('cron.timeout') }}</label>
              <input
                type="number"
                v-model.number="taskForm.timeout"
                :placeholder="3600"
                min="1"
              >
              <span class="form-hint">{{ $t('cron.timeoutHint') }}</span>
            </div>
          </div>
          <!-- Cron 预设 -->
          <div class="form-group">
            <label>{{ $t('cron.presets') }}</label>
            <div class="presets">
              <button
                type="button"
                v-for="preset in cronPresets"
                :key="preset.value"
                class="preset-btn"
                @click="taskForm.cron_expr = preset.value; validateCronLive()"
              >
                {{ $t(preset.label) }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>{{ $t('cron.description') }}</label>
            <textarea
              v-model="taskForm.description"
              :placeholder="$t('cron.descriptionPlaceholder')"
              rows="2"
            ></textarea>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="taskForm.enabled">
              <span>{{ $t('cron.enableAfterCreate') }}</span>
            </label>
          </div>
          <div class="alert alert-info" v-if="modalError">{{ modalError }}</div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary" :disabled="actionLoading">
              {{ $t('common.save') }}
            </button>
            <button type="button" class="btn btn-secondary" @click="showModal = false">
              {{ $t('common.cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 历史记录模态框 -->
    <div class="modal" v-if="showHistoryModal" @click="handleModalBackdropClick($event, 'showHistoryModal')">
      <div class="modal-content modal-large glass-card">
        <div class="modal-header">
          <h3>{{ $t('cron.historyTitle') }} - {{ historyTaskName }}</h3>
          <button class="close-btn" @click="showHistoryModal = false">&times;</button>
        </div>
        <div class="history-actions">
          <button class="btn btn-secondary btn-sm" @click="refreshHistory" :disabled="historyLoading">
            {{ $t('common.refresh') }}
          </button>
          <button class="btn btn-danger btn-sm" @click="clearHistory" :disabled="clearingHistory">
            {{ clearingHistory ? $t('common.loading') + '...' : $t('common.clear') }}
          </button>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ $t('cron.startTime') }}</th>
                <th>{{ $t('cron.duration') }}</th>
                <th>{{ $t('cron.status') }}</th>
                <th>{{ $t('cron.trigger') }}</th>
                <th>{{ $t('cron.exitCode') }}</th>
                <th>{{ $t('cron.output') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="historyLoading">
                <td colspan="6" class="loading">{{ $t('common.loading') }}</td>
              </tr>
              <tr v-else-if="historyList.length === 0">
                <td colspan="6" class="no-data">{{ $t('cron.noHistory') }}</td>
              </tr>
              <tr v-for="record in historyList" :key="record.run_id">
                <td class="time-cell">{{ formatTime(record.start_time) }}</td>
                <td>{{ formatDuration(record.duration) }}</td>
                <td>
                  <span class="action-badge" :class="record.status === 'success' ? 'badge-success' : 'badge-failed'">
                    {{ record.status === 'success' ? $t('common.success') : $t('common.error') }}
                  </span>
                </td>
                <td>
                  <span class="direction-badge">{{ record.trigger_type === 'manual' ? $t('cron.manual') : $t('cron.scheduled') }}</span>
                </td>
                <td>
                  <code class="exit-code" :class="record.exit_code === 0 ? 'code-success' : 'code-failed'">{{ record.exit_code }}</code>
                </td>
                <td>
                  <button class="btn btn-secondary btn-sm" @click="showOutput(record)">
                    {{ $t('cron.viewOutput') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 输出详情模态框 -->
    <div class="modal" v-if="showOutputModal" @click="handleModalBackdropClick($event, 'showOutputModal')">
      <div class="modal-content modal-large glass-card">
        <div class="modal-header">
          <h3>{{ $t('cron.outputTitle') }}</h3>
          <button class="close-btn" @click="showOutputModal = false">&times;</button>
        </div>
        <div class="output-detail" v-if="currentOutput">
          <div class="output-meta">
            <span><strong>{{ $t('cron.command') }}:</strong> <code>{{ currentOutput.command }}</code></span>
            <span><strong>{{ $t('cron.startTime') }}:</strong> {{ formatTime(currentOutput.start_time) }}</span>
            <span><strong>{{ $t('cron.duration') }}:</strong> {{ formatDuration(currentOutput.duration) }}</span>
            <span><strong>{{ $t('cron.exitCode') }}:</strong> {{ currentOutput.exit_code }}</span>
          </div>
          <div class="output-section">
            <h4>stdout</h4>
            <pre class="output-block">{{ currentOutput.stdout || $t('cron.noOutput') }}</pre>
          </div>
          <div class="output-section">
            <h4>stderr</h4>
            <pre class="output-block" :class="{ 'has-error': currentOutput.stderr }">{{ currentOutput.stderr || $t('cron.noOutput') }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CronManager',
  data() {
    return {
      loading: false,
      actionLoading: false,
      error: '',
      tasks: [],
      searchQuery: '',
      filterStatus: '',
      currentPage: 1,
      pageSize: 15,
      // 模态框
      showModal: false,
      editingTask: null,
      modalError: '',
      taskForm: {
        name: '',
        command: '',
        cron_expr: '',
        description: '',
        enabled: true,
        timeout: 3600
      },
      cronValid: null,
      // 历史
      showHistoryModal: false,
      historyTaskId: '',
      historyTaskName: '',
      historyList: [],
      historyLoading: false,
      // 输出
      showOutputModal: false,
      currentOutput: null,
      // 自动刷新
      refreshInterval: null,
      // Cron 校验防抖定时器
      cronValidateTimer: null,
      // 清空历史 loading 状态
      clearingHistory: false,
      // 正在运行的任务 ID（防止延迟刷新期间重复点击）
      runningTaskId: null,
      // Cron 预设
      cronPresets: [
        { value: '* * * * *', label: 'cron.everyMinute' },
        { value: '*/5 * * * *', label: 'cron.every5Minutes' },
        { value: '*/30 * * * *', label: 'cron.every30Minutes' },
        { value: '0 * * * *', label: 'cron.everyHour' },
        { value: '0 */6 * * *', label: 'cron.every6Hours' },
        { value: '0 0 * * *', label: 'cron.everyDay' },
        { value: '0 2 * * *', label: 'cron.everyDay2am' },
        { value: '0 0 * * 0', label: 'cron.everyWeek' },
        { value: '0 0 1 * *', label: 'cron.everyMonth' }
      ]
    }
  },
  computed: {
    filteredTasks() {
      let list = this.tasks
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase()
        list = list.filter(t =>
          String(t.name || '').toLowerCase().includes(q) ||
          String(t.command || '').toLowerCase().includes(q) ||
          String(t.cron_expr || '').toLowerCase().includes(q) ||
          String(t.description || '').toLowerCase().includes(q)
        )
      }
      if (this.filterStatus === 'enabled') {
        list = list.filter(t => t.enabled)
      } else if (this.filterStatus === 'disabled') {
        list = list.filter(t => !t.enabled)
      }
      return list
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredTasks.length / this.pageSize))
    },
    paginatedTasks() {
      const page = Math.min(this.currentPage, this.totalPages)
      const start = (page - 1) * this.pageSize
      return this.filteredTasks.slice(start, start + this.pageSize)
    },
    enabledCount() {
      return this.tasks.filter(t => t.enabled).length
    },
    totalRuns() {
      return this.tasks.reduce((sum, t) => sum + (t.run_count || 0), 0)
    },
    lastRunSuccess() {
      // 有任何失败返回 false，否则若有成功返回 true，无运行返回 null
      const hasFailed = this.tasks.some(t => t.last_status === 'failed')
      const hasSuccess = this.tasks.some(t => t.last_status === 'success')
      if (hasFailed) return false
      if (hasSuccess) return true
      return null
    },
    lastRunStatusText() {
      if (this.lastRunSuccess === null) return this.$t('cron.neverRun')
      return this.lastRunSuccess ? this.$t('common.success') : this.$t('common.error')
    },
    lastRunStatusClass() {
      if (this.lastRunSuccess === null) return 'text-muted'
      return this.lastRunSuccess ? 'text-success' : 'text-danger'
    },
    cronValidationClass() {
      if (this.cronValid === null) return ''
      return this.cronValid ? 'hint-success' : 'hint-error'
    },
    cronValidationMessage() {
      if (!this.taskForm.cron_expr) return this.$t('cron.cronHint')
      if (this.cronValid === null) return this.$t('cron.cronHint')
      return this.cronValid ? this.$t('cron.cronValid') : this.$t('cron.cronInvalid')
    }
  },
  watch: {
    searchQuery() { this.currentPage = 1 },
    filterStatus() { this.currentPage = 1 },
    // 当列表收缩（删除/刷新）导致当前页越界时，自动回退到最后一页
    totalPages(newVal) {
      if (this.currentPage > newVal) {
        this.currentPage = newVal
      }
    }
  },
  mounted() {
    this.fetchTasks()
    // 每 60 秒自动刷新任务列表
    this.refreshInterval = setInterval(() => {
      this.fetchTasks()
    }, 60000)
    // ESC 键关闭模态框
    document.addEventListener('keydown', this.handleKeyDown)
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
    if (this.cronValidateTimer) {
      clearTimeout(this.cronValidateTimer)
    }
    document.removeEventListener('keydown', this.handleKeyDown)
  },
  methods: {
    // ESC 键关闭当前打开的模态框
    handleKeyDown(e) {
      if (e.key === 'Escape') {
        if (this.showOutputModal) {
          this.showOutputModal = false
        } else if (this.showHistoryModal) {
          this.showHistoryModal = false
        } else if (this.showModal) {
          this.showModal = false
        }
      }
    },
    // 点击模态框背景关闭
    handleModalBackdropClick(e, modalName) {
      if (e.target === e.currentTarget) {
        this[modalName] = false
      }
    },
    async fetchTasks() {
      this.loading = true
      this.error = ''
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/cron/tasks',
          method: 'GET'
        })
        if (data.status === 'success') {
          this.tasks = data.tasks || []
        } else {
          this.error = data.message || 'Failed to load tasks'
        }
      } catch (err) {
        this.error = err.message || 'Failed to load tasks'
      } finally {
        this.loading = false
      }
    },
    showAddModal() {
      this.editingTask = null
      this.modalError = ''
      this.cronValid = null
      this.taskForm = {
        name: '',
        command: '',
        cron_expr: '',
        description: '',
        enabled: true,
        timeout: 3600
      }
      this.showModal = true
    },
    showEditModal(task) {
      this.editingTask = task
      this.modalError = ''
      this.cronValid = true
      this.taskForm = {
        name: task.name,
        command: task.command,
        cron_expr: task.cron_expr,
        description: task.description || '',
        enabled: task.enabled,
        timeout: task.timeout || 3600
      }
      this.showModal = true
    },
    async validateCronLive() {
      if (!this.taskForm.cron_expr) {
        this.cronValid = null
        if (this.cronValidateTimer) {
          clearTimeout(this.cronValidateTimer)
          this.cronValidateTimer = null
        }
        return
      }
      // 防抖：300ms 内只发送最后一次请求
      if (this.cronValidateTimer) {
        clearTimeout(this.cronValidateTimer)
      }
      this.cronValidateTimer = setTimeout(async () => {
        try {
          const data = await this.$store.dispatch('apiRequest', {
            url: '/api/cron/validate',
            method: 'POST',
            body: { cron_expr: this.taskForm.cron_expr }
          })
          this.cronValid = data.valid === true
        } catch (err) {
          this.cronValid = false
        } finally {
          this.cronValidateTimer = null
        }
      }, 300)
    },
    async saveTask() {
      this.modalError = ''
      if (!this.taskForm.name.trim() || !this.taskForm.command.trim() || !this.taskForm.cron_expr.trim()) {
        this.modalError = this.$t('cron.requiredFields')
        return
      }
      this.actionLoading = true
      try {
        const payload = {
          name: this.taskForm.name,
          command: this.taskForm.command,
          cron_expr: this.taskForm.cron_expr,
          description: this.taskForm.description,
          enabled: this.taskForm.enabled,
          timeout: this.taskForm.timeout
        }
        let data
        if (this.editingTask) {
          data = await this.$store.dispatch('apiRequest', {
            url: `/api/cron/tasks/${this.editingTask.task_id}`,
            method: 'PUT',
            body: payload
          })
        } else {
          data = await this.$store.dispatch('apiRequest', {
            url: '/api/cron/tasks',
            method: 'POST',
            body: payload
          })
        }
        if (data.status === 'success') {
          this.showModal = false
          await this.fetchTasks()
        } else {
          this.modalError = data.message || 'Failed to save task'
        }
      } catch (err) {
        this.modalError = err.message || 'Failed to save task'
      } finally {
        this.actionLoading = false
      }
    },
    async toggleTask(task) {
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: `/api/cron/tasks/${task.task_id}/toggle`,
          method: 'POST'
        })
        if (data.status === 'success') {
          await this.fetchTasks()
        } else {
          this.error = data.message || 'Toggle failed'
        }
      } catch (err) {
        this.error = err.message || 'Toggle failed'
      } finally {
        this.actionLoading = false
      }
    },
    async runTask(task) {
      // 防止延迟刷新期间重复点击
      if (this.runningTaskId !== null) return
      this.runningTaskId = task.task_id
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: `/api/cron/tasks/${task.task_id}/run`,
          method: 'POST'
        })
        if (data.status === 'success') {
          // 稍后刷新以获取执行结果
          setTimeout(async () => {
            await this.fetchTasks()
            this.runningTaskId = null
          }, 2000)
        } else {
          this.error = data.message || 'Run failed'
          this.runningTaskId = null
        }
      } catch (err) {
        this.error = err.message || 'Run failed'
        this.runningTaskId = null
      }
    },
    async deleteTask(task) {
      if (!confirm(this.$t('cron.confirmDelete'))) return
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: `/api/cron/tasks/${task.task_id}`,
          method: 'DELETE'
        })
        if (data.status === 'success') {
          await this.fetchTasks()
        } else {
          this.error = data.message || 'Delete failed'
        }
      } catch (err) {
        this.error = err.message || 'Delete failed'
      } finally {
        this.actionLoading = false
      }
    },
    async showHistory(task) {
      this.historyTaskId = task.task_id
      this.historyTaskName = task.name
      this.showHistoryModal = true
      await this.refreshHistory()
    },
    async refreshHistory() {
      this.historyLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: `/api/cron/tasks/${this.historyTaskId}/history?limit=50`,
          method: 'GET'
        })
        if (data.status === 'success') {
          this.historyList = data.history || []
        }
      } catch (err) {
        this.error = err.message
      } finally {
        this.historyLoading = false
      }
    },
    async clearHistory() {
      if (!confirm(this.$t('cron.confirmClearHistory'))) return
      this.clearingHistory = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: `/api/cron/tasks/${this.historyTaskId}/history`,
          method: 'DELETE'
        })
        if (data.status === 'success') {
          await this.refreshHistory()
        } else {
          this.error = data.message || 'Clear failed'
        }
      } catch (err) {
        this.error = err.message
      } finally {
        this.clearingHistory = false
      }
    },
    showOutput(record) {
      this.currentOutput = record
      this.showOutputModal = true
    },
    formatTime(isoStr) {
      if (!isoStr) return '-'
      try {
        const d = new Date(isoStr)
        const pad = n => String(n).padStart(2, '0')
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
      } catch (e) {
        return isoStr
      }
    },
    formatDuration(seconds) {
      if (seconds == null) return '-'
      if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
      if (seconds < 60) return `${seconds.toFixed(2)}s`
      const m = Math.floor(seconds / 60)
      const s = (seconds % 60).toFixed(0)
      return `${m}m ${s}s`
    }
  }
}
</script>

<style scoped>
/* 页面容器 */
.cron-page {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-5);
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--ios-space-4);
}

.header-title h2 {
  font-size: var(--ios-text-title2);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  margin: 0 0 var(--ios-space-1) 0;
  letter-spacing: var(--ios-tracking-tight);
}

.page-subtitle {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
}

.page-actions {
  display: flex;
  gap: var(--ios-space-2);
  flex-wrap: wrap;
}

/* 玻璃卡片 */
.glass-card {
  background: var(--ios-glass-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-md), inset 0 1px 0 0 var(--ios-glass-highlight);
  padding: var(--ios-space-5);
  transition: var(--ios-theme-transition);
}

/* 状态卡片网格 */
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--ios-space-4);
}

.status-card {
  display: flex;
  align-items: center;
  gap: var(--ios-space-4);
  padding: var(--ios-space-4) var(--ios-space-5);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--ios-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-total { background: rgba(0, 122, 255, 0.15); color: var(--ios-blue); }
.icon-enabled { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.icon-history { background: rgba(255, 149, 0, 0.15); color: var(--ios-orange); }
.icon-success { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.icon-failed { background: rgba(255, 59, 48, 0.15); color: var(--ios-red); }

.card-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.card-label {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

.text-success { color: var(--ios-green); }
.text-danger { color: var(--ios-red); }
.text-muted { color: var(--ios-label-tertiary); }

/* 段落标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0 0 var(--ios-space-4) 0;
}

.section-icon { color: var(--ios-blue); }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ios-space-4);
}

.section-header .section-title { margin: 0; }

/* 筛选 */
.rules-filter {
  display: flex;
  gap: var(--ios-space-3);
  margin-bottom: var(--ios-space-4);
  flex-wrap: wrap;
}

.filter-input,
.filter-select {
  padding: 8px 12px;
  border-radius: var(--ios-radius-md);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-subhead);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.filter-input {
  flex: 1;
  min-width: 200px;
}

.filter-input:focus,
.filter-select:focus {
  border-color: var(--ios-blue);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

/* 表格 */
.table-container {
  overflow-x: auto;
  border-radius: var(--ios-radius-lg);
  background: var(--ios-fill-quaternary);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: var(--ios-space-3) var(--ios-space-4);
  text-align: left;
  border-bottom: 0.5px solid var(--ios-separator);
}

.data-table th {
  background: var(--ios-fill-tertiary);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  font-size: var(--ios-text-caption1);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.data-table td {
  color: var(--ios-label-primary);
  font-size: var(--ios-text-footnote);
}

.data-table tr:hover td {
  background: var(--ios-fill-quaternary);
}

.loading,
.no-data {
  text-align: center !important;
  color: var(--ios-label-secondary) !important;
  padding: var(--ios-space-6) !important;
}

/* 任务名称与描述 */
.task-name {
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
}

.task-desc {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-tertiary);
  margin-top: 2px;
}

/* Cron 表达式代码 */
.cron-code {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-size: var(--ios-text-footnote);
  background: var(--ios-fill-tertiary);
  padding: 2px 8px;
  border-radius: var(--ios-radius-sm);
  color: var(--ios-blue);
}

.time-cell {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  white-space: nowrap;
}

/* 徽章 */
.action-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--ios-radius-full);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  text-transform: uppercase;
  margin-right: 4px;
}

.badge-enabled {
  background: rgba(52, 199, 89, 0.2);
  color: var(--ios-green);
}

.badge-disabled {
  background: rgba(142, 142, 147, 0.2);
  color: var(--ios-label-secondary);
}

.badge-success {
  background: rgba(52, 199, 89, 0.2);
  color: var(--ios-green);
}

.badge-failed {
  background: rgba(255, 59, 48, 0.2);
  color: var(--ios-red);
}

.status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
}

.direction-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
}

.exit-code {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-size: var(--ios-text-footnote);
  padding: 2px 6px;
  border-radius: var(--ios-radius-sm);
}

.code-success { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.code-failed { background: rgba(255, 59, 48, 0.15); color: var(--ios-red); }

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-3);
  margin-top: var(--ios-space-4);
}

.page-info {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  padding: 0 var(--ios-space-2);
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-3) var(--ios-space-5);
  border-radius: var(--ios-radius-lg);
  border: none;
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: 6px 12px;
  font-size: var(--ios-text-footnote);
}

.btn-primary {
  background: var(--ios-blue);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0066d6;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.btn-secondary {
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--ios-fill-secondary);
}

.btn-danger {
  background: var(--ios-red);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c8232c;
  box-shadow: 0 2px 8px rgba(255, 59, 48, 0.3);
}

/* 警告框 */
.alert {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-3) var(--ios-space-4);
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-footnote);
}

.alert-error {
  background: rgba(255, 59, 48, 0.1);
  color: var(--ios-red);
  border: 0.5px solid rgba(255, 59, 48, 0.2);
}

.alert-info {
  background: rgba(0, 122, 255, 0.1);
  color: var(--ios-blue);
  border: 0.5px solid rgba(0, 122, 255, 0.2);
}

.alert-icon { flex-shrink: 0; }

/* 模态框 */
.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--ios-space-4);
}

.modal-content {
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 900px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ios-space-5);
}

.modal-header h3 {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--ios-radius-full);
  border: none;
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: all var(--ios-transition-fast);
}

.close-btn:hover {
  background: var(--ios-fill-secondary);
  color: var(--ios-label-primary);
}

/* 表单 */
.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-2);
  margin-bottom: var(--ios-space-4);
}

.form-group label {
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 10px 12px;
  border-radius: var(--ios-radius-md);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-body);
  outline: none;
  transition: all var(--ios-transition-fast);
  font-family: inherit;
  resize: vertical;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--ios-blue);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ios-space-3);
}

.form-hint {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-tertiary);
}

.hint-success { color: var(--ios-green); }
.hint-error { color: var(--ios-red); }

.form-actions {
  display: flex;
  gap: var(--ios-space-3);
  justify-content: flex-end;
  margin-top: var(--ios-space-5);
}

/* 复选框 */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  cursor: pointer;
  font-size: var(--ios-text-body);
  color: var(--ios-label-primary);
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--ios-blue);
}

/* Cron 预设 */
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ios-space-2);
}

.preset-btn {
  padding: 5px 12px;
  border-radius: var(--ios-radius-full);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
  font-size: var(--ios-text-caption1);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
}

.preset-btn:hover {
  background: var(--ios-blue);
  color: white;
  border-color: var(--ios-blue);
}

/* 历史操作栏 */
.history-actions {
  display: flex;
  gap: var(--ios-space-2);
  margin-bottom: var(--ios-space-4);
}

/* 输出详情 */
.output-detail {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-4);
}

.output-meta {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-2);
  padding: var(--ios-space-3) var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-md);
  font-size: var(--ios-text-footnote);
  color: var(--ios-label-secondary);
}

.output-meta code {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  background: var(--ios-fill-tertiary);
  padding: 2px 6px;
  border-radius: var(--ios-radius-sm);
  color: var(--ios-blue);
}

.output-section h4 {
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  margin: 0 0 var(--ios-space-2) 0;
}

.output-block {
  background: var(--ios-fill-quaternary);
  border: 0.5px solid var(--ios-separator);
  border-radius: var(--ios-radius-md);
  padding: var(--ios-space-3);
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-size: var(--ios-text-footnote);
  color: var(--ios-label-primary);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
  margin: 0;
}

.output-block.has-error {
  border-color: rgba(255, 59, 48, 0.3);
  color: var(--ios-red);
}

/* 加载旋转动画 */
.icon-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .status-cards {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .data-table {
    font-size: var(--ios-text-caption1);
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
