<template>
  <div class="skill-detail">
    <div v-if="appStore.loadingSkill" class="loading">Loading...</div>
    <div v-else-if="appStore.selectedSkillDetail" class="markdown-body" v-html="renderedMarkdown"></div>
    <div v-else class="empty">Select a skill to view SOP</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()

const renderedMarkdown = computed(() => {
  const raw = appStore.selectedSkillDetail?.raw ?? ''
  // Strip frontmatter
  const body = raw.replace(/^---[\s\S]*?---\n?/, '')
  return marked.parse(body, { async: false }) as string
})
</script>

<style scoped>
.skill-detail {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
}
.loading, .empty {
  color: #64748b;
  padding: 40px;
  text-align: center;
}
</style>

<style>
.markdown-body h1 { font-size: 22px; margin: 0 0 12px; }
.markdown-body h2 { font-size: 18px; margin: 16px 0 8px; }
.markdown-body h3 { font-size: 15px; margin: 12px 0 6px; }
.markdown-body p { margin: 8px 0; line-height: 1.6; }
.markdown-body code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.markdown-body pre {
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
.markdown-body ul { padding-left: 20px; }
.markdown-body li { margin: 4px 0; }
</style>
