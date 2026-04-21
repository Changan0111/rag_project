<template>
  <div class="evaluation-page">
    <div class="page-header">
      <h2>内置评估</h2>
      <div class="header-actions">
        <el-button type="primary" @click="runBatchEvaluation" :loading="evaluating">
          <el-icon><DataAnalysis /></el-icon>
          批量评估
        </el-button>
        <el-button plain @click="loadSummary">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon faithfulness">
          <el-icon :size="24"><DocumentChecked /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.faithfulness) }}</div>
          <div class="stat-label">忠实度</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon relevancy">
          <el-icon :size="24"><Aim /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.answer_relevancy) }}</div>
          <div class="stat-label">答案相关性</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon precision">
          <el-icon :size="24"><Filter /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.context_precision) }}</div>
          <div class="stat-label">上下文精确度</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon overall">
          <el-icon :size="24"><TrendCharts /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ formatScore(summary.average_scores?.overall_score) }}</div>
          <div class="stat-label">综合评分</div>
        </div>
      </div>
    </div>

    <div class="top-section">
      <div class="config-panel">
        <div class="panel-card">
          <div class="panel-header">
            <h3>评估配置</h3>
          </div>
          <div class="panel-content">
            <el-form :model="evalConfig" label-width="80px">
              <el-form-item label="评估数量">
                <el-input-number v-model="evalConfig.limit" :min="1" :max="50" />
              </el-form-item>
              <el-form-item label="评估框架">
                <el-tag type="info">内置评估</el-tag>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </div>

      <div class="single-eval-panel">
        <div class="panel-card">
          <div class="panel-header">
            <h3>单条评估</h3>
          </div>
          <div class="panel-content">
            <el-form :model="singleEval" label-width="80px">
              <el-form-item label="问题">
                <el-input v-model="singleEval.query" type="textarea" :rows="2" placeholder="输入用户问题" />
              </el-form-item>
              <el-form-item label="回答">
                <el-input v-model="singleEval.answer" type="textarea" :rows="3" placeholder="输入系统回答" />
              </el-form-item>
              <el-form-item label="上下文">
                <el-input v-model="singleEval.contextsText" type="textarea" :rows="3" placeholder="输入检索上下文（每行一条）" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="runSingleEvaluation" :loading="singleEvaluating">
                  开始评估
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="panel-card" v-if="singleResult">
          <div class="panel-header">
            <h3>评估结果</h3>
          </div>
          <div class="panel-content">
            <div class="result-scores">
              <div class="score-item">
                <span class="score-label">忠实度</span>
                <el-progress 
                  :percentage="singleResult.scores.faithfulness * 100" 
                  :color="getScoreColor(singleResult.scores.faithfulness)"
                  :format="() => formatScore(singleResult.scores.faithfulness)"
                />
              </div>
              <div class="score-item">
                <span class="score-label">答案相关性</span>
                <el-progress 
                  :percentage="singleResult.scores.answer_relevancy * 100" 
                  :color="getScoreColor(singleResult.scores.answer_relevancy)"
                  :format="() => formatScore(singleResult.scores.answer_relevancy)"
                />
              </div>
              <div class="score-item">
                <span class="score-label">上下文精确度</span>
                <el-progress 
                  :percentage="singleResult.scores.context_precision * 100" 
                  :color="getScoreColor(singleResult.scores.context_precision)"
                  :format="() => formatScore(singleResult.scores.context_precision)"
                />
              </div>
              <div class="score-item overall">
                <span class="score-label">综合评分</span>
                <el-progress 
                  :percentage="singleResult.scores.overall_score * 100" 
                  :color="getScoreColor(singleResult.scores.overall_score)"
                  :format="() => formatScore(singleResult.scores.overall_score)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="results-section">
      <div class="panel-card full-width">
        <div class="panel-header">
          <h3>评估结果列表</h3>
          <el-tag>共 {{ evaluationResults.length }} 条</el-tag>
        </div>
        <div class="panel-content">
          <div class="results-grid" v-if="evaluationResults.length > 0">
            <div 
              class="result-card" 
              v-for="(result, index) in evaluationResults" 
              :key="index"
              @click="showResultDetail(result)"
            >
              <div class="result-header">
                <span class="result-index">#{{ index + 1 }}</span>
                <span class="result-time">{{ formatTime(result.created_at) }}</span>
              </div>
              <div class="result-query">{{ result.query }}</div>
              <div class="result-scores-mini">
                <span class="mini-score" :class="getScoreClass(result.scores.faithfulness)">
                  忠实: {{ formatScore(result.scores.faithfulness) }}
                </span>
                <span class="mini-score" :class="getScoreClass(result.scores.answer_relevancy)">
                  相关: {{ formatScore(result.scores.answer_relevancy) }}
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
    </div>

    <el-dialog v-model="detailDialogVisible" title="评估详情" width="700px">
      <div class="detail-content" v-if="selectedResult">
        <div class="detail-section">
          <h4>用户问题</h4>
          <p>{{ selectedResult.query }}</p>
        </div>
        <div class="detail-section">
          <h4>系统回答</h4>
          <p>{{ selectedResult.answer }}</p>
        </div>
        <div class="detail-section">
          <h4>检索上下文</h4>
          <div class="context-list">
            <div class="context-item" v-for="(ctx, idx) in selectedResult.contexts" :key="idx">
              <span class="context-index">{{ idx + 1 }}</span>
              <span class="context-text">{{ ctx }}</span>
            </div>
          </div>
        </div>
        <div class="detail-section">
          <h4>评分详情</h4>
          <div class="detail-scores">
            <div class="detail-score-item">
              <span class="label">忠实度</span>
              <el-progress 
                :percentage="selectedResult.scores.faithfulness * 100" 
                :color="getScoreColor(selectedResult.scores.faithfulness)"
                :format="() => formatScore(selectedResult.scores.faithfulness)"
              />
            </div>
            <div class="detail-score-item">
              <span class="label">答案相关性</span>
              <el-progress 
                :percentage="selectedResult.scores.answer_relevancy * 100" 
                :color="getScoreColor(selectedResult.scores.answer_relevancy)"
                :format="() => formatScore(selectedResult.scores.answer_relevancy)"
              />
            </div>
            <div class="detail-score-item">
              <span class="label">上下文精确度</span>
              <el-progress 
                :percentage="selectedResult.scores.context_precision * 100" 
                :color="getScoreColor(selectedResult.scores.context_precision)"
                :format="() => formatScore(selectedResult.scores.context_precision)"
              />
            </div>
            <div class="detail-score-item overall">
              <span class="label">综合评分</span>
              <el-progress 
                :percentage="selectedResult.scores.overall_score * 100" 
                :color="getScoreColor(selectedResult.scores.overall_score)"
                :format="() => formatScore(selectedResult.scores.overall_score)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { evaluationApi } from '@/api/modules'

