<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const temperature = ref(24.5)
const humidity = ref(45)
const airQuality = ref('EXCELLENT')
const activeUnits = ref(12)
const totalUnits = ref(14)
const aiIndex = ref(99.2)

const tempHistory = ref([23.8, 24.1, 23.9, 24.3, 24.5, 24.4, 24.5])
const humidityHistory = ref([42, 43, 44, 45, 45, 44, 45])

let interval = null

onMounted(() => {
  interval = setInterval(() => {
    temperature.value = (24.0 + Math.random() * 1).toFixed(1)
    humidity.value = Math.floor(40 + Math.random() * 10)
    tempHistory.value.push(parseFloat(temperature.value))
    humidityHistory.value.push(humidity.value)
    if (tempHistory.value.length > 10) {
      tempHistory.value.shift()
      humidityHistory.value.shift()
    }
  }, 3000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})

const getAirQualityColor = (quality) => {
  const colors = {
    EXCELLENT: '#4ade80',
    GOOD: '#84cc16',
    MODERATE: '#eab308',
    POOR: '#f97316',
    SEVERE: '#ef4444'
  }
  return colors[quality] || '#64748b'
}

const getAirQualityBg = (quality) => {
  const colors = {
    EXCELLENT: 'rgba(34, 197, 94, 0.15)',
    GOOD: 'rgba(132, 204, 22, 0.15)',
    MODERATE: 'rgba(234, 179, 8, 0.15)',
    POOR: 'rgba(249, 115, 22, 0.15)',
    SEVERE: 'rgba(239, 68, 68, 0.15)'
  }
  return colors[quality] || 'rgba(100, 116, 139, 0.15)'
}
</script>

<template>
  <div class="environmental-monitor">
    <div class="monitor-header">
      <div class="icon">🌡️</div>
      <div class="header-info">
        <h3>环境监控</h3>
        <span class="status">实时更新</span>
      </div>
    </div>
    
    <div class="monitor-grid">
      <div class="monitor-card">
        <div class="card-header">
          <span class="label">温度</span>
          <span class="trend up">↑</span>
        </div>
        <div class="card-content">
          <span class="value">{{ temperature }}°C</span>
          <div class="mini-chart">
            <div 
              v-for="(val, idx) in tempHistory" 
              :key="idx"
              class="chart-bar"
              :style="{ height: ((val - 23) / 2 * 100) + '%' }"
            ></div>
          </div>
        </div>
      </div>
      
      <div class="monitor-card">
        <div class="card-header">
          <span class="label">湿度</span>
          <span class="trend stable">→</span>
        </div>
        <div class="card-content">
          <span class="value">{{ humidity }}%</span>
          <div class="mini-chart">
            <div 
              v-for="(val, idx) in humidityHistory" 
              :key="idx"
              class="chart-bar"
              :style="{ height: ((val - 35) / 20 * 100) + '%' }"
            ></div>
          </div>
        </div>
      </div>
      
      <div class="monitor-card">
        <div class="card-header">
          <span class="label">空气质量</span>
        </div>
        <div class="card-content">
          <span 
            class="value" 
            :style="{ color: getAirQualityColor(airQuality) }"
          >{{ airQuality }}</span>
          <div 
            class="quality-bar"
            :style="{ background: getAirQualityBg(airQuality) }"
          >
            <div 
              class="quality-fill"
              :style="{ width: '100%', background: getAirQualityColor(airQuality) }"
            ></div>
          </div>
        </div>
      </div>
      
      <div class="monitor-card">
        <div class="card-header">
          <span class="label">在线设备</span>
        </div>
        <div class="card-content">
          <span class="value">{{ activeUnits }}/{{ totalUnits }}</span>
          <div class="progress-bar">
            <div 
              class="progress-fill"
              :style="{ width: (activeUnits / totalUnits * 100) + '%' }"
            ></div>
          </div>
        </div>
      </div>
      
      <div class="monitor-card">
        <div class="card-header">
          <span class="label">AI 可靠性</span>
        </div>
        <div class="card-content">
          <span class="value">{{ aiIndex }}%</span>
          <div class="ai-gauge">
            <svg viewBox="0 0 100 50">
              <path 
                d="M 10 45 A 40 40 0 0 1 90 45" 
                fill="none" 
                stroke="rgba(51, 65, 85, 0.5)" 
                stroke-width="8"
                stroke-linecap="round"
              />
              <path 
                d="M 10 45 A 40 40 0 0 1 90 45" 
                fill="none" 
                stroke="#22c55e" 
                stroke-width="8"
                stroke-linecap="round"
                :stroke-dasharray="`${aiIndex * 1.26} 126`"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.environmental-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  border-radius: 8px;
  overflow: hidden;
}

.monitor-header {
  padding: 8px;
  background: rgba(30, 58, 95, 0.5);
  border-bottom: 1px solid rgba(51, 65, 85, 0.5);
  display: flex;
  align-items: center;
  gap: 8px;
}

.monitor-header .icon {
  font-size: 16px;
}

.monitor-header h3 {
  font-size: 12px;
  font-weight: 600;
  color: #f1f5f9;
}

.monitor-header .status {
  font-size: 8px;
  padding: 1px 5px;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.monitor-grid {
  flex: 1;
  padding: 6px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  overflow-y: auto;
}

.monitor-grid::-webkit-scrollbar {
  width: 4px;
}

.monitor-grid::-webkit-scrollbar-track {
  background: rgba(51, 65, 85, 0.2);
}

.monitor-grid::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 2px;
}

.monitor-card {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 6px;
  padding: 6px;
  border: 1px solid rgba(51, 65, 85, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.card-header .label {
  font-size: 9px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.trend {
  font-size: 10px;
  font-weight: bold;
}

.trend.up {
  color: #4ade80;
}

.trend.down {
  color: #ef4444;
}

.trend.stable {
  color: #94a3b8;
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content .value {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
}

.mini-chart {
  display: flex;
  gap: 2px;
  height: 16px;
  align-items: flex-end;
}

.chart-bar {
  width: 4px;
  background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 2px;
  min-height: 3px;
  transition: height 0.3s ease;
}

.quality-bar {
  width: 60px;
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
}

.quality-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-bar {
  width: 60px;
  height: 4px;
  border-radius: 2px;
  background: rgba(51, 65, 85, 0.5);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #22c55e 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.ai-gauge {
  width: 60px;
  height: 30px;
}

.ai-gauge svg {
  width: 100%;
  height: 100%;
}
</style>
