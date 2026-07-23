/**
 * 权限校验工具
 *
 * 从 main.js 的 Vuex getter 中抽离，便于单元测试。
 * 支持通配符匹配：'user:*'、'*:view'、'*:manage'、'*:*'
 * manage 隐含 view/create/update/delete/execute；execute/create/update/delete 隐含 view。
 */

/**
 * 检查当前权限列表是否包含指定权限
 * @param {string[]} permissions - 用户拥有的权限列表
 * @param {string} permission - 待校验权限，格式 "资源:操作"
 * @returns {boolean}
 */
export function hasPermission(permissions, permission) {
  if (!permission || !permissions || !permissions.length) return false

  // 完全匹配
  if (permissions.includes(permission)) return true

  const [res, act] = permission.split(':')

  for (const p of permissions) {
    if (p === permission) return true
    const [pr, pa] = p.split(':')
    // 通配符匹配
    if ((pr === '*' || pr === res) && (pa === '*' || pa === act)) return true
    // manage 隐含 view/create/update/delete/execute
    if (pa === 'manage' && ['view', 'create', 'update', 'delete', 'execute'].includes(act) && (pr === '*' || pr === res)) return true
    // execute/create/update/delete 隐含 view
    if (['execute', 'create', 'update', 'delete'].includes(pa) && act === 'view' && (pr === '*' || pr === res)) return true
  }
  return false
}

export default hasPermission
