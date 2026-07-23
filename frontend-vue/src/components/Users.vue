<template>
  <div id="users" class="page">
    <div class="page-header">
      <h2>用户管理</h2>
      <button id="add-user-btn" class="btn btn-primary" @click="showAddUserModal">添加用户</button>
    </div>
    <div class="table-container">
      <table id="users-table" class="data-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>角色</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="loading-row">
            <td colspan="5" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="5" class="no-data">没有找到用户</td>
          </tr>
          <tr
            v-for="user in users"
            :key="user.username"
            class="user-row"
            :class="{ 'row-disabled': user.status === 'disabled' }"
          >
            <td>{{ user.username }}</td>
            <td>
              <span :class="['role-badge', `role-${user.role.toLowerCase()}`]">
                {{ roleLabel(user.role) }}
              </span>
            </td>
            <td>
              <span :class="['status-badge', `status-${user.status}`]">
                {{ user.status === 'active' ? '启用' : '禁用' }}
              </span>
            </td>
            <td>{{ formatTime(user.created_at) }}</td>
            <td>
              <div class="action-buttons">
                <button
                  class="btn btn-secondary btn-sm"
                  @click="editUser(user)"
                >编辑</button>
                <button
                  class="btn btn-warning btn-sm"
                  @click="resetPassword(user.username)"
                >重置密码</button>
                <button
                  v-if="user.status === 'active'"
                  class="btn btn-secondary btn-sm"
                  @click="toggleStatus(user)"
                >禁用</button>
                <button
                  v-else
                  class="btn btn-success btn-sm"
                  @click="toggleStatus(user)"
                >启用</button>
                <button
                  class="btn btn-danger btn-sm"
                  :disabled="isCurrentUser(user.username)"
                  @click="deleteUser(user.username)"
                >删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加/编辑用户模态框 -->
    <div v-if="showModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isEditing ? '编辑用户' : '添加用户' }}</h3>
          <button class="close-btn" @click="showModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveUser">
            <div class="form-group">
              <label for="username">用户名</label>
              <input
                type="text"
                id="username"
                v-model="formData.username"
                :disabled="isEditing"
                required
                placeholder="字母开头，3-32位字母/数字/下划线"
              >
            </div>
            <div class="form-group" v-if="!isEditing">
              <label for="password">密码</label>
              <input
                type="password"
                id="password"
                v-model="formData.password"
                required
                placeholder="8-32位，需含大小写字母、数字及特殊字符"
              >
            </div>
            <div class="form-group">
              <label for="role">角色</label>
              <select id="role" v-model="formData.role" required>
                <option value="admin">管理员</option>
                <option value="user">普通用户</option>
              </select>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? '保存中...' : '保存' }}
              </button>
              <button type="button" class="btn btn-secondary" @click="showModal = false">取消</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 重置密码模态框 -->
    <div v-if="showResetModal" class="modal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>重置密码 - {{ resetTarget }}</h3>
          <button class="close-btn" @click="showResetModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="confirmResetPassword">
            <div class="form-group">
              <label for="new_password">新密码</label>
              <input
                type="password"
                id="new_password"
                v-model="resetForm.new_password"
                required
                placeholder="8-32位，需含大小写字母、数字及特殊字符"
              >
            </div>
            <div class="form-group">
              <label for="confirm_password">确认新密码</label>
              <input
                type="password"
                id="confirm_password"
                v-model="resetForm.confirm_password"
                required
              >
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? '保存中...' : '确认重置' }}
              </button>
              <button type="button" class="btn btn-secondary" @click="showResetModal = false">取消</button>
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
      loading: false,
      submitting: false,
      showModal: false,
      isEditing: false,
      formData: {
        username: '',
        password: '',
        role: 'user'
      },
      showResetModal: false,
      resetTarget: '',
      resetForm: {
        new_password: '',
        confirm_password: ''
      }
    }
  },
  mounted() {
    this.fetchUsers()
  },
  computed: {
    currentUser() {
      return this.$store.getters.getUser ? this.$store.getters.getUser.username : null
    }
  },
  methods: {
    isCurrentUser(username) {
      return username === this.currentUser
    },
    roleLabel(role) {
      return role === 'admin' ? '管理员' : '普通用户'
    },
    formatTime(iso) {
      if (!iso) return '-'
      // 兼容 'YYYY-MM-DDTHH:MM:SS' 格式
      const t = iso.replace('T', ' ')
      return t
    },
    fetchUsers() {
      this.loading = true
      this.$store.dispatch('apiRequest', {
        url: '/api/users',
        method: 'GET'
      })
        .then(data => {
          if (data.status === 'success') {
            this.users = (data.users || []).map(u => ({
              username: u.username,
              role: u.role || 'user',
              status: u.status || 'active',
              created_at: u.created_at,
              updated_at: u.updated_at
            }))
          } else {
            console.error('获取用户列表失败:', data.message)
            this.users = []
          }
          this.loading = false
        })
        .catch(error => {
          console.error('获取用户列表失败:', error.message || error)
          this.users = []
          this.loading = false
        })
    },
    showAddUserModal() {
      this.isEditing = false
      this.formData = {
        username: '',
        password: '',
        role: 'user'
      }
      this.showModal = true
    },
    editUser(user) {
      this.isEditing = true
      this.formData = {
        username: user.username,
        password: '',
        role: user.role
      }
      this.showModal = true
    },
    saveUser() {
      this.submitting = true
      if (this.isEditing) {
        // 编辑用户：仅更新角色
        this.$store.dispatch('apiRequest', {
          url: `/api/users/${this.formData.username}/role`,
          method: 'PUT',
          body: { new_role: this.formData.role }
        })
          .then(data => {
            this.submitting = false
            if (data.status === 'success') {
              this.showModal = false
              this.fetchUsers()
            } else {
              alert(`更新失败: ${data.message}`)
            }
          })
          .catch(error => {
            this.submitting = false
            alert(`更新失败: ${error.message}`)
          })
      } else {
        // 添加用户
        this.$store.dispatch('apiRequest', {
          url: '/api/users',
          method: 'POST',
          body: {
            username: this.formData.username,
            password: this.formData.password,
            role: this.formData.role
          }
        })
          .then(data => {
            this.submitting = false
            if (data.status === 'success') {
              this.showModal = false
              this.fetchUsers()
            } else {
              alert(`添加失败: ${data.message}`)
            }
          })
          .catch(error => {
            this.submitting = false
            alert(`添加失败: ${error.message}`)
          })
      }
    },
    deleteUser(username) {
      if (!confirm(`确定要删除用户 ${username} 吗？此操作不可恢复。`)) return
      this.$store.dispatch('apiRequest', {
        url: `/api/users/${username}`,
        method: 'DELETE'
      })
        .then(data => {
          if (data.status === 'success') {
            this.fetchUsers()
          } else {
            alert(`删除失败: ${data.message}`)
          }
        })
        .catch(error => {
          alert(`删除失败: ${error.message}`)
        })
    },
    resetPassword(username) {
      this.resetTarget = username
      this.resetForm = { new_password: '', confirm_password: '' }
      this.showResetModal = true
    },
    confirmResetPassword() {
      if (this.resetForm.new_password !== this.resetForm.confirm_password) {
        alert('两次输入的密码不一致')
        return
      }
      this.submitting = true
      this.$store.dispatch('apiRequest', {
        url: `/api/users/${this.resetTarget}/password`,
        method: 'PUT',
        body: { new_password: this.resetForm.new_password }
      })
        .then(data => {
          this.submitting = false
          if (data.status === 'success') {
            this.showResetModal = false
            alert(`用户 ${this.resetTarget} 的密码已重置`)
          } else {
            alert(`重置失败: ${data.message}`)
          }
        })
        .catch(error => {
          this.submitting = false
          alert(`重置失败: ${error.message}`)
        })
    },
    toggleStatus(user) {
      const newStatus = user.status === 'active' ? 'disabled' : 'active'
      const action = newStatus === 'disabled' ? '禁用' : '启用'
      if (!confirm(`确定要${action}用户 ${user.username} 吗？`)) return
      this.$store.dispatch('apiRequest', {
        url: `/api/users/${user.username}/status`,
        method: 'PUT',
        body: { status: newStatus }
      })
        .then(data => {
          if (data.status === 'success') {
            this.fetchUsers()
          } else {
            alert(`${action}失败: ${data.message}`)
          }
        })
        .catch(error => {
          alert(`${action}失败: ${error.message}`)
        })
    }
  }
}
</script>

<style scoped>
/* 角色徽章 */
.role-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.role-admin {
  background-color: #d4edda;
  color: #155724;
}

.role-user {
  background-color: #d1ecf1;
  color: #0c5460;
}

/* 状态徽章 */
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-active {
  background-color: #e2e3e5;
  color: #383d41;
}

.status-disabled {
  background-color: #f8d7da;
  color: #721c24;
}

/* 禁用用户行高亮 */
.row-disabled {
  opacity: 0.6;
}

/* 模态框表单 */
.modal-body form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-size: 14px;
  color: #2c3e50;
}

.form-group input,
.form-group select {
  padding: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
}

.form-group input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }

  .btn-sm {
    width: 100%;
  }
}
</style>
