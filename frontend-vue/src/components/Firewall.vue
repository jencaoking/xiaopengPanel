<template>
  <div id="firewall" class="page firewall-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-title">
        <h2>{{ $t('firewall.title') }}</h2>
        <p class="page-subtitle">{{ $t('firewall.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="fetchStatus" :disabled="loading">
          <svg v-if="loading" class="icon-spin" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
          </svg>
          <span v-else>{{ $t('common.refresh') }}</span>
        </button>
        <button
          v-if="status.backend"
          class="btn btn-secondary"
          @click="reloadFirewall"
          :disabled="!supportsReload"
          :title="!supportsReload ? $t('firewall.reloadNotSupported') : ''"
        >
          {{ $t('firewall.reload') }}
        </button>
        <button
          class="btn"
          :class="status.enabled ? 'btn-danger' : 'btn-success'"
          @click="toggleFirewall"
          :disabled="!status.backend || actionLoading"
        >
          {{ status.enabled ? $t('firewall.disable') : $t('firewall.enable') }}
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
    <div class="status-cards" v-if="status.backend">
      <div class="status-card glass-card">
        <div class="card-icon" :class="status.enabled ? 'icon-active' : 'icon-inactive'">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path v-if="status.enabled" fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
            <path v-else fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 17l-4-4 1.41-1.41L11 15.17l5.59-5.59L18 11l-7 7z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('firewall.status') }}</span>
          <span class="card-value" :class="status.enabled ? 'text-success' : 'text-danger'">
            {{ status.enabled ? $t('firewall.active') : $t('firewall.inactive') }}
          </span>
        </div>
      </div>

      <div class="status-card glass-card">
        <div class="card-icon icon-backend">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('firewall.backend') }}</span>
          <span class="card-value">{{ status.backend }}</span>
        </div>
      </div>

      <div class="status-card glass-card">
        <div class="card-icon icon-rules">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('firewall.ruleCount') }}</span>
          <span class="card-value">{{ filteredRules.length }}</span>
        </div>
      </div>

      <div class="status-card glass-card" v-if="status.platform">
        <div class="card-icon icon-platform">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('firewall.platform') }}</span>
          <span class="card-value">{{ status.platform }}</span>
        </div>
      </div>
    </div>

    <!-- 默认策略（仅 ufw 显示） -->
    <div class="policy-section glass-card" v-if="status.default_policy && status.backend === 'ufw'">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" width="18" height="18" class="section-icon">
          <path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
        </svg>
        {{ $t('firewall.defaultPolicy') }}
      </h3>
      <div class="policy-grid">
        <div class="policy-item" v-for="(value, key) in status.default_policy" :key="key">
          <span class="policy-label">{{ $t(`firewall.${key}`) }}</span>
          <div class="policy-control">
            <span class="policy-badge" :class="`policy-${value}`">{{ value }}</span>
            <select
              class="policy-select"
              :value="value"
              @change="updatePolicy(key, $event.target.value)"
              :disabled="actionLoading"
            >
              <option value="allow">{{ $t('firewall.allow') }}</option>
              <option value="deny">{{ $t('firewall.deny') }}</option>
              <option value="reject">{{ $t('firewall.reject') }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions glass-card">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" width="18" height="18" class="section-icon">
          <path fill="currentColor" d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/>
        </svg>
        {{ $t('firewall.quickActions') }}
      </h3>
      <div class="quick-actions-grid">
        <div class="quick-action-item">
          <span class="quick-label">{{ $t('firewall.port') }}</span>
          <input
            type="text"
            v-model="quickPort"
            :placeholder="$t('firewall.portPlaceholder')"
            class="quick-input"
            @keyup.enter="quickAllow"
          >
        </div>
        <div class="quick-action-item">
          <span class="quick-label">{{ $t('firewall.protocol') }}</span>
          <select v-model="quickProtocol" class="quick-select">
            <option value="tcp">TCP</option>
            <option value="udp">UDP</option>
          </select>
        </div>
        <button class="btn btn-success btn-sm" @click="quickAllow" :disabled="actionLoading || !quickPort">
          {{ $t('firewall.quickAllow') }}
        </button>
        <button class="btn btn-danger btn-sm" @click="quickBlock" :disabled="actionLoading || !quickPort">
          {{ $t('firewall.quickBlock') }}
        </button>
      </div>
    </div>

    <!-- 规则列表 -->
    <div class="rules-section glass-card">
      <div class="section-header">
        <h3 class="section-title">
          <svg viewBox="0 0 24 24" width="18" height="18" class="section-icon">
            <path fill="currentColor" d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/>
          </svg>
          {{ $t('firewall.rules') }}
        </h3>
        <button class="btn btn-primary btn-sm" @click="showAddRuleModal">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          {{ $t('firewall.addRule') }}
        </button>
      </div>

      <!-- 筛选 -->
      <div class="rules-filter">
        <input
          type="text"
          v-model="searchQuery"
          :placeholder="$t('firewall.searchRules')"
          class="filter-input"
        >
        <select v-model="filterAction" class="filter-select">
          <option value="">{{ $t('firewall.allActions') }}</option>
          <option value="ALLOW">{{ $t('firewall.allow') }}</option>
          <option value="DENY">{{ $t('firewall.deny') }}</option>
          <option value="BLOCK">{{ $t('firewall.block') }}</option>
        </select>
        <select v-model="filterDirection" class="filter-select">
          <option value="">{{ $t('firewall.allDirections') }}</option>
          <option value="IN">IN</option>
          <option value="OUT">OUT</option>
        </select>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ $t('firewall.target') }}</th>
              <th>{{ $t('firewall.action') }}</th>
              <th>{{ $t('firewall.direction') }}</th>
              <th>{{ $t('firewall.source') }}</th>
              <th v-if="status.backend === 'netsh'">{{ $t('firewall.ruleName') }}</th>
              <th v-if="status.backend === 'iptables'">{{ $t('firewall.chain') }}</th>
              <th>{{ $t('common.delete') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" class="loading-row">
              <td :colspan="columnCount" class="loading">{{ $t('common.loading') }}</td>
            </tr>
            <tr v-else-if="filteredRules.length === 0">
              <td :colspan="columnCount" class="no-data">{{ $t('firewall.noRules') }}</td>
            </tr>
            <tr
              v-for="(rule, index) in paginatedRules"
              :key="index"
              class="rule-row"
            >
              <td class="rule-target">{{ rule.target || '-' }}</td>
              <td>
                <span class="action-badge" :class="actionClass(rule.action)">
                  {{ rule.action || '-' }}
                </span>
              </td>
              <td>
                <span class="direction-badge">{{ rule.direction || 'IN' }}</span>
              </td>
              <td>{{ rule.from || $t('firewall.anywhere') }}</td>
              <td v-if="status.backend === 'netsh'">{{ rule.name || '-' }}</td>
              <td v-if="status.backend === 'iptables'">{{ rule.chain || '-' }}</td>
              <td>
                <button
                  class="btn btn-danger btn-sm btn-icon"
                  @click="deleteRule(rule, index)"
                  :disabled="actionLoading"
                  :title="$t('common.delete')"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14">
                    <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="filteredRules.length > pageSize">
        <button
          class="btn btn-secondary btn-sm"
          :disabled="currentPage === 1"
          @click="currentPage--"
        >{{ $t('common.prev') }}</button>
        <span class="page-info">
          {{ currentPage }} / {{ totalPages }}
        </span>
        <button
          class="btn btn-secondary btn-sm"
          :disabled="currentPage >= totalPages"
          @click="currentPage++"
        >{{ $t('common.next') }}</button>
      </div>
    </div>

    <!-- 添加规则模态框 -->
    <div v-if="showModal" class="modal" @click.self="showModal = false">
      <div class="modal-content glass-card">
        <div class="modal-header">
          <h3>{{ $t('firewall.addRule') }}</h3>
          <button class="close-btn" @click="showModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="addRule">
            <div class="form-group">
              <label>{{ $t('firewall.port') }} *</label>
              <input
                type="text"
                v-model="ruleForm.port"
                :placeholder="$t('firewall.portPlaceholder')"
                required
              >
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('firewall.protocol') }}</label>
                <select v-model="ruleForm.protocol">
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('firewall.action') }}</label>
                <select v-model="ruleForm.action">
                  <option value="allow">{{ $t('firewall.allow') }}</option>
                  <option value="deny">{{ $t('firewall.deny') }}</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>{{ $t('firewall.direction') }}</label>
                <select v-model="ruleForm.direction">
                  <option value="in">{{ $t('firewall.inbound') }}</option>
                  <option value="out">{{ $t('firewall.outbound') }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>{{ $t('firewall.sourceIp') }}</label>
                <input
                  type="text"
                  v-model="ruleForm.source_ip"
                  :placeholder="$t('firewall.sourceIpPlaceholder')"
                >
              </div>
            </div>
            <div class="form-group" v-if="status.backend === 'netsh'">
              <label>{{ $t('firewall.ruleName') }}</label>
              <input
                type="text"
                v-model="ruleForm.name"
                :placeholder="$t('firewall.ruleNamePlaceholder')"
              >
            </div>
            <div class="alert alert-info" v-if="addRuleError">
              {{ addRuleError }}
            </div>
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
    </div>
  </div>
</template>

<script>
export default {
  name: 'Firewall',
  data() {
    return {
      loading: false,
      actionLoading: false,
      error: '',
      status: {
        enabled: false,
        backend: '',
        platform: '',
        default_policy: null,
        rules: []
      },
      searchQuery: '',
      filterAction: '',
      filterDirection: '',
      currentPage: 1,
      pageSize: 20,
      showModal: false,
      addRuleError: '',
      ruleForm: {
        port: '',
        protocol: 'tcp',
        action: 'allow',
        direction: 'in',
        source_ip: '',
        name: ''
      },
      quickPort: '',
      quickProtocol: 'tcp',
      refreshInterval: null
    }
  },
  computed: {
    filteredRules() {
      let rules = this.status.rules || []
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase()
        rules = rules.filter(r =>
          String(r.target || '').toLowerCase().includes(q) ||
          String(r.from || '').toLowerCase().includes(q) ||
          String(r.name || '').toLowerCase().includes(q) ||
          String(r.action || '').toLowerCase().includes(q)
        )
      }
      if (this.filterAction) {
        rules = rules.filter(r => String(r.action || '').toUpperCase() === this.filterAction)
      }
      if (this.filterDirection) {
        rules = rules.filter(r => String(r.direction || '').toUpperCase() === this.filterDirection)
      }
      return rules
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.filteredRules.length / this.pageSize))
    },
    paginatedRules() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.filteredRules.slice(start, start + this.pageSize)
    },
    columnCount() {
      let count = 6
      if (this.status.backend === 'netsh' || this.status.backend === 'iptables') {
        count = 7
      }
      return count
    },
    supportsReload() {
      return ['ufw', 'firewalld'].includes(this.status.backend)
    }
  },
  watch: {
    searchQuery() { this.currentPage = 1 },
    filterAction() { this.currentPage = 1 },
    filterDirection() { this.currentPage = 1 }
  },
  mounted() {
    this.fetchStatus()
    // 30 秒自动刷新状态
    this.refreshInterval = setInterval(() => {
      this.fetchStatus()
    }, 30000)
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  },
  methods: {
    async fetchStatus() {
      this.loading = true
      this.error = ''
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/status',
          method: 'GET'
        })
        if (data.status === 'success') {
          this.status = {
            enabled: data.enabled || false,
            backend: data.backend || '',
            platform: data.platform || '',
            default_policy: data.default_policy || null,
            rules: data.rules || []
          }
        } else {
          this.error = data.message || 'Failed to load firewall status'
        }
      } catch (err) {
        this.error = err.message || 'Failed to load firewall status'
      } finally {
        this.loading = false
      }
    },
    async toggleFirewall() {
      if (!confirm(
        this.status.enabled
          ? this.$t('firewall.confirmDisable')
          : this.$t('firewall.confirmEnable')
      )) return
      this.actionLoading = true
      try {
        const url = this.status.enabled ? '/api/firewall/disable' : '/api/firewall/enable'
        const data = await this.$store.dispatch('apiRequest', {
          url,
          method: 'POST'
        })
        if (data.status === 'success') {
          await this.fetchStatus()
        } else {
          this.error = data.message || 'Operation failed'
        }
      } catch (err) {
        this.error = err.message || 'Operation failed'
      } finally {
        this.actionLoading = false
      }
    },
    async reloadFirewall() {
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/reload',
          method: 'POST'
        })
        if (data.status !== 'success') {
          this.error = data.message || 'Reload failed'
        }
        await this.fetchStatus()
      } catch (err) {
        this.error = err.message || 'Reload failed'
      } finally {
        this.actionLoading = false
      }
    },
    async updatePolicy(direction, policy) {
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/default-policy',
          method: 'PUT',
          body: { direction, policy }
        })
        if (data.status !== 'success') {
          this.error = data.message || 'Failed to update policy'
        }
        await this.fetchStatus()
      } catch (err) {
        this.error = err.message || 'Failed to update policy'
      } finally {
        this.actionLoading = false
      }
    },
    showAddRuleModal() {
      this.ruleForm = {
        port: '',
        protocol: 'tcp',
        action: 'allow',
        direction: 'in',
        source_ip: '',
        name: ''
      }
      this.addRuleError = ''
      this.showModal = true
    },
    async addRule() {
      this.actionLoading = true
      this.addRuleError = ''
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/rules',
          method: 'POST',
          body: { ...this.ruleForm }
        })
        if (data.status === 'success') {
          this.showModal = false
          await this.fetchStatus()
        } else {
          this.addRuleError = data.message || 'Failed to add rule'
        }
      } catch (err) {
        this.addRuleError = err.message || 'Failed to add rule'
      } finally {
        this.actionLoading = false
      }
    },
    async deleteRule(rule, index) {
      if (!confirm(this.$t('firewall.confirmDeleteRule'))) return
      this.actionLoading = true
      try {
        // 根据后端类型构造删除参数
        const params = {}
        if (rule.name && this.status.backend === 'netsh') {
          params.name = rule.name
        } else {
          // 从 target 中解析端口和协议，例如 "80/tcp"
          const target = rule.target || ''
          const parts = target.split('/')
          if (parts.length === 2) {
            params.port = parts[0]
            params.protocol = parts[1]
          } else {
            params.port = target
            params.protocol = 'tcp'
          }
          if (rule.action) {
            params.action = rule.action.toLowerCase()
          }
          if (rule.direction) {
            params.direction = rule.direction.toLowerCase()
          }
        }
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/rules',
          method: 'DELETE',
          body: params
        })
        if (data.status === 'success') {
          await this.fetchStatus()
        } else {
          this.error = data.message || 'Failed to delete rule'
        }
      } catch (err) {
        this.error = err.message || 'Failed to delete rule'
      } finally {
        this.actionLoading = false
      }
    },
    async quickAllow() {
      if (!this.quickPort) return
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/quick-allow',
          method: 'POST',
          body: { port: parseInt(this.quickPort), protocol: this.quickProtocol }
        })
        if (data.status === 'success') {
          this.quickPort = ''
          await this.fetchStatus()
        } else {
          this.error = data.message || 'Failed to allow port'
        }
      } catch (err) {
        this.error = err.message || 'Failed to allow port'
      } finally {
        this.actionLoading = false
      }
    },
    async quickBlock() {
      if (!this.quickPort) return
      this.actionLoading = true
      try {
        const data = await this.$store.dispatch('apiRequest', {
          url: '/api/firewall/quick-block',
          method: 'POST',
          body: { port: parseInt(this.quickPort), protocol: this.quickProtocol }
        })
        if (data.status === 'success') {
          this.quickPort = ''
          await this.fetchStatus()
        } else {
          this.error = data.message || 'Failed to block port'
        }
      } catch (err) {
        this.error = err.message || 'Failed to block port'
      } finally {
        this.actionLoading = false
      }
    },
    actionClass(action) {
      const a = String(action || '').toUpperCase()
      if (a === 'ALLOW') return 'badge-allow'
      if (a === 'DENY' || a === 'BLOCK' || a === 'REJECT') return 'badge-deny'
      return ''
    }
  }
}
</script>

