<template>
  <div class="tfa-page">
    <div class="page-header">
      <h2>双因素认证 (2FA)</h2>
      <p class="page-subtitle">为您的账户添加额外的安全保护</p>
    </div>

    <!-- 2FA状态卡片 -->
    <div class="status-card ios-glass">
      <div class="status-row">
        <div class="status-info">
          <div class="status-icon" :class="{ 'enabled': status.enabled }">
            <svg v-if="status.enabled" viewBox="0 0 24 24" fill="none">
              <path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5"/>
              <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="0.5" fill="currentColor"/>
            </svg>
          </div>
          <div>
            <h3 class="status-title">{{ status.enabled ? '已启用' : '未启用' }}</h3>
            <p class="status-desc" v-if="status.enabled">
              您的账户已受双因素认证保护
            </p>
            <p class="status-desc" v-else>
              启用双因素认证以增强账户安全
            </p>
          </div>
        </div>
        <div class="status-action">
          <button
            v-if="!status.enabled"
            class="ios-btn ios-btn-primary"
            @click="startSetup"
            :disabled="loading"
          >
            {{ loading ? '生成中...' : '启用2FA' }}
          </button>
          <button
            v-else
            class="ios-btn ios-btn-danger"
            @click="showDisableModal = true"
          >
            禁用2FA
          </button>
        </div>
      </div>

      <!-- 备用验证码信息 -->
      <div v-if="status.enabled" class="backup-info">
        <div class="backup-header">
          <svg class="backup-icon" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 10h8M8 14h8M8 18h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <span>备用验证码</span>
        </div>
        <p class="backup-count">剩余 {{ status.backup_codes_remaining }} 个备用验证码</p>
        <button
          class="ios-btn ios-btn-secondary btn-sm"
          @click="showRegenerateModal = true"
        >
          重新生成
        </button>
      </div>
    </div>

    <!-- 2FA设置弹窗 -->
    <div v-if="setupData" class="tfa-modal-overlay" @click.self="cancelSetup">
      <div class="tfa-modal ios-glass">
        <div class="modal-header">
          <h3>设置双因素认证</h3>
          <button class="close-btn" @click="cancelSetup">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 步骤1：扫描二维码 -->
          <div v-if="setupStep === 1" class="setup-step">
            <div class="step-title">
              <span class="step-number">1</span>
              扫描二维码
            </div>
            <p class="step-desc">使用 Google Authenticator、Microsoft Authenticator 或其他TOTP应用扫描下方二维码</p>
            <div class="qr-container">
              <img :src="'data:image/png;base64,' + setupData.qr_code" alt="2FA QR Code" class="qr-image" />
            </div>
            <div class="secret-section">
              <p class="secret-label">无法扫描？手动输入密钥：</p>
              <div class="secret-display">
                <code>{{ setupData.secret }}</code>
                <button class="copy-btn" @click="copySecret">
                  <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
                    <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="1.5"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" stroke-width="1.5"/>
                  </svg>
                </button>
              </div>
            </div>
            <button class="ios-btn ios-btn-primary full-width" @click="setupStep = 2">
              下一步
            </button>
          </div>

          <!-- 步骤2：验证验证码 -->
          <div v-if="setupStep === 2" class="setup-step">
            <div class="step-title">
              <span class="step-number">2</span>
              验证验证码
            </div>
            <p class="step-desc">请在下方输入认证应用中显示的6位验证码</p>
            <div class="code-input-container">
              <input
                v-for="i in 6"
                :key="i"
                :ref="'codeInput' + i"
                v-model="codeInputs[i - 1]"
                type="text"
                maxlength="1"
                class="code-input"
                @input="onCodeInput(i, $event)"
                @keydown.delete="onCodeDelete(i, $event)"
                @paste="onCodePaste"
              />
            </div>
            <Transition name="ios-fade">
              <div v-if="setupError" class="error-msg">{{ setupError }}</div>
            </Transition>
            <div class="step-actions">
              <button class="ios-btn ios-btn-secondary" @click="setupStep = 1">上一步</button>
              <button
                class="ios-btn ios-btn-primary"
                @click="confirmEnable"
                :disabled="verifying || codeInputs.join('').length !== 6"
              >
                <span v-if="verifying" class="ios-spinner-sm"></span>
                {{ verifying ? '验证中...' : '确认启用' }}
              </button>
            </div>
          </div>

          <!-- 步骤3：显示备用验证码 -->
          <div v-if="setupStep === 3" class="setup-step">
            <div class="step-title">
              <span class="step-number">3</span>
              保存备用验证码
            </div>
            <p class="step-desc">请妥善保存以下备用验证码，当您无法使用认证应用时可使用它们登录</p>
            <div class="backup-codes-grid">
              <div v-for="(code, index) in backupCodes" :key="index" class="backup-code-item">
                {{ code }}
              </div>
            </div>
            <div class="step-actions">
              <button class="ios-btn ios-btn-secondary" @click="downloadBackupCodes">
                下载验证码
              </button>
              <button class="ios-btn ios-btn-primary" @click="finishSetup">
                完成
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 禁用2FA弹窗 -->
    <div v-if="showDisableModal" class="tfa-modal-overlay" @click.self="showDisableModal = false">
      <div class="tfa-modal ios-glass">
        <div class="modal-header">
          <h3>禁用双因素认证</h3>
          <button class="close-btn" @click="showDisableModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="modal-warn">禁用双因素认证将降低您账户的安全性，请输入验证码以确认操作</p>
          <div class="code-input-container">
            <input
              v-for="i in 6"
              :key="i"
              :ref="'disableCodeInput' + i"
              v-model="disableCodeInputs[i - 1]"
              type="text"
              maxlength="1"
              class="code-input"
              @input="onDisableCodeInput(i, $event)"
              @keydown.delete="onDisableCodeDelete(i, $event)"
              @paste="onDisableCodePaste"
            />
          </div>
          <Transition name="ios-fade">
            <div v-if="disableError" class="error-msg">{{ disableError }}</div>
          </Transition>
          <div class="step-actions">
            <button class="ios-btn ios-btn-secondary" @click="showDisableModal = false">取消</button>
            <button
              class="ios-btn ios-btn-danger"
              @click="confirmDisable"
              :disabled="disabling || disableCodeInputs.join('').length !== 6"
            >
              <span v-if="disabling" class="ios-spinner-sm"></span>
              {{ disabling ? '处理中...' : '确认禁用' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重新生成备用码弹窗 -->
    <div v-if="showRegenerateModal" class="tfa-modal-overlay" @click.self="showRegenerateModal = false">
      <div class="tfa-modal ios-glass">
        <div class="modal-header">
          <h3>重新生成备用验证码</h3>
          <button class="close-btn" @click="showRegenerateModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="step-desc">请输入当前认证应用中的验证码以确认操作</p>
          <div class="code-input-container">
            <input
              v-for="i in 6"
              :key="i"
              :ref="'regenCodeInput' + i"
              v-model="regenCodeInputs[i - 1]"
              type="text"
              maxlength="1"
              class="code-input"
              @input="onRegenCodeInput(i, $event)"
              @keydown.delete="onRegenCodeDelete(i, $event)"
              @paste="onRegenCodePaste"
            />
          </div>
          <Transition name="ios-fade">
            <div v-if="regenError" class="error-msg">{{ regenError }}</div>
          </Transition>
          <div v-if="newBackupCodes.length > 0" class="backup-codes-grid">
            <div v-for="(code, index) in newBackupCodes" :key="index" class="backup-code-item">
              {{ code }}
            </div>
          </div>
          <div class="step-actions">
            <button class="ios-btn ios-btn-secondary" @click="showRegenerateModal = false">关闭</button>
            <button
              v-if="newBackupCodes.length === 0"
              class="ios-btn ios-btn-primary"
              @click="confirmRegenerate"
              :disabled="regenerating || regenCodeInputs.join('').length !== 6"
            >
              <span v-if="regenerating" class="ios-spinner-sm"></span>
              {{ regenerating ? '处理中...' : '确认生成' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TwoFactorAuth',
  data() {
    return {
      status: { enabled: false, backup_codes_remaining: 0 },
      loading: false,
      // 设置流程
      setupData: null,
      setupStep: 1,
      codeInputs: ['', '', '', '', '', ''],
      verifying: false,
      setupError: null,
      backupCodes: [],
      // 禁用流程
      showDisableModal: false,
      disableCodeInputs: ['', '', '', '', '', ''],
      disabling: false,
      disableError: null,
      // 重新生成备用码
      showRegenerateModal: false,
      regenCodeInputs: ['', '', '', '', '', ''],
      regenerating: false,
      regenError: null,
      newBackupCodes: []
    }
  },
  async mounted() {
    await this.fetchStatus()
  },
  methods: {
    async apiRequest(url, method = 'GET', body = null) {
      const token = this.$store.state.token
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const options = { method, headers }
      if (body && method !== 'GET') {
        options.body = JSON.stringify(body)
      }

      const res = await fetch(url, options)
      if (res.status === 401) {
        this.$store.commit('setToken', null)
        this.$store.commit('setUser', null)
        return null
      }
      return res.json()
    },

    async fetchStatus() {
      try {
        const data = await this.apiRequest('/api/2fa/status')
        if (data && data.status === 'success') {
          this.status = data
        }
      } catch (e) {
        console.error('Failed to fetch 2FA status:', e)
      }
    },

    async startSetup() {
      this.loading = true
      try {
        const data = await this.apiRequest('/api/2fa/setup', 'POST')
        if (data && data.status === 'success') {
          this.setupData = data
          this.setupStep = 1
          this.codeInputs = ['', '', '', '', '', '']
          this.setupError = null
        }
      } catch (e) {
        console.error('2FA setup failed:', e)
      } finally {
        this.loading = false
      }
    },

    cancelSetup() {
      this.setupData = null
      this.setupStep = 1
      this.codeInputs = ['', '', '', '', '', '']
      this.setupError = null
    },

    async confirmEnable() {
      const code = this.codeInputs.join('')
      if (code.length !== 6) return

      this.verifying = true
      this.setupError = null
      try {
        const data = await this.apiRequest('/api/2fa/enable', 'POST', {
          secret: this.setupData.secret,
          verification_code: code
        })
        if (data && data.status === 'success') {
          this.backupCodes = data.backup_codes || []
          this.setupStep = 3
          this.status.enabled = true
          this.status.backup_codes_remaining = this.backupCodes.length
        } else {
          this.setupError = data ? data.message : '验证失败'
        }
      } catch (e) {
        this.setupError = '网络错误，请重试'
      } finally {
        this.verifying = false
      }
    },

    finishSetup() {
      this.setupData = null
      this.setupStep = 1
      this.backupCodes = []
    },

    async confirmDisable() {
      const code = this.disableCodeInputs.join('')
      if (code.length !== 6) return

      this.disabling = true
      this.disableError = null
      try {
        const data = await this.apiRequest('/api/2fa/disable', 'POST', {
          verification_code: code
        })
        if (data && data.status === 'success') {
          this.showDisableModal = false
          this.status.enabled = false
          this.status.backup_codes_remaining = 0
          this.disableCodeInputs = ['', '', '', '', '', '']
        } else {
          this.disableError = data ? data.message : '操作失败'
        }
      } catch (e) {
        this.disableError = '网络错误，请重试'
      } finally {
        this.disabling = false
      }
    },

    async confirmRegenerate() {
      const code = this.regenCodeInputs.join('')
      if (code.length !== 6) return

      this.regenerating = true
      this.regenError = null
      try {
        const data = await this.apiRequest('/api/2fa/backup-codes/regenerate', 'POST', {
          verification_code: code
        })
        if (data && data.status === 'success') {
          this.newBackupCodes = data.backup_codes || []
          this.status.backup_codes_remaining = this.newBackupCodes.length
          this.regenCodeInputs = ['', '', '', '', '', '']
        } else {
          this.regenError = data ? data.message : '操作失败'
        }
      } catch (e) {
        this.regenError = '网络错误，请重试'
      } finally {
        this.regenerating = false
      }
    },

    copySecret() {
      if (this.setupData && this.setupData.secret) {
        navigator.clipboard.writeText(this.setupData.secret)
      }
    },

    downloadBackupCodes() {
      const text = 'xiaopengPanel 备用验证码\n\n' + this.backupCodes.join('\n') + '\n\n请妥善保存！'
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'backup_codes.txt'
      a.click()
      URL.revokeObjectURL(url)
    },

    // 验证码输入框处理
    onCodeInput(index, event) {
      const value = event.target.value.replace(/\D/g, '')
      this.codeInputs[index - 1] = value
      if (value && index < 6) {
        const nextInput = this.$refs['codeInput' + (index + 1)]
        if (nextInput) nextInput[0].focus()
      }
    },
    onCodeDelete(index, event) {
      if (!this.codeInputs[index - 1] && index > 1) {
        const prevInput = this.$refs['codeInput' + (index - 1)]
        if (prevInput) prevInput[0].focus()
      }
    },
    onCodePaste(event) {
      event.preventDefault()
      const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
      for (let i = 0; i < 6; i++) {
        this.codeInputs[i] = pasted[i] || ''
      }
    },
    onDisableCodeInput(index, event) {
      const value = event.target.value.replace(/\D/g, '')
      this.disableCodeInputs[index - 1] = value
      if (value && index < 6) {
        const nextInput = this.$refs['disableCodeInput' + (index + 1)]
        if (nextInput) nextInput[0].focus()
      }
    },
    onDisableCodeDelete(index, event) {
      if (!this.disableCodeInputs[index - 1] && index > 1) {
        const prevInput = this.$refs['disableCodeInput' + (index - 1)]
        if (prevInput) prevInput[0].focus()
      }
    },
    onDisableCodePaste(event) {
      event.preventDefault()
      const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
      for (let i = 0; i < 6; i++) {
        this.disableCodeInputs[i] = pasted[i] || ''
      }
    },
    onRegenCodeInput(index, event) {
      const value = event.target.value.replace(/\D/g, '')
      this.regenCodeInputs[index - 1] = value
      if (value && index < 6) {
        const nextInput = this.$refs['regenCodeInput' + (index + 1)]
        if (nextInput) nextInput[0].focus()
      }
    },
    onRegenCodeDelete(index, event) {
      if (!this.regenCodeInputs[index - 1] && index > 1) {
        const prevInput = this.$refs['regenCodeInput' + (index - 1)]
        if (prevInput) prevInput[0].focus()
      }
    },
    onRegenCodePaste(event) {
      event.preventDefault()
      const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
      for (let i = 0; i < 6; i++) {
        this.regenCodeInputs[i] = pasted[i] || ''
      }
    }
  }
}
</script>

<style scoped>
.tfa-page {
  max-width: 680px;
}

.page-header {
  margin-bottom: var(--ios-space-6);
}

.page-header h2 {
  font-size: var(--ios-text-title2);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  margin: 0 0 var(--ios-space-1);
}

.page-subtitle {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
}

/* 状态卡片 */
.status-card {
  padding: var(--ios-space-6);
  border-radius: var(--ios-radius-2xl);
  background: var(--ios-glass-bg);
  backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate));
  border: 0.5px solid var(--ios-glass-border);
  transition: var(--ios-theme-transition);
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ios-space-4);
}

