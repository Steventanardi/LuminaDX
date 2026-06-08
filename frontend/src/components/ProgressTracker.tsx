import clsx from 'clsx'
import type { AnalysisJob } from '../types'

const _STEPS = [
  { key: 'processing', label: 'DICOM' },
  { key: 'segmenting', label: 'Segment' },
  { key: 'extracting', label: 'Radiomics' },
  { key: 'analyzing',  label: 'LLM+RAG' },
  { key: 'complete',   label: 'Done' },
]

export default function ProgressTracker({ job, isDark = false }: { job: AnalysisJob; isDark?: boolean }) {
  const pct = job.progress
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-600')}>{job.current_step}</span>
        <span className="text-accent font-mono font-semibold text-sm">{pct}%</span>
      </div>
      <div className={clsx('h-2 rounded-full overflow-hidden', isDark ? 'bg-slate-800' : 'bg-slate-100')}>
        <div className={clsx('h-full rounded-full transition-all duration-700', job.status === 'failed' ? 'bg-red-500' : 'bg-accent')} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex gap-1">
        {_STEPS.map(step => {
          const idx    = _STEPS.findIndex(s => s.key === step.key)
          const curIdx = _STEPS.findIndex(s => s.key === job.status) ?? -1
          const done   = curIdx >= idx
          return (
            <div key={step.key} className="flex-1 text-center">
              <div className={clsx('mx-auto mb-1 h-1 rounded-full transition-colors duration-500', done ? 'bg-accent' : isDark ? 'bg-slate-700' : 'bg-slate-200')} />
              <p className={clsx('text-[9px]', done ? isDark ? 'text-slate-400' : 'text-slate-600' : isDark ? 'text-slate-700' : 'text-slate-300')}>{step.label}</p>
            </div>
          )
        })}
      </div>
      {job.status === 'failed' && <p className={clsx('text-xs', isDark ? 'text-red-400' : 'text-red-600')}>Error: {job.error}</p>}
    </div>
  )
}

