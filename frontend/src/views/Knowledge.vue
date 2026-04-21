<template>
  <div class="knowledge-page">
    <el-card class="knowledge-card">
      <template #header>
        <div class="card-header">
          <span>知识库管理</span>
          <div class="header-actions">
            <el-button type="primary" :loading="syncLoading" :disabled="syncLoading" @click="handleSync">
              <el-icon v-if="!syncLoading"><Refresh /></el-icon>
              {{ syncLoading ? '正在同步中...' : '同步到向量库' }}
            </el-button>
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              添加知识
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-select v-model="filterCategory" placeholder="选择分类" clearable @change="fetchList" style="width: 200px;">
          <el-option label="全部分类" value="" />
          <el-option label="商品知识" value="product" />
          <el-option label="售后政策" value="policy" />
          <el-option label="物流信息" value="logistics" />
          <el-option label="客户服务" value="service" />
        </el-select>

        <el-input
          v-model="searchKeyword"
          placeholder="搜索知识内容"
          clearable
          @keyup.enter="fetchList"
          style="width: 300px; margin-left: 16px;"
        >
          <template #append>
            <el-button @click="fetchList">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 同步进度提示 -->
      <el-alert
        v-if="syncLoading"
        title="正在同步知识库到向量数据库..."
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #default>
          <div class="sync-progress-info">
            <p>⏳ 正在生成Embedding向量并构建索引，请耐心等待...</p>
            <p class="sync-tip">（预计需要20-40秒，取决于数据量和服务器性能）</p>
          </div>
        </template>
      </el-alert>

      <!-- 同步成功结果 -->
      <el-alert
        v-if="syncResult && !syncLoading"
        :title="`✅ ${syncResult.message}`"
        type="success"
        closable
        @close="syncResult = null"
        style="margin-bottom: 16px;"
      >
        <template #default>
          <div v-if="syncResult.milvus || syncResult.bm25" class="sync-result-detail">
            <div v-if="syncResult.milvus" class="result-item">
              <strong>📊 Milvus向量数据库：</strong>
              <span>索引类型：{{ syncResult.milvus.index_type }} | 向量数：{{ syncResult.milvus.num_entities }}</span>
            </div>
            <div v-if="syncResult.bm25" class="result-item">
              <strong>📝 BM25倒排索引：</strong>
              <span>文档数：{{ syncResult.bm25.doc_count }} | 词汇量：{{ syncResult.bm25.vocab_size }}</span>
            </div>
          </div>
        </template>
      </el-alert>
      
      <el-table :data="knowledgeList" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag :type="getCategoryType(row.category)">{{ getCategoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" min-width="300">
          <template #default="{ row }">
            <div class="content-preview">{{ row.content.substring(0, 100) }}{{ row.content.length > 100 ? '...' : '' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="handleView(row)">查看</el-button>
            <el-button type="warning" size="small" text @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <span class="pagination-total">总共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="10"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchList"
        />
        <div class="pagination-jumper">
          <span>跳转</span>
          <el-input-number
            v-model="jumpPage"
            :min="1"
            :max="Math.ceil(total / 10) || 1"
            size="small"
            controls-position="right"
            @change="handleJumpPage"
          />
          <span>页</span>
        </div>
      </div>
    </el-card>
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入知识标题" />
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%;">
            <el-option label="商品知识" value="product" />
            <el-option label="售后政策" value="policy" />
            <el-option label="物流信息" value="logistics" />
            <el-option label="客户服务" value="service" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="来源" prop="source">
          <el-input v-model="form.source" placeholder="请输入来源" />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            placeholder="请输入知识内容"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
    
    <el-dialog v-model="viewDialogVisible" title="知识详情" width="600px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="标题">{{ viewData.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag :type="getCategoryType(viewData.category)">{{ getCategoryLabel(viewData.category) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源">{{ viewData.source }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(viewData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="内容">
          <div class="view-content">{{ viewData.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '@/api/modules'

const loading = ref(false)
const submitLoading = ref(false)
const syncLoading = ref(false)
const syncResult = ref(null)
const knowledgeList = ref([])
const total = ref(0)
const currentPage = ref(1)
const jumpPage = ref(1)
const filterCategory = ref('')
const searchKeyword = ref('')

const dialogVisible = ref(false)
const dialogTitle = ref('添加知识')
const isEdit = ref(false)
const editId = ref(null)
const viewDialogVisible = ref(false)
const viewData = ref({})
const formRef = ref(null)

const form = reactive({
  title: '',
  category: '',
  source: '',
  content: ''
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

onMounted(() => {
  fetchList()
})

async function fetchList() {
  loading.value = true
  try {
    const data = await knowledgeApi.getList({
      offset: (currentPage.value - 1) * 10,
      limit: 10,
      category: filterCategory.value || undefined
    })
    knowledgeList.value = data.items || []
    total.value = data.total || 0
    jumpPage.value = currentPage.value
  } catch (error) {
    console.error('获取知识列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleJumpPage(val) {
  if (val >= 1 && val <= Math.ceil(total.value / 10)) {
    currentPage.value = val
    fetchList()
  }
}

function getCategoryType(category) {
  const types = {
    'product': 'primary',
    'policy': 'success',
    'logistics': 'warning',
    'service': 'danger'
  }
  return types[category] || 'info'
}

function getCategoryLabel(category) {
  const labels = {
    'product': '商品知识',
    'policy': '售后政策',
    'logistics': '物流信息',
    'service': '客户服务'
  }
  return labels[category] || category
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function handleAdd() {
  dialogTitle.value = '添加知识'
  isEdit.value = false
  editId.value = null
  form.title = ''
  form.category = ''
  form.source = ''
  form.content = ''
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑知识'
  isEdit.value = true
  editId.value = row.id
  form.title = row.title
  form.category = row.category
  form.source = row.source
  form.content = row.content
  dialogVisible.value = true
}

function handleView(row) {
  viewData.value = row
  viewDialogVisible.value = true
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除这条知识吗？删除后无法恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await knowledgeApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitLoading.value = true
  try {
    const data = {
      title: form.title,
      category: form.category,
      source: form.source,
      content: form.content
    }

    if (isEdit.value) {
      await knowledgeApi.update(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await knowledgeApi.add(data)
      ElMessage.success('添加成功')
    }
    
    dialogVisible.value = false
    fetchList()
  } catch (error) {
    console.error('操作失败:', error)
  } finally {
    submitLoading.value = false
  }
}

async function handleSync() {
  try {
    await ElMessageBox.confirm('确定要将所有知识同步到向量数据库吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    syncLoading.value = true
    syncResult.value = null

    const result = await knowledgeApi.sync()
    syncResult.value = result

    ElMessage.success(`同步成功！已同步 ${result.message.includes('条') ? result.message.split(' ')[1] : ''} 条知识文档到向量数据库`)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('同步失败:', error)
      ElMessage.error(error?.response?.data?.detail || '同步失败，请重试')
    }
  } finally {
    syncLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.knowledge-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.knowledge-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    span {
      font-size: 16px;
      font-weight: 500;
    }
    
    .header-actions {
      display: flex;
      gap: 12px;
    }
  }
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.content-preview {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
}

.pagination-total {
  color: var(--text-secondary);
  font-size: 14px;
}

.pagination-jumper {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  
  .el-input-number {
    width: 80px;
  }
}

.view-content {
  white-space: pre-wrap;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

.sync-progress-info {
  p {
    margin: 4px 0;
    color: #606266;
    font-size: 14px;
  }

  .sync-tip {
    color: #909399;
    font-size: 12px;
    font-style: italic;
  }
}

.sync-result-detail {
  .result-item {
    padding: 6px 0;
    border-bottom: 1px solid #ebeef5;

    &:last-child {
      border-bottom: none;
    }

    strong {
      display: inline-block;
      width: 160px;
      color: #303133;
    }

    span {
      color: #606266;
      font-size: 13px;
    }
  }
}
</style>
