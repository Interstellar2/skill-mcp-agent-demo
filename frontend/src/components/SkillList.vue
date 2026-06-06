<template>
  <div class="skill-list">
    <h2 class="title">Skills</h2>
    <div
      v-for="skill in appStore.skills"
      :key="skill.name"
      class="skill-item"
      :class="{ active: appStore.selectedSkillName === skill.name }"
      @click="appStore.selectSkill(skill.name)"
    >
      <div class="skill-name">{{ skill.name }}</div>
      <div class="skill-desc">{{ skill.description }}</div>
      <div class="skill-meta">{{ skill.steps_count }} steps</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '../stores/app'
const appStore = useAppStore()
</script>

<style scoped>
.skill-list {
  padding: 16px;
}
.title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 700;
}
.skill-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s;
  border: 1px solid transparent;
}
.skill-item:hover {
  background: #f1f5f9;
}
.skill-item.active {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.skill-name {
  font-weight: 600;
  font-size: 14px;
}
.skill-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
.skill-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}
</style>
