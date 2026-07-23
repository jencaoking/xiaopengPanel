<template>
  <!-- AI 浮动按钮 -->
  <button
    v-if="!isOpen"
    class="ai-fab"
    @click="openPanel"
    :title="$t('common.aiAssistant') || 'AI 助手'"
    aria-label="AI 助手"
  >
    <svg viewBox="0 0 24 24" class="ai-fab-icon">
      <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
    </svg>
    <span class="ai-fab-badge" v-if="activeAlertCount > 0">{{ activeAlertCount }}</span>
  </button>

  <!-- AI 抽屉面板 -->
  <transition name="ai-slide">
    <div v-if="isOpen" class="ai-drawer" role="dialog" aria-label="AI 助手">
      <!-- 头部 -->
      <div class="ai-drawer-header">
        <div class="ai-header-title">
          <svg viewBox="0 0 24 24" class="ai-header-icon">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
          <h2>AI 助手</h2>
          <span class="ai-status-dot" :class="{ 'active': aiAvailable, 'inactive': !aiAvailable }"></span>
        </div>
        <button class="ai-close-btn" @click="closePanel" aria-label="关闭">
          <svg viewBox="0 0 24 24"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>

      <!-- Tab 导航 -->
      <div class="ai-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="ai-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="ai-tab-icon" v-html="tab.icon"></span>
          <span class="ai-tab-label">{{ tab.label }}</span>
          <span class="ai-tab-badge" v-if="tab.badge">{{ tab.badge }}</span>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="ai-drawer-body">
        <!-- 对话 Tab -->
        <div v-if="activeTab === 'chat'" class="ai-chat-panel">
          <div class="ai-messages" ref="messagesContainer">
            <div v-if="messages.length === 0" class="ai-empty-state">
              <p class="ai-empty-title">开始与 AI 对话</p>
              <p class="ai-empty-desc">AI 可以查询系统状态、诊断故障、执行修复</p>
              <div class="ai-suggestions">
                <button v-for="s in suggestions" :key="s" class="ai-suggestion-chip" @click="sendMessage(s)">
                  {{ s }}
                </button>
              </div>
            </div>
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="ai-message"
              :class="msg.role"
            >
              <div class="ai-message-avatar" v-if="msg.role === 'assistant'">AI</div>
              <div class="ai-message-content">
                <div class="ai-message-text" v-html="renderMarkdown(msg.content)"></div>
                <div v-if="msg.toolCalls && msg.toolCalls.length" class="ai-tool-calls">
                  <div v-for="tc in msg.toolCalls" :key="tc.tool" class="ai-tool-call-item">
                    <span class="ai-tool-level" :class="tc.level">{{ tc.level }}</span>
                    <span class="ai-tool-name">{{ tc.tool }}</span>
                    <span class="ai-tool-status" :class="tc.status">{{ tc.status === 'pending_confirmation' ? '待确认' : tc.status }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="isThinking" class="ai-message assistant">
              <div class="ai-message-avatar">AI</div>
              <div class="ai-message-content">
                <div class="ai-typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- 确认操作栏 -->
          <div v-if="pendingConfirmation" class="ai-confirm-bar">
            <div class="ai-confirm-info">
              <span class="ai-confirm-level" :class="pendingConfirmation.level">{{ pendingConfirmation.level }}</span>
              <span>{{ pendingConfirmation.description }}</span>
            </div>
            <div class="ai-confirm-actions">
              <button class="btn btn-sm btn-danger" @click="cancelConfirmation">拒绝</button>
              <button class="btn btn-sm btn-primary" @click="confirmAction">确认执行</button>
            </div>
          </div>

          <!-- 输入区 -->
          <div class="ai-input-area">
            <textarea
              v-model="inputText"
              class="ai-input"
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              @keydown.enter.exact.prevent="handleEnter"
              rows="1"
              ref="inputRef"
            ></textarea>
            <button class="ai-send-btn" @click="handleSend" :disabled="!inputText.trim() || isThinking">
              <svg viewBox="0 0 24 24"><path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
          </div>
        </div>

        <!-- 诊断 Tab -->
        <div v-if="activeTab === 'diagnose'" class="ai-diagnose-panel">
          <div class="ai-diagnose-header">
            <p class="ai-section-desc">AI 将自动收集系统指标、分析日志、定位根因，生成诊断报告</p>
            <button class="btn btn-primary" @click="runDiagnosis" :disabled="isDiagnosing">
              {{ isDiagnosing ? '诊断中...' : '一键诊断' }}
            </button>
          </div>

          <div v-if="diagnosticResult" class="ai-diagnose-result">
            <div class="ai-diagnose-summary">
              <div class="ai-stat-item" :class="{ critical: diagnosticResult.critical_count > 0 }">
                <span class="ai-stat-value">{{ diagnosticResult.critical_count || 0 }}</span>
                <span class="ai-stat-label">严重</span>
              </div>
              <div class="ai-stat-item warning">
                <span class="ai-stat-value">{{ diagnosticResult.warning_count || 0 }}</span>
                <span class="ai-stat-label">警告</span>
              </div>
              <div class="ai-stat-item">
                <span class="ai-stat-value">{{ diagnosticResult.issue_count || 0 }}</span>
                <span class="ai-stat-label">总计</span>
              </div>
            </div>

            <div v-if="diagnosticResult.issues && diagnosticResult.issues.length" class="ai-issues-list">
              <div v-for="(issue, idx) in diagnosticResult.issues" :key="idx" class="ai-issue-item" :class="issue.severity">
                <span class="ai-issue-severity">{{ issue.severity === 'critical' ? '严重' : '警告' }}</span>
                <span class="ai-issue-message">{{ issue.message }}</span>
                <button v-if="issue.severity === 'critical'" class="ai-issue-fix-btn" @click="proposeFix(issue.message)">
                  修复
                </button>
              </div>
            </div>

            <div class="ai-report" v-html="renderMarkdown(diagnosticResult.report)"></div>
          </div>

          <div v-if="isDiagnosing" class="ai-loading">
            <div class="ai-spinner"></div>
            <p>正在收集系统数据并分析...</p>
          </div>

          <!-- 诊断历史 -->
          <div v-if="diagnosticHistory.length" class="ai-history-section">
            <h4>诊断历史</h4>
            <div v-for="(h, idx) in diagnosticHistory" :key="idx" class="ai-history-item" @click="diagnosticResult = h">
              <span class="ai-history-time">{{ formatTime(h.timestamp) }}</span>
              <span class="ai-history-issues">{{ h.issue_count }} 个问题</span>
            </div>
          </div>
        </div>

        <!-- 告警 Tab -->
        <div v-if="activeTab === 'alerts'" class="ai-alerts-panel">
          <div class="ai-alerts-header">
            <p class="ai-section-desc">AI 智能告警分析与分级</p>
            <button class="btn btn-secondary btn-sm" @click="loadSmartAlerts" :disabled="isLoadingAlerts">
              {{ isLoadingAlerts ? '刷新中...' : '刷新' }}
            </button>
          </div>

          <div v-if="smartAlerts" class="ai-alerts-summary">
            <div class="ai-stat-item critical">
              <span class="ai-stat-value">{{ smartAlerts.ai_summary?.critical || 0 }}</span>
              <span class="ai-stat-label">严重</span>
            </div>
            <div class="ai-stat-item warning">
              <span class="ai-stat-value">{{ smartAlerts.ai_summary?.warning || 0 }}</span>
              <span class="ai-stat-label">警告</span>
            </div>
            <div class="ai-stat-item">
              <span class="ai-stat-value">{{ smartAlerts.ai_summary?.info || 0 }}</span>
              <span class="ai-stat-label">信息</span>
            </div>
          </div>

          <div v-if="smartAlerts?.alerts?.length" class="ai-alerts-list">
            <div v-for="(item, idx) in smartAlerts.alerts" :key="idx" class="ai-alert-item" :class="item.analysis?.severity">
              <div class="ai-alert-header">
                <span class="ai-alert-severity" :class="item.analysis?.severity">
                  {{ severityLabel(item.analysis?.severity) }}
                </span>
                <span class="ai-alert-metric">{{ item.alert?.metric_name }}</span>
                <span class="ai-alert-time">{{ formatTime(item.alert?.timestamp) }}</span>
              </div>
              <div class="ai-alert-message">{{ item.alert?.message }}</div>
              <div class="ai-alert-analysis" v-if="item.analysis?.analysis">
                <strong>分析:</strong> {{ item.analysis.analysis }}
              </div>
              <div class="ai-alert-suggestion" v-if="item.analysis?.suggestion">
                <strong>建议:</strong> {{ item.analysis.suggestion }}
              </div>
              <div class="ai-alert-confidence" v-if="item.analysis?.confidence !== undefined">
                置信度: {{ Math.round(item.analysis.confidence * 100) }}%
              </div>
            </div>
          </div>
          <div v-else-if="!isLoadingAlerts" class="ai-empty-state">
            <p>暂无活跃告警</p>
          </div>
        </div>

        <!-- 设置 Tab -->
        <div v-if="activeTab === 'settings'" class="ai-settings-panel">
          <div class="ai-settings-group">
            <label class="ai-setting-label">启用 AI</label>
            <input type="checkbox" v-model="aiConfig.enabled" @change="saveConfig">
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">供应商</label>
            <select v-model="aiConfig.provider" @change="onProviderChange">
              <option value="deepseek">DeepSeek</option>
              <option value="openai">OpenAI</option>
              <option value="qwen">通义千问</option>
              <option value="moonshot">Moonshot</option>
              <option value="custom">自定义</option>
            </select>
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">API Key</label>
            <input
              type="password"
              v-model="aiConfig.api_key"
              :placeholder="aiConfig.api_key_configured ? '已配置（输入新值替换）' : '输入 API Key'"
              @blur="saveConfig"
            >
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">模型</label>
            <input type="text" v-model="aiConfig.model" @blur="saveConfig" placeholder="模型名称">
          </div>

          <div class="ai-settings-group" v-if="aiConfig.provider === 'custom'">
            <label class="ai-setting-label">Base URL</label>
            <input type="text" v-model="aiConfig.base_url" @blur="saveConfig" placeholder="https://api.example.com/v1">
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">温度 ({{ aiConfig.temperature }})</label>
            <input type="range" min="0" max="1" step="0.1" v-model.number="aiConfig.temperature" @change="saveConfig">
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">最大 Token 数</label>
            <input type="number" v-model.number="aiConfig.max_tokens" @blur="saveConfig" min="256" max="32768">
          </div>

          <div class="ai-settings-group">
            <label class="ai-setting-label">自动修复</label>
            <input type="checkbox" v-model="aiConfig.auto_repair_enabled" @change="saveConfig">
            <span class="ai-setting-hint">启用后 AI 可自动执行修复操作（仍需确认）</span>
          </div>

          <button class="btn btn-primary ai-save-btn" @click="saveConfig">保存配置</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useStore } from 'vuex'

