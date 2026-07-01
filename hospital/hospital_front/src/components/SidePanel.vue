<script setup>
import { ref } from 'vue'

defineProps({
  title: String,
  icon: String,
  position: {
    type: String,
    default: 'left'
  }
})

const isOpen = ref(false)

const togglePanel = () => {
  isOpen.value = !isOpen.value
}
</script>

<template>
  <div 
    class="side-panel-container"
    :class="{ 'is-open': isOpen }"
    :style="{ [position]: '0' }"
  >
    <button class="toggle-btn" @click="togglePanel">
      <span class="icon">{{ icon }}</span>
      <span class="label">{{ title }}</span>
    </button>
    <div class="panel-content">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.side-panel-container {
  position: fixed;
  top: 80px;
  bottom: 20px;
  width: 320px;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 0 12px 12px 0;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3);
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.side-panel-container.is-open {
  transform: translateX(0);
}

.side-panel-container[style*="right"] {
  border-radius: 12px 0 0 12px;
  transform: translateX(100%);
}

.side-panel-container[style*="right"].is-open {
  transform: translateX(0);
}

.toggle-btn {
  position: absolute;
  right: -40px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 80px;
  background: linear-gradient(180deg, #1e3a5f 0%, #0f172a 100%);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-left: none;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: all 0.3s ease;
  color: #94a3b8;
}

.side-panel-container[style*="right"] .toggle-btn {
  right: auto;
  left: -40px;
  border-left: 1px solid rgba(51, 65, 85, 0.5);
  border-right: none;
  border-radius: 8px 0 0 8px;
}

.toggle-btn:hover {
  background: linear-gradient(180deg, #2d4a6f 0%, #1e293b 100%);
  color: #e2e8f0;
}

.toggle-btn .icon {
  font-size: 18px;
}

.toggle-btn .label {
  font-size: 10px;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  letter-spacing: 1px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: rgba(51, 65, 85, 0.3);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 3px;
}
</style>
