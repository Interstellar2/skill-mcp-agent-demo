import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { APIRun, AgentThought, ParallelBatch } from '../types'

export type ExecutionStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error'

export const useRunStore = defineStore('run', () => {
  const runs = ref<APIRun[]>([])
  const activeRun = ref<APIRun | null>(null)
  const wsConnected = ref(false)
  const hitlPending = ref<{ approvalId: string; prompt: string; stepIndex: number; arguments: Record<string, unknown> } | null>(null)
  const agentThoughts = ref<AgentThought[]>([])
  const executionStatus = ref<ExecutionStatus>('idle')
  const parallelBatches = ref<ParallelBatch[]>([])
  const activeBatchIndex = ref<number | null>(null)
  const logEntries = ref<{ stepIndex: number; message: string; level: 'info' | 'success' | 'error' }[]>([])
  const stepStatusMap = ref<Record<number, string>>({})

  const currentRunId = computed(() => activeRun.value?.run_id ?? null)

  function setActiveRun(run: APIRun | null) {
    activeRun.value = run
    if (!run) {
      executionStatus.value = 'idle'
      return
    }

    executionStatus.value = run.overall_status === 'pending' ? 'running' : (run.overall_status as ExecutionStatus)

    if (run?.steps) {
      stepStatusMap.value = {}
      run.steps.forEach(s => {
        stepStatusMap.value[s.step_index] = s.status
      })
    }

    // 如果是历史 run（非当前正在执行的），用步骤数据重建日志，让用户能看到回放
    if (run.overall_status !== 'pending') {
      clearLogs()
      addLog(0, `加载历史运行: ${run.run_id} (${run.skill_name} / ${run.mode})`, 'info')
      run.steps?.forEach(s => {
        const level: 'success' | 'error' | 'info' =
          s.status === 'success' ? 'success' : s.status === 'error' ? 'error' : 'info'
        addLog(s.step_index, `步骤 ${s.step_index}: ${s.tool_name} - ${s.status}`, level)
        if (s.result_text) {
          addLog(s.step_index, `  结果: ${s.result_text}`, 'success')
        }
        if (s.error_message) {
          addLog(s.step_index, `  错误: ${s.error_message}`, 'error')
        }
      })
      const finalLevel: 'success' | 'error' = run.overall_status === 'success' ? 'success' : 'error'
      addLog(0, `运行结束: ${run.overall_status}`, finalLevel)
    }
  }

  function addLog(stepIndex: number, message: string, level: 'info' | 'success' | 'error' = 'info') {
    logEntries.value.push({ stepIndex, message, level })
  }

  function clearLogs() {
    logEntries.value = []
    agentThoughts.value = []
    parallelBatches.value = []
    activeBatchIndex.value = null
    stepStatusMap.value = {}
    hitlPending.value = null
  }

  function handleStepStart(payload: { step_index: number; tool_name: string; arguments: Record<string, unknown> }) {
    stepStatusMap.value[payload.step_index] = 'pending'
    addLog(payload.step_index, `开始步骤 ${payload.step_index}: ${payload.tool_name}`, 'info')
  }

  function handleStepFinish(payload: { step_index: number; result_text?: string }) {
    stepStatusMap.value[payload.step_index] = 'success'
    addLog(payload.step_index, `步骤 ${payload.step_index} 完成`, 'success')
  }

  function handleStepError(payload: { step_index: number; error_message: string }) {
    stepStatusMap.value[payload.step_index] = 'error'
    addLog(payload.step_index, `步骤 ${payload.step_index} 错误: ${payload.error_message}`, 'error')
    executionStatus.value = 'error'
  }

  function handleHITLRequest(payload: { approval_id: string; prompt: string; step_index: number; arguments: Record<string, unknown> }) {
    hitlPending.value = {
      approvalId: payload.approval_id,
      prompt: payload.prompt,
      stepIndex: payload.step_index,
      arguments: payload.arguments,
    }
    executionStatus.value = 'paused'
    addLog(payload.step_index, `HITL 请求: ${payload.prompt}`, 'info')
  }

  function resolveHITL() {
    hitlPending.value = null
    executionStatus.value = 'running'
  }

  function handleBatchStart(payload: { batch_index: number; step_indices: number[]; total_batches: number }) {
    activeBatchIndex.value = payload.batch_index
    parallelBatches.value.push({
      batch_index: payload.batch_index,
      step_indices: payload.step_indices,
      total_batches: payload.total_batches,
    })
    addLog(0, `批次 ${payload.batch_index}/${payload.total_batches} 开始: 步骤 ${payload.step_indices.join(', ')}`, 'info')
  }

  function handleBatchFinish(payload: { batch_index: number; step_indices: number[] }) {
    activeBatchIndex.value = null
    addLog(0, `批次 ${payload.batch_index} 完成`, 'success')
  }

  function handlePlanGenerated(payload: { steps: unknown[] }) {
    addLog(0, `计划已生成，共 ${payload.steps.length} 个步骤`, 'info')
  }

  function handleCheckpointSaved(payload: { step_index: number; checkpoint_id?: string }) {
    addLog(payload.step_index, `检查点已保存: ${payload.checkpoint_id ?? '-'}`, 'info')
  }

  function handleAgentThought(payload: AgentThought) {
    agentThoughts.value.push({ ...payload, timestamp: Date.now() })
  }

  function handleRunComplete(payload: { run_id: string; status: string }) {
    executionStatus.value = payload.status === 'success' ? 'completed' : payload.status as ExecutionStatus
    addLog(0, `执行结束: ${payload.status}`, payload.status === 'success' ? 'success' : 'error')
  }

  function setWsConnected(connected: boolean) {
    wsConnected.value = connected
  }

  function handleWsMessage(msg: Record<string, unknown>) {
    const type = msg.type as string
    const payload = msg as Record<string, unknown>
    switch (type) {
      case 'init':
        if (payload.run) setActiveRun(payload.run as APIRun)
        setWsConnected(true)
        break
      case 'step_start':
        handleStepStart(payload as any)
        break
      case 'step_finish':
        handleStepFinish(payload as any)
        break
      case 'step_error':
        handleStepError(payload as any)
        break
      case 'hitl_request':
        handleHITLRequest(payload as any)
        break
      case 'batch_start':
        handleBatchStart(payload as any)
        break
      case 'batch_finish':
        handleBatchFinish(payload as any)
        break
      case 'plan_generated':
        handlePlanGenerated(payload as any)
        break
      case 'checkpoint_saved':
        handleCheckpointSaved(payload as any)
        break
      case 'agent_thought':
        handleAgentThought(payload as any)
        break
      case 'run_complete':
        handleRunComplete(payload as any)
        setWsConnected(false)
        break
    }
  }

  return {
    runs,
    activeRun,
    wsConnected,
    hitlPending,
    agentThoughts,
    executionStatus,
    parallelBatches,
    activeBatchIndex,
    logEntries,
    stepStatusMap,
    currentRunId,
    setActiveRun,
    addLog,
    clearLogs,
    handleStepStart,
    handleStepFinish,
    handleStepError,
    handleHITLRequest,
    resolveHITL,
    handleBatchStart,
    handleBatchFinish,
    handlePlanGenerated,
    handleCheckpointSaved,
    handleAgentThought,
    handleRunComplete,
    setWsConnected,
    handleWsMessage,
  }
})
