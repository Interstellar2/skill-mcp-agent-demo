<template>
  <div class="run-history">
    <h3 class="header">Run History</h3>
    <div class="list">
      <div
        v-for="run in runs"
        :key="run.run_id"
        class="run-item"
        :class="{ active: runStore.activeRun?.run_id === run.run_id }"
        @click="selectRun(run.run_id)"
      >
        <div class="run-top">
          <span class="run-id">{{ run.run_id }}</span>
          <span class="run-status" :class="run.overall_status">{{ run.overall_status }}</span>
        </div>
        <div class="run-meta">
          {{ run.skill_name }} · {{ run.mode }}
        </div>
        <div class="run-time">{{ run.started_at }}</div>
      </div>
      <div v-if="runs.length === 0" class="empty">No runs yet</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRunStore } from '../stores/run'
import { fetchRuns, fetchRun } from '../composables/useApi'
import type { APIRun } from '../types'

const runStore = useRunStore()
const runs = ref<APIRun[]>([])

async function loadRuns() {
  runs.value = await fetchRuns()
}

async function selectRun(runId: string) {
  const run = await fetchRun(runId)
  runStore.setActiveRun(run)
}

onMounted(() => {
  loadRuns()
})
</script>

<style scoped>
.run-history {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.header {
  margin: 0;
  padding: 12px 16px;
  font-size: 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.run-item {
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
}
.run-item:hover {
  background: #f1f5f9;
}
.run-item.active {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.run-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.run-id {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #334155;
}
.run-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e2e8f0;
  color: #475569;
  text-transform: uppercase;
}
.run-status.success {
  background: #dcfce7;
  color: #166534;
}
.run-status.error {
  background: #fee2e2;
  color: #991b1b;
}
.run-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
.run-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}
.empty {
  color: #94a3b8;
  padding: 20px;
  text-align: center;
}
</style>
