<template>
  <div class="login-page">
    <div class="login-background">
      <div class="bg-gradient"></div>
      <div class="bg-grid"></div>
      <div class="floating-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
    </div>

    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="40" height="40" rx="12" fill="url(#logoGradient)"/>
              <path d="M12 20C12 15.5817 15.5817 12 20 12C24.4183 12 28 15.5817 28 20C28 24.4183 24.4183 28 20 28" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
              <path d="M16 20C16 17.7909 17.7909 16 20 16C22.2091 16 24 17.7909 24 20" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
              <circle cx="20" cy="20" r="2" fill="white"/>
              <defs>
                <linearGradient id="logoGradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#4a7aff"/>
                  <stop offset="1" stop-color="#5b8bff"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 class="login-title">智能客服系统</h1>
        </div>

        <el-tabs v-model="activeTab" class="login-tabs" :before-leave="handleTabChange">
          <el-tab-pane label="登录" name="login">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              label-position="top"
              class="login-form"
            >
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  size="large"
                  :prefix-icon="User"
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  @keydown.enter="handleLogin"
                />
              </el-form-item>

              <el-form-item label="登录身份" prop="role">
                <el-radio-group v-model="loginForm.role" class="role-radio-group">
                  <el-radio value="user">
                    <div class="role-option">
                      <div class="role-icon user-icon">
                        <el-icon><User /></el-icon>
                      </div>
                      <span>普通用户</span>
                    </div>
                  </el-radio>
                  <el-radio value="admin">
                    <div class="role-option">
                      <div class="role-icon admin-icon">
                        <el-icon><Setting /></el-icon>
                      </div>
                      <span>管理员</span>
                    </div>
                  </el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="loginLoading"
                  size="large"
                  @click="handleLogin"
                  class="login-btn"
                >
                  <span v-if="!loginLoading">登 录</span>
                  <span v-else>登录中...</span>
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              label-position="top"
              class="login-form"
            >
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名"
                  size="large"
                  :prefix-icon="User"
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item label="确认密码" prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="请再次输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  @keydown.enter="handleRegister"
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="registerLoading"
                  size="large"
                  @click="handleRegister"
                  class="login-btn"
                >
                  <span v-if="!registerLoading">注 册</span>
                  <span v-else>注册中...</span>
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>

        <div class="demo-account">
          <div class="demo-divider">
            <span>测试账号</span>
          </div>
          <div class="demo-accounts">
            <div class="demo-item">
              <el-tag type="warning" size="small">管理员</el-tag>
              <span>zhangsan / 123456</span>
            </div>
          </div>
        </div>
      </div>

      <div class="login-footer">
        <p>智能客服系统 &copy; 2024 - 基于RAG技术构建</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Setting } from '@element-plus/icons-vue'
import { authApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { useChatStore } from '@/stores/chat'

const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()

const activeTab = ref('login')
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loginLoading = ref(false)
const registerLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择登录身份', trigger: 'change' }
  ]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

function handleTabChange(activeName) {
  if (activeName === 'register') {
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
  }
}

async function handleLogin() {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loginLoading.value = true
  try {
    const response = await authApi.login({
      username: loginForm.username,
      password: loginForm.password,
      role: loginForm.role
    })
    userStore.setToken(response.access_token)
    userStore.setRole(response.role)

    const userInfo = await authApi.getProfile()
    userStore.setUserInfo(userInfo)

    chatStore.initSession()

    const roleText = response.role === 'admin' ? '管理员' : '用户'
    ElMessage.success(`登录成功，欢迎${roleText}！`)
    router.push('/')
  } catch (error) {
    console.error('登录失败:', error)
    if (error.response?.status === 403) {
      ElMessage.error(error.response.data.detail || '权限不足，无法以管理员身份登录')
    }
  } finally {
    loginLoading.value = false
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  registerLoading.value = true
  try {
    await authApi.register({
      username: registerForm.username,
      password: registerForm.password
    })

    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
    registerForm.password = ''
    registerForm.confirmPassword = ''
  } catch (error) {
    console.error('注册失败:', error)
  } finally {
    registerLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--gray-950);
}

.login-background {
  position: absolute;
  inset: 0;
  z-index: 0;

  .bg-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  }

  .bg-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(90, 139, 255, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(90, 139, 255, 0.03) 1px, transparent 1px);
    background-size: 60px 60px;
  }
}

