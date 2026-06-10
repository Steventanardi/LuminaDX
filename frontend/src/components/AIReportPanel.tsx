import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { pdf } from '@react-pdf/renderer'
import { analysisApi } from '../services/api'
import { useI18n } from '../i18n'
import type { DiagnosticReport, LesionFinding, SignOff, SignOffDecision } from '../types'
import LiRadsScore from './LiRadsScore'
import ReportPDF from './ReportPDF'

interface Props {
  report: DiagnosticReport
  jobId: string
  signOff: SignOff | null
  onSignOff: (name: string, decision: SignOffDecision, comments?: string) => Promise<void>
  currentSlice?: string
  isDark?: boolean
  currentUserName?: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function deepCopy(r: DiagnosticReport): DiagnosticReport {
  return {
    ...r,
    lesions: r.lesions.map(l => ({
      ...l,
      major_features: [...l.major_features],
      ancillary_features: [...l.ancillary_features],
    })),
    differential_diagnosis: [...r.differential_diagnosis],
    recommendations:        [...r.recommendations],
    guideline_citations:    [...r.guideline_citations],
  }
}

const toLines = (arr: string[]) => arr.join('\n')
const fromLines = (s: string): string[] => s.split('\n').map(x => x.trim()).filter(Boolean)

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ title, isDark }: { title: string; isDark: boolean }) {
  return (
    <h3 className={clsx('text-[10px] font-semibold uppercase tracking-widest',
      isDark ? 'text-slate-400' : 'text-slate-500')}>
      {title}
    </h3>
  )
}

function EditTextarea({
  value, onChange, rows = 3, placeholder, isDark,
}: {
  value: string; onChange: (v: string) => void; rows?: number; placeholder?: string; isDark: boolean
}) {
  return (
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      rows={rows}
      placeholder={placeholder}
      className={clsx(
        'w-full rounded-xl px-3 py-2 text-xs border resize-y focus:outline-none focus:border-accent/60 transition-colors leading-relaxed',
        isDark
          ? 'bg-white/[0.08] border-white/[0.15] text-slate-200 placeholder:text-slate-500'
          : 'bg-white/80 border-black/[0.10] text-slate-800 placeholder:text-slate-400',
      )}
    />
  )
}

function EditInput({
  value, onChange, placeholder, isDark, type = 'text',
}: {
  value: string; onChange: (v: string) => void; placeholder?: string; isDark: boolean; type?: string
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={clsx(
        'w-full rounded-lg px-3 py-1.5 text-xs border focus:outline-none focus:border-accent/60 transition-colors',
        isDark
          ? 'bg-white/[0.08] border-white/[0.15] text-slate-200 placeholder:text-slate-500'
          : 'bg-white/80 border-black/[0.10] text-slate-800 placeholder:text-slate-400',
      )}
    />
  )
}

// ── Lesion card (view + edit) ─────────────────────────────────────────────────

