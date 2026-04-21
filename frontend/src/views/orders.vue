<template>
  <div class="orders-page">
    <div class="page-container">
      <div class="page-header">
        <h2 class="page-title">订单查询</h2>
        <el-select v-model="statusFilter" placeholder="订单状态" clearable @change="loadOrders" style="width: 150px;">
          <el-option label="全部" value="" />
          <el-option label="待支付" value="pending" />
          <el-option label="已支付" value="paid" />
          <el-option label="已发货" value="shipped" />
          <el-option label="已送达" value="delivered" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </div>
      
      <div v-loading="loading" class="orders-list">
        <div v-if="orders.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无订单数据" />
        </div>
        
        <div v-for="order in orders" :key="order.id" class="order-card">
          <div class="order-header">
            <div class="order-info">
              <span class="order-no">订单号：{{ order.order_no }}</span>
              <span class="order-user" v-if="isAdmin && order.username">用户：{{ order.username }}</span>
              <span class="order-time">{{ formatDate(order.created_at) }}</span>
            </div>
            <el-tag :type="getStatusType(order.status)" size="small">
              {{ getStatusText(order.status) }}
            </el-tag>
          </div>
          
          <div class="order-items">
            <div v-for="item in order.order_items" :key="item.id" class="order-item">
              <div class="item-info">
                <span class="item-name">{{ item.product_name }}</span>
                <span class="item-quantity">x{{ item.quantity }}</span>
              </div>
              <span class="item-price">¥{{ item.unit_price }}</span>
            </div>
          </div>
          
          <div class="order-footer">
            <div class="order-total">
              共 {{ getTotalQuantity(order) }} 件商品，合计：<span class="total-amount">¥{{ order.total_amount }}</span>
            </div>
            <div class="order-actions">
              <el-button size="small" @click="showLogistics(order)" v-if="order.status !== 'pending' && order.status !== 'cancelled'">
                查看物流
              </el-button>
              <el-button size="small" @click="showDetail(order)">
                订单详情
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <el-dialog v-model="detailVisible" title="订单详情" width="500px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_no }}</el-descriptions-item>
          <el-descriptions-item label="订单状态">
            <el-tag :type="getStatusType(currentOrder.status)" size="small">
              {{ getStatusText(currentOrder.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="订单金额">¥{{ currentOrder.total_amount }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ currentOrder.payment_method || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下单时间">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="detail-items">
          <h4>商品明细</h4>
          <div v-for="item in currentOrder.order_items" :key="item.id" class="detail-item">
            <span>{{ item.product_name }}</span>
            <span>x{{ item.quantity }}</span>
            <span>¥{{ item.unit_price }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
    
    <el-dialog v-model="logisticsVisible" title="物流信息" width="500px">
      <div v-if="logistics" class="logistics-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="快递公司">{{ logistics.carrier }}</el-descriptions-item>
          <el-descriptions-item label="快递单号">{{ logistics.tracking_no }}</el-descriptions-item>
          <el-descriptions-item label="物流状态">
            <el-tag :type="getLogisticsStatusType(logistics.status)" size="small">
              {{ getLogisticsStatusText(logistics.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="logistics-tracks">
          <h4>物流轨迹</h4>
          <el-timeline>
            <el-timeline-item
              v-for="track in logistics.tracks"
              :key="track.id"
              :timestamp="track.track_time"
              placement="top"
            >
              <div class="track-location">{{ track.location }}</div>
              <div class="track-status">{{ track.status }}</div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { orderApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const orders = ref([])
const statusFilter = ref('')
const detailVisible = ref(false)
const logisticsVisible = ref(false)
const currentOrder = ref(null)
const logistics = ref(null)

const isAdmin = computed(() => userStore.isAdmin)

const statusMap = {
  pending: { text: '待支付', type: 'warning' },
  paid: { text: '已支付', type: 'info' },
  shipped: { text: '已发货', type: 'primary' },
  delivered: { text: '已送达', type: 'success' },
  cancelled: { text: '已取消', type: 'danger' }
}

const logisticsStatusMap = {
  pending: { text: '待发货', type: 'warning' },
  shipped: { text: '已发货', type: 'primary' },
  in_transit: { text: '运输中', type: '' },
  delivered: { text: '已签收', type: 'success' }
}

function getStatusText(status) {
  return statusMap[status]?.text || status
}

function getStatusType(status) {
  return statusMap[status]?.type || 'info'
}

function getLogisticsStatusText(status) {
  return logisticsStatusMap[status]?.text || status
}

function getLogisticsStatusType(status) {
  return logisticsStatusMap[status]?.type || 'info'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getTotalQuantity(order) {
  return order.order_items?.reduce((sum, item) => sum + item.quantity, 0) || 0
}

async function loadOrders() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    orders.value = await orderApi.getList(params)
  } catch (error) {
    ElMessage.error('加载订单列表失败')
  } finally {
    loading.value = false
  }
}

function showDetail(order) {
  currentOrder.value = order
  detailVisible.value = true
}

async function showLogistics(order) {
  try {
    logistics.value = await orderApi.getLogistics(order.order_no)
    logisticsVisible.value = true
  } catch (error) {
    ElMessage.error('获取物流信息失败')
  }
}

onMounted(() => {
  loadOrders()
})
</script>

<style lang="scss" scoped>
.orders-page {
  height: 100%;
  overflow-y: auto;
  background: var(--background-color);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  padding: 60px 0;
}

.order-card {
  background: var(--surface-color);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: #fafafa;
}

.order-info {
  display: flex;
  gap: 20px;
  
  .order-no {
    font-weight: 500;
    color: var(--text-primary);
  }
  
  .order-user {
    color: var(--primary-color);
    font-weight: 500;
  }
  
  .order-time {
    color: var(--text-secondary);
    font-size: 13px;
  }
}

.order-items {
  padding: 16px 20px;
}

.order-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  
  &:not(:last-child) {
    border-bottom: 1px dashed var(--border-color);
  }
}

.item-info {
  display: flex;
  gap: 12px;
  
  .item-name {
    color: var(--text-primary);
  }
  
  .item-quantity {
    color: var(--text-secondary);
  }
}

.item-price {
  color: var(--text-primary);
  font-weight: 500;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  background: #fafafa;
}

.order-total {
  color: var(--text-secondary);
  
  .total-amount {
    color: var(--error-color);
    font-size: 16px;
    font-weight: 600;
  }
}

.order-actions {
  display: flex;
  gap: 8px;
}

.order-detail {
  .detail-items {
    margin-top: 20px;
    
    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--text-primary);
    }
  }
  
  .detail-item {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
    
    &:last-child {
      border-bottom: none;
    }
  }
}

.logistics-detail {
  .logistics-tracks {
    margin-top: 20px;
    
    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--text-primary);
    }
  }
  
  .track-location {
    font-weight: 500;
    color: var(--text-primary);
  }
  
  .track-status {
    color: var(--text-secondary);
    font-size: 13px;
    margin-top: 4px;
  }
}
</style>