.status-info {
  display: flex;
  align-items: center;
  gap: var(--ios-space-4);
}

.status-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--ios-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 59, 48, 0.1);
  color: var(--ios-red);
  flex-shrink: 0;
}

.status-icon.enabled {
  background: rgba(52, 199, 89, 0.1);
  color: var(--ios-green);
}

.status-icon svg {
  width: 24px;
  height: 24px;
}

.status-title {
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0 0 var(--ios-space-1);
}

.status-desc {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
}

/* 备用验证码信息 */
.backup-info {
  margin-top: var(--ios-space-5);
  padding-top: var(--ios-space-5);
  border-top: 0.5px solid var(--ios-separator);
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  flex-wrap: wrap;
}

.backup-header {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
}

.backup-icon {
  width: 20px;
  height: 20px;
  color: var(--ios-label-secondary);
}

.backup-count {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  margin: 0;
  flex: 1;
}

/* 弹窗 */
.tfa-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--ios-space-4);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.tfa-modal {
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--ios-glass-bg);
  backdrop-filter: blur(40px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-2xl);
  box-shadow: var(--ios-shadow-2xl);
  animation: slideUp 0.3s var(--ios-ease-spring);
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ios-space-5) var(--ios-space-6);
  border-bottom: 0.5px solid var(--ios-separator);
}