export default {
  name: 'AIAssistant',
  setup() {
    const store = useStore()
    const isOpen = ref(false)
    const activeTab = ref('chat')
    const inputText = ref('')
    const isThinking = ref(false)
    const isDiagnosing = ref(false)
    const isLoadingAlerts = ref(false)
    const messagesContainer = ref(null)
    const inputRef = ref(null)
    const pendingConfirmation = ref(null)

    // 对话状态
    const messages = ref([])
    const sessionId = ref('')

    // 诊断状态
    const diagnosticResult = ref(null)
    const diagnosticHistory = ref([])

    // 告警状态
    const smartAlerts = ref(null)
    const activeAlertCount = ref(0)

    // AI 配置
    const aiConfig = reactive({
      enabled: false,
      provider: 'deepseek',
      api_key: '',
      api_key_configured: false,
      model: 'deepseek-chat',
      base_url: '',
      temperature: 0.3,
      max_tokens: 4096,
      auto_repair_enabled: false,
    })

    const aiAvailable = ref(false)

    const tabs = computed(() => [
      { id: 'chat', label: '对话', icon: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>' },
      { id: 'diagnose', label: '诊断', icon: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-4 14H9v-2h6v2zm0-4H9v-2h6v2zm0-4H9V7h6v2z"/></svg>' },
      { id: 'alerts', label: '告警', icon: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5S10.5 3.17 10.5 4v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>', badge: activeAlertCount.value || undefined },
      { id: 'settings', label: '设置', icon: '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L5.04 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>' },
    ])

    const suggestions = [
      '当前系统状态如何？',
      '检查是否有异常进程',
      '哪些服务状态异常？',
      '分析最近的告警',
    ]

    // API 请求辅助
    async function apiCall(url, method = 'GET', body = null) {
      const headers = { 'Content-Type': 'application/json' }
      if (store.state.token) {
        headers['Authorization'] = `Bearer ${store.state.token}`
      }
      const options = { method, headers }
      if (body && method !== 'GET') {
        options.body = JSON.stringify(body)
      }
      const resp = await fetch(url, options)
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }
      return resp.json()
    }

    // 流式 SSE 请求
    async function streamChat(message) {
      const headers = { 'Content-Type': 'application/json' }
      if (store.state.token) {
        headers['Authorization'] = `Bearer ${store.state.token}`
      }

      const resp = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: sessionId.value,
          message,
        }),
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const assistantMsg = reactive({ role: 'assistant', content: '', toolCalls: [] })
      messages.value.push(assistantMsg)

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const dataStr = line.slice(6).trim()
            if (!dataStr) continue

            try {
              const event = JSON.parse(dataStr)
              if (event.type === 'content') {
                assistantMsg.content += event.content
                scrollToBottom()
              } else if (event.type === 'tool_start') {
                assistantMsg.toolCalls.push({
                  tool: event.tool,
                  level: event.level,
                  params: event.params,
                  status: 'running',
                })
              } else if (event.type === 'tool_result') {
                const tc = assistantMsg.toolCalls.find(t => t.tool === event.tool && t.status === 'running')
                if (tc) tc.status = event.result.status || 'done'
              } else if (event.type === 'confirmation') {
                pendingConfirmation.value = event
                assistantMsg.toolCalls.find(t => t.tool === event.tool && t.status === 'running').status = 'pending_confirmation'
              } else if (event.type === 'session_update') {
                sessionId.value = event.session_id
              } else if (event.type === 'done') {
                if (event.messages) {
                  sessionId.value = sessionId.value || ''
                }
              } else if (event.type === 'error') {
                assistantMsg.content += `\n\n⚠️ 错误: ${event.content}`
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    }

    function openPanel() {
      isOpen.value = true
      checkAIHealth()
      if (activeTab.value === 'alerts' && !smartAlerts.value) {
        loadSmartAlerts()
      }
      nextTick(() => {
        inputRef.value?.focus()
      })
    }

    function closePanel() {
      isOpen.value = false
    }

    async function checkAIHealth() {
      try {
        const result = await apiCall('/api/ai/health')
        aiAvailable.value = result.available
      } catch {
        aiAvailable.value = false
      }
    }

    async function loadAIConfig() {
      try {
        const result = await apiCall('/api/ai/config')
        if (result.config) {
          Object.assign(aiConfig, result.config)
        }
      } catch {
        // 忽略
      }
    }

    async function saveConfig() {
      try {
        await apiCall('/api/ai/config', 'PUT', { ...aiConfig })
        checkAIHealth()
      } catch (e) {
        console.error('保存 AI 配置失败:', e)
      }
    }

    function onProviderChange() {
      const defaults = {
        deepseek: { model: 'deepseek-chat', base_url: '' },
        openai: { model: 'gpt-4o-mini', base_url: '' },
        qwen: { model: 'qwen-plus', base_url: '' },
        moonshot: { model: 'moonshot-v1-8k', base_url: '' },
      }
      const d = defaults[aiConfig.provider]
      if (d) {
        aiConfig.model = d.model
        aiConfig.base_url = d.base_url
      }
    }

    function handleEnter() {
      if (!isThinking.value && inputText.value.trim()) {
        handleSend()
      }
    }

    async function handleSend() {
      const msg = inputText.value.trim()
      if (!msg || isThinking.value) return

      inputText.value = ''
      messages.value.push({ role: 'user', content: msg })
      isThinking.value = true

      try {
        await streamChat(msg)
      } catch (e) {
        messages.value.push({ role: 'assistant', content: `⚠️ 请求失败: ${e.message}` })
      } finally {
        isThinking.value = false
        scrollToBottom()
      }
    }

    async function sendMessage(text) {
      inputText.value = text
      await handleSend()
    }

    async function confirmAction() {
      if (!pendingConfirmation.value) return
      try {
        const result = await apiCall('/api/ai/confirm', 'POST', {
          confirmation_token: pendingConfirmation.value.confirmation_token,
          action: 'confirm',
        })
        if (result.reply) {
          messages.value.push({ role: 'assistant', content: result.reply })
        }
      } catch (e) {
        messages.value.push({ role: 'assistant', content: `⚠️ 执行失败: ${e.message}` })
      } finally {
        pendingConfirmation.value = null
      }
    }

    async function cancelConfirmation() {
      if (!pendingConfirmation.value) return
      try {
        await apiCall('/api/ai/confirm', 'POST', {
          confirmation_token: pendingConfirmation.value.confirmation_token,
          action: 'cancel',
        })
      } catch {
        // 忽略
      }
      pendingConfirmation.value = null
    }

    async function runDiagnosis() {
      isDiagnosing.value = true
      diagnosticResult.value = null
      try {
        const result = await apiCall('/api/ai/diagnose', 'POST', { target: 'system' })
        diagnosticResult.value = result
        // 加载历史
        loadDiagnosticHistory()
      } catch (e) {
        diagnosticResult.value = {
          status: 'error',
          report: `## 诊断失败\n\n${e.message}`,
          issues: [],
          issue_count: 0,
          critical_count: 0,
          warning_count: 0,
        }
      } finally {
        isDiagnosing.value = false
      }
    }

    async function loadDiagnosticHistory() {
      try {
        const result = await apiCall('/api/ai/diagnostics/history?limit=5')
        diagnosticHistory.value = result.history || []
      } catch {
        // 忽略
      }
    }

    async function proposeFix(issue) {
      activeTab.value = 'chat'
      isThinking.value = true
      messages.value.push({ role: 'user', content: `请修复以下问题: ${issue}` })
      try {
        const result = await apiCall('/api/ai/repair/propose', 'POST', { issue })
        if (result.ai_plan) {
          messages.value.push({ role: 'assistant', content: result.ai_plan })
        }
      } catch (e) {
        messages.value.push({ role: 'assistant', content: `⚠️ 生成修复方案失败: ${e.message}` })
      } finally {
        isThinking.value = false
      }
    }

    async function loadSmartAlerts() {
      isLoadingAlerts.value = true
      try {
        const result = await apiCall('/api/ai/alerts/smart')
        smartAlerts.value = result
        activeAlertCount.value = result.active_count || 0
      } catch (e) {
        console.error('加载智能告警失败:', e)
      } finally {
        isLoadingAlerts.value = false
      }
    }

    function scrollToBottom() {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }

    function severityLabel(sev) {
      const labels = { critical: '严重', warning: '警告', info: '信息' }
      return labels[sev] || sev
    }

    function formatTime(ts) {
      if (!ts) return ''
      const d = new Date(ts * 1000)
      return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
    }

    function renderMarkdown(text) {
      if (!text) return ''
      // 简单 Markdown 渲染
      let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
      // 代码块
      html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      // 标题
      html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
      html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
      html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')
      // 粗体
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // 行内代码
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
      // 列表
      html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
      html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
      // 段落
      html = html.replace(/\n\n/g, '</p><p>')
      html = `<p>${html}</p>`
      return html
    }

    // 定时检查告警
    let alertTimer = null
    onMounted(() => {
      loadAIConfig()
      checkAIHealth()
      // 每 60 秒检查告警数
      alertTimer = setInterval(async () => {
        try {
          const result = await apiCall('/api/ai/alerts/smart')
          activeAlertCount.value = result.active_count || 0
        } catch {
          // 忽略
        }
      }, 60000)
    })

    // 清理定时器
    const originalUnmounted = onMounted
    // 使用 onUnmounted
    import('vue').then(({ onUnmounted }) => {
      onUnmounted(() => {
        if (alertTimer) clearInterval(alertTimer)
      })
    })

    return {
      isOpen,
      activeTab,
      tabs,
      inputText,
      isThinking,
      isDiagnosing,
      isLoadingAlerts,
      messages,
      messagesContainer,
      inputRef,
      pendingConfirmation,
      diagnosticResult,
      diagnosticHistory,
      smartAlerts,
      activeAlertCount,
      aiConfig,
      aiAvailable,
      suggestions,
      openPanel,
      closePanel,
      handleSend,
      handleEnter,
      sendMessage,
      confirmAction,
      cancelConfirmation,
      runDiagnosis,
      loadSmartAlerts,
      proposeFix,
      saveConfig,
      onProviderChange,
      severityLabel,
      formatTime,
      renderMarkdown,
    }
  }
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  border-radius: var(--ios-radius-full);
  background: linear-gradient(135deg, var(--ios-blue), var(--ios-indigo));
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.35);
  z-index: var(--ios-z-fixed);
  transition: transform 0.3s, box-shadow 0.3s;
}
.ai-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 12px 32px rgba(0, 122, 255, 0.45);
}
.ai-fab-icon {
  width: 28px;
  height: 28px;
}
.ai-fab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--ios-red);
  color: white;
  font-size: 11px;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  border: 2px solid var(--bg-primary);
}

