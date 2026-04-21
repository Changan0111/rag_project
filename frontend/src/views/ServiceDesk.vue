<template>
  <div class="service-desk">
    <el-card class="page-header-card" shadow="hover">
      <div class="page-header">
        <div class="header-content">
          <h2>
            <el-icon class="header-icon"><Service /></el-icon>
            客服工作台
          </h2>
          <el-text type="info">处理用户的人工客服咨询</el-text>
        </div>
        <div class="header-stats">
          <el-tag v-if="pendingCount > 0" type="warning" effect="dark" size="large">
            <el-icon><Bell /></el-icon>
            {{ pendingCount }} 个待处理工单
          </el-tag>
          <el-tag v-else type="info" effect="dark" size="large">
            <el-icon><CircleCheck /></el-icon>
            当前无待处理工单
          </el-tag>
        </div>
      </div>
    </el-card>

    <div class="user-cards" v-loading="loading">
      <el-scrollbar height="calc(100vh - 180px)">
        <div
          v-for="user in userSessions"
          :key="user.user_id"
          class="user-card-wrapper"
        >
          <el-card class="user-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <div class="user-info">
                  <el-avatar :size="40" :color="getAvatarColor(user.username)">
                    {{ user.username.charAt(0).toUpperCase() }}
                  </el-avatar>
                  <div class="user-details">
                    <div class="username">{{ user.username }}</div>
                    <el-text type="info" size="small">
                      共 {{ user.total_tickets }} 个咨询
                    </el-text>
                  </div>
                </div>
                <div class="latest-time">
                  <el-text type="info" size="small">
                    <el-icon><Clock /></el-icon>
                    {{ formatTime(user.latest_message_time) }}
                  </el-text>
                </div>
              </div>
            </template>

            <div class="ticket-list">
              <div
                v-for="ticket in user.tickets"
                :key="ticket.ticket_id"
                class="ticket-item"
              >
                <div class="ticket-left">
                  <div class="ticket-status-time">
                    <el-tag 
                      :type="getStatusType(ticket.status)" 
                      size="small"
                      effect="light"
                    >
                      {{ getStatusText(ticket.status) }}
                    </el-tag>
                    <el-text type="info" size="small">
                      <el-icon><Clock /></el-icon>
                      {{ formatTime(ticket.created_at) }}
                    </el-text>
                  </div>
                  <div class="ticket-preview">
                    {{ ticket.first_message }}
                  </div>
                </div>
                <div class="ticket-right">
                  <div class="ticket-actions">
                    <el-button 
                      v-if="ticket.status !== 'closed'"
                      type="primary" 
                      size="small" 
                      plain
                      @click="handleOpenTicket(ticket)"
                    >
                      接手处理
                    </el-button>
                    <el-button 
                      size="small" 
                      text
                      @click="handleOpenTicket(ticket)"
                    >
                      查看详情
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <div v-if="userSessions.length === 0 && !loading" class="no-data">
          <el-empty description="暂无咨询">
            <el-button type="primary" @click="fetchSessions">
              <el-icon><Refresh /></el-icon>
              刷新列表
            </el-button>
          </el-empty>
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Service, 
  Bell, 
  CircleCheck, 
  Clock, 
  Refresh 
} from '@element-plus/icons-vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const sessionStore = useSessionStore()

const userSessions = computed(() => sessionStore.sessions)
const loading = computed(() => sessionStore.loading)

const pendingCount = computed(() => {
  let count = 0
  userSessions.value.forEach(user => {
    user.tickets.forEach(ticket => {
      if (ticket.status === 'pending') {
        count++
      }
    })
  })
  return count
})

async function fetchSessions() {
  await sessionStore.fetchSessions()
}

function handleOpenTicket(ticket) {
  try {
    const queryParams = {
      ticket_id: ticket.ticket_id,
      session_id: ticket.session_id
    }
    
    router.push({
      path: '/',
      query: queryParams
    }).catch(err => {
      console.error('路由跳转失败:', err)
      ElMessage.error('打开会话失败，请重试')
    })
  } catch (error) {
    console.error('handleOpenTicket 出错:', error)
    ElMessage.error('操作失败，请重试')
  }
}

function getStatusType(status) {
  const typeMap = {
    'pending': 'warning',
    'handling': 'primary',
    'closed': 'info'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    'pending': '待处理',
    'handling': '处理中',
    'closed': '已关闭'
  }
  return textMap[status] || status
}

function getAvatarColor(username) {
  const colors = [
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
    '#ec4899', '#f43f5e', '#f97316', '#f59e0b'
  ]
  const index = username.charCodeAt(0) % colors.length
  return colors[index]
}

function formatTime(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return Math.floor(diff / 60000) + '分钟前'
  } else if (diff < 86400000) {
    return Math.floor(diff / 3600000) + '小时前'
  } else if (diff < 604800000) {
    return Math.floor(diff / 86400000) + '天前'
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

onMounted(() => {
  fetchSessions()
})

onActivated(() => {
  fetchSessions()
})
</script>

<style scoped lang="scss">
.service-desk {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.page-header-card {
  flex-shrink: 0;
  
  :deep(.el-card__body) {
    padding: var(--spacing-md) var(--spacing-lg);
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .header-content {
    h2 {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-size: var(--font-size-xl);
      font-weight: 700;
      color: var(--el-text-color-primary);
      margin: 0 0 var(--spacing-xs) 0;
      letter-spacing: -0.01em;
    }

    .header-icon {
      font-size: var(--font-size-2xl);
      color: var(--el-color-primary);
    }

    .el-text {
      font-size: var(--font-size-sm);
    }
  }

  .header-stats {
    display: flex;
    align-items: center;

    .el-tag {
      display: flex;
      align-items: center;
      gap: var(--spacing-xs);
      padding: var(--spacing-sm) var(--spacing-md);
    }
  }
}

.user-cards {
  flex: 1;
  overflow: hidden;
}

.user-card-wrapper {
  margin-bottom: var(--spacing-sm);
}

.user-card {
  border-radius: var(--el-border-radius-base);
  transition: all var(--duration-normal) var(--ease-out-expo);
  border: 1px solid var(--el-border-color-light);
  animation: fadeInUp var(--duration-slow) var(--ease-out-expo) both;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
    border-color: var(--el-border-color);
  }
  
  :deep(.el-card__header) {
    padding: var(--spacing-md);
    background: linear-gradient(135deg, var(--primary-50) 0%, var(--el-bg-color) 100%);
    border-bottom: 1px solid var(--el-border-color-light);
  }
  
  :deep(.el-card__body) {
    padding: 0;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);

  .user-details {
    .username {
      font-size: var(--font-size-base);
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin-bottom: 2px;
    }
  }
}

.latest-time {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.ticket-list {
  display: flex;
  flex-direction: column;
}

.ticket-item {
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);

  &:hover {
    background: linear-gradient(90deg, var(--primary-50) 0%, var(--el-bg-color) 100%);

    .ticket-actions {
      opacity: 1;
      transform: translateX(0);
    }
  }

  &:not(:last-child) {
    border-bottom: 1px solid var(--el-border-color-light);
  }
}

.ticket-left {
  flex: 1;
  min-width: 0;
}

.ticket-status-time {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.ticket-preview {
  font-size: var(--font-size-sm);
  color: var(--el-text-color-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.5;
}

.ticket-right {
  flex-shrink: 0;
}

.ticket-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  opacity: 0;
  transform: translateX(8px);
  transition: all 0.2s ease;
}

.no-data {
  padding: var(--spacing-xl) 0;
  text-align: center;
}
</style>
