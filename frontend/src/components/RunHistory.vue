<template>
  <div class="run-history">
    <div class="header">
      <span>Run History</span>
      <button class="refresh-btn" :disabled="loading" @click="loadRuns" title="刷新">
        <span :class="{ spin: loading }">↻</span>
      </button>
    </div>
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
        <div class="run-time">{{ formatTime(run.started_at) }}</div>
      </div>
      <div v-if="runs.length === 0 && !loading" class="empty">No runs yet</div>
      <div v-if="error" class="error">{{ error }}</div>
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
const loading = ref(false)
const error = ref<string | null>(null)

async function loadRuns() {
  loading.value = true
  error.value = null
  try {
    runs.value = await fetchRuns()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function selectRun(runId: string) {
  error.value = null
  try {
    const run = await fetchRun(runId)
    runStore.setActiveRun(run)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
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
  font-size: 15px;
  font-weight: 700;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 4px;
}
.refresh-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #334155;
}
.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.run-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  background: #fff;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}
.run-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.run-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
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
  font-weight: 600;
}
.run-status {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  text-transform: uppercase;
  font-weight: 700;
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
.run-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
}
.run-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.empty {
  color: #94a3b8;
  padding: 32px 0;
  text-align: center;
  font-size: 13px;
}
.error {
  color: #991b1b;
  background: #fee2e2;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  margin-top: 8px;
}
</style>
