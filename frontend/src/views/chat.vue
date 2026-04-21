<template>
  <div class="chat-page">
    <div class="chat-container">
      <div class="chat-header">
        <div class="header-left">
          <h2>{{ isAdminConversation ? '人工客服对话' : '智能客服对话' }}</h2>
          <template v-if="hasTicketSelected && ticketInfo">
            <el-tag :type="statusTagType(ticketInfo.status)" size="small">
              {{ statusText(ticketInfo.status) }}
            </el-tag>
            <span class="user-label">用户: {{ ticketInfo.username }}</span>
          </template>
        </div>
        <div class="header-actions">
          <el-button v-if="hasTicketSelected" @click="goBackToServiceDesk">
            <el-icon><Back /></el-icon>
            返回工作台
          </el-button>
          <el-button v-else-if="!isAdminConversation" type="primary" plain size="small" @click="handleNewSession">
            <el-icon><Plus /></el-icon>
            新对话
          </el-button>
        </div>
      </div>

      <div v-if="humanServiceStatus.inService" class="human-service-banner">
        <el-icon><Connection /></el-icon>
        <span v-if="humanServiceStatus.status === 'pending'">
          正在等待人工客服处理，请稍候...
        </span>
        <span v-else-if="humanServiceStatus.status === 'handling'">
          人工客服 ({{ humanServiceStatus.adminName || '客服' }}) 正在为您服务
        </span>
        <el-button type="primary" size="small" plain @click="closeHumanServiceAndDisconnect">
          结束人工服务
        </el-button>
      </div>

      <div v-if="hasTicketSelected && ticketInfo && ticketInfo.status === 'closed'" class="closed-banner">
        <el-icon><Lock /></el-icon>
        <span>此工单已关闭，无法继续发送消息</span>
      </div>

      <div class="chat-messages" ref="messagesContainer" v-loading="isLoadingHistory">
        <div v-if="isAdminConversation && !hasTicketSelected" class="admin-empty-message">
          <div class="welcome-icon">
            <el-icon :size="48"><User /></el-icon>
          </div>
          <h3>请选择左侧人工会话</h3>
          <p>已处理会话会保留在列表中，方便继续查看记录</p>
        </div>

        <div v-if="chatStore.messages.length === 0 && !isAdminConversation" class="welcome-message">
          <div class="welcome-icon">
            <el-icon :size="48"><ChatDotRound /></el-icon>
          </div>
          <h3>欢迎使用智能客服</h3>
          <p>我可以帮助您解答商品、订单、售后和活动相关问题</p>
          <div class="quick-questions">
            <div
              v-for="(question, index) in quickQuestions"
              :key="index"
              class="quick-question"
              @click="handleQuickQuestion(question)"
            >
              {{ question }}
            </div>
          </div>
        </div>

        <div
          v-for="(message, index) in chatStore.messages"
          :key="message.id || index"
          :class="['message', message.role, message.source === 'human' ? 'human-service' : '']"
        >
          <div class="message-avatar">
            <el-avatar v-if="message.role === 'user'" :size="36" class="user-avatar" :src="userAvatarUrl">
              <el-icon><UserFilled /></el-icon>
            </el-avatar>
            <el-avatar v-else-if="message.source === 'human'" :size="36" class="human-avatar">
              <el-icon><Service /></el-icon>
            </el-avatar>
            <el-avatar v-else :size="36" class="assistant-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content" :class="{ 'user-content': message.role === 'user' }">
            <div v-if="message.role === 'assistant'" class="message-source-label">
              {{ message.source === 'human' ? '人工客服' : message.source === 'system' ? '系统提示' : '智能助手' }}
            </div>
            <div 
              v-if="message.role === 'assistant' && message.source !== 'system'"
              class="message-text assistant-bubble"
              v-html="renderMarkdown(message.content)"
            ></div>
            <div v-else-if="message.role === 'user'" class="message-text user-bubble">
              {{ formatMessageContent(message.content) }}
            </div>
            <div v-else class="message-text system-bubble">
              {{ formatMessageContent(message.content) }}
            </div>
            
            <div v-if="message.role === 'assistant' && message.sources && message.sources.length > 0" class="source-actions">
              <el-popover placement="top-start" :width="420" trigger="hover">
                <template #reference>
                  <el-button text size="small" type="primary">
                    <el-icon><Document /></el-icon>
                    {{ message.sources.length }} 个参考来源
                  </el-button>
                </template>
                <div class="source-popover-list">
                  <div 
                    v-for="(source, idx) in message.sources" 
                    :key="idx" 
                    class="source-item clickable"
                    @click="viewSourceDetail(source, idx)"
                  >
                    <div class="source-header">
                      <div class="source-title">
                        <el-icon><Document /></el-icon>
                        {{ source.title || '知识点' }}
                      </div>
                      <el-tag v-if="source.category" size="small" :type="getCategoryTagType(source.category)">
                        {{ getCategoryLabel(source.category) }}
                      </el-tag>
                    </div>
                    <div v-if="source.content" class="source-preview">{{ source.content }}...</div>
                    <div class="source-footer">
                      <el-icon><View /></el-icon>
                      <span>点击查看详情</span>
                    </div>
                  </div>
                </div>
              </el-popover>
            </div>
            
            <div v-if="message.role === 'assistant' && message.source !== 'system'" class="feedback-actions">
              <div class="feedback-buttons">
                <button 
                  :class="['feedback-btn', message.feedback === 'like' ? 'liked' : '']"
                  @click="handleFeedback(message, 'like')"
                  title="有帮助"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M7 10v12"></path>
                    <path d="M15 5.88L14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88z"></path>
                  </svg>
                  <span class="feedback-text">有帮助</span>
                </button>
                <button 
                  :class="['feedback-btn', message.feedback === 'dislike' ? 'disliked' : '']"
                  @click="handleFeedback(message, 'dislike')"
                  title="没帮助"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M17 14V2"></path>
                    <path d="M9 18.12L10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88z"></path>
                  </svg>
                  <span class="feedback-text">没帮助</span>
                </button>
              </div>
            </div>
          </div>
          <div v-if="message.timestamp" class="message-time">
            <el-text type="info" size="small">{{ formatMessageTime(message.timestamp) }}</el-text>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="message-avatar">
            <el-avatar :size="36" class="assistant-avatar">
              <el-icon><ChatDotRound /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div v-if="streamingContent" class="message-text assistant-bubble" v-html="renderMarkdown(streamingContent)"></div>
            <div v-else class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          :placeholder="adminAwareInputPlaceholder"
          :disabled="loading || (isAdminConversation && !ticketId) || (isAdminMode && ticketInfo?.status === 'closed')"
          @keydown.enter.exact.prevent="handleSend"
          class="chat-textarea"
        />
        <div class="input-toolbar">
          <div class="toolbar-left">
            <el-button
              v-if="!isAdminConversation && !humanServiceStatus.inService"
              type="warning"
              plain
              size="small"
              :disabled="loading"
              @click="handleTransferToHuman"
            >
              <el-icon><Connection /></el-icon>
              转人工
            </el-button>
            <el-button
              v-if="hasTicketSelected && ticketInfo && ticketInfo.status !== 'closed'"
              type="danger"
              plain
              size="small"
              @click="handleCloseTicket"
            >
              <el-icon><CircleClose /></el-icon>
              结束服务
            </el-button>
          </div>
          <div class="toolbar-right">
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!inputMessage.trim() || (isAdminConversation && !ticketId) || (isAdminMode && ticketInfo?.status === 'closed')"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
              发送
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 来源详情对话框 -->
    <el-dialog
      v-model="sourceDetailVisible"
      title="来源详情"
      width="600px"
      :close-on-click-modal="true"
      destroy-on-close
    >
      <div v-if="currentSource" class="source-detail-content">
        <div class="detail-header">
          <div class="detail-title-row">
            <el-icon :size="20" class="detail-icon"><Document /></el-icon>
            <h3 class="detail-title">{{ currentSource.title || '知识点详情' }}</h3>
          </div>
          <el-tag v-if="currentSource.category" size="large" :type="getCategoryTagType(currentSource.category)">
            {{ getCategoryLabel(currentSource.category) }}
          </el-tag>
        </div>
        
        <div class="detail-body">
          <div class="detail-section">
            <div class="section-label">
              <el-icon><Document /></el-icon>
              文档内容
            </div>
            <div class="section-content">
              <div class="content-text" v-html="renderMarkdown(currentSource.content || '暂无内容')"></div>
            </div>
          </div>
          
          <div class="detail-section" v-if="currentSource.similarity">
            <div class="section-label">
              <el-icon><DataAnalysis /></el-icon>
              相似度
            </div>
            <div class="section-content">
              <el-progress 
                :percentage="Math.round(currentSource.similarity * 100)" 
                :stroke-width="8"
                :text-inside="true"
                color="var(--primary-500)"
              />
            </div>
          </div>
          
          <div class="detail-section" v-if="currentSource.doc_id">
            <div class="section-label">
              <el-icon><Clock /></el-icon>
              文档信息
            </div>
            <div class="section-content">
              <div class="info-row">
                <span class="info-label">文档 ID:</span>
                <span class="info-value">{{ currentSource.doc_id }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="sourceDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {
  ref,
  nextTick,
  onMounted,
  onActivated,
  onDeactivated,
  onUnmounted,
  computed,
  watch
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  ChatDotRound, 
  Service, 
  Promotion, 
  Back, 
  Plus, 
  User, 
  UserFilled, 
  Lock, 
  Document, 
  CaretTop, 
  CaretBottom, 
  Connection, 
  CircleClose,
  View,
  DataAnalysis,
  Clock
} from '@element-plus/icons-vue'
import { chatApi, ticketApi } from '@/api/modules'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import { useUserStore } from '@/stores/user'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true
})

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const sessionStore = useSessionStore()
const userStore = useUserStore()

