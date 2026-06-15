import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { APISkillMeta, Skill, ToolInfo, SkillValidationResult, SkillPreviewResponse } from '../types'
import { fetchSkills, fetchSkill, fetchTools, validateSkill, generateSkillDraft, previewSkillDraft, saveSkillDraft } from '../composables/useApi'

export const useAppStore = defineStore('app', () => {
  const skills = ref<APISkillMeta[]>([])
  const selectedSkillName = ref<string | null>(null)
  const selectedSkillDetail = ref<Skill | null>(null)
  const loadingSkill = ref(false)
  const tools = ref<ToolInfo[]>([])
  const loadingTools = ref(false)
  const validation = ref<SkillValidationResult | null>(null)
  const validating = ref(false)

  // Generator state
  const generatorPhase = ref<'prompt' | 'preview' | 'success'>('prompt')
  const draftMarkdown = ref('')
  const previewResult = ref<SkillPreviewResponse | null>(null)
  const generating = ref(false)
  const saving = ref(false)
  const generatorError = ref<string | null>(null)

  const selectedSkill = computed(() => {
    return skills.value.find(s => s.name === selectedSkillName.value) || null
  })

  const invalidStepIndices = computed(() => {
    const indices = new Set<number>()
    if (validation.value?.step_errors) {
      for (const err of validation.value.step_errors) {
        if (err.step_index != null) {
          indices.add(err.step_index)
        }
      }
    }
    return indices
  })

  async function loadSkills() {
    skills.value = await fetchSkills()
  }

  async function loadTools() {
    loadingTools.value = true
    try {
      tools.value = await fetchTools()
    } finally {
      loadingTools.value = false
    }
  }

  async function selectSkill(name: string) {
    selectedSkillName.value = name
    loadingSkill.value = true
    validation.value = null
    try {
      selectedSkillDetail.value = await fetchSkill(name)
      await runValidation(name)
    } finally {
      loadingSkill.value = false
    }
  }

  async function runValidation(name: string) {
    validating.value = true
    try {
      validation.value = await validateSkill(name)
    } catch (e) {
      validation.value = {
        valid: false,
        errors: [e instanceof Error ? e.message : String(e)],
        step_errors: [],
      }
    } finally {
      validating.value = false
    }
  }

  // Generator actions
  async function generateDraft(prompt: string, model?: string) {
    generatorError.value = null
    generating.value = true
    try {
      const res = await generateSkillDraft({ prompt, model })
      draftMarkdown.value = res.draft_markdown
      generatorPhase.value = 'preview'
      await previewDraft()
    } catch (e) {
      generatorError.value = e instanceof Error ? e.message : String(e)
    } finally {
      generating.value = false
    }
  }

  async function previewDraft() {
    generatorError.value = null
    try {
      previewResult.value = await previewSkillDraft({ draft_markdown: draftMarkdown.value })
    } catch (e) {
      generatorError.value = e instanceof Error ? e.message : String(e)
      previewResult.value = null
    }
  }

  async function saveDraft(name: string, overwrite?: boolean) {
    generatorError.value = null
    saving.value = true
    try {
      await saveSkillDraft({ name, draft_markdown: draftMarkdown.value, overwrite })
      generatorPhase.value = 'success'
      await loadSkills()
    } catch (e) {
      generatorError.value = e instanceof Error ? e.message : String(e)
    } finally {
      saving.value = false
    }
  }

  function resetGenerator() {
    generatorPhase.value = 'prompt'
    draftMarkdown.value = ''
    previewResult.value = null
    generatorError.value = null
    generating.value = false
    saving.value = false
  }

  return {
    skills,
    selectedSkillName,
    selectedSkillDetail,
    selectedSkill,
    loadingSkill,
    tools,
    loadingTools,
    validation,
    validating,
    invalidStepIndices,
    loadSkills,
    loadTools,
    selectSkill,
    runValidation,
    // generator
    generatorPhase,
    draftMarkdown,
    previewResult,
    generating,
    saving,
    generatorError,
    generateDraft,
    previewDraft,
    saveDraft,
    resetGenerator,
  }
})
