<template>
  <div class="app-layout">
    <aside class="sidebar">
      <SkillList />
    </aside>
    <main class="main-content">
      <ExecutionPanel />
      <div class="panels">
        <SkillDetail />
        <GraphViewer />
      </div>
      <div class="bottom-panels">
        <LogViewer />
        <AgentThinking />
      </div>
      <HitlModal v-if="runStore.hitlPending" />
    </main>
    <aside class="right-panel">
      <RunHistory />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
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

const appStore = useAppStore()
const runStore = useRunStore()

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
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.panels {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.bottom-panels {
  height: 220px;
  display: flex;
  border-top: 1px solid #e2e8f0;
  background: #fff;
  flex-shrink: 0;
}

.right-panel {
  width: 280px;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  overflow-y: auto;
  flex-shrink: 0;
}
</style>
