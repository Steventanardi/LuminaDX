import ProgressTracker from './ProgressTracker'
import type { AnalysisJob } from '../types'

interface Props {
  job: AnalysisJob
  previewSlices: string[]
  modality: string | null
}

export default function AnalysingScreen({ job }: Props) {
  const pct = job.progress

  return (
    <div className="h-full flex items-center justify-center bg-surface relative overflow-hidden">
      {/* Background radial glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 50% 40% at 50% 50%, rgba(99,102,241,0.08) 0%, transparent 70%)',
        }}
      />

      {/* Progress card */}
      <div className="relative z-10 bg-panel border border-border rounded-2xl p-10 w-full max-w-md space-y-8 shadow-[0_0_60px_rgba(16,185,129,0.08)]">

        {/* Animated icon */}
        <div className="flex justify-center">
          <div className="relative flex items-center justify-center w-24 h-24">
            <div className="absolute w-24 h-24 rounded-full border border-accent/20 animate-ping" style={{ animationDuration: '2s' }} />
            <div className="absolute w-16 h-16 rounded-full border border-accent/30 animate-ping" style={{ animationDuration: '2s', animationDelay: '0.4s' }} />
            <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/40 flex items-center justify-center">
              <svg className="w-6 h-6 text-accent animate-spin" style={{ animationDuration: '3s' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
                <circle cx="12" cy="10" r="3" strokeLinecap="round" strokeLinejoin="round" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 19c0-3.3 2.7-6 6-6s6 2.7 6 6" />
              </svg>
            </div>
          </div>
        </div>

        {/* Text */}
        <div className="text-center space-y-1.5">
          <h2 className="text-lg font-semibold text-slate-100">AI Analysis in Progress</h2>
          <p className="text-sm text-slate-500">{job.current_step || 'Starting pipeline...'}</p>
        </div>

        {/* Progress */}
        <ProgressTracker job={job} />

        {/* Percentage indicator */}
        <div className="text-center">
          <span className="text-3xl font-bold text-accent font-mono tabular-nums">{pct}%</span>
          <p className="text-[10px] text-slate-600 mt-1">Complete</p>
        </div>

        {/* Pipeline steps grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            { key: 'processing',  label: 'DICOM Conversion',    icon: '1' },
            { key: 'segmenting',  label: 'GPU Segmentation',    icon: '2' },
            { key: 'extracting',  label: 'Radiomic Features',   icon: '3' },
            { key: 'analyzing',   label: 'LLM + RAG Report',    icon: '4' },
          ].map(step => {
            const STATUS_ORDER = ['processing', 'segmenting', 'extracting', 'analyzing', 'complete']
            const stepIdx = STATUS_ORDER.indexOf(step.key)
            const curIdx  = STATUS_ORDER.indexOf(job.status)
            const done    = curIdx > stepIdx
            const active  = curIdx === stepIdx
            return (
              <div key={step.key} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface/60 border border-border/50">
                <span className={done ? 'text-emerald-400' : active ? 'text-accent animate-pulse' : 'text-slate-600'}>
                  {done ? '✓' : step.icon}
                </span>
                <span className={done ? 'text-slate-300' : active ? 'text-slate-200' : 'text-slate-600'}>
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

