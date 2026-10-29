import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AggregationType,
  PipecatClient,
  type BotOutputData,
  type Participant,
  type TranscriptData,
} from '@pipecat-ai/client-js'
import { WebSocketTransport } from '@pipecat-ai/websocket-transport'

export type CallStatus = 'idle' | 'connecting' | 'listening' | 'speaking' | 'ended' | 'error'

export interface Line {
  role: 'caller' | 'agent'
  text: string
  // Agent sentences arrive once per spoken status (new, completed) with the same
  // segment id, so we use it to update the line instead of appending a duplicate.
  segmentId?: number
}

function callUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/call`
}

export function useCall() {
  const [status, setStatus] = useState<CallStatus>('idle')
  const [lines, setLines] = useState<Line[]>([])
  const [error, setError] = useState<string | null>(null)
  const clientRef = useRef<PipecatClient | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    audioRef.current = new Audio()
    audioRef.current.autoplay = true
    return () => {
      void clientRef.current?.disconnect()
    }
  }, [])

  const addLine = useCallback((line: Line) => {
    setLines((prev) => {
      if (line.segmentId !== undefined) {
        const i = prev.findIndex((l) => l.role === line.role && l.segmentId === line.segmentId)
        if (i !== -1) return prev.map((l, j) => (j === i ? line : l))
      }
      return [...prev, line]
    })
  }, [])

  const start = useCallback(async () => {
    setError(null)
    setLines([])
    setStatus('connecting')

    const client = new PipecatClient({
      transport: new WebSocketTransport(),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onBotReady: () => setStatus('listening'),
        onBotStartedSpeaking: () => setStatus('speaking'),
        onBotStoppedSpeaking: () => setStatus('listening'),
        onDisconnected: () => setStatus((s) => (s === 'error' ? s : 'ended')),
        onUserTranscript: (t: TranscriptData) => {
          if (t.final && t.text.trim()) addLine({ role: 'caller', text: t.text })
        },
        onBotOutput: (d: BotOutputData) => {
          if (d.aggregated_by === AggregationType.SENTENCE && d.text.trim()) {
            addLine({ role: 'agent', text: d.text, segmentId: d.segment_id })
          }
        },
        onTrackStarted: (track: MediaStreamTrack, participant?: Participant) => {
          if (!participant?.local && track.kind === 'audio' && audioRef.current) {
            audioRef.current.srcObject = new MediaStream([track])
          }
        },
      },
    })
    clientRef.current = client

    try {
      await client.initDevices()
      await client.connect({ wsUrl: callUrl() })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus('error')
      void client.disconnect()
    }
  }, [addLine])

  const end = useCallback(async () => {
    await clientRef.current?.disconnect()
    setStatus('ended')
  }, [])

  return { status, lines, error, start, end }
}
