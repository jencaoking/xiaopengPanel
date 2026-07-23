/**
 * Vuex Store 单元测试
 *
 * 测试范围：
 * - mutations（setToken, setUser, setPermissions, toggleTheme, setCurrentPage 等）
 * - getters（isLoggedIn, hasPermission）
 * - actions（login, verify2FA, logout）使用 mock fetch
 *
 * 注意：store 定义在 main.js 中且内联了应用初始化逻辑（主题监听等），
 * 无法直接导入。这里重建相同的 store 配置进行测试，逻辑与 main.js 保持一致。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createStore } from 'vuex'
import { hasPermission } from '../../src/utils/permissions.js'

function createTestStore() {
  return createStore({
    state() {
      return {
        systemInfo: { cpuUsage: 0, memoryUsage: 0, diskUsage: 0, uptime: '0d 0h 0m' },
        token: null,
        user: null,
        permissions: [],
        currentPage: 'dashboard',
        sidebarOpen: true,
        theme: 'dark',
        language: 'zh',
      }
    },
    mutations: {
      setSystemInfo(state, info) {
        state.systemInfo = { ...state.systemInfo, ...info }
      },
      setToken(state, token) {
        state.token = token
        if (token) localStorage.setItem('token', token)
        else localStorage.removeItem('token')
      },
      setUser(state, user) {
        state.user = user
        if (user) localStorage.setItem('user', JSON.stringify(user))
        else localStorage.removeItem('user')
      },
      setPermissions(state, permissions) {
        state.permissions = Array.isArray(permissions) ? permissions : []
        if (state.permissions.length) localStorage.setItem('permissions', JSON.stringify(state.permissions))
        else localStorage.removeItem('permissions')
      },
      setCurrentPage(state, page) { state.currentPage = page },
      toggleSidebar(state) { state.sidebarOpen = !state.sidebarOpen },
      toggleTheme(state) {
        state.theme = state.theme === 'dark' ? 'light' : 'dark'
        localStorage.setItem('theme', state.theme)
      },
      setTheme(state, theme) {
        state.theme = theme
        localStorage.setItem('theme', theme)
      },
      setLanguage(state, language) {
        state.language = language
        localStorage.setItem('language', language)
      },
    },
    actions: {
      async login({ commit }, { username, password }) {
        try {
          const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
          })
          const data = await response.json()
          if (data.status === 'success') {
            commit('setToken', data.token)
            commit('setUser', { username: data.user.username, role: data.user.role })
            commit('setPermissions', data.user.permissions || [])
            return { success: true }
          } else if (data.status === '2fa_required') {
            return { success: false, twoFactorRequired: true, tempToken: data.temp_token }
          } else {
            return { success: false, message: data.message }
          }
        } catch (error) {
          return { success: false, message: error.message }
        }
      },
      async verify2FA({ commit }, { tempToken, verificationCode }) {
        try {
          const response = await fetch('/api/login/2fa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ temp_token: tempToken, verification_code: verificationCode }),
          })
          const data = await response.json()
          if (data.status === 'success') {
            commit('setToken', data.token)
            commit('setUser', { username: data.user.username, role: data.user.role })
            commit('setPermissions', data.user.permissions || [])
            return { success: true }
          } else {
            return { success: false, message: data.message }
          }
        } catch (error) {
          return { success: false, message: error.message }
        }
      },
      logout({ commit }) {
        commit('setToken', null)
        commit('setUser', null)
        commit('setPermissions', [])
      },
    },
    getters: {
      isLoggedIn: (state) => !!state.token,
      getUser: (state) => state.user,
      getPermissions: (state) => state.permissions,
      hasPermission: (state) => (permission) => hasPermission(state.permissions, permission),
    },
  })
}

describe('Vuex Store', () => {
  let store

  beforeEach(() => {
    // 每个测试前重置 localStorage
    localStorage.clear()
    store = createTestStore()
  })

  // ==================== Mutations ====================

  describe('mutations', () => {
    it('setToken 设置令牌并持久化到 localStorage', () => {
      store.commit('setToken', 'test-jwt-token')
      expect(store.state.token).toBe('test-jwt-token')
      expect(localStorage.getItem('token')).toBe('test-jwt-token')
    })

    it('setToken 传 null 清除令牌和 localStorage', () => {
      store.commit('setToken', 'test-jwt-token')
      store.commit('setToken', null)
      expect(store.state.token).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
    })

    it('setUser 设置用户并持久化', () => {
      const user = { username: 'admin', role: 'admin' }
      store.commit('setUser', user)
      expect(store.state.user).toEqual(user)
      expect(JSON.parse(localStorage.getItem('user'))).toEqual(user)
    })

    it('setUser 传 null 清除用户', () => {
      store.commit('setUser', { username: 'admin', role: 'admin' })
      store.commit('setUser', null)
      expect(store.state.user).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
    })

    it('setPermissions 设置权限并持久化', () => {
      const perms = ['user:view', 'file:view']
      store.commit('setPermissions', perms)
      expect(store.state.permissions).toEqual(perms)
      expect(JSON.parse(localStorage.getItem('permissions'))).toEqual(perms)
    })

    it('setPermissions 空数组清除 localStorage', () => {
      store.commit('setPermissions', ['user:view'])
      store.commit('setPermissions', [])
      expect(store.state.permissions).toEqual([])
      expect(localStorage.getItem('permissions')).toBeNull()
    })

    it('setPermissions 非数组输入转为空数组', () => {
      store.commit('setPermissions', 'not-an-array')
      expect(store.state.permissions).toEqual([])
    })

    it('setCurrentPage 更新当前页面', () => {
      store.commit('setCurrentPage', 'users')
      expect(store.state.currentPage).toBe('users')
    })

    it('toggleSidebar 切换侧边栏状态', () => {
      expect(store.state.sidebarOpen).toBe(true)
      store.commit('toggleSidebar')
      expect(store.state.sidebarOpen).toBe(false)
      store.commit('toggleSidebar')
      expect(store.state.sidebarOpen).toBe(true)
    })

    it('toggleTheme 在 dark/light 间切换', () => {
      expect(store.state.theme).toBe('dark')
      store.commit('toggleTheme')
      expect(store.state.theme).toBe('light')
      expect(localStorage.getItem('theme')).toBe('light')
      store.commit('toggleTheme')
      expect(store.state.theme).toBe('dark')
    })

    it('setLanguage 更新语言并持久化', () => {
      store.commit('setLanguage', 'en')
      expect(store.state.language).toBe('en')
      expect(localStorage.getItem('language')).toBe('en')
    })

    it('setSystemInfo 合并系统信息', () => {
      store.commit('setSystemInfo', { cpuUsage: 45.5, memoryUsage: 60 })
      expect(store.state.systemInfo.cpuUsage).toBe(45.5)
      expect(store.state.systemInfo.memoryUsage).toBe(60)
      // 未更新的字段保持不变
      expect(store.state.systemInfo.diskUsage).toBe(0)
    })
  })

  // ==================== Getters ====================

  describe('getters', () => {
    it('isLoggedIn 无令牌时返回 false', () => {
      expect(store.getters.isLoggedIn).toBe(false)
    })

    it('isLoggedIn 有令牌时返回 true', () => {
      store.commit('setToken', 'some-token')
      expect(store.getters.isLoggedIn).toBe(true)
    })

    it('getUser 返回当前用户', () => {
      const user = { username: 'admin', role: 'admin' }
      store.commit('setUser', user)
      expect(store.getters.getUser).toEqual(user)
    })

    it('getPermissions 返回权限列表', () => {
      store.commit('setPermissions', ['user:view'])
      expect(store.getters.getPermissions).toEqual(['user:view'])
    })

    it('hasPermission 通过 getter 调用', () => {
      store.commit('setPermissions', ['*:manage'])
      expect(store.getters.hasPermission('user:view')).toBe(true)
      expect(store.getters.hasPermission('user:delete')).toBe(true)
    })

    it('hasPermission 无权限时返回 false', () => {
      store.commit('setPermissions', ['*:view'])
      expect(store.getters.hasPermission('user:delete')).toBe(false)
    })
  })

  // ==================== Actions ====================

  describe('actions - login', () => {
    it('登录成功时设置 token/user/permissions', async () => {
      const mockResponse = {
        status: 'success',
        token: 'jwt-token-123',
        user: { username: 'admin', role: 'admin', permissions: ['*:manage'] },
      }
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await store.dispatch('login', { username: 'admin', password: 'pass' })
      expect(result.success).toBe(true)
      expect(store.state.token).toBe('jwt-token-123')
      expect(store.state.user).toEqual({ username: 'admin', role: 'admin' })
      expect(store.state.permissions).toEqual(['*:manage'])
    })

    it('2FA 启用时返回 twoFactorRequired', async () => {
      const mockResponse = {
        status: '2fa_required',
        temp_token: 'temp-abc',
      }
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await store.dispatch('login', { username: 'admin', password: 'pass' })
      expect(result.success).toBe(false)
      expect(result.twoFactorRequired).toBe(true)
      expect(result.tempToken).toBe('temp-abc')
      // 不应设置 token
      expect(store.state.token).toBeNull()
    })

    it('登录失败时返回错误消息', async () => {
      const mockResponse = { status: 'error', message: '密码错误' }
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await store.dispatch('login', { username: 'admin', password: 'wrong' })
      expect(result.success).toBe(false)
      expect(result.message).toBe('密码错误')
    })

    it('网络错误时返回错误', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))
      const result = await store.dispatch('login', { username: 'admin', password: 'pass' })
      expect(result.success).toBe(false)
      expect(result.message).toBe('Network error')
    })
  })

  describe('actions - verify2FA', () => {
    it('2FA 验证成功时设置 token/user', async () => {
      const mockResponse = {
        status: 'success',
        token: 'jwt-after-2fa',
        user: { username: 'admin', role: 'admin', permissions: ['*:manage'] },
      }
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await store.dispatch('verify2FA', {
        tempToken: 'temp-abc',
        verificationCode: '123456',
      })
      expect(result.success).toBe(true)
      expect(store.state.token).toBe('jwt-after-2fa')
    })

    it('2FA 验证失败时返回错误', async () => {
      const mockResponse = { status: 'error', message: '验证码错误' }
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await store.dispatch('verify2FA', {
        tempToken: 'temp-abc',
        verificationCode: '000000',
      })
      expect(result.success).toBe(false)
      expect(result.message).toBe('验证码错误')
    })
  })

  describe('actions - logout', () => {
    it('登出时清除所有认证状态', () => {
      // 先设置认证状态
      store.commit('setToken', 'some-token')
      store.commit('setUser', { username: 'admin', role: 'admin' })
      store.commit('setPermissions', ['*:manage'])

      // 登出
      store.dispatch('logout')

      expect(store.state.token).toBeNull()
      expect(store.state.user).toBeNull()
      expect(store.state.permissions).toEqual([])
      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('user')).toBeNull()
      expect(localStorage.getItem('permissions')).toBeNull()
    })
  })
})
