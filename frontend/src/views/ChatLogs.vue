<template>
  <div class="chat-logs-page">
    <div class="page-header">
      <h2>对话日志分析</h2>
    </div>

    <div class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="会话ID">
          <el-input
            v-model="filters.session_id"
            placeholder="输入会话ID"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索关键词"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-card">
      <div class="table-header">
        <span class="total-count">共 {{ total }} 条记录</span>
      </div>

      <el-table
        :data="logs"
        v-loading="loading"
        stripe
        @row-click="handleRowClick"
        style="cursor: pointer"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="session_id" label="会话ID" width="260">
          <template #default="{ row }">
            <el-tooltip :content="row.session_id" placement="top">
              <span class="session-id">{{ row.session_id.substring(0, 18) }}...</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="用户问题" min-width="280">
          <template #default="{ row }">
            <el-tooltip :content="row.content" placement="top" :disabled="row.content.length < 50">
              <span class="content-text">{{ row.content }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="viewSession(row.session_id)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="sessionDialogVisible"
      title="会话详情"
      width="700px"
      destroy-on-close
    >
      <div class="session-detail" v-loading="sessionLoading">
        <div
          v-for="(msg, index) in sessionMessages"
          :key="index"
          :class="['message-item', msg.role]"
        >
          <div class="message-role">
            <el-tag :type="msg.role === 'user' ? 'primary' : 'success'" size="small">
              {{ msg.role === 'user' ? '用户' : '助手' }}
            </el-tag>
            <span class="message-time">{{ formatDateTime(msg.created_at) }}</span>
          </div>
          <div class="message-content">{{ msg.content }}</div>
        </div>
        <el-empty v-if="sessionMessages.length === 0 && !sessionLoading" description="暂无数据" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { statsApi } from '@/api/modules'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dateRange = ref([])
const filters = reactive({
  session_id: '',
  keyword: ''
})

const sessionDialogVisible = ref(false)
const sessionLoading = ref(false)
const sessionMessages = ref([])

const dateShortcuts = [
  {
    text: '今天',
    value: () => {
      const today = new Date()
      return [today, today]
    }
  },
  {
    text: '近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  }
]

function formatDateTime(dateStr) {
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

async function loadLogs() {
  loading.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    }

    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    if (filters.session_id) {
      params.session_id = filters.session_id
    }

    if (filters.keyword) {
      params.keyword = filters.keyword
    }

    const data = await statsApi.getChatLogs(params)
    logs.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  loadLogs()
}

function handleReset() {
  dateRange.value = []
  filters.session_id = ''
  filters.keyword = ''
  currentPage.value = 1
  loadLogs()
}

function handleSizeChange(size) {
  pageSize.value = size
  loadLogs()
}

function handlePageChange(page) {
  currentPage.value = page
  loadLogs()
}

function handleRowClick(row) {
  viewSession(row.session_id)
}

async function viewSession(sessionId) {
  sessionDialogVisible.value = true
  sessionLoading.value = true
  sessionMessages.value = []

  try {
    const data = await statsApi.getSessionDetail(sessionId)
    sessionMessages.value = data
  } catch (error) {
    ElMessage.error('加载会话详情失败')
  } finally {
    sessionLoading.value = false
  }
}

onMounted(() => {
  loadLogs()
})
</script>

<style lang="scss" scoped>
.chat-logs-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
    font-size: 20px;
    color: var(--primary-color);
  }
}

.filter-card {
  background: var(--surface-color);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  
  .filter-form {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    
    :deep(.el-form-item) {
      margin-bottom: 0;
    }
  }
}

.table-card {
  background: var(--surface-color);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  
  .table-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
    
    .total-count {
      font-size: 14px;
      color: var(--text-secondary);
    }
  }
  
  .session-id {
    font-family: monospace;
    font-size: 12px;
    color: var(--text-muted);
  }
  
  .content-text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .pagination-wrapper {
    padding: 16px 20px;
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--border-color);
  }
}

.session-detail {
  max-height: 500px;
  overflow-y: auto;
  
  .message-item {
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    
    &.user {
      background: rgba(26, 54, 93, 0.05);
    }
    
    &.assistant {
      background: rgba(103, 194, 58, 0.05);
    }
    
    .message-role {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
      
      .message-time {
        font-size: 12px;
        color: var(--text-muted);
      }
    }
    
    .message-content {
      font-size: 14px;
      line-height: 1.6;
      color: var(--text-primary);
      white-space: pre-wrap;
    }
  }
}
</style>