<style scoped>
/* 页面容器 */
.firewall-page {
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

.icon-active {
  background: rgba(52, 199, 89, 0.15);
  color: var(--ios-green);
}

.icon-inactive {
  background: rgba(255, 59, 48, 0.15);
  color: var(--ios-red);
}

.icon-backend {
  background: rgba(0, 122, 255, 0.15);
  color: var(--ios-blue);
}

.icon-rules {
  background: rgba(255, 149, 0, 0.15);
  color: var(--ios-orange);
}

.icon-platform {
  background: rgba(175, 82, 222, 0.15);
  color: var(--ios-purple);
}

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

.section-icon {
  color: var(--ios-blue);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ios-space-4);
}

.section-header .section-title {
  margin: 0;
}

/* 默认策略 */
.policy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--ios-space-4);
}

.policy-item {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-2);
}

.policy-label {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  text-transform: capitalize;
}

.policy-control {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
}

.policy-badge {
  padding: 2px 8px;
  border-radius: var(--ios-radius-sm);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
}

.policy-allow { background: rgba(52, 199, 89, 0.2); color: var(--ios-green); }
.policy-deny { background: rgba(255, 59, 48, 0.2); color: var(--ios-red); }
.policy-reject { background: rgba(255, 149, 0, 0.2); color: var(--ios-orange); }

