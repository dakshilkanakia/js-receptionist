import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { get, type CallPage, type Callback, type Outcome, type Question, type Stats } from '../../api/client'
import { OutcomeBadge } from '../../components/OutcomeBadge'
import { Card, CardHeader, Empty, Loading, PageHeader } from '../../components/ui'
import { formatDuration, formatPhone, OUTCOME_LABEL, relativeTime } from '../../lib/format'

function Stat({ label, value, to, highlight }: { label: string; value: string | number; to?: string; highlight?: boolean }) {
  const body = (
    <Card className={`p-5 ${to ? 'transition hover:border-slate-300' : ''}`}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-semibold tabular-nums ${highlight ? 'text-amber-600' : 'text-slate-900'}`}>{value}</p>
    </Card>
  )
  return to ? <Link to={to}>{body}</Link> : body
}

const ORDER: Outcome[] = ['answered', 'callback_requested', 'unanswered', 'abandoned']

export default function OverviewPage() {
  const stats = useQuery({ queryKey: ['stats'], queryFn: () => get<Stats>('/api/stats'), refetchInterval: 5000 })
  const calls = useQuery({
    queryKey: ['calls', 'recent'], queryFn: () => get<CallPage>('/api/calls?page_size=6'), refetchInterval: 5000,
  })
  const callbacks = useQuery({
    queryKey: ['callbacks', 'pending'], queryFn: () => get<Callback[]>('/api/callbacks?status=pending'), refetchInterval: 5000,
  })
  const questions = useQuery({
    queryKey: ['questions', 'open'], queryFn: () => get<Question[]>('/api/unanswered?status=open'), refetchInterval: 5000,
  })

  if (!stats.data) return <Loading />
  const s = stats.data
  const total7 = s.calls_7d || 1

  return (
    <>
      <PageHeader title="Overview" subtitle="Updates live as calls come in." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Calls today" value={s.calls_today} to="/owner/calls" />
        <Stat label="Avg call length (7 days)" value={formatDuration(s.avg_duration_s_7d)} />
        <Stat label="Callbacks waiting" value={s.pending_callbacks} to="/owner/callbacks" highlight={s.pending_callbacks > 0} />
        <Stat label="Unanswered questions" value={s.open_questions} to="/owner/questions" highlight={s.open_questions > 0} />
      </div>

      <Card className="mt-6">
        <CardHeader title="Last 7 days" subtitle={`${s.calls_7d} calls by outcome`} />
        <div className="p-5">
          <div className="flex h-3 overflow-hidden rounded-full bg-slate-100">
            {ORDER.map((o) => {
              const n = s.outcomes_7d[o] ?? 0
              const color = { answered: 'bg-emerald-500', callback_requested: 'bg-blue-500', unanswered: 'bg-amber-400', abandoned: 'bg-slate-300' }[o as string]
              return n ? <div key={o} className={color} style={{ width: `${(n / total7) * 100}%` }} title={`${OUTCOME_LABEL[o]}: ${n}`} /> : null
            })}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
            {ORDER.map((o) => (
              <span key={o} className="flex items-center gap-2">
                <OutcomeBadge outcome={o} /> <span className="tabular-nums">{s.outcomes_7d[o] ?? 0}</span>
              </span>
            ))}
          </div>
        </div>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Callbacks waiting" action={<Link className="text-sm font-medium text-brand-600" to="/owner/callbacks">View all</Link>} />
          {callbacks.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {callbacks.data.slice(0, 5).map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-4 px-5 py-3">
                  <div className="min-w-0">
                    <p className="font-medium">{c.first_name} · <a className="text-brand-600" href={`tel:${c.phone_e164}`}>{formatPhone(c.phone_e164)}</a></p>
                    <p className="truncate text-sm text-slate-500">{c.reason}</p>
                  </div>
                  <span className="shrink-0 text-xs text-slate-500">{relativeTime(c.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : <Empty title="No callbacks waiting" />}
        </Card>

        <Card>
          <CardHeader title="Questions Jenny couldn't answer"
            action={<Link className="text-sm font-medium text-brand-600" to="/owner/questions">Answer them</Link>} />
          {questions.data?.length ? (
            <ul className="divide-y divide-slate-100">
              {questions.data.slice(0, 5).map((q) => (
                <li key={q.id} className="flex items-center justify-between gap-4 px-5 py-3">
                  <p className="min-w-0 truncate text-sm">{q.question}</p>
                  <span className="shrink-0 text-xs text-slate-500">{relativeTime(q.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : <Empty title="Nothing unanswered" />}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Recent calls" action={<Link className="text-sm font-medium text-brand-600" to="/owner/calls">All calls</Link>} />
        {calls.isPending ? <Loading /> : calls.data?.items.length ? (
          <ul className="divide-y divide-slate-100">
            {calls.data.items.map((c) => (
              <li key={c.id}>
                <Link to={`/owner/calls/${c.id}`} className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-slate-50">
                  <div className="min-w-0">
                    <p className="truncate text-sm">{c.consent_declined ? <span className="italic text-slate-500">Transcript not stored (caller declined)</span> : c.preview ?? <span className="text-slate-400">No speech</span>}</p>
                    <p className="text-xs text-slate-500">{relativeTime(c.started_at)} · {formatDuration(c.duration_s)}</p>
                  </div>
                  <OutcomeBadge outcome={c.outcome} />
                </Link>
              </li>
            ))}
          </ul>
        ) : <Empty title="No calls yet" />}
      </Card>
    </>
  )
}
