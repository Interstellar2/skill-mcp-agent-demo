<template>
  <div class="run-replay" v-if="runStore.activeRun">
    <div class="header">
      <div class="title">
        <div class="run-id">Run {{ runStore.activeRun.run_id }}</div>
        <div class="run-sub">{{ runStore.activeRun.skill_name }} · {{ runStore.activeRun.mode }}</div>
      </div>
      <span class="run-status" :class="runStore.activeRun.overall_status">{{ runStore.activeRun.overall_status }}</span>
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
        <span class="status-badge" :class="step.status">{{ step.status }}</span>
      </div>
    </div>
  </div>
  <div v-else class="run-replay empty">
    <div class="empty-text">Select a run from history to view replay</div>
  </div>
</template>

<script setup lang="ts">
import { useRunStore } from '../stores/run'
const runStore = useRunStore()
</script>

<style scoped>
.run-replay {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.run-replay.empty {
  align-items: center;
  justify-content: center;
}
.header {
  padding: 10px 12px;
  font-weight: 700;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.run-id {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #0f172a;
}
.run-sub {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}
.run-status {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
}
.run-status.success {
  background: #dcfce7;
  color: #166534;
}
.run-status.error {
  background: #fee2e2;
  color: #991b1b;
}
.run-status.pending {
  background: #fef3c7;
  color: #92400e;
}
.steps {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.step {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 4px;
  background: #f8fafc;
}
.step.success {
  background: #f0fdf4;
}
.step.error {
  background: #fef2f2;
}
.idx {
  width: 20px;
  color: #64748b;
  font-weight: 600;
  font-family: ui-monospace, monospace;
}
.tool {
  flex: 1;
  color: #0f172a;
  font-weight: 500;
}
.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
}
.status-badge.success {
  background: #dcfce7;
  color: #166534;
}
.status-badge.error {
  background: #fee2e2;
  color: #991b1b;
}
.empty-text {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}
</style>
