import clsx from 'clsx'
import DicomViewer from './DicomViewer'
import type { AnalysisJob, PatientContext, UploadResponse } from '../types'

interface Props {
  upload: UploadResponse
  previewSlices: string[]
  ctx: PatientContext
  setCtx: React.Dispatch<React.SetStateAction<PatientContext>>
  onAnalyse: () => void
  onReset: () => void
  isRunning: boolean
  failedJob: AnalysisJob | null
}

const CTX_LABELS: Record<string, string> = {
  cirrhosis: 'Cirrhosis',
  hepatitis_b: 'Hep B',
  hepatitis_c: 'Hep C',
  prior_hcc: 'Prior HCC',
}

export default function PreviewScreen({ upload, previewSlices, ctx, setCtx, onAnalyse, onReset, isRunning, failedJob }: Props) {
  return (
    <div className="h-full flex flex-col overflow-hidden">

      {/* Study info strip */}
      <div className="flex items-center gap-4 px-4 py-2 bg-panel border-b border-border shrink-0 text-xs">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-md bg-border text-slate-300 font-mono font-semibold text-[10px]">
            {upload.modality ?? 'DICOM'}
          </span>
          <span className="text-slate-500">{upload.num_files} files</span>
          <span className="text-slate-700">·</span>
          <span className="text-slate-500">{upload.series.length} series</span>
        </div>
        {failedJob && (
          <span className="text-red-400 text-[10px] font-medium">
            ⚠ Previous run failed — {failedJob.error?.slice(0, 60)}
          </span>
        )}
        <div className="ml-auto">
          <button
            onClick={onReset}
            className="text-[10px] text-slate-600 hover:text-slate-300 transition-colors underline underline-offset-2"
          >
            Upload different scan
          </button>
        </div>
      </div>

      {/* DICOM viewer — takes all remaining space */}
      <div className="flex-1 min-h-0 bg-black">
        <DicomViewer
          slices={previewSlices}
          modality={upload.modality ?? null}
          phase={upload.series[0]?.phase ?? null}
          isRunning={false}
        />
      </div>

      {/* Clinical context dock */}
      <div className="shrink-0 bg-panel border-t border-border px-5 py-4">
        <div className="flex items-center gap-4 flex-wrap">

          {/* Label */}
          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-600 shrink-0">
            Clinical Context
          </span>

          {/* Condition pill toggles */}
          <div className="flex items-center gap-2 flex-wrap">
            {(['cirrhosis', 'hepatitis_b', 'hepatitis_c', 'prior_hcc'] as const).map(key => (
              <button
                key={key}
                onClick={() => setCtx(p => ({ ...p, [key]: !p[key] }))}
                className={clsx(
                  'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
                  ctx[key]
                    ? 'bg-accent text-white shadow-sm shadow-accent/30'
                    : 'bg-border text-slate-400 hover:bg-accent/15 hover:text-slate-200',
                )}
              >
                {CTX_LABELS[key]}
              </button>
            ))}
          </div>

          {/* AFP level */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 whitespace-nowrap">AFP</span>
            <div className="relative">
              <input
                type="number"
                value={ctx.afp_level ?? ''}
                onChange={e => setCtx(p => ({ ...p, afp_level: e.target.value ? Number(e.target.value) : null }))}
                placeholder="—"
                className="w-24 bg-surface border border-border rounded-lg pl-2.5 pr-9 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-accent transition-colors"
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-slate-600 pointer-events-none">
                ng/mL
              </span>
            </div>
          </div>

          {/* Spacer */}
          <div className="flex-1 min-w-0" />

          {/* Run Analysis CTA */}
          <button
            onClick={onAnalyse}
            disabled={isRunning}
            className={clsx(
              'flex items-center gap-2.5 px-6 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200 shrink-0',
              isRunning
                ? 'bg-accent/20 text-accent/60 cursor-not-allowed'
                : 'bg-accent hover:bg-indigo-500 active:bg-indigo-700 text-white shadow-lg shadow-accent/25 hover:shadow-accent/40',
            )}
          >
            {isRunning ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analysing…
              </>
            ) : (
              <>
                Run Analysis
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