.modal-header h3 {
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--ios-label-secondary);
  font-size: 24px;
  cursor: pointer;
  border-radius: var(--ios-radius-md);
  transition: all var(--ios-transition-fast);
}

.close-btn:hover {
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-primary);
}

.modal-body {
  padding: var(--ios-space-6);
}

/* 设置步骤 */
.setup-step {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-4);
}

.step-title {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  font-size: var(--ios-text-body);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
}

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ios-blue);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-bold);
}

.step-desc {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
  line-height: 1.5;
}

.modal-warn {
  font-size: var(--ios-text-subhead);
  color: var(--ios-orange, #FF9500);
  margin: 0;
  padding: var(--ios-space-3);
  background: rgba(255, 149, 0, 0.1);
  border-radius: var(--ios-radius-lg);
}

/* QR码 */
.qr-container {
  display: flex;
  justify-content: center;
  padding: var(--ios-space-4);
  background: white;
  border-radius: var(--ios-radius-xl);
}

.qr-image {
  width: 200px;
  height: 200px;
}

/* 密钥显示 */
.secret-section {
  padding: var(--ios-space-3);
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-lg);
}

.secret-label {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  margin: 0 0 var(--ios-space-2);
}

.secret-display {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  justify-content: space-between;
}

.secret-display code {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-primary);
  word-break: break-all;
}

