import UploadPanel from './UploadPanel'
import type { UploadResponse } from '../types'

interface Props {
  onUploaded: (res: UploadResponse) => void
  ragStatus: { chunks: number; pdf_count: number } | null
}

export default function UploadScreen({ onUploaded, ragStatus }: Props) {
  return (
    <div className="h-full flex items-center justify-center p-8 relative overflow-hidden">
      {/* Subtle radial glow behind the card */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 60% 50% at 50% 50%, rgba(99,102,241,0.06) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-lg space-y-8">
        {/* Icon + heading */}
        <div className="text-center space-y-4">
          <div className="relative inline-flex">
            <div className="absolute inset-0 rounded-2xl bg-accent/20 blur-xl" />
            <div className="relative w-16 h-16 rounded-2xl bg-accent/15 border border-accent/30 flex items-center justify-center">
              <svg className="w-8 h-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3 5a2 2 0 012-2h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
                <circle cx="12" cy="10" r="3" strokeLinecap="round" strokeLinejoin="round" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 19c0-3.3 2.7-6 6-6s6 2.7 6 6" />
              </svg>
            </div>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Upload Medical Scan</h2>
            <p className="text-sm text-slate-500 mt-1">
              MRI &amp; CT · DICOM · NIfTI · JPG/PNG
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <UploadPanel onUploaded={onUploaded} />

        {/* No guidelines warning */}
        {ragStatus && ragStatus.chunks === 0 && (
          <div className="flex items-start gap-2.5 bg-amber-950/30 border border-amber-900/30 rounded-xl px-3.5 py-3 text-xs">
            <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <div>
              <p className="font-semibold text-amber-400">No clinical guidelines loaded</p>
              <p className="text-amber-400/60 mt-0.5 leading-relaxed">
                Add PDFs to <code className="font-mono text-amber-300/70">backend/data/knowledge_base/</code> and use Settings → Ingest.
              </p>
            </div>
          </div>
        )}

        {/* Features row */}
        <div className="flex items-center justify-center gap-6 text-[10px] text-slate-600">
          {['HIPAA De-identified', 'Local LLM — no PHI leaves device', 'LI-RADS v2024'].map(f => (
            <span key={f} className="flex items-center gap-1">
              <span className="text-accent">✓</span>
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
