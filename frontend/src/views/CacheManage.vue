<template>
  <div class="cache-manage">
    <div class="page-header">
      <h2>缓存管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="loadCacheStats" :loading="statsLoading">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
        <el-button type="danger" @click="handleClearAllCache" :loading="clearLoading">
          <el-icon><Delete /></el-icon>
          一键清除
        </el-button>
      </div>
    </div>

    <div class="stats-cards">
      <el-card class="stat-card" v-loading="statsLoading">
        <template #header>
          <div class="card-header">
            <el-icon class="card-icon"><Connection /></el-icon>
            <span>Redis状态</span>
          </div>
        </template>
        <div class="stat-content">
          <div class="stat-item">
            <span class="stat-label">连接状态</span>
            <el-tag :type="cacheStats.redis?.enabled ? 'success' : 'danger'" size="small">
              {{ cacheStats.redis?.enabled ? '已连接' : '未连接' }}
            </el-tag>
          </div>
          <div class="stat-item" v-if="cacheStats.redis?.enabled">
            <span class="stat-label">连接客户端</span>
            <span class="stat-value">{{ cacheStats.redis?.connected_clients || 0 }}</span>
          </div>
          <div class="stat-item" v-if="cacheStats.redis?.enabled">
            <span class="stat-label">缓存命中</span>
            <span class="stat-value">{{ formatNumber(cacheStats.redis?.keyspace_hits) }}</span>
          </div>
          <div class="stat-item" v-if="cacheStats.redis?.enabled">
            <span class="stat-label">缓存未命中</span>
            <span class="stat-value">{{ formatNumber(cacheStats.redis?.keyspace_misses) }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card" v-loading="statsLoading">
        <template #header>
          <div class="card-header">
            <el-icon class="card-icon"><Collection /></el-icon>
            <span>语义缓存</span>
          </div>
        </template>
        <div class="stat-content">
          <div class="stat-item">
            <span class="stat-label">缓存状态</span>
            <el-tag :type="cacheStats.semantic_cache?.enabled ? 'success' : 'danger'" size="small">
              {{ cacheStats.semantic_cache?.enabled ? '已启用' : '未启用' }}
            </el-tag>
          </div>
          <div class="stat-item" v-if="cacheStats.semantic_cache?.enabled">
            <span class="stat-label">缓存条目</span>
            <span class="stat-value">{{ cacheStats.semantic_cache?.cache_entries || 0 }}</span>
          </div>
          <div class="stat-item" v-if="cacheStats.semantic_cache?.enabled">
            <span class="stat-label">向量条目</span>
            <span class="stat-value">{{ cacheStats.semantic_cache?.embedding_entries || 0 }}</span>
          </div>
          <div class="stat-item" v-if="cacheStats.semantic_cache?.enabled">
            <span class="stat-label">相似度阈值</span>
            <span class="stat-value">{{ cacheStats.semantic_cache?.similarity_threshold || 0.95 }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card" v-loading="statsLoading">
        <template #header>
          <div class="card-header">
            <el-icon class="card-icon"><Coin /></el-icon>
            <span>内存使用</span>
          </div>
        </template>
        <div class="stat-content">
          <div class="stat-item">
            <span class="stat-label">当前使用</span>
            <span class="stat-value">{{ cacheStats.memory?.used_memory_human || '0B' }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">峰值使用</span>
            <span class="stat-value">{{ cacheStats.memory?.used_memory_peak_human || '0B' }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">数据库大小</span>
            <span class="stat-value">{{ formatNumber(cacheStats.db_size) }} 条</span>
          </div>
        </div>
      </el-card>
    </div>

    <el-card class="cache-list-card">
      <template #header>
        <div class="list-header">
          <span>缓存列表</span>
          <div class="search-box">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索问题或回答..."
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearch"
              style="width: 300px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="cacheList"
        v-loading="listLoading"
        @selection-change="handleSelectionChange"
        stripe
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="key" label="缓存键" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tooltip :content="row.key" placement="top">
              <span class="cache-key">{{ row.key }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="query_preview" label="问题预览" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer_preview" label="回答预览" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ttl" label="TTL(秒)" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTtlTagType(row.ttl)" size="small">
              {{ row.ttl > 0 ? row.ttl : (row.ttl === -1 ? '永久' : '已过期') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleViewDetail(row)">
              详情
            </el-button>
            <el-button type="danger" link size="small" @click="handleDeleteSingle(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <div class="batch-actions">
          <el-button
            type="danger"
            :disabled="selectedKeys.length === 0"
            @click="handleBatchDelete"
          >
            批量删除 ({{ selectedKeys.length }})
          </el-button>
        </div>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadCacheList"
          @current-change="loadCacheList"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="detailDialogVisible"
      title="缓存详情"
      width="700px"
      destroy-on-close
    >
      <div class="cache-detail" v-loading="detailLoading">
        <el-descriptions :column="1" border v-if="cacheDetail">
          <el-descriptions-item label="缓存键">
            <span class="detail-key">{{ cacheDetail.key }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="问题">
            <div class="detail-content">{{ cacheDetail.query }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="回答">
            <div class="detail-content">{{ cacheDetail.answer }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="TTL">
            {{ cacheDetail.ttl > 0 ? cacheDetail.ttl + ' 秒' : (cacheDetail.ttl === -1 ? '永久' : '已过期') }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ cacheDetail.created_at || '未知' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="danger" @click="handleDeleteFromDetail">删除此缓存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { statsApi } from '@/api/modules'

const statsLoading = ref(false)
const listLoading = ref(false)
const detailLoading = ref(false)
const clearLoading = ref(false)

const cacheStats = ref({
  redis: {},
  semantic_cache: {},
  memory: {},
  db_size: 0
})

const cacheList = ref([])
const selectedKeys = ref([])
const searchKeyword = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const detailDialogVisible = ref(false)
const cacheDetail = ref(null)

onMounted(() => {
  loadCacheStats()
  loadCacheList()
})

async function loadCacheStats() {
  statsLoading.value = true
  try {
    const res = await statsApi.getCacheStats()
    cacheStats.value = res
    await loadCacheList()
  } catch (error) {
    console.error('加载缓存统计失败:', error)
    ElMessage.error('加载缓存统计失败')
  } finally {
    statsLoading.value = false
  }
}

async function loadCacheList() {
  listLoading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    const res = await statsApi.getCacheList(params)
    cacheList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载缓存列表失败:', error)
    ElMessage.error('加载缓存列表失败')
  } finally {
    listLoading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadCacheList()
}

function handleSelectionChange(selection) {
  selectedKeys.value = selection.map(item => item.key)
}

async function handleViewDetail(row) {
  detailDialogVisible.value = true
  detailLoading.value = true
  try {
    const res = await statsApi.getCacheDetail(row.key)
    cacheDetail.value = res
  } catch (error) {
    console.error('加载缓存详情失败:', error)
    ElMessage.error('加载缓存详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function handleDeleteSingle(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条缓存吗？\n问题: ${row.query_preview || '未知'}`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await statsApi.deleteCacheKey(row.key)
    ElMessage.success('缓存已删除')
    loadCacheList()
    loadCacheStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除缓存失败:', error)
      ElMessage.error('删除缓存失败')
    }
  }
}

async function handleBatchDelete() {
  if (selectedKeys.value.length === 0) {
    ElMessage.warning('请选择要删除的缓存')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedKeys.value.length} 条缓存吗？`,
      '批量删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const res = await statsApi.deleteCacheKeys(selectedKeys.value)
    ElMessage.success(res.message || '缓存已删除')
    selectedKeys.value = []
    loadCacheList()
    loadCacheStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除缓存失败:', error)
      ElMessage.error('批量删除缓存失败')
    }
  }
}

async function handleClearAllCache() {
  try {
    await ElMessageBox.confirm(
      '确定要清除所有缓存吗？此操作不可恢复！',
      '清除所有缓存',
      {
        confirmButtonText: '确定清除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    clearLoading.value = true
    await statsApi.clearAllCache()
    ElMessage.success('所有缓存已清除')
    loadCacheList()
    loadCacheStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清除缓存失败:', error)
      ElMessage.error('清除缓存失败')
    }
  } finally {
    clearLoading.value = false
  }
}

async function handleDeleteFromDetail() {
  if (!cacheDetail.value?.key) return
  
  try {
    await ElMessageBox.confirm('确定要删除这条缓存吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await statsApi.deleteCacheKey(cacheDetail.value.key)
    ElMessage.success('缓存已删除')
    detailDialogVisible.value = false
    loadCacheList()
    loadCacheStats()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除缓存失败:', error)
      ElMessage.error('删除缓存失败')
    }
  }
}

function formatNumber(num) {
  if (!num) return '0'
  return num.toLocaleString()
}

function getTtlTagType(ttl) {
  if (ttl === -1) return 'success'
  if (ttl === -2 || ttl <= 0) return 'danger'
  if (ttl < 300) return 'warning'
  return 'info'
}
</script>

<style lang="scss" scoped>
.cache-manage {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 20px;
    color: var(--text-primary);
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
    
    .card-icon {
      font-size: 18px;
      color: var(--primary-color);
    }
  }
  
  .stat-content {
    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--border-color);
      
      &:last-child {
        border-bottom: none;
      }
      
      .stat-label {
        color: var(--text-secondary);
        font-size: 14px;
      }
      
      .stat-value {
        font-weight: 500;
        color: var(--text-primary);
      }
    }
  }
}

.cache-list-card {
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .search-box {
      display: flex;
      gap: 8px;
    }
  }
}

.cache-key {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.cache-detail {
  .detail-key {
    font-family: monospace;
    font-size: 12px;
    word-break: break-all;
  }
  
  .detail-content {
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

@media (max-width: 1200px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
