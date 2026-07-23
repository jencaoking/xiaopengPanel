<template>
  <div id="roles" class="page roles-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-title">
        <h2>{{ $t('roles.title') }}</h2>
        <p class="page-subtitle">{{ $t('roles.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="fetchData" :disabled="loading">
          <svg v-if="loading" class="icon-spin" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
          </svg>
          <span v-else>{{ $t('common.refresh') }}</span>
        </button>
        <button
          v-if="canCreate"
          class="btn btn-primary"
          @click="showAddModal"
        >
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
          </svg>
          {{ $t('roles.addRole') }}
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
            <path fill="currentColor" d="M12 2l-5.5 2.5v6c0 3.5 2.5 6.5 5.5 7.5 3-1 5.5-4 5.5-7.5v-6L12 2z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('roles.totalRoles') }}</span>
          <span class="card-value">{{ roleList.length }}</span>
        </div>
      </div>
      <div class="status-card glass-card">
        <div class="card-icon icon-custom">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M3 5v14h18V5H3zm16 12H5V7h14v10zM7 9h10v2H7zm0 4h7v2H7z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('roles.customRoles') }}</span>
          <span class="card-value">{{ customCount }}</span>
        </div>
      </div>
      <div class="status-card glass-card">
        <div class="card-icon icon-system">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('roles.builtinRoles') }}</span>
          <span class="card-value">{{ systemCount }}</span>
        </div>
      </div>
      <div class="status-card glass-card">
        <div class="card-icon icon-perms">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 14l-2-2 1.41-1.41L11 12.17l4.59-4.59L17 9l-6 6z"/>
          </svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('roles.totalPermissions') }}</span>
          <span class="card-value">{{ totalPermissionDefs }}</span>
        </div>
      </div>
    </div>

    <!-- 角色列表 -->
    <div class="section-header">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" width="20" height="20" class="section-icon">
          <path fill="currentColor" d="M12 2l-5.5 2.5v6c0 3.5 2.5 6.5 5.5 7.5 3-1 5.5-4 5.5-7.5v-6L12 2z"/>
        </svg>
        {{ $t('roles.roleList') }}
      </h3>
    </div>

    <div v-if="loading && roleList.length === 0" class="loading-state">
      <div class="ios-spinner"></div>
      <span>{{ $t('common.loading') }}</span>
    </div>

    <div v-else-if="roleList.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" width="48" height="48">
        <path fill="currentColor" d="M12 2l-5.5 2.5v6c0 3.5 2.5 6.5 5.5 7.5 3-1 5.5-4 5.5-7.5v-6L12 2z" opacity="0.4"/>
      </svg>
      <p>{{ $t('roles.noRoles') }}</p>
    </div>

    <div v-else class="roles-grid">
      <div
        v-for="role in roleList"
        :key="role.key"
        class="role-card glass-card"
        :class="{ 'role-system': role.is_system }"
      >
        <div class="role-card-header">
          <div class="role-meta">
            <h4 class="role-name">{{ role.name }}</h4>
            <div class="role-key-row">
              <code class="role-key">{{ role.key }}</code>
              <span :class="['role-badge', role.is_system ? 'badge-system' : 'badge-custom']">
                {{ role.is_system ? $t('roles.builtin') : $t('roles.custom') }}
              </span>
            </div>
          </div>
          <div class="role-perm-count">
            <span class="perm-count-num">{{ role.permissions.length }}</span>
            <span class="perm-count-label">{{ $t('roles.permissions') }}</span>
          </div>
        </div>

        <p class="role-description">{{ role.description || $t('roles.noDescription') }}</p>

        <div class="role-perms-preview">
          <span
            v-for="perm in previewPermissions(role.permissions)"
            :key="perm"
            class="perm-chip"
          >{{ perm }}</span>
          <span v-if="role.permissions.length > previewLimit" class="perm-chip perm-more">
            +{{ role.permissions.length - previewLimit }}
          </span>
        </div>

        <div class="role-actions">
          <button
            v-if="canUpdate"
            class="btn btn-secondary btn-sm"
            @click="editRole(role)"
          >
            <svg viewBox="0 0 24 24" width="14" height="14">
              <path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
            {{ $t('common.edit') }}
          </button>
          <button
            v-if="canDelete && !role.is_system"
            class="btn btn-danger btn-sm"
            @click="confirmDelete(role)"
          >
            <svg viewBox="0 0 24 24" width="14" height="14">
              <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
            </svg>
            {{ $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑角色模态框 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-container modal-large">
        <div class="modal-header">
          <h3>{{ isEditing ? $t('roles.editRole') : $t('roles.addRole') }}</h3>
          <button class="close-btn" @click="closeModal" aria-label="close">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveRole">
            <div class="form-grid">
              <div class="form-group">
                <label for="role-key">{{ $t('roles.roleKey') }}</label>
                <input
                  type="text"
                  id="role-key"
                  v-model="formData.key"
                  :disabled="isEditing"
                  :placeholder="$t('roles.roleKeyPlaceholder')"
                  required
                  pattern="[a-zA-Z_][a-zA-Z0-9_]*"
                >
                <small class="form-hint">{{ $t('roles.roleKeyHint') }}</small>
              </div>
              <div class="form-group">
                <label for="role-name">{{ $t('roles.roleName') }}</label>
                <input
                  type="text"
                  id="role-name"
                  v-model="formData.name"
                  :placeholder="$t('roles.roleNamePlaceholder')"
                  required
                >
              </div>
            </div>
            <div class="form-group">
              <label for="role-desc">{{ $t('roles.description') }}</label>
              <input
                type="text"
                id="role-desc"
                v-model="formData.description"
                :placeholder="$t('roles.descriptionPlaceholder')"
              >
            </div>

            <!-- 权限矩阵 -->
            <div class="perm-matrix-section">
              <div class="perm-matrix-header">
                <h4>{{ $t('roles.permissionMatrix') }}</h4>
                <div v-if="!isEditing || !editingSystemRole" class="perm-bulk-actions">
                  <button type="button" class="btn-link" @click="selectAllManage">{{ $t('roles.selectAllManage') }}</button>
                  <button type="button" class="btn-link" @click="selectAllView">{{ $t('roles.selectAllView') }}</button>
                  <button type="button" class="btn-link danger" @click="clearAll">{{ $t('roles.clearAll') }}</button>
                </div>
              </div>

              <div v-if="isEditing && editingSystemRole" class="alert alert-info">
                <svg viewBox="0 0 24 24" width="18" height="18" class="alert-icon">
                  <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
                </svg>
                <span>{{ $t('roles.systemRolePermLocked') }}</span>
              </div>

              <div class="perm-matrix-wrapper">
                <table class="perm-matrix">
                  <thead>
                    <tr>
                      <th class="perm-resource-col">{{ $t('roles.resource') }}</th>
                      <th v-for="act in actionList" :key="act.key" class="perm-action-col">
                        {{ $t('roles.actions.' + act.key) || act.label }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="res in resourceList" :key="res.key">
                      <td class="perm-resource-col">
                        <span class="resource-label">{{ $t('roles.resources.' + res.key) || res.label }}</span>
                      </td>
                      <td v-for="act in actionList" :key="act.key" class="perm-cell">
                        <label class="perm-checkbox">
                          <input
                            type="checkbox"
                            :checked="hasPerm(res.key, act.key)"
                            :disabled="isEditing && editingSystemRole"
                            @change="togglePerm(res.key, act.key, $event.target.checked)"
                          >
                          <span class="check-mark"></span>
                        </label>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="closeModal">{{ $t('common.cancel') }}</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting || (isEditing && editingSystemRole && !formData.name)">
                {{ submitting ? $t('common.loading') : $t('common.save') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 删除确认模态框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-container">
        <div class="modal-header">
          <h3>{{ $t('roles.confirmDeleteTitle') }}</h3>
          <button class="close-btn" @click="showDeleteModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="delete-warning">{{ $t('roles.confirmDeleteMsg', { name: deleteTarget ? deleteTarget.name : '' }) }}</p>
          <div v-if="deleteError" class="alert alert-error">
            <span>{{ deleteError }}</span>
          </div>
          <div class="form-actions">
            <button class="btn btn-secondary" @click="showDeleteModal = false">{{ $t('common.cancel') }}</button>
            <button class="btn btn-danger" :disabled="submitting" @click="doDelete">
              {{ submitting ? $t('common.loading') : $t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Roles',
  data() {
    return {
      roles: {},
      permissionsDef: { resources: {}, actions: {} },
      loading: false,
      submitting: false,
      error: null,
      showModal: false,
      isEditing: false,
      editingSystemRole: false,
      formData: {
        key: '',
        name: '',
        description: '',
        permissions: []
      },
      showDeleteModal: false,
      deleteTarget: null,
      deleteError: null,
      previewLimit: 4
    }
  },
  computed: {
    roleList() {
      return Object.values(this.roles).sort((a, b) => {
        // 内置角色排前面，自定义角色按名称排序
        if (a.is_system && !b.is_system) return -1
        if (!a.is_system && b.is_system) return 1
        return a.name.localeCompare(b.name)
      })
    },
    resourceList() {
      return Object.entries(this.permissionsDef.resources || {}).map(([key, label]) => ({ key, label }))
    },
    actionList() {
      return Object.entries(this.permissionsDef.actions || {}).map(([key, label]) => ({ key, label }))
    },
    customCount() {
      return this.roleList.filter(r => !r.is_system).length
    },
    systemCount() {
      return this.roleList.filter(r => r.is_system).length
    },
    totalPermissionDefs() {
      return this.resourceList.length * this.actionList.length
    },
    canCreate() {
      return this.$store.getters.hasPermission('role:create')
    },
    canUpdate() {
      return this.$store.getters.hasPermission('role:update')
    },
    canDelete() {
      return this.$store.getters.hasPermission('role:delete')
    }
  },
  mounted() {
    this.fetchData()
  },
  methods: {
    async fetchData() {
      this.loading = true
      this.error = null
      try {
        const [rolesRes, permsRes] = await Promise.all([
          this.$store.dispatch('apiRequest', { url: '/api/roles', method: 'GET' }),
          this.$store.dispatch('apiRequest', { url: '/api/permissions', method: 'GET' })
        ])
        if (rolesRes.status === 'success') {
          this.roles = rolesRes.roles || {}
        } else {
          this.error = rolesRes.message
        }
        if (permsRes.status === 'success') {
          this.permissionsDef = permsRes.permissions || { resources: {}, actions: {} }
        }
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    previewPermissions(perms) {
      return perms.slice(0, this.previewLimit)
    },
    hasPerm(res, act) {
      return this.formData.permissions.includes(`${res}:${act}`)
    },
    /**
     * 切换某项权限。勾选 manage 时自动勾选该资源全部操作；
     * 取消 view 时若其他操作仍勾选则保留 view（因后者隐含 view，后端会放行）。
     */
    togglePerm(res, act, checked) {
      const perm = `${res}:${act}`
      const set = new Set(this.formData.permissions)
      if (checked) {
        set.add(perm)
        if (act === 'manage') {
          // manage 隐含全部操作，自动勾选
          this.actionList.forEach(a => set.add(`${res}:${a.key}`))
        }
      } else {
        set.delete(perm)
        if (act === 'manage') {
          // 取消 manage 仅移除 manage，保留细粒度操作
        } else {
          // 取消细粒度操作时，若该资源已勾选 manage，需同时取消 manage（避免语义冲突）
          set.delete(`${res}:manage`)
        }
      }
      this.formData.permissions = Array.from(set)
    },
    selectAllManage() {
      this.formData.permissions = this.resourceList.map(r => `${r.key}:manage`)
    },
    selectAllView() {
      this.formData.permissions = this.resourceList.map(r => `${r.key}:view`)
    },
    clearAll() {
      this.formData.permissions = []
    },
    showAddModal() {
      this.isEditing = false
      this.editingSystemRole = false
      this.formData = { key: '', name: '', description: '', permissions: [] }
      this.showModal = true
    },
    editRole(role) {
      this.isEditing = true
      this.editingSystemRole = !!role.is_system
      this.formData = {
        key: role.key,
        name: role.name,
        description: role.description || '',
        permissions: [...(role.permissions || [])]
      }
      this.showModal = true
    },
    closeModal() {
      this.showModal = false
    },
    async saveRole() {
      this.submitting = true
      try {
        let res
        if (this.isEditing) {
          // 内置角色不允许改权限（后端会拒绝），仅提交名称和描述
          const body = { name: this.formData.name, description: this.formData.description }
          if (!this.editingSystemRole) {
            body.permissions = this.formData.permissions
          }
          res = await this.$store.dispatch('apiRequest', {
            url: `/api/roles/${encodeURIComponent(this.formData.key)}`,
            method: 'PUT',
            body
          })
        } else {
          res = await this.$store.dispatch('apiRequest', {
            url: '/api/roles',
            method: 'POST',
            body: {
              key: this.formData.key,
              name: this.formData.name,
              description: this.formData.description,
              permissions: this.formData.permissions
            }
          })
        }
        if (res.status === 'success') {
          this.showModal = false
          this.fetchData()
        } else {
          alert(res.message)
        }
      } catch (e) {
        alert(e.message)
      } finally {
        this.submitting = false
      }
    },
    confirmDelete(role) {
      this.deleteTarget = role
      this.deleteError = null
      this.showDeleteModal = true
    },
    async doDelete() {
      if (!this.deleteTarget) return
      this.submitting = true
      this.deleteError = null
      try {
        const res = await this.$store.dispatch('apiRequest', {
          url: `/api/roles/${encodeURIComponent(this.deleteTarget.key)}`,
          method: 'DELETE'
        })
        if (res.status === 'success') {
          this.showDeleteModal = false
          this.deleteTarget = null
          this.fetchData()
        } else {
          this.deleteError = res.message
        }
      } catch (e) {
        this.deleteError = e.message
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style scoped>
/* 页面容器 */
.roles-page {
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
  transition: var(--ios-theme-transition);
}

/* 状态卡片 */
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
.icon-custom { background: rgba(88, 86, 214, 0.15); color: #5856D6; }
.icon-system { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.icon-perms { background: rgba(255, 149, 0, 0.15); color: var(--ios-orange); }

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

/* 段落标题 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0;
}

.section-icon { color: var(--ios-blue); }

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-2) var(--ios-space-4);
  border: none;
  border-radius: var(--ios-radius-md);
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  cursor: pointer;
  transition: all var(--ios-transition-fast);
  text-decoration: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--ios-space-1) var(--ios-space-3);
  font-size: var(--ios-text-caption1);
}

.btn-primary {
  background: var(--ios-blue);
  color: white;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: #0066d6;
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
  transform: translateY(-1px);
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
  background: #d70015;
}

/* 链接按钮 */
.btn-link {
  background: none;
  border: none;
  color: var(--ios-blue);
  font-size: var(--ios-text-caption1);
  cursor: pointer;
  padding: var(--ios-space-1) var(--ios-space-2);
  border-radius: var(--ios-radius-sm);
  transition: background var(--ios-transition-fast);
}

.btn-link:hover {
  background: rgba(0, 122, 255, 0.1);
}

.btn-link.danger {
  color: var(--ios-red);
}

.btn-link.danger:hover {
  background: rgba(255, 59, 48, 0.1);
}

/* 加载/空状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ios-space-3);
  padding: var(--ios-space-8) var(--ios-space-4);
  color: var(--ios-label-secondary);
}

.empty-state svg {
  color: var(--ios-label-tertiary);
}

.ios-spinner {
  width: 28px;
  height: 28px;
  border: 2.5px solid var(--ios-fill-tertiary);
  border-top-color: var(--ios-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.icon-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 角色卡片网格 */
.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--ios-space-4);
}

.role-card {
  padding: var(--ios-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-3);
}

.role-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--ios-shadow-lg), inset 0 1px 0 0 var(--ios-glass-highlight);
}

.role-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ios-space-3);
}

.role-meta {
  flex: 1;
  min-width: 0;
}

.role-name {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0 0 var(--ios-space-1) 0;
}

.role-key-row {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  flex-wrap: wrap;
}

.role-key {
  font-family: 'SF Mono', 'Monaco', monospace;
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-secondary);
  background: var(--ios-fill-tertiary);
  padding: 2px var(--ios-space-2);
  border-radius: var(--ios-radius-sm);
}

.role-badge {
  font-size: var(--ios-text-caption2);
  padding: 2px var(--ios-space-2);
  border-radius: var(--ios-radius-full);
  font-weight: var(--ios-weight-medium);
}

.badge-system {
  background: rgba(52, 199, 89, 0.15);
  color: var(--ios-green);
}

.badge-custom {
  background: rgba(88, 86, 214, 0.15);
  color: #5856D6;
}

.role-perm-count {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ios-space-2) var(--ios-space-3);
  background: var(--ios-fill-tertiary);
  border-radius: var(--ios-radius-md);
  flex-shrink: 0;
}

.perm-count-num {
  font-size: var(--ios-text-title3);
  font-weight: var(--ios-weight-bold);
  color: var(--ios-label-primary);
}

.perm-count-label {
  font-size: var(--ios-text-caption2);
  color: var(--ios-label-tertiary);
}

.role-description {
  font-size: var(--ios-text-subhead);
  color: var(--ios-label-secondary);
  margin: 0;
  line-height: 1.4;
}

.role-perms-preview {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ios-space-1);
}

.perm-chip {
  font-size: var(--ios-text-caption2);
  padding: 2px var(--ios-space-2);
  border-radius: var(--ios-radius-sm);
  background: var(--ios-fill-quaternary);
  color: var(--ios-label-secondary);
  font-family: 'SF Mono', 'Monaco', monospace;
}

.perm-more {
  background: rgba(0, 122, 255, 0.1);
  color: var(--ios-blue);
}

.role-actions {
  display: flex;
  gap: var(--ios-space-2);
  margin-top: auto;
  padding-top: var(--ios-space-2);
  border-top: 0.5px solid var(--ios-separator);
}

/* 模态框 */
.modal-overlay {
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
  animation: fadeIn var(--ios-duration-fast) var(--ios-ease-out);
}

.modal-container {
  background: var(--ios-glass-bg);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-xl);
  box-shadow: var(--ios-shadow-xl), inset 0 1px 0 0 var(--ios-glass-highlight);
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  animation: slideUp var(--ios-duration-normal) var(--ios-ease-spring);
}

.modal-large {
  max-width: 880px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-space-5);
  border-bottom: 0.5px solid var(--ios-separator);
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
  border: none;
  border-radius: var(--ios-radius-full);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-secondary);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: all var(--ios-transition-fast);
}

.close-btn:hover {
  background: var(--ios-fill-secondary);
  color: var(--ios-label-primary);
}

.modal-body {
  padding: var(--ios-space-5);
  overflow-y: auto;
}

/* 表单 */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ios-space-4);
  margin-bottom: var(--ios-space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--ios-space-1);
  margin-bottom: var(--ios-space-4);
}

