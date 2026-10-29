import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { get, type CallDetail, type Turn } from '../../api/client'
import { OutcomeBadge } from '../../components/OutcomeBadge'
import { Badge, Card, CardHeader, Empty, ErrorNote, Loading } from '../../components/ui'
import { formatDateTime, formatDuration, formatPhone, formatTime } from '../../lib/format'

function TurnRow({ t }: { t: Turn }) {
  if (t.role === 'tool') {
    return (
      <div className="flex justify-center">
        <p className="max-w-[90%] rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-1.5 font-mono text-xs text-slate-600">
          {t.text}
        </p>
      </div>
    )
  }
  const caller = t.role === 'user'
  return (
    <div className={`flex ${caller ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[80%]">
        <p className={`mb-1 text-xs text-slate-500 ${caller ? 'text-right' : ''}`}>
          {caller ? 'Caller' : 'Jenny'} · {formatTime(t.created_at)}
          {t.interrupted && ' · interrupted'}
        </p>
        <p className={`rounded-2xl px-4 py-2 text-sm ${caller ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
          {t.text}
        </p>
      </div>
    </div>
  )
}

export default function CallDetailPage() {
  const { id } = useParams()
  const call = useQuery({
    queryKey: ['call', id],
    queryFn: () => get<CallDetail>(`/api/calls/${id}`),
    refetchInterval: (q) => (q.state.data?.outcome === 'in_progress' ? 3000 : false),
  })

  if (call.error) return <ErrorNote error={call.error} />
  if (!call.data) return <Loading />
  const c = call.data

  return (
    <>
      <Link to="/owner/calls" className="text-sm font-medium text-slate-500 hover:text-slate-900">← All calls</Link>
      <div className="mt-3 mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Call on {formatDateTime(c.started_at)}</h1>
        <OutcomeBadge outcome={c.outcome} />
        {c.consent_declined && <Badge tone="red">Transcript declined</Badge>}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Transcript" subtitle="Dashed lines are actions Jenny took (quotes, saved callbacks, logged questions)." />
          <div className="space-y-4 p-5">
            {c.consent_declined ? (
              <Empty title="The caller asked not to be transcribed">Only the time, length and outcome were kept.</Empty>
            ) : c.turns.length ? c.turns.map((t) => <TurnRow key={t.idx} t={t} />) : <Empty title="No speech recorded" />}
          </div>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Details" />
            <dl className="divide-y divide-slate-100 text-sm">
              {[
                ['Started', formatDateTime(c.started_at)],
                ['Length', formatDuration(c.duration_s)],
                ['Facts version', c.facts_version_id ? `v${c.facts_version_id}` : '—'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between px-5 py-2.5">
                  <dt className="text-slate-500">{k}</dt><dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>

          {c.callbacks.length > 0 && (
            <Card>
              <CardHeader title="Callback requested" action={<Link to="/owner/callbacks" className="text-sm font-medium text-brand-600">Queue</Link>} />
              {c.callbacks.map((cb) => (
                <div key={cb.id} className="space-y-1 px-5 py-4 text-sm">
                  <p className="font-medium">{cb.first_name} · <a className="text-brand-600" href={`tel:${cb.phone_e164}`}>{formatPhone(cb.phone_e164)}</a></p>
                  <p className="text-slate-600">{cb.reason}</p>
                  <Badge tone={cb.status === 'done' ? 'green' : 'amber'}>{cb.status === 'done' ? 'Done' : 'Waiting'}</Badge>
                </div>
              ))}
            </Card>
          )}

          {c.questions.length > 0 && (
            <Card>
              <CardHeader title="Couldn't answer" action={<Link to="/owner/questions" className="text-sm font-medium text-brand-600">Answer</Link>} />
              <ul className="divide-y divide-slate-100 text-sm">
                {c.questions.map((q) => (
                  <li key={q.id} className="flex items-center justify-between gap-3 px-5 py-3">
                    <span>{q.question}</span>
                    <Badge tone={q.status === 'answered' ? 'green' : q.status === 'open' ? 'amber' : 'gray'}>{q.status}</Badge>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </>
  )
}
