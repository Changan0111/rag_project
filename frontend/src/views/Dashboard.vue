<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>数据概览</h2>
      <el-button type="primary" plain @click="loadData">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 统计卡片区域 -->
    <div class="stats-cards">
      <div 
        class="stat-card" 
        v-for="(card, index) in statCards" 
        :key="card.key"
        :class="{ 'expanded': activeStatCard === card.key }"
        @click="openStatDetail(card.key)"
        :style="{ animationDelay: index * 100 + 'ms' }"
      >
        <div class="stat-icon" :class="card.iconClass">
          <el-icon :size="24"><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ overview[card.valueKey] }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
        <div class="expand-hint">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 图表区域第一行 -->
    <div class="charts-row">
      <!-- 知识库分类统计 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>知识库分类统计</h3>
        </div>
        <div class="chart-content">
          <div class="category-bars">
            <div 
              class="category-item clickable" 
              v-for="(count, category) in overview.knowledge_by_category" 
              :key="category"
              @click="openCategoryDetail(category, count)"
            >
              <div class="category-label">{{ getCategoryLabel(category) }}</div>
              <div class="category-bar-wrapper">
                <div 
                  class="category-bar" 
                  :style="{ width: getBarWidth(count) + '%' }"
                  :class="[category, { 'active': activeCategory === category }]"
                ></div>
              </div>
              <div class="category-count">{{ count }}</div>
              <el-icon class="expand-icon"><ArrowRight /></el-icon>
            </div>
          </div>
          
          <!-- 分类详情展开区域 -->
          <transition name="slide-down">
            <div class="category-detail-panel" v-if="activeCategory && categoryDetailVisible">
              <div class="detail-header">
                <h4>{{ getCategoryLabel(activeCategory) }} 详情</h4>
                <el-icon class="close-btn" @click.stop="closeCategoryDetail"><Close /></el-icon>
              </div>
              <div class="detail-content">
                <div class="detail-stats">
                  <div class="mini-stat">
                    <span class="mini-label">文档数量</span>
                    <span class="mini-value">{{ overview.knowledge_by_category[activeCategory] }}</span>
                  </div>
                  <div class="mini-stat">
                    <span class="mini-label">占比</span>
                    <span class="mini-value">{{ getCategoryPercentage(activeCategory) }}%</span>
                  </div>
                </div>
                <div class="detail-docs-list">
                  <div class="doc-item" v-for="i in 5" :key="i">
                    <el-icon><Document /></el-icon>
                    <span>{{ getCategoryLabel(activeCategory) }}相关文档示例 {{ i }}</span>
                    <el-tag size="small" type="info">已同步</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <!-- 近7天对话趋势 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>近7天对话趋势</h3>
        </div>
        <div class="chart-content">
          <div class="trend-chart">
            <div class="trend-bars">
              <div 
                class="trend-item" 
                v-for="item in overview.daily_conversations" 
                :key="item.date"
                @click="openTrendDetail(item)"
                :class="{ 'active': activeTrendDate === item.date }"
              >
                <div class="trend-bar-wrapper">
                  <div 
                    class="trend-bar" 
                    :style="{ height: getTrendHeight(item.count) + '%' }"
                    :class="{ 'active': activeTrendDate === item.date }"
                  >
                    <span class="trend-value">{{ item.count }}</span>
                  </div>
                </div>
                <div class="trend-label">{{ formatDate(item.date) }}</div>
              </div>
            </div>
          </div>
          
          <!-- 趋势详情悬浮卡片 -->
          <transition name="fade-slide">
            <div class="trend-detail-card" v-if="activeTrendDate && trendDetailVisible">
              <div class="trend-detail-header">
                <h4>{{ formatFullDate(activeTrendDate) }} 对话详情</h4>
                <el-icon class="close-btn" @click.stop="closeTrendDetail"><Close /></el-icon>
              </div>
              <div class="trend-detail-body">
                <div class="trend-metric">
                  <span class="metric-label">总对话数</span>
                  <span class="metric-value">{{ getActiveTrendCount() }}</span>
                </div>
                <div class="trend-breakdown">
                  <div class="breakdown-item">
                    <div class="breakdown-color product"></div>
                    <span>商品咨询</span>
                    <span class="breakdown-value">{{ Math.floor(getActiveTrendCount() * 0.4) }}</span>
                  </div>
                  <div class="breakdown-item">
                    <div class="breakdown-color policy"></div>
                    <span>售后政策</span>
                    <span class="breakdown-value">{{ Math.floor(getActiveTrendCount() * 0.35) }}</span>
                  </div>
                  <div class="breakdown-item">
                    <div class="breakdown-color logistics"></div>
                    <span>物流查询</span>
                    <span class="breakdown-value">{{ Math.floor(getActiveTrendCount() * 0.25) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <!-- 图表区域第二行 -->
    <div class="charts-row">
      <!-- 热门问题 TOP 10 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>热门问题 TOP 10</h3>
          <el-select v-model="hotDays" size="small" @change="loadHotQuestions" style="width: 120px">
            <el-option label="近7天" :value="7" />
            <el-option label="近15天" :value="15" />
            <el-option label="近30天" :value="30" />
          </el-select>
        </div>
        <div class="chart-content">
          <div class="hot-questions">
            <div 
              class="hot-item clickable" 
              v-for="(item, index) in hotQuestions" 
              :key="index"
              @click="toggleHotQuestion(index)"
              :class="{ 'expanded': expandedHotQuestion === index, 'has-similar': item.similar_questions?.length > 1 }"
            >
              <div class="hot-rank" :class="{ top: index < 3 }">{{ index + 1 }}</div>
              <div class="hot-content">
                <div class="question-text">{{ item.question }}</div>
                
                <!-- 展开的相似问题列表 -->
                <transition name="expand">
                  <div class="similar-questions-expanded" v-if="expandedHotQuestion === index && item.similar_questions?.length > 1">
                    <div class="similar-header">相似问题 ({{ item.similar_questions.length - 1 }}个)</div>
                    <div class="similar-list">
                      <div 
                        class="similar-item" 
                        v-for="(sq, sqIndex) in item.similar_questions.slice(1)" 
                        :key="sqIndex"
                      >
                        <el-icon><ChatDotRound /></el-icon>
                        <span>{{ sq }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- 未展开时的简略标签 -->
                  <div class="similar-questions" v-else-if="item.similar_questions && item.similar_questions.length > 1">
                    <el-tag 
                      v-for="(sq, sqIndex) in item.similar_questions.slice(0, 2)" 
                      :key="sqIndex"
                      size="small"
                      type="info"
                      class="similar-tag"
                    >
                      {{ sq.substring(0, 20) }}{{ sq.length > 20 ? '...' : '' }}
                    </el-tag>
                    <el-tag size="small" class="more-tag" v-if="item.similar_questions.length > 3">
                      +{{ item.similar_questions.length - 3 }}
                    </el-tag>
                  </div>
                </transition>

                <!-- 提问用户信息 -->
                <div class="question-meta" v-if="item.askers?.length > 0">
                  <div class="meta-item askers-info">
                    <el-icon><User /></el-icon>
                    <span>提问用户: {{ item.askers.join(', ') }}</span>
                  </div>
                  <div class="meta-item">
                    <el-icon><Document /></el-icon>
                    <span>来源: 知识库匹配</span>
                  </div>
                </div>
              </div>
              <div class="hot-count">{{ item.count }}次</div>
              <el-icon class="expand-chevron" :class="{ 'rotated': expandedHotQuestion === index }" v-if="item.similar_questions?.length > 1">
                <ArrowDown />
              </el-icon>
            </div>
            <el-empty v-if="hotQuestions.length === 0" description="暂无数据" />
          </div>
        </div>
      </div>

      <!-- 同步状态 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>同步状态</h3>
          <el-button type="danger" size="small" plain @click="handleClearSyncLogs">
            <el-icon><Delete /></el-icon>
            清除记录
          </el-button>
        </div>
        <div class="chart-content">
          <div class="sync-status">
            <div class="sync-summary">
              <div class="sync-item success">
                <el-icon><CircleCheck /></el-icon>
                <span>成功: {{ syncStatus.success_count }}</span>
              </div>
              <div class="sync-item failed">
                <el-icon><CircleClose /></el-icon>
                <span>失败: {{ syncStatus.failed_count }}</span>
              </div>
            </div>
            <div class="sync-logs">
              <div class="log-header">
                <span>最近同步记录</span>
              </div>
              <div class="log-list">
                <div 
                  class="log-item clickable" 
                  v-for="log in syncStatus.recent_logs" 
                  :key="log.id"
                  @click="toggleSyncLog(log)"
                  :class="{ 'expanded': expandedSyncLog?.id === log.id }"
                >
                  <div class="log-action">{{ getActionLabel(log.action) }}</div>
                  <div class="log-doc">文档ID: {{ log.doc_id }}</div>
                  <div class="log-status" :class="log.status">
                    {{ log.status === 'success' ? '成功' : '失败' }}
                  </div>
                  <div class="log-time">{{ formatTime(log.created_at) }}</div>
                  <el-icon class="expand-chevron" :class="{ 'rotated': expandedSyncLog?.id === log.id }">
                    <ArrowDown />
                  </el-icon>
                  
                  <!-- 同步日志详情展开 -->
                  <transition name="expand">
                    <div class="log-detail" v-if="expandedSyncLog?.id === log.id">
                      <div class="detail-section">
                        <div class="detail-title">文档信息</div>
                        <div class="detail-info">
                          <div class="info-row">
                            <span class="info-label">文档ID:</span>
                            <span class="info-value">{{ log.doc_id }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">操作类型:</span>
                            <span class="info-value">{{ getActionLabel(log.action) }}</span>
                          </div>
                          <div class="info-row">
                            <span class="info-label">执行时间:</span>
                            <span class="info-value">{{ formatFullTime(log.created_at) }}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div class="detail-section error-section" v-if="log.status === 'failed'">
                        <div class="detail-title">错误信息</div>
                        <div class="error-message">
                          <el-icon><WarningFilled /></el-icon>
                          <span>文档解析失败: 格式不兼容或内容为空</span>
                        </div>
                        <el-button type="warning" size="small" plain class="retry-btn">
                          <el-icon><RefreshRight /></el-icon>
                          重试同步
                        </el-button>
                      </div>
                      
                      <div class="detail-section success-section" v-else>
                        <div class="detail-title">同步结果</div>
                        <div class="success-message">
                          <el-icon><CircleCheckFilled /></el-icon>
                          <span>文档已成功同步至知识库</span>
                        </div>
                        <div class="doc-preview">
                          <el-icon><Document /></el-icon>
                          <span>预览文档内容片段...</span>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>
                <el-empty v-if="syncStatus.recent_logs?.length === 0" description="暂无记录" :image-size="60" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计卡片详情抽屉 -->
    <el-drawer
      v-model="statDrawerVisible"
      :title="currentStatCard?.label || '详情'"
      direction="rtl"
      size="420px"
      :modal="true"
      :modal-class="'stat-drawer-modal'"
    >
      <div class="stat-drawer-content" v-if="currentStatCard">
        <div class="drawer-overview">
          <div class="overview-number">{{ overview[currentStatCard.valueKey] }}</div>
          <div class="overview-label">{{ currentStatCard.label }}总数</div>
        </div>
        
        <div class="drawer-charts">
          <!-- 根据不同卡片类型展示不同的图表 -->
          <div class="chart-section" v-if="currentStatCard.key === 'users'">
            <h4>用户统计概览</h4>
            <div class="user-stats-grid">
              <div class="user-stat-item">
                <div class="stat-icon-wrapper active">
                  <el-icon><UserFilled /></el-icon>
                </div>
                <div class="stat-text">
                  <span class="stat-number">{{ overview.active_users || 0 }}</span>
                  <span class="stat-desc">活跃用户</span>
                </div>
              </div>
              <div class="user-stat-item">
                <div class="stat-icon-wrapper new">
                  <el-icon><Plus /></el-icon>
                </div>
                <div class="stat-text">
                  <span class="stat-number">+{{ overview.week_new_users || 0 }}</span>
                  <span class="stat-desc">本周新增</span>
                </div>
              </div>
              <div class="user-stat-item">
                <div class="stat-icon-wrapper today">
                  <el-icon><Calendar /></el-icon>
                </div>
                <div class="stat-text">
                  <span class="stat-number">+{{ overview.today_new_users || 0 }}</span>
                  <span class="stat-desc">今日注册</span>
                </div>
              </div>
            </div>

            <h4 style="margin-top: var(--spacing-lg);">最近注册用户</h4>
            <div class="user-list">
              <div
                class="user-item"
                v-for="(user, index) in recentUsers"
                :key="user.id || index"
              >
                <div class="user-avatar">
                  {{ user.username.charAt(0) }}
                </div>
                <div class="user-info">
                  <div class="user-name">{{ user.username }}</div>
                  <div class="user-meta">
                    <span>📱 {{ user.phone }}</span>
                    <el-tag 
                      size="small" 
                      :type="isRecentLogin(user.last_login_at) ? 'success' : 'info'" 
                      round
                      effect="plain"
                    >
                      {{ formatLastLogin(user.last_login_at) }}
                    </el-tag>
                  </div>
                </div>
                <div class="user-time">注册于 {{ formatRelativeTime(user.created_at) }}</div>
              </div>
            </div>
          </div>
          
          <div class="chart-section" v-else-if="currentStatCard.key === 'knowledge'">
            <h4>知识库分布</h4>
            <div class="pie-chart-container">
              <div class="pie-chart-wrapper">
                <div 
                  class="pie-chart" 
                  :style="{ background: pieChartGradient }"
                >
                  <div class="pie-center">
                    <div class="pie-total">{{ overview.total_knowledge }}</div>
                    <div class="pie-label">总文档</div>
                  </div>
                </div>
              </div>
              <div class="pie-legend">
                <div 
                  class="legend-item" 
                  v-for="(count, cat) in overview.knowledge_by_category" 
                  :key="cat"
                >
                  <div class="legend-color" :class="cat"></div>
                  <span class="legend-name">{{ getCategoryLabel(cat) }}</span>
                  <span class="legend-value">{{ count }}</span>
                  <span class="legend-percent">{{ getCategoryPercentage(cat) }}%</span>
                </div>
              </div>
            </div>
          </div>

          <div class="chart-section" v-else-if="currentStatCard.key === 'conversations'">
            <h4>对话类型分布</h4>
            
            <!-- 饼状图 -->
            <div v-if="conversationStats.type_distribution.length > 0" class="pie-chart-container">
              <div 
                class="pie-chart" 
                :style="{ background: generatePieGradient() }"
              ></div>
              <div class="pie-legend">
                <div 
                  class="legend-item clickable"
                  v-for="item in conversationStats.type_distribution"
                  :key="item.category"
                  @click="showConversationsByType(item.category)"
                >
                  <div class="legend-color" :class="item.category"></div>
                  <span class="legend-name">{{ getCategoryLabel(item.category) }}</span>
                  <span class="legend-value">{{ item.count }}个</span>
                  <span class="legend-percent">{{ item.percent }}%</span>
                </div>
              </div>
            </div>
            
            <el-empty v-else description="暂无对话数据" :image-size="80" />
            
            <div class="chart-stats" v-if="conversationStats.type_distribution.length > 0">
              <div class="stat-row">
                <span>平均响应时间</span>
                <strong>{{ conversationStats.avg_response_time }}秒</strong>
              </div>
              <div class="stat-row">
                <span>平均对话轮次</span>
                <strong>{{ conversationStats.avg_turns }}轮</strong>
              </div>
            </div>
          </div>
          
          <div class="chart-section" v-else-if="currentStatCard.key === 'today'">
            <h4>今日对话消息</h4>
            <div class="today-messages-card">
              <div class="messages-scroll" v-if="todayRecentMessages.length > 0">
                <div 
                  class="message-item" 
                  v-for="msg in todayRecentMessages" 
                  :key="msg.id"
                >
                  <div class="msg-avatar">{{ msg.username.charAt(0) }}</div>
                  <div class="msg-body">
                    <div class="msg-header">
                      <span class="msg-username">{{ msg.username }}</span>
                      <span class="msg-time">{{ formatDateTime(msg.created_at) }}</span>
                    </div>
                    <div class="msg-content">{{ msg.content }}</div>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无今日对话" :image-size="60" />
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
    
    <!-- 对话类型详情弹窗 -->
    <el-dialog
      v-model="conversationTypeDialogVisible"
      :title="`${getCategoryLabel(selectedConversationType)} - 会话列表`"
      width="700px"
      :close-on-click-modal="true"
    >
      <div v-if="conversationsByType.length > 0" class="conversation-list">
        <div 
          v-for="conv in conversationsByType" 
          :key="conv.session_id"
          class="conversation-item clickable"
          @click="showConversationDetail(conv)"
        >
          <div class="conversation-header">
            <div class="user-info">
              <el-icon><User /></el-icon>
              <span class="username">{{ conv.username }}</span>
              <span v-if="conv.phone" class="phone">{{ conv.phone }}</span>
            </div>
            <div class="conversation-meta">
              <el-tag size="small">{{ conv.message_count }}轮对话</el-tag>
              <span class="time">{{ formatDateTime(conv.last_active) }}</span>
            </div>
          </div>
          <div class="conversation-preview">
            {{ conv.first_message }}
          </div>
        </div>
      </div>
      <el-empty v-else description="该类型暂无会话数据" />
    </el-dialog>
    
    <!-- 对话详情弹窗 -->
    <el-dialog
      v-model="conversationDetailDialogVisible"
      title="对话详情"
      width="800px"
      :close-on-click-modal="true"
    >
      <div v-if="selectedConversationDetail" class="conversation-detail-content">
        <div class="detail-header">
          <div class="detail-user">
            <el-icon><User /></el-icon>
            <span>{{ selectedConversationDetail.username }}</span>
            <span v-if="selectedConversationDetail.phone" class="phone">({{ selectedConversationDetail.phone }})</span>
          </div>
          <div class="detail-time">
            会话时间：{{ formatDateTime(selectedConversationDetail.created_at) }} - {{ formatDateTime(selectedConversationDetail.last_active) }}
          </div>
        </div>
        
        <div class="chat-messages" ref="chatMessagesContainer">
          <div 
            v-for="(msg, idx) in selectedConversationDetail.messages" 
            :key="idx"
            :class="['message', msg.role]"
          >
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'user'"><UserFilled /></el-icon>
              <el-icon v-else><Service /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-time">{{ formatDateTime(msg.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, User, UserFilled, Document, ChatDotRound, Calendar,
  ArrowRight, ArrowDown, Close, Star, Delete, Plus,
  CircleCheck, CircleClose, WarningFilled, CircleCheckFilled,
  RefreshRight, ShoppingCart, Service, Van
} from '@element-plus/icons-vue'
import { statsApi } from '@/api/modules'

const overview = ref({
  total_users: 0,
  total_knowledge: 0,
  total_conversations: 0,
  today_conversations: 0,
  knowledge_by_category: {},
  daily_conversations: []
})

const hotQuestions = ref([])
const hotDays = ref(7)

const syncStatus = ref({
  success_count: 0,
  failed_count: 0,
  recent_logs: []
})

// 展开状态管理
const statDrawerVisible = ref(false)
const currentStatCard = ref(null)
const activeStatCard = ref(null)

const activeCategory = ref(null)
const categoryDetailVisible = ref(false)

const activeTrendDate = ref(null)
const trendDetailVisible = ref(false)

const expandedHotQuestion = ref(null)

const expandedSyncLog = ref(null)

// 最近注册用户数据（从API获取）
const recentUsers = ref([])

// 对话统计数据（从API获取）
const conversationStats = ref({
  total_sessions: 0,
  type_distribution: [],
  avg_response_time: 0,
  avg_turns: 0
})

// 对话类型详情弹窗
const conversationTypeDialogVisible = ref(false)
const selectedConversationType = ref(null)
const conversationsByType = ref([])

// 对话详情弹窗
const conversationDetailDialogVisible = ref(false)
const selectedConversationDetail = ref(null)

// 今日对话统计数据（从API获取）
const todayRecentMessages = ref([])

// 统计卡片配置
const statCards = computed(() => [
  {
    key: 'users',
    label: '注册用户',
    valueKey: 'total_users',
    icon: 'User',
    iconClass: 'users'
  },
  {
    key: 'knowledge',
    label: '知识文档',
    valueKey: 'total_knowledge',
    icon: 'Document',
    iconClass: 'knowledge'
  },
  {
    key: 'conversations',
    label: '总对话数',
    valueKey: 'total_conversations',
    icon: 'ChatDotRound',
    iconClass: 'conversations'
  },
  {
    key: 'today',
    label: '今日对话',
    valueKey: 'today_conversations',
    icon: 'Calendar',
    iconClass: 'today'
  }
])

const maxKnowledgeCount = computed(() => {
  const values = Object.values(overview.value.knowledge_by_category)
  return Math.max(...values, 1)
})

// 饼状图渐变（conic-gradient）
const pieChartGradient = computed(() => {
  const categories = overview.value.knowledge_by_category
  const total = Object.values(categories).reduce((a, b) => a + b, 0)
  if (total === 0) return '#f1f5f9'

  const colorMap = {
    'product': '#667eea',
    'policy': '#f093fb',
    'logistics': '#43e97b',
    'service': '#fbbf24'
  }

  let currentAngle = 0
  const gradientParts = []

  Object.entries(categories).forEach(([category, count]) => {
    const percentage = (count / total) * 100
    const startAngle = currentAngle
    const endAngle = currentAngle + percentage

    gradientParts.push(`${colorMap[category] || '#94a3b8'} ${startAngle}% ${endAngle}%`)

    currentAngle = endAngle
  })

  return `conic-gradient(${gradientParts.join(', ')})`
})

const maxTrendCount = computed(() => {
  const values = overview.value.daily_conversations.map(d => d.count)
  return Math.max(...values, 1)
})

function getBarWidth(count) {
  return (count / maxKnowledgeCount.value) * 100
}

function getTrendHeight(count) {
  return (count / maxTrendCount.value) * 100
}

function getCategoryLabel(category) {
  const labels = {
    'product': '商品知识',
    'policy': '售后政策',
    'logistics': '物流信息',
    'service': '服务支持'
  }
  return labels[category] || category
}

function getCategoryPercentage(category) {
  const total = Object.values(overview.value.knowledge_by_category).reduce((a, b) => a + b, 0)
  if (total === 0) return 0
  return ((overview.value.knowledge_by_category[category] / total) * 100).toFixed(1)
}

function getActionLabel(action) {
  const labels = {
    'insert': '新增',
    'update': '更新',
    'delete': '删除'
  }
  return labels[action] || action
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function formatFullDate(dateStr) {
  const date = new Date(dateStr)
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(dateStr) {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

function formatFullTime(dateStr) {
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

// 统计卡片展开功能
function openStatDetail(key) {
  currentStatCard.value = statCards.value.find(card => card.key === key)
  activeStatCard.value = key
  statDrawerVisible.value = true
}

// 知识库分类展开功能
function openCategoryDetail(category, count) {
  if (activeCategory.value === category && categoryDetailVisible.value) {
    closeCategoryDetail()
  } else {
    activeCategory.value = category
    categoryDetailVisible.value = true
  }
}

function closeCategoryDetail() {
  categoryDetailVisible.value = false
  setTimeout(() => {
    activeCategory.value = null
  }, 300)
}

// 趋势图展开功能
function openTrendDetail(item) {
  if (activeTrendDate.value === item.date && trendDetailVisible.value) {
    closeTrendDetail()
  } else {
    activeTrendDate.value = item.date
    trendDetailVisible.value = true
  }
}

function closeTrendDetail() {
  trendDetailVisible.value = false
  setTimeout(() => {
    activeTrendDate.value = null
  }, 300)
}

function getActiveTrendCount() {
  const item = overview.value.daily_conversations.find(d => d.date === activeTrendDate.value)
  return item ? item.count : 0
}

// 热门问题展开功能
function toggleHotQuestion(index) {
  if (expandedHotQuestion.value === index) {
    expandedHotQuestion.value = null
  } else {
    expandedHotQuestion.value = index
  }
}

// 同步日志展开功能
function toggleSyncLog(log) {
  if (expandedSyncLog.value?.id === log.id) {
    expandedSyncLog.value = null
  } else {
    expandedSyncLog.value = log
  }
}

async function loadRecentUsers() {
  try {
    const data = await statsApi.getRecentUsers({ limit: 10 })
    recentUsers.value = data
  } catch (error) {
    console.error('加载最近用户失败:', error)
  }
}

async function loadConversationStats() {
  try {
    const data = await statsApi.getConversationStats()
    conversationStats.value = data
  } catch (error) {
    console.error('加载对话统计失败:', error)
  }
}

async function loadTodayRecentMessages() {
  try {
    const data = await statsApi.getTodayRecentMessages({ limit: 20 })
    todayRecentMessages.value = data
  } catch (error) {
    console.error('加载今日对话消息失败:', error)
  }
}

async function showConversationsByType(category) {
  selectedConversationType.value = category
  conversationTypeDialogVisible.value = true
  
  try {
    const data = await statsApi.getConversationsByType(category)
    conversationsByType.value = data
  } catch (error) {
    console.error('加载会话列表失败:', error)
    ElMessage.error('加载会话列表失败')
  }
}

async function showConversationDetail(conv) {
  try {
    const messages = await statsApi.getSessionDetail(conv.session_id)
    selectedConversationDetail.value = {
      ...conv,
      messages: messages
    }
    conversationDetailDialogVisible.value = true
  } catch (error) {
    console.error('加载对话详情失败:', error)
    ElMessage.error('加载对话详情失败')
  }
}

function generatePieGradient() {
  if (!conversationStats.value.type_distribution.length) return '#f0f0f0'
  
  let currentAngle = 0
  const segments = conversationStats.value.type_distribution.map(item => {
    const percentage = item.percent / 100
    const startAngle = currentAngle
    currentAngle += percentage * 360
    return `${getCategoryColor(item.category)} ${startAngle}deg ${currentAngle}deg`
  })
  
  return `conic-gradient(${segments.join(', ')})`
}

function getCategoryColor(category) {
  const colors = {
    'product': '#4A7AFF',
    'policy': '#FF6B9D',
    'logistics': '#00D4AA',
    'service': '#FFA940',
    'other': '#909399'
  }
  return colors[category] || colors['other']
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatRelativeTime(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 30) return `${diffDays}天前`
  return dateStr.split('T')[0]
}

function isRecentLogin(updatedAt) {
  if (!updatedAt) return false
  const diffMs = new Date() - new Date(updatedAt)
  const diffDays = Math.floor(diffMs / 86400000)
  return diffDays <= 7
}

function formatLastLogin(updatedAt) {
  if (!updatedAt) return '从未登录'
  
  const date = new Date(updatedAt)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / 86400000)
  
  // 超过7天：显示X天前登录
  if (diffDays > 7) {
    return `${diffDays}天前登录`
  }
  
  // 7天内：显示具体日期（月日 + 时间）
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  
  if (diffDays === 0) {
    return '今天登录'
  } else if (diffDays === 1) {
    return '昨天登录'
  } else {
    return `${month}月${day}日登录`
  }
}

async function loadData() {
  try {
    const [overviewData, syncData] = await Promise.all([
      statsApi.getOverview(),
      statsApi.getSyncStatus()
    ])
    overview.value = overviewData
    syncStatus.value = syncData
    await Promise.all([
      loadHotQuestions(),
      loadRecentUsers(),
      loadConversationStats(),
      loadTodayRecentMessages()
    ])
  } catch (error) {
    ElMessage.error('加载数据失败')
  }
}

async function loadHotQuestions() {
  try {
    const data = await statsApi.getHotQuestions({ days: hotDays.value })
    hotQuestions.value = data
  } catch (error) {
    console.error('加载热门问题失败:', error)
  }
}

async function handleClearSyncLogs() {
  try {
    await ElMessageBox.confirm('确定要清除所有同步记录吗？此操作不可恢复。', '清除确认', {
      confirmButtonText: '确定清除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const data = await statsApi.clearSyncLogs()
    ElMessage.success(data.message)
    syncStatus.value = {
      success_count: 0,
      failed_count: 0,
      recent_logs: []
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.dashboard-page {
  height: 100%;
  padding: var(--spacing-xl);
  overflow-y: auto;
  box-sizing: border-box;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(circle at 20% 50%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(236, 72, 153, 0.03) 0%, transparent 50%);
    pointer-events: none;
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  position: relative;
  z-index: 1;

  h2 {
    margin: 0;
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  position: relative;
  z-index: 1;
}

.stat-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.6);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) both;
  cursor: pointer;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, transparent 0%, rgba(102, 126, 234, 0.05) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.18), 0 4px 12px rgba(0, 0, 0, 0.08);

    &::before {
      opacity: 1;
    }

    .expand-hint {
      opacity: 1;
      transform: translateX(0);
    }

    .stat-icon {
      transform: scale(1.1) rotate(5deg);
    }
  }

  &:active {
    transform: translateY(-3px) scale(0.98);
  }

  &.expanded {
    border-color: #667eea;
    box-shadow: 0 12px 40px rgba(102, 126, 234, 0.25);
  }

  &:nth-child(1) { animation-delay: 0ms; }
  &:nth-child(2) { animation-delay: 100ms; }
  &:nth-child(3) { animation-delay: 200ms; }
  &:nth-child(4) { animation-delay: 300ms; }

  .stat-icon {
    width: 64px;
    height: 64px;
    border-radius: var(--radius-xl);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    z-index: 1;

    &::after {
      content: '';
      position: absolute;
      inset: -2px;
      border-radius: inherit;
      background: inherit;
      filter: blur(12px);
      opacity: 0.4;
      z-index: -1;
    }

    &.users { 
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    &.knowledge { 
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    &.conversations { 
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    &.today { 
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
  }

  .stat-info {
    flex: 1;
    position: relative;
    z-index: 1;

    .stat-value {
      font-family: 'Outfit', sans-serif;
      font-size: var(--font-size-3xl);
      font-weight: 700;
      color: #1a1a2e;
      line-height: 1.2;
      letter-spacing: -0.02em;
    }

    .stat-label {
      font-size: var(--font-size-sm);
      color: #64748b;
      margin-top: 4px;
      font-weight: 500;
    }
  }

  .expand-hint {
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%) translateX(10px);
    opacity: 0;
    transition: all 0.3s ease;
    color: #94a3b8;
    font-size: 18px;
  }
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  position: relative;
  z-index: 1;
}

.chart-card {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.6);
  overflow: hidden;
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) both;
  animation-delay: 400ms;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 8px 32px rgba(102, 126, 234, 0.12);
  }

  .chart-header {
    padding: var(--spacing-md) var(--spacing-lg);
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);

    h3 {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      font-size: var(--font-size-lg);
      font-weight: 600;
      color: #1e293b;
    }
  }

  .chart-content {
    padding: var(--spacing-lg);
    position: relative;
  }
}

.category-bars {
  .category-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
    padding: 8px 12px;
    border-radius: var(--radius-md);
    transition: all 0.3s ease;

    &:last-child {
      margin-bottom: 0;
    }

    &.clickable {
      cursor: pointer;

      &:hover {
        background: rgba(102, 126, 234, 0.04);

        .category-bar {
          filter: brightness(1.1);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .expand-icon {
          opacity: 1;
          transform: translateX(0);
        }
      }

      &.active {
        background: rgba(102, 126, 234, 0.06);
      }
    }

    .category-label {
      width: 80px;
      font-size: var(--font-size-sm);
      color: #475569;
      font-weight: 600;
    }

    .category-bar-wrapper {
      flex: 1;
      height: 28px;
      background: #f1f5f9;
      border-radius: var(--radius-full);
      overflow: hidden;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.04);
    }

    .category-bar {
      height: 100%;
      border-radius: var(--radius-full);
      transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;

      &::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        animation: shimmer 2s infinite;
      }

      &.product { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); }
      &.policy { background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); }
      &.logistics { background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%); }

      &.active {
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
      }
    }

    .category-count {
      width: 40px;
      text-align: right;
      font-size: var(--font-size-sm);
      font-weight: 700;
      color: #1e293b;
    }

    .expand-icon {
      opacity: 0;
      transform: translateX(-8px);
      transition: all 0.3s ease;
      color: #94a3b8;
      font-size: 16px;
    }
  }
}

// 分类详情展开面板
.category-detail-panel {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(8px);

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);

    h4 {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      font-size: var(--font-size-base);
      font-weight: 600;
      color: #667eea;
    }

    .close-btn {
      cursor: pointer;
      color: #94a3b8;
      transition: all 0.2s ease;

      &:hover {
        color: #ef4444;
        transform: rotate(90deg);
      }
    }
  }

  .detail-content {
    .detail-stats {
      display: flex;
      gap: var(--spacing-xl);
      margin-bottom: var(--spacing-md);

      .mini-stat {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .mini-label {
          font-size: var(--font-size-xs);
          color: #64748b;
          font-weight: 500;
        }

        .mini-value {
          font-size: var(--font-size-xl);
          font-weight: 700;
          color: #1e293b;
          font-family: 'Outfit', sans-serif;
        }
      }
    }

    .detail-docs-list {
      .doc-item {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        padding: 8px 0;
        border-bottom: 1px solid rgba(226, 232, 240, 0.5);
        font-size: var(--font-size-sm);
        color: #475569;

        &:last-child {
          border-bottom: none;
        }

        .el-icon {
          color: #667eea;
        }
      }
    }
  }
}