.ai-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 480px;
  max-width: 100vw;
  height: 100vh;
  background: var(--bg-secondary);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: var(--ios-z-modal);
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.3);
}

.ai-slide-enter-active,
.ai-slide-leave-active {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.ai-slide-enter-from,
.ai-slide-leave-to {
  transform: translateX(100%);
}

.ai-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}
.ai-header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-header-icon {
  width: 24px;
  height: 24px;
  color: var(--ios-blue);
}
.ai-header-title h2 {
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  margin: 0;
  color: var(--text-primary);
}
.ai-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.ai-status-dot.active {
  background: var(--ios-green);
  box-shadow: 0 0 8px var(--ios-green);
}
.ai-status-dot.inactive {
  background: var(--ios-red);
}
.ai-close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--ios-radius-sm);
  display: flex;
}
.ai-close-btn:hover {
  background: var(--ios-fill-secondary);
}
.ai-close-btn svg {
  width: 20px;
  height: 20px;
}

.ai-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}
.ai-tab {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: var(--ios-text-caption1);
  position: relative;
  transition: color 0.2s;
}
.ai-tab:hover {
  color: var(--text-primary);
}
.ai-tab.active {
  color: var(--ios-blue);
}
.ai-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 25%;
  right: 25%;
  height: 2px;
  background: var(--ios-blue);
  border-radius: 1px;
}
.ai-tab-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-tab-icon :deep(svg) {
  width: 20px;
  height: 20px;
}
.ai-tab-badge {
  position: absolute;
  top: 8px;
  right: calc(50% - 24px);
  background: var(--ios-red);
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

.ai-drawer-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 对话面板 */
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  gap: 8px;
}
.ai-empty-title {
  font-size: var(--ios-text-body);
  font-weight: var(--ios-weight-semibold);
  color: var(--text-primary);
}
.ai-empty-desc {
  font-size: var(--ios-text-footnote);
  color: var(--text-secondary);
}
.ai-suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
  width: 100%;
}
.ai-suggestion-chip {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 10px 14px;
  border-radius: var(--ios-radius-md);
  cursor: pointer;
  font-size: var(--ios-text-footnote);
  text-align: left;
  transition: all 0.2s;
}
.ai-suggestion-chip:hover {
  background: var(--ios-fill-secondary);
  border-color: var(--ios-blue);
}

