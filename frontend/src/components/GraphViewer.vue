<template>
  <div class="graph-viewer">
    <div class="toolbar">
      <button
        v-for="l in layouts"
        :key="l"
        :class="{ active: layout === l }"
        @click="setLayout(l)"
      >
        {{ l }}
      </button>
    </div>
    <div ref="container" class="cy-container" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useAppStore } from '../stores/app'
import { useRunStore } from '../stores/run'
import { useCytoscape } from '../composables/useCytoscape'
import { createGraph, buildElements } from '../graph/render'
import { buildDagElements } from '../graph/dag-layout'

const appStore = useAppStore()
const runStore = useRunStore()
const container = ref<HTMLElement | null>(null)
const layout = ref('breadthfirst')
const layouts = ['breadthfirst', 'dagre', 'grid', 'circle']

const { mount, highlightNode, highlightBatch, clearBatchHighlights } = useCytoscape()

function buildElementsForSkill() {
  if (!appStore.selectedSkillDetail) return []
  return layout.value === 'dagre'
    ? buildDagElements(appStore.selectedSkillDetail)
    : buildElements(appStore.selectedSkillDetail)
}

function rebuild() {
  if (!container.value || !appStore.selectedSkillDetail) return
  const elements = buildElementsForSkill()
  const layoutName = layout.value === 'dagre' ? 'breadthfirst' : layout.value
  mount(
    (c) => createGraph(c, elements, layoutName),
    container.value
  )
  Object.entries(runStore.stepStatusMap).forEach(([idx, status]) => {
    highlightNode(Number(idx), status)
  })
}

function setLayout(l: string) {
  layout.value = l
  rebuild()
}

watch(() => appStore.selectedSkillDetail, () => {
  nextTick(rebuild)
})

watch(() => runStore.stepStatusMap, (map) => {
  Object.entries(map).forEach(([idx, status]) => {
    highlightNode(Number(idx), status)
  })
}, { deep: true })

watch(() => runStore.activeBatchIndex, (batchIdx) => {
  clearBatchHighlights()
  if (batchIdx != null) {
    const batch = runStore.parallelBatches.find((b) => b.batch_index === batchIdx)
    if (batch) {
      highlightBatch(batch.step_indices, true)
    }
  }
})
</script>

<style scoped>
.graph-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
.toolbar {
  padding: 8px 12px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
}
.toolbar button {
  padding: 4px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}
.toolbar button.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}
.cy-container {
  flex: 1;
}
</style>