// 对话类型分布 - 饼状图
.pie-chart-container {
  display: flex;
  align-items: center;
  gap: 30px;
  margin: 20px 0;
  
  .pie-chart {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    position: relative;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    
    &::after {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 80px;
      height: 80px;
      background: white;
      border-radius: 50%;
    }
  }
  
  .pie-legend {
    flex: 1;
    
    .legend-item {
      display: flex;
      align-items: center;
      padding: 10px 12px;
      margin-bottom: 8px;
      background: #f8fafc;
      border-radius: 8px;
      transition: all 0.3s ease;
      
      &.clickable {
        cursor: pointer;
        
        &:hover {
          background: #e2e8f0;
          transform: translateX(4px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
      }
      
      .legend-color {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        margin-right: 10px;
        flex-shrink: 0;
        
        &.product { background: #4A7AFF; }
        &.policy { background: #FF6B9D; }
        &.logistics { background: #00D4AA; }
        &.service { background: #FFA940; }
        &.other { background: #909399; }
      }
      
      .legend-name {
        flex: 1;
        font-weight: 500;
        color: #334155;
      }
      
      .legend-value {
        color: #64748b;
        font-size: 13px;
        margin-right: 15px;
      }
      
      .legend-percent {
        color: #475569;
        font-weight: 600;
        font-size: 14px;
        min-width: 45px;
        text-align: right;
      }
    }
  }
}

// 对话列表弹窗
.conversation-list {
  max-height: 500px;
  overflow-y: auto;
  
  .conversation-item {
    padding: 16px;
    border-bottom: 1px solid #f1f5f9;
    transition: all 0.2s ease;
    
    &:last-child {
      border-bottom: none;
    }
    
    &.clickable {
      cursor: pointer;
      
      &:hover {
        background: #f8fafc;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      }
    }
    
    .conversation-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .username {
          font-weight: 600;
          color: #1e293b;
        }
        
        .phone {
          color: #64748b;
          font-size: 13px;
        }
      }
      
      .conversation-meta {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .time {
          color: #94a3b8;
          font-size: 13px;
        }
      }
    }
    
    .conversation-preview {
      color: #64748b;
      font-size: 14px;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
  }
}

// 对话详情弹窗
.conversation-detail-content {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 2px solid #f1f5f9;
    margin-bottom: 20px;
    
    .detail-user {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
      
      .phone {
        color: #64748b;
        font-weight: 400;
        font-size: 14px;
      }
    }
    
    .detail-time {
      color: #64748b;
      font-size: 13px;
    }
  }
  
  .chat-messages {
    max-height: 500px;
    overflow-y: auto;
    padding: 16px;
    background: #f8fafc;
    border-radius: 12px;
    
    .message {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      &.user {
        flex-direction: row-reverse;
        
        .message-content {
          background: #4A7AFF;
          color: white;
          
          .message-time {
            color: rgba(255, 255, 255, 0.8);
            text-align: right;
          }
        }
      }
      
      &.assistant {
        .message-content {
          background: white;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
      }
      
      .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #e2e8f0;
        color: #64748b;
        flex-shrink: 0;
        font-size: 18px;
      }
      
      .message-content {
        max-width: 70%;
        padding: 12px 16px;
        border-radius: 18px;
        
        .message-text {
          line-height: 1.5;
          margin-bottom: 6px;
          word-break: break-word;
        }
        
        .message-time {
          font-size: 11px;
          color: #94a3b8;
        }
      }
    }
  }
}

.trend-chart {
  .trend-bars {
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    height: 180px;
    padding: var(--spacing-md) 0;

    .trend-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex: 1;
      cursor: pointer;
      padding: 4px;
      border-radius: var(--radius-md);
      transition: all 0.3s ease;

      &:hover {
        background: rgba(102, 126, 234, 0.04);

        .trend-bar {
          filter: brightness(1.15);
          box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
        }
      }

      &.active {
        background: rgba(102, 126, 234, 0.08);
      }

      .trend-bar-wrapper {
        width: 48px;
        height: 160px;
        display: flex;
        align-items: flex-end;
        justify-content: center;

        .trend-bar {
          width: 100%;
          background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
          border-radius: var(--radius-md) var(--radius-md) 0 0;
          min-height: 4px;
          position: relative;
          transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 -4px 12px rgba(102, 126, 234, 0.3);
          cursor: pointer;

          &::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.2) 0%, transparent 50%);
            border-radius: inherit;
          }

          &.active {
            box-shadow: 0 -8px 32px rgba(102, 126, 234, 0.5);
            transform: scaleX(1.1);
          }

          .trend-value {
            position: absolute;
            top: -28px;
            left: 50%;
            transform: translateX(-50%);
            font-size: var(--font-size-xs);
            font-weight: 700;
            color: #667eea;
            background: white;
            padding: 2px 8px;
            border-radius: var(--radius-full);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
          }
        }
      }

      .trend-label {
        margin-top: var(--spacing-sm);
        font-size: var(--font-size-xs);
        color: #94a3b8;
        font-weight: 600;
      }
    }
  }
}

// 趋势详情悬浮卡片
.trend-detail-card {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: var(--spacing-md);
  padding: var(--spacing-lg);
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: 0 12px 48px rgba(102, 126, 234, 0.2), 0 4px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(102, 126, 234, 0.15);
  min-width: 320px;
  z-index: 10;

  .trend-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);

    h4 {
      margin: 0;
      font-family: 'Outfit', sans-serif;
      font-size: var(--font-size-base);
      font-weight: 600;
      color: #1e293b;
    }

    .close-btn {
      cursor: pointer;
      color: #94a3b8;
      transition: all 0.2s ease;

      &:hover {
        color: #ef4444;
        transform: rotate(90deg);
      }
    }
  }

  .trend-detail-body {
    .trend-metric {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: var(--spacing-md);
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
      border-radius: var(--radius-md);
      margin-bottom: var(--spacing-md);

      .metric-label {
        font-size: var(--font-size-sm);
        color: #64748b;
        font-weight: 500;
      }

      .metric-value {
        font-size: var(--font-size-2xl);
        font-weight: 700;
        color: #667eea;
        font-family: 'Outfit', sans-serif;
      }
    }

    .trend-breakdown {
      .breakdown-item {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        padding: 8px 0;
        font-size: var(--font-size-sm);
        color: #475569;

        .breakdown-color {
          width: 12px;
          height: 12px;
          border-radius: 3px;

          &.product { background: linear-gradient(135deg, #667eea, #764ba2); }
          &.policy { background: linear-gradient(135deg, #f093fb, #f5576c); }
          &.logistics { background: linear-gradient(135deg, #43e97b, #38f9d7); }
        }

        span:first-of-type {
          flex: 1;
        }

        .breakdown-value {
          font-weight: 700;
          color: #1e293b;
        }
      }
    }
  }
}

.hot-questions {
  .hot-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    border-radius: var(--radius-md);
    transition: all 0.3s ease;
    cursor: default;

    &:last-child {
      border-bottom: none;
    }

    &.has-similar {
      cursor: pointer;

      &:hover {
        background: rgba(102, 126, 234, 0.03);
        transform: translateX(4px);
      }

      &.expanded {
        background: rgba(102, 126, 234, 0.05);
        border-left: 3px solid #667eea;
      }
    }

    .hot-rank {
      width: 28px;
      height: 28px;
      border-radius: var(--radius-md);
      background: #f1f5f9;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: var(--font-size-sm);
      font-weight: 700;
      color: #94a3b8;
      flex-shrink: 0;
      transition: all 0.3s ease;

      &.top {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
      }
    }

    .hot-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
      overflow: hidden;
      min-width: 0;

      .question-text {
        font-size: var(--font-size-sm);
        font-weight: 600;
        color: #1e293b;
        line-height: 1.5;
      }

      .similar-questions-expanded {
        .similar-header {
          font-size: var(--font-size-xs);
          color: #667eea;
          font-weight: 600;
          margin-bottom: 8px;
          padding-left: 4px;
        }

        .similar-list {
          display: flex;
          flex-direction: column;
          gap: 6px;

          .similar-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            background: rgba(102, 126, 234, 0.04);
            border-radius: var(--radius-sm);
            font-size: var(--font-size-xs);
            color: #475569;
            transition: all 0.2s ease;

            &:hover {
              background: rgba(102, 126, 234, 0.08);
              transform: translateX(4px);
            }

            .el-icon {
              color: #667eea;
              font-size: 14px;
            }
          }
        }
      }

      .question-meta {
        display: flex;
        gap: var(--spacing-md);
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px dashed rgba(102, 126, 234, 0.2);

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: var(--font-size-xs);
          color: #64748b;

          .el-icon {
            color: #667eea;
          }
        }
      }

      .similar-questions {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;

        .similar-tag {
          font-size: var(--font-size-xs);
        }

        .more-tag {
          background: #f1f5f9;
          border-color: #e2e8f0;
          color: #64748b;
        }
      }
    }

    .hot-count {
      font-size: var(--font-size-sm);
      font-weight: 700;
      color: #667eea;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .expand-chevron {
      color: #cbd5e1;
      font-size: 16px;
      flex-shrink: 0;
      margin-top: 2px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &.rotated {
        transform: rotate(180deg);
        color: #667eea;
      }
    }
  }
}

.sync-status {
  .sync-summary {
    display: flex;
    gap: var(--spacing-xl);
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);

    .sync-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-size: var(--font-size-sm);
      font-weight: 600;

      .el-icon {
        font-size: 18px;
      }

      &.success {
        color: #059669;

        .el-icon {
          color: #10b981;
        }
      }

      &.failed {
        color: #dc2626;

        .el-icon {
          color: #ef4444;
        }
      }
    }
  }

  .sync-logs {
    .log-header {
      font-size: var(--font-size-sm);
      color: #64748b;
      margin-bottom: var(--spacing-sm);
      padding-bottom: var(--spacing-sm);
      border-bottom: 1px solid rgba(226, 232, 240, 0.6);
      font-weight: 600;
    }

    .log-list {
      max-height: 280px;
      overflow-y: auto;

      .log-item {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
        padding: var(--spacing-sm) var(--spacing-md);
        font-size: var(--font-size-sm);
        border-radius: var(--radius-md);
        transition: all 0.3s ease;
        cursor: default;
        position: relative;

        &.clickable {
          cursor: pointer;

          &:hover {
            background: rgba(102, 126, 234, 0.03);
          }

          &.expanded {
            background: rgba(102, 126, 234, 0.05);
            border-left: 3px solid #667eea;
            flex-wrap: wrap;
          }
        }

        .log-action {
          width: 40px;
          color: #64748b;
          font-weight: 600;
        }

        .log-doc {
          flex: 1;
          color: #475569;
          font-size: var(--font-size-xs);
          font-family: 'SF Mono', monospace;
        }

        .log-status {
          width: 40px;
          text-align: center;
          font-weight: 700;
          font-size: var(--font-size-xs);

          &.success {
            color: #059669;
          }

          &.failed {
            color: #dc2626;
          }
        }

        .log-time {
          width: 80px;
          text-align: right;
          color: #94a3b8;
          font-size: var(--font-size-xs);
        }

        .expand-chevron {
          color: #cbd5e1;
          font-size: 14px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

          &.rotated {
            transform: rotate(180deg);
            color: #667eea;
          }
        }

        // 日志详情展开区域
        .log-detail {
          width: 100%;
          margin-top: var(--spacing-md);
          padding: var(--spacing-md);
          background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
          border: 1px solid rgba(102, 126, 234, 0.1);
          border-radius: var(--radius-md);

          .detail-section {
            margin-bottom: var(--spacing-md);

            &:last-child {
              margin-bottom: 0;
            }

            .detail-title {
              font-size: var(--font-size-xs);
              font-weight: 700;
              color: #1e293b;
              margin-bottom: 8px;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }

            .detail-info {
              .info-row {
                display: flex;
                gap: var(--spacing-sm);
                padding: 4px 0;
                font-size: var(--font-size-xs);

                .info-label {
                  color: #64748b;
                  min-width: 70px;
                }

                .info-value {
                  color: #1e293b;
                  font-weight: 500;
                  font-family: 'SF Mono', monospace;
                }
              }
            }

            &.error-section {
              .error-message {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: var(--spacing-sm) var(--spacing-md);
                background: rgba(239, 68, 68, 0.05);
                border: 1px solid rgba(239, 68, 68, 0.15);
                border-radius: var(--radius-sm);
                color: #dc2626;
                font-size: var(--font-size-xs);
                margin-bottom: 8px;

                .el-icon {
                  color: #ef4444;
                }
              }

              .retry-btn {
                width: 100%;
              }
            }

            &.success-section {
              .success-message {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: var(--spacing-sm) var(--spacing-md);
                background: rgba(16, 185, 129, 0.05);
                border: 1px solid rgba(16, 185, 129, 0.15);
                border-radius: var(--radius-sm);
                color: #059669;
                font-size: var(--font-size-xs);
                margin-bottom: 8px;

                .el-icon {
                  color: #10b981;
                }
              }

              .doc-preview {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: var(--spacing-sm);
                background: white;
                border-radius: var(--radius-sm);
                font-size: var(--font-size-xs);
                color: #64748b;

                .el-icon {
                  color: #667eea;
                }
              }
            }
          }
        }
      }
    }
  }
}