.copy-btn {
  border: none;
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
  padding: var(--ios-space-2);
  border-radius: var(--ios-radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--ios-transition-fast);
  flex-shrink: 0;
}

.copy-btn:hover {
  background: var(--ios-fill-secondary);
  color: var(--ios-label-primary);
}

/* 验证码输入框 */
.code-input-container {
  display: flex;
  gap: var(--ios-space-2);
  justify-content: center;
}

.code-input {
  width: 44px;
  height: 52px;
  text-align: center;
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  background: var(--ios-fill-quaternary);
  border: 2px solid transparent;
  border-radius: var(--ios-radius-lg);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.code-input:focus {
  border-color: var(--ios-blue);
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15);
}

/* 备用验证码网格 */
.backup-codes-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ios-space-2);
  padding: var(--ios-space-4);
  background: var(--ios-fill-quaternary);
  border-radius: var(--ios-radius-lg);
}

.backup-code-item {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
  text-align: center;
  padding: var(--ios-space-2);
  background: var(--ios-fill-tertiary);
  border-radius: var(--ios-radius-md);
}

/* 按钮样式 */
.ios-btn {
  padding: var(--ios-space-3) var(--ios-space-5);
  border: none;
  border-radius: var(--ios-radius-lg);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-semibold);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-2);
}

