import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { ApiError, get, post, type Stats } from '../../api/client'
import { Loading } from '../../components/ui'

const NAV = [
  { to: '/owner', label: 'Overview', end: true },
  { to: '/owner/calls', label: 'Calls' },
  { to: '/owner/callbacks', label: 'Callbacks', countKey: 'pending_callbacks' as const },
  { to: '/owner/questions', label: 'Unanswered', countKey: 'open_questions' as const },
  { to: '/owner/facts', label: 'Facts & prices' },
]

function CallJennyLink() {
  // New tab, so the dashboard stays open and the call shows up here live.
  return (
    <a
      href="/"
      target="_blank"
      rel="noopener"
      className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M3 5.5A2.5 2.5 0 0 1 5.5 3h1.6a1 1 0 0 1 .95.68l1.1 3.3a1 1 0 0 1-.4 1.15l-1.5 1a11 11 0 0 0 6.6 6.6l1-1.5a1 1 0 0 1 1.16-.4l3.3 1.1a1 1 0 0 1 .69.95v1.6A2.5 2.5 0 0 1 18.5 21C10 21 3 14 3 5.5Z" />
      </svg>
      Call Jenny
    </a>
  )
}

export default function OwnerLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [menuOpen, setMenuOpen] = useState(false)
  const me = useQuery({ queryKey: ['me'], queryFn: () => get<{ email: string }>('/api/auth/me') })
  const stats = useQuery({
    queryKey: ['stats'], queryFn: () => get<Stats>('/api/stats'), enabled: me.isSuccess, refetchInterval: 5000,
  })

  if (me.isPending) return <Loading />
  if (me.error instanceof ApiError && me.error.status === 401) {
    return <Navigate to="/owner/login" replace state={{ from: location.pathname }} />
  }

  async function logout() {
    await post('/api/auth/logout')
    qc.clear()
    navigate('/owner/login')
  }

  const nav = (
    <nav className="space-y-1">
      {NAV.map((n) => {
        const count = n.countKey ? stats.data?.[n.countKey] : undefined
        return (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            onClick={() => setMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium ${
                isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            {n.label}
            {!!count && <span className="rounded-full bg-amber-400 px-2 py-0.5 text-xs font-semibold text-slate-900">{count}</span>}
          </NavLink>
        )
      })}
    </nav>
  )

  return (
    <div className="min-h-full lg:flex">
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 lg:flex lg:flex-col">
        <Link to="/" className="mb-6 block px-3">
          <div className="font-semibold">J's Cleaners</div>
          <div className="text-xs text-slate-500">Owner dashboard</div>
        </Link>
        {nav}
        <div className="mt-4"><CallJennyLink /></div>
        <div className="mt-auto border-t border-slate-100 px-3 pt-4 text-xs text-slate-500">
          <div className="truncate">{me.data?.email}</div>
          <button onClick={logout} className="mt-1 font-medium text-slate-700 hover:text-slate-900">Sign out</button>
        </div>
      </aside>

      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Link to="/" className="font-semibold">J's Cleaners</Link>
        <button onClick={() => setMenuOpen((o) => !o)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm">
          Menu
        </button>
      </div>
      {menuOpen && (
        <div className="border-b border-slate-200 bg-white p-4 lg:hidden">
          {nav}
          <div className="mt-3"><CallJennyLink /></div>
          <button onClick={logout} className="mt-3 px-3 text-sm font-medium text-slate-700">Sign out</button>
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 lg:py-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