.floating-shapes {
  position: absolute;
  inset: 0;
  overflow: hidden;

  .shape {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
    animation: float 20s ease-in-out infinite;
  }

  .shape-1 {
    width: 400px;
    height: 400px;
    background: linear-gradient(135deg, var(--primary-500), var(--primary-700));
    top: -100px;
    left: -100px;
    animation-delay: 0s;
  }

  .shape-2 {
    width: 300px;
    height: 300px;
    background: linear-gradient(135deg, var(--accent-500), var(--accent-600));
    bottom: -50px;
    right: -50px;
    animation-delay: -7s;
  }

  .shape-3 {
    width: 200px;
    height: 200px;
    background: linear-gradient(135deg, var(--primary-400), var(--accent-400));
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation-delay: -14s;
  }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  padding: var(--spacing-lg);
  animation: fadeInUp var(--duration-slower) var(--ease-out-expo) both;
}

.login-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -2px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-lg);

  .logo-icon {
    width: 48px;
    height: 48px;
    margin: 0 auto var(--spacing-sm);

    svg {
      width: 100%;
      height: 100%;
      filter: drop-shadow(0 4px 12px rgba(74, 122, 255, 0.3));
    }
  }

  .login-title {
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.03em;
  }

  .login-subtitle {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin: 0;
  }
}

.login-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: var(--spacing-md);
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__active-bar) {
    background: linear-gradient(90deg, var(--primary-600), var(--accent-500));
    height: 3px;
    border-radius: var(--radius-full);
  }

  :deep(.el-tabs__item) {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--text-secondary);
    padding: 0 var(--spacing-lg);
    height: 40px;
    line-height: 40px;

    &:hover {
      color: var(--text-primary);
    }

    &.is-active {
      color: var(--primary-600);
      font-weight: 600;
    }
  }
}

.login-form {
  :deep(.el-form-item__label) {
    font-weight: 500;
    color: var(--text-primary);
    padding-bottom: var(--spacing-sm);
  }

  :deep(.el-input__wrapper) {
    padding: 4px 16px;
    box-shadow: 0 0 0 1px var(--border-color);

    &:focus-within {
      box-shadow: 0 0 0 2px var(--primary-200);
    }
  }

  :deep(.el-input__inner) {
    height: 40px;
    font-size: var(--font-size-base);
  }

  :deep(.el-input__prefix) {
    color: var(--text-tertiary);
  }
}

.role-radio-group {
  display: flex;
  gap: var(--spacing-md);
  width: 100%;

  :deep(.el-radio) {
    margin: 0;
    height: auto;

    .el-radio__input {
      display: none;
    }

    .el-radio__label {
      padding: 0;
    }

    &:first-child {
      flex: 1;
    }

    &:last-child {
      flex: 1;
    }
  }
}

.role-option {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-md);
  background: var(--gray-50);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);
  min-height: 52px;

  &:hover {
    border-color: var(--primary-300);
    background: var(--primary-50);
  }

  .role-icon {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 14px;
  }

  .user-icon {
    background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
  }

  .admin-icon {
    background: linear-gradient(135deg, var(--accent-500), var(--accent-600));
  }

  span {
    font-weight: 500;
    color: var(--text-primary);
    font-size: var(--font-size-sm);
  }
}

:deep(.el-radio__input.is-checked + .el-radio__label .role-option) {
  border-color: var(--primary-500);
  background: linear-gradient(135deg, var(--primary-50), rgba(90, 139, 255, 0.1));
  box-shadow: 0 0 0 3px rgba(90, 139, 255, 0.15);
}

.login-btn {
  width: 100%;
  height: 52px;
  font-size: var(--font-size-lg);
  font-weight: 600;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
  border: none;
  box-shadow: 0 4px 14px rgba(74, 122, 255, 0.35);
  margin-top: var(--spacing-md);

  &:hover:not(.is-disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(74, 122, 255, 0.45);
  }

  &:active:not(.is-disabled) {
    transform: translateY(0);
  }
}

.demo-account {
  margin-top: var(--spacing-xl);
}

.demo-divider {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-color);
  }

  span {
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
    white-space: nowrap;
  }
}

.demo-accounts {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: 0 var(--spacing-md);
}

.demo-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);

  .el-tag {
    flex-shrink: 0;
  }
}

.login-footer {
  text-align: center;
  margin-top: var(--spacing-xl);

  p {
    font-size: var(--font-size-sm);
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
  }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}
</style>
