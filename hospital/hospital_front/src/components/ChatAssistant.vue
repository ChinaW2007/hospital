<script setup>
import { ref, onMounted, nextTick } from 'vue'

const messages = ref([
  {
    id: 1,
    sender: 'ai',
    content: '您好，这里是系统助手。请问有什么我可以协助您的？',
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
])

const inputMessage = ref('')
const isLoading = ref(false)
const chatContainer = ref(null)

const backendUrl = 'http://localhost:8000'

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || isLoading.value) return
  
  const currentTime = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  
  messages.value.push({
    id: Date.now(),
    sender: 'user',
    content: text,
    time: currentTime
  })
  
  inputMessage.value = ''
  isLoading.value = true
  await scrollToBottom()
  
  try {
    const res = await fetch(`${backendUrl}/api/v1/agent/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ query: text })
    })
    
    if (res.ok) {
      const data = await res.json()
      messages.value.push({
        id: Date.now() + 1,
        sender: 'ai',
        content: data.response,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })
    } else {
      throw new Error('接口返回异常')
    }
  } catch (error) {
    console.error('AI Assistant Error:', error)
    messages.value.push({
      id: Date.now() + 2,
      sender: 'ai',
      content: '服务响应异常，请稍后重试。',
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="chat-assistant">
    <!-- 极简头部 -->
    <div class="chat-header">
      <div class="header-icon">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.083.185.125.39.125.603V16.5a2.25 2.25 0 0 1-2.25 2.25h-1.072a4.78 4.78 0 0 0-1.413.236l-2.167.723a1.5 1.5 0 0 1-1.9-.382l-1.176-1.43a1.5 1.5 0 0 0-1.157-.497H7.5A2.25 2.25 0 0 1 5.25 16.5V9.114c0-.213.042-.418.125-.603m14.875 0c-.04-.087-.09-.168-.147-.243M19.5 8.25c-.18.005-.358-.003-.535-.024m-12.44 0a4.12 4.12 0 0 1-.535.024m14.875 0a3.75 3.75 0 0 0-1.493-2.923l-3.326-2.5a3.75 3.75 0 0 0-4.502 0l-3.326 2.5A3.75 3.75 0 0 0 5.25 8.25m14.25 0A3 3 0 1 1 13.5 8.25m-11.25 0a3 3 0 1 1 5.25 0" />
        </svg>
      </div>
      <div class="header-info">
        <h3>智能助手</h3>
        <span class="status-indicator">
          <span class="pulse-dot"></span>
          系统联机
        </span>
      </div>
    </div>
    
    <!-- 消息区域 -->
    <div ref="chatContainer" class="chat-messages">
      <div 
        v-for="msg in messages" 
        :key="msg.id"
        class="message"
        :class="msg.sender"
      >
        <div class="message-content">
          {{ msg.content }}
        </div>
        <span class="message-time">{{ msg.time }}</span>
      </div>
      
      <!-- 加载中 -->
      <div v-if="isLoading" class="message ai">
        <div class="message-content loading">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    </div>
    
    <!-- 输入框 -->
    <div class="chat-input">
      <input 
        v-model="inputMessage"
        type="text" 
        placeholder="请输入您的问题..."
        :disabled="isLoading"
        @keyup.enter="sendMessage"
      />
      <button :disabled="isLoading || !inputMessage.trim()" @click="sendMessage">
        发送
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-assistant {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(12, 16, 34, 0.95);
  color: #f8fafc;
}

.chat-header {
  padding: 12px 16px;
  background: rgba(22, 32, 60, 0.8);
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.header-icon svg {
  width: 16px;
  height: 16px;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.header-info h3 {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
  margin: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: #64748b;
}

.pulse-dot {
  width: 5px;
  height: 5px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.8);
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.8);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.9);
    box-shadow: 0 0 2px rgba(16, 185, 129, 0.3);
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-messages::-webkit-scrollbar {
  width: 3px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(37, 99, 235, 0.15);
  border-radius: 2px;
}

.message {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  align-items: flex-end;
}

.message.ai {
  align-self: flex-start;
  align-items: flex-start;
}

.message-content {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
}

.message.user .message-content {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.message.ai .message-content {
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.03);
  color: #e2e8f0;
}

.message-time {
  font-size: 9px;
  color: #475569;
  font-family: 'JetBrains Mono', monospace;
}

.chat-input {
  padding: 10px 14px;
  background: rgba(22, 32, 60, 0.8);
  border-top: 1px solid rgba(37, 99, 235, 0.1);
  display: flex;
  gap: 8px;
}

.chat-input input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  background: rgba(12, 16, 34, 0.8);
  color: #f8fafc;
  font-size: 13px;
  outline: none;
  transition: all 0.2s ease;
}

.chat-input input:focus {
  border-color: #2563eb;
  background: rgba(12, 16, 34, 0.95);
  box-shadow: 0 0 8px rgba(37, 99, 235, 0.1);
}

.chat-input input::placeholder {
  color: #475569;
}

.chat-input button {
  padding: 8px 16px;
  background: #2563eb;
  border: none;
  border-radius: 6px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chat-input button:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 2px 10px rgba(37, 99, 235, 0.25);
}

.chat-input button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Loading Dots */
.message-content.loading {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  align-items: center;
}

.message-content.loading .dot {
  width: 5px;
  height: 5px;
  background: #64748b;
  border-radius: 50%;
  animation: loading-dot 1.4s infinite ease-in-out both;
}

.message-content.loading .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.message-content.loading .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes loading-dot {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>
