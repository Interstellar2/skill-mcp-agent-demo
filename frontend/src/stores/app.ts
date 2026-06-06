import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { APISkillMeta, Skill, ToolInfo, SkillValidationResult } from '../types'
import { fetchSkills, fetchSkill, fetchTools, validateSkill } from '../composables/useApi'

export const useAppStore = defineStore('app', () => {
  const skills = ref<APISkillMeta[]>([])
  const selectedSkillName = ref<string | null>(null)
  const selectedSkillDetail = ref<Skill | null>(null)
  const loadingSkill = ref(false)
  const tools = ref<ToolInfo[]>([])
  const loadingTools = ref(false)
  const validation = ref<SkillValidationResult | null>(null)
  const validating = ref(false)

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
  }
})
