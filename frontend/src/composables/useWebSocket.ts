import { ref } from 'vue'

export function useWebSocket() {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let messageHandler: ((msg: Record<string, unknown>) => void) | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let shouldReconnect = true

  function connect(runId: string, onMessage: (msg: Record<string, unknown>) => void) {
    disconnect()
    shouldReconnect = true
    messageHandler = onMessage
    const url = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/run/${runId}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        onMessage(msg)
      } catch {
        // ignore
      }
    }

    ws.onclose = () => {
      connected.value = false
      ws = null
      if (shouldReconnect && messageHandler) {
        reconnectTimer = setTimeout(() => {
          if (messageHandler && shouldReconnect) {
            connect(runId, messageHandler)
          }
        }, 3000)
      }
    }

    ws.onerror = () => {
      connected.value = false
    }
  }

  function send(msg: Record<string, unknown>) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg))
    }
  }

  function disconnect() {
    shouldReconnect = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
    messageHandler = null
  }

  return {
    connected,
    connect,
    send,
    disconnect,
  }
}