const inputMessage = ref('')
const loading = ref(false)
const isLoadingHistory = ref(false)
const messagesContainer = ref(null)
const streamingContent = ref('')
const humanServiceStatus = ref({
  inService: false,
  status: null,
  adminName: null
})
const sourceDetailVisible = ref(false)
const currentSource = ref(null)

const hasTicketSelected = computed(() => route.query.ticket_id !== undefined)
const isAdminConversation = computed(() => userStore.isAdmin)
const isAdminMode = computed(() => userStore.isAdmin || hasTicketSelected.value)
const ticketInfo = ref(null)
const ticketId = ref(null)
const avatarTimestamp = ref(Date.now())

const userAvatarUrl = computed(() => {
  if (userStore.userInfo?.avatar) {
    return `${userStore.userInfo.avatar}?t=${avatarTimestamp.value}`
  }
  return ''
})

let pollingTimer = null

const quickQuestions = [
  '2024年旗舰手机怎么选？iPhone 15 Pro Max和华为Mate 60 Pro哪个更值得买？',
  '商品收到有质量问题想退货，具体的退换货流程是什么？',
  '如何查询物流信息？不同地区的配送时效分别是多久？',
  '会员等级体系是怎样的？积分如何获取和使用？',
  '平台支持哪些支付方式？分期付款的费率和条件是什么？',
  '产品出现故障需要维修，售后保修流程是怎么样的？'
]

