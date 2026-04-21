<template>
  <div class="evaluation-page">
    <div class="page-header">
      <div>
        <h2>RAGAS 评估测试</h2>
        <p>使用 RAGAS 框架对 RAG 系统进行自动化评估</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="runBatchEvaluation" :loading="evaluating">
          <el-icon><DataAnalysis /></el-icon>
          运行 RAGAS 批量评估
        </el-button>
        <el-button plain @click="loadSummary">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon faithfulness">
          <el-icon :size="22"><DocumentChecked /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.faithfulness) }}</div>
          <div class="stat-label">忠实度</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon relevancy">
          <el-icon :size="22"><Aim /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.answer_relevancy) }}</div>
          <div class="stat-label">答案相关性</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon precision">
          <el-icon :size="22"><Filter /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.context_precision) }}</div>
          <div class="stat-label">上下文精确度</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon overall">
          <el-icon :size="22"><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.overall_score) }}</div>
          <div class="stat-label">综合得分</div>
        </div>
      </div>
    </div>

    <div class="top-section">
      <div class="panel-card config-panel">
        <div class="panel-header">
          <h3>评估配置参数</h3>
        </div>
        <div class="panel-content">
          <el-form :model="evalConfig" label-width="110px">
            <el-form-item label="评估样本数量">
              <el-input-number v-model="evalConfig.limit" :min="1" :max="20" />
              <div class="form-tip">建议评估样本数量为 1 到 5 条</div>
            </el-form-item>
            <el-form-item label="评估严格度">
              <el-select v-model="evalConfig.strictness">
                <el-option :value="0" label="0 - 极宽松 (推荐)" />
                <el-option :value="1" label="1 - 宽松" />
              </el-select>
            </el-form-item>
            <el-form-item label="并发数量">
              <el-select v-model="evalConfig.max_workers">
                <el-option :value="1" label="1" />
                <el-option :value="2" label="2 (推荐)" />
              </el-select>
            </el-form-item>
            <el-form-item label="评估超时时间">
              <div class="input-with-suffix">
                <el-input-number v-model="evalConfig.timeout" :min="300" :max="1800" :step="60" />
                <span class="input-suffix">秒</span>
              </div>
            </el-form-item>
            <el-form-item label="评估框架">
              <el-tag type="success">RAGAS</el-tag>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <div class="panel-card dataset-panel">
        <div class="panel-header">
          <h3>测试数据集管理</h3>
          <div class="header-buttons">
            <el-button size="small" type="warning" plain @click="openBatchAnnotationDialog">
              批量标注
            </el-button>
            <el-button size="small" type="primary" @click="showAddDatasetDialog">
              <el-icon><Plus /></el-icon>
              添加测试数据
            </el-button>
            <el-button size="small" plain @click="loadDataset">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="datasetItems.length" class="dataset-grid">
            <div class="dataset-item" v-for="item in datasetItems" :key="item.id">
              <div class="dataset-question">{{ item.question }}</div>
              <div class="dataset-truth">{{ item.ground_truth }}</div>
              <div class="dataset-tags">
                <el-tag size="small" v-if="item.category">{{ item.category }}</el-tag>
                <el-tag size="small" type="success">
                  已标注相关文档: {{ (item.relevant_doc_ids || []).length }}
                </el-tag>
              </div>
              <div class="dataset-actions">
                <el-button size="small" type="danger" link @click="deleteDatasetItem(item.id)">
                  删除
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无测试数据" :image-size="70" />
        </div>
      </div>
    </div>

    <div class="panel-card results-panel">
      <div class="panel-header">
        <h3>评估结果记录</h3>
        <el-tag>共 {{ evaluationResults.length }} 条</el-tag>
      </div>
      <div class="panel-content">
        <div v-if="evaluationResults.length" class="results-grid">
          <div
            v-for="(result, index) in evaluationResults"
            :key="index"
            class="result-card"
            @click="showResultDetail(result)"
          >
            <div class="result-header">
              <span class="result-index">#{{ index + 1 }}</span>
              <span class="result-time">{{ formatTime(result.created_at) }}</span>
              <el-tag size="small" type="success">RAGAS</el-tag>
            </div>
            <div class="result-query">{{ result.query }}</div>
            <div class="result-scores-mini">
              <span class="mini-score" :class="getScoreClass(result.scores.faithfulness)">
                忠实度: {{ formatScore(result.scores.faithfulness) }}
              </span>
              <span class="mini-score" :class="getScoreClass(result.scores.answer_relevancy)">
                相关性: {{ formatScore(result.scores.answer_relevancy) }}
              </span>
              <span class="mini-score" :class="getScoreClass(result.scores.context_precision)">
                精确度: {{ formatScore(result.scores.context_precision) }}
              </span>
              <span class="mini-score" :class="getScoreClass(result.scores.overall_score)">
                综合: {{ formatScore(result.scores.overall_score) }}
              </span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无评估结果" />
      </div>
    </div>

    <el-dialog v-model="detailDialogVisible" title="评估详情" width="760px">
      <div v-if="selectedResult" class="detail-content">
        <div class="detail-section">
          <h4>用户问题</h4>
          <p>{{ selectedResult.query }}</p>
        </div>
        <div class="detail-section">
          <h4>回答</h4>
          <p>{{ selectedResult.answer }}</p>
        </div>
        <div class="detail-section">
          <h4>检索到的上下文文档</h4>
          <div class="context-list">
            <div class="context-item" v-for="(ctx, idx) in selectedResult.contexts" :key="idx">
              <span class="context-index">{{ idx + 1 }}</span>
              <span class="context-text">{{ ctx }}</span>
            </div>
          </div>
        </div>
        <div class="detail-section" v-if="selectedResult.ground_truth">
          <h4>标准答案</h4>
          <p>{{ selectedResult.ground_truth }}</p>
        </div>
        <div class="detail-section">
          <h4>评估指标得分</h4>
          <div class="detail-scores">
            <div class="detail-score-item">
              <span class="label">忠实度</span>
              <el-progress
                :percentage="toPercent(selectedResult.scores.faithfulness)"
                :color="getScoreColor(selectedResult.scores.faithfulness)"
                :format="() => formatScore(selectedResult.scores.faithfulness)"
              />
            </div>
            <div class="detail-score-item">
              <span class="label">答案相关性</span>
              <el-progress
                :percentage="toPercent(selectedResult.scores.answer_relevancy)"
                :color="getScoreColor(selectedResult.scores.answer_relevancy)"
                :format="() => formatScore(selectedResult.scores.answer_relevancy)"
              />
            </div>
            <div class="detail-score-item">
              <span class="label">上下文精确度</span>
              <el-progress
                :percentage="toPercent(selectedResult.scores.context_precision)"
                :color="getScoreColor(selectedResult.scores.context_precision)"
                :format="() => formatScore(selectedResult.scores.context_precision)"
              />
            </div>
            <div class="detail-score-item overall">
              <span class="label">综合得分</span>
              <el-progress
                :percentage="toPercent(selectedResult.scores.overall_score)"
                :color="getScoreColor(selectedResult.scores.overall_score)"
                :format="() => formatScore(selectedResult.scores.overall_score)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="addDatasetDialogVisible" title="添加测试数据" width="560px">
      <el-form :model="newDatasetItem" label-width="90px">
        <el-form-item label="问题">
          <el-input v-model="newDatasetItem.question" type="textarea" :rows="2" placeholder="请输入测试问题" />
        </el-form-item>
        <el-form-item label="标准答案">
          <el-input v-model="newDatasetItem.ground_truth" type="textarea" :rows="3" placeholder="请输入标准答案 ground_truth" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="newDatasetItem.category" placeholder="请选择分类" style="width: 100%">
            <el-option label="商品咨询" value="商品咨询" />
            <el-option label="订单查询" value="订单查询" />
            <el-option label="物流配送" value="物流配送" />
            <el-option label="售后服务" value="售后服务" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDatasetDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addDatasetItem" :loading="addingDataset">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchAnnotationDialogVisible"
      title="批量标注"
      width="920px"
      @closed="resetBatchAnnotationDialog"
    >
      <div v-if="editingDatasetItem" class="batch-annotation-dialog">
        <div class="batch-annotation-bar">
          <div class="batch-annotation-main">
            <el-tag type="warning">批量标注模式</el-tag>
            <span class="batch-annotation-text">进度: {{ batchProgressText }}</span>
          </div>
          <div class="batch-annotation-status">
            <el-tag :type="annotatedCount > 0 ? 'success' : 'info'">
              已标注 {{ annotatedCount }} / {{ batchAnnotationQueue.length }}
            </el-tag>
          </div>
        </div>

        <div class="batch-jump-bar">
          <span class="jump-label">快速跳转:</span>
          <el-input-number
            v-model="jumpToIndex"
            :min="1"
            :max="batchAnnotationQueue.length"
            size="small"
            style="width: 100px"
          />
          <span class="jump-text">/ {{ batchAnnotationQueue.length }} 条</span>
          <el-button size="small" type="primary" plain @click="handleJumpToIndex">
            跳转
          </el-button>
        </div>

        <div class="annotation-edit-form">
          <div class="edit-form-item">
            <label>问题</label>
            <el-input
              v-model="editingDatasetItem.question"
              type="textarea"
              :rows="2"
              placeholder="请输入问题"
            />
          </div>
          <div class="edit-form-item">
            <label>标准答案</label>
            <el-input
              v-model="editingDatasetItem.ground_truth"
              type="textarea"
              :rows="3"
              placeholder="请输入标准答案"
            />
          </div>
        </div>

        <div class="annotation-toolbar">
          <el-input
            v-model="knowledgeSearch"
            placeholder="搜索知识库文档..."
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-tag type="success">已选 {{ selectedRelevantDocIds.length }} 个</el-tag>
        </div>

        <div class="knowledge-select-grid">
          <div class="knowledge-list">
            <div
              v-for="doc in filteredKnowledgeDocs"
              :key="doc.id"
              class="knowledge-card"
              :class="{ selected: selectedRelevantDocIds.includes(doc.id) }"
            >
              <div class="knowledge-head">
                <div class="knowledge-meta">
                  <el-tag size="small" v-if="doc.category">{{ doc.category }}</el-tag>
                  <span class="knowledge-doc-id">ID {{ doc.id }}</span>
                </div>
                <div class="knowledge-actions">
                  <el-button size="small" link type="primary" @click="showDocDetail(doc)">
                    <el-icon><View /></el-icon>
                    详情
                  </el-button>
                  <el-tag
                    size="small"
                    :type="selectedRelevantDocIds.includes(doc.id) ? 'success' : 'info'"
                    effect="light"
                    class="select-tag"
                    @click="toggleRelevantDoc(doc.id)"
                  >
                    {{ selectedRelevantDocIds.includes(doc.id) ? '已选择' : '选择' }}
                  </el-tag>
                </div>
              </div>
              <div class="knowledge-title">{{ doc.title }}</div>
              <div class="knowledge-content">{{ doc.content }}</div>
            </div>
          </div>

          <div class="selected-sidebar">
            <h4>已选相关文档</h4>
            <div v-if="selectedKnowledgeDocs.length" class="selected-docs">
              <div v-for="doc in selectedKnowledgeDocs" :key="doc.id" class="selected-doc-item">
                <div>
                  <div class="selected-doc-title">{{ doc.title }}</div>
                  <div class="selected-doc-meta">
                    {{ doc.category || '未分类' }} | ID {{ doc.id }}
                  </div>
                </div>
                <el-button type="danger" size="small" link @click="toggleRelevantDoc(doc.id)">移除</el-button>
              </div>
            </div>
            <el-empty v-else description="暂未选择文档" :image-size="60" />
          </div>
        </div>
      </div>
      <template #footer>
        <div class="batch-footer">
          <div class="batch-footer-nav">
            <el-button @click="showPreviousBatchItem" :disabled="!canGoPreviousBatchItem || savingBatchAnnotation">
              上一条
            </el-button>
            <el-button @click="showNextBatchItem" :disabled="!canGoNextBatchItem || savingBatchAnnotation">
              下一条
            </el-button>
          </div>
          <div class="batch-footer-actions">
            <el-button @click="batchAnnotationDialogVisible = false">关闭</el-button>
            <el-button type="primary" plain @click="saveCurrentBatchItem" :loading="savingBatchAnnotation">
              保存当前
            </el-button>
            <el-button type="primary" @click="saveAndAdvanceBatch" :loading="savingBatchAnnotation">
              {{ canGoNextBatchItem ? '保存并继续下一条' : '保存并完成' }}
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="docDetailDialogVisible"
      title="文档详情"
      width="700px"
    >
      <div v-if="currentDocDetail" class="doc-detail-content">
        <div class="doc-detail-item">
          <label>文档ID</label>
          <p>{{ currentDocDetail.id }}</p>
        </div>
        <div class="doc-detail-item">
          <label>标题</label>
          <p>{{ currentDocDetail.title }}</p>
        </div>
        <div class="doc-detail-item" v-if="currentDocDetail.category">
          <label>分类</label>
          <p>{{ currentDocDetail.category }}</p>
        </div>
        <div class="doc-detail-item" v-if="currentDocDetail.source">
          <label>来源</label>
          <p>{{ currentDocDetail.source }}</p>
        </div>
        <div class="doc-detail-item">
          <label>内容</label>
          <div class="doc-detail-text">{{ currentDocDetail.content }}</div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="docDetailDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { evaluationApi, knowledgeApi } from '@/api/modules'

