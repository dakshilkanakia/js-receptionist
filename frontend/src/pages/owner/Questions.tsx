import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, post, type Question } from '../../api/client'
import { Badge, Button, Card, Empty, ErrorNote, Field, Input, Loading, PageHeader, Tabs, Textarea } from '../../components/ui'
import { relativeTime } from '../../lib/format'

type Status = 'open' | 'answered' | 'dismissed'

function OpenQuestion({ q }: { q: Question }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [question, setQuestion] = useState(q.question)
  const [answer, setAnswer] = useState('')
  const refresh = () => ['questions', 'stats', 'facts'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  const save = useMutation({
    mutationFn: () => post<Question>(`/api/unanswered/${q.id}/answer`, { answer, question }),
    onSuccess: refresh,
  })
  const dismiss = useMutation({ mutationFn: () => post<Question>(`/api/unanswered/${q.id}/dismiss`), onSuccess: refresh })

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium">{q.question}</p>
          <p className="mt-1 text-xs text-slate-500">
            Asked {relativeTime(q.created_at)}
            {q.call_id && <> · <Link className="hover:underline" to={`/owner/calls/${q.call_id}`}>View call</Link></>}
          </p>
        </div>
        {!editing && (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setEditing(true)}>Answer</Button>
            <Button size="sm" variant="ghost" disabled={dismiss.isPending} onClick={() => dismiss.mutate()}>Dismiss</Button>
          </div>
        )}
      </div>
      {editing && (
        <form
          className="mt-4 space-y-3 rounded-lg bg-slate-50 p-4"
          onSubmit={(e) => { e.preventDefault(); save.mutate() }}
        >
          <Field label="Question" hint="Tidy up the wording if you like. This is what Jenny will match against.">
            <Input value={question} onChange={(e) => setQuestion(e.target.value)} required />
          </Field>
          <Field label="Answer" hint="Jenny says this on the next call. Write a full sentence, e.g. “Yes, leather jackets start at $60.”">
            <Textarea rows={3} value={answer} onChange={(e) => setAnswer(e.target.value)} required autoFocus />
          </Field>
          <ErrorNote error={save.error} />
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={save.isPending || !answer.trim()}>
              {save.isPending ? 'Saving…' : 'Save answer'}
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </form>
      )}
    </li>
  )
}

export default function QuestionsPage() {
  const [status, setStatus] = useState<Status>('open')
  const questions = useQuery({
    queryKey: ['questions', status],
    queryFn: () => get<Question[]>(`/api/unanswered?status=${status}`),
    refetchInterval: 5000,
  })

  return (
    <>
      <PageHeader title="Unanswered questions"
        subtitle="Questions Jenny wasn't sure about. Answer one and she'll use it from the next call on." />
      <div className="mb-4">
        <Tabs<Status> value={status} onChange={setStatus} options={[
          { value: 'open', label: 'Open' }, { value: 'answered', label: 'Answered' }, { value: 'dismissed', label: 'Dismissed' },
        ]} />
      </div>
      <Card>
        {questions.isPending ? <Loading /> : !questions.data?.length ? (
          <Empty title={status === 'open' ? "Jenny hasn't been stumped yet" : 'Nothing here'} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {questions.data.map((q) => status === 'open' ? <OpenQuestion key={q.id} q={q} /> : (
              <li key={q.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-medium">{q.question}</p>
                  <Badge tone={q.status === 'answered' ? 'green' : 'gray'}>{q.status}</Badge>
                </div>
                {q.answer && <p className="mt-2 text-sm text-slate-700">{q.answer}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