const adminAwareInputPlaceholder = computed(() => {
  if (isAdminConversation.value) {
    return ticketId.value ? '输入人工客服回复...' : '请选择左侧人工会话后回复...'
  }
  return '请输入您的问题...'
})

function renderMarkdown(text) {
  if (!text) return ''
  let processed = text
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  let result = md.render(processed)
  return result
    .replace(/<p>\s*<\/p>/g, '')
    .trim()
}

function formatMessageTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  return date.toLocaleDateString('zh-CN')
}

function statusText(status) {
  const map = {
    pending: '待处理',
    handling: '处理中',
    closed: '已关闭'
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    pending: 'warning',
    handling: 'primary',
    closed: 'info'
  }
  return map[status] || ''
}

function normalizeMessages(history) {
  return history
    .filter(item => {
      if (!isAdminConversation.value) {
        return true
      }
      return item.role === 'user' || (item.role === 'assistant' && item.source === 'human')
    })
    .map(item => ({
      id: item.id,
      role: item.role,
      content: item.content,
      source: item.source || 'bot',
      timestamp: item.created_at,
      sources: Array.isArray(item.sources) ? JSON.parse(JSON.stringify(item.sources)) : []
    }))
}

function handleFeedback(message, type) {
  message.feedback = message.feedback === type ? null : type
  ElMessage.success(message.feedback ? '感谢您的反馈' : '已取消反馈')
}

function getCategoryLabel(category) {
  const labels = {
    'product': '商品咨询',
    'policy': '售后政策',
    'logistics': '物流配送',
    'promotion': '优惠活动',
    'order': '订单查询',
    'member': '会员服务',
    'payment': '支付帮助',
    'technical': '技术支持',
    'service': '客服服务'
  }
  return labels[category] || category
}

function getCategoryTagType(category) {
  const typeMap = {
    'product': 'success',
    'policy': 'warning',
    'logistics': 'primary',
    'promotion': 'danger',
    'order': 'info',
    'member': 'success',
    'payment': 'warning',
    'technical': 'primary',
    'service': 'info'
  }
  return typeMap[category] || 'info'
}

function viewSourceDetail(source, idx) {
  currentSource.value = source
  sourceDetailVisible.value = true
}

async function initAdminMode() {
  const sessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  const tId = route.query.ticket_id
  if (hasTicketSelected.value && sessionId && tId) {
    ticketId.value = parseInt(tId)
    chatStore.setSessionId(sessionId)

    await loadTicketInfo(true)
    
    if (ticketInfo.value && ticketInfo.value.status === 'pending') {
      try {
        await ticketApi.setHandling(ticketId.value)
        await loadTicketInfo(true)
      } catch (error) {
        console.error('接单失败:', error)
      }
    }
    return
  }

  ticketId.value = null
  ticketInfo.value = null
  if (isAdminConversation.value) {
    chatStore.clearMessages()
  }
}

async function loadTicketInfo(syncMessages = false) {
  if (!ticketId.value) return
  try {
    const data = await ticketApi.getDetail(ticketId.value)
    ticketInfo.value = data
    if (syncMessages) {
      chatStore.setMessages(normalizeMessages(data.messages || []))
      scrollToBottom()
    }
  } catch (error) {
    ElMessage.error('加载工单信息失败')
  }
}

