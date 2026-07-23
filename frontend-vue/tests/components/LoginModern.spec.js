/**
 * LoginModern 组件测试
 *
 * 测试范围：
 * - 表单渲染与初始状态
 * - 表单校验（isValid computed）
 * - 登录流程（成功、失败、2FA）
 * - 密码可见性切换
 * - 2FA 验证流程
 * - 2FA 取消
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import LoginModern from '../../src/components/LoginModern.vue'

function createMockStore(loginResult = { success: true }) {
  return createStore({
    state: {
      token: null,
      user: null,
      permissions: [],
      currentPage: 'login',
    },
    actions: {
      login: vi.fn().mockResolvedValue(loginResult),
      verify2FA: vi.fn().mockResolvedValue({ success: true }),
    },
    mutations: {
      setCurrentPage(state, page) { state.currentPage = page },
    },
  })
}

function mountLogin(store = createMockStore()) {
  return mount(LoginModern, {
    global: {
      plugins: [store],
      stubs: {
        // 跳过 i18n 指令依赖
        teleport: true,
      },
    },
  })
}

describe('LoginModern', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mountLogin()
  })

  // ==================== 表单渲染 ====================

  it('渲染登录标题与副标题', () => {
    expect(wrapper.find('.login-title').text()).toBe('小鹏面板')
    expect(wrapper.find('.login-subtitle').text()).toBe('服务器运维管理系统')
  })

  it('渲染用户名和密码输入框', () => {
    expect(wrapper.find('#username').exists()).toBe(true)
    expect(wrapper.find('#password').exists()).toBe(true)
  })

  it('渲染登录按钮', () => {
    const btn = wrapper.find('.btn-login')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('登录')
  })

  it('初始状态下不显示 2FA 表单', () => {
    expect(wrapper.find('.tfa-section').exists()).toBe(false)
  })

  it('初始状态下 loading 为 false 且无错误', () => {
    expect(wrapper.vm.loading).toBe(false)
    expect(wrapper.vm.error).toBeNull()
  })

  // ==================== 表单校验 ====================

  it('isValid 在用户名和密码都填写时为 true', async () => {
    await wrapper.find('#username').setValue('admin')
    await wrapper.find('#password').setValue('password')
    expect(wrapper.vm.isValid).toBeTruthy()
  })

  it('isValid 在用户名为空时为 false', async () => {
    await wrapper.find('#password').setValue('password')
    expect(wrapper.vm.isValid).toBeFalsy()
  })

  it('isValid 在密码为空时为 false', async () => {
    await wrapper.find('#username').setValue('admin')
    expect(wrapper.vm.isValid).toBeFalsy()
  })

  it('isValid 对空白用户名返回 false（trim）', async () => {
    await wrapper.find('#username').setValue('   ')
    await wrapper.find('#password').setValue('password')
    expect(wrapper.vm.isValid).toBeFalsy()
  })

  // ==================== 密码可见性 ====================

  it('点击密码可见性按钮切换类型', async () => {
    const passwordInput = wrapper.find('#password')
    expect(passwordInput.attributes('type')).toBe('password')

    await wrapper.find('.password-toggle').trigger('click')
    expect(passwordInput.attributes('type')).toBe('text')

    await wrapper.find('.password-toggle').trigger('click')
    expect(passwordInput.attributes('type')).toBe('password')
  })

  // ==================== 登录流程 ====================

  it('登录成功时调用 store login action', async () => {
    const store = wrapper.vm.$store
    const dispatchSpy = vi.spyOn(store, 'dispatch')
    wrapper.vm.form.username = 'admin'
    wrapper.vm.form.password = 'Test@123456'
    await wrapper.vm.handleLogin()
    await wrapper.vm.$nextTick()

    expect(dispatchSpy).toHaveBeenCalledWith('login', {
      username: 'admin',
      password: 'Test@123456',
    })
  })

  it('登录成功后切换到 dashboard 页面', async () => {
    const store = wrapper.vm.$store
    wrapper.vm.form.username = 'admin'
    wrapper.vm.form.password = 'Test@123456'
    await wrapper.vm.handleLogin()

    expect(store.state.currentPage).toBe('dashboard')
  })

  it('需要 2FA 时显示验证码输入表单', async () => {
    const twoFactorResult = { success: false, twoFactorRequired: true, tempToken: 'temp-abc' }
    const store = createMockStore(twoFactorResult)
    wrapper = mountLogin(store)

    wrapper.vm.form.username = 'admin'
    wrapper.vm.form.password = 'Test@123456'
    await wrapper.vm.handleLogin()

    expect(wrapper.vm.twoFactorRequired).toBe(true)
    expect(wrapper.vm.tempToken).toBe('temp-abc')
    expect(wrapper.find('.tfa-section').exists()).toBe(true)
  })

  it('登录失败时显示错误消息', async () => {
    const failResult = { success: false, message: '用户名或密码错误' }
    const store = createMockStore(failResult)
    wrapper = mountLogin(store)

    wrapper.vm.form.username = 'admin'
    wrapper.vm.form.password = 'wrong'
    await wrapper.vm.handleLogin()

    expect(wrapper.vm.error).toBe('用户名或密码错误')
  })

  // ==================== 2FA 取消 ====================

  it('cancel2FA 重置 2FA 状态', async () => {
    // 先进入 2FA 模式
    const twoFactorResult = { success: false, twoFactorRequired: true, tempToken: 'temp-abc' }
    const store = createMockStore(twoFactorResult)
    wrapper = mountLogin(store)

    await wrapper.find('#username').setValue('admin')
    await wrapper.find('#password').setValue('Test@123456')
    await wrapper.find('.login-form').trigger('submit.prevent')
    await new Promise(r => setTimeout(r, 0))

    expect(wrapper.vm.twoFactorRequired).toBe(true)

    // 取消 2FA
    wrapper.vm.cancel2FA()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.twoFactorRequired).toBe(false)
    expect(wrapper.vm.tempToken).toBeNull()
    expect(wrapper.vm.error).toBeNull()
  })

  // ==================== 表单数据绑定 ====================

  it('输入用户名更新 form.username', async () => {
    await wrapper.find('#username').setValue('testuser')
    expect(wrapper.vm.form.username).toBe('testuser')
  })

  it('输入密码更新 form.password', async () => {
    await wrapper.find('#password').setValue('mypass123')
    expect(wrapper.vm.form.password).toBe('mypass123')
  })

  it('勾选记住我更新 form.rememberMe', async () => {
    const toggle = wrapper.find('.ios-toggle-input')
    await toggle.setValue(true)
    expect(wrapper.vm.form.rememberMe).toBe(true)
  })

  // ==================== 2FA 输入 ====================

  it('tfaCode 初始为 6 个空字符串', () => {
    expect(wrapper.vm.tfaCode).toEqual(['', '', '', '', '', ''])
    expect(wrapper.vm.tfaCode.length).toBe(6)
  })

  it('onTfaInput 只保留数字', () => {
    wrapper.vm.onTfaInput(1, { target: { value: 'a1b2c3' } })
    expect(wrapper.vm.tfaCode[0]).toBe('123')
  })

  it('onTfaPaste 从剪贴板提取 6 位数字', () => {
    const event = {
      preventDefault: vi.fn(),
      clipboardData: { getData: () => '123456' },
    }
    wrapper.vm.onTfaPaste(event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(wrapper.vm.tfaCode).toEqual(['1', '2', '3', '4', '5', '6'])
  })

  it('onTfaPaste 超过 6 位时只取前 6 位', () => {
    const event = {
      preventDefault: vi.fn(),
      clipboardData: { getData: () => '123456789' },
    }
    wrapper.vm.onTfaPaste(event)
    expect(wrapper.vm.tfaCode).toEqual(['1', '2', '3', '4', '5', '6'])
  })
})