const evaluating = ref(false)
const singleEvaluating = ref(false)
const detailDialogVisible = ref(false)
const selectedResult = ref(null)

const summary = ref({
  total_evaluations: 0,
  average_scores: {},
  score_distribution: {}
})

const evalConfig = ref({
  limit: 10,
  framework: 'builtin'
})

const singleEval = ref({
  query: '',
  answer: '',
  contextsText: ''
})

const singleResult = ref(null)
const evaluationResults = ref([])

function formatScore(score) {
  if (score === undefined || score === null) return '-'
  return (score * 100).toFixed(1) + '%'
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
      evaluationApi.getSummary({ framework: 'builtin' }),
      evaluationApi.getRecords({ limit: 50, framework: 'builtin' })
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
    console.error('加载摘要失败:', error)
  }
}

async function runBatchEvaluation() {
  evaluating.value = true
  try {
    const data = await evaluationApi.evaluateBatch({
      limit: evalConfig.value.limit,
      framework: 'builtin'
    })
    
    if (data.success) {
      evaluationResults.value = data.results
      summary.value = data.summary
      ElMessage.success(`内置评估完成，共 ${data.results.length} 条`)
    }
  } catch (error) {
    console.error('批量评估失败:', error)
    ElMessage.error('批量评估失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    evaluating.value = false
  }
}

async function runSingleEvaluation() {
  if (!singleEval.value.query || !singleEval.value.answer) {
    ElMessage.warning('请填写问题和回答')
    return
  }
  
  singleEvaluating.value = true
  try {
    const contexts = singleEval.value.contextsText
      .split('\n')
      .map(c => c.trim())
      .filter(c => c.length > 0)
    
    const data = await evaluationApi.evaluateSingle({
      query: singleEval.value.query,
      answer: singleEval.value.answer,
      contexts: contexts.length > 0 ? contexts : ['无上下文']
    })
    
    if (data.success) {
      singleResult.value = data
      ElMessage.success('评估完成')
    }
  } catch (error) {
    console.error('评估失败:', error)
    ElMessage.error('评估失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    singleEvaluating.value = false
  }
}

function showResultDetail(result) {
  selectedResult.value = result
  detailDialogVisible.value = true
}

onMounted(() => {
  loadSummary()
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
  align-items: center;
  margin-bottom: 24px;
  
  h2 {
    margin: 0;
    font-size: 20px;
    color: var(--primary-color);
  }
  
  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--surface-color);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  
  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    
    &.faithfulness { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    &.relevancy { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    &.precision { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    &.overall { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
  }
  
  .stat-info {
    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: var(--text-primary);
    }
    
    .stat-label {
      font-size: 14px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
  }
}

.top-section {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.config-panel {
  .panel-card {
    margin-bottom: 0;
    height: 100%;
    min-height: 360px;
  }
  
  .panel-content {
    padding: 16px;
  }
}

.single-eval-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 360px;
  
  .panel-card {
    margin-bottom: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    
    .panel-content {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }
}

.results-section {
  .panel-card.full-width {
    margin-bottom: 0;
  }
}

.panel-card {
  background: var(--surface-color);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  
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
    padding: 20px;
  }
}

.result-scores {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  
  .score-item {
    margin-bottom: 0;
    
    &.overall {
      grid-column: span 2;
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
    }
    
    .score-label {
      display: block;
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 8px;
    }
  }
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
  
  .result-card {
    padding: 16px;
    border-radius: 8px;
    background: var(--background-color);
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: var(--hover-color);
    }
    
    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .result-index {
        font-weight: 600;
        color: var(--primary-color);
      }
      
      .result-time {
        font-size: 12px;
        color: var(--text-muted);
      }
    }
    
    .result-query {
      font-size: 14px;
      color: var(--text-primary);
      margin-bottom: 12px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    
    .result-scores-mini {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      
      .mini-score {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 4px;
        
        &.excellent { background: #f0f9eb; color: #67c23a; }
        &.good { background: #ecf5ff; color: #409eff; }
        &.fair { background: #fdf6ec; color: #e6a23c; }
        &.poor { background: #fef0f0; color: #f56c6c; }
      }
    }
  }
}

.detail-content {
  .detail-section {
    margin-bottom: 20px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    h4 {
      margin: 0 0 12px;
      font-size: 14px;
      color: var(--text-secondary);
    }
    
    p {
      margin: 0;
      font-size: 14px;
      color: var(--text-primary);
      line-height: 1.6;
      padding: 12px;
      background: var(--background-color);
      border-radius: 8px;
    }
  }
}

.context-list {
  .context-item {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: var(--background-color);
    border-radius: 8px;
    margin-bottom: 8px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .context-index {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--primary-color);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      flex-shrink: 0;
    }
    
    .context-text {
      font-size: 13px;
      color: var(--text-primary);
      line-height: 1.5;
    }
  }
}

.detail-scores {
  .detail-score-item {
    margin-bottom: 16px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    &.overall {
      padding-top: 16px;
      border-top: 1px solid var(--border-color);
    }
    
    .label {
      display: block;
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 8px;
    }
  }
}
</style>