async function loadHistory() {
  if (!chatStore.sessionId) return
  if (hasTicketSelected.value) {
    await loadTicketInfo(true)
    return
  }
  if (isAdminConversation.value) {
    return
  }
  try {
    isLoadingHistory.value = true
    const history = await chatApi.getHistory(chatStore.sessionId, 100)
    const normalized = normalizeMessages(history)
    const localMessages = chatStore.messages
    for (let i = 0; i < normalized.length; i++) {
      const remote = normalized[i]
      if (remote.role === 'assistant' && (!remote.sources || remote.sources.length === 0)) {
        if (i < localMessages.length) {
          const local = localMessages[i]
          if (local && local.role === 'assistant' && local.sources && local.sources.length > 0) {
            remote.sources = JSON.parse(JSON.stringify(local.sources))
          }
        }
      }
    }
    chatStore.setMessages(normalized)
    scrollToBottom()
  } catch (error) {
    console.error('加载会话历史失败:', error)
  } finally {
    isLoadingHistory.value = false
  }
}

async function checkHumanServiceStatus() {
  if (!chatStore.sessionId || isAdminConversation.value) return

  try {
    const result = await ticketApi.checkUserTicket(chatStore.sessionId)
    if (result.exists && ['pending', 'handling'].includes(result.status)) {
      humanServiceStatus.value = {
        inService: true,
        status: result.status,
        adminName: result.assigned_admin_name
      }
    } else {
      humanServiceStatus.value = {
        inService: false,
        status: null,
        adminName: null
      }
    }
  } catch (error) {
    console.error('检查人工服务状态失败:', error)
  }
}

async function closeHumanService() {
  humanServiceStatus.value = {
    inService: false,
    status: null,
    adminName: null
  }
  ElMessage.success('已结束人工服务')
}

async function refreshCurrentHistory() {
  if (!chatStore.sessionId) return

  try {
    const history = await chatApi.getHistory(chatStore.sessionId, 100)
    const normalized = normalizeMessages(history)
    const localMessages = chatStore.messages
    for (let i = 0; i < normalized.length; i++) {
      const remote = normalized[i]
      if (remote.role === 'assistant' && (!remote.sources || remote.sources.length === 0)) {
        if (i < localMessages.length) {
          const local = localMessages[i]
          if (local && local.role === 'assistant' && local.sources && local.sources.length > 0) {
            remote.sources = JSON.parse(JSON.stringify(local.sources))
          }
        }
      }
    }
    chatStore.setMessages(normalized)
    scrollToBottom()
  } catch (error) {
    console.error('加载会话历史失败:', error)
  }
}

async function pollNewMessages() {
  if (loading.value) return

  if (isAdminConversation.value) {
    await sessionStore.fetchSessions()
  }

  if (hasTicketSelected.value) {
    try {
      await loadTicketInfo(true)
    } catch (error) {
      console.error('轮询人工会话失败:', error)
    }
    return
  }

  if (isAdminConversation.value) {
    return
  }

  if (!chatStore.sessionId) return

  try {
    const history = await chatApi.getHistory(chatStore.sessionId, 100)
    const normalized = normalizeMessages(history)
    const latestRemoteId = normalized[normalized.length - 1]?.id || null
    const latestLocalId = chatStore.messages[chatStore.messages.length - 1]?.id || null

    if (normalized.length !== chatStore.messages.length || latestRemoteId !== latestLocalId) {
      const localMessages = chatStore.messages
      for (let i = 0; i < normalized.length; i++) {
        const remote = normalized[i]
        if (remote.role === 'assistant' && (!remote.sources || remote.sources.length === 0)) {
          if (i < localMessages.length) {
            const local = localMessages[i]
            if (local && local.role === 'assistant' && local.sources && local.sources.length > 0) {
              remote.sources = JSON.parse(JSON.stringify(local.sources))
            }
          }
        }
      }
      chatStore.setMessages(normalized)
      scrollToBottom()
    }
    if (humanServiceStatus.value.inService) {
      await checkHumanServiceStatus()
    }
  } catch (error) {
    console.error('轮询消息失败:', error)
  }
}

function startPolling() {
  if (pollingTimer) return
  pollingTimer = window.setInterval(() => {
    pollNewMessages()
  }, 3000)
}

function stopPolling() {
  if (!pollingTimer) return
  window.clearInterval(pollingTimer)
  pollingTimer = null
}

async function handleSend() {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return

  inputMessage.value = ''

  if (isAdminConversation.value) {
    await handleAdminSend(message)
  } else {
    await handleUserSend(message)
  }
}

async function handleAdminSend(message) {
  if (!ticketId.value) return

  loading.value = true
  scrollToBottom()

  try {
    await ticketApi.reply(ticketId.value, { content: message })
    await loadTicketInfo(true)
    scrollToBottom()
  } catch (error) {
    ElMessage.error('发送回复失败')
  } finally {
    loading.value = false
  }
}

