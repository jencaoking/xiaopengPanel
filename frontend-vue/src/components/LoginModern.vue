<template>
  <div class="ios-login-page">
    <div class="login-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
    </div>
    
    <div class="login-container">
      <div class="login-card ios-glass">
        <div class="login-header">
          <div class="logo-container">
            <div class="logo">
              <svg viewBox="0 0 32 32" fill="none">
                <defs>
                  <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#007AFF"/>
                    <stop offset="100%" style="stop-color:#5856D6"/>
                  </linearGradient>
                </defs>
                <rect x="2" y="2" width="12" height="12" rx="3" fill="url(#logoGrad)" opacity="0.9"/>
                <rect x="18" y="2" width="12" height="12" rx="3" fill="url(#logoGrad)" opacity="0.7"/>
                <rect x="2" y="18" width="12" height="12" rx="3" fill="url(#logoGrad)" opacity="0.7"/>
                <rect x="18" y="18" width="12" height="12" rx="3" fill="url(#logoGrad)" opacity="0.5"/>
              </svg>
            </div>
          </div>
          <h1 class="login-title">小鹏面板</h1>
          <p class="login-subtitle">服务器运维管理系统</p>
        </div>
        
        <form class="login-form" @submit.prevent="handleLogin">
          <div class="form-group">
            <label class="form-label" for="username">用户名</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <input
                id="username"
                v-model="form.username"
                type="text"
                class="form-input"
                placeholder="请输入用户名"
                required
                autocomplete="username"
                :disabled="loading"
              >
            </div>
          </div>
          
          <div class="form-group">
            <label class="form-label" for="password">密码</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" stroke-width="1.5"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                placeholder="请输入密码"
                required
                autocomplete="current-password"
                :disabled="loading"
              >
              <button
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>
          
          <div class="form-options">
            <label class="ios-toggle-wrapper">
              <input v-model="form.rememberMe" type="checkbox" class="ios-toggle-input" :disabled="loading">
              <span class="ios-toggle-slider"></span>
              <span class="toggle-label">记住我</span>
            </label>
          </div>
          
          <button
            type="submit"
            class="ios-btn ios-btn-primary btn-login"
            :disabled="loading || !isValid"
          >
            <span v-if="loading" class="ios-spinner"></span>
            <span>{{ loading ? '登录中...' : '登录' }}</span>
          </button>
        </form>
        
        <Transition name="ios-fade">
          <div v-if="error" class="ios-alert ios-alert-error" role="alert">
            <svg class="alert-icon" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
              <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="1" fill="currentColor"/>
            </svg>
            <span>{{ error }}</span>
          </div>
        </Transition>
        
        <div class="login-footer">
          <p>© 2026 小鹏面板. 保留所有权利.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginModern',
  data() {
    return {
      form: {
        username: '',
        password: '',
        rememberMe: false
      },
      showPassword: false,
      loading: false,
      error: null
    }
  },
  computed: {
    isValid() {
      return this.form.username.trim() && this.form.password.length >= 1
    }
  },
  methods: {
    async handleLogin() {
      if (!this.isValid) return
      this.loading = true
      this.error = null
      try {
        const result = await this.$store.dispatch('login', {
          username: this.form.username.trim(),
          password: this.form.password
        })
        if (result.success) {
          this.$store.commit('setCurrentPage', 'dashboard')
        } else {
          this.error = result.message || '登录失败，请检查用户名和密码'
        }
      } catch (err) {
        this.error = err.message || '登录失败，请稍后重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.ios-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--ios-bg-grouped);
}

.login-background {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, var(--ios-blue), var(--ios-purple));
  top: -150px;
  right: -100px;
  animation: ios-float 25s ease-in-out infinite;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, var(--ios-teal), var(--ios-green));
  bottom: -100px;
  left: -100px;
  animation: ios-float 30s ease-in-out infinite reverse;
}

@keyframes ios-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -40px) scale(1.1); }
  66% { transform: translate(-30px, 30px) scale(0.95); }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  padding: var(--ios-space-4);
}