.form-group label {
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
  color: var(--ios-label-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: var(--ios-space-2) var(--ios-space-3);
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-md);
  background: var(--ios-fill-tertiary);
  color: var(--ios-label-primary);
  font-size: var(--ios-text-body);
  outline: none;
  transition: all var(--ios-transition-fast);
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--ios-blue);
  background: var(--ios-fill-secondary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2);
}

.form-group input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-hint {
  font-size: var(--ios-text-caption1);
  color: var(--ios-label-tertiary);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--ios-space-3);
  padding-top: var(--ios-space-4);
  border-top: 0.5px solid var(--ios-separator);
}

/* 权限矩阵 */
.perm-matrix-section {
  margin-top: var(--ios-space-4);
}

.perm-matrix-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ios-space-2);
  margin-bottom: var(--ios-space-3);
}

.perm-matrix-header h4 {
  font-size: var(--ios-text-headline);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-primary);
  margin: 0;
}

.perm-bulk-actions {
  display: flex;
  gap: var(--ios-space-1);
}

.perm-matrix-wrapper {
  border: 0.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-lg);
  overflow: auto;
  max-height: 400px;
}

.perm-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--ios-text-subhead);
}

.perm-matrix thead {
  position: sticky;
  top: 0;
  background: var(--ios-fill-tertiary);
  z-index: 1;
}