.policy-select {
  flex: 1;
  padding: 6px 10px;
  border-radius: var(--ios-radius-sm);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-footnote);
  outline: none;
  cursor: pointer;
}

/* 快速操作 */
.quick-actions-grid {
  display: flex;
  align-items: flex-end;
  gap: var(--ios-space-3);
  flex-wrap: wrap;
}

.quick-action-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quick-label {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
}

.quick-input,
.quick-select {
  padding: 8px 12px;
  border-radius: var(--ios-radius-md);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-subhead);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.quick-input {
  width: 140px;
}

.quick-select {
  width: 90px;
}

.quick-input:focus,
.quick-select:focus {
  border-color: var(--ios-blue);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

/* 规则筛选 */
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

.rule-target {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-weight: var(--ios-weight-medium);
}

.loading,
.no-data {
  text-align: center !important;
  color: var(--ios-label-secondary) !important;
  padding: var(--ios-space-6) !important;
}

/* 徽章 */
.action-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--ios-radius-full);
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  text-transform: uppercase;
}

.badge-allow {
  background: rgba(52, 199, 89, 0.2);
  color: var(--ios-green);
}

.badge-deny {
  background: rgba(255, 59, 48, 0.2);
  color: var(--ios-red);
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

.btn-icon {
  padding: 6px;
  width: 28px;
  height: 28px;
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

.btn-success {
  background: var(--ios-green);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #28a745;
  box-shadow: 0 2px 8px rgba(52, 199, 89, 0.3);
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

.alert-icon {
  flex-shrink: 0;
}

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
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
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
.form-group select {
  padding: 10px 12px;
  border-radius: var(--ios-radius-md);
  border: 0.5px solid var(--ios-separator);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-body);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.form-group input:focus,
.form-group select:focus {
  border-color: var(--ios-blue);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ios-space-3);
}

.form-actions {
  display: flex;
  gap: var(--ios-space-3);
  justify-content: flex-end;
  margin-top: var(--ios-space-5);
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

  .quick-actions-grid {
    flex-direction: column;
    align-items: stretch;
  }

  .quick-input,
  .quick-select {
    width: 100%;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .data-table {
    font-size: var(--ios-text-caption1);
  }

  .data-table th,
  .data-table td {
    padding: var(--ios-space-2);
  }
}
</style>
