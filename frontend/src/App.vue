<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="app-title">Kitchen SOP</h1>
      </div>
      <SkillList />
      <button class="fab" @click="showGenerator = true" title="生成 Skill">
        <span class="fab-icon">+</span>
      </button>
    </aside>
    <main class="main-content">
      <ExecutionPanel />
      <div class="panels">
        <SkillDetail />
        <GraphViewer />
      </div>
      <div class="bottom-panels">
        <LogViewer />
        <RunReplay />
        <AgentThinking />
      </div>
      <HitlModal v-if="runStore.hitlPending" />
    </main>
    <aside class="right-panel">
      <RunHistory />
    </aside>
    <SkillGenerator
      v-if="showGenerator"
      @close="showGenerator = false"
      @saved="onSkillSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAppStore } from './stores/app'
import { useRunStore } from './stores/run'
import SkillList from './components/SkillList.vue'
import ExecutionPanel from './components/ExecutionPanel.vue'
import SkillDetail from './components/SkillDetail.vue'
import GraphViewer from './components/GraphViewer.vue'
import LogViewer from './components/LogViewer.vue'
import HitlModal from './components/HitlModal.vue'
import RunHistory from './components/RunHistory.vue'
import AgentThinking from './components/AgentThinking.vue'
import SkillGenerator from './components/SkillGenerator.vue'
import RunReplay from './components/RunReplay.vue'

const appStore = useAppStore()
const runStore = useRunStore()
const showGenerator = ref(false)

function onSkillSaved() {
  showGenerator.value = false
  appStore.loadSkills()
}

onMounted(() => {
  appStore.loadSkills()
  appStore.loadTools()
})
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f8fafc;
  color: #1e293b;
}

.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}

.app-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.3px;
}

.fab {
  position: sticky;
  bottom: 16px;
  align-self: flex-end;
  margin: 0 16px 16px 0;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
  transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
  flex-shrink: 0;
}

.fab:hover {
  background: #1d4ed8;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
}

.fab:active {
  transform: translateY(2px) scale(0.96);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
}

.fab-icon {
  font-size: 28px;
  font-weight: 300;
  line-height: 1;
}

.generate-btn {
  width: 100%;
  padding: 10px 12px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.15s, transform 0.05s;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
}

.generate-btn:hover {
  background: #1d4ed8;
}

.generate-btn:active {
  transform: translateY(1px);
}

.plus {
  font-size: 18px;
  line-height: 1;
}

.sidebar :deep(.skill-list) {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  background: #f1f5f9;
}

.panels {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  gap: 12px;
  padding: 12px;
}

.panels > * {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.bottom-panels {
  height: 240px;
  display: flex;
  border-top: 1px solid #e2e8f0;
  background: #fff;
  flex-shrink: 0;
  overflow: hidden;
}

.bottom-panels > * {
  flex: 1;
  min-width: 0;
  border-right: 1px solid #e2e8f0;
}

.bottom-panels > *:last-child {
  border-right: none;
}

.right-panel {
  width: 300px;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
</style>
