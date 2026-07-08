<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  title: String,
  location: String,
  status: {
    type: String,
    default: 'LIVE'
  },
  cameraId: String,
  isPov: {
    type: Boolean,
    default: false
  }
})

const backendUrl = 'http://localhost:8000'

const isRecording = ref(true)
const signalStrength = ref('STABLE')
const battery = ref(86)
const speed = ref(0.4)
const power = ref(12)
const heading = ref(284)
const streamError = ref(false)
const isLoading = ref(true)
const retryTimer = ref(null)
const countdown = ref(5)
const streamKey = ref(0) // 用于强制重新创建img元素

const cameraStreamUrl = computed(() => {
  if (props.isPov) {
    if (props.cameraId === 'ROBOT_02') {
      return `${backendUrl}/api/v1/camera/robot2`
    }
    return `${backendUrl}/api/v1/camera/robot`
  }
  return `${backendUrl}/api/v1/camera/opencv`
})

// 图片加载成功
const handleImageLoad = () => {
  isLoading.value = false
  streamError.value = false
}

// 图片加载失败（延迟3秒再显示错误，给RTSP连接时间）
let errorDelayTimer = null
const handleImageError = () => {
  if (errorDelayTimer) return // 防止重复触发
  errorDelayTimer = setTimeout(() => {
    streamError.value = true
    isLoading.value = false
    countdown.value = 5
    if (retryTimer.value) clearInterval(retryTimer.value)
    retryTimer.value = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(retryTimer.value)
        retryTimer.value = null
        doRetry()
      }
    }, 1000)
    errorDelayTimer = null
  }, 3000) // 延迟3秒显示错误
}

// 执行重试
const doRetry = () => {
  streamKey.value++ // 强制重新创建img元素，避免浏览器缓存错误状态
  isLoading.value = true
  streamError.value = false
}

// 强制刷新视频流
const refreshStream = () => {
  if (retryTimer.value) {
    clearInterval(retryTimer.value)
    retryTimer.value = null
  }
  if (errorDelayTimer) {
    clearTimeout(errorDelayTimer)
    errorDelayTimer = null
  }
  doRetry()
}

const getStatusColor = (status) => {
  return status === 'LIVE' ? '#10b981' : '#d97706'
}

const getSignalColor = (signal) => {
  const colors = {
    STABLE: '#10b981',
    WEAK: '#d97706',
    LOST: '#ef4444'
  }
  return colors[signal] || '#64748b'
}
</script>

<template>
  <div class="camera-feed glass-card">
    <div class="feed-header">
      <h3>{{ title }}</h3>
    </div>
    
    <div class="feed-content">
      <div class="video-container">
        <!-- 加载中状态 -->
        <div v-if="isLoading && !streamError" class="stream-loading">
          <div class="loading-spinner"></div>
          <div class="loading-text">正在连接摄像头...</div>
        </div>
        <!-- 错误状态 -->
        <div v-else-if="streamError" class="stream-error" @click="refreshStream">
          <div class="error-icon">&#9888;</div>
          <div class="error-text">摄像头连接失败</div>
          <div class="error-hint">点击重试 ({{ countdown }}秒后自动重试)</div>
        </div>
        <!-- 正常视频流 -->
        <img
          v-show="!streamError"
          :key="streamKey"
          :src="cameraStreamUrl"
          alt="Camera feed"
          class="video-feed"
          @load="handleImageLoad"
          @error="handleImageError"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.camera-feed {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(37, 99, 235, 0.12);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.feed-header {
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.45);
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
  display: flex;
  justify-content: center;
  align-items: center;
}

.feed-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  text-align: center;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.camera-id {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.record-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  color: #ef4444;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.record-btn.recording {
  background: rgba(239, 68, 68, 0.15);
}

.record-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.feed-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.video-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
  background: #f1f5f9;
}

.video-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.stream-error {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  cursor: pointer;
  gap: 8px;
}

.stream-loading {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  gap: 12px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(37, 99, 235, 0.1);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 13px;
  color: #64748b;
}

.error-icon {
  font-size: 36px;
  color: #d97706;
}

.error-text {
  font-size: 14px;
  color: #334155;
  font-weight: 600;
}

.error-hint {
  font-size: 11px;
  color: #64748b;
}

.pov-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.holographic-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 200px;
  height: 200px;
  border: 2px solid rgba(37, 99, 235, 0.35);
  border-radius: 50%;
  animation: rotate 10s linear infinite;
}

.holographic-ring.ring-2 {
  width: 300px;
  height: 300px;
  border-color: rgba(16, 185, 129, 0.2);
  animation-direction: reverse;
  animation-duration: 15s;
}

@keyframes rotate {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.navigation-line {
  position: absolute;
  bottom: 30%;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 40%;
  background: linear-gradient(180deg, #2563eb 0%, transparent 100%);
}

.feed-info {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.35);
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgba(37, 99, 235, 0.08);
}

.info-item {
  display: flex;
  gap: 8px;
}

.info-label {
  font-size: 10px;
  color: #64748b;
}

.info-value {
  font-size: 11px;
  color: #334155;
  font-family: monospace;
}

.pov-data {
  padding: 10px 16px;
  background: rgba(248, 250, 252, 0.9);
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
}

.data-row {
  display: flex;
  justify-content: space-around;
}

.data-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.data-label {
  font-size: 9px;
  color: #64748b;
}

.data-value {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  font-family: monospace;
}
</style>
