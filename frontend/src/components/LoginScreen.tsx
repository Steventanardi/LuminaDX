import clsx from 'clsx'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

interface Props { isDark: boolean }

export default function LoginScreen({ isDark }: Props) {
  const { login } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) return
    setLoading(true)
    setError('')
    try {
      await login(email.trim(), password)
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const GLASS = clsx(
    'border shadow-2xl rounded-2xl',
    isDark ? 'bg-[#10151d] border-[#1f2835]' : 'bg-white border-[#e2e8ee]',
  )

  const INPUT = clsx(
    'w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-accent/60 transition-colors border',
    isDark
      ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-600'
      : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
  )

  return (
    <div className={clsx(
      'h-screen flex flex-col items-center justify-center relative overflow-hidden',
      isDark ? 'bg-[#0a0e14]' : 'bg-surface',
    )}>

      {/* Flat background — blobs removed for a calmer clinical feel */}

      <div className={clsx(GLASS, 'w-full max-w-sm mx-4 p-8 space-y-6 relative z-10')}>

        {/* Logo */}
        <div className="text-center space-y-3">
          <div className={clsx(
            'w-14 h-14 rounded-2xl border flex items-center justify-center mx-auto shadow-lg',
            isDark ? 'bg-accent/15 border-accent/30' : 'bg-accent/10 border-accent/20',
          )}>
            <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
            </svg>
          </div>
          <div>
            <h1 className={clsx('text-xl font-bold', isDark ? 'text-white' : 'text-slate-900')}>
              LuminaDx
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">Multi-Cancer AI Diagnostics</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-600')}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="doctor@hospital.com"
              autoComplete="email"
              required
              className={INPUT}
            />
          </div>

          <div className="space-y-1.5">
            <label className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-600')}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              className={INPUT}
            />
          </div>

          {error && (
            <p className={clsx(
              'text-xs rounded-lg px-3 py-2 border',
              isDark
                ? 'text-red-400 bg-red-950/30 border-red-900/30'
                : 'text-red-600 bg-red-50/80 border-red-200/60',
            )}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !email.trim() || !password}
            className={clsx(
              'w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200',
              loading || !email.trim() || !password
                ? 'bg-accent/40 text-white/50 cursor-not-allowed'
                : 'bg-accent hover:bg-teal-700 active:bg-teal-800 text-white shadow-lg shadow-teal-900/20',
            )}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Signing in…
              </span>
            ) : 'Sign in'}
          </button>
        </form>

        {/* Footer note */}
        <p className={clsx('text-[10px] text-center leading-relaxed', isDark ? 'text-slate-600' : 'text-slate-400')}>
          Clinician access only. Contact your administrator for account setup.
        </p>
      </div>

      {/* Disclaimer */}
      <p className={clsx('relative z-10 text-[10px] text-center mt-4 max-w-sm mx-4',
        isDark ? 'text-slate-700' : 'text-slate-400')}>
        For research and clinical decision support only. Not a substitute for professional medical judgment.
      </p>
    </div>
  )
}