async function handleUserSend(message) {
  chatStore.addMessage('user', message, 'user')

  loading.value = true
  streamingContent.value = ''
  scrollToBottom()

  let currentContent = ''
  let currentSessionId = chatStore.sessionId
  let handoffNotice = ''
  let sources = []

  chatApi.sendMessageStream(
    {
      session_id: chatStore.sessionId,
      content: message
    },
    (eventData) => {
      if (eventData.type === 'session') {
        currentSessionId = eventData.session_id
        chatStore.setSessionId(eventData.session_id)
      } else if (eventData.type === 'content') {
        currentContent += eventData.content
        streamingContent.value = currentContent
        scrollToBottom()
      } else if (eventData.type === 'cached') {
        currentContent = eventData.content
        streamingContent.value = currentContent
        sources = eventData.sources || []
        scrollToBottom()
      } else if (eventData.type === 'done') {
        // ✅ 新增：从 done 事件中提取参考来源
        if (eventData.sources && Array.isArray(eventData.sources)) {
          sources = eventData.sources
          console.log('📚 收到参考来源:', sources.length, '篇')
        }
      } else if (eventData.type === 'handoff') {
        handoffNotice = eventData.content
      } else if (eventData.type === 'error') {
        streamingContent.value = eventData.content
      }
    },
    () => {
      ElMessage.error('发送消息失败，请稍后重试')
      if (currentContent) {
        chatStore.addMessage('assistant', currentContent)
      } else if (handoffNotice) {
        chatStore.addMessage('assistant', handoffNotice, 'system')
      } else {
        chatStore.addMessage('assistant', '抱歉，系统出现了一些问题，请稍后重试。')
      }
      loading.value = false
      streamingContent.value = ''
      scrollToBottom()
    },
    async () => {
      const localSources = [...sources]
      const lastMsgIndex = chatStore.messages.length
      
      if (currentContent) {
        chatStore.addMessage('assistant', currentContent, 'bot', sources)
      }
      if (handoffNotice) {
        chatStore.addMessage('assistant', handoffNotice, 'system')
      }

      if (currentSessionId) {
        chatStore.setSessionId(currentSessionId)
      }

      loading.value = false
      streamingContent.value = ''
      
      try {
        await refreshCurrentHistory()
      } catch (historyError) {
        console.warn('刷新历史记录失败，使用本地数据:', historyError)
      }
      
      if (localSources.length > 0 && chatStore.messages.length > 0) {
        const messages = chatStore.messages
        let lastAssistantMsg = null
        
        for (let i = messages.length - 1; i >= 0; i--) {
          if (messages[i].role === 'assistant') {
            lastAssistantMsg = messages[i]
            break
          }
        }
        
        if (lastAssistantMsg && (!lastAssistantMsg.sources || lastAssistantMsg.sources.length === 0)) {
          lastAssistantMsg.sources = localSources
          localStorage.setItem('chat_messages', JSON.stringify(chatStore.messages))
        }
      }
      
      sessionStore.fetchSessions()
      
      if (handoffNotice) {
        await checkHumanServiceStatus()
      }
      
      scrollToBottom()
    }
  )
}

async function handleTransferToHuman() {
  if (loading.value || humanServiceStatus.value.inService) return

  const draftMessage = inputMessage.value.trim()
  const lastUserMessage = [...chatStore.messages].reverse().find(item => item.role === 'user')?.content
  const transferContent = draftMessage || lastUserMessage || '请求转人工服务'

  if (draftMessage) {
    chatStore.addMessage('user', draftMessage, 'user')
    inputMessage.value = ''
    scrollToBottom()
  }

  loading.value = true

  try {
    const ticket = await ticketApi.create({
      session_id: chatStore.sessionId,
      content: transferContent,
      transfer_reason: 'user_requested'
    })

    if (ticket?.session_id) {
      chatStore.setSessionId(ticket.session_id)
    }

    await refreshCurrentHistory()
    await checkHumanServiceStatus()
    await sessionStore.fetchSessions()
    ElMessage.success('已为您转接人工客服')
  } catch (error) {
    ElMessage.error('转人工失败')
  } finally {
    loading.value = false
  }
}

function handleQuickQuestion(question) {
  inputMessage.value = question
  handleSend()
}

async function handleNewSession() {
  try {
    if (chatStore.sessionId && chatStore.messages.length > 0) {
      await chatApi.clearSession(chatStore.sessionId)
    }
    chatStore.initSession()
    humanServiceStatus.value = {
      inService: false,
      status: null,
      adminName: null
    }
    ElMessage.success('已开始新对话')
  } catch (error) {
    chatStore.initSession()
  }
}

async function closeHumanServiceAndDisconnect() {
  if (!chatStore.sessionId) return

  try {
    await ticketApi.closeBySession(chatStore.sessionId)
    humanServiceStatus.value = {
      inService: false,
      status: null,
      adminName: null
    }
    await refreshCurrentHistory()
    await sessionStore.fetchSessions()
    ElMessage.success('已结束人工服务')
  } catch (error) {
    ElMessage.error('结束人工服务失败')
  }
}

async function handleCloseTicket() {
  if (!ticketId.value) return

  try {
    await ElMessageBox.confirm('确认结束当前人工服务工单吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })

    await ticketApi.close(ticketId.value)
    ElMessage.success('工单已关闭')
    await loadTicketInfo(true)
    await sessionStore.fetchSessions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('关闭工单失败')
    }
  }
}

function goBackToServiceDesk() {
  router.push('/service-desk')
}

