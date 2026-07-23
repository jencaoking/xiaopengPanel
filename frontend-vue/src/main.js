import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import { createStore } from 'vuex'
import App from './App.vue'
import zhCN from './locales/zh-CN.js'
import enUS from './locales/en-US.js'

// 导入设计系统样式
import './styles/design-system.css'
import './styles/animations.css'

// 创建i18n实例
const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  fallbackLocale: 'en',
  messages: {
    'zh': zhCN,
    'en': enUS
  }
})

// 安全地解析 JSON
function safeJSONParse(str, defaultValue = null) {
  try {
    return JSON.parse(str)
  } catch (e) {
    return defaultValue
  }
}

// 安全地获取 localStorage
function safeLocalStorageGet(key, defaultValue = null) {
  try {
    return localStorage.getItem(key) || defaultValue
  } catch (e) {
    console.warn(`Failed to read localStorage key "${key}":`, e)
    return defaultValue
  }
}

// 初始化主题：优先使用用户保存的偏好，其次检测系统偏好
function initializeTheme() {
  const savedTheme = safeLocalStorageGet('theme', null)
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const theme = savedTheme || (prefersDark ? 'dark' : 'dark') // 默认暗色
  document.documentElement.setAttribute('data-theme', theme)
  document.documentElement.style.colorScheme = theme
  return theme
}

// 监听系统主题变化（仅当用户未手动设置时跟随）
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  const savedTheme = safeLocalStorageGet('theme', null)
  if (!savedTheme) {
    const theme = e.matches ? 'dark' : 'light'
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.style.colorScheme = theme
  }
})

// 创建Vuex Store
const store = createStore({
  state() {
    return {
      systemInfo: {
        cpuUsage: 0,
        memoryUsage: 0,
        diskUsage: 0,
        uptime: '0d 0h 0m'
      },
      token: safeLocalStorageGet('token', null),
      user: safeJSONParse(safeLocalStorageGet('user'), null),
      currentPage: 'dashboard',
      sidebarOpen: true,
      theme: safeLocalStorageGet('theme', 'dark'),
      language: safeLocalStorageGet('language', 'zh')
    }
  },
  mutations: {
    setSystemInfo(state, info) {
      state.systemInfo = { ...state.systemInfo, ...info }
    },
    setToken(state, token) {
      state.token = token
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    setUser(state, user) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    },
    setCurrentPage(state, page) {
      state.currentPage = page
    },
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen
    },
    toggleTheme(state) {
      state.theme = state.theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', state.theme)
      document.documentElement.setAttribute('data-theme', state.theme)
      document.documentElement.style.colorScheme = state.theme
    },
    setLanguage(state, language) {
      state.language = language
      localStorage.setItem('language', language)
    }
  },
  actions: {
    // API请求封装，自动添加token
    async apiRequest({ state }, { url, method = 'GET', body = null }) {
      const headers = {
        'Content-Type': 'application/json'
      }
      
      if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`
      }
      
      const options = {
        method,
        headers
      }
      
      if (body && method !== 'GET') {
        options.body = typeof body === 'string' ? body : JSON.stringify(body)
      }
      
      const response = await fetch(url, options)
      
      if (!response.ok) {
        if (response.status === 401) {
          // Token过期，清除登录状态
          store.commit('setToken', null)
          store.commit('setUser', null)
          window.location.href = '/login'
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      return await response.json()
    },
    
    // 登录
    async login({ commit }, { username, password }) {
      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ username, password })
        })
        
        const data = await response.json()
        
        if (data.status === 'success') {
          commit('setToken', data.token)
          commit('setUser', { username: data.user.username, role: data.user.role })
          return { success: true }
        } else {
          return { success: false, message: data.message }
        }
      } catch (error) {
        return { success: false, message: error.message }
      }
    },
    
    // 登出
    logout({ commit }) {
      commit('setToken', null)
      commit('setUser', null)
    }
  },
  getters: {
    getSystemInfo: (state) => state.systemInfo,
    isLoggedIn: (state) => !!state.token,
    getUser: (state) => state.user
  }
})

// 初始化主题
const initialTheme = initializeTheme()

// 创建Vue应用
const app = createApp(App)

// 使用插件
app.use(i18n)
app.use(store)

// 挂载应用
app.mount('#app')