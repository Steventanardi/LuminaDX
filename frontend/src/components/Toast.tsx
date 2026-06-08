import { useEffect } from 'react'
import clsx from 'clsx'

interface Props {
  message: string
  type?: 'success' | 'info' | 'error'
  isDark?: boolean
  onClose: () => void
}

export default function Toast({ message, type = 'info', isDark = false, onClose }: Props) {
  useEffect(() => {
    const t = setTimeout(onClose, 5000)
    return () => clearTimeout(t)
  }, [onClose])

  return (
    <div className={clsx(
      'fixed bottom-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-2xl',
      'shadow-2xl border backdrop-blur-xl toast-enter max-w-sm',
      type === 'success'
        ? isDark ? 'bg-emerald-950/90 border-emerald-800/50 text-emerald-200' : 'bg-white/90 border-emerald-200 text-emerald-800'
        : type === 'error'
        ? isDark ? 'bg-red-950/90 border-red-800/50 text-red-200' : 'bg-white/90 border-red-200 text-red-700'
        : isDark ? 'bg-slate-900/90 border-white/10 text-slate-200' : 'bg-white/90 border-black/10 text-slate-700',
    )}>
      {type === 'success' && (
        <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
      {type === 'error' && (
        <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center shrink-0">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      )}
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="text-current opacity-40 hover:opacity-80 transition-opacity text-lg leading-none ml-1 shrink-0">×</button>
    </div>
  )
}
