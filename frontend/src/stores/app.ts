import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { APISkillMeta, Skill } from '../types'
import { fetchSkills, fetchSkill } from '../composables/useApi'

export const useAppStore = defineStore('app', () => {
  const skills = ref<APISkillMeta[]>([])
  const selectedSkillName = ref<string | null>(null)
  const selectedSkillDetail = ref<Skill | null>(null)
  const loadingSkill = ref(false)

  const selectedSkill = computed(() => {
    return skills.value.find(s => s.name === selectedSkillName.value) || null
  })

  async function loadSkills() {
    skills.value = await fetchSkills()
  }

  async function selectSkill(name: string) {
    selectedSkillName.value = name
    loadingSkill.value = true
    try {
      selectedSkillDetail.value = await fetchSkill(name)
    } finally {
      loadingSkill.value = false
    }
  }

  return {
    skills,
    selectedSkillName,
    selectedSkillDetail,
    selectedSkill,
    loadingSkill,
    loadSkills,
    selectSkill,
  }
})