function LesionCard({
  l, cancerType = 'liver', editMode, onUpdate, defaultExpanded = true, isDark = false,
}: {
  l: LesionFinding; cancerType?: string; editMode: boolean
  onUpdate: (updated: LesionFinding) => void
  defaultExpanded?: boolean; isDark?: boolean
}) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(defaultExpanded)
  const isLiver = cancerType === 'liver'

  const upd = (patch: Partial<LesionFinding>) => onUpdate({ ...l, ...patch })

  const CARD = clsx('border rounded-xl overflow-hidden',
    isDark ? 'bg-slate-800/50 border-white/[0.08]' : 'bg-white/50 border-black/[0.06]',
    editMode && (isDark ? 'border-accent/30' : 'border-accent/25'),
  )

  return (
    <div className={CARD}>
      <button
        onClick={() => setExpanded(e => !e)}
        className={clsx('w-full flex items-center justify-between gap-2 px-3.5 py-2.5 transition-colors',
          isDark ? 'hover:bg-white/[0.04]' : 'hover:bg-black/[0.03]')}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('font-semibold text-sm font-mono', isDark ? 'text-slate-100' : 'text-slate-800')}>
            {l.lesion_id}
          </span>
          {l.size_mm != null && <span className="text-[10px] text-slate-400 font-mono">{l.size_mm} mm</span>}
          {l.location_segment && <span className="text-[10px] text-slate-400">{l.location_segment}</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <LiRadsScore category={l.lirads_category} score={l.score} scoreSystem={l.score_system} size="lg" />
          <svg className={clsx('w-3.5 h-3.5 text-slate-400 transition-transform', expanded && 'rotate-180')}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className={clsx('px-3.5 pb-3.5 space-y-3 border-t',
          isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>

          {editMode ? (
            /* ── Edit fields ── */
            <div className="space-y-2.5 pt-2.5">
              <div className="grid grid-cols-2 gap-2">
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wide text-slate-400">Location</span>
                  <EditInput value={l.location_segment ?? ''} isDark={isDark}
                    placeholder="e.g. Segment VI"
                    onChange={v => upd({ location_segment: v || null })} />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase tracking-wide text-slate-400">Size (mm)</span>
                  <EditInput type="number" value={l.size_mm != null ? String(l.size_mm) : ''} isDark={isDark}
                    placeholder="—"
                    onChange={v => upd({ size_mm: v ? Number(v) : null })} />
                </label>
              </div>
              <label className="block space-y-1">
                <span className="text-[10px] uppercase tracking-wide text-slate-400">Score / Category</span>
                <EditInput value={l.score ?? l.lirads_category} isDark={isDark}
                  placeholder="e.g. LR-5 / High risk"
                  onChange={v => upd({ score: v })} />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] uppercase tracking-wide text-slate-400">
                  Major Features <span className="normal-case font-normal">(one per line)</span>
                </span>
                <EditTextarea rows={3} value={toLines(l.major_features)} isDark={isDark}
                  placeholder="Arterial phase hyperenhancement&#10;Washout appearance"
                  onChange={v => upd({ major_features: fromLines(v) })} />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] uppercase tracking-wide text-slate-400">
                  Ancillary Features <span className="normal-case font-normal">(one per line)</span>
                </span>
                <EditTextarea rows={2} value={toLines(l.ancillary_features)} isDark={isDark}
                  placeholder="T2 mild hyperintensity&#10;DWI restricted diffusion"
                  onChange={v => upd({ ancillary_features: fromLines(v) })} />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] uppercase tracking-wide text-slate-400">Reasoning / Notes</span>
                <EditTextarea rows={3} value={l.reasoning ?? ''} isDark={isDark}
                  placeholder="Clinical reasoning…"
                  onChange={v => upd({ reasoning: v || null })} />
              </label>
            </div>
          ) : (
            /* ── View fields ── */
            <>
              {isLiver && (
                <div className="space-y-0.5 pt-2">
                  {[
                    ['APHE',    l.aphe_present],
                    ['Washout', l.washout_present],
                    ['Capsule', l.capsule_present],
                    ['DWI',     l.diffusion_restriction],
                  ].map(([label, val]) => (
                    <div key={String(label)} className={clsx('flex items-center justify-between py-1 border-b last:border-0',
                      isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>
                      <span className="text-xs text-slate-400">{label}</span>
                      {val === null || val === undefined
                        ? <span className="text-slate-400 font-mono text-xs">&mdash;</span>
                        : val
                          ? <span className="text-emerald-500 font-semibold text-xs">{t('ai.yes')}</span>
                          : <span className="text-red-400 font-semibold text-xs">{t('ai.no')}</span>}
                    </div>
                  ))}
                </div>
              )}
              {l.major_features.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">{t('ai.majorFeatures')}</p>
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
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">{t('ai.ancillaryFeatures')}</p>
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
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── Sign-off badge ─────────────────────────────────────────────────────────────

function SignOffBadge({ signOff, isDark = false }: { signOff: SignOff; isDark?: boolean }) {
  const { t } = useI18n()
  const approved = signOff.decision === 'approved'
  return (
    <div className={clsx('rounded-xl p-3 space-y-1.5 border', approved
      ? isDark ? 'bg-emerald-950/60 border-emerald-800/40' : 'bg-emerald-50/80 border-emerald-200/70'
      : isDark ? 'bg-amber-950/60 border-amber-800/40'     : 'bg-amber-50/80 border-amber-200/70')}>
      <span className={clsx('text-xs font-bold uppercase tracking-wide',
        approved
          ? isDark ? 'text-emerald-400' : 'text-emerald-700'
          : isDark ? 'text-amber-400'   : 'text-amber-700')}>
        {approved ? t('ai.approved') : t('ai.changesRequested')}
      </span>
      <p className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>
        {t('ai.by')}{' '}
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

// ── Sign-off form ─────────────────────────────────────────────────────────────

function SignOffForm({
  onSignOff, prefillName = '', isDark = false,
}: {
  onSignOff: Props['onSignOff']; prefillName?: string; isDark?: boolean
}) {
  const { t } = useI18n()
  const [name, setName]         = useState(prefillName)
  const [decision, setDecision] = useState<SignOffDecision | null>(null)
  const [comments, setComments] = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async (d: SignOffDecision) => {
    if (!name.trim()) return
    setDecision(d); setLoading(true)
    try { await onSignOff(name.trim(), d, comments.trim() || undefined) }
    finally { setLoading(false) }
  }

  const INPUT = clsx(
    'mt-1 w-full border rounded-lg px-3 py-2 text-xs placeholder:text-slate-500 focus:outline-none focus:border-accent/50 transition-colors font-mono',
    isDark ? 'bg-white/[0.08] border-white/[0.12] text-slate-200' : 'bg-white/70 border-black/[0.07] text-slate-800',
  )

  return (
    <div className={clsx('space-y-3 border rounded-xl p-3.5',
      isDark ? 'bg-slate-800/40 border-white/[0.08]' : 'bg-white/40 border-black/[0.06]')}>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{t('ai.radiologistReview')}</p>
      <label className="block">
        <span className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-500')}>{t('ai.nameId')}</span>
        <input type="text" value={name} onChange={e => setName(e.target.value)}
          placeholder={t('ai.namePlaceholder')}
          readOnly={!!prefillName}
          className={clsx(INPUT, prefillName && 'opacity-70 cursor-default')} />
      </label>
      <label className="block">
        <span className={clsx('text-xs font-medium', isDark ? 'text-slate-400' : 'text-slate-500')}>{t('ai.commentsOptional')}</span>
        <textarea value={comments} onChange={e => setComments(e.target.value)}
          rows={2} placeholder={t('ai.notes')} className={INPUT.replace('font-mono', 'resize-none')} />
      </label>
      <div className="flex gap-2">
        <button onClick={() => submit('approved')} disabled={!name.trim() || loading}
          className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-sm">
          {loading && decision === 'approved' ? t('ai.saving') : '✓ ' + t('ai.approve')}
        </button>
        <button onClick={() => submit('changes_requested')} disabled={!name.trim() || loading}
          className="flex-1 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-sm">
          {loading && decision === 'changes_requested' ? t('ai.saving') : t('ai.requestChanges')}
        </button>
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function AIReportPanel({
  report, jobId, signOff, onSignOff, currentSlice, isDark = false, currentUserName,
}: Props) {
  const { t } = useI18n()

  // Local editable draft — initialized from the AI report, editable by the doctor
  const [draft, setDraft]       = useState<DiagnosticReport>(() => deepCopy(report))
  const [editMode, setEditMode] = useState(false)
  const [editBuf, setEditBuf]   = useState<DiagnosticReport>(() => deepCopy(report))

  // If parent passes a new report (re-analysis), reset draft
  useEffect(() => {
    const fresh = deepCopy(report)
    setDraft(fresh)
    setEditBuf(fresh)
    setEditMode(false)
  }, [report.study_id, report.generated_at])

  const [pdfLoading, setPdfLoading] = useState(false)
  const [copied, setCopied]         = useState(false)
  const canExport = !!signOff

  // ── Mutators on editBuf ──────────────────────────────────────────────────

  const updBuf = (patch: Partial<DiagnosticReport>) =>
    setEditBuf(p => ({ ...p, ...patch }))

  const updLesion = (i: number, updated: LesionFinding) =>
    setEditBuf(p => {
      const lesions = [...p.lesions]
      lesions[i] = updated
      return { ...p, lesions }
    })

  const enterEdit = () => { setEditBuf(deepCopy(draft)); setEditMode(true) }
  const saveEdit  = () => { setDraft(deepCopy(editBuf)); setEditMode(false) }
  const cancelEdit = () => setEditMode(false)

  // ── Export handlers ──────────────────────────────────────────────────────

  const handlePDF = async () => {
    setPdfLoading(true)
    try {
      const blob = await pdf(
        <ReportPDF report={draft} signOff={signOff} currentSlice={currentSlice} />
      ).toBlob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `luminadx_${draft.cancer_type}_${new Date().toISOString().split('T')[0]}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } finally { setPdfLoading(false) }
  }

  const handleFhir = () => {
    const a = document.createElement('a')
    a.href = analysisApi.fhirUrl(jobId)
    a.download = `fhir_${jobId.slice(0, 8)}.json`
    a.click()
  }

  const handleCopy = () => {
    const lines = [
      'LUMINADX DIAGNOSTIC REPORT',
      `Generated: ${new Date(draft.generated_at).toLocaleString()}`,
      `Cancer type: ${draft.cancer_type.toUpperCase()}  Modality: ${draft.modality}`,
      '', 'OVERALL IMPRESSION', draft.overall_impression,
    ]
    if (draft.differential_diagnosis.length) {
      lines.push('', 'DIFFERENTIAL DIAGNOSIS')
      draft.differential_diagnosis.forEach((d, i) => lines.push(`  ${i + 1}. ${d}`))
    }
    if (draft.recommendations.length) {
      lines.push('', 'RECOMMENDATIONS')
      draft.recommendations.forEach(r => lines.push(`  → ${r}`))
    }
    lines.push('', '⚠ AI decision support only — requires clinician review.')
    navigator.clipboard.writeText(lines.join('\n'))
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }

  const cur = editMode ? editBuf : draft

  // ── Shared style helpers ─────────────────────────────────────────────────

  const TA = clsx('border-b pb-3', isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')

  return (
    <div className="h-full overflow-y-auto space-y-5 pr-1">

      {/* ── Header: modality badge + edit toggle + copy ── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('text-[10px] font-mono px-2 py-0.5 rounded-md font-semibold border',
            isDark ? 'bg-slate-700/60 border-white/[0.08] text-slate-300' : 'bg-white/60 border-black/[0.06] text-slate-600')}>
            {cur.modality}
          </span>
          {cur.rag_context_used && (
            <span className="text-[10px] bg-accent/10 text-accent px-2 py-0.5 rounded-md font-medium border border-accent/20">
              {t('ai.ragAugmented')}
            </span>
          )}
          {editMode && (
            <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-md font-semibold">
              Editing draft
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {/* Copy button stays at top */}
          <button onClick={handleCopy}
            className={clsx('text-[10px] px-2 py-0.5 rounded-md border font-mono shrink-0 transition-colors',
              isDark
                ? 'text-slate-400 hover:text-slate-200 border-white/[0.08]'
                : 'text-slate-500 hover:text-slate-700 border-black/[0.08] hover:border-slate-400')}>
            {copied ? t('ai.copied') : t('ai.copy')}
          </button>
          {/* Edit / Save / Cancel */}
          {!signOff && (
            editMode ? (
              <div className="flex items-center gap-1">
                <button onClick={saveEdit}
                  className="text-[10px] px-2.5 py-0.5 rounded-md bg-accent hover:bg-violet-600 text-white font-semibold transition-colors">
                  Save
                </button>
                <button onClick={cancelEdit}
                  className={clsx('text-[10px] px-2 py-0.5 rounded-md border font-mono transition-colors',
                    isDark ? 'border-white/[0.08] text-slate-400 hover:text-slate-200' : 'border-black/[0.08] text-slate-500 hover:text-slate-800')}>
                  Cancel
                </button>
              </div>
            ) : (
              <button onClick={enterEdit}
                className={clsx('flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-md border font-semibold transition-colors',
                  isDark ? 'border-white/[0.08] text-slate-300 hover:text-accent hover:border-accent/40'
                         : 'border-black/[0.08] text-slate-600 hover:text-accent hover:border-accent/30')}>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487z" />
                </svg>
                Edit
              </button>
            )
          )}
        </div>
      </div>

      {/* ── Overall Impression ── */}
      <div className={TA}>
        <div className="flex items-center justify-between mb-2">
          <SectionHeader title="Overall Impression" isDark={isDark} />
        </div>
        {editMode ? (
          <EditTextarea
            value={editBuf.overall_impression} rows={4} isDark={isDark}
            placeholder="Overall diagnostic impression…"
            onChange={v => updBuf({ overall_impression: v })} />
        ) : (
          <p className={clsx('text-sm leading-relaxed', isDark ? 'text-slate-200' : 'text-slate-700')}>
            {cur.overall_impression}
          </p>
        )}
      </div>

      {/* ── Lesions ── */}
      {cur.lesions.length > 0 && (
        <div className={TA}>
          <SectionHeader title={t('ai.lesions', { n: cur.lesions.length })} isDark={isDark} />
          <div className="mt-2.5 space-y-2">
            {cur.lesions.map((l, i) => (
              <LesionCard
                key={l.lesion_id}
                l={editMode ? editBuf.lesions[i] ?? l : l}
                cancerType={cur.cancer_type}
                editMode={editMode}
                onUpdate={updated => updLesion(i, updated)}
                defaultExpanded={i === 0}
                isDark={isDark}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Differential Diagnosis ── */}
      {(cur.differential_diagnosis.length > 0 || editMode) && (
        <div className={TA}>
          <SectionHeader title={t('ai.differential')} isDark={isDark} />
          {editMode ? (
            <div className="mt-2">
              <p className={clsx('text-[10px] mb-1.5', isDark ? 'text-slate-500' : 'text-slate-400')}>
                One diagnosis per line, most likely first
              </p>
              <EditTextarea
                value={toLines(editBuf.differential_diagnosis)} rows={4} isDark={isDark}
                placeholder="HCC (most likely)&#10;Dysplastic nodule&#10;Metastasis"
                onChange={v => updBuf({ differential_diagnosis: fromLines(v) })} />
            </div>
          ) : (
            <ol className="mt-2.5 space-y-1.5">
              {cur.differential_diagnosis.map((d, i) => (
                <li key={`${d}-${i}`} className="flex gap-2.5 items-start">
                  <span className="text-accent font-mono text-xs font-bold w-4 shrink-0 mt-0.5">{i + 1}.</span>
                  <span className={clsx('text-xs leading-relaxed', isDark ? 'text-slate-300' : 'text-slate-600')}>{d}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* ── Staging ── */}
      {(cur.bclc_stage || cur.vascular_involvement || cur.staging || editMode) && (
        <div className={TA}>
          <SectionHeader title={t('ai.staging')} isDark={isDark} />
          {editMode ? (
            <div className="mt-2 space-y-2">
              {cur.bclc_stage !== undefined && (
                <label className="block space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wide">BCLC Stage</span>
                  <EditInput value={editBuf.bclc_stage ?? ''} isDark={isDark}
                    placeholder="e.g. BCLC-A"
                    onChange={v => updBuf({ bclc_stage: v || null })} />
                </label>
              )}
              <label className="block space-y-1">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide">Staging / TNM</span>
                <EditInput value={editBuf.staging ?? ''} isDark={isDark}
                  placeholder="e.g. cT3N1M0 (Stage IIIB)"
                  onChange={v => updBuf({ staging: v || null })} />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] text-slate-400 uppercase tracking-wide">Vascular Involvement</span>
                <EditInput value={editBuf.vascular_involvement ?? ''} isDark={isDark}
                  placeholder="e.g. No portal vein tumour thrombus"
                  onChange={v => updBuf({ vascular_involvement: v || null })} />
              </label>
            </div>
          ) : (
            <div className={clsx('mt-2.5 border rounded-xl overflow-hidden',
              isDark ? 'bg-slate-800/40 border-white/[0.08]' : 'bg-white/40 border-black/[0.06]')}>
              {cur.bclc_stage && (
                <div className={clsx('flex items-center justify-between px-3 py-2 border-b',
                  isDark ? 'border-white/[0.05]' : 'border-black/[0.04]')}>
                  <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>{t('ai.bclcStage')}</span>
                  <span className="text-sm font-bold text-orange-500 font-mono">{cur.bclc_stage}</span>
                </div>
              )}
              {cur.staging && !cur.bclc_stage && (
                <div className={clsx('flex items-start justify-between gap-4 px-3 py-2',
                  cur.vascular_involvement ? `border-b ${isDark ? 'border-white/[0.05]' : 'border-black/[0.04]'}` : '')}>
                  <span className={clsx('text-xs shrink-0', isDark ? 'text-slate-400' : 'text-slate-500')}>Staging</span>
                  <span className={clsx('text-xs font-mono text-right', isDark ? 'text-slate-200' : 'text-slate-700')}>
                    {cur.staging}
                  </span>
                </div>
              )}
              {cur.vascular_involvement && (
                <div className="flex items-center justify-between px-3 py-2">
                  <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>{t('ai.vascular')}</span>
                  <span className={clsx('text-xs font-mono', isDark ? 'text-slate-200' : 'text-slate-700')}>
                    {cur.vascular_involvement}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Radiomics (view only — computed data) ── */}
      {draft.radiomics_summary && !draft.radiomics_summary.startsWith('Feature extraction unavailable') && (
        <div className={TA}>
          <RadiomicsSection summary={draft.radiomics_summary} isDark={isDark} />
        </div>
      )}

      {/* ── Recommendations ── */}
      {(cur.recommendations.length > 0 || editMode) && (
        <div className={TA}>
          <SectionHeader title={t('ai.recommendations')} isDark={isDark} />
          {editMode ? (
            <div className="mt-2">
              <p className={clsx('text-[10px] mb-1.5', isDark ? 'text-slate-500' : 'text-slate-400')}>
                One recommendation per line
              </p>
              <EditTextarea
                value={toLines(editBuf.recommendations)} rows={5} isDark={isDark}
                placeholder="Multidisciplinary tumour board review&#10;AFP / AFP-L3 serology&#10;Follow-up MRI in 3 months"
                onChange={v => updBuf({ recommendations: fromLines(v) })} />
            </div>
          ) : (
            <ul className="mt-2.5 space-y-1.5">
              {cur.recommendations.map((r, i) => (
                <li key={`${r}-${i}`} className="flex gap-2 items-start">
                  <span className="text-accent shrink-0 mt-0.5 text-xs">&rarr;</span>
                  <span className={clsx('text-xs leading-relaxed', isDark ? 'text-slate-300' : 'text-slate-600')}>{r}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Guideline Citations ── */}
      {(cur.guideline_citations.length > 0 || editMode) && (
        <div className={TA}>
          <SectionHeader title={t('ai.citations')} isDark={isDark} />
          {editMode ? (
            <div className="mt-2">
              <p className={clsx('text-[10px] mb-1.5', isDark ? 'text-slate-500' : 'text-slate-400')}>
                One citation per line
              </p>
              <EditTextarea
                value={toLines(editBuf.guideline_citations)} rows={3} isDark={isDark}
                placeholder="LI-RADS v2024 Section 4.2&#10;AASLD 2023 HCC Guidance §5.1"
                onChange={v => updBuf({ guideline_citations: fromLines(v) })} />
            </div>
          ) : (
            <ul className="mt-2.5 space-y-1">
              {cur.guideline_citations.map(c => (
                <li key={c} className={clsx('text-xs italic', isDark ? 'text-slate-400' : 'text-slate-500')}>[{c}]</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Radiologist Review / Sign-off ── */}
      <div className="space-y-2.5">
        <SectionHeader title={t('ai.radiologistReview')} isDark={isDark} />
        {signOff
          ? <SignOffBadge signOff={signOff} isDark={isDark} />
          : <SignOffForm onSignOff={onSignOff} prefillName={currentUserName} isDark={isDark} />}
      </div>

      {/* ── Export section — appears below sign-off badge when approved ── */}
      {canExport && (
        <div className={clsx('rounded-2xl border p-4 space-y-3',
          isDark ? 'bg-emerald-950/20 border-emerald-800/30' : 'bg-emerald-50/60 border-emerald-200/60')}>
          <p className={clsx('text-[10px] font-semibold uppercase tracking-widest',
            isDark ? 'text-emerald-400' : 'text-emerald-700')}>
            Export Approved Report
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handlePDF}
              disabled={pdfLoading}
              className={clsx(
                'flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all border shadow-sm',
                isDark
                  ? 'bg-emerald-800/60 hover:bg-emerald-700/80 border-emerald-700/50 text-emerald-200 disabled:opacity-40'
                  : 'bg-emerald-600 hover:bg-emerald-500 border-emerald-700/20 text-white disabled:opacity-40',
              )}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              {pdfLoading ? 'Generating…' : 'Download PDF'}
            </button>
            <button
              onClick={handleFhir}
              className={clsx(
                'flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all border shadow-sm',
                isDark
                  ? 'bg-sky-900/50 hover:bg-sky-800/70 border-sky-700/40 text-sky-300'
                  : 'bg-sky-600 hover:bg-sky-500 border-sky-700/20 text-white',
              )}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
              </svg>
              FHIR JSON
            </button>
          </div>
          <p className={clsx('text-[10px] leading-relaxed',
            isDark ? 'text-emerald-400/60' : 'text-emerald-700/60')}>
            PDF includes your edits and the radiologist sign-off.
          </p>
        </div>
      )}

      {/* Disclaimer */}
      <div className={clsx('border rounded-xl p-3 text-xs leading-relaxed',
        isDark ? 'border-amber-900/25 bg-amber-950/15 text-amber-300/50' : 'border-amber-200/60 bg-amber-50/60 text-amber-700/70')}>
        {t('ai.disclaimer')}
      </div>
    </div>
  )
}

// ── RadiomicsSection (unchanged from original, just moved here) ───────────────

function RadiomicsSection({ summary, isDark = false }: { summary: string; isDark?: boolean }) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const lines = summary.split('\n').filter(Boolean)
  return (
    <div className="space-y-2.5">
      <button onClick={() => setExpanded(e => !e)} className="flex items-center justify-between w-full group">
        <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 group-hover:text-slate-500 transition-colors">
          {t('ai.radiomicFeatures')}
        </h3>
        <span className="text-[10px] text-slate-400 group-hover:text-slate-500 transition-colors font-mono">
          {expanded ? t('ai.collapse') : t('ai.featuresCount', { n: lines.length })}
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
