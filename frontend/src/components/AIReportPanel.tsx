import clsx from 'clsx'
import { useState } from 'react'
import { pdf } from '@react-pdf/renderer'
import { analysisApi } from '../services/api'
import type { DiagnosticReport, LesionFinding, SignOff, SignOffDecision } from '../types'
import LiRadsScore from './LiRadsScore'
import ReportPDF from './ReportPDF'

interface Props {
  report: DiagnosticReport; jobId: string
  signOff: SignOff | null
  onSignOff: (name: string, decision: SignOffDecision, comments?: string) => Promise<void>
  currentSlice?: string
  isDark?: boolean
}

function Bool({ val }: { val: boolean | null }) {
  if (val === null || val === undefined) return <span className="text-slate-400 font-mono">&mdash;</span>
  return val
    ? <span className="text-emerald-500 font-semibold">Yes</span>
    : <span className="text-red-400 font-semibold">No</span>
}

function DataRow({ label, value, isDark = false }: { label: string; value: React.ReactNode; isDark?: boolean }) {
  return (
    <div className={clsx('flex items-center justify-between py-1 border-b last:border-0',
      isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>
      <span className="text-xs text-slate-400">{label}</span>
      <span className={clsx('text-xs font-mono', isDark ? 'text-slate-200' : 'text-slate-700')}>{value}</span>
    </div>
  )
}

function LesionCard({ l, defaultExpanded = true, isDark = false }: { l: LesionFinding; defaultExpanded?: boolean; isDark?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  return (
    <div className={clsx('border rounded-xl overflow-hidden',
      isDark ? 'bg-slate-800/50 border-white/[0.08]' : 'bg-white/50 border-black/[0.06]')}>
      <button
        onClick={() => setExpanded(e => !e)}
        className={clsx('w-full flex items-center justify-between gap-2 px-3.5 py-2.5 transition-colors',
          isDark ? 'hover:bg-white/[0.04]' : 'hover:bg-black/[0.03]')}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('font-semibold text-sm font-mono', isDark ? 'text-slate-100' : 'text-slate-800')}>{l.lesion_id}</span>
          {l.size_mm != null && <span className="text-[10px] text-slate-400 font-mono">{l.size_mm} mm</span>}
          {l.location_segment && <span className="text-[10px] text-slate-400">{l.location_segment}</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <LiRadsScore category={l.lirads_category} size="lg" />
          <svg className={clsx('w-3.5 h-3.5 text-slate-400 transition-transform duration-200', expanded && 'rotate-180')}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {expanded && (
        <div className={clsx('px-3.5 pb-3.5 space-y-3 border-t',
          isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>
          <div className="space-y-0.5 pt-2">
            <DataRow label="APHE"    value={<Bool val={l.aphe_present} />}          isDark={isDark} />
            <DataRow label="Washout" value={<Bool val={l.washout_present} />}       isDark={isDark} />
            <DataRow label="Capsule" value={<Bool val={l.capsule_present} />}       isDark={isDark} />
            <DataRow label="DWI"     value={<Bool val={l.diffusion_restriction} />} isDark={isDark} />
          </div>
          {l.major_features.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Major Features</p>
              <ul className="space-y-1">
                {l.major_features.map(f => (
                  <li key={f} className={clsx('text-xs flex gap-1.5', isDark ? 'text-slate-300' : 'text-slate-600')}>
                    <span className="text-accent mt-0.5 shrink-0">&bull;</span>{f}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {l.ancillary_features.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Ancillary Features</p>
              <ul className="space-y-1">
                {l.ancillary_features.map(f => (
                  <li key={f} className={clsx('text-xs flex gap-1.5', isDark ? 'text-slate-400' : 'text-slate-500')}>
                    <span className={clsx('mt-0.5 shrink-0', isDark ? 'text-slate-600' : 'text-slate-300')}>&#9702;</span>{f}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {l.reasoning && (
            <p className={clsx('text-xs italic border-t pt-2.5 leading-relaxed',
              isDark ? 'text-slate-400 border-white/[0.05]' : 'text-slate-500 border-black/[0.04]')}>
              {l.reasoning}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2.5">
      <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{title}</h3>
      {children}
    </div>
  )
}

function RadiomicsSection({ summary, isDark = false }: { summary: string; isDark?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const lines = summary.split('\n').filter(Boolean)
  return (
    <div className="space-y-2.5">
      <button onClick={() => setExpanded(e => !e)} className="flex items-center justify-between w-full group">
        <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 group-hover:text-slate-500 transition-colors">
          Radiomic Features
        </h3>
        <span className="text-[10px] text-slate-400 group-hover:text-slate-500 transition-colors font-mono">
          {expanded ? '▲ collapse' : `▼ ${lines.length} features`}
        </span>
      </button>
      <pre className={clsx(
        'text-xs whitespace-pre-wrap font-mono rounded-xl px-3 py-2 leading-relaxed border',
        isDark ? 'bg-slate-800/50 border-white/[0.06] text-slate-400' : 'bg-white/50 border-black/[0.05] text-slate-500',
        !expanded && 'italic',
      )}>
        {expanded ? summary : `${lines.slice(0, 3).join('\n')}${lines.length > 3 ? '\n…' : ''}`}
      </pre>
    </div>
  )
}

function formatText(report: DiagnosticReport): string {
  const lines = [
    'LIVER CANCER AI DIAGNOSTIC REPORT',
    `Generated: ${new Date(report.generated_at).toLocaleString()}`,
    `Modality: ${report.modality}`, '',
    'OVERALL IMPRESSION', report.overall_impression,
  ]
  if (report.bclc_stage) lines.push('', `BCLC: ${report.bclc_stage}`)
  if (report.recommendations.length) {
    lines.push('', 'RECOMMENDATIONS')
    report.recommendations.forEach(r => lines.push(`→ ${r}`))
  }
  lines.push('', '⚠ AI decision support only.')
  return lines.join('\n')
}

function SignOffBadge({ signOff, isDark = false }: { signOff: SignOff; isDark?: boolean }) {
  const approved = signOff.decision === 'approved'
  return (
    <div className={clsx('rounded-xl p-3 space-y-1.5 border', approved
      ? isDark ? 'bg-emerald-950/60 border-emerald-800/40' : 'bg-emerald-50/80 border-emerald-200/70'
      : isDark ? 'bg-amber-950/60 border-amber-800/40'   : 'bg-amber-50/80 border-amber-200/70')}>
      <span className={clsx('text-xs font-bold uppercase tracking-wide',
        approved
          ? isDark ? 'text-emerald-400' : 'text-emerald-700'
          : isDark ? 'text-amber-400'   : 'text-amber-700')}>
        {approved ? '✓ Approved' : '⚠ Changes Requested'}
      </span>
      <p className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>
        by{' '}
        <span className={clsx('font-medium', isDark ? 'text-slate-200' : 'text-slate-700')}>
          {signOff.radiologist_name}
        </span>
        {' · '}{new Date(signOff.signed_at).toLocaleString()}
      </p>
      {signOff.comments && (
        <p className={clsx('text-xs italic border-t pt-1.5',
          isDark ? 'text-slate-400 border-white/[0.05]' : 'text-slate-500 border-black/[0.05]')}>
          &ldquo;{signOff.comments}&rdquo;
        </p>
      )}
    </div>
  )
}

function SignOffForm({ onSignOff, isDark = false }: { onSignOff: Props['onSignOff']; isDark?: boolean }) {
  const [name, setName]         = useState('')
  const [decision, setDecision] = useState<SignOffDecision | null>(null)
  const [comments, setComments] = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async (d: SignOffDecision) => {
    if (!name.trim()) return
    setDecision(d); setLoading(true)
    try { await onSignOff(name.trim(), d, comments.trim() || undefined) } finally { setLoading(false) }
  }

  const INPUT = clsx(
    'mt-1 w-full border rounded-lg px-3 py-2 text-xs placeholder:text-slate-500 focus:outline-none focus:border-accent/50 transition-colors font-mono',
    isDark
      ? 'bg-slate-700/50 border-white/[0.08] text-slate-200'
      : 'bg-white/70 border-black/[0.07] text-slate-800',
  )

  return (
    <div className={clsx('space-y-3 border rounded-xl p-3.5',
      isDark ? 'bg-slate-800/40 border-white/[0.08]' : 'bg-white/40 border-black/[0.06]')}>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Radiologist Review</p>
      <label className="block">
        <span className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-500')}>Name / ID</span>
        <input
          type="text" value={name} onChange={e => setName(e.target.value)}
          placeholder="Dr. Smith / RAD-001" className={INPUT} />
      </label>
      <label className="block">
        <span className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-500')}>Comments (optional)</span>
        <textarea
          value={comments} onChange={e => setComments(e.target.value)}
          rows={2} placeholder="Notes…" className={INPUT.replace('font-mono', 'resize-none')} />
      </label>
      <div className="flex gap-2">
        <button
          onClick={() => submit('approved')} disabled={!name.trim() || loading}
          className="flex-1 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors disabled:opacity-40">
          {loading && decision === 'approved' ? 'Saving…' : '✓ Approve'}
        </button>
        <button
          onClick={() => submit('changes_requested')} disabled={!name.trim() || loading}
          className="flex-1 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition-colors disabled:opacity-40">
          {loading && decision === 'changes_requested' ? 'Saving…' : '⚠ Request Changes'}
        </button>
      </div>
    </div>
  )
}

export default function AIReportPanel({ report, jobId, signOff, onSignOff, currentSlice, isDark = false }: Props) {
  const [copied, setCopied]       = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const canExport = !!signOff

  const handleCopy = () =>
    navigator.clipboard.writeText(formatText(report))
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })

  const handlePDF = async () => {
    if (!canExport) return
    setPdfLoading(true)
    try {
      const blob = await pdf(<ReportPDF report={report} signOff={signOff} currentSlice={currentSlice} />).toBlob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `liver_ai_${new Date().toISOString().split('T')[0]}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } finally { setPdfLoading(false) }
  }

  const handleFhir = () => {
    if (!canExport) return
    const a = document.createElement('a')
    a.href = analysisApi.fhirUrl(jobId); a.download = `fhir_${jobId.slice(0,8)}.json`; a.click()
  }

  const BTN = (active: boolean) => clsx(
    'text-[10px] px-2 py-0.5 rounded-md border font-mono shrink-0 transition-colors',
    active
      ? isDark
        ? 'text-slate-400 hover:text-slate-200 border-white/[0.08] hover:border-slate-500'
        : 'text-slate-600 hover:text-slate-800 border-black/[0.08] hover:border-slate-400'
      : 'text-slate-500 border-black/[0.04] cursor-not-allowed opacity-40',
  )

  return (
    <div className="h-full overflow-y-auto space-y-5 pr-1">

      {/* Header row */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className={clsx('text-[10px] font-mono px-2 py-0.5 rounded-md font-semibold border',
              isDark ? 'bg-slate-700/60 border-white/[0.08] text-slate-300' : 'bg-white/60 border-black/[0.06] text-slate-600')}>
              {report.modality}
            </span>
            {report.rag_context_used && (
              <span className="text-[10px] bg-accent/10 text-accent px-2 py-0.5 rounded-md font-medium border border-accent/20">
                RAG-augmented
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={handlePDF} disabled={!canExport || pdfLoading}
              title={canExport ? 'Download PDF' : 'Sign-off required'} className={BTN(canExport && !pdfLoading)}>
              {pdfLoading ? 'Gen…' : 'PDF'}
            </button>
            <button onClick={handleFhir} disabled={!canExport}
              title={canExport ? 'FHIR R4 JSON' : 'Sign-off required'} className={BTN(canExport)}>
              FHIR
            </button>
            <button onClick={handleCopy}
              className={clsx('text-[10px] px-2 py-0.5 rounded-md border font-mono shrink-0 transition-colors',
                isDark
                  ? 'text-slate-400 hover:text-slate-200 border-white/[0.08]'
                  : 'text-slate-500 hover:text-slate-700 border-black/[0.08] hover:border-slate-400')}>
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>
        <p className={clsx('text-sm leading-relaxed', isDark ? 'text-slate-300' : 'text-slate-700')}>
          {report.overall_impression}
        </p>
        {!canExport && (
          <p className={clsx('text-[10px] italic', isDark ? 'text-amber-400/70' : 'text-amber-600/80')}>
            Sign-off required to enable PDF and FHIR export.
          </p>
        )}
      </div>

      {/* Lesions */}
      {report.lesions.length > 0 && (
        <Section title={`Lesions (${report.lesions.length})`}>
          {report.lesions.map((l, i) => (
            <LesionCard key={l.lesion_id} l={l} defaultExpanded={i === 0} isDark={isDark} />
          ))}
        </Section>
      )}

      {/* Differential */}
      {report.differential_diagnosis.length > 0 && (
        <Section title="Differential Diagnosis">
          <ol className="space-y-1.5">
            {report.differential_diagnosis.map((d, i) => (
              <li key={d} className="flex gap-2.5 items-start">
                <span className="text-accent font-mono text-xs font-bold w-4 shrink-0 mt-0.5">{i + 1}.</span>
                <span className={clsx('text-xs leading-relaxed', isDark ? 'text-slate-300' : 'text-slate-600')}>{d}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Staging */}
      {(report.bclc_stage || report.vascular_involvement) && (
        <Section title="Staging">
          <div className={clsx('border rounded-xl overflow-hidden',
            isDark ? 'bg-slate-800/40 border-white/[0.08]' : 'bg-white/40 border-black/[0.06]')}>
            {report.bclc_stage && (
              <div className={clsx('flex items-center justify-between px-3 py-2 border-b',
                isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>
                <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>BCLC Stage</span>
                <span className="text-sm font-bold text-orange-500 font-mono">{report.bclc_stage}</span>
              </div>
            )}
            {report.vascular_involvement && (
              <div className="flex items-center justify-between px-3 py-2">
                <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>Vascular</span>
                <span className={clsx('text-xs font-mono', isDark ? 'text-slate-200' : 'text-slate-700')}>
                  {report.vascular_involvement}
                </span>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Radiomics */}
      {report.radiomics_summary && !report.radiomics_summary.startsWith('Feature extraction unavailable') && (
        <RadiomicsSection summary={report.radiomics_summary} isDark={isDark} />
      )}

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <Section title="Recommendations">
          <ul className="space-y-1.5">
            {report.recommendations.map(r => (
              <li key={r} className="flex gap-2 items-start">
                <span className="text-accent shrink-0 mt-0.5 text-xs">&rarr;</span>
                <span className={clsx('text-xs leading-relaxed', isDark ? 'text-slate-300' : 'text-slate-600')}>{r}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Guideline Citations */}
      {report.guideline_citations.length > 0 && (
        <Section title="Guideline Citations">
          <ul className="space-y-1">
            {report.guideline_citations.map(c => (
              <li key={c} className="text-xs text-slate-400 italic">[{c}]</li>
            ))}
          </ul>
        </Section>
      )}

      {/* Sign-off */}
      <Section title="Radiologist Review">
        {signOff
          ? <SignOffBadge signOff={signOff} isDark={isDark} />
          : <SignOffForm onSignOff={onSignOff} isDark={isDark} />}
      </Section>

      {/* Disclaimer */}
      <div className={clsx('border rounded-xl p-3 text-xs leading-relaxed',
        isDark ? 'border-amber-900/25 bg-amber-950/15 text-amber-300/50' : 'border-amber-200/60 bg-amber-50/60 text-amber-700/70')}>
        &#9888; AI decision support only. Radiologist review required before clinical use.
      </div>
    </div>
  )
}
