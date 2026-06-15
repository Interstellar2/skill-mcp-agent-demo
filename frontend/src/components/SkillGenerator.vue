<template>
  <div class="generator-modal-backdrop" @click.self="emit('close')">
    <div class="generator-modal">
      <header class="generator-header">
        <h2>生成 Skill</h2>
        <button class="close-btn" @click="emit('close')">×</button>
      </header>

      <div class="generator-body">
        <!-- Prompt Phase -->
        <div v-if="appStore.generatorPhase === 'prompt'" class="phase">
          <label for="skill-prompt">描述你想生成的 SOP（菜名、流程、关键步骤等）</label>
          <textarea
            id="skill-prompt"
            v-model="prompt"
            rows="6"
            placeholder="例如：生成一份青椒炒肉 SOP，包含切肉、腌制、炒制、调味、装盘等步骤"
            :disabled="appStore.generating"
          />
          <div class="actions">
            <input
              v-model="model"
              class="model-input"
              placeholder="模型（可选）"
              :disabled="appStore.generating"
            />
            <button
              class="primary"
              :disabled="!prompt.trim() || appStore.generating"
              @click="onGenerate"
            >
              {{ appStore.generating ? '生成中...' : '生成草稿' }}
            </button>
          </div>
        </div>

        <!-- Preview Phase -->
        <div v-else-if="appStore.generatorPhase === 'preview'" class="phase preview-phase">
          <div class="editor-pane">
            <label>SKILL.md 草稿（可编辑）</label>
            <textarea
              v-model="appStore.draftMarkdown"
              rows="16"
              spellcheck="false"
            />
            <div class="editor-actions">
              <button class="secondary" @click="onReparse">重新解析</button>
              <button class="secondary" @click="onRegenerate">重新生成</button>
            </div>
          </div>

          <div class="preview-pane">
            <label>预览</label>
            <div class="preview-content">
              <div v-if="appStore.previewResult" class="preview-result">
                <div class="section">
                  <h4>元数据</h4>
                  <pre class="code-block">{{ JSON.stringify(appStore.previewResult.metadata, null, 2) }}</pre>
                </div>

                <div class="section">
                  <h4>步骤 ({{ appStore.previewResult.steps.length }})</h4>
                  <ul class="step-list">
                    <li
                      v-for="(step, idx) in appStore.previewResult.steps"
                      :key="idx"
                      :class="{ invalid: isStepInvalid(idx + 1) }"
                    >
                      <strong>{{ step.tool_name }}</strong>
                      <span class="args">{{ formatArgs(step.arguments) }}</span>
                      <span v-if="step.parallel_group_id" class="badge">group: {{ step.parallel_group_id }}</span>
                      <span v-if="step.depends_on?.length" class="badge">depends: {{ step.depends_on.join(', ') }}</span>
                    </li>
                  </ul>
                </div>

                <div v-if="appStore.previewResult.errors.length" class="section errors">
                  <h4>错误</h4>
                  <ul>
                    <li v-for="(err, idx) in appStore.previewResult.errors" :key="`err-${idx}`">{{ err }}</li>
                  </ul>
                </div>

                <div v-if="appStore.previewResult.step_errors.length" class="section errors">
                  <h4>步骤错误</h4>
                  <ul>
                    <li v-for="(err, idx) in appStore.previewResult.step_errors" :key="`se-${idx}`">
                      步骤 {{ err.step_index }}: {{ err.message }}
                    </li>
                  </ul>
                </div>

                <div class="section valid-row">
                  <span class="valid-badge" :class="appStore.previewResult.valid ? 'ok' : 'bad'">
                    {{ appStore.previewResult.valid ? '校验通过' : '校验未通过' }}
                  </span>
                </div>
              </div>
              <div v-else class="empty">点击“重新解析”查看结果</div>
            </div>
          </div>

          <div class="save-bar">
            <input
              v-model="saveName"
              class="name-input"
              placeholder="skill 名称（如 green_pepper_pork）"
              :disabled="appStore.saving"
            />
            <button
              class="primary"
              :disabled="!canSave"
              @click="onSave"
            >
              {{ appStore.saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>

        <!-- Success Phase -->
        <div v-else-if="appStore.generatorPhase === 'success'" class="phase success-phase">
          <p class="success-msg">Skill 保存成功！</p>
          <p class="hint">左侧列表已刷新，可在列表中查看并运行验证。</p>
          <button class="primary" @click="onClose">完成</button>
        </div>

        <div v-if="appStore.generatorError" class="error-banner">
          {{ appStore.generatorError }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAppStore } from '../stores/app'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const appStore = useAppStore()

const prompt = ref('')
const model = ref('')
const saveName = ref('')

const canSave = computed(() => {
  return (
    saveName.value.trim() !== '' &&
    /^[a-zA-Z0-9_-]+$/.test(saveName.value.trim()) &&
    !appStore.saving &&
    appStore.previewResult?.valid === true
  )
})

function isStepInvalid(stepIndex: number) {
  return appStore.previewResult?.step_errors.some(e => e.step_index === stepIndex) ?? false
}

function formatArgs(args: Record<string, unknown>) {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ')
}

async function onGenerate() {
  await appStore.generateDraft(prompt.value.trim(), model.value.trim() || undefined)
}

async function onReparse() {
  await appStore.previewDraft()
}

function onRegenerate() {
  appStore.resetGenerator()
}

async function onSave() {
  await appStore.saveDraft(saveName.value.trim())
  if (appStore.generatorPhase === 'success') {
    emit('saved')
  }
}

function onClose() {
  appStore.resetGenerator()
  emit('close')
}

watch(() => appStore.generatorPhase, (phase) => {
  if (phase === 'prompt') {
    saveName.value = ''
  }
})
</script>

<style scoped>
.generator-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.generator-modal {
  background: #fff;
  border-radius: 12px;
  width: 920px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.generator-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.generator-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #64748b;
}

.generator-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.phase {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

label {
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}

textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.model-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

button {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}

button.primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

button.primary:disabled,
button.secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

button.secondary:hover {
  background: #f1f5f9;
}

.preview-phase {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.editor-pane,
.preview-pane {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.editor-pane textarea {
  flex: 1;
  min-height: 280px;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.preview-content {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  background: #f8fafc;
  flex: 1;
  overflow-y: auto;
  min-height: 280px;
  max-height: 420px;
}

.section {
  margin-bottom: 16px;
}

.section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #475569;
}

.code-block {
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  margin: 0;
}

.step-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.step-list li {
  padding: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 13px;
}

.step-list li.invalid {
  border-color: #ef4444;
  background: #fef2f2;
}

.args {
  display: block;
  color: #64748b;
  margin-top: 4px;
  font-size: 12px;
}

.badge {
  display: inline-block;
  background: #e0f2fe;
  color: #0369a1;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  margin-top: 4px;
  margin-right: 4px;
}

.errors {
  color: #b91c1c;
}

.errors ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
}

.valid-row {
  display: flex;
  justify-content: flex-end;
}

.valid-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.valid-badge.ok {
  background: #dcfce7;
  color: #15803d;
}

.valid-badge.bad {
  background: #fee2e2;
  color: #b91c1c;
}

.empty {
  color: #94a3b8;
  text-align: center;
  padding: 40px 0;
}

.save-bar {
  grid-column: 1 / -1;
  display: flex;
  gap: 12px;
  align-items: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
}

.name-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.error-banner {
  grid-column: 1 / -1;
  background: #fee2e2;
  color: #991b1b;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 8px;
}

.success-phase {
  align-items: center;
  text-align: center;
  padding: 40px 0;
}

.success-msg {
  font-size: 20px;
  font-weight: 700;
  color: #15803d;
  margin: 0;
}

.hint {
  color: #64748b;
  margin: 8px 0 20px;
}
</style>