const evaluating = ref(false)
const addingDataset = ref(false)
const savingBatchAnnotation = ref(false)
const detailDialogVisible = ref(false)
const addDatasetDialogVisible = ref(false)
const batchAnnotationDialogVisible = ref(false)
const docDetailDialogVisible = ref(false)

const selectedResult = ref(null)
const datasetItems = ref([])
const evaluationResults = ref([])
const knowledgeDocs = ref([])
const editingDatasetItem = ref(null)
const selectedRelevantDocIds = ref([])
const knowledgeSearch = ref('')
const batchAnnotationQueue = ref([])
const batchAnnotationIndex = ref(0)
const jumpToIndex = ref(1)
const currentDocDetail = ref(null)

const summary = ref({
  total_evaluations: 0,
  average_scores: {},
  score_distribution: {}
})

const evalConfig = ref({
  limit: 1,
  strictness: 0,
  max_workers: 2,
  timeout: 600
})

const newDatasetItem = ref({
  question: '',
  ground_truth: '',
  category: '',
  relevant_doc_ids: []
})

const filteredKnowledgeDocs = computed(() => {
  const keyword = knowledgeSearch.value.trim().toLowerCase()
  const matchedDocs = !keyword
    ? knowledgeDocs.value
    : knowledgeDocs.value.filter(doc =>
    [doc.title, doc.content, doc.category, doc.source]
      .filter(Boolean)
      .some(field => String(field).toLowerCase().includes(keyword))
  )

  const selectedIdSet = new Set(selectedRelevantDocIds.value)
  return [...matchedDocs].sort((left, right) => {
    const leftSelected = selectedIdSet.has(left.id)
    const rightSelected = selectedIdSet.has(right.id)

    if (leftSelected === rightSelected) return 0
    return leftSelected ? -1 : 1
  })
})

