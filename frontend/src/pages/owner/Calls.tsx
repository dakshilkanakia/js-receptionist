import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, type CallPage, type Outcome } from '../../api/client'
import { OutcomeBadge } from '../../components/OutcomeBadge'
import { Badge, Button, Card, Empty, Loading, PageHeader, Tabs } from '../../components/ui'
import { formatDateTime, formatDuration } from '../../lib/format'

type Filter = 'all' | Outcome
const PAGE_SIZE = 25

export default function CallsPage() {
  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(1)
  const calls = useQuery({
    queryKey: ['calls', filter, page],
    queryFn: () => get<CallPage>(`/api/calls?page=${page}&page_size=${PAGE_SIZE}${filter === 'all' ? '' : `&outcome=${filter}`}`),
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  })
  const pages = calls.data ? Math.max(1, Math.ceil(calls.data.total / PAGE_SIZE)) : 1

  return (
    <>
      <PageHeader title="Calls" subtitle="Every call with time, length, outcome and transcript. Times are Eastern." />
      <div className="mb-4">
        <Tabs<Filter>
          value={filter}
          onChange={(v) => { setFilter(v); setPage(1) }}
          options={[
            { value: 'all', label: 'All' },
            { value: 'answered', label: 'Answered' },
            { value: 'callback_requested', label: 'Callback' },
            { value: 'unanswered', label: 'Unanswered' },
            { value: 'abandoned', label: 'Abandoned' },
          ]}
        />
      </div>

      <Card>
        {calls.isPending ? <Loading /> : !calls.data?.items.length ? <Empty title="No calls here yet" /> : (
          <>
          {/* Phones: one card per call */}
          <ul className="divide-y divide-slate-100 sm:hidden">
            {calls.data.items.map((c) => (
              <li key={c.id}>
                <Link to={`/owner/calls/${c.id}`} className="block px-4 py-3 active:bg-slate-50">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{formatDateTime(c.started_at)}</span>
                    <OutcomeBadge outcome={c.outcome} />
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-600">
                    {c.consent_declined
                      ? <span className="italic text-slate-400">Transcript not stored (caller declined)</span>
                      : c.preview ?? <span className="text-slate-400">No speech</span>}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">{formatDuration(c.duration_s)}</p>
                </Link>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Time</th>
                  <th className="px-5 py-3 font-medium">Length</th>
                  <th className="px-5 py-3 font-medium">Outcome</th>
                  <th className="px-5 py-3 font-medium">Caller asked</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {calls.data.items.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-5 py-3">
                      <Link to={`/owner/calls/${c.id}`} className="font-medium text-slate-900 hover:text-brand-600">
                        {formatDateTime(c.started_at)}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-5 py-3 tabular-nums text-slate-600">{formatDuration(c.duration_s)}</td>
                    <td className="whitespace-nowrap px-5 py-3">
                      <div className="flex gap-1.5">
                        <OutcomeBadge outcome={c.outcome} />
                        {c.has_unanswered && c.outcome !== 'unanswered' && <Badge tone="amber">Question</Badge>}
                      </div>
                    </td>
                    <td className="max-w-md truncate px-5 py-3 text-slate-600">
                      <Link to={`/owner/calls/${c.id}`}>
                        {c.consent_declined
                          ? <span className="italic text-slate-400">Transcript not stored (caller declined)</span>
                          : c.preview ?? <span className="text-slate-400">—</span>}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </Card>

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-3 text-sm text-slate-600">
          <Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          Page {page} of {pages}
          <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      )}
    </>
  )
}
