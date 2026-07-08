<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const backendUrl = 'http://localhost:8000'

const items = ref([])
const stats = ref({ total: 0, pending: 0, approved: 0, dispensed: 0 })
const loading = ref(true)
const error = ref('')
let pollTimer = null

const fetchData = async () => {
  try {
    const [itemsRes, statsRes] = await Promise.all([
      fetch(`${backendUrl}/api/v1/prescriptions/items/latest?limit=30`),
      fetch(`${backendUrl}/api/v1/prescriptions/stats`),
    ])
    let hasData = false
    if (itemsRes.ok) {
      const data = await itemsRes.json()
      items.value = data.list || []
      if (items.value.length > 0) {
        hasData = true
      }
    }
    if (statsRes.ok) {
      const data = await statsRes.json()
      stats.value = data
    }

    // 不使用假数据，只显示真实数据
    error.value = ''
    loading.value = false
  } catch (e) {
    console.error('PrescriptionMonitor fetch error:', e)
    // 不使用假数据，显示错误状态
    error.value = '数据获取失败，请检查网络连接'
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  pollTimer = setInterval(fetchData, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 按处方 ID 分组药品明细并按状态及时间排序
// HIS状态映射: pending(待审核)排在前面, approved(已通过)排在后面
const groupedByPrescription = computed(() => {
  const groups = {}
  for (const item of items.value) {
    const pid = item.prescription_id
    if (!groups[pid]) {
      groups[pid] = {
        prescription_id: pid,
        prescription_code: item.prescription_code || '',
        patient_name: item.patient_name || '未知患者',
        doctor_name: item.doctor_name || '系统医生',
        status: item.prescription_status,
        created_at: item.created_at,
        items: [],
      }
    }
    groups[pid].items.push(item)
  }
  return Object.values(groups).sort((a, b) => {
    // pending状态排在最前面
    if (a.status === 'pending' && b.status !== 'pending') return -1
    if (a.status !== 'pending' && b.status === 'pending') return 1
    // approved状态排在前面（仅次于pending）
    if (a.status === 'approved' && b.status !== 'approved' && b.status !== 'pending') return -1
    if (a.status !== 'approved' && a.status !== 'pending' && b.status === 'approved') return 1
    // 其他状态按时间排序
    return new Date(b.created_at) - new Date(a.created_at)
  })
})

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<template>
  <div class="patient-monitor">
    <!-- 头部标题 -->
    <div class="monitor-header">
      <div class="header-title">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.109A11.386 11.386 0 0 1 10.089 20.8a11.383 11.383 0 0 1-4.966-1.564V19.13M21 15.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM6 18.303V19.13m4.5-3.13h-4.5m4.5 0A4.125 4.125 0 0 0 3 15.75m12 0v-.003c0-1.113-.285-2.16-.786-3.07M3 15.75a3 3 0 1 1 6 0 3 3 0 0 1-6 0Zm9.458-10.223a3 3 0 1 1-5.714 0 3 3 0 0 1 5.714 0ZM21 12.75a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0ZM2.25 12.75a2.25 2.25 0 1 1 4.5 0 2.25 2.25 0 0 1-4.5 0Z" />
        </svg>
        <span>患者队列</span>
      </div>
      <div class="header-subtitle">实时同步 HIS 系统</div>
    </div>

    <!-- KPI 关键数据大看板 -->
    <!-- HIS系统状态映射: pending(待审核)→待处理处方, dispensed(已发放)→已发放处方 -->
    <div class="kpi-container">
      <div class="kpi-card warning">
        <div class="kpi-info">
          <span class="kpi-label">待处理处方</span>
          <span class="kpi-val">{{ stats.pending || 0 }}</span>
        </div>
        <div class="kpi-icon">⏳</div>
      </div>
      <div class="kpi-card success">
        <div class="kpi-info">
          <span class="kpi-label">已发放处方</span>
          <span class="kpi-val">{{ stats.dispensed || 0 }}</span>
        </div>
        <div class="kpi-icon">✓</div>
      </div>
      <div class="kpi-card info">
        <div class="kpi-info">
          <span class="kpi-label">今日总处方</span>
          <span class="kpi-val">{{ stats.total || 0 }}</span>
        </div>
        <div class="kpi-icon">📊</div>
      </div>
    </div>

    <!-- 列表内容 -->
    <div v-if="loading && !items.length" class="monitor-loading">
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
      <span>正在加载患者数据...</span>
    </div>

    <div v-else-if="error" class="monitor-error">
      {{ error }}
    </div>

    <div v-else class="monitor-body">
      <div class="patient-list">
        <div 
          v-for="group in groupedByPrescription" 
          :key="group.prescription_id"
          class="patient-card"
          :class="{ 'pending-card': group.status === 'pending', 'completed-card': group.status === 'approved' || group.status === 'dispensed' }"
        >
          <div class="card-left">
            <span class="patient-name">{{ group.patient_name }}</span>
            <span class="patient-time">{{ formatTime(group.created_at) }} · {{ group.prescription_code || '#' + group.prescription_id }}</span>
          </div>
          
          <div class="card-center">
            <div class="medicine-tags">
              <span 
                v-for="item in group.items" 
                :key="item.id" 
                class="medicine-tag"
                :class="{ 'pending-med': group.status === 'pending' }"
              >
                {{ item.medicine_name }} <span class="tag-qty">x{{ item.quantity }}</span>
              </span>
            </div>
          </div>
          
          <div class="card-right">
            <span 
              class="status-tag"
              :class="{ 'completed': group.status === 'approved' || group.status === 'dispensed', 'pending': group.status === 'pending', 'rejected': group.status === 'rejected' }"
            >
              <span v-if="group.status === 'pending'" class="pulse-dot"></span>
              {{ group.status === 'approved' ? '已发放' : group.status === 'dispensed' ? '已完成' : group.status === 'rejected' ? '已拒绝' : '待处理' }}
            </span>
          </div>
        </div>
        
        <div v-if="!groupedByPrescription.length" class="empty-state">
          <span>暂无患者挂号数据</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.patient-monitor {
  background: #ffffff;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-left: 5px solid #2563eb; /* 蓝色左边框突出核心主题 */
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 6px 24px rgba(37, 99, 235, 0.04);
}

.monitor-header {
  padding: 12px 18px;
  background: rgba(37, 99, 235, 0.03); /* 淡蓝色底面 */
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #1e3a8a; /* 突出核心标题 */
}

.header-title svg {
  width: 18px;
  height: 18px;
  color: #2563eb;
}

.header-subtitle {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

/* KPI 大看板 */
.kpi-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 14px 18px 10px 18px;
  background: rgba(255, 255, 255, 0.45);
  border-bottom: 1px solid rgba(37, 99, 235, 0.06);
}

.kpi-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.01);
  transition: all 0.2s ease;
}

.kpi-card.warning {
  border-left: 4px solid #f59e0b;
  background: linear-gradient(135deg, #ffffff 0%, rgba(245, 158, 11, 0.01) 100%);
}

.kpi-card.success {
  border-left: 4px solid #10b981;
  background: linear-gradient(135deg, #ffffff 0%, rgba(16, 185, 129, 0.01) 100%);
}

.kpi-card.info {
  border-left: 4px solid #2563eb;
  background: linear-gradient(135deg, #ffffff 0%, rgba(37, 99, 235, 0.01) 100%);
}

.kpi-info {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
  margin-bottom: 2px;
}

.kpi-val {
  font-size: 26px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1.1;
}

.kpi-card.warning .kpi-val { color: #d97706; }
.kpi-card.success .kpi-val { color: #10b981; }
.kpi-card.info .kpi-val { color: #2563eb; }

.kpi-icon {
  font-size: 16px;
  opacity: 0.8;
}

.monitor-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.monitor-body::-webkit-scrollbar {
  width: 3px;
}

.monitor-body::-webkit-scrollbar-track {
  background: transparent;
}

.monitor-body::-webkit-scrollbar-thumb {
  background: rgba(37, 99, 235, 0.15);
  border-radius: 2px;
}

.patient-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Patient Card Contrast */
.patient-card {
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.patient-card.pending-card {
  background: #ffffff;
  border: 1.5px solid rgba(37, 99, 235, 0.15);
  border-left: 5px solid #2563eb;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.05);
}

.patient-card.pending-card:hover {
  border-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.08);
}

.patient-card.completed-card {
  background: rgba(248, 250, 252, 0.55);
  border: 1px solid rgba(0, 0, 0, 0.03);
  opacity: 0.55;
}

.patient-card.completed-card:hover {
  opacity: 0.85;
  background: rgba(248, 250, 252, 0.8);
}

.card-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 100px;
}

.patient-card.pending-card .patient-name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.patient-card.completed-card .patient-name {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  text-decoration: line-through;
  text-decoration-color: rgba(100, 116, 139, 0.3);
}

.patient-time {
  font-size: 12px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.card-center {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.medicine-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.medicine-tag {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(37, 99, 235, 0.15);
  color: #0f172a;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 13px;
  transition: all 0.2s ease;
  box-shadow: inset 0 1px 1px rgba(255,255,255,0.8), 0 1px 1px rgba(0,0,0,0.01);
}

.medicine-tag.pending-med {
  background: rgba(37, 99, 235, 0.03);
  border-color: rgba(37, 99, 235, 0.2);
  color: #1d4ed8;
  font-weight: 600;
}

.medicine-tag:hover {
  background: rgba(37, 99, 235, 0.04);
  border-color: rgba(37, 99, 235, 0.25);
  color: #0f172a;
}

.tag-qty {
  color: #64748b;
  font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
  margin-left: 2px;
}

.card-right {
  display: flex;
  align-items: center;
}

.status-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.03);
  color: #64748b;
  border: 1px solid rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
}

.status-tag.completed {
  background: rgba(16, 185, 129, 0.05);
  border-color: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.status-tag.pending {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
  color: #d97706;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pulse-dot {
  width: 5px;
  height: 5px;
  background-color: #d97706;
  border-radius: 50%;
  animation: pulse-warn 1.5s infinite;
}

@keyframes pulse-warn {
  0% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.7);
  }
  70% {
    transform: scale(1.15);
    box-shadow: 0 0 0 4px rgba(217, 119, 6, 0);
  }
  100% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(217, 119, 6, 0);
  }
}

.monitor-loading {
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: #2563eb;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

.monitor-error {
  padding: 20px;
  text-align: center;
  color: #ef4444;
  font-size: 12px;
}

.empty-state {
  padding: 30px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
