<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 处方进度条数据列表
const prescriptions = ref([])
const loading = ref(false)
const error = ref('')

// API轮询：获取处方进度
const fetchProgress = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/v1/prescriptions/progress?limit=20')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    prescriptions.value = data.list || []
    error.value = ''
    console.log('Prescription progress updated:', data)
  } catch (err) {
    console.error('Prescription progress fetch error:', err)
    error.value = '数据加载失败，将在下次轮询重试'
  }
}

let timer = null

onMounted(() => {
  fetchProgress()
  timer = setInterval(fetchProgress, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

// 获取节点状态对应的CSS类
const getStepClass = (step) => {
  return {
    'completed': step.status === 'completed',
    'active': step.status === 'active',
    'pending': step.status === 'pending',
  }
}
</script>

<template>
  <div class="prescription-progress">
    <div class="flow-header">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="header-svg">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75c.621 0 1.125.504 1.125 1.125v12.75c0 .621-.504 1.125-1.125 1.125H5.625a1.125 1.125 0 0 1-1.125-1.125V5.625c0-.621.504-1.125 1.125-1.125Z" />
      </svg>
      <span>药品运输流程</span>
      <span class="flow-count">{{ prescriptions.length }}条处方</span>
    </div>

    <div class="flow-body">
      <!-- 空状态 -->
      <div v-if="prescriptions.length === 0 && !error" class="empty-state">
        <span>暂无进行中的处方</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="error-state">
        <span>{{ error }}</span>
      </div>

      <!-- 处方进度条列表 -->
      <div v-if="prescriptions.length > 0" class="prescription-list">
        <div
          v-for="presc in prescriptions"
          :key="presc.prescription_id"
          class="prescription-row"
        >
          <!-- 左侧：处方码 -->
          <div class="presc-info">
            <span class="presc-code">{{ presc.prescription_code }}</span>
            <span class="presc-patient">{{ presc.patient_name || '-' }}</span>
          </div>

          <!-- 右侧：4节点进度条 -->
          <div class="presc-steps-wrapper">
            <div class="steps">
              <!-- 进度条背景线 -->
              <div class="steps-progress" :style="{ width: presc.progress + '%' }"></div>

              <!-- 4个节点 -->
              <div
                v-for="step in presc.steps"
                :key="step.id"
                class="step-item"
                :class="getStepClass(step)"
              >
                <div class="step-num">{{ step.id }}</div>
                <div class="step-content">
                  <span class="step-title">{{ step.name }}</span>
                  <span v-if="step.desc" class="step-desc">{{ step.desc }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prescription-progress {
  background: #ffffff;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-left: 5px solid #2563eb;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(37, 99, 235, 0.04);
  height: 100%;
}

.flow-header {
  padding: 12px 18px;
  background: rgba(37, 99, 235, 0.03);
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #1e3a8a;
  flex-shrink: 0;
}

.header-svg {
  width: 18px;
  height: 18px;
  color: #2563eb;
  flex-shrink: 0;
}

.flow-count {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: rgba(37, 99, 235, 0.06);
  padding: 2px 10px;
  border-radius: 10px;
}

.flow-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
}

.error-state {
  color: #ef4444;
}

/* 处方列表 */
.prescription-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 每行：左侧处方信息 + 右侧进度条 */
.prescription-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid rgba(37, 99, 235, 0.06);
}

.presc-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
  flex-shrink: 0;
}

.presc-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  color: #1e3a8a;
  letter-spacing: 0.5px;
}

.presc-patient {
  font-size: 11px;
  color: #64748b;
}

/* 进度条容器 - 保持原有样式 */
.presc-steps-wrapper {
  flex: 1;
  min-width: 0;
}

/* 水平进度步骤条 - 保持原有样式 */
.steps {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  width: 100%;
  position: relative;
}

.steps::before {
  content: '';
  position: absolute;
  top: 14px;
  left: 20px;
  right: 20px;
  height: 2px;
  background: rgba(0, 0, 0, 0.05);
  z-index: 1;
}

.steps-progress {
  position: absolute;
  top: 14px;
  left: 20px;
  height: 2px;
  background: linear-gradient(90deg, #10b981 0%, #2563eb 100%);
  z-index: 1;
  transition: width 0.3s ease;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  flex: 1;
  transition: all 0.3s ease;
}

/* pending状态：灰色，未到达的节点 */
.step-item.pending {
  opacity: 0.5;
}

/* completed状态：绿色，已完成的节点 */
.step-item.completed {
  opacity: 1;
}

/* active状态：蓝色呼吸动画，当前正在进行的节点 */
.step-item.active {
  background: rgba(37, 99, 235, 0.05);
  border: 1.5px solid rgba(37, 99, 235, 0.25);
  border-radius: 8px;
  padding: 4px 8px;
  margin: -4px -4px;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.08);
  position: relative;
  z-index: 5;
  transform: translateY(-2px);
}

.step-item.active::before {
  content: '进行中';
  position: absolute;
  top: -14px;
  left: 50%;
  transform: translateX(-50%);
  background: #2563eb;
  color: #ffffff;
  font-size: 8px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  white-space: nowrap;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);
  animation: bounce-small 2s infinite;
}

@keyframes bounce-small {
  0%, 100% { transform: translate(-50%, 0); }
  50% { transform: translate(-50%, -2px); }
}

.step-num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #f8fafc;
  border: 2px solid #cbd5e1;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.3s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

/* completed状态：绿色实心圆 */
.step-item.completed .step-num {
  background: #10b981;
  border-color: #10b981;
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(16, 185, 129, 0.3);
}

/* active状态：蓝色圆形 + 呼吸动画 */
.step-item.active .step-num {
  border-color: #2563eb;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.05);
  position: relative;
  box-shadow: 0 0 10px rgba(37, 99, 235, 0.15);
}

.step-item.active .step-num::before,
.step-item.active .step-num::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(37, 99, 235, 0.35);
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  animation: double-pulse 2s infinite ease-out;
  pointer-events: none;
}

.step-item.active .step-num::after {
  animation-delay: 1s;
}

@keyframes double-pulse {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

.step-content {
  margin-top: 10px;
  text-align: center;
}

.step-title {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}

.step-desc {
  display: block;
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
  line-height: 1.2;
}

.step-item.active .step-title {
  color: #2563eb;
  font-weight: 700;
}

.step-item.completed .step-title {
  color: #0f172a;
}
</style>
