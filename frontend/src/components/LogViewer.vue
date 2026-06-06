<template>
  <div class="log-viewer">
    <div class="header">Execution Log</div>
    <div class="logs">
      <div
        v-for="(entry, i) in runStore.logEntries"
        :key="i"
        class="log-line"
        :class="entry.level"
      >
        <span v-if="entry.stepIndex > 0" class="step-label">[{{ entry.stepIndex }}]</span>
        {{ entry.message }}
      </div>
      <div v-if="runStore.logEntries.length === 0" class="empty">No logs yet</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRunStore } from '../stores/run'
const runStore = useRunStore()
</script>

<style scoped>
.log-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e2e8f0;
  overflow: hidden;
}
.header {
  padding: 8px 12px;
  font-weight: 700;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.logs {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.log-line {
  margin: 3px 0;
  color: #334155;
}
.log-line.success {
  color: #166534;
}
.log-line.error {
  color: #991b1b;
}
.step-label {
  color: #64748b;
  margin-right: 6px;
}
.empty {
  color: #94a3b8;
  padding: 20px 0;
}
</style>
