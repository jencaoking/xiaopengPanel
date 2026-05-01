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
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="loading-row">
            <td colspan="3" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="3" class="no-data">没有找到用户</td>
          </tr>
          <tr 
            v-for="user in users" 
            :key="user.username"
            class="user-row"
          >
            <td>{{ user.username }}</td>
            <td>
              <span :class="['role-badge', `role-${user.role.toLowerCase()}`]">
                {{ user.role }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button 
                  class="btn btn-secondary btn-sm"
                  @click="editUser(user)"
                >编辑</button>
                <button 
                  class="btn btn-danger btn-sm"
                  @click="deleteUser(user.username)"
                >删除</button>
                <button 
                  class="btn btn-warning btn-sm"
                  @click="resetPassword(user.username)"
                >重置密码</button>
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
              >
            </div>
            <div class="form-group">
              <label for="password">密码</label>
              <input 
                type="password" 
                id="password" 
                v-model="formData.password"
                :required="!isEditing"
              >
            </div>
            <div class="form-group">
              <label for="role">角色</label>
              <select id="role" v-model="formData.role" required>
                <option value="Admin">管理员</option>
                <option value="User">普通用户</option>
              </select>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary">保存</button>
              <button type="button" class="btn btn-secondary" @click="showModal = false">取消</button>
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
      users: [
        { username: 'admin', role: 'Admin' },
        { username: 'user1', role: 'User' },
        { username: 'user2', role: 'User' }
      ],
      loading: false,
      showModal: false,
      isEditing: false,
      formData: {
        username: '',
        password: '',
        role: 'User'
      }
    }
  },
  methods: {
    showAddUserModal() {
      this.isEditing = false
      this.formData = {
        username: '',
        password: '',
        role: 'User'
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
      if (this.isEditing) {
        // 编辑用户
        const index = this.users.findIndex(u => u.username === this.formData.username)
        if (index !== -1) {
          this.users[index] = {
            ...this.users[index],
            role: this.formData.role
          }
          console.log('编辑用户:', this.formData.username)
        }
      } else {
        // 添加用户
        this.users.push({
          username: this.formData.username,
          role: this.formData.role
        })
        console.log('添加用户:', this.formData.username)
      }
      this.showModal = false
    },
    deleteUser(username) {
      if (confirm(`确定要删除用户 ${username} 吗？`)) {
        this.users = this.users.filter(u => u.username !== username)
        console.log('删除用户:', username)
      }
    },
    resetPassword(username) {
      if (confirm(`确定要重置用户 ${username} 的密码吗？`)) {
        console.log('重置密码:', username)
        // 这里可以添加API调用
      }
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