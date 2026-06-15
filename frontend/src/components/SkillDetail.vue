<template>
  <div class="skill-detail">
    <div v-if="appStore.loadingSkill" class="loading">Loading...</div>
    <template v-else-if="appStore.selectedSkillDetail">
      <div v-if="appStore.validation" class="validation-panel">
        <div v-if="appStore.validating" class="validation-loading">
          Validating...
        </div>
        <div v-else-if="appStore.validation.valid" class="validation-success">
          Skill validation passed
        </div>
        <div v-else class="validation-errors">
          <div class="validation-header">
            <span class="validation-icon">⚠️</span>
            Skill validation failed
            <span class="validation-count">({{ totalErrors }})</span>
          </div>
          <ul>
            <li v-for="(err, i) in appStore.validation.errors" :key="'e-' + i">{{ err }}</li>
            <li v-for="(err, i) in appStore.validation.step_errors" :key="'s-' + i">
              Step {{ err.step_index }}: {{ err.message }}
            </li>
          </ul>
        </div>
      </div>
      <div class="markdown-body" v-html="renderedMarkdown"></div>
    </template>
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

const totalErrors = computed(() => {
  const v = appStore.validation
  if (!v) return 0
  return v.errors.length + v.step_errors.length
})
</script>

<style scoped>
.skill-detail {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
}
.loading, .empty {
  color: #64748b;
  padding: 40px;
  text-align: center;
}

.validation-panel {
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
}

.validation-loading {
  padding: 10px 14px;
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
}

.validation-success {
  padding: 10px 14px;
  background: #dcfce7;
  color: #166534;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
}

.validation-errors {
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 12px 14px;
}

.validation-header {
  font-weight: 700;
  color: #92400e;
  font-size: 14px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.validation-icon {
  font-size: 16px;
}

.validation-count {
  font-weight: 500;
  font-size: 12px;
  color: #b45309;
  margin-left: 4px;
}

.validation-errors ul {
  margin: 0;
  padding-left: 18px;
  color: #78350f;
  font-size: 13px;
  line-height: 1.7;
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
