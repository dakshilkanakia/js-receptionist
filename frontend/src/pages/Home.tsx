import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useCall, type CallStatus } from '../voice/useCall'

const STATUS: Record<CallStatus, string> = {
  idle: 'Tap to call. Your browser will ask for the microphone.',
  connecting: 'Connecting…',
  listening: 'Jenny is listening',
  speaking: 'Jenny is speaking',
  ended: 'Call ended. Thanks for calling!',
  error: 'Couldn\'t start the call',
}

function PhoneIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={className} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 5.5A2.5 2.5 0 0 1 5.5 3h1.6a1 1 0 0 1 .95.68l1.1 3.3a1 1 0 0 1-.4 1.15l-1.5 1a11 11 0 0 0 6.6 6.6l1-1.5a1 1 0 0 1 1.16-.4l3.3 1.1a1 1 0 0 1 .69.95v1.6A2.5 2.5 0 0 1 18.5 21C10 21 3 14 3 5.5Z" />
    </svg>
  )
}

export default function Home() {
  const { status, lines, error, start, end } = useCall()
  const inCall = status === 'connecting' || status === 'listening' || status === 'speaking'
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [lines])

  return (
    <div className="min-h-full bg-gradient-to-b from-brand-50 to-white">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-5">
        <div className="text-lg font-semibold tracking-tight">J's Cleaners</div>
        <Link to="/owner" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Owner dashboard →
        </Link>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-16">
        <section className="pt-10 text-center sm:pt-16">
          <p className="text-sm font-medium uppercase tracking-wider text-brand-600">AI receptionist</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            Questions about cleaning? Just ask Jenny.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-slate-600">
            Prices, rush service, alterations, pickup and delivery. Jenny answers right in your browser, and if she
            can't help, she'll have someone from our team call you back.
          </p>

          <div className="mt-10 flex flex-col items-center">
            <div className="relative">
              {inCall && (
                <span className={`absolute inset-0 rounded-full ${status === 'speaking' ? 'animate-ping bg-emerald-400/40' : 'bg-transparent'}`} />
              )}
              <button
                onClick={inCall ? end : start}
                disabled={status === 'connecting'}
                aria-label={inCall ? 'End call' : 'Call Jenny'}
                className={`relative flex h-24 w-24 items-center justify-center rounded-full text-white shadow-lg transition
                  focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-brand-500
                  ${inCall ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}
              >
                <PhoneIcon className={`h-10 w-10 ${inCall ? 'rotate-[135deg]' : ''} transition`} />
              </button>
            </div>
            <p className="mt-4 text-sm font-medium text-slate-700">{inCall ? 'End call' : 'Call Jenny'}</p>
            <p className="mt-1 text-sm text-slate-500" aria-live="polite">{STATUS[status]}</p>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          </div>
        </section>

        {lines.length > 0 && (
          <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-500">Live captions</h2>
            <div className="max-h-80 space-y-3 overflow-y-auto">
              {lines.map((l, i) => (
                <div key={i} className={`flex ${l.role === 'caller' ? 'justify-end' : 'justify-start'}`}>
                  <p className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                    l.role === 'caller' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
                    {l.text}
                  </p>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          </section>
        )}

        <section className="mt-12 grid gap-4 text-sm text-slate-600 sm:grid-cols-3">
          {[
            ['Honest by design', 'Jenny is an AI. She only shares our real prices and policies, and says so when she isn\'t sure.'],
            ['Transcribed calls', 'Calls are transcribed so our team can follow up. Ask Jenny to stop anytime.'],
            ['Demo', 'This is a demo. Please use a made-up name and phone number.'],
          ].map(([t, d]) => (
            <div key={t} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="font-medium text-slate-900">{t}</p>
              <p className="mt-1">{d}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  )
}