.perm-matrix th {
  padding: var(--ios-space-2) var(--ios-space-3);
  text-align: left;
  font-size: var(--ios-text-caption1);
  font-weight: var(--ios-weight-semibold);
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 0.5px solid var(--ios-separator);
  white-space: nowrap;
}

.perm-resource-col {
  min-width: 120px;
}

.perm-action-col {
  text-align: center;
  min-width: 60px;
}

.perm-matrix td {
  padding: var(--ios-space-1) var(--ios-space-3);
  border-bottom: 0.5px solid var(--ios-separator);
  color: var(--ios-label-primary);
}

.perm-matrix tbody tr:hover {
  background: var(--ios-fill-quaternary);
}

.resource-label {
  font-size: var(--ios-text-subhead);
  font-weight: var(--ios-weight-medium);
}

.perm-cell {
  text-align: center;
}

/* 复选框样式 */
.perm-checkbox {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
}

.perm-checkbox input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.check-mark {
  width: 20px;
  height: 20px;
  border: 1.5px solid var(--ios-glass-border);
  border-radius: var(--ios-radius-sm);
  background: var(--ios-fill-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--ios-transition-fast);
}

.perm-checkbox input:checked + .check-mark {
  background: var(--ios-blue);
  border-color: var(--ios-blue);
}

.perm-checkbox input:checked + .check-mark::after {
  content: '';
  width: 6px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
  margin-bottom: 2px;
}

.perm-checkbox input:disabled + .check-mark {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 提示 */
.alert {
  display: flex;
  align-items: center;
  gap: var(--ios-space-2);
  padding: var(--ios-space-3) var(--ios-space-4);
  border-radius: var(--ios-radius-md);
  font-size: var(--ios-text-subhead);
  margin-bottom: var(--ios-space-3);
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

.delete-warning {
  color: var(--ios-label-primary);
  line-height: 1.5;
  margin: 0 0 var(--ios-space-3) 0;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .roles-grid {
    grid-template-columns: 1fr;
  }

  .perm-matrix-wrapper {
    max-height: 320px;
  }
}
</style>
