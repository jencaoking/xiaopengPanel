/**
 * 权限校验工具单元测试
 *
 * 测试范围：
 * - 完全匹配
 * - 通配符匹配（user:* / *:view / *:manage / *:*）
 * - manage 隐含 view/create/update/delete/execute
 * - execute/create/update/delete 隐含 view
 * - 边界情况（空值、无效格式）
 */
import { describe, it, expect } from 'vitest'
import { hasPermission } from '../../src/utils/permissions.js'

describe('hasPermission', () => {
  // ==================== 完全匹配 ====================

  it('完全匹配返回 true', () => {
    expect(hasPermission(['user:view'], 'user:view')).toBe(true)
    expect(hasPermission(['user:create', 'file:view'], 'file:view')).toBe(true)
  })

  it('不匹配返回 false', () => {
    expect(hasPermission(['user:view'], 'user:create')).toBe(false)
    expect(hasPermission(['file:view'], 'user:view')).toBe(false)
  })

  // ==================== 通配符匹配 ====================

  it('资源通配符 user:* 匹配所有 user 操作', () => {
    const perms = ['user:*']
    expect(hasPermission(perms, 'user:view')).toBe(true)
    expect(hasPermission(perms, 'user:create')).toBe(true)
    expect(hasPermission(perms, 'user:update')).toBe(true)
    expect(hasPermission(perms, 'user:delete')).toBe(true)
    expect(hasPermission(perms, 'user:manage')).toBe(true)
  })

  it('操作通配符 *:view 匹配所有资源的 view 操作', () => {
    const perms = ['*:view']
    expect(hasPermission(perms, 'user:view')).toBe(true)
    expect(hasPermission(perms, 'file:view')).toBe(true)
    expect(hasPermission(perms, 'system:view')).toBe(true)
    // 但不匹配 manage
    expect(hasPermission(perms, 'user:manage')).toBe(false)
  })

  it('超级权限 *:manage 匹配所有操作', () => {
    const perms = ['*:manage']
    expect(hasPermission(perms, 'user:view')).toBe(true)
    expect(hasPermission(perms, 'user:create')).toBe(true)
    expect(hasPermission(perms, 'user:manage')).toBe(true)
    expect(hasPermission(perms, 'file:delete')).toBe(true)
    expect(hasPermission(perms, 'system:execute')).toBe(true)
  })

  // ==================== manage 隐含 ====================

  it('manage 隐含 view/create/update/delete/execute', () => {
    const perms = ['file:manage']
    expect(hasPermission(perms, 'file:view')).toBe(true)
    expect(hasPermission(perms, 'file:create')).toBe(true)
    expect(hasPermission(perms, 'file:update')).toBe(true)
    expect(hasPermission(perms, 'file:delete')).toBe(true)
    expect(hasPermission(perms, 'file:execute')).toBe(true)
    // manage 隐含 manage
    expect(hasPermission(perms, 'file:manage')).toBe(true)
  })

  it('manage 不隐含其他资源的操作', () => {
    const perms = ['file:manage']
    expect(hasPermission(perms, 'user:view')).toBe(false)
    expect(hasPermission(perms, 'system:view')).toBe(false)
  })

  // ==================== execute/create/update/delete 隐含 view ====================

  it('execute 隐含 view', () => {
    expect(hasPermission(['terminal:execute'], 'terminal:view')).toBe(true)
  })

  it('create 隐含 view', () => {
    expect(hasPermission(['cron:create'], 'cron:view')).toBe(true)
  })

  it('update 隐含 view', () => {
    expect(hasPermission(['site:update'], 'site:view')).toBe(true)
  })

  it('delete 隐含 view', () => {
    expect(hasPermission(['log:delete'], 'log:view')).toBe(true)
  })

  it('execute 不隐含 create', () => {
    expect(hasPermission(['terminal:execute'], 'terminal:create')).toBe(false)
  })

  // ==================== 边界情况 ====================

  it('空权限列表返回 false', () => {
    expect(hasPermission([], 'user:view')).toBe(false)
  })

  it('null/undefined 权限列表返回 false', () => {
    expect(hasPermission(null, 'user:view')).toBe(false)
    expect(hasPermission(undefined, 'user:view')).toBe(false)
  })

  it('空/null 权限参数返回 false', () => {
    expect(hasPermission(['user:view'], '')).toBe(false)
    expect(hasPermission(['user:view'], null)).toBe(false)
    expect(hasPermission(['user:view'], undefined)).toBe(false)
  })

  it('多个权限组合正确匹配', () => {
    const perms = ['*:view', 'process:manage', 'terminal:execute']
    // *:view 覆盖
    expect(hasPermission(perms, 'user:view')).toBe(true)
    // process:manage 隐含
    expect(hasPermission(perms, 'process:create')).toBe(true)
    // terminal:execute 隐含 view
    expect(hasPermission(perms, 'terminal:view')).toBe(true)
    // 不在权限中
    expect(hasPermission(perms, 'user:delete')).toBe(false)
  })

  it('模拟 admin 角色权限', () => {
    const adminPerms = ['*:manage']
    expect(hasPermission(adminPerms, 'user:view')).toBe(true)
    expect(hasPermission(adminPerms, 'user:delete')).toBe(true)
    expect(hasPermission(adminPerms, 'system:manage')).toBe(true)
    // *:manage 仅隐含 view/create/update/delete/execute，不匹配未识别的操作
    expect(hasPermission(adminPerms, 'anything:view')).toBe(true)
    expect(hasPermission(adminPerms, 'anything:create')).toBe(true)
  })

  it('模拟 viewer 角色权限', () => {
    const viewerPerms = ['*:view']
    expect(hasPermission(viewerPerms, 'user:view')).toBe(true)
    expect(hasPermission(viewerPerms, 'file:view')).toBe(true)
    expect(hasPermission(viewerPerms, 'user:create')).toBe(false)
    expect(hasPermission(viewerPerms, 'user:delete')).toBe(false)
  })

  it('模拟 operator 角色权限', () => {
    const operatorPerms = [
      'dashboard:view', 'system:view', 'monitor:view',
      'process:manage', 'service:manage', 'file:manage',
      'site:manage', 'database:manage', 'log:view',
      'web_service:manage', 'terminal:execute', 'editor:view',
      'cron:manage', 'ai:view', 'ai:execute',
    ]
    // 有权限
    expect(hasPermission(operatorPerms, 'process:view')).toBe(true)
    expect(hasPermission(operatorPerms, 'process:create')).toBe(true) // manage 隐含
    expect(hasPermission(operatorPerms, 'terminal:view')).toBe(true) // execute 隐含
    // 无权限
    expect(hasPermission(operatorPerms, 'user:view')).toBe(false)
    expect(hasPermission(operatorPerms, 'user:create')).toBe(false)
  })

  it('模拟 auditor 角色权限', () => {
    const auditorPerms = ['dashboard:view', 'system:view', 'monitor:view', 'log:view']
    expect(hasPermission(auditorPerms, 'log:view')).toBe(true)
    expect(hasPermission(auditorPerms, 'system:view')).toBe(true)
    expect(hasPermission(auditorPerms, 'file:view')).toBe(false)
    expect(hasPermission(auditorPerms, 'user:view')).toBe(false)
  })
})
