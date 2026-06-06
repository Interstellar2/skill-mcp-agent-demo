<template>
  <div class="modal-overlay" @click.self="reject">
    <div class="modal">
      <h3>Human-in-the-Loop Approval</h3>
      <p class="prompt">{{ runStore.hitlPending?.prompt }}</p>
      <div class="args">
        <div v-for="(v, k) in runStore.hitlPending?.arguments" :key="k">
          <strong>{{ k }}:</strong> {{ v }}
        </div>
      </div>
      <div class="actions">
        <button class="approve" @click="approve">Approve</button>
        <button class="reject" @click="reject">Reject</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRunStore } from '../stores/run'
import { useExecution } from '../composables/useExecution'

const runStore = useRunStore()
const exec = useExecution()

function approve() {
  exec.approveHITL('approved')
}

function reject() {
  exec.approveHITL('rejected')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}
.modal h3 {
  margin: 0 0 12px;
  font-size: 18px;
}
.prompt {
  font-size: 14px;
  color: #334155;
  margin: 0 0 12px;
  line-height: 1.5;
}
.args {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}
.actions {
  display: flex;
  gap: 10px;
}
.actions button {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  border: none;
  font-weight: 700;
  cursor: pointer;
}
.approve {
  background: #22c55e;
  color: #fff;
}
.reject {
  background: #ef4444;
  color: #fff;
}
</style>
