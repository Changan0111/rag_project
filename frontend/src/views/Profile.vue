<template>
  <div class="profile-page">
    <div class="profile-header">
      <div class="avatar-section">
        <div class="avatar-wrapper" @click="triggerAvatarUpload">
          <el-avatar :size="80" class="user-avatar" :src="avatarUrl">
            <el-icon :size="40"><User /></el-icon>
          </el-avatar>
          <div class="avatar-overlay">
            <el-icon :size="20"><Camera /></el-icon>
            <span>更换头像</span>
          </div>
          <input
            ref="avatarInputRef"
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            style="display: none"
            @change="handleAvatarChange"
          />
        </div>
        <div class="user-info">
          <h2 class="username">{{ userStore.userInfo?.username }}</h2>
        </div>
      </div>
    </div>

    <div class="profile-content">
      <div class="info-section">
        <div class="section-header">
          <el-icon><UserFilled /></el-icon>
          <span>基本信息</span>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">用户名</div>
            <div class="info-value">{{ userStore.userInfo?.username }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">用户角色</div>
            <div class="info-value">
              <el-tag :type="userStore.isAdmin ? 'danger' : 'primary'" effect="dark" round>
                {{ userStore.isAdmin ? '管理员' : '普通用户' }}
              </el-tag>
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">手机号</div>
            <div class="info-value">{{ userStore.userInfo?.phone || '未设置' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">注册时间</div>
            <div class="info-value">{{ formatDate(userStore.userInfo?.created_at) }}</div>
          </div>
        </div>
      </div>

      <div class="info-section">
        <div class="section-header">
          <el-icon><Edit /></el-icon>
          <span>修改信息</span>
        </div>
        <el-form 
          ref="profileFormRef" 
          :model="profileForm" 
          :rules="profileRules" 
          label-position="top"
          class="profile-form"
        >
          <el-form-item label="用户名" prop="username">
            <el-input 
              v-model="profileForm.username" 
              placeholder="请输入用户名"
              prefix-icon="User"
            />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input 
              v-model="profileForm.phone" 
              placeholder="请输入手机号"
              prefix-icon="Phone"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">
              <el-icon><Check /></el-icon>
              保存修改
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="info-section">
        <div class="section-header">
          <el-icon><Lock /></el-icon>
          <span>修改密码</span>
        </div>
        <el-form 
          ref="passwordFormRef" 
          :model="passwordForm" 
          :rules="passwordRules" 
          label-position="top"
          class="profile-form"
        >
          <el-form-item label="原密码" prop="old_password">
            <el-input 
              v-model="passwordForm.old_password" 
              type="password"
              placeholder="请输入原密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input 
              v-model="passwordForm.new_password" 
              type="password"
              placeholder="请输入新密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input 
              v-model="passwordForm.confirm_password" 
              type="password"
              placeholder="请再次输入新密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="warning" :loading="passwordLoading" @click="handleUpdatePassword">
              <el-icon><Check /></el-icon>
              修改密码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="info-section danger-section">
        <div class="section-header">
          <el-icon><Warning /></el-icon>
          <span>账号操作</span>
        </div>
        <div class="danger-content">
          <div class="danger-info">
            <h4>退出登录</h4>
            <p>退出当前账号，需要重新登录才能使用系统</p>
          </div>
          <el-button type="danger" plain @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const avatarInputRef = ref(null)
const profileLoading = ref(false)
const passwordLoading = ref(false)
const avatarLoading = ref(false)

const avatarTimestamp = ref(Date.now())

const avatarUrl = computed(() => {
  if (userStore.userInfo?.avatar) {
    return `${userStore.userInfo.avatar}?t=${avatarTimestamp.value}`
  }
  return ''
})

const profileForm = reactive({
  username: '',
  phone: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const profileRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function triggerAvatarUpload() {
  avatarInputRef.value?.click()
}

async function handleAvatarChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5MB')
    return
  }
  
  avatarLoading.value = true
  try {
    await authApi.uploadAvatar(file)
    const userInfo = await authApi.getProfile()
    userStore.setUserInfo(userInfo)
    avatarTimestamp.value = Date.now()
    ElMessage.success('头像上传成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
  } finally {
    avatarLoading.value = false
    event.target.value = ''
  }
}

async function handleUpdateProfile() {
  const valid = await profileFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  profileLoading.value = true
  try {
    const userInfo = await authApi.updateProfile({
      username: profileForm.username,
      phone: profileForm.phone
    })
    userStore.setUserInfo(userInfo)
    ElMessage.success('修改成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    profileLoading.value = false
  }
}

async function handleUpdatePassword() {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  passwordLoading.value = true
  try {
    await authApi.updatePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    passwordFormRef.value.resetFields()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '密码修改失败')
  } finally {
    passwordLoading.value = false
  }
}

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  }).catch(() => {})
}

onMounted(async () => {
  try {
    const userInfo = await authApi.getProfile()
    userStore.setUserInfo(userInfo)
    profileForm.username = userInfo.username || ''
    profileForm.phone = userInfo.phone || ''
  } catch (error) {
    profileForm.username = userStore.userInfo?.username || ''
    profileForm.phone = userStore.userInfo?.phone || ''
  }
})
</script>

<style lang="scss" scoped>
.profile-page {
  padding: 24px;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

.profile-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 32px 40px;
  color: white;
  flex-shrink: 0;
  
  .avatar-section {
    display: flex;
    align-items: center;
    gap: 32px;
  }
  
  .avatar-wrapper {
    position: relative;
    cursor: pointer;
    
    .user-avatar {
      background: rgba(255, 255, 255, 0.2);
      border: 3px solid rgba(255, 255, 255, 0.5);
    }
    
    .avatar-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      opacity: 0;
      transition: opacity 0.3s;
      color: white;
      font-size: 12px;
      
      .el-icon {
        margin-bottom: 4px;
      }
    }
    
    &:hover .avatar-overlay {
      opacity: 1;
    }
  }
  
  .user-info {
    .username {
      margin: 0 0 8px 0;
      font-size: 28px;
      font-weight: 600;
    }
    
    .user-role {
      margin: 0;
    }
  }
}

.profile-content {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: 1fr;
  gap: 24px;
  flex: 1;
  min-height: 0;
  
  @media (max-width: 1400px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 800px) {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }
}

.info-section {
  background: var(--surface-color);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  min-height: 320px;
  
  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
    flex-shrink: 0;
    
    .el-icon {
      color: var(--primary-color);
      font-size: 18px;
    }
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  flex: 1;
  
  .info-item {
    padding: 16px;
    background: var(--background-color);
    border-radius: 8px;
    
    .info-label {
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 8px;
    }
    
    .info-value {
      font-size: 16px;
      color: var(--text-primary);
      font-weight: 500;
    }
  }
}

.profile-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  
  :deep(.el-form-item__label) {
    font-weight: 500;
    color: var(--text-primary);
  }
  
  :deep(.el-input__wrapper) {
    border-radius: 8px;
  }
  
  :deep(.el-form-item:last-child) {
    margin-top: auto;
  }
}

.danger-section {
  border: 1px solid rgba(245, 108, 108, 0.3);
  
  .section-header .el-icon {
    color: #f56c6c;
  }
  
  .danger-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    flex: 1;
    text-align: center;
    gap: 16px;
  }
  
  .danger-info {
    h4 {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: var(--text-primary);
    }
    
    p {
      margin: 0;
      font-size: 14px;
      color: var(--text-secondary);
    }
  }
}
</style>
