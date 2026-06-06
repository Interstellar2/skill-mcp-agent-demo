<template>
  <div class="execution-panel">
    <div class="row">
      <label>Mode</label>
      <select v-model="selectedMode">
        <option value="demo">Demo</option>
        <option value="agent">Agent</option>
        <option value="plan_then_execute">Plan-then-Execute</option>
        <option value="hitl">HITL</option>
        <option value="parallel">Parallel</option>
        <option value="resumable">Resumable</option>
      </select>
    </div>
    <div v-if="selectedMode === 'agent' || selectedMode === 'plan_then_execute'" class="row">
      <label>Model</label>
      <input v-model="model" type="text" />
    </div>
    <VariableForm v-if="appStore.selectedSkill?.variables" :definitions="appStore.selectedSkill.variables" v-model="variables" />
    <div class="row actions">
      <button
        class="run-btn"
        :disabled="!appStore.selectedSkillName || runStore.executionStatus === 'running'"
        @click="exec.launchRun"
      >
        {{ runStore.executionStatus === 'running' ? 'Running...' : 'Run' }}
      </button>
      <span v-if="exec.wsConnected" class="ws-badge connected">WS</span>
      <span v-else class="ws-badge">WS</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { toRefs } from 'vue'
import { useAppStore } from '../stores/app'
import { useRunStore } from '../stores/run'
import { useExecution } from '../composables/useExecution'
import VariableForm from './VariableForm.vue'

const appStore = useAppStore()
const runStore = useRunStore()
const exec = useExecution()
const { selectedMode, variables, model } = toRefs(exec)
</script>

<style scoped>
.execution-panel {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.row label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}
select, input {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 13px;
}
.run-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}
.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ws-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #e2e8f0;
  color: #64748b;
}
.ws-badge.connected {
  background: #dcfce7;
  color: #166534;
}
</style>