function formatMessageContent(content) {
  if (!content) return ''
  return content.replace(/\n{3,}/g, '\n\n').trim()
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(
  () => route.query,
  async () => {
    await initAdminMode()
  },
  { immediate: false }
)

onMounted(async () => {
  await initAdminMode()
  if (!isAdminConversation.value && chatStore.sessionId) {
    await loadHistory()
  }
  scrollToBottom()
  startPolling()
  
  if (!isAdminConversation.value) {
    await checkHumanServiceStatus()
  }
})

onActivated(async () => {
  await initAdminMode()
  if (!isAdminConversation.value && chatStore.sessionId) {
    await loadHistory()
  }
  scrollToBottom()
  startPolling()
  
  if (!isAdminConversation.value) {
    checkHumanServiceStatus()
  }
})

onDeactivated(() => {
  stopPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
      radial-gradient(ellipse at 0% 0%, rgba(90, 139, 255, 0.1) 0%, transparent 50%),
      radial-gradient(ellipse at 100% 100%, rgba(118, 75, 162, 0.08) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
  }
  
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 800px;
    height: 800px;
    background: radial-gradient(circle, rgba(90, 139, 255, 0.05) 0%, transparent 70%);
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 0;
    animation: pulse 8s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.2);
  }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  position: relative;
  z-index: 1;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, 
      transparent 0%, 
      var(--primary-400) 20%, 
      var(--primary-600) 50%, 
      var(--primary-400) 80%, 
      transparent 100%
    );
    opacity: 0.8;
  }
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--spacing-xl);
  height: 60px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.8) 100%);
  border-bottom: 1px solid rgba(226, 232, 240, 0.5);
  flex-shrink: 0;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
      transparent 0%, 
      rgba(90, 139, 255, 0.3) 50%, 
      transparent 100%
    );
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  h2 {
    margin: 0;
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-800) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .user-label {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
  }
}

.human-service-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  background: linear-gradient(135deg, rgba(240, 253, 244, 0.95) 0%, rgba(209, 250, 229, 0.9) 100%);
  border-bottom: 1px solid rgba(167, 243, 208, 0.5);
  color: #15803d;
  font-size: var(--font-size-sm);
  font-weight: 500;
  flex-shrink: 0;
  animation: slideDown var(--duration-normal) var(--ease-out-expo);
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, var(--success-500), var(--success-600));
  }

  .el-icon {
    font-size: 18px;
    color: #16a34a;
  }

  span {
    flex: 1;
  }
}

.closed-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-xl);
  background: linear-gradient(135deg, rgba(255, 251, 235, 0.95) 0%, rgba(254, 243, 199, 0.9) 100%);
  border-bottom: 1px solid rgba(253, 230, 138, 0.5);
  color: #b45309;
  font-size: var(--font-size-sm);
  font-weight: 500;
  flex-shrink: 0;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, var(--warning-500), var(--warning-600));
  }

  .el-icon {
    font-size: 18px;
    color: #d97706;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.6) 100%);
  position: relative;
  min-height: 0;

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--gray-300);
    border-radius: var(--radius-full);

    &:hover {
      background: var(--gray-400);
    }
  }
}

.welcome-message {
  text-align: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  animation: fadeInUp var(--duration-slower) var(--ease-out-expo) both;

  .welcome-icon {
    width: 80px;
    height: 80px;
    margin: 0 auto var(--spacing-xl);
    background: linear-gradient(135deg, var(--primary-100), var(--primary-200));
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-600);
    box-shadow: var(--shadow-glow-primary);
    animation: float 6s ease-in-out infinite;
  }

  h3 {
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-3xl);
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-sm);
    letter-spacing: -0.03em;
  }

  p {
    color: var(--text-secondary);
    margin: 0 0 var(--spacing-xl);
    font-size: var(--font-size-lg);
  }
}

.admin-empty-message {
  text-align: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  animation: fadeInUp var(--duration-slower) var(--ease-out-expo) both;

  .welcome-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto var(--spacing-lg);
    background: var(--gray-100);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--gray-400);
  }

  h3 {
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-2xl);
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 var(--spacing-sm);
  }

  p {
    color: var(--text-secondary);
    margin: 0;
  }
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--spacing-sm);
  max-width: 800px;
  margin: 0 auto;
}

.quick-question {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--surface-0);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  transition: all var(--duration-normal) var(--ease-out-expo);
  box-shadow: var(--shadow-xs);

  &:hover {
    border-color: var(--primary-400);
    color: var(--primary-600);
    background: var(--primary-50);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md), var(--shadow-glow-primary);
  }

  &:active {
    transform: translateY(0);
  }
}

.message {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  position: relative;
  animation: messageSlideIn var(--duration-normal) var(--ease-out-expo) both;

  &.user {
    flex-direction: row-reverse;

    .message-content {
      align-items: flex-end;
    }

    .message-time {
      left: auto;
      right: 52px;
    }
  }

  &.assistant {
    .message-content {
      align-items: flex-start;
    }
  }

  &.human-service {
    .assistant-bubble {
      background: linear-gradient(135deg, var(--success-50) 0%, #f0fdf4 100%);
      border-color: #bbf7d0;
    }

    .message-source-label {
      color: var(--success-600);
    }
  }
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;

  :deep(.el-avatar) {
    border: 2px solid var(--border-light);
    box-shadow: var(--shadow-sm);
  }
}

.user-avatar {
  background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
}

.assistant-avatar {
  background: linear-gradient(135deg, var(--primary-400), var(--primary-500));
}

.human-avatar {
  background: linear-gradient(135deg, var(--success-500), var(--success-600));
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 72%;
}

.user-content {
  align-items: flex-end;
}

.message-source-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-bottom: 4px;
  padding-left: 4px;
  font-weight: 500;
}

