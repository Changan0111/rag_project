<template>
  <div class="main-layout">
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <h1 class="logo">智能客服系统</h1>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-icon><User /></el-icon>
              {{ userStore.userInfo?.username }}
              <el-tag v-if="userStore.isAdmin" type="warning" size="small" style="margin-left: 8px;">
                管理员
              </el-tag>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <el-aside :width="asideWidth" class="layout-aside">
          <div class="aside-nav">
            <div class="toggle-btn" @click="toggleAside">
              <div class="toggle-switch">
                <div class="toggle-track">
                  <div class="toggle-thumb" :class="{ 'is-expanded': !asideCollapsed }">
                    <el-icon class="toggle-icon">
                      <component :is="asideCollapsed ? 'DArrowRight' : 'DArrowLeft'" />
                    </el-icon>
                  </div>
                </div>
              </div>
            </div>

            <el-menu
              :default-active="currentRoute"
              :collapse="asideCollapsed"
              :collapse-transition="false"
              router
              class="side-menu"
            >
              <el-menu-item :index="userStore.isAdmin ? '/service-desk' : '/'">
                <el-icon><ChatDotRound /></el-icon>
                <template #title>{{ userStore.isAdmin ? '客服工作台' : '智能客服对话' }}</template>
              </el-menu-item>
              <el-menu-item index="/dashboard" v-if="userStore.isAdmin">
                <el-icon><DataAnalysis /></el-icon>
                <template #title>数据概览</template>
              </el-menu-item>
              <el-menu-item index="/orders">
                <el-icon><Document /></el-icon>
                <template #title>订单查询</template>
              </el-menu-item>
              <el-menu-item index="/knowledge" v-if="userStore.isAdmin">
                <el-icon><Collection /></el-icon>
                <template #title>知识库管理</template>
              </el-menu-item>
              <el-menu-item index="/chat-logs" v-if="userStore.isAdmin">
                <el-icon><Tickets /></el-icon>
                <template #title>对话日志</template>
              </el-menu-item>
              <el-menu-item index="/cache" v-if="userStore.isAdmin">
                <el-icon><Coin /></el-icon>
                <template #title>缓存管理</template>
              </el-menu-item>
              <el-menu-item index="/builtin-evaluation" v-if="userStore.isAdmin">
                <el-icon><DataAnalysis /></el-icon>
                <template #title>内置评估</template>
              </el-menu-item>
              <el-menu-item index="/recall-comparison" v-if="userStore.isAdmin">
                <el-icon><Histogram /></el-icon>
                <template #title>Top-K检索对比实验</template>
              </el-menu-item>
              <el-menu-item index="/profile">
                <el-icon><User /></el-icon>
                <template #title>个人中心</template>
              </el-menu-item>
            </el-menu>
          </div>

          <div v-show="showUserSessionList" class="session-list">
            <div class="session-header">
              <span class="session-title-text">历史对话</span>
              <el-button type="primary" size="small" text @click="handleNewSession">
                <el-icon><Plus /></el-icon>
                新对话
              </el-button>
            </div>

            <el-scrollbar class="session-scroll">
              <div class="session-items" v-loading="sessionStore.loading">
                <div
                  v-for="session in sessionStore.sessions"
                  :key="session.session_id"
                  :class="['session-item', { active: chatStore.sessionId === session.session_id }]"
                  @click="handleSelectSession(session)"
                >
                  <div class="session-top">
                    <div class="session-title">{{ session.first_message || '新对话' }}</div>
                  </div>
                  <div class="session-meta">
                    <el-text type="info" size="small">
                      <el-icon><Clock /></el-icon>
                      {{ formatTime(session.updated_at) }}
                    </el-text>
                  </div>
                  <el-button
                    class="delete-btn"
                    type="danger"
                    size="small"
                    text
                    @click.stop="handleDeleteSession(session.session_id)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>

                <div v-if="sessionStore.sessions.length === 0 && !sessionStore.loading" class="no-sessions">
                  <el-text type="info" size="small">暂无历史对话</el-text>
                </div>
              </div>
            </el-scrollbar>
          </div>
        </el-aside>

        <el-main class="layout-main">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useUserStore } from '@/stores/user'
import { chatApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const chatStore = useChatStore()
const sessionStore = useSessionStore()

const asideCollapsed = ref(false)

const currentRoute = computed(() => {
  if (userStore.isAdmin && route.path === '/') {
    return '/service-desk'
  }
  return route.path
})

const asideWidth = computed(() => (asideCollapsed.value ? '64px' : '230px'))
const showUserSessionList = computed(
  () => !userStore.isAdmin && currentRoute.value === '/' && !asideCollapsed.value
)

function toggleAside() {
  asideCollapsed.value = !asideCollapsed.value
}

watch(showUserSessionList, visible => {
  if (visible) {
    sessionStore.fetchSessions()
  }
})

onMounted(() => {
  if (showUserSessionList.value) {
    sessionStore.fetchSessions()
  }
})

function formatTime(dateStr) {
  if (!dateStr) return ''

  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`

  return date.toLocaleDateString('zh-CN')
}

async function handleNewSession() {
  chatStore.initSession()
  router.push('/')
}

async function handleSelectSession(session) {
  if (chatStore.sessionId === session.session_id) return

  chatStore.setSessionId(session.session_id)

  try {
    const history = await chatApi.getHistory(session.session_id)
    chatStore.setMessages(
      history.map(item => ({
        id: item.id,
        role: item.role,
        content: item.content,
        source: item.source || 'bot',
        sources: Array.isArray(item.sources) ? JSON.parse(JSON.stringify(item.sources)) : [],
        timestamp: item.created_at
      }))
    )
  } catch (error) {
    console.error('加载会话历史失败:', error)
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await ElMessageBox.confirm('确认删除这个历史对话吗？', '提示', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await chatApi.clearSession(sessionId)
    sessionStore.removeSession(sessionId)

    if (chatStore.sessionId === sessionId) {
      chatStore.initSession()
    }

    ElMessage.success('历史对话已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除历史对话失败:', error)
    }
  }
}

function handleCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
    return
  }

  if (command === 'logout') {
    ElMessageBox.confirm('确认退出当前账号吗？', '提示', {
      confirmButtonText: '确认退出',
      cancelButtonText: '取消',
      type: 'warning'
    })
      .then(() => {
        userStore.logout()
        router.push('/login')
        ElMessage.success('已退出登录')
      })
      .catch(() => {})
  }
}
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;

  .el-container {
    height: 100%;
  }
}

.layout-header {
  background: linear-gradient(135deg, var(--primary-700) 0%, var(--primary-600) 50%, var(--primary-500) 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  box-shadow: 0 4px 20px rgba(74, 122, 255, 0.25);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
      radial-gradient(ellipse at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);
    pointer-events: none;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    z-index: 1;

    .logo {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      margin: 0;
      font-family: 'Outfit', sans-serif;
      font-size: var(--font-size-xl);
      font-weight: 700;
      color: white;
      letter-spacing: -0.02em;

      .logo-icon {
        width: 32px;
        height: 32px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(10px);
      }
    }
  }

  .header-right {
    z-index: 1;

    .user-dropdown {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) var(--spacing-md);
      background: rgba(255, 255, 255, 0.15);
      border-radius: var(--radius-full);
      color: white;
      font-weight: 500;
      cursor: pointer;
      transition: all var(--duration-normal) var(--ease-out-expo);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.2);

      &:hover {
        background: rgba(255, 255, 255, 0.25);
        transform: translateY(-1px);
      }

      .el-icon {
        font-size: 16px;
      }

      .el-icon--right {
        font-size: 12px;
        opacity: 0.8;
      }
    }

    :deep(.el-dropdown-menu) {
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-xl);
      border: 1px solid var(--border-light);
      padding: var(--spacing-sm);
      min-width: 180px;

      .el-dropdown-menu__item {
        border-radius: var(--radius-md);
        padding: var(--spacing-sm) var(--spacing-md);
        font-weight: 500;

        &:hover {
          background: var(--primary-50);
          color: var(--primary-600);
        }

        &.is-divided {
          margin-top: var(--spacing-sm);
          border-top: 1px solid var(--border-light);
          padding-top: var(--spacing-md);
        }
      }
    }
  }
}

.header-left {
  .logo {
    margin: 0;
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: #fff;
    letter-spacing: 0.5px;
  }
}

.header-right {
  .user-dropdown {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    color: #fff;
    cursor: pointer;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--el-border-radius-small);
    transition: background-color 0.2s;

    &:hover {
      background-color: rgba(255, 255, 255, 0.15);
    }
  }
}

.layout-aside {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(226, 232, 240, 0.5);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.08);
  transition: width 0.3s ease;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(180deg,
      transparent 0%,
      rgba(90, 139, 255, 0.2) 50%,
      transparent 100%
    );
  }
}

.aside-nav {
  flex-shrink: 0;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 52px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid var(--el-border-color);

  &:hover .toggle-track {
    border-color: var(--primary-400);
    box-shadow: 0 0 0 3px rgba(90, 139, 255, 0.15);
  }

  &:hover .toggle-thumb {
    color: var(--primary-600);
  }

  .toggle-switch {
    .toggle-track {
      position: relative;
      display: flex;
      align-items: center;
      width: 48px;
      height: 26px;
      padding: 2px;
      background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
      border: 2px solid #e2e8f0;
      border-radius: 13px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 
        inset 0 1px 3px rgba(0, 0, 0, 0.08),
        0 1px 2px rgba(255, 255, 255, 0.9);

      .toggle-thumb {
        position: absolute;
        left: 2px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
        border-radius: 50%;
        color: white;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
          0 2px 6px rgba(90, 139, 255, 0.4),
          0 1px 2px rgba(0, 0, 0, 0.1);

        &.is-expanded {
          transform: translateX(22px);
        }

        .toggle-icon {
          font-size: 12px;
          font-weight: bold;
        }
      }
    }
  }
}

.side-menu {
  border-right: none;
  background: transparent;

  .el-menu-item {
    height: 48px;
    line-height: 48px;
    margin: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-md);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;

    &.is-active {
      color: #fff;
      background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
      border-left: none;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(90, 139, 255, 0.3);
      
      .el-icon {
        transform: scale(1.1);
      }
      
      &::after {
        content: '';
        position: absolute;
        right: -8px;
        top: 50%;
        width: 4px;
        height: 60%;
        background: linear-gradient(180deg, var(--primary-400), var(--primary-700));
        border-radius: 0 4px 4px 0;
        transform: translateY(-50%);
      }
    }

    &:hover:not(.is-active) {
      background: linear-gradient(135deg, rgba(90, 139, 255, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
      transform: translateX(2px);
      
      .el-icon {
        color: var(--primary-600);
      }
    }

    .el-icon {
      transition: all 0.25s ease;
      font-size: 18px;
    }
  }
}

.session-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid var(--el-border-color);
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--el-border-color);

  .session-title-text {
    font-size: var(--font-size-sm);
    color: var(--el-text-color-regular);
    font-weight: 500;
  }
}

.session-scroll {
  flex: 1;
  overflow: hidden;
}

.session-items {
  padding: var(--spacing-sm);
}

.session-item {
  position: relative;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  cursor: pointer;
  border-radius: var(--el-border-radius-small);
  transition: all 0.2s ease;
  border-left: 3px solid transparent;

  &:hover {
    background-color: var(--el-color-primary-light-9);

    .delete-btn {
      opacity: 1;
    }
  }

  &.active {
    background-color: var(--el-color-primary-light-9);
    border-left-color: var(--el-color-primary);

    .session-title {
      color: var(--el-color-primary);
      font-weight: 500;
    }
  }

  .delete-btn {
    position: absolute;
    top: 50%;
    right: var(--spacing-sm);
    opacity: 0;
    transform: translateY(-50%);
    transition: opacity 0.2s;
  }
}

.session-top {
  margin-bottom: var(--spacing-xs);
  padding-right: 24px;
}

.session-title {
  overflow: hidden;
  font-size: var(--font-size-base);
  color: var(--el-text-color-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.no-sessions {
  padding: var(--spacing-xl);
  text-align: center;
}

.layout-main {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  padding: 0;
  overflow: hidden;
  background: var(--el-bg-color-page);
}
</style>
