import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { pdf } from '@react-pdf/renderer'
import { analysisApi } from '../services/api'
import { useI18n } from '../i18n'
import type { DiagnosticReport, LesionFinding, SignOff, SignOffDecision } from '../types'
import ReportPDF from './ReportPDF'
import LiRadsScore from './LiRadsScore'
import {
  deepCopy, toLines, fromLines,
  SectionHeader, EditTextarea, EditInput,
  LesionCard, SignOffBadge, SignOffForm, RadiomicsSection,
} from './ReportSections'

interface Props {
  report: DiagnosticReport
  jobId: string
  signOff: SignOff | null
  onSignOff: (name: string, decision: SignOffDecision, comments?: string) => Promise<void>
  currentSlice?: string
  isDark?: boolean
  currentUserName?: string
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

  // CNN activation-heatmap overlays (explainability) — fetched when a job exists
  const [overlays, setOverlays] = useState<{ key: string; label: string; image: string }[]>([])
  const [overlayZoom, setOverlayZoom] = useState<string | null>(null)
  useEffect(() => {
    if (!jobId) { setOverlays([]); return }
    analysisApi.overlays(jobId).then(r => setOverlays(r.overlays)).catch(() => setOverlays([]))
  }, [jobId, report.generated_at])

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

  // Primary lesion → reference-style result card (real fields only; no fabricated confidence)
  const primary = cur.lesions[0] ?? null
  const sizeStr = primary?.size_mm != null ? `${(primary.size_mm / 10).toFixed(1)} cm` : '—'
  const enhStr  = primary?.aphe_present === true ? 'Arterial (APHE)' : primary?.aphe_present === false ? 'None' : '—'
  const washStr = primary?.washout_present === true ? 'Present' : primary?.washout_present === false ? 'Absent' : '—'
  const subtitle = primary
    ? (primary.lirads_category && primary.lirads_category !== 'Indeterminate'
        ? `${primary.lirads_category} · primary finding`
        : primary.score_system && primary.score ? `${primary.score_system} ${primary.score} · primary finding` : 'Primary finding')
    : ''

  // ── Shared style helpers ─────────────────────────────────────────────────

  const TA = clsx('border-b pb-3', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')

  return (
    <div className="h-full overflow-y-auto space-y-5 pr-1">

      {/* ── Reference-style result card (real fields only) ── */}
      {primary && (
        <div className={clsx('rounded-2xl border p-4', isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className={clsx('text-base font-semibold leading-tight truncate', isDark ? 'text-white' : 'text-slate-900')}>
                {cur.differential_diagnosis[0] ?? 'Primary finding'}
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">{subtitle}</p>
            </div>
            <LiRadsScore
              category={primary.lirads_category}
              score={primary.score}
              scoreSystem={primary.score_system}
              size="sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-2 mt-3">
            {([
              ['Lesion size', sizeStr],
              ['Location', primary.location_segment ?? '—'],
              ['Enhancement', enhStr],
              ['Washout', washStr],
            ] as [string, string][]).map(([k, v]) => (
              <div key={k} className={clsx('rounded-xl px-3 py-2', isDark ? 'bg-[#0d1219]' : 'bg-slate-50')}>
                <div className="text-[9px] uppercase tracking-wide text-slate-400">{k}</div>
                <div className={clsx('text-sm font-semibold mt-0.5 truncate', isDark ? 'text-slate-100' : 'text-slate-800')}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Header: modality badge + edit toggle + copy ── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('text-[10px] font-mono px-2 py-0.5 rounded-md font-semibold border',
            isDark ? 'bg-[#121924] border-[#1f2835] text-slate-300' : 'bg-white border-[#e2e8ee] text-slate-600')}>
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
                ? 'text-slate-400 hover:text-slate-200 border-[#1f2835]'
                : 'text-slate-500 hover:text-slate-700 border-[#e2e8ee] hover:border-slate-400')}>
            {copied ? t('ai.copied') : t('ai.copy')}
          </button>
          {/* Edit / Save / Cancel */}
          {!signOff && (
            editMode ? (
              <div className="flex items-center gap-1">
                <button onClick={saveEdit}
                  className="text-[10px] px-2.5 py-0.5 rounded-md bg-accent hover:bg-teal-700 text-white font-semibold transition-colors">
                  Save
                </button>
                <button onClick={cancelEdit}
                  className={clsx('text-[10px] px-2 py-0.5 rounded-md border font-mono transition-colors',
                    isDark ? 'border-[#1f2835] text-slate-400 hover:text-slate-200' : 'border-[#e2e8ee] text-slate-500 hover:text-slate-800')}>
                  Cancel
                </button>
              </div>
            ) : (
              <button onClick={enterEdit}
                className={clsx('flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-md border font-semibold transition-colors',
                  isDark ? 'border-[#1f2835] text-slate-300 hover:text-accent hover:border-accent/40'
                         : 'border-[#e2e8ee] text-slate-600 hover:text-accent hover:border-accent/30')}>
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
          {report.model && (
            <span
              title="LLM that produced this report"
              className={clsx('text-[9px] font-mono px-1.5 py-0.5 rounded border',
                isDark ? 'bg-[#121924] border-[#1f2835] text-slate-400' : 'bg-slate-100 border-[#e2e8ee] text-slate-500')}
            >
              {report.model}
            </span>
          )}
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
              {cur.cancer_type === 'liver' && (
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
              {cur.cancer_type === 'liver' && (
                <label className="block space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wide">Vascular Involvement</span>
                  <EditInput value={editBuf.vascular_involvement ?? ''} isDark={isDark}
                    placeholder="e.g. No portal vein tumour thrombus"
                    onChange={v => updBuf({ vascular_involvement: v || null })} />
                </label>
              )}
            </div>
          ) : (
            <div className={clsx('mt-2.5 border rounded-xl overflow-hidden',
              isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
              {cur.bclc_stage && (
                <div className={clsx('flex items-center justify-between px-3 py-2 border-b',
                  isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
                  <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>{t('ai.bclcStage')}</span>
                  <span className="text-sm font-bold text-orange-500 font-mono">{cur.bclc_stage}</span>
                </div>
              )}
              {cur.staging && !cur.bclc_stage && (
                <div className={clsx('flex items-start justify-between gap-4 px-3 py-2',
                  cur.vascular_involvement ? `border-b ${isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]'}` : '')}>
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

      {/* ── CNN attention heatmaps (explainability) ── */}
      {overlays.length > 0 && (
        <div className={TA}>
          <SectionHeader title={t('ai.attention')} isDark={isDark} />
          <p className={clsx('text-[10px] mt-1 mb-2', isDark ? 'text-slate-500' : 'text-slate-400')}>
            {t('ai.attentionHint')}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {overlays.map(o => (
              <button key={o.key} onClick={() => setOverlayZoom(o.image)}
                className={clsx('group rounded-xl overflow-hidden border text-left transition-colors',
                  isDark ? 'border-[#1f2835] hover:border-accent/40' : 'border-[#e2e8ee] hover:border-accent/30')}>
                <img src={`data:image/png;base64,${o.image}`} alt={o.label}
                  className="w-full aspect-square object-cover" />
                <div className={clsx('px-2 py-1 text-[10px] font-mono truncate',
                  isDark ? 'bg-[#121924] text-slate-300' : 'bg-white text-slate-600')}>
                  {o.label}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {overlayZoom && (
        <div onClick={() => setOverlayZoom(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-8 cursor-zoom-out">
          <img src={`data:image/png;base64,${overlayZoom}`} alt="attention heatmap"
            className="max-w-full max-h-full rounded-xl shadow-2xl" />
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

