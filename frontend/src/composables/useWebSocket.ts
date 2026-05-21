import { ref, onUnmounted } from 'vue'

export interface WSMessage {
  type: 'log' | 'progress' | 'complete' | 'error' | 'new_useful_comment'
  level?: string
  message?: string
  data?: any
  phase?: string
  current?: number
  total?: number
}

export function useWebSocket(taskId: number) {
  const connected = ref(false)
  const messages = ref<WSMessage[]>([])
  const progress = ref({ phase: '', current: 0, total: 0 })

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    ws = new WebSocket(`${protocol}//${host}/ws/tasks/${taskId}/logs`)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)

        if (msg.type === 'pong') return

        messages.value.push(msg)
        // Keep last 200 messages
        if (messages.value.length > 200) {
          messages.value = messages.value.slice(-200)
        }

        if (msg.type === 'progress') {
          progress.value = {
            phase: msg.phase || '',
            current: msg.current || 0,
            total: msg.total || 0,
          }
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      connected.value = false
      // Auto reconnect after 3s
      reconnectTimer = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function sendPing() {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send('ping')
    }
  }

  // Auto-ping every 30s to keep alive
  const pingInterval = setInterval(sendPing, 30000)

  onUnmounted(() => {
    disconnect()
    clearInterval(pingInterval)
  })

  return {
    connected,
    messages,
    progress,
    connect,
    disconnect,
  }
}
