import { useEffect, useRef, useState } from 'react'
import type { PipelineEvent } from '../types'

export function usePipeline(onEvent?: (event: PipelineEvent) => void) {
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<PipelineEvent | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    const es = new EventSource('/api/pipeline/events')
    eventSourceRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      try {
        const event: PipelineEvent = JSON.parse(e.data)
        setLastEvent(event)
        onEventRef.current?.(event)
      } catch {
        // keepalive or invalid data
      }
    }

    es.onerror = () => {
      setConnected(false)
      // EventSource auto-reconnects
    }

    return () => {
      es.close()
      setConnected(false)
    }
  }, [])

  return { connected, lastEvent }
}
