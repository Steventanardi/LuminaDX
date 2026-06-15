import clsx from 'clsx'
import { useState } from 'react'
import AIReportPanel from './AIReportPanel'
import DicomViewer from './DicomViewer'
import type { AnalysisJob, DiagnosticReport, SignOffDecision } from '../types'

interface Props {
  slices: string[]
  rawSlices: string[]
  modality: string | null
  phase: string | null
  report: DiagnosticReport
  job: AnalysisJob
  signOff: (name: string, decision: SignOffDecision, comments?: string) => Promise<void>
  onRunAgain: () => void
}

export default function ResultsScreen({ slices, rawSlices, modality, phase, report, job, signOff, onRunAgain }: Props) {
  const [showRaw, setShowRaw] = useState(false)

  const lirads = report.lesions[0]?.lirads_category
  const bclc   = report.bclc_stage

  const liradsColor: Record<string, string> = {
    'LR-1': 'text-green-400', 'LR-2': 'text-lime-400',
    'LR-3': 'text-yellow-400', 'LR-4': 'text-orange-400',
    'LR-5': 'text-red-400', 'LR-M': 'text-purple-400',
    'LR-TIV': 'text-pink-400', 'Indeterminate': 'text-slate-400',
  }

  return (
    <div className="h-full flex overflow-hidden">

      {/* Left: DICOM viewer — takes majority of space */}
      <div className="flex-1 min-w-0 bg-black flex flex-col overflow-hidden">

        {/* Viewer toolbar */}
        <div className="flex items-center gap-3 px-3 py-2 bg-panel/80 border-b border-border shrink-0 text-xs">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-md bg-border text-slate-300 font-mono font-semibold text-[10px]">
              {modality ?? 'SCAN'}
            </span>
            <span className="text-slate-600">{slices.length} slices</span>
          </div>
          {lirads && (
            <span className={clsx('font-bold font-mono text-xs', liradsColor[lirads] ?? 'text-slate-300')}>
              {lirads}
            </span>
          )}
          {bclc && (
            <span className="text-orange-300 font-mono font-semibold text-xs">
              BCLC-{bclc}
            </span>
          )}
          <div className="flex-1" />
          <button
            onClick={onRunAgain}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-border hover:bg-accent/20 text-slate-400 hover:text-accent transition-colors text-[10px] font-medium"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Re-run
          </button>
        </div>

        {/* DICOM Viewer */}
        <div className="flex-1 min-h-0">
          <DicomViewer
            slices={slices}
            rawSlices={rawSlices.length ? rawSlices : undefined}
            modality={modality}
            phase={phase}
            isRunning={false}
          />
        </div>
      </div>

      {/* Right: Report panel */}
      <div className="w-[440px] shrink-0 flex flex-col border-l border-border overflow-hidden bg-panel">

        {/* Report header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-100">AI Report</h2>
            {report.rag_context_used && (
              <span className="text-[9px] bg-accent/15 text-accent px-2 py-0.5 rounded-full font-medium border border-accent/20">
                RAG
              </span>
            )}
            {job.sign_off && (
              <span className={clsx(
                'text-[9px] px-2 py-0.5 rounded-full font-medium border',
                job.sign_off.decision === 'approved'
                  ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800/40'
                  : 'bg-amber-950/50 text-amber-400 border-amber-800/40'
              )}>
                {job.sign_off.decision === 'approved' ? '✓ Signed' : '⚠ Pending'}
              </span>
            )}
          </div>
          <div className="flex rounded-lg overflow-hidden border border-border text-[10px] font-mono">
            <button
              onClick={() => setShowRaw(false)}
              className={clsx('px-2.5 py-1 transition-colors', !showRaw ? 'bg-accent text-white' : 'text-slate-500 hover:text-slate-300')}
            >
              Structured
            </button>
            <button
              onClick={() => setShowRaw(true)}
              className={clsx('px-2.5 py-1 transition-colors', showRaw ? 'bg-accent text-white' : 'text-slate-500 hover:text-slate-300')}
            >
              Raw
            </button>
          </div>
        </div>

        {/* Report content */}
        <div className="flex-1 overflow-hidden p-4">
          {showRaw ? (
            <pre className="text-xs text-slate-400 whitespace-pre-wrap font-mono overflow-y-auto h-full leading-relaxed">
              {report.raw_llm_output}
            </pre>
          ) : (
            <AIReportPanel
              report={report}
              jobId={job.job_id}
              signOff={job.sign_off ?? null}
              onSignOff={signOff}
              currentSlice={slices.length ? slices[Math.floor(slices.length / 2)] : undefined}
            />
          )}
        </div>
      </div>
    </div>
  )
}
