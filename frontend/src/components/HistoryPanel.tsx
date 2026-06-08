import { useEffect, useState } from 'react'
import { analysisApi } from '../services/api'
import type { AnalysisJob } from '../types'

interface Props { open: boolean; onClose: () => void; isDark?: boolean }

function elapsed(job: AnalysisJob): string {
  if (!job.completed_at) return '—'
  return `${Math.round((new Date(job.completed_at).getTime() - new Date(job.created_at).getTime()) / 1000)}s`
}

const STATUS_LIGHT: Record<string, string> = {
  complete:   'bg-emerald-50 text-emerald-700 border border-emerald-200',
  failed:     'bg-red-50 text-red-600 border border-red-200',
  processing: 'bg-amber-50 text-amber-700 border border-amber-200',
  segmenting: 'bg-amber-50 text-amber-700 border border-amber-200',
  analyzing:  'bg-violet-50 text-violet-700 border border-violet-200',
}
const STATUS_DARK: Record<string, string> = {
  complete:   'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40',
  failed:     'bg-red-950/60 text-red-400 border border-red-800/40',
  processing: 'bg-amber-950/60 text-amber-400 border border-amber-800/40',
  segmenting: 'bg-amber-950/60 text-amber-400 border border-amber-800/40',
  analyzing:  'bg-violet-950/60 text-violet-400 border border-violet-800/40',
}

export default function HistoryPanel({ open, onClose, isDark = false }: Props) {
  const [jobs, setJobs] = useState<AnalysisJob[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    analysisApi.history().then(setJobs).catch(() => setJobs([])).finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  const STATUS = isDark ? STATUS_DARK : STATUS_LIGHT

  return (
    <>
      <div className={clsx('fixed inset-0 z-40 backdrop-blur-sm', isDark ? 'bg-black/50' : 'bg-black/20')} onClick={onClose} />
      <aside className={clsx('fixed right-0 top-0 bottom-0 z-50 w-80 flex flex-col shadow-2xl backdrop-blur-xl border-l',
        isDark ? 'bg-slate-900/90 border-white/[0.06]' : 'bg-white/80 border-white/80 shadow-violet-100/30')}>
        <div className={clsx('flex items-center justify-between px-4 py-3 border-b shrink-0', isDark ? 'border-white/[0.06]' : 'border-black/[0.06]')}>
          <h2 className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>Session History</h2>
          <button onClick={onClose} className={clsx('text-lg leading-none transition-colors', isDark ? 'text-slate-500 hover:text-slate-200' : 'text-slate-400 hover:text-slate-700')}>×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loading ? (
            <div className="flex items-center justify-center h-24 text-slate-400 text-sm">Loading…</div>
          ) : jobs.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-slate-400 text-sm text-center px-4">No analyses yet</div>
          ) : (
            jobs.map(job => (
              <div key={job.job_id} className={clsx('rounded-xl border p-3 space-y-2', isDark ? 'bg-white/5 border-white/[0.06]' : 'bg-white/60 border-black/[0.06]')}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-mono text-slate-400 truncate">{job.job_id.slice(0, 8)}…</span>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${STATUS[job.status] ?? (isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-50 text-slate-500')}`}>{job.status}</span>
                </div>
                <div className="grid grid-cols-3 gap-1 text-[10px]">
                  {[['LI-RADS', job.report?.lesions?.[0]?.lirads_category ?? '—'], ['BCLC', job.report?.bclc_stage ?? '—'], ['Time', elapsed(job)]].map(([k, v]) => (
                    <div key={k}>
                      <span className="text-slate-400 block">{k}</span>
                      <span className={clsx('font-medium', isDark ? 'text-slate-200' : 'text-slate-700')}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  )
}

function clsx(...args: (string | false | null | undefined)[]) {
  return args.filter(Boolean).join(' ')
}

