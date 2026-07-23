<template>
  <div id="users" class="page users-page">
    <div class="page-header">
      <div class="header-title">
        <h2>{{ $t('users.title') }}</h2>
        <p class="page-subtitle">{{ $t('users.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="fetchData" :disabled="loading">
          <svg v-if="loading" class="icon-spin" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
          </svg>
          <span v-else>{{ $t('common.refresh') }}</span>
        </button>
        <button v-if="canCreate" class="btn btn-primary" @click="showAddUserModal">
          <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
          {{ $t('users.addUser') }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">
      <svg viewBox="0 0 24 24" width="20" height="20" class="alert-icon">
        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
      </svg>
      <span>{{ error }}</span>
    </div>

    <div class="status-cards">
      <div class="status-card glass-card">
        <div class="card-icon icon-total">
          <svg viewBox="0 0 24 24" width="28" height="28"><path fill="currentColor" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('users.totalUsers') }}</span>
          <span class="card-value">{{ users.length }}</span>
        </div>
      </div>
      <div class="status-card glass-card">
        <div class="card-icon icon-active">
          <svg viewBox="0 0 24 24" width="28" height="28"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('users.activeUsers') }}</span>
          <span class="card-value text-success">{{ activeCount }}</span>
        </div>
      </div>
      <div class="status-card glass-card">
        <div class="card-icon icon-disabled">
          <svg viewBox="0 0 24 24" width="28" height="28"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </div>
        <div class="card-info">
          <span class="card-label">{{ $t('users.disabledUsers') }}</span>
          <span class="card-value text-danger">{{ disabledCount }}</span>
        </div>
      </div>
    </div>

    <div class="section-header">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" width="20" height="20" class="section-icon"><path fill="currentColor" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
        {{ $t('users.userList') }}
      </h3>
    </div>

    <div class="glass-card table-card">
      <div v-if="loading && users.length === 0" class="loading-state">
        <div class="ios-spinner"></div>
        <span>{{ $t('common.loading') }}</span>
      </div>
      <div v-else-if="users.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" width="48" height="48"><path fill="currentColor" d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z" opacity="0.4"/></svg>
        <p>{{ $t('users.noUsers') }}</p>
      </div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ $t('users.username') }}</th>
              <th>{{ $t('users.role') }}</th>
              <th>{{ $t('users.status') }}</th>
              <th class="actions-col">{{ $t('users.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.username" class="user-row" :class="{ 'row-disabled': user.status === 'disabled' }">
              <td>
                <div class="user-cell">
                  <div class="user-avatar">{{ user.username.charAt(0).toUpperCase() }}</div>
                  <span class="user-name-text">{{ user.username }}</span>
                  <span v-if="isCurrentUser(user.username)" class="self-badge">{{ $t('users.self') }}</span>
                </div>
              </td>
              <td>
                <span :class="['role-badge', roleBadgeClass(user.role)]">{{ roleLabel(user.role) }}</span>
              </td>
              <td>
                <span :class="['status-badge', `status-${user.status}`]">
                  <span class="status-dot"></span>
                  {{ user.status === 'active' ? $t('users.active') : $t('users.disabled') }}
                </span>
              </td>
              <td class="actions-col">
                <div class="action-buttons">
                  <button v-if="canUpdate" class="btn btn-secondary btn-sm" @click="editUser(user)">{{ $t('common.edit') }}</button>
                  <button v-if="canUpdate" class="btn btn-secondary btn-sm" @click="resetPassword(user.username)">{{ $t('users.resetPassword') }}</button>
                  <button v-if="canUpdate" class="btn btn-sm" :class="user.status === 'active' ? 'btn-warning' : 'btn-success'" :disabled="isCurrentUser(user.username)" @click="toggleStatus(user)">{{ user.status === 'active' ? $t('users.disable') : $t('users.enable') }}</button>
                  <button v-if="canDelete" class="btn btn-danger btn-sm" :disabled="isCurrentUser(user.username)" @click="deleteUser(user.username)">{{ $t('common.delete') }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-container">
        <div class="modal-header">
          <h3>{{ isEditing ? $t('users.editUser') : $t('users.addUser') }}</h3>
          <button class="close-btn" @click="closeModal" aria-label="close">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveUser">
            <div class="form-group">
              <label for="username">{{ $t('users.username') }}</label>
              <input type="text" id="username" v-model="formData.username" :disabled="isEditing" required :placeholder="$t('users.usernamePlaceholder')">
            </div>
            <div class="form-group" v-if="!isEditing">
              <label for="password">{{ $t('users.password') }}</label>
              <input type="password" id="password" v-model="formData.password" required :placeholder="$t('users.passwordPlaceholder')">
            </div>
            <div class="form-group">
              <label for="role">{{ $t('users.role') }}</label>
              <select id="role" v-model="formData.role" required>
                <option v-for="role in roleOptions" :key="role.key" :value="role.key">
                  {{ role.name }}<template v-if="role.is_system"> ({{ $t('roles.builtin') }})</template>
                </option>
              </select>
              <small class="form-hint" v-if="selectedRoleDesc">{{ selectedRoleDesc }}</small>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="closeModal">{{ $t('common.cancel') }}</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">{{ submitting ? $t('common.loading') : $t('common.save') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <div v-if="showResetModal" class="modal-overlay" @click.self="showResetModal = false">
      <div class="modal-container">
        <div class="modal-header">
          <h3>{{ $t('users.resetPasswordTitle') }} - {{ resetTarget }}</h3>
          <button class="close-btn" @click="showResetModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="confirmResetPassword">
            <div class="form-group">
              <label for="new_password">{{ $t('users.newPassword') }}</label>
              <input type="password" id="new_password" v-model="resetForm.new_password" required :placeholder="$t('users.passwordPlaceholder')">
            </div>
            <div class="form-group">
              <label for="confirm_password">{{ $t('users.confirmPassword') }}</label>
              <input type="password" id="confirm_password" v-model="resetForm.confirm_password" required>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="showResetModal = false">{{ $t('common.cancel') }}</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">{{ submitting ? $t('common.loading') : $t('users.confirmReset') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Users',
  data() {
    return {
      users: [],
      roles: {},
      loading: false,
      submitting: false,
      error: null,
      showModal: false,
      isEditing: false,
      formData: { username: '', password: '', role: 'viewer' },
      showResetModal: false,
      resetTarget: '',
      resetForm: { new_password: '', confirm_password: '' }
    }
  },
  computed: {
    currentUser() {
      return this.$store.getters.getUser ? this.$store.getters.getUser.username : null
    },
    roleOptions() {
      return Object.values(this.roles).sort((a, b) => {
        if (a.is_system && !b.is_system) return -1
        if (!a.is_system && b.is_system) return 1
        return a.name.localeCompare(b.name)
      })
    },
    selectedRoleDesc() {
      const role = this.roles[this.formData.role]
      return role ? role.description : ''
    },
    activeCount() { return this.users.filter(u => u.status === 'active').length },
    disabledCount() { return this.users.filter(u => u.status === 'disabled').length },
    canCreate() { return this.$store.getters.hasPermission('user:create') },
    canUpdate() { return this.$store.getters.hasPermission('user:update') },
    canDelete() { return this.$store.getters.hasPermission('user:delete') }
  },
  mounted() { this.fetchData() },
  methods: {
    isCurrentUser(username) { return username === this.currentUser },
    roleLabel(roleKey) {
      const role = this.roles[roleKey]
      return role ? role.name : roleKey
    },
    roleBadgeClass(roleKey) {
      if (roleKey === 'admin') return 'badge-admin'
      const role = this.roles[roleKey]
      if (role && role.is_system) return 'badge-system'
      return 'badge-custom'
    },
    async fetchData() {
      this.loading = true
      this.error = null
      try {
        const [usersRes, rolesRes] = await Promise.all([
          this.$store.dispatch('apiRequest', { url: '/api/users', method: 'GET' }),
          this.$store.dispatch('apiRequest', { url: '/api/roles', method: 'GET' })
        ])
        if (usersRes.status === 'success') {
          this.users = (usersRes.users || []).map(u => ({
            username: u.username,
            role: u.role || 'viewer',
            status: u.status || 'active'
          }))
        } else {
          this.error = usersRes.message
          this.users = []
        }
        if (rolesRes.status === 'success') {
          this.roles = rolesRes.roles || {}
        }
      } catch (e) {
        this.error = e.message
        this.users = []
      } finally {
        this.loading = false
      }
    },
    showAddUserModal() {
      this.isEditing = false
      this.formData = { username: '', password: '', role: 'viewer' }
      this.showModal = true
    },
    editUser(user) {
      this.isEditing = true
      this.formData = { username: user.username, password: '', role: user.role }
      this.showModal = true
    },
    closeModal() { this.showModal = false },
    async saveUser() {
      this.submitting = true
      try {
        let res
        if (this.isEditing) {
          res = await this.$store.dispatch('apiRequest', {
            url: `/api/users/${encodeURIComponent(this.formData.username)}/role`,
            method: 'PUT',
            body: { new_role: this.formData.role }
          })
        } else {
          res = await this.$store.dispatch('apiRequest', {
            url: '/api/users',
            method: 'POST',
            body: { username: this.formData.username, password: this.formData.password, role: this.formData.role }
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
    async deleteUser(username) {
      if (!confirm(this.$t('users.confirmDelete', { name: username }))) return
      try {
        const res = await this.$store.dispatch('apiRequest', {
          url: `/api/users/${encodeURIComponent(username)}`,
          method: 'DELETE'
        })
        if (res.status === 'success') {
          this.fetchData()
        } else {
          alert(res.message)
        }
      } catch (e) {
        alert(e.message)
      }
    },
    resetPassword(username) {
      this.resetTarget = username
      this.resetForm = { new_password: '', confirm_password: '' }
      this.showResetModal = true
    },
    async confirmResetPassword() {
      if (this.resetForm.new_password !== this.resetForm.confirm_password) {
        alert(this.$t('users.passwordMismatch'))
        return
      }
      this.submitting = true
      try {
        const res = await this.$store.dispatch('apiRequest', {
          url: `/api/users/${encodeURIComponent(this.resetTarget)}/password`,
          method: 'PUT',
          body: { new_password: this.resetForm.new_password }
        })
        if (res.status === 'success') {
          this.showResetModal = false
          alert(this.$t('users.passwordResetSuccess', { name: this.resetTarget }))
        } else {
          alert(res.message)
        }
      } catch (e) {
        alert(e.message)
      } finally {
        this.submitting = false
      }
    },
    async toggleStatus(user) {
      const newStatus = user.status === 'active' ? 'disabled' : 'active'
      const action = newStatus === 'disabled' ? this.$t('users.disable') : this.$t('users.enable')
      if (!confirm(this.$t('users.confirmToggleStatus', { action, name: user.username }))) return
      try {
        const res = await this.$store.dispatch('apiRequest', {
          url: `/api/users/${encodeURIComponent(user.username)}/status`,
          method: 'PUT',
          body: { status: newStatus }
        })
        if (res.status === 'success') {
          this.fetchData()
        } else {
          alert(res.message)
        }
      } catch (e) {
        alert(e.message)
      }
    }
  }
}
</script>

<style scoped>
.users-page { display: flex; flex-direction: column; gap: var(--ios-space-5); }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: var(--ios-space-4); }
.header-title h2 { font-size: var(--ios-text-title2); font-weight: var(--ios-weight-bold); color: var(--ios-label-primary); margin: 0 0 var(--ios-space-1) 0; }
.page-subtitle { font-size: var(--ios-text-subhead); color: var(--ios-label-secondary); margin: 0; }
.page-actions { display: flex; gap: var(--ios-space-2); flex-wrap: wrap; }
.glass-card { background: var(--ios-glass-bg); backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate)); -webkit-backdrop-filter: blur(var(--ios-glass-blur)) saturate(var(--ios-glass-saturate)); border: 0.5px solid var(--ios-glass-border); border-radius: var(--ios-radius-xl); box-shadow: var(--ios-shadow-md), inset 0 1px 0 0 var(--ios-glass-highlight); transition: var(--ios-theme-transition); }
.status-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--ios-space-4); }
.status-card { display: flex; align-items: center; gap: var(--ios-space-4); padding: var(--ios-space-4) var(--ios-space-5); }
.card-icon { width: 48px; height: 48px; border-radius: var(--ios-radius-lg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.icon-total { background: rgba(0, 122, 255, 0.15); color: var(--ios-blue); }
.icon-active { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.icon-disabled { background: rgba(255, 59, 48, 0.15); color: var(--ios-red); }
.card-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.card-label { font-size: var(--ios-text-caption1); color: var(--ios-label-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.card-value { font-size: var(--ios-text-title3); font-weight: var(--ios-weight-semibold); color: var(--ios-label-primary); }
.text-success { color: var(--ios-green); }
.text-danger { color: var(--ios-red); }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-title { display: flex; align-items: center; gap: var(--ios-space-2); font-size: var(--ios-text-headline); font-weight: var(--ios-weight-semibold); color: var(--ios-label-primary); margin: 0; }
.section-icon { color: var(--ios-blue); }
.table-card { overflow: hidden; }
.loading-state, .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--ios-space-3); padding: var(--ios-space-8) var(--ios-space-4); color: var(--ios-label-secondary); }
.empty-state svg { color: var(--ios-label-tertiary); }
.ios-spinner { width: 28px; height: 28px; border: 2.5px solid var(--ios-fill-tertiary); border-top-color: var(--ios-blue); border-radius: 50%; animation: spin 0.8s linear infinite; }
.icon-spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--ios-text-subhead); }
.data-table th { padding: var(--ios-space-3) var(--ios-space-4); text-align: left; font-size: var(--ios-text-caption1); font-weight: var(--ios-weight-semibold); color: var(--ios-label-secondary); text-transform: uppercase; letter-spacing: 0.3px; border-bottom: 0.5px solid var(--ios-separator); white-space: nowrap; }
.data-table td { padding: var(--ios-space-3) var(--ios-space-4); border-bottom: 0.5px solid var(--ios-separator); color: var(--ios-label-primary); vertical-align: middle; }
.data-table tbody tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--ios-fill-quaternary); }
.actions-col { text-align: right; }
.user-cell { display: flex; align-items: center; gap: var(--ios-space-2); }
.user-avatar { width: 32px; height: 32px; border-radius: var(--ios-radius-full); background: linear-gradient(135deg, var(--ios-blue), var(--ios-purple)); color: white; display: flex; align-items: center; justify-content: center; font-size: var(--ios-text-caption1); font-weight: var(--ios-weight-semibold); flex-shrink: 0; }
.user-name-text { font-weight: var(--ios-weight-medium); }
.self-badge { font-size: var(--ios-text-caption2); padding: 1px var(--ios-space-2); border-radius: var(--ios-radius-full); background: rgba(0, 122, 255, 0.15); color: var(--ios-blue); }
.role-badge { display: inline-block; padding: 3px var(--ios-space-2); border-radius: var(--ios-radius-sm); font-size: var(--ios-text-caption1); font-weight: var(--ios-weight-medium); }
.badge-admin { background: rgba(255, 149, 0, 0.15); color: var(--ios-orange); }
.badge-system { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.badge-custom { background: rgba(88, 86, 214, 0.15); color: #5856D6; }
.status-badge { display: inline-flex; align-items: center; gap: var(--ios-space-1); padding: 3px var(--ios-space-2); border-radius: var(--ios-radius-full); font-size: var(--ios-text-caption1); font-weight: var(--ios-weight-medium); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-active { background: rgba(52, 199, 89, 0.15); color: var(--ios-green); }
.status-active .status-dot { background: var(--ios-green); }
.status-disabled { background: rgba(255, 59, 48, 0.15); color: var(--ios-red); }
.status-disabled .status-dot { background: var(--ios-red); }
.row-disabled { opacity: 0.6; }
.action-buttons { display: flex; gap: var(--ios-space-1); justify-content: flex-end; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: var(--ios-space-2); padding: var(--ios-space-2) var(--ios-space-4); border: none; border-radius: var(--ios-radius-md); font-size: var(--ios-text-subhead); font-weight: var(--ios-weight-medium); cursor: pointer; transition: all var(--ios-transition-fast); white-space: nowrap; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: var(--ios-space-1) var(--ios-space-3); font-size: var(--ios-text-caption1); }
.btn-primary { background: var(--ios-blue); color: white; box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3); }
.btn-primary:hover:not(:disabled) { background: #0066d6; box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4); }
.btn-secondary { background: var(--ios-fill-tertiary); color: var(--ios-label-primary); }
.btn-secondary:hover:not(:disabled) { background: var(--ios-fill-secondary); }
.btn-success { background: var(--ios-green); color: white; }
.btn-success:hover:not(:disabled) { background: #248a3d; }
.btn-warning { background: var(--ios-orange); color: white; }
.btn-warning:hover:not(:disabled) { background: #c93400; }
.btn-danger { background: var(--ios-red); color: white; }
.btn-danger:hover:not(:disabled) { background: #d70015; }
.alert { display: flex; align-items: center; gap: var(--ios-space-2); padding: var(--ios-space-3) var(--ios-space-4); border-radius: var(--ios-radius-md); font-size: var(--ios-text-subhead); }
.alert-error { background: rgba(255, 59, 48, 0.1); color: var(--ios-red); border: 0.5px solid rgba(255, 59, 48, 0.2); }
.alert-icon { flex-shrink: 0; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: var(--ios-space-4); animation: fadeIn var(--ios-duration-fast) var(--ios-ease-out); }
.modal-container { background: var(--ios-glass-bg); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%); border: 0.5px solid var(--ios-glass-border); border-radius: var(--ios-radius-xl); box-shadow: var(--ios-shadow-xl), inset 0 1px 0 0 var(--ios-glass-highlight); width: 100%; max-width: 480px; max-height: 90vh; display: flex; flex-direction: column; animation: slideUp var(--ios-duration-normal) var(--ios-ease-spring); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: var(--ios-space-5); border-bottom: 0.5px solid var(--ios-separator); }
.modal-header h3 { font-size: var(--ios-text-title3); font-weight: var(--ios-weight-semibold); color: var(--ios-label-primary); margin: 0; }
.close-btn { width: 32px; height: 32px; border: none; border-radius: var(--ios-radius-full); background: var(--ios-fill-tertiary); color: var(--ios-label-secondary); font-size: 22px; line-height: 1; cursor: pointer; transition: all var(--ios-transition-fast); }
.close-btn:hover { background: var(--ios-fill-secondary); color: var(--ios-label-primary); }
.modal-body { padding: var(--ios-space-5); overflow-y: auto; }
.form-group { display: flex; flex-direction: column; gap: var(--ios-space-1); margin-bottom: var(--ios-space-4); }
.form-group label { font-size: var(--ios-text-subhead); font-weight: var(--ios-weight-medium); color: var(--ios-label-primary); }
.form-group input, .form-group select { padding: var(--ios-space-2) var(--ios-space-3); border: 0.5px solid var(--ios-glass-border); border-radius: var(--ios-radius-md); background: var(--ios-fill-tertiary); color: var(--ios-label-primary); font-size: var(--ios-text-body); outline: none; transition: all var(--ios-transition-fast); }
.form-group input:focus, .form-group select:focus { border-color: var(--ios-blue); background: var(--ios-fill-secondary); box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2); }
.form-group input:disabled { opacity: 0.6; cursor: not-allowed; }
.form-hint { font-size: var(--ios-text-caption1); color: var(--ios-label-tertiary); }
.form-actions { display: flex; justify-content: flex-end; gap: var(--ios-space-3); padding-top: var(--ios-space-4); border-top: 0.5px solid var(--ios-separator); }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 768px) {
  .action-buttons { flex-direction: column; align-items: stretch; }
  .actions-col { text-align: left; }
  .btn-sm { width: 100%; }
}
</style>