.message-text {
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-lg);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--font-size-base);
}

.user-bubble {
  background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
  color: white;
  border-top-left-radius: var(--radius-lg);
  border-top-right-radius: 4px;
  border-bottom-left-radius: var(--radius-lg);
  border-bottom-right-radius: var(--radius-lg);
  box-shadow: 0 4px 14px rgba(74, 122, 255, 0.3);
}

.assistant-bubble {
  background: var(--surface-0);
  border: 1px solid var(--border-color);
  border-top-left-radius: 4px;
  border-top-right-radius: var(--radius-lg);
  border-bottom-left-radius: var(--radius-lg);
  border-bottom-right-radius: var(--radius-lg);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
  white-space: normal;

  :deep(p) {
    margin: 0 0 8px;
    line-height: 1.7;

    &:last-child {
      margin-bottom: 0 !important;
    }

    + p {
      margin-top: 4px;
    }
  }

  :deep(ul), :deep(ol) {
    margin: var(--spacing-sm) 0;
    padding-left: 20px;
  }

  :deep(code) {
    background: var(--gray-100);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.9em;
    color: var(--primary-600);
  }

  :deep(pre) {
    background: var(--gray-900);
    color: var(--gray-100);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: var(--spacing-sm) 0;

    code {
      background: transparent;
      padding: 0;
      color: inherit;
    }
  }

  :deep(blockquote) {
    border-left: 3px solid var(--primary-400);
    padding-left: var(--spacing-md);
    margin: var(--spacing-sm) 0;
    color: var(--text-secondary);
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: var(--spacing-sm) 0;
    font-size: var(--font-size-sm);

    th, td {
      border: 1px solid var(--border-color);
      padding: 6px 10px;
    }

    th {
      background: var(--gray-50);
      font-weight: 600;
    }
  }
}

.system-bubble {
  background: linear-gradient(135deg, var(--warning-50) 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
  color: var(--warning-700);
  font-size: var(--font-size-sm);
  text-align: center;
}

.source-actions {
  margin-top: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: rgba(248, 250, 252, 0.8);
  border-radius: var(--radius-md);
  border: 1px solid rgba(226, 232, 240, 0.6);
  backdrop-filter: blur(10px);
}

.feedback-actions {
  margin-top: var(--spacing-md);
  display: flex;
  justify-content: flex-end;
}

.feedback-buttons {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.feedback-btn {
  padding: 8px 16px;
  border-radius: var(--radius-full);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--text-tertiary);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.8);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);

  .feedback-text {
    font-size: var(--font-size-sm);
    font-weight: 500;
  }

  &:hover {
    background: white;
    color: var(--primary-600);
    border-color: var(--primary-300);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(90, 139, 255, 0.15);
  }

  &:active {
    transform: translateY(0);
  }

  svg {
    width: 18px;
    height: 18px;
    transition: transform 0.2s ease;
  }

  &:hover svg {
    transform: scale(1.1);
  }

  &.liked {
    color: #16a34a;
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border-color: #86efac;
    box-shadow: 0 2px 8px rgba(34, 197, 94, 0.2);

    &:hover {
      background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
      border-color: #4ade80;
      box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
      transform: translateY(-1px);
    }
  }

  &.disliked {
    color: #dc2626;
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border-color: #fca5a5;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);

    &:hover {
      background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
      border-color: #f87171;
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
      transform: translateY(-1px);
    }
  }
}

.message-time {
  position: absolute;
  bottom: -20px;
  left: 52px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.typing-indicator {
  display: flex;
  gap: 5px;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-0);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  border-top-left-radius: 4px;
  box-shadow: var(--shadow-sm);

  span {
    width: 8px;
    height: 8px;
    background: var(--primary-400);
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out both;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }

    &:nth-child(2) {
      animation-delay: -0.16s;
    }
  }
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.source-popover-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--gray-300);
    border-radius: 2px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: var(--gray-400);
  }
}

.source-item {
  padding: var(--spacing-md);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  transition: all 0.2s ease;
  cursor: pointer;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    border-color: var(--primary-400);
    background: var(--primary-50);
    transform: translateX(4px);
  }

  .source-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-xs);
  }

  .source-title {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--primary-600);
  }

  .source-desc {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    padding-left: 20px;
  }

  .source-preview {
    font-size: var(--font-size-xs);
    color: var(--text-muted);
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: var(--spacing-xs);
  }

  .source-footer {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: var(--font-size-xs);
    color: var(--primary-500);
    margin-top: var(--spacing-xs);

    .el-icon {
      font-size: 12px;
    }
  }
}