const selectedKnowledgeDocs = computed(() => {
  const idSet = new Set(selectedRelevantDocIds.value)
  return knowledgeDocs.value.filter(doc => idSet.has(doc.id))
})

const batchProgressText = computed(() => {
  if (!batchAnnotationQueue.value.length) return ''
  return `${batchAnnotationIndex.value + 1} / ${batchAnnotationQueue.value.length}`
})

const canGoPreviousBatchItem = computed(() => batchAnnotationIndex.value > 0)

const canGoNextBatchItem = computed(() => batchAnnotationIndex.value < batchAnnotationQueue.value.length - 1)

const annotatedCount = computed(() => {
  return batchAnnotationQueue.value.filter(item => (item.relevant_doc_ids || []).length > 0).length
})

function formatScore(score) {
  if (score === undefined || score === null) return '-'
  return `${(score * 100).toFixed(1)}%`
}

function toPercent(score) {
  if (score === undefined || score === null) return 0
  return Number((score * 100).toFixed(2))
}

function getScoreColor(score) {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#409eff'
  if (score >= 0.4) return '#e6a23c'
  return '#f56c6c'
}

function getScoreClass(score) {
  if (score >= 0.8) return 'excellent'
  if (score >= 0.6) return 'good'
  if (score >= 0.4) return 'fair'
  return 'poor'
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

async function loadSummary() {
  try {
    const [summaryData, recordsData] = await Promise.all([
      evaluationApi.getSummary({ framework: 'ragas' }),
      evaluationApi.getRecords({ limit: 50, framework: 'ragas' })
    ])

    if (summaryData.success) {
      const evalStats = summaryData.evaluation_stats || {}
      summary.value = {
        total_evaluations: evalStats.total_evaluations || 0,
        average_scores: evalStats.average_scores || {},
        score_distribution: {}
      }
    }

    if (recordsData.success) {
      evaluationResults.value = recordsData.records || []
    }
  } catch (error) {
    console.error('加载评估摘要失败:', error)
  }
}

async function loadDataset() {
  try {
    const data = await evaluationApi.getDataset()
    if (data.success) {
      datasetItems.value = data.items || []
    }
  } catch (error) {
    console.error('加载测试数据集失败:', error)
  }
}

async function loadKnowledgeDocs() {
  try {
    const data = await knowledgeApi.getList({ limit: 100, offset: 0 })
    knowledgeDocs.value = Array.isArray(data.items) ? data.items : (Array.isArray(data) ? data : [])
  } catch (error) {
    console.error('加载知识库文档失败:', error)
    knowledgeDocs.value = []
  }
}

async function runBatchEvaluation() {
  evaluating.value = true
  try {
    const data = await evaluationApi.evaluateBatch({
      limit: evalConfig.value.limit,
      framework: 'ragas',
      strictness: evalConfig.value.strictness,
      max_workers: evalConfig.value.max_workers,
      timeout: evalConfig.value.timeout
    })

    if (data.success) {
      evaluationResults.value = data.results || []
      summary.value = data.summary || summary.value
      ElMessage.success(`RAGAS 评估完成，共评估 ${data.results.length} 条数据`)
    }
  } catch (error) {
    console.error('评估失败:', error)
    ElMessage.error(`评估失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    evaluating.value = false
  }
}

function showResultDetail(result) {
  selectedResult.value = result
  detailDialogVisible.value = true
}

function showAddDatasetDialog() {
  newDatasetItem.value = {
    question: '',
    ground_truth: '',
    category: '',
    relevant_doc_ids: []
  }
  addDatasetDialogVisible.value = true
}

async function addDatasetItem() {
  if (!newDatasetItem.value.question || !newDatasetItem.value.ground_truth) {
    ElMessage.warning('请填写问题和标准答案')
    return
  }

  addingDataset.value = true
  try {
    const data = await evaluationApi.addDatasetItem(newDatasetItem.value)
    if (data.success) {
      ElMessage.success('测试数据添加成功')
      addDatasetDialogVisible.value = false
      await loadDataset()
    }
  } catch (error) {
    ElMessage.error(`添加失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    addingDataset.value = false
  }
}

async function deleteDatasetItem(id) {
  try {
    await ElMessageBox.confirm('确定要删除这条测试数据吗？删除后无法恢复。', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const data = await evaluationApi.deleteDatasetItem(id)
    if (data.success) {
      ElMessage.success('删除成功')
      await loadDataset()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function toggleRelevantDoc(docId) {
  if (selectedRelevantDocIds.value.includes(docId)) {
    selectedRelevantDocIds.value = selectedRelevantDocIds.value.filter(id => id !== docId)
  } else {
    selectedRelevantDocIds.value = [...selectedRelevantDocIds.value, docId]
  }
}

function showDocDetail(doc) {
  currentDocDetail.value = doc
  docDetailDialogVisible.value = true
}

function handleJumpToIndex() {
  const targetIndex = jumpToIndex.value - 1
  if (targetIndex >= 0 && targetIndex < batchAnnotationQueue.value.length) {
    showBatchItem(targetIndex)
  }
}

function applyBatchAnnotationTarget(item) {
  editingDatasetItem.value = item ? { ...item } : null
  selectedRelevantDocIds.value = [...(item?.relevant_doc_ids || [])]
  knowledgeSearch.value = ''
  jumpToIndex.value = batchAnnotationIndex.value + 1
}

function buildBatchAnnotationQueue() {
  return [...datasetItems.value]
    .filter(item => item.question && item.ground_truth)
    .sort((left, right) => {
      const leftAnnotated = (left.relevant_doc_ids || []).length > 0
      const rightAnnotated = (right.relevant_doc_ids || []).length > 0

      if (leftAnnotated !== rightAnnotated) {
        return leftAnnotated ? -1 : 1
      }

      return (left.id || 0) - (right.id || 0)
    })
}

async function openBatchAnnotationDialog() {
  const queue = buildBatchAnnotationQueue()

  if (!queue.length) {
    ElMessage.warning('没有可标注的数据，请先添加测试数据')
    return
  }

  if (!knowledgeDocs.value.length) {
    await loadKnowledgeDocs()
  }

  batchAnnotationQueue.value = queue
  batchAnnotationIndex.value = 0
  applyBatchAnnotationTarget(queue[0])
  batchAnnotationDialogVisible.value = true
}

async function persistBatchAnnotation({ silent = false } = {}) {
  if (!editingDatasetItem.value) return false

  if (selectedRelevantDocIds.value.length === 0) {
    ElMessage.warning('请至少选择一个相关文档后再保存')
    return false
  }

  savingBatchAnnotation.value = true
  try {
    const data = await evaluationApi.updateDatasetItem(editingDatasetItem.value.id, {
      question: editingDatasetItem.value.question,
      ground_truth: editingDatasetItem.value.ground_truth,
      relevant_doc_ids: selectedRelevantDocIds.value
    })

    if (data.success) {
      const updatedItem = data.item
      datasetItems.value = datasetItems.value.map(item =>
        item.id === updatedItem.id
          ? { ...item, ...updatedItem }
          : item
      )

      batchAnnotationQueue.value = batchAnnotationQueue.value.map(item =>
        item.id === updatedItem.id
          ? { ...item, ...updatedItem }
          : item
      )

      if (!silent) {
        ElMessage.success('保存成功')
      }

      return true
    }
  } catch (error) {
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    savingBatchAnnotation.value = false
  }

  return false
}

async function saveCurrentBatchItem() {
  await persistBatchAnnotation()
}

function showBatchItem(index) {
  const item = batchAnnotationQueue.value[index]
  if (!item) return

  batchAnnotationIndex.value = index
  applyBatchAnnotationTarget(item)
}

function showPreviousBatchItem() {
  if (!canGoPreviousBatchItem.value) return
  showBatchItem(batchAnnotationIndex.value - 1)
}

function showNextBatchItem() {
  if (!canGoNextBatchItem.value) return
  showBatchItem(batchAnnotationIndex.value + 1)
}

async function saveAndAdvanceBatch() {
  const saved = await persistBatchAnnotation({ silent: true })
  if (!saved) return

  if (canGoNextBatchItem.value) {
    showBatchItem(batchAnnotationIndex.value + 1)
    ElMessage.success('已保存，已跳转到下一条')
    return
  }

  ElMessage.success('批量标注已完成')
  batchAnnotationDialogVisible.value = false
  await loadDataset()
}

function resetBatchAnnotationDialog() {
  batchAnnotationQueue.value = []
  batchAnnotationIndex.value = 0
  editingDatasetItem.value = null
  selectedRelevantDocIds.value = []
  knowledgeSearch.value = ''
}

onMounted(() => {
  loadSummary()
  loadDataset()
})
</script>

<style lang="scss" scoped>
.evaluation-page {
  height: 100%;
  padding: 24px;
  overflow-y: auto;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;

  h2 {
    margin: 0 0 8px;
    font-size: 22px;
    color: var(--primary-color);
  }

  p {
    margin: 0;
    color: var(--text-secondary);
    line-height: 1.6;
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--surface-color);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);

  .stat-icon {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    &.faithfulness { background: linear-gradient(135deg, #3b82f6, #6366f1); }
    &.relevancy { background: linear-gradient(135deg, #ef4444, #f97316); }
    &.precision { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
    &.overall { background: linear-gradient(135deg, #22c55e, #14b8a6); }
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    margin-top: 4px;
    color: var(--text-secondary);
    font-size: 14px;
  }
}

.top-section {
  --dataset-row-height: 180px;
  --dataset-total-height: calc(var(--dataset-row-height) * 2 + 12px);
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  margin-bottom: 20px;
  align-items: stretch;
}

.panel-card {
  background: var(--surface-color);
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.config-panel,
.dataset-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.config-panel {
  height: var(--dataset-total-height);
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;

  h3 {
    margin: 0;
    font-size: 16px;
    color: var(--text-primary);
  }
}

.panel-content {
  padding: 18px;
}

.config-panel .panel-content,
.dataset-panel .panel-content {
  flex: 1;
}

.dataset-panel .panel-content {
  display: flex;
  min-height: var(--dataset-total-height);
}

.config-panel :deep(.el-input-number),
.config-panel :deep(.el-select) {
  width: 100%;
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.input-with-suffix {
  display: flex;
  align-items: center;
}

.input-suffix {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  white-space: nowrap;
}

.header-buttons {
  display: flex;
  gap: 8px;
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  grid-auto-rows: var(--dataset-row-height);
  gap: 12px;
  flex: 1;
  max-height: var(--dataset-total-height);
  overflow-y: auto;
  align-content: start;
  padding-right: 6px;
}

.dataset-item {
  border-radius: 12px;
  background: var(--background-color);
  padding: 14px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dataset-question {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.dataset-truth {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dataset-tags,
.dataset-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.dataset-tags {
  margin-top: auto;
}

.dataset-actions {
  margin-top: 10px;
}

.results-panel {
  margin-bottom: 20px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.result-card {
  padding: 16px;
  border-radius: 12px;
  background: var(--background-color);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  }
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.result-index {
  font-weight: 700;
  color: var(--primary-color);
}

.result-time {
  flex: 1;
  font-size: 12px;
  color: var(--text-muted);
}

.result-query {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 12px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-scores-mini {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mini-score {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;

  &.excellent { background: #f0fdf4; color: #16a34a; }
  &.good { background: #eff6ff; color: #2563eb; }
  &.fair { background: #fffbeb; color: #d97706; }
  &.poor { background: #fef2f2; color: #dc2626; }
}

.detail-section {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }

  h4 {
    margin: 0 0 10px;
    font-size: 14px;
    color: var(--text-secondary);
  }

  p {
    margin: 0;
    padding: 12px;
    border-radius: 10px;
    background: var(--background-color);
    color: var(--text-primary);
    line-height: 1.7;
  }
}

.context-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.context-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  border-radius: 10px;
  background: var(--background-color);
}

.context-index {
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  background: var(--primary-color);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.context-text {
  color: var(--text-primary);
  line-height: 1.6;
}

.detail-score-item {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  &.overall {
    padding-top: 14px;
    border-top: 1px solid var(--border-color);
  }

  .label {
    display: block;
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--text-secondary);
  }
}

.batch-annotation-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.batch-annotation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.08);
}

.batch-annotation-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-annotation-text {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.batch-annotation-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.annotation-edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.edit-form-item {
  label {
    display: block;
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
  }
}

.edit-form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.annotation-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.batch-jump-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--background-color);
  border-radius: 10px;
}

.jump-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.jump-text {
  font-size: 13px;
  color: var(--text-muted);
}

.knowledge-select-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr;
  gap: 16px;
}

.knowledge-list {
  max-height: 360px;
  overflow-y: auto;
  display: grid;
  gap: 12px;
}

.knowledge-card {
  padding: 14px;
  border-radius: 12px;
  background: var(--background-color);
  border: 1px solid transparent;

  &.selected {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
  }
}

.knowledge-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.knowledge-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.knowledge-doc-id {
  color: var(--text-muted);
  font-size: 12px;
}

.knowledge-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.select-tag {
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.knowledge-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.knowledge-content {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.selected-sidebar {
  border-radius: 12px;
  background: var(--background-color);
  padding: 14px;

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: var(--text-primary);
  }
}

.selected-docs {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

.selected-doc-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: var(--surface-color);
}

.selected-doc-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.6;
}

.selected-doc-meta {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.doc-detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.doc-detail-item {
  label {
    display: block;
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 500;
    margin-bottom: 6px;
  }

  p {
    margin: 0;
    padding: 12px;
    background: var(--background-color);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.6;
  }
}

.doc-detail-text {
  padding: 16px;
  background: var(--background-color);
  border-radius: 10px;
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.batch-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.batch-footer-nav,
.batch-footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 1200px) {
  .top-section,
  .knowledge-select-grid {
    grid-template-columns: 1fr;
  }
}

.detail-view-content {
  padding: 16px;
  background: var(--background-color);
  border-radius: 10px;
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

@media (max-width: 900px) {
  .stats-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .page-header {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }

  .annotation-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .batch-annotation-bar,
  .batch-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .batch-footer-nav,
  .batch-footer-actions,
  .batch-annotation-main {
    width: 100%;
  }
}
</style>