.ai-message {
  display: flex;
  gap: 10px;
  max-width: 90%;
}
.ai-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.ai-message-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--ios-radius-full);
  background: linear-gradient(135deg, var(--ios-blue), var(--ios-indigo));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.ai-message-content {
  background: var(--bg-tertiary);
  padding: 10px 14px;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-footnote);
  line-height: var(--ios-leading-relaxed);
  color: var(--text-primary);
}
.ai-message.user .ai-message-content {
  background: var(--ios-blue);
  color: white;
}
.ai-message-text :deep(h3) { font-size: 15px; margin: 8px 0 4px; font-weight: 600; }
.ai-message-text :deep(h4) { font-size: 14px; margin: 6px 0 3px; font-weight: 600; }
.ai-message-text :deep(p) { margin: 4px 0; }
.ai-message-text :deep(pre) {
  background: rgba(0,0,0,0.3);
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}
.ai-message-text :deep(code) {
  background: rgba(0,0,0,0.2);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}
.ai-message-text :deep(ul) { padding-left: 16px; margin: 4px 0; }
.ai-message-text :deep(li) { margin: 2px 0; }

.ai-tool-calls {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-tool-call-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 4px 8px;
  background: rgba(0,0,0,0.2);
  border-radius: 4px;
}
.ai-tool-level {
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 700;
  font-size: 10px;
}
.ai-tool-level.L1 { background: var(--ios-green); color: white; }
.ai-tool-level.L2 { background: var(--ios-blue); color: white; }
.ai-tool-level.L3 { background: var(--ios-orange); color: white; }
.ai-tool-level.L4 { background: var(--ios-red); color: white; }
.ai-tool-status.pending_confirmation { color: var(--ios-orange); font-weight: 600; }

