import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  ApiError, DAYS, get, post, put, type Day, type Facts, type FactsVersion, type VersionSummary,
} from '../../api/client'
import { StringList } from '../../components/StringList'
import { Button, Card, CardHeader, ErrorNote, Field, Input, Loading, PageHeader, Textarea } from '../../components/ui'
import { formatDateTime } from '../../lib/format'

const DAY_LABEL: Record<Day, string> = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' }
const CATEGORY_LABEL = {
  dry_cleaning: 'Dry cleaning', wash_fold: 'Wash & fold', household: 'Household', sneakers: 'Sneakers', alteration: 'Alteration',
}

const clone = <T,>(x: T): T => structuredClone(x)
const slug = (s: string) => s.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'item'

function uniqueId(base: string, taken: Set<string>) {
  let id = base
  for (let i = 2; taken.has(id); i++) id = `${base}_${i}`
  return id
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <div className="p-5">{children}</div>
    </Card>
  )
}

const cell = 'px-2 py-2 align-top'

export default function FactsPage() {
  const qc = useQueryClient()
  const current = useQuery({ queryKey: ['facts'], queryFn: () => get<FactsVersion>('/api/facts') })
  const versions = useQuery({ queryKey: ['facts', 'versions'], queryFn: () => get<VersionSummary[]>('/api/facts/versions') })
  const [draft, setDraft] = useState<Facts | null>(null)
  const [baseId, setBaseId] = useState<number | null>(null)
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState<number | null>(null)
  const [confirmRestore, setConfirmRestore] = useState<number | null>(null)

  // Start a fresh draft whenever a new version is loaded and there are no unsaved edits.
  useEffect(() => {
    if (current.data && (draft === null || baseId === null)) {
      setDraft(clone(current.data.data))
      setBaseId(current.data.version_id)
    }
  }, [current.data, draft, baseId])

  const dirty = useMemo(
    () => !!draft && !!current.data && baseId === current.data.version_id && JSON.stringify(draft) !== JSON.stringify(current.data.data),
    [draft, current.data, baseId],
  )

  const reload = () => { setDraft(null); setBaseId(null); qc.invalidateQueries({ queryKey: ['facts'] }) }

  const save = useMutation({
    mutationFn: () => put<FactsVersion>('/api/facts', { data: cleanForSave(draft!), note: note || undefined, base_version_id: baseId }),
    onSuccess: (v) => {
      qc.setQueryData(['facts'], v)
      qc.invalidateQueries({ queryKey: ['facts', 'versions'] })
      setDraft(clone(v.data)); setBaseId(v.version_id); setNote(''); setSaved(v.version_id)
    },
  })
  const restore = useMutation({
    mutationFn: (id: number) => post<FactsVersion>(`/api/facts/versions/${id}/restore`),
    onSuccess: (v) => {
      qc.setQueryData(['facts'], v)
      qc.invalidateQueries({ queryKey: ['facts', 'versions'] })
      setDraft(clone(v.data)); setBaseId(v.version_id); setConfirmRestore(null); setSaved(v.version_id)
    },
  })

  if (!draft || !current.data) return current.error ? <ErrorNote error={current.error} /> : <Loading />

  const set = (fn: (d: Facts) => void) => {
    setSaved(null)
    setDraft((d) => { const n = clone(d!); fn(n); return n })
  }
  const stale = save.error instanceof ApiError && save.error.status === 409

  return (
    <>
      <PageHeader
        title="Facts & prices"
        subtitle={`Jenny only says what's on this page. Changes apply to the next call, no redeploy. Current version: v${current.data.version_id}.`}
      />

      {saved && !dirty && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Saved as version v{saved}. The next call will use it.
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1fr_280px]">
        <div className="space-y-6 pb-28">
          <Section title="Prices" subtitle="Starting-at prices. Same-day rush is only offered for items ticked below.">
            {/* Phones: one card per item */}
            <div className="space-y-3 sm:hidden">
              {draft.prices.map((p, i) => (
                <div key={p.id} className="space-y-2 rounded-lg border border-slate-200 p-3">
                  <Field label="Item"><Input value={p.name} onChange={(e) => set((d) => { d.prices[i].name = e.target.value })} /></Field>
                  <div className="grid grid-cols-3 gap-2">
                    <Field label="Price ($)">
                      <Input inputMode="decimal" value={p.price} onChange={(e) => set((d) => { d.prices[i].price = e.target.value })} />
                    </Field>
                    <Field label="Per">
                      <select className="w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm" value={p.unit}
                        onChange={(e) => set((d) => { d.prices[i].unit = e.target.value as typeof p.unit })}>
                        <option value="each">each</option><option value="lb">lb</option><option value="pair">pair</option>
                      </select>
                    </Field>
                    <Field label="Min">
                      <Input inputMode="numeric" value={p.min_qty ?? ''} placeholder="—"
                        onChange={(e) => set((d) => { d.prices[i].min_qty = e.target.value ? Number(e.target.value) : null })} />
                    </Field>
                  </div>
                  <Field label="Category">
                    <select className="w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm" value={p.category}
                      onChange={(e) => set((d) => { d.prices[i].category = e.target.value as typeof p.category })}>
                      {Object.entries(CATEGORY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                  </Field>
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" className="h-4 w-4" checked={p.same_day_eligible}
                        onChange={(e) => set((d) => { d.prices[i].same_day_eligible = e.target.checked })} />
                      Same-day rush allowed
                    </label>
                    <Button variant="ghost" size="sm" onClick={() => set((d) => { d.prices.splice(i, 1) })}>Remove</Button>
                  </div>
                </div>
              ))}
            </div>
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr><th className={cell}>Item</th><th className={cell}>Price ($)</th><th className={cell}>Per</th>
                    <th className={cell}>Min</th><th className={cell}>Category</th><th className={cell}>Same-day</th><th className={cell} /></tr>
                </thead>
                <tbody>
                  {draft.prices.map((p, i) => (
                    <tr key={p.id} className="border-t border-slate-100">
                      <td className={cell}><Input value={p.name} onChange={(e) => set((d) => { d.prices[i].name = e.target.value })} /></td>
                      <td className={`${cell} w-28`}><Input inputMode="decimal" value={p.price} onChange={(e) => set((d) => { d.prices[i].price = e.target.value })} /></td>
                      <td className={`${cell} w-28`}>
                        <select className="w-full rounded-lg border border-slate-300 bg-white px-2 py-2" value={p.unit}
                          onChange={(e) => set((d) => { d.prices[i].unit = e.target.value as typeof p.unit })}>
                          <option value="each">each</option><option value="lb">lb</option><option value="pair">pair</option>
                        </select>
                      </td>
                      <td className={`${cell} w-20`}>
                        <Input inputMode="numeric" value={p.min_qty ?? ''} placeholder="—"
                          onChange={(e) => set((d) => { d.prices[i].min_qty = e.target.value ? Number(e.target.value) : null })} />
                      </td>
                      <td className={`${cell} w-40`}>
                        <select className="w-full rounded-lg border border-slate-300 bg-white px-2 py-2" value={p.category}
                          onChange={(e) => set((d) => { d.prices[i].category = e.target.value as typeof p.category })}>
                          {Object.entries(CATEGORY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                      </td>
                      <td className={`${cell} text-center`}>
                        <input type="checkbox" className="mt-2.5 h-4 w-4" checked={p.same_day_eligible}
                          onChange={(e) => set((d) => { d.prices[i].same_day_eligible = e.target.checked })} />
                      </td>
                      <td className={cell}>
                        <Button variant="ghost" size="sm" aria-label={`Remove ${p.name}`}
                          onClick={() => set((d) => { d.prices.splice(i, 1) })}>Remove</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Button variant="secondary" size="sm" className="mt-3" onClick={() => set((d) => {
              const id = uniqueId('new_item', new Set([...d.prices, ...d.addons].map((x) => x.id)))
              d.prices.push({ id, name: '', unit: 'each', price: '0.00', category: 'dry_cleaning', min_qty: null, same_day_eligible: false })
            })}>Add item</Button>
          </Section>

          <Section title="Add-ons">
            <div className="space-y-3">
              {draft.addons.map((a, i) => (
                <div key={a.id} className="grid gap-2 sm:grid-cols-[1fr_110px_150px_auto]">
                  <Input value={a.name} onChange={(e) => set((d) => { d.addons[i].name = e.target.value })} />
                  <Input inputMode="decimal" value={a.price} onChange={(e) => set((d) => { d.addons[i].price = e.target.value })} />
                  <select className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm" value={a.unit}
                    onChange={(e) => set((d) => { d.addons[i].unit = e.target.value as typeof a.unit })}>
                    <option value="piece">per piece</option><option value="each">each</option>
                  </select>
                  <Button variant="ghost" size="sm" onClick={() => set((d) => { d.addons.splice(i, 1) })}>Remove</Button>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Turnaround & rush">
            <div className="space-y-4">
              <Field label="Turnaround"><Textarea rows={2} value={draft.turnaround} onChange={(e) => set((d) => { d.turnaround = e.target.value })} /></Field>
              {draft.rush.map((r, i) => (
                <div key={r.id} className="grid gap-3 sm:grid-cols-[160px_1fr]">
                  <Field label={`${r.label} surcharge (%)`}>
                    <Input inputMode="decimal" value={r.surcharge_pct} onChange={(e) => set((d) => { d.rush[i].surcharge_pct = e.target.value })} />
                  </Field>
                  <Field label="Condition">
                    <Input value={r.condition ?? ''} placeholder="None"
                      onChange={(e) => set((d) => { d.rush[i].condition = e.target.value || null })} />
                  </Field>
                </div>
              ))}
            </div>
          </Section>

          {draft.stores.map((s, si) => (
            <Section key={si} title={`Hours: ${s.name}`} subtitle="Jenny only quotes hours for stores listed here.">
              <div className="mb-4 grid gap-3 sm:grid-cols-2">
                <Field label="Store name"><Input value={s.name} onChange={(e) => set((d) => { d.stores[si].name = e.target.value })} /></Field>
                <Field label="Store phone"><Input value={s.phone ?? ''} placeholder="Not listed"
                  onChange={(e) => set((d) => { d.stores[si].phone = e.target.value || null })} /></Field>
              </div>
              <div className="space-y-2">
                {DAYS.map((day) => {
                  const h = s.hours[day]
                  return (
                    <div key={day} className="flex flex-wrap items-center gap-3 text-sm">
                      <span className="w-10 font-medium">{DAY_LABEL[day]}</span>
                      <label className="flex items-center gap-2 text-slate-600">
                        <input type="checkbox" checked={!h}
                          onChange={(e) => set((d) => { d.stores[si].hours[day] = e.target.checked ? null : { open: '09:00', close: '17:00' } })} />
                        Closed
                      </label>
                      {h && (
                        <>
                          <Input type="time" className="w-32" value={h.open}
                            onChange={(e) => set((d) => { d.stores[si].hours[day]!.open = e.target.value })} />
                          <span className="text-slate-400">to</span>
                          <Input type="time" className="w-32" value={h.close}
                            onChange={(e) => set((d) => { d.stores[si].hours[day]!.close = e.target.value })} />
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            </Section>
          ))}

          <Section title="Policies">
            <div className="space-y-4">
              <Field label="Price note"><Textarea rows={2} value={draft.price_note} onChange={(e) => set((d) => { d.price_note = e.target.value })} /></Field>
              <Field label="Alterations"><Textarea rows={3} value={draft.alterations} onChange={(e) => set((d) => { d.alterations = e.target.value })} /></Field>
              <Field label="Pickup & delivery"><Textarea rows={3} value={draft.pickup_delivery} onChange={(e) => set((d) => { d.pickup_delivery = e.target.value })} /></Field>
              <Field label="Services" hint="One per line."><StringList value={draft.services} onChange={(v) => set((d) => { d.services = v })} rows={8} /></Field>
              <Field label="Jenny must never…" hint="One per line. These go to a callback instead.">
                <StringList value={draft.never} onChange={(v) => set((d) => { d.never = v })} />
              </Field>
            </div>
          </Section>

          <Section title="Answers to common questions" subtitle="Added from Unanswered questions, or write your own.">
            <div className="space-y-4">
              {draft.faqs.length === 0 && <p className="text-sm text-slate-500">None yet.</p>}
              {draft.faqs.map((f, i) => (
                <div key={i} className="space-y-2 rounded-lg border border-slate-200 p-3">
                  <Input value={f.question} placeholder="Question" onChange={(e) => set((d) => { d.faqs[i].question = e.target.value })} />
                  <Textarea rows={2} value={f.answer} placeholder="Answer" onChange={(e) => set((d) => { d.faqs[i].answer = e.target.value })} />
                  <Button variant="ghost" size="sm" onClick={() => set((d) => { d.faqs.splice(i, 1) })}>Remove</Button>
                </div>
              ))}
              <Button variant="secondary" size="sm" onClick={() => set((d) => { d.faqs.push({ question: '', answer: '', unanswered_id: null }) })}>
                Add answer
              </Button>
            </div>
          </Section>

          <Section title="Business">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Name"><Input value={draft.business.name} onChange={(e) => set((d) => { d.business.name = e.target.value })} /></Field>
              <Field label="Main phone"><Input value={draft.business.main_phone} onChange={(e) => set((d) => { d.business.main_phone = e.target.value })} /></Field>
              <Field label="Locations page"><Input value={draft.business.locations_url} onChange={(e) => set((d) => { d.business.locations_url = e.target.value })} /></Field>
              <Field label="Number of stores"><Input inputMode="numeric" value={draft.business.store_count}
                onChange={(e) => set((d) => { d.business.store_count = Number(e.target.value) || 0 })} /></Field>
            </div>
          </Section>
        </div>

        <aside className="xl:sticky xl:top-8 xl:self-start">
          <Card>
            <CardHeader title="Version history" subtitle="Every save is kept." />
            <ul className="max-h-[60vh] divide-y divide-slate-100 overflow-y-auto text-sm">
              {versions.data?.map((v) => (
                <li key={v.id} className="px-5 py-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">v{v.id}{v.id === current.data.version_id && <span className="ml-2 text-xs text-emerald-600">current</span>}</span>
                    {v.id !== current.data.version_id && (
                      confirmRestore === v.id ? (
                        <span className="flex gap-1">
                          <Button size="sm" disabled={restore.isPending} onClick={() => restore.mutate(v.id)}>Confirm</Button>
                          <Button size="sm" variant="ghost" onClick={() => setConfirmRestore(null)}>Cancel</Button>
                        </span>
                      ) : <Button size="sm" variant="ghost" disabled={dirty} onClick={() => setConfirmRestore(v.id)}>Restore</Button>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">{formatDateTime(v.created_at)} · {v.created_by}</p>
                  {v.note && <p className="mt-0.5 text-xs text-slate-600">{v.note}</p>}
                </li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>

      {(dirty || save.error) && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur lg:left-60">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-slate-700">Unsaved changes</span>
            <Input className="min-w-48 flex-1" placeholder="What changed? (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            <Button variant="ghost" onClick={reload}>Discard</Button>
            <Button disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? 'Saving…' : 'Save changes'}</Button>
            {save.error && (
              <div className="w-full">
                <ErrorNote error={save.error} />
                {stale && <Button variant="secondary" size="sm" className="mt-2" onClick={reload}>Load latest version</Button>}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

/** Give new items stable ids from their names and drop blank FAQ rows before saving. */
function cleanForSave(d: Facts): Facts {
  const out = clone(d)
  const isNew = (id: string) => id.startsWith('new_item')
  const taken = new Set([...out.prices, ...out.addons].map((x) => x.id).filter((id) => !isNew(id)))
  for (const p of out.prices) {
    if (isNew(p.id)) {
      p.id = uniqueId(slug(p.name), taken)
      taken.add(p.id)
    }
  }
  out.faqs = out.faqs.filter((f) => f.question.trim() && f.answer.trim())
  out.services = out.services.map((s) => s.trim()).filter(Boolean)
  out.never = out.never.map((s) => s.trim()).filter(Boolean)
  return out
}
