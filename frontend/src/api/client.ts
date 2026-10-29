export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    // FastAPI validation errors: [{loc, msg}]
    if (Array.isArray(d)) {
      return d
        .map((e: { loc?: (string | number)[]; msg?: string }) =>
          `${(e.loc ?? []).filter((p) => p !== 'body').join(' › ')}: ${e.msg ?? ''}`)
        .join('\n')
    }
  }
  return fallback
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  })
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, detailMessage(body, res.statusText))
  return body as T
}

export const get = <T,>(path: string) => api<T>(path)
export const post = <T,>(path: string, data?: unknown) =>
  api<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) })
export const put = <T,>(path: string, data: unknown) => api<T>(path, { method: 'PUT', body: JSON.stringify(data) })
export const patch = <T,>(path: string, data: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(data) })

// ---- Types mirroring the backend ----

export type Outcome = 'answered' | 'callback_requested' | 'unanswered' | 'abandoned' | 'in_progress'

export interface CallSummary {
  id: number
  started_at: string
  ended_at: string | null
  duration_s: number | null
  outcome: Outcome
  consent_declined: boolean
  has_unanswered: boolean
  facts_version_id: number | null
  turn_count: number
  preview: string | null
}

export interface CallPage {
  items: CallSummary[]
  total: number
  page: number
  page_size: number
}

export interface Turn {
  idx: number
  role: 'user' | 'assistant' | 'tool'
  text: string
  interrupted: boolean
  created_at: string
}

export interface CallDetail extends CallSummary {
  turns: Turn[]
  callbacks: { id: number; first_name: string; phone_e164: string; reason: string; status: string }[]
  questions: { id: number; question: string; status: string }[]
}

export interface Callback {
  id: number
  call_id: number | null
  first_name: string
  phone_e164: string
  reason: string
  status: 'pending' | 'done'
  owner_note: string | null
  created_at: string
  handled_at: string | null
}

export interface Question {
  id: number
  call_id: number | null
  question: string
  status: 'open' | 'answered' | 'dismissed'
  answer: string | null
  created_at: string
  answered_at: string | null
}

export interface Stats {
  calls_today: number
  calls_7d: number
  outcomes_7d: Partial<Record<Outcome, number>>
  avg_duration_s_7d: number | null
  pending_callbacks: number
  open_questions: number
}

export interface OpenHours { open: string; close: string }
export const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const
export type Day = (typeof DAYS)[number]

export interface Facts {
  business: {
    name: string; city: string; years: string; main_phone: string; timezone: string
    store_count: number; boroughs: string[]; locations_url: string
  }
  stores: { name: string; phone: string | null; hours: Record<Day, OpenHours | null> }[]
  services: string[]
  prices: {
    id: string; name: string; unit: 'each' | 'lb' | 'pair'; price: string
    category: 'dry_cleaning' | 'wash_fold' | 'household' | 'sneakers' | 'alteration'
    min_qty: number | null; same_day_eligible: boolean
  }[]
  addons: { id: string; name: string; unit: 'each' | 'piece'; price: string; requires_item: string | null }[]
  price_note: string
  turnaround: string
  rush: { id: 'next_day' | 'same_day'; label: string; surcharge_pct: string; condition: string | null }[]
  alterations: string
  pickup_delivery: string
  never: string[]
  faqs: { question: string; answer: string; unanswered_id: number | null }[]
}

export interface FactsVersion {
  version_id: number
  created_at: string
  created_by: string
  note: string | null
  data: Facts
}

export interface VersionSummary { id: number; created_at: string; created_by: string; note: string | null }