.ai-typing {
  display: flex;
  gap: 4px;
  padding: 8px;
}
.ai-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-secondary);
  animation: ai-typing 1.4s infinite;
}
.ai-typing span:nth-child(2) { animation-delay: 0.2s; }
.ai-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes ai-typing {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

.ai-confirm-bar {
  padding: 12px 16px;
  background: var(--ios-orange);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.ai-confirm-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--ios-text-footnote);
  flex: 1;
}
.ai-confirm-level {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.25);
  font-weight: 700;
  font-size: 10px;
}
.ai-confirm-actions {
  display: flex;
  gap: 8px;
}
.ai-confirm-actions button {
  border: none;
  padding: 6px 12px;
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  cursor: pointer;
}
.ai-confirm-actions .btn-primary {
  background: white;
  color: var(--ios-orange);
}
.ai-confirm-actions .btn-danger {
  background: rgba(255,255,255,0.2);
  color: white;
}

.ai-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}
.ai-input {
  flex: 1;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--ios-radius-md);
  padding: 10px 12px;
  color: var(--text-primary);
  font-size: var(--ios-text-footnote);
  font-family: var(--ios-font-family);
  resize: none;
  outline: none;
  min-height: 40px;
  max-height: 120px;
}
.ai-input:focus {
  border-color: var(--ios-blue);
}
.ai-send-btn {
  width: 40px;
  height: 40px;
  border-radius: var(--ios-radius-md);
  background: var(--ios-blue);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.ai-send-btn svg {
  width: 20px;
  height: 20px;
}

/* 诊断面板 */
.ai-diagnose-panel,
.ai-alerts-panel,
.ai-settings-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.ai-diagnose-header,
.ai-alerts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.ai-section-desc {
  font-size: var(--ios-text-footnote);
  color: var(--text-secondary);
  flex: 1;
  margin: 0;
}
.ai-diagnose-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ai-diagnose-summary,
.ai-alerts-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.ai-stat-item {
  flex: 1;
  background: var(--bg-tertiary);
  border-radius: var(--ios-radius-md);
  padding: 12px;
  text-align: center;
  border: 1px solid var(--border-color);
}
.ai-stat-item.critical {
  border-color: var(--ios-red);
}
.ai-stat-item.warning {
  border-color: var(--ios-orange);
}
.ai-stat-value {
  display: block;
  font-size: var(--ios-text-title1);
  font-weight: var(--ios-weight-bold);
  color: var(--text-primary);
}
.ai-stat-item.critical .ai-stat-value {
  color: var(--ios-red);
}
.ai-stat-item.warning .ai-stat-value {
  color: var(--ios-orange);
}
.ai-stat-label {
  font-size: var(--ios-text-caption1);
  color: var(--text-secondary);
}
.ai-issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-issue-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-footnote);
}
.ai-issue-item.critical {
  border-left: 3px solid var(--ios-red);
}
.ai-issue-item.warning {
  border-left: 3px solid var(--ios-orange);
}
.ai-issue-severity {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.ai-issue-item.critical .ai-issue-severity {
  background: var(--ios-red);
  color: white;
}
.ai-issue-item.warning .ai-issue-severity {
  background: var(--ios-orange);
  color: white;
}
.ai-issue-message {
  flex: 1;
  color: var(--text-primary);
}
.ai-issue-fix-btn {
  background: var(--ios-blue);
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: var(--ios-radius-sm);
  font-size: 11px;
  cursor: pointer;
}
.ai-report {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: var(--ios-radius-md);
  font-size: var(--ios-text-footnote);
  line-height: var(--ios-leading-relaxed);
  color: var(--text-primary);
}
.ai-report :deep(h3) { font-size: 15px; margin: 8px 0 4px; }
.ai-report :deep(h4) { font-size: 14px; margin: 6px 0 3px; }
.ai-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
}
.ai-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--ios-fill-tertiary);
  border-top-color: var(--ios-blue);
  border-radius: 50%;
  animation: ai-spin 0.8s linear infinite;
}
@keyframes ai-spin {
  to { transform: rotate(360deg); }
}
.ai-history-section {
  margin-top: 24px;
}
.ai-history-section h4 {
  font-size: var(--ios-text-footnote);
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.ai-history-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-caption1);
  cursor: pointer;
  margin-bottom: 4px;
}
.ai-history-item:hover {
  background: var(--ios-fill-secondary);
}

