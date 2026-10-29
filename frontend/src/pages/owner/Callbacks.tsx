import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, patch, type Callback } from '../../api/client'
import { Button, Card, Empty, ErrorNote, Input, Loading, PageHeader, Tabs } from '../../components/ui'
import { formatDateTime, formatPhone, relativeTime } from '../../lib/format'

type Status = 'pending' | 'done'

function CallbackRow({ cb }: { cb: Callback }) {
  const qc = useQueryClient()
  const [note, setNote] = useState(cb.owner_note ?? '')
  const update = useMutation({
    mutationFn: (body: Partial<Pick<Callback, 'status' | 'owner_note'>>) => patch<Callback>(`/api/callbacks/${cb.id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['callbacks'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
  const pending = cb.status === 'pending'

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-medium">
            {cb.first_name} ·{' '}
            <a href={`tel:${cb.phone_e164}`} className="text-brand-600 hover:underline">{formatPhone(cb.phone_e164)}</a>
          </p>
          <p className="mt-1 text-sm text-slate-700">{cb.reason}</p>
          <p className="mt-1 text-xs text-slate-500">
            Requested {relativeTime(cb.created_at)}
            {cb.call_id && <> · <Link className="hover:underline" to={`/owner/calls/${cb.call_id}`}>View call</Link></>}
            {cb.handled_at && <> · Done {formatDateTime(cb.handled_at)}</>}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <a href={`tel:${cb.phone_e164}`}><Button variant="secondary" size="sm">Call</Button></a>
          <Button size="sm" variant={pending ? 'primary' : 'secondary'} disabled={update.isPending}
            onClick={() => update.mutate({ status: pending ? 'done' : 'pending' })}>
            {pending ? 'Mark done' : 'Reopen'}
          </Button>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Input placeholder="Add a note (e.g. left voicemail)" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button size="sm" variant="secondary" disabled={note === (cb.owner_note ?? '') || update.isPending}
          onClick={() => update.mutate({ owner_note: note })}>Save</Button>
      </div>
      <div className="mt-2"><ErrorNote error={update.error} /></div>
    </li>
  )
}

export default function CallbacksPage() {
  const [status, setStatus] = useState<Status>('pending')
  const callbacks = useQuery({
    queryKey: ['callbacks', status],
    queryFn: () => get<Callback[]>(`/api/callbacks?status=${status}`),
    refetchInterval: 5000,
  })

  return (
    <>
      <PageHeader title="Callbacks" subtitle="People Jenny promised a call back. Oldest first." />
      <div className="mb-4">
        <Tabs<Status> value={status} onChange={setStatus}
          options={[{ value: 'pending', label: 'Waiting' }, { value: 'done', label: 'Done' }]} />
      </div>
      <Card>
        {callbacks.isPending ? <Loading /> : callbacks.data?.length ? (
          <ul className="divide-y divide-slate-100">
            {callbacks.data.map((cb) => <CallbackRow key={cb.id} cb={cb} />)}
          </ul>
        ) : <Empty title={status === 'pending' ? 'No one is waiting for a call back' : 'Nothing marked done yet'} />}
      </Card>
    </>
  )
}
