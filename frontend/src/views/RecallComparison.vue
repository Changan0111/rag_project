<template>
  <div class="recall-page">
    <div class="page-header">
      <div>
        <h2>Top-K 检索对比实验</h2>
        <p>基于 <b>relevant_doc_ids</b> 标注结果，对不同检索方式在 <b>Top-3 / Top-5 / Top-10</b> 下的命中表现进行评测。</p>
      </div>
      <el-button type="primary" @click="runComparison" :loading="running">
        <el-icon><Histogram /></el-icon>
        开始实验
      </el-button>
    </div>

    <div class="top-grid">
      <div class="panel-card">
        <div class="panel-header">
          <h3>实验配置</h3>
        </div>
        <div class="panel-content">
          <el-form :model="form" label-width="110px">
            <el-form-item label="样本数量">
              <el-input-number v-model="form.sample_limit" :min="1" :max="50" />
            </el-form-item>
            <el-form-item label="Top-K 列表">
              <el-input v-model="form.top_ks_text" placeholder="例如 3,5,10" />
            </el-form-item>
            <el-form-item label="检索方式">
              <el-checkbox-group v-model="form.retrieval_modes">
                <el-checkbox label="vector">向量检索</el-checkbox>
                <el-checkbox label="bm25">BM25</el-checkbox>
                <el-checkbox label="hybrid">混合检索</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="混合权重">
              <el-input
                v-model="form.vector_weights_text"
                placeholder="例如 0.3,0.5,0.7"
                :disabled="!form.retrieval_modes.includes('hybrid')"
              />
              <div class="form-tip">仅在混合检索模式下生效。该权重表示“向量检索权重”，越大越偏向向量检索。</div>
            </el-form-item>
            <el-form-item label="最佳配置排序">
              <el-select v-model="form.best_sort_by" placeholder="选择排序策略" style="width: 100%;">
                <el-option label="优先 Hit@K（更强调命中率）" value="hit_rate" />
                <el-option label="优先 MRR（更强调相关文档排在前面）" value="mrr" />
                <el-option label="优先 F1（权衡 Recall 与 Precision）" value="f1" />
              </el-select>
              <div class="form-tip">用于决定“最佳配置”的排序方式，不影响单次检索本身。</div>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h3>实验摘要</h3>
        </div>
        <div class="panel-content">
          <div v-if="comparisonResults" class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">样本数</span>
              <strong>{{ comparisonResults.sample_count }}</strong>
            </div>
            <div class="summary-item">
              <span class="summary-label">配置数</span>
              <strong>{{ comparisonResults.config_count }}</strong>
            </div>
            <div class="summary-item wide" v-if="summaryExperiment">
              <span class="summary-label">最佳配置</span>
              <strong>{{ summaryExperiment.config_label }}</strong>
            </div>
            <div class="summary-item" v-if="summaryExperiment">
              <span class="summary-label">平均 Hit@K</span>
              <strong>{{ formatPercent(summaryExperiment.hit_rate) }}</strong>
            </div>
            <div class="summary-item" v-if="summaryExperiment">
              <span class="summary-label">MRR</span>
              <strong>{{ formatPercent(summaryExperiment.mrr) }}</strong>
            </div>
            <div class="summary-item" v-if="summaryExperiment">
              <span class="summary-label">平均 F1@K</span>
              <strong>{{ formatPercent(summaryExperiment.average_f1_at_k) }}</strong>
            </div>
            <div class="summary-item" v-if="summaryExperiment && !singleLabelMode">
              <span class="summary-label">平均 Recall@K</span>
              <strong>{{ formatPercent(summaryExperiment.average_recall_at_k) }}</strong>
            </div>
            <div class="summary-item" v-if="summaryExperiment && !singleLabelMode">
              <span class="summary-label">平均 Precision@K</span>
              <strong>{{ formatPercent(summaryExperiment.average_precision_at_k) }}</strong>
            </div>
          </div>
          <el-empty v-else description="运行实验后显示摘要" :image-size="70" />

        </div>
      </div>
    </div>

    <div v-if="comparisonResults?.experiments?.length" class="results-grid">
      <div class="panel-card">
        <div class="panel-header">
          <h3>指标对比</h3>
        </div>
        <div class="panel-content">
          <div
            v-for="experiment in comparisonResults.experiments"
            :key="experiment.config_label"
            class="compare-row"
            :class="{ active: selectedExperiment?.config_label === experiment.config_label }"
            @click="selectExperiment(experiment)"
          >
            <div class="compare-title">
              <div class="name">{{ experiment.config_label }}</div>
              <div class="meta">
                <el-tag size="small">{{ experiment.retrieval_mode }}</el-tag>
                <el-tag size="small" type="info">Top-{{ experiment.top_k }}</el-tag>
              </div>
            </div>

            <div class="metric-row">
              <span>Hit@K</span>
              <div class="bar-track">
                <div class="bar-fill hit" :style="{ width: scoreWidth(experiment.hit_rate) }"></div>
              </div>
              <strong>{{ formatPercent(experiment.hit_rate) }}</strong>
            </div>
            <div class="metric-row">
              <span>MRR</span>
              <div class="bar-track">
                <div class="bar-fill mrr" :style="{ width: scoreWidth(experiment.mrr) }"></div>
              </div>
              <strong>{{ formatPercent(experiment.mrr) }}</strong>
            </div>
            <div class="metric-row">
              <span>F1</span>
              <div class="bar-track">
                <div class="bar-fill precision" :style="{ width: scoreWidth(experiment.average_f1_at_k) }"></div>
              </div>
              <strong>{{ formatPercent(experiment.average_f1_at_k) }}</strong>
            </div>
            <div v-if="!singleLabelMode" class="metric-row">
              <span>Recall</span>
              <div class="bar-track">
                <div class="bar-fill recall" :style="{ width: scoreWidth(experiment.average_recall_at_k) }"></div>
              </div>
              <strong>{{ formatPercent(experiment.average_recall_at_k) }}</strong>
            </div>
            <div v-if="!singleLabelMode" class="metric-row">
              <span>Precision</span>
              <div class="bar-track">
                <div class="bar-fill precision" :style="{ width: scoreWidth(experiment.average_precision_at_k) }"></div>
              </div>
              <strong>{{ formatPercent(experiment.average_precision_at_k) }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h3>配置结果表</h3>
        </div>
        <div class="panel-content">
          <el-table :data="comparisonResults.experiments" stripe @row-click="selectExperiment">
            <el-table-column prop="config_label" label="配置" min-width="240" />
            <el-table-column prop="retrieval_mode" label="方式" width="100" />
            <el-table-column prop="top_k" label="Top-K" width="90" />
            <el-table-column label="权重" width="100">
              <template #default="{ row }">
                {{ row.vector_weight ?? '-' }}
              </template>
            </el-table-column>
            <el-table-column label="Hit@K" width="110">
              <template #default="{ row }">
                {{ formatPercent(row.hit_rate) }}
              </template>
            </el-table-column>
            <el-table-column label="MRR" width="100">
              <template #default="{ row }">
                {{ formatPercent(row.mrr) }}
              </template>
            </el-table-column>
            <el-table-column label="F1@K" width="110">
              <template #default="{ row }">
                {{ formatPercent(row.average_f1_at_k) }}
              </template>
            </el-table-column>
            <el-table-column v-if="!singleLabelMode" label="Recall@K" width="120">
              <template #default="{ row }">
                {{ formatPercent(row.average_recall_at_k) }}
              </template>
            </el-table-column>
            <el-table-column v-if="!singleLabelMode" label="Precision@K" width="130">
              <template #default="{ row }">
                {{ formatPercent(row.average_precision_at_k) }}
              </template>
            </el-table-column>
            <el-table-column label="平均返回数" width="120">
              <template #default="{ row }">
                {{ row.average_retrieved_count }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <div v-if="selectedExperiment" class="panel-card detail-panel">
      <div class="panel-header">
        <h3>样本明细</h3>
        <el-tag type="success">{{ selectedExperiment.config_label }}</el-tag>
      </div>
      <div class="panel-content">
        <div class="sample-grid">
          <div v-for="(sample, index) in selectedExperiment.samples" :key="index" class="sample-card">
            <div class="sample-head">
              <span class="sample-index">样本 {{ index + 1 }}</span>
              <el-tag :type="sample.is_hit ? 'success' : 'danger'" size="small">
                {{ sample.is_hit ? '命中' : '未命中' }}
              </el-tag>
            </div>

            <div class="sample-block">
              <span class="block-label">问题</span>
              <p>{{ sample.question }}</p>
            </div>

            <div class="sample-block" v-if="sample.ground_truth">
              <span class="block-label">标准答案</span>
              <p>{{ sample.ground_truth }}</p>
            </div>

            <div class="sample-block">
              <span class="block-label">标准相关文档 ID</span>
              <div class="id-list">
                <el-tag v-for="docId in sample.relevant_doc_ids" :key="docId" size="small" type="success">
                  #{{ docId }}
                </el-tag>
              </div>
            </div>

            <div class="sample-block">
              <span class="block-label">实际召回文档 ID</span>
              <div class="id-list">
                <el-tag v-for="docId in sample.retrieved_doc_ids" :key="docId" size="small">
                  #{{ docId }}
                </el-tag>
                <span v-if="!sample.retrieved_doc_ids?.length" class="empty-text">无返回结果</span>
              </div>
            </div>

            <div class="score-inline">
              <div class="score-chip">
                <span>Hit@K</span>
                <strong>{{ formatPercent(sample.is_hit ? 1 : 0) }}</strong>
              </div>
              <div class="score-chip">
                <span>命中排名</span>
                <strong>{{ sample.first_hit_rank || '-' }}</strong>
              </div>
              <div class="score-chip">
                <span>MRR</span>
                <strong>{{ formatPercent(sample.reciprocal_rank) }}</strong>
              </div>
              <div v-if="!singleLabelMode" class="score-chip">
                <span>Recall@K</span>
                <strong>{{ formatPercent(sample.recall_at_k) }}</strong>
              </div>
              <div v-if="!singleLabelMode" class="score-chip">
                <span>Precision@K</span>
                <strong>{{ formatPercent(sample.precision_at_k) }}</strong>
              </div>
            </div>

            <div class="sample-block">
              <span class="block-label">命中文档</span>
              <div class="id-list">
                <el-tag
                  v-for="docId in sample.matched_doc_ids"
                  :key="docId"
                  size="small"
                  type="warning"
                >
                  #{{ docId }}
                </el-tag>
                <span v-if="!sample.matched_doc_ids?.length" class="empty-text">未命中标准相关文档</span>
              </div>
            </div>

            <div class="sample-block">
              <span class="block-label">检索结果明细</span>
              <div v-if="sample.retrieved_docs?.length" class="retrieved-docs">
                <div v-for="doc in sample.retrieved_docs" :key="`${sample.question}-${doc.doc_id}`" class="retrieved-doc-item">
                  <div class="retrieved-doc-head">
                    <span class="doc-id">#{{ doc.doc_id }}</span>
                    <el-tag
                      size="small"
                      :type="sample.matched_doc_ids.includes(doc.doc_id) ? 'success' : 'info'"
                    >
                      {{ sample.matched_doc_ids.includes(doc.doc_id) ? '相关' : '非标注相关' }}
                    </el-tag>
                  </div>
                  <div class="doc-content">{{ doc.content }}</div>
                </div>
              </div>
              <el-empty v-else description="该样本没有检索结果" :image-size="50" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Histogram } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { evaluationApi } from '@/api/modules'

const running = ref(false)
const comparisonResults = ref(null)
const selectedExperiment = ref(null)

const form = ref({
  sample_limit: 10,
  top_ks_text: '3,5,10',
  retrieval_modes: ['vector', 'bm25', 'hybrid'],
  vector_weights_text: '0.3,0.5,0.7',
  best_sort_by: 'hit_rate'
})

const singleLabelMode = computed(() => Boolean(comparisonResults.value?.single_label_mode))
const summaryExperiment = computed(() => (
  comparisonResults.value?.best_experiment ||
  comparisonResults.value?.experiments?.[0] ||
  null
))

function parseIntegerList(text) {
  return [...new Set(
    (text || '')
      .split(',')
      .map(item => Number(item.trim()))
      .filter(item => Number.isInteger(item) && item > 0)
  )].sort((left, right) => left - right)
}

function parseFloatList(text) {
  return [...new Set(
    (text || '')
      .split(',')
      .map(item => Number(item.trim()))
      .filter(item => !Number.isNaN(item) && item >= 0 && item <= 1)
  )].sort((left, right) => left - right)
}

function formatPercent(value) {
  if (value === undefined || value === null) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function scoreWidth(value) {
  const numeric = Number(value || 0)
  return `${Math.max(0, Math.min(100, numeric * 100))}%`
}

function selectExperiment(experiment) {
  selectedExperiment.value = experiment
}

async function runComparison() {
  const topKs = parseIntegerList(form.value.top_ks_text)
  const vectorWeights = parseFloatList(form.value.vector_weights_text)

  if (!topKs.length) {
    ElMessage.warning('请至少输入一个有效的 Top-K')
    return
  }

  if (!form.value.retrieval_modes.length) {
    ElMessage.warning('请至少选择一种检索方式')
    return
  }

  if (form.value.retrieval_modes.includes('hybrid') && !vectorWeights.length) {
    ElMessage.warning('混合检索至少需要一个有效权重')
    return
  }

  running.value = true
  try {
    const data = await evaluationApi.compareRecallConfigs({
      sample_limit: form.value.sample_limit,
      top_ks: topKs,
      retrieval_modes: form.value.retrieval_modes,
      vector_weights: vectorWeights,
      best_sort_by: form.value.best_sort_by
    })

    if (data.success) {
      comparisonResults.value = data.results
      selectedExperiment.value = data.results.experiments?.[0] || null
      ElMessage.success(`Top-K 实验完成，共生成 ${data.results.config_count} 组配置`)
    }
  } catch (error) {
    console.error('Top-K 对比失败:', error)
    ElMessage.error(`Top-K 对比失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    running.value = false
  }
}
</script>

<style lang="scss" scoped>
.recall-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
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

.top-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.results-grid {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.panel-card {
  background: var(--surface-color);
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-color);

  h3 {
    margin: 0;
    font-size: 16px;
    color: var(--text-primary);
  }
}

.panel-content {
  padding: 20px;
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  padding: 14px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(26, 54, 93, 0.06), rgba(34, 197, 94, 0.08));

  &.wide {
    grid-column: span 2;
  }

  .summary-label {
    display: block;
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  strong {
    display: block;
    color: var(--text-primary);
    line-height: 1.5;
  }
}

.compare-row {
  padding: 16px;
  border-radius: 12px;
  background: var(--background-color);
  margin-bottom: 12px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover,
  &.active {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
  }
}

.compare-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;

  .name {
    font-weight: 600;
    color: var(--text-primary);
  }

  .meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}

.metric-row {
  display: grid;
  grid-template-columns: 70px 1fr 68px;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;

  &:last-child {
    margin-bottom: 0;
  }

  span {
    color: var(--text-secondary);
    font-size: 13px;
  }

  strong {
    text-align: right;
    color: var(--text-primary);
    font-size: 13px;
  }
}

.bar-track {
  height: 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;

  &.recall {
    background: linear-gradient(90deg, #2563eb, #38bdf8);
  }

  &.precision {
    background: linear-gradient(90deg, #16a34a, #4ade80);
  }

  &.hit {
    background: linear-gradient(90deg, #f59e0b, #facc15);
  }

  &.mrr {
    background: linear-gradient(90deg, #7c3aed, #c084fc);
  }
}

.detail-panel {
  margin-bottom: 20px;
}

.sample-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.sample-card {
  border-radius: 14px;
  background: var(--background-color);
  padding: 16px;
}

.sample-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.sample-index {
  font-weight: 600;
  color: var(--primary-color);
}

.sample-block {
  margin-bottom: 14px;

  .block-label {
    display: block;
    margin-bottom: 8px;
    color: var(--text-secondary);
    font-size: 13px;
  }

  p {
    margin: 0;
    padding: 12px;
    border-radius: 10px;
    background: var(--surface-color);
    color: var(--text-primary);
    line-height: 1.7;
  }
}

.id-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-text {
  color: var(--text-muted);
  font-size: 12px;
}

.score-inline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.score-chip {
  padding: 12px;
  border-radius: 12px;
  background: var(--surface-color);

  span {
    display: block;
    margin-bottom: 6px;
    color: var(--text-secondary);
    font-size: 12px;
  }

  strong {
    color: var(--text-primary);
  }
}

.retrieved-docs {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.retrieved-doc-item {
  padding: 12px;
  border-radius: 10px;
  background: var(--surface-color);
}

.retrieved-doc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.doc-id {
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
}

.doc-content {
  color: var(--text-primary);
  line-height: 1.6;
  font-size: 13px;
}

@media (max-width: 1200px) {
  .top-grid,
  .results-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
  }

  .summary-grid,
  .score-inline {
    grid-template-columns: 1fr;
  }

  .summary-item.wide {
    grid-column: span 1;
  }

  .sample-grid {
    grid-template-columns: 1fr;
  }
}
</style>