.login-card {
  background: var(--ios-glass-bg);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-3xl);
  box-shadow: var(--ios-shadow-2xl);
  padding: var(--ios-space-10);
  animation: ios-slide-up 0.6s var(--ios-ease-spring);
}

@keyframes ios-slide-up {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.login-header {
  text-align: center;
  margin-bottom: var(--ios-space-8);
}

.logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: var(--ios-space-5);
}

.logo {
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, rgba(0, 122, 255, 0.1), rgba(88, 86, 214, 0.1));
  border-radius: var(--ios-radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--ios-shadow-md);
}

.logo svg {
  width: 48px;
  height: 48px;
}

.login-title {
  font-size: var(--ios-text-large-title);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
  margin-bottom: var(--ios-space-2);
  letter-spacing: var(--ios-tracking-tight);
}

.login-subtitle {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-2);
}

.form-label {
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: var(--ios-space-4);
  width: 20px;
  height: 20px;
  color: var(--ios-label-tertiary);
  pointer-events: none;
  transition: color var(--ios-transition-fast);
}

.form-input {
  width: 100%;
  padding: var(--ios-space-4);
  padding-left: var(--ios-space-12);
  font-family: var(--ios-font-family);
  font-size: var(--ios-text-body);
  color: var(--ios-label-primary);
  background: var(--ios-fill-quaternary);
  border: none;
  border-radius: var(--ios-radius-xl);
  transition: all var(--ios-transition-fast);
}

.form-input:focus {
  outline: none;
  background: var(--ios-fill-tertiary);
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.15);
}

.form-input:focus + .input-icon,
.input-wrapper:focus-within .input-icon {
  color: var(--ios-blue);
}

.form-input::placeholder {
  color: var(--ios-label-tertiary);
}

.password-toggle {
  position: absolute;
  right: var(--ios-space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  color: var(--ios-label-tertiary);
  cursor: pointer;
  border-radius: var(--ios-radius-md);
  transition: all var(--ios-transition-fast);
}

.password-toggle:hover {
  color: var(--ios-label-primary);
  background: var(--ios-fill-quaternary);
}

.password-toggle:active {
  transform: scale(0.95);
}

.password-toggle svg {
  width: 20px;
  height: 20px;
}

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ios-toggle-wrapper {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  cursor: pointer;
}

.ios-toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.ios-toggle-slider {
  position: relative;
  width: 51px;
  height: 31px;
  background: var(--ios-fill-secondary);
  border-radius: 31px;
  transition: background var(--ios-transition-normal);
}

.ios-toggle-slider::before {
  content: '';
  position: absolute;
  width: 27px;
  height: 27px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  transition: transform var(--ios-transition-spring);
}

.ios-toggle-input:checked + .ios-toggle-slider {
  background: var(--ios-green);
}

.ios-toggle-input:checked + .ios-toggle-slider::before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
}

.btn-login {
  width: 100%;
  padding: var(--ios-space-4);
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  margin-top: var(--ios-space-2);
  border-radius: var(--ios-radius-xl);
}

.btn-login:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-login:not(:disabled):active {
  transform: scale(0.98);
}

.ios-alert {
  display: flex;
  align-items: center;
  gap: var(--ios-space-3);
  margin-top: var(--ios-space-4);
  padding: var(--ios-space-4);
  border-radius: var(--ios-radius-xl);
  font-size: var(--ios-text-subhead);
}

.ios-alert-error {
  background: rgba(255, 59, 48, 0.1);
  color: var(--ios-red);
}

.alert-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.login-footer {
  margin-top: var(--ios-space-8);
  padding-top: var(--ios-space-6);
  border-top: 0.5px solid var(--ios-separator);
  text-align: center;
}

.login-footer p {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-tertiary);
  margin: 0;
}

.ios-fade-enter-active,
.ios-fade-leave-active {
  transition: all var(--ios-transition-normal);
}

.ios-fade-enter-from,
.ios-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 480px) {
  .login-card {
    padding: var(--ios-space-6);
    border-radius: var(--ios-radius-2xl);
  }
  
  .login-title {
    font-size: var(--ios-text-title1);
  }
  
  .orb-1, .orb-2 {
    display: none;
  }
}
</style>
