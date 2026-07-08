<script setup>import { ref } from 'vue';
const queueItems = ref([
 { id: 1, name: '阿莫西林胶囊', priority: 'high', status: 'processing', progress: 75, patient: '张某某', room: 'A-101' },
 { id: 2, name: '布洛芬缓释片', priority: 'medium', status: 'waiting', progress: 0, patient: '李某某', room: 'B-203' },
 { id: 3, name: '生理盐水', priority: 'high', status: 'processing', progress: 45, patient: '王某某', room: 'C-302' },
 { id: 4, name: '葡萄糖注射液', priority: 'low', status: 'queued', progress: 0, patient: '赵某某', room: 'A-105' },
 { id: 5, name: '头孢克肟分散片', priority: 'medium', status: 'waiting', progress: 0, patient: '刘某某', room: 'B-208' },
 { id: 6, name: '氨溴索口服液', priority: 'low', status: 'queued', progress: 0, patient: '陈某某', room: 'C-305' },
]);
const stats = ref({
 total: 24,
 processing: 6,
 waiting: 12,
 completed: 6
});
const getPriorityColor = (priority) => {
 const colors = {
 high: '#ef4444',
 medium: '#f59e0b',
 low: '#3b82f6'
 };
 return colors[priority] || '#64748b';
};
const getPriorityBg = (priority) => {
 const colors = {
 high: 'rgba(239, 68, 68, 0.15)',
 medium: 'rgba(245, 158, 11, 0.15)',
 low: 'rgba(59, 130, 246, 0.15)'
 };
 return colors[priority] || 'rgba(100, 116, 139, 0.15)';
};
const getStatusText = (status) => {
 const texts = {
 processing: '配药中',
 waiting: '待处理',
 queued: '排队中',
 completed: '已完成'
 };
 return texts[status] || status;
};
const getStatusColor = (status) => {
 const colors = {
 processing: '#22c55e',
 waiting: '#f59e0b',
 queued: '#64748b',
 completed: '#22c55e'
 };
 return colors[status] || '#64748b';
};
</script>

<template>
  <div class="medicine-queue">
    <div class="queue-header">
      <div class="header-title">
        <span class="icon">💊</span>
        <h2>药品排队情况</h2>
      </div>
      <div class="queue-stats">
        <div class="stat-item">
          <span class="stat-value">{{ stats.total }}</span>
          <span class="stat-label">总任务</span>
        </div>
        <div class="stat-item">
          <span class="stat-value processing">{{ stats.processing }}</span>
          <span class="stat-label">配药中</span>
        </div>
        <div class="stat-item">
          <span class="stat-value waiting">{{ stats.waiting }}</span>
          <span class="stat-label">待处理</span>
        </div>
        <div class="stat-item">
          <span class="stat-value completed">{{ stats.completed }}</span>
          <span class="stat-label">已完成</span>
        </div>
      </div>
    </div>
    
    <div class="queue-content">
      <div class="queue-list">
        <div 
          v-for="item in queueItems" 
          :key="item.id"
          class="queue-item"
          :style="{ borderLeftColor: getPriorityColor(item.priority) }"
        >
          <div class="item-info">
            <div class="item-header">
              <span 
                class="priority-badge"
                :style="{ background: getPriorityBg(item.priority), color: getPriorityColor(item.priority) }"
              >
                {{ item.priority === 'high' ? '紧急' : item.priority === 'medium' ? '普通' : '低' }}
              </span>
              <span 
                class="status-badge"
                :style="{ color: getStatusColor(item.status) }"
              >
                {{ getStatusText(item.status) }}
              </span>
            </div>
            <h4 class="item-name">{{ item.name }}</h4>
            <div class="item-details">
              <span class="detail">
                <span class="detail-icon">👤</span>
                {{ item.patient }}
              </span>
              <span class="detail">
                <span class="detail-icon">🏠</span>
                {{ item.room }}
              </span>
            </div>
          </div>
          
          <div class="item-progress">
            <div 
              v-if="item.status === 'processing'"
              class="progress-container"
            >
              <div 
                class="progress-bar"
                :style="{ width: item.progress + '%' }"
              ></div>
              <span class="progress-text">{{ item.progress }}%</span>
            </div>
            <div v-else class="progress-placeholder">
              <span>{{ getStatusText(item.status) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="queue-chart">
        <div class="chart-title">今日配药趋势</div>
        <div class="chart-bars">
          <div class="bar-item">
            <div class="bar-fill" style="height: 60%"></div>
            <span class="bar-label">08:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 85%"></div>
            <span class="bar-label">10:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 95%"></div>
            <span class="bar-label">12:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 70%"></div>
            <span class="bar-label">14:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 80%"></div>
            <span class="bar-label">16:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 55%"></div>
            <span class="bar-label">18:00</span>
          </div>
          <div class="bar-item">
            <div class="bar-fill" style="height: 40%"></div>
            <span class="bar-label">20:00</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.medicine-queue {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.queue-header {
  padding: 16px;
  background: rgba(30, 58, 95, 0.5);
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.header-title .icon {
  font-size: 20px;
}

.header-title h2 {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}

.queue-stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #f1f5f9;
}

.stat-value.processing {
  color: #22c55e;
}

.stat-value.waiting {
  color: #f59e0b;
}

.stat-value.completed {
  color: #3b82f6;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
}

.queue-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

.queue-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-list::-webkit-scrollbar {
  width: 4px;
}

.queue-list::-webkit-scrollbar-track {
  background: rgba(51, 65, 85, 0.2);
}

.queue-list::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 2px;
}

.queue-item {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  padding: 12px;
  border-left: 4px solid;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.queue-item:hover {
  background: rgba(30, 41, 59, 0.8);
  transform: translateX(4px);
}

.item-info {
  flex: 1;
}

.item-header {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.status-badge {
  font-size: 10px;
  color: #64748b;
}

.item-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.item-details {
  display: flex;
  gap: 12px;
}

.detail {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-icon {
  font-size: 10px;
}

.item-progress {
  min-width: 100px;
  text-align: right;
}

.progress-container {
  position: relative;
  height: 8px;
  background: rgba(51, 65, 85, 0.5);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #22c55e 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: #94a3b8;
}

.progress-placeholder {
  font-size: 11px;
  color: #64748b;
}

.queue-chart {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-title {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
}

.chart-bars {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-bottom: 8px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.bar-fill {
  width: 24px;
  background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
}

.bar-label {
  font-size: 9px;
  color: #64748b;
}

@media (max-width: 1200px) {
  .queue-content {
    grid-template-columns: 1fr;
  }
  
  .queue-chart {
    order: -1;
  }
}
</style>
