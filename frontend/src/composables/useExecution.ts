import { ref } from 'vue'
import { useRunStore } from '../stores/run'
import { useAppStore } from '../stores/app'
import { useWebSocket } from './useWebSocket'
import { startRun, sendHITLApproval, fetchRun } from './useApi'

export function useExecution() {
  const runStore = useRunStore()
  const appStore = useAppStore()
  const ws = useWebSocket()
  const selectedMode = ref('demo')
  const variables = ref<Record<string, unknown>>({})
  const model = ref('gpt-4o-mini')

  async function launchRun() {
    if (!appStore.selectedSkillName) return
    runStore.clearLogs()
    runStore.executionStatus = 'running'
    const res = await startRun({
      skill_name: appStore.selectedSkillName,
      mode: selectedMode.value,
      variables: variables.value,
      model: model.value,
    })
    const run = await fetchRun(res.run_id)
    runStore.setActiveRun(run)
    ws.connect(res.run_id, (msg) => runStore.handleWsMessage(msg))
  }

  async function approveHITL(decision: string, modifiedArguments?: Record<string, unknown>) {
    const runId = runStore.currentRunId
    if (!runId) return
    if (ws.connected.value) {
      ws.send({ type: 'hitl_approval', decision, modified_arguments: modifiedArguments })
    } else {
      await sendHITLApproval(runId, decision, modifiedArguments)
    }
    runStore.resolveHITL()
  }

  function disconnect() {
    ws.disconnect()
  }

  return {
    selectedMode,
    variables,
    model,
    wsConnected: ws.connected,
    launchRun,
    approveHITL,
    disconnect,
  }
}