// 来源详情对话框样式
.source-detail-content {
  .detail-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 2px solid var(--primary-100);

    .detail-title-row {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      flex: 1;

      .detail-icon {
        color: var(--primary-600);
      }

      .detail-title {
        margin: 0;
        font-size: var(--font-size-xl);
        font-weight: 600;
        color: var(--text-primary);
        font-family: 'Outfit', sans-serif;
      }
    }
  }

  .detail-body {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .detail-section {
    .section-label {
      display: flex;
      align-items: center;
      gap: var(--spacing-xs);
      font-size: var(--font-size-sm);
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: var(--spacing-sm);
    }

    .section-content {
      .content-text {
        padding: var(--spacing-md);
        background: var(--gray-50);
        border-radius: var(--radius-md);
        border-left: 4px solid var(--primary-500);
        max-height: 300px;
        overflow-y: auto;
        font-size: var(--font-size-base);
        line-height: 1.8;
        color: var(--text-primary);

        :deep(p) {
          margin: var(--spacing-sm) 0;
        }

        :deep(code) {
          background: var(--gray-200);
          padding: 2px 6px;
          border-radius: var(--radius-sm);
          font-size: 0.9em;
          color: var(--primary-600);
        }

        :deep(pre) {
          background: var(--gray-900);
          color: var(--gray-100);
          padding: var(--spacing-md);
          border-radius: var(--radius-md);
          overflow-x: auto;
          margin: var(--spacing-sm) 0;

          code {
            background: transparent;
            padding: 0;
            color: inherit;
          }
        }
      }

      .info-row {
        display: flex;
        gap: var(--spacing-md);
        padding: var(--spacing-sm) 0;
        font-size: var(--font-size-sm);

        .info-label {
          font-weight: 600;
          color: var(--text-secondary);
          min-width: 80px;
        }

        .info-value {
          color: var(--text-primary);
        }
      }
    }
  }
}

.chat-input-area {
  padding: var(--spacing-md) var(--spacing-xl);
  background: rgba(255, 255, 255, 0.95);
  border-top: 1px solid rgba(226, 232, 240, 0.5);
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
      transparent 0%, 
      rgba(90, 139, 255, 0.2) 50%, 
      transparent 100%
    );
  }

  .chat-textarea {
    margin-bottom: var(--spacing-sm);

    :deep(.el-textarea__inner) {
      border: 1px solid rgba(226, 232, 240, 0.8);
      border-radius: var(--radius-lg);
      padding: var(--spacing-md);
      font-size: var(--font-size-base);
      line-height: 1.6;
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(10px);
      transition: all var(--duration-normal) var(--ease-out-expo);
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);

      &:focus {
        border-color: var(--primary-400);
        box-shadow: 0 0 0 3px rgba(90, 139, 255, 0.15), 0 4px 12px rgba(90, 139, 255, 0.1);
        background: white;
      }

      &::placeholder {
        color: var(--text-tertiary);
      }
    }
  }

  .input-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: var(--spacing-sm);

    .toolbar-left {
      display: flex;
      gap: var(--spacing-md);
      
      :deep(.el-button) {
        border-radius: var(--radius-full);
        font-weight: 500;
        padding: 8px 20px;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        
        &.el-button--warning {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-color: #fbbf24;
          color: #92400e;
          
          &:hover:not(.is-disabled) {
            background: linear-gradient(135deg, #fde68a 0%, #fcd34d 100%);
            border-color: #f59e0b;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
          }
          
          &:active:not(.is-disabled) {
            transform: translateY(0);
          }
        }
        
        &.el-button--danger {
          background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
          border-color: #f87171;
          color: #991b1b;
          
          &:hover:not(.is-disabled) {
            background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%);
            border-color: #ef4444;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
          }
        }
      }
    }

    .toolbar-right {
      display: flex;
      gap: var(--spacing-md);
      
      :deep(.el-button--primary) {
        background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
        border: none;
        border-radius: var(--radius-full);
        font-weight: 600;
        padding: 10px 28px;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 14px rgba(90, 139, 255, 0.35);
        position: relative;
        overflow: hidden;
        
        &::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 0;
          height: 0;
          background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
          transition: all 0.5s ease;
          transform: translate(-50%, -50%);
          border-radius: 50%;
        }
        
        &:hover:not(.is-disabled):not(:active) {
          background: linear-gradient(135deg, var(--primary-400) 0%, var(--primary-500) 100%);
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(90, 139, 255, 0.45);
          
          &::before {
            width: 300%;
            height: 300%;
          }
        }
        
        &:active:not(.is-disabled) {
          transform: translateY(0);
          box-shadow: 0 2px 8px rgba(90, 139, 255, 0.35);
        }
        
        &.is-loading,
        &.is-disabled {
          opacity: 0.7;
          cursor: not-allowed;
          transform: none !important;
          box-shadow: none;
        }
        
        .el-icon {
          margin-right: 6px;
          font-size: 16px;
        }
      }
    }
  }
}
</style>