// 动画定义
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% {
    left: -100%;
  }
  100% {
    left: 100%;
  }
}

// 过渡动画
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-10px);
  max-height: 0;
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
  max-height: 0;
}

.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 400px;
  opacity: 1;
  transform: translateY(0);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
  opacity: 1;
}

// 抽屉样式覆盖
:deep(.el-drawer) {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: -8px 0 40px rgba(102, 126, 234, 0.15);
}

:deep(.el-drawer__header) {
  padding: var(--spacing-lg);
  margin-bottom: 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);

  .el-drawer__title {
    font-family: 'Outfit', sans-serif;
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: #1e293b;
  }
}

.stat-drawer-content {
  padding: var(--spacing-lg);

  .drawer-overview {
    text-align: center;
    padding: var(--spacing-xl) 0;
    margin-bottom: var(--spacing-xl);
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    border-radius: var(--radius-xl);
    border: 1px solid rgba(102, 126, 234, 0.1);

    .overview-number {
      font-family: 'Outfit', sans-serif;
      font-size: 48px;
      font-weight: 700;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
      margin-bottom: 8px;
    }

    .overview-label {
      font-size: var(--font-size-base);
      color: #64748b;
      font-weight: 500;
    }
  }

  .drawer-charts {
    .chart-section {
      margin-bottom: var(--spacing-xl);

      &:last-child {
        margin-bottom: 0;
      }

      h4 {
        font-family: 'Outfit', sans-serif;
        font-size: var(--font-size-base);
        font-weight: 600;
        color: #1e293b;
        margin-bottom: var(--spacing-md);
        padding-bottom: var(--spacing-sm);
        border-bottom: 2px solid rgba(102, 126, 234, 0.1);
      }

      .mini-trend-chart {
        height: 120px;
        background: #f8fafc;
        border-radius: var(--radius-md);
        position: relative;
        margin-bottom: var(--spacing-md);
        overflow: hidden;

        .trend-line {
          position: absolute;
          bottom: 20px;
          left: 10%;
          right: 10%;
          height: 2px;
          background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
          clip-path: polygon(0% 80%, 15% 60%, 30% 70%, 45% 40%, 60% 50%, 75% 30%, 90% 45%, 100% 20%, 100% 100%, 0% 100%);
        }

        .trend-points {
          position: absolute;
          inset: 0;

          .point {
            position: absolute;
            bottom: 20px;
            transform: translateX(-50%);

            .point-dot {
              width: 8px;
              height: 8px;
              background: #667eea;
              border-radius: 50%;
              border: 2px solid white;
              box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            }

            .point-label {
              position: absolute;
              top: 16px;
              left: 50%;
              transform: translateX(-50%);
              font-size: 10px;
              color: #94a3b8;
              white-space: nowrap;
            }
          }
        }
      }

      // 用户统计网格
      .user-stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: var(--spacing-md);

        .user-stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          padding: 16px 12px;
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
          border-radius: var(--radius-lg);
          border: 1px solid rgba(102, 126, 234, 0.08);
          transition: all 0.3s ease;

          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.12);
            border-color: rgba(102, 126, 234, 0.2);
          }

          .stat-icon-wrapper {
            width: 44px;
            height: 44px;
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            color: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);

            &.active {
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            
            &.new {
              background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            }
            
            &.today {
              background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }
          }

          .stat-text {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;

            .stat-number {
              font-family: 'Outfit', sans-serif;
              font-size: var(--font-size-xl);
              font-weight: 700;
              color: #1e293b;
            }

            .stat-desc {
              font-size: var(--font-size-xs);
              color: #64748b;
              font-weight: 500;
            }
          }
        }
      }

      // 用户列表
      .user-list {
        max-height: 320px;
        overflow-y: auto;

        .user-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 12px;
          border-bottom: 1px solid rgba(226, 232, 240, 0.5);
          transition: all 0.3s ease;
          cursor: pointer;
          border-radius: var(--radius-md);

          &:last-child {
            border-bottom: none;
          }

          &:hover {
            background: rgba(102, 126, 234, 0.04);
            transform: translateX(4px);

            .user-avatar {
              transform: scale(1.1);
              box-shadow: 0 4px 16px rgba(102, 126, 234, 0.25);
            }
          }

          .user-avatar {
            width: 42px;
            height: 42px;
            border-radius: var(--radius-lg);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--font-size-lg);
            font-weight: 700;
            flex-shrink: 0;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
          }

          .user-info {
            flex: 1;
            min-width: 0;

            .user-name {
              font-size: var(--font-size-sm);
              font-weight: 600;
              color: #1e293b;
              margin-bottom: 4px;
            }

            .user-meta {
              display: flex;
              align-items: center;
              gap: 8px;
              font-size: var(--font-size-xs);
              color: #64748b;

              span {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }
          }

          .user-time {
            font-size: var(--font-size-xs);
            color: #94a3b8;
            white-space: nowrap;
            font-weight: 500;
          }
        }
      }

      // 饼状图容器
      .pie-chart-container {
        display: flex;
        align-items: center;
        gap: var(--spacing-xl);
        padding: var(--spacing-md) 0;

        .pie-chart-wrapper {
          flex-shrink: 0;

          .pie-chart {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            position: relative;
            box-shadow: 
              0 8px 32px rgba(102, 126, 234, 0.15),
              inset 0 2px 8px rgba(255, 255, 255, 0.3);
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);

            &:hover {
              transform: scale(1.05);
              box-shadow: 
                0 12px 40px rgba(102, 126, 234, 0.25),
                inset 0 2px 8px rgba(255, 255, 255, 0.3);
            }

            .pie-center {
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              width: 100px;
              height: 100px;
              background: white;
              border-radius: 50%;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              box-shadow: 
                0 4px 16px rgba(0, 0, 0, 0.08),
                inset 0 1px 2px rgba(255, 255, 255, 0.9);

              .pie-total {
                font-family: 'Outfit', sans-serif;
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
                line-height: 1;
              }

              .pie-label {
                font-size: var(--font-size-xs);
                color: #64748b;
                margin-top: 4px;
                font-weight: 500;
              }
            }
          }
        }

        // 图例
        .pie-legend {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 10px;

          .legend-item {
            display: grid;
            grid-template-columns: 12px auto 40px 45px;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            background: rgba(248, 250, 252, 0.5);
            border-radius: var(--radius-md);
            transition: all 0.3s ease;

            &:hover {
              background: rgba(102, 126, 234, 0.04);
              transform: translateX(4px);
            }

            .legend-color {
              width: 12px;
              height: 12px;
              border-radius: 3px;
              box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);

              &.product { background: linear-gradient(135deg, #667eea, #764ba2); }
              &.policy { background: linear-gradient(135deg, #f093fb, #f5576c); }
              &.logistics { background: linear-gradient(135deg, #43e97b, #38f9d7); }
              &.service { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
            }

            .legend-name {
              font-size: var(--font-size-sm);
              font-weight: 600;
              color: #334155;
            }

            .legend-value {
              font-size: var(--font-size-sm);
              font-weight: 700;
              color: #1e293b;
              text-align: right;
              font-family: 'Outfit', sans-serif;
            }

            .legend-percent {
              font-size: var(--font-size-xs);
              color: #667eea;
              font-weight: 600;
              text-align: right;
              font-family: 'Outfit', sans-serif;
            }
          }
        }
      }

      .conversation-types {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .type-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: #f8fafc;
          border-radius: var(--radius-md);
          transition: all 0.3s ease;

          &:hover {
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
          }

          .type-icon {
            width: 44px;
            height: 44px;
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;

            &.product { background: linear-gradient(135deg, #667eea, #764ba2); }
            &.policy { background: linear-gradient(135deg, #f093fb, #f5576c); }
            &.logistics { background: linear-gradient(135deg, #43e97b, #38f9d7); }
          }

          .type-info {
            flex: 1;
            display: flex;
            justify-content: space-between;
            align-items: center;

            .type-name {
              font-size: var(--font-size-sm);
              font-weight: 600;
              color: #1e293b;
            }

            .type-percent {
              font-size: var(--font-size-base);
              font-weight: 700;
              color: #667eea;
              font-family: 'Outfit', sans-serif;
            }
          }
        }
      }

      .today-messages-card {
        .messages-scroll {
          max-height: 264px;
          overflow-y: auto;
          padding-right: 4px;

          &::-webkit-scrollbar {
            width: 4px;
          }

          &::-webkit-scrollbar-track {
            background: transparent;
          }

          &::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.2);
            border-radius: 2px;

            &:hover {
              background: rgba(102, 126, 234, 0.4);
            }
          }

          .message-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
            border-radius: var(--radius-lg);
            border: 1px solid rgba(102, 126, 234, 0.08);
            transition: all 0.3s ease;

            &:hover {
              background: rgba(102, 126, 234, 0.06);
              border-color: rgba(102, 126, 234, 0.15);
              transform: translateX(4px);
            }

            &:last-child {
              margin-bottom: 0;
            }

            .msg-avatar {
              width: 36px;
              height: 36px;
              border-radius: var(--radius-lg);
              background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
              color: white;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: var(--font-size-sm);
              font-weight: 700;
              flex-shrink: 0;
              box-shadow: 0 2px 8px rgba(67, 233, 123, 0.25);
            }

            .msg-body {
              flex: 1;
              min-width: 0;

              .msg-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;

                .msg-username {
                  font-size: var(--font-size-sm);
                  font-weight: 600;
                  color: #1e293b;
                }

                .msg-time {
                  font-size: var(--font-size-xs);
                  color: #94a3b8;
                  white-space: nowrap;
                }
              }

              .msg-content {
                font-size: var(--font-size-sm);
                color: #475569;
                line-height: 1.5;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                word-break: break-word;
              }
            }
          }
        }
      }

      .chart-stats {
        margin-top: var(--spacing-md);
        padding-top: var(--spacing-md);
        border-top: 1px dashed rgba(102, 126, 234, 0.2);

        .stat-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          font-size: var(--font-size-sm);

          span {
            color: #64748b;
          }

          strong {
            color: #1e293b;
            font-family: 'Outfit', sans-serif;

            &.positive {
              color: #059669;
            }

            &.warning {
              color: #f59e0b;
            }
          }
        }
      }
    }
  }
}
</style>
