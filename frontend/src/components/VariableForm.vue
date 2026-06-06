<template>
  <div class="variable-form">
    <div v-for="(def, key) in definitions" :key="key" class="field">
      <label>{{ key }}</label>
      <input
        v-if="typeof def === 'number' || typeof def === 'string'"
        v-model="local[key]"
        :type="typeof def === 'number' ? 'number' : 'text'"
      />
      <select v-else-if="typeof def === 'boolean'" v-model="local[key]">
        <option :value="true">true</option>
        <option :value="false">false</option>
      </select>
      <input v-else v-model="local[key]" type="text" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  definitions: Record<string, unknown>
  modelValue: Record<string, unknown>
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', val: Record<string, unknown>): void
}>()

const local = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})
</script>

<style scoped>
.variable-form {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.field label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}
input, select {
  padding: 5px 8px;
  border-radius: 5px;
  border: 1px solid #cbd5e1;
  font-size: 12px;
}
</style>
