import { useCall } from './voice/useCall'
import './App.css'

const STATUS_LABEL: Record<string, string> = {
  idle: 'Ready',
  connecting: 'Connecting…',
  listening: 'Listening',
  speaking: 'Speaking',
  ended: 'Call ended',
  error: 'Something went wrong',
}

export default function App() {
  const { status, lines, error, start, end } = useCall()
  const inCall = status === 'connecting' || status === 'listening' || status === 'speaking'

  return (
    <main className="home">
      <h1>J's Cleaners</h1>
      <p className="tagline">Talk to our AI receptionist, right in your browser.</p>

      <button className={inCall ? 'call end' : 'call'} onClick={inCall ? end : start}>
        {inCall ? 'End call' : 'Call the receptionist'}
      </button>
      <p className="status">{STATUS_LABEL[status]}</p>
      {error && <p className="error">{error}</p>}

      <section className="transcript">
        {lines.map((l, i) => (
          <p key={i} className={l.role}>
            <strong>{l.role === 'caller' ? 'You' : 'Receptionist'}:</strong> {l.text}
          </p>
        ))}
      </section>
    </main>
  )
}
