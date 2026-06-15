<template>
  <div class="skill-list">
    <div class="section-title">Skills</div>
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
  padding: 12px;
}
.section-title {
  margin: 0 0 10px 4px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #94a3b8;
}
.skill-item {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
  border: 1px solid transparent;
  background: #fff;
}
.skill-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.skill-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
}
.skill-name {
  font-weight: 700;
  font-size: 14px;
  color: #0f172a;
}
.skill-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.skill-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 8px;
  font-weight: 600;
}
</style>