.ios-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ios-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.ios-btn-primary {
  background: var(--ios-blue);
  color: white;
}

.ios-btn-primary:hover:not(:disabled) {
  background: #0066d6;
}

.ios-btn-secondary {
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
}

.ios-btn-secondary:hover:not(:disabled) {
  background: var(--ios-fill-secondary);
}

.ios-btn-danger {
  background: var(--ios-red);
  color: white;
}

.ios-btn-danger:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-sm {
  padding: var(--ios-space-2) var(--ios-space-3);
  font-size: var(--ios-text-caption1);
}

.full-width {
  width: 100%;
}

.step-actions {
  display: flex;
  gap: var(--ios-space-3);
  justify-content: flex-end;
  margin-top: var(--ios-space-2);
}

.error-msg {
  color: var(--ios-red);
  font-size: var(--ios-text-subhead);
  text-align: center;
  padding: var(--ios-space-2);
  background: rgba(255, 59, 48, 0.1);
  border-radius: var(--ios-radius-md);
}

.ios-spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ios-fade-enter-active,
.ios-fade-leave-active {
  transition: all var(--ios-transition-fast);
}

.ios-fade-enter-from,
.ios-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 响应式 */
@media (max-width: 480px) {
  .code-input {
    width: 38px;
    height: 46px;
  }

  .status-row {
    flex-direction: column;
    align-items: stretch;
  }

  .backup-codes-grid {
    grid-template-columns: 1fr;
  }
}
</style>
