<template>
  <div class="agent-thinking">
    <div class="header" @click="collapsed = !collapsed">
      <span>Agent Thinking</span>
      <span class="toggle">{{ collapsed ? '▸' : '▾' }}</span>
    </div>
    <div v-if="!collapsed" class="thoughts">
      <div
        v-for="(t, i) in runStore.agentThoughts"
        :key="i"
        class="thought"
        :class="t.type"
      >
        <div class="type">{{ t.type }}</div>
        <div v-if="t.tool" class="detail">tool: {{ t.tool }}</div>
        <div v-if="t.input" class="detail">input: {{ JSON.stringify(t.input) }}</div>
        <div v-if="t.output" class="detail">output: {{ t.output }}</div>
        <div v-if="t.log" class="detail">log: {{ t.log }}</div>
      </div>
      <div v-if="runStore.agentThoughts.length === 0" class="empty">No thoughts yet</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRunStore } from '../stores/run'
const runStore = useRunStore()
const collapsed = ref(true)
</script>

<style scoped>
.agent-thinking {
  width: 280px;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header {
  padding: 8px 12px;
  font-weight: 700;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  cursor: pointer;
}
.toggle {
  color: #64748b;
}
.thoughts {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}
.thought {
  padding: 8px;
  border-radius: 6px;
  background: #f8fafc;
  margin-bottom: 6px;
  font-size: 12px;
}
.thought .type {
  font-weight: 700;
  text-transform: uppercase;
  font-size: 10px;
  color: #64748b;
  margin-bottom: 4px;
}
.thought .detail {
  color: #334155;
  word-break: break-word;
}
.empty {
  color: #94a3b8;
  padding: 12px 0;
}
</style>
