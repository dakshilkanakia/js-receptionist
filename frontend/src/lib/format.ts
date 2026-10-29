import type { Outcome } from '../api/client'

const TZ = 'America/New_York'

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    timeZone: TZ, month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { timeZone: TZ, hour: 'numeric', minute: '2-digit', second: '2-digit' })
}

export function relativeTime(iso: string): string {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return formatDateTime(iso)
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m ? `${m}m ${s.toString().padStart(2, '0')}s` : `${s}s`
}

export function formatPhone(e164: string): string {
  const m = e164.match(/^\+1(\d{3})(\d{3})(\d{4})$/)
  return m ? `(${m[1]}) ${m[2]}-${m[3]}` : e164
}

export const OUTCOME_LABEL: Record<Outcome, string> = {
  answered: 'Answered',
  callback_requested: 'Callback',
  unanswered: 'Unanswered',
  abandoned: 'Abandoned',
  in_progress: 'In progress',
}

export const OUTCOME_TONE: Record<Outcome, 'green' | 'blue' | 'amber' | 'gray' | 'violet'> = {
  answered: 'green',
  callback_requested: 'blue',
  unanswered: 'amber',
  abandoned: 'gray',
  in_progress: 'violet',
}
