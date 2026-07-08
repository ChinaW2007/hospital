<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ChatAssistant from './components/ChatAssistant.vue'
import CameraFeed from './components/CameraFeed.vue'
import PrescriptionMonitor from './components/PrescriptionMonitor.vue'
import PrescriptionProgress from './components/PrescriptionProgress.vue'

// 时钟状态
const currentTime = ref('')
const updateTime = () => {
  const d = new Date()
  const pad = n => String(n).padStart(2, '0')
  currentTime.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 传感器状态
const temperature = ref(24.5)
const humidity = ref(45)
const airQuality = ref('极佳')
const activeUnits = ref(12)
const totalUnits = ref(14)

// 聊天展开状态
const isChatOpen = ref(false)

let timer = null
let sensorTimer = null

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)

  sensorTimer = setInterval(() => {
    temperature.value = (24.0 + Math.random() * 1).toFixed(1)
    humidity.value = Math.floor(40 + Math.random() * 10)
  }, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (sensorTimer) clearInterval(sensorTimer)
})

const toggleChat = () => {
  isChatOpen.value = !isChatOpen.value
}
</script>

<template>
  <div class="dashboard">
    <!-- 顶部 Header -->
    <header class="dashboard-header">
      <div class="header-left">
        <span class="current-time">{{ currentTime }}</span>
      </div>
      
      <div class="header-center">
        <h1>药剂师可视化大屏</h1>
      </div>
      
      <div class="header-right">
        <div class="sensor-inline">
          <div class="sensor-pill">
            <span class="sensor-label">温度</span>
            <span class="sensor-value">{{ temperature }}°C</span>
          </div>
          <div class="sensor-pill">
            <span class="sensor-label">湿度</span>
            <span class="sensor-value">{{ humidity }}%</span>
          </div>
          <div class="sensor-pill">
            <span class="sensor-label">环境</span>
            <span class="sensor-value success">{{ airQuality }}</span>
          </div>
          <div class="sensor-pill">
            <span class="sensor-label">设备率</span>
            <span class="sensor-value">{{ activeUnits }}/{{ totalUnits }}</span>
          </div>
        </div>
      </div>
    </header>
    
    <!-- 主体内容 -->
    <main class="dashboard-main">
      <!-- 中间摄像头行 -->
      <section class="camera-row">
        <CameraFeed
          title="机器人导航 (POV 1)"
          location="UNIT_RX_09"
          camera-id="ROBOT_01"
          :is-pov="true"
          status="ACTIVE"
        />
        <CameraFeed
          title="走廊监控 (LIVE)"
          location="WEST_WING_LVL4"
          camera-id="CAM_042"
          status="ACTIVE"
        />
        <CameraFeed
          title="机器人导航 (POV 2)"
          location="UNIT_RX_10"
          camera-id="ROBOT_02"
          :is-pov="true"
          status="ACTIVE"
        />
      </section>
      
      <!-- 底部双栏行 -->
      <section class="bottom-row">
        <!-- 左侧：药品运输流程（按处方显示进度条） -->
        <PrescriptionProgress />
        
        <!-- 右侧：挂号患者列表 -->
        <div class="patient-list-container">
          <PrescriptionMonitor />
        </div>
      </section>
    </main>
    
    <!-- 右下角悬浮 AI 助手 -->
    <div class="floating-chat-container">
      <div v-if="isChatOpen" class="chat-window-popup">
        <ChatAssistant />
      </div>
      <button class="chat-fab" @click="toggleChat" :class="{ 'active': isChatOpen }">
        <svg v-if="!isChatOpen" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="fab-svg">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="fab-svg">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style>
/* 全局页面样式重置，避免双重滚动条 */
html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  height: 100vh;
  width: 100vw;
  background: #f8fafc;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>

<style scoped>
.dashboard {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
  box-sizing: border-box;
}

/* Header 布局与毛玻璃优化 (亮色主题) */
.dashboard-header {
  height: 56px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(37, 99, 235, 0.12);
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  align-items: center;
  padding: 0 20px;
  box-sizing: border-box;
  z-index: 10;
}

.header-left {
  display: flex;
  justify-content: flex-start;
}

.current-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #334155;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.header-center {
  display: flex;
  justify-content: center;
}

.header-center h1 {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 6px;
  margin: 0;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 1px 3px rgba(37, 99, 235, 0.08);
}

.header-right {
  display: flex;
  justify-content: flex-end;
}

.sensor-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sensor-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  background: rgba(37, 99, 235, 0.05);
  border: 1px solid rgba(37, 99, 235, 0.15);
  padding: 3px 8px;
  border-radius: 4px;
}

.sensor-label {
  color: #64748b;
}

.sensor-value {
  color: #334155;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
}

.sensor-value.success {
  color: #10b981;
}

/* 主内容布局比例控制 */
.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 16px;
  box-sizing: border-box;
  overflow: hidden;
  height: calc(100vh - 56px);
}

/* 中间摄像头行 (48%高度) */
.camera-row {
  height: 48%;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  box-sizing: border-box;
}

/* 底部双栏行 (52%减去gap高度) */
.bottom-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 16px;
  box-sizing: border-box;
  min-height: 0;
}

.patient-list-container {
  min-height: 0;
  height: 100%;
}

/* 右下角悬浮 AI 助手 */
.floating-chat-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.chat-window-popup {
  width: 340px;
  height: 440px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.12);
  transform-origin: bottom right;
  animation: popup-slide 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes popup-slide {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.chat-fab {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(37, 99, 235, 0.15);
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.chat-fab:hover {
  border-color: #2563eb;
  color: #1d4ed8;
  transform: scale(1.05);
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.12);
}

.chat-fab.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.25);
}

.fab-svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
</style>