/* 告警面板 */
.ai-alerts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-alert-item {
  background: var(--bg-tertiary);
  border-radius: var(--ios-radius-md);
  padding: 12px;
  border-left: 3px solid var(--ios-fill-primary);
}
.ai-alert-item.critical { border-left-color: var(--ios-red); }
.ai-alert-item.warning { border-left-color: var(--ios-orange); }
.ai-alert-item.info { border-left-color: var(--ios-blue); }
.ai-alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.ai-alert-severity {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
}
.ai-alert-severity.critical { background: var(--ios-red); color: white; }
.ai-alert-severity.warning { background: var(--ios-orange); color: white; }
.ai-alert-severity.info { background: var(--ios-blue); color: white; }
.ai-alert-metric {
  font-weight: 600;
  font-size: var(--ios-text-footnote);
  color: var(--text-primary);
}
.ai-alert-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-secondary);
}
.ai-alert-message {
  font-size: var(--ios-text-footnote);
  color: var(--text-primary);
  margin-bottom: 4px;
}
.ai-alert-analysis,
.ai-alert-suggestion {
  font-size: var(--ios-text-caption1);
  color: var(--text-secondary);
  margin-top: 4px;
}
.ai-alert-confidence {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 设置面板 */
.ai-settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ai-settings-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-setting-label {
  font-size: var(--ios-text-footnote);
  font-weight: var(--ios-weight-medium);
  color: var(--text-primary);
}
.ai-settings-group input[type="text"],
.ai-settings-group input[type="password"],
.ai-settings-group input[type="number"],
.ai-settings-group select {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--ios-radius-sm);
  padding: 8px 10px;
  color: var(--text-primary);
  font-size: var(--ios-text-footnote);
  outline: none;
}
.ai-settings-group input[type="range"] {
  width: 100%;
}
.ai-setting-hint {
  font-size: 11px;
  color: var(--text-secondary);
}
.ai-save-btn {
  margin-top: 8px;
}

/* 响应式 */
@media (max-width: 600px) {
  .ai-drawer {
    width: 100vw;
  }
}
</style>
