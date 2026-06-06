<template>
  <div class="run-replay" v-if="runStore.activeRun">
    <div class="header">
      Replay: {{ runStore.activeRun.run_id }}
      <button @click="replay">Replay</button>
    </div>
    <div class="steps">
      <div
        v-for="step in runStore.activeRun.steps"
        :key="step.step_index"
        class="step"
        :class="step.status"
      >
        <span class="idx">{{ step.step_index }}</span>
        <span class="tool">{{ step.tool_name }}</span>
        <span class="status">{{ step.status }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRunStore } from '../stores/run'
const runStore = useRunStore()

function replay() {
  // Placeholder: could animate through steps with timeouts
  alert('Replay animation not yet implemented')
}
</script>

<style scoped>
.run-replay {
  padding: 12px;
}
.header {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header button {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #fff;
  cursor: pointer;
}
.step {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 4px;
}
.step.success {
  background: #dcfce7;
}
.step.error {
  background: #fee2e2;
}
.idx {
  width: 20px;
  color: #64748b;
}
.tool {
  flex: 1;
}
.status {
  font-size: 11px;
  text-transform: uppercase;
  color: #475569;
}
</style>
