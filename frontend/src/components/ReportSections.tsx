import clsx from 'clsx'
import { useState } from 'react'
import LiRadsScore from './LiRadsScore'
import { useI18n } from '../i18n'
import type { DiagnosticReport, DifferentialItem, LesionFinding, SignOff, SignOffDecision } from '../types'

// ── Utilities ─────────────────────────────────────────────────────────────────

export function deepCopy(r: DiagnosticReport): DiagnosticReport {
  return {
    ...r,
    lesions: r.lesions.map(l => ({
      ...l,
      abcde: l.abcde ? { ...l.abcde } : null,
      major_features: [...l.major_features],
      ancillary_features: [...l.ancillary_features],
    })),
    differential_diagnosis: [...r.differential_diagnosis],
    differential_assessment: r.differential_assessment?.map(d => ({
      ...d,
      supporting_features: [...d.supporting_features],
      opposing_features:   [...d.opposing_features],
    })),
    recommendations:        [...r.recommendations],
    guideline_citations:    [...r.guideline_citations],
  }
}

export const toLines = (arr: string[]) => arr.join('\n')
export const fromLines = (s: string): string[] => s.split('\n').map(x => x.trim()).filter(Boolean)

// ── Shared presentational atoms ───────────────────────────────────────────────

export function SectionHeader({ title, isDark }: { title: string; isDark: boolean }) {
  return (
    <h3 className={clsx('text-[10px] font-semibold uppercase tracking-widest',
      isDark ? 'text-slate-400' : 'text-slate-500')}>
      {title}
    </h3>
  )
}

export function EditTextarea({
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
          ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-500'
          : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
      )}
    />
  )
}

export function EditInput({
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
          ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-500'
          : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
      )}
    />
  )
}

// ── Lesion card (view + edit) ─────────────────────────────────────────────────

export function LesionCard({
  l, cancerType = 'liver', editMode, onUpdate, defaultExpanded = true, isDark = false,
}: {
  l: LesionFinding; cancerType?: string; editMode: boolean
  onUpdate: (updated: LesionFinding) => void
  defaultExpanded?: boolean; isDark?: boolean
}) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(defaultExpanded)
  const isLiver = cancerType === 'liver'
  const isSkin = cancerType === 'skin'

  const upd = (patch: Partial<LesionFinding>) => onUpdate({ ...l, ...patch })

  const CARD = clsx('border rounded-xl overflow-hidden',
    isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]',
    editMode && (isDark ? 'border-accent/30' : 'border-accent/25'),
  )

  return (
    <div className={CARD}>
      <button
        onClick={() => setExpanded(e => !e)}
        className={clsx('w-full flex flex-col md:flex-row md:items-center justify-between gap-3 px-3.5 py-2.5 transition-colors text-left',
          isDark ? 'hover:bg-[#121924]' : 'hover:bg-slate-100')}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={clsx('font-semibold text-sm font-mono', isDark ? 'text-slate-100' : 'text-slate-800')}>
            {l.lesion_id}
          </span>
          {l.size_mm != null && <span className="text-[10px] text-slate-400 font-mono">{l.size_mm} mm</span>}
          {l.location_segment && <span className="text-[10px] text-slate-400">{l.location_segment}</span>}
          {isSkin && l.dermoscopy_score != null && (
            <span className={clsx('text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded',
              l.dermoscopy_score >= 3 ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-500')}>
              7-pt {l.dermoscopy_score}/7
            </span>
          )}
        </div>
        <div className="flex items-center justify-between w-full md:w-auto gap-2 shrink-0">
          <div className="min-w-0">
            <LiRadsScore category={l.lirads_category} score={l.score} scoreSystem={l.score_system} size="lg" />
          </div>
          <svg className={clsx('w-3.5 h-3.5 text-slate-400 transition-transform shrink-0', expanded && 'rotate-180')}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className={clsx('px-3.5 pb-3.5 space-y-3 border-t',
          isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>

          {editMode ? (
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
                      isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
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
              {isSkin && l.abcde && (
                <div className="space-y-0.5 pt-2">
                  {([
                    ['Asymmetry', l.abcde.A_asymmetry],
                    ['Border',    l.abcde.B_border],
                    ['Colour',    l.abcde.C_color],
                    ['Diameter',  l.abcde.D_diameter],
                    ['Evolution', l.abcde.E_evolution],
                  ] as const).map(([label, val]) => (
                    <div key={label} className={clsx('flex items-center justify-between py-1 border-b last:border-0',
                      isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
                      <span className="text-xs text-slate-400">{label}</span>
                      {val === null || val === undefined
                        ? <span className="text-slate-400 font-mono text-xs">&mdash;</span>
                        : val
                          ? <span className="text-red-400 font-semibold text-xs">{t('ai.yes')}</span>
                          : <span className="text-emerald-500 font-semibold text-xs">{t('ai.no')}</span>}
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
                        <span className="text-accent mt-0.5 shrink-0">&bull;</span><span className="min-w-0 break-words">{f}</span>
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
                        <span className={clsx('mt-0.5 shrink-0', isDark ? 'text-slate-600' : 'text-slate-300')}>&#9702;</span><span className="min-w-0 break-words">{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {l.reasoning && (
                <p className={clsx('text-xs italic border-t pt-2.5 leading-relaxed',
                  isDark ? 'text-slate-400 border-[#1f2835]' : 'text-slate-500 border-[#e2e8ee]')}>
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

export function SignOffBadge({ signOff, isDark = false }: { signOff: SignOff; isDark?: boolean }) {
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
          isDark ? 'text-slate-400 border-[#1f2835]' : 'text-slate-500 border-[#e2e8ee]')}>
          &ldquo;{signOff.comments}&rdquo;
        </p>
      )}
    </div>
  )
}

// ── Sign-off form ─────────────────────────────────────────────────────────────

type OnSignOff = (name: string, decision: SignOffDecision, comments?: string) => Promise<void>

export function SignOffForm({
  onSignOff, prefillName = '', isDark = false,
}: {
  onSignOff: OnSignOff; prefillName?: string; isDark?: boolean
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
    isDark ? 'bg-[#121924] border-[#1f2835] text-slate-200' : 'bg-white border-[#e2e8ee] text-slate-800',
  )

  return (
    <div className={clsx('space-y-3 border rounded-xl p-3.5',
      isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
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
          {loading && decision === 'approved' ? t('ai.saving') : t('ai.approve')}
        </button>
        <button onClick={() => submit('changes_requested')} disabled={!name.trim() || loading}
          className="flex-1 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-sm">
          {loading && decision === 'changes_requested' ? t('ai.saving') : t('ai.requestChanges')}
        </button>
      </div>
    </div>
  )
}

// ── Differential assessment (for / against per diagnosis) ──────────────────────

export function DifferentialAssessment({ items, isDark = false }: {
  items: DifferentialItem[]; isDark?: boolean
}) {
  const badgeFor = (l?: string | null) => {
    switch ((l ?? '').toLowerCase()) {
      case 'high':     return { label: 'High', cls: 'bg-red-500/15 text-red-400' }
      case 'moderate': return { label: 'Moderate', cls: 'bg-amber-500/15 text-amber-500' }
      case 'low':      return { label: 'Low', cls: 'bg-emerald-500/15 text-emerald-500' }
      default:         return null
    }
  }
  return (
    <div className="mt-2.5 space-y-2">
      {items.map((d, i) => {
        const badge = badgeFor(d.likelihood)
        return (
          <div key={`${d.diagnosis}-${i}`} className={clsx('border rounded-xl px-3 py-2.5',
            isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-accent font-mono text-xs font-bold">{i + 1}.</span>
              <span className={clsx('text-xs font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>
                {d.diagnosis}
              </span>
              {badge && (
                <span className={clsx('text-[10px] font-semibold px-1.5 py-0.5 rounded', badge.cls)}>
                  {badge.label}
                </span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5 mt-1.5">
              {d.supporting_features.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-emerald-500/80 mb-0.5">Supports</p>
                  <ul className="space-y-0.5">
                    {d.supporting_features.map((f, j) => (
                      <li key={j} className={clsx('text-xs flex gap-1.5', isDark ? 'text-slate-300' : 'text-slate-600')}>
                        <span className="text-emerald-500 mt-0.5 shrink-0 font-bold">+</span>
                        <span className="min-w-0 break-words">{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {d.opposing_features.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-red-400/80 mb-0.5">Against</p>
                  <ul className="space-y-0.5">
                    {d.opposing_features.map((f, j) => (
                      <li key={j} className={clsx('text-xs flex gap-1.5', isDark ? 'text-slate-400' : 'text-slate-500')}>
                        <span className="text-red-400 mt-0.5 shrink-0 font-bold">−</span>
                        <span className="min-w-0 break-words">{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function EditableDifferential({ items, onChange, isDark = false }: {
  items: DifferentialItem[]; onChange: (items: DifferentialItem[]) => void; isDark?: boolean
}) {
  const update = (idx: number, patch: Partial<DifferentialItem>) =>
    onChange(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  const remove = (idx: number) => onChange(items.filter((_, i) => i !== idx))
  const add = () => onChange([...items,
    { diagnosis: '', likelihood: 'moderate', supporting_features: [], opposing_features: [] }])

  const SELECT = clsx('rounded-lg px-2 py-1.5 text-xs border focus:outline-none focus:border-accent/60 transition-colors',
    isDark ? 'bg-[#121924] border-[#1f2835] text-slate-200' : 'bg-white border-[#e2e8ee] text-slate-800')

  return (
    <div className="mt-2 space-y-2.5">
      {items.map((d, i) => (
        <div key={i} className={clsx('border rounded-xl p-2.5 space-y-2',
          isDark ? 'border-[#1f2835] bg-[#121924]' : 'border-[#e2e8ee] bg-white')}>
          <div className="flex items-center gap-2">
            <span className="text-accent font-mono text-xs font-bold shrink-0">{i + 1}.</span>
            <div className="flex-1 min-w-0">
              <EditInput value={d.diagnosis} isDark={isDark} placeholder="Diagnosis"
                onChange={v => update(i, { diagnosis: v })} />
            </div>
            <select className={SELECT} value={(d.likelihood ?? '').toLowerCase()}
              onChange={e => update(i, { likelihood: e.target.value || null })}>
              <option value="">—</option>
              <option value="high">High</option>
              <option value="moderate">Moderate</option>
              <option value="low">Low</option>
            </select>
            <button onClick={() => remove(i)} title="Remove diagnosis"
              className="text-red-400 text-xs px-1.5 py-1 rounded hover:bg-red-500/10 shrink-0">✕</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wide text-emerald-500/80">Supports (one per line)</span>
              <EditTextarea rows={2} value={toLines(d.supporting_features)} isDark={isDark}
                placeholder="Blue-white veil&#10;Asymmetry in 2 axes"
                onChange={v => update(i, { supporting_features: fromLines(v) })} />
            </label>
            <label className="block space-y-1">
              <span className="text-[10px] uppercase tracking-wide text-red-400/80">Against (one per line)</span>
              <EditTextarea rows={2} value={toLines(d.opposing_features)} isDark={isDark}
                placeholder="No regression structures"
                onChange={v => update(i, { opposing_features: fromLines(v) })} />
            </label>
          </div>
        </div>
      ))}
      <button onClick={add}
        className={clsx('text-xs px-2.5 py-1.5 rounded-lg border border-dashed transition-colors',
          isDark ? 'border-[#2a3441] text-slate-400 hover:text-slate-200'
                 : 'border-[#d8e0ea] text-slate-500 hover:text-slate-700')}>
        + Add diagnosis
      </button>
    </div>
  )
}

// ── Radiomics section ─────────────────────────────────────────────────────────

// The backend ships radiomics as a flat multi-section text blob (derm ABCD/TDS +
// CNN + KNN + trained-classifier summaries). We parse it into typed chunks so it
// can be rendered as friendly metric rows instead of a raw mono dump — and so the
// PDF exporter can reuse the exact same parse.
export type RadiomicChunk =
  // `hint` carries a long parenthetical caveat (e.g. "physical mm not available
  // — no calibration in image") pulled off the value so it no longer bloats the
  // metric row; it renders as a muted sub-line instead.
  | { kind: 'title';   text: string }
  | { kind: 'metric';  label: string; value: string; tag?: string; hint?: string }
  | { kind: 'result';  text: string }
  | { kind: 'warning'; text: string }
  | { kind: 'note';    text: string }
  | { kind: 'text';    text: string }

// ── Plain-language glossary ────────────────────────────────────────────────────
// Short explanations so the panel teaches the reader what each number means rather
// than dumping raw metrics. Shared with the PDF exporter so both stay in sync.
const RADIOMIC_METRIC_HELP: [RegExp, string][] = [
  [/^asymmetry/i,            'How lopsided the lesion is around its centre — a higher % is more asymmetric, a melanoma warning sign.'],
  [/border irregularity/i,   'How ragged the edge is. 1.0 is a smooth circle; higher means a more notched, irregular border.'],
  [/(maximum )?diameter/i,   'Longest width of the lesion. Reported in pixels because the photo carries no real-world scale.'],
  [/colou?r variegation/i,   'Number of distinct colours in the lesion. Three or more colours raises melanoma suspicion.'],
  [/lesion covers/i,         'How much of the photo the lesion fills — a framing check, not a risk factor.'],
  [/predicted class/i,       'Label shared by the most visually similar reference images — a look-alike vote, not a trained diagnosis.'],
  [/nearest neighbou?rs/i,   'The closest reference images and their similarity score (1.00 = identical).'],
  [/most likely/i,           'The single class the trained network scored highest for this lesion.'],
  [/malignancy probability/i,'Combined probability across the cancerous classes (melanoma + BCC + AKIEC).'],
]

const RADIOMIC_SECTION_HELP: [RegExp, string][] = [
  [/stolz|dermoscopy score|abcd/i, 'A scored dermoscopy rule: Asymmetry, Border, Colour and Differential structures are weighted into one TDS number. Above ~5.45 is melanoma-suspicious.'],
  [/knn classification|nearest[- ]neighbou?r/i, "Compares this lesion's deep-learning fingerprint to a labelled image library and takes a vote of the closest matches — similarity-based, not a trained diagnosis."],
  [/ham10000|trained classifier/i, 'A neural network trained on the HAM10000 dermoscopy dataset to sort lesions into 7 diagnostic classes.'],
  [/class probabilit/i, "The network's confidence spread across all classes (totals 100%)."],
]

export function radiomicMetricHelp(label: string): string | undefined {
  return RADIOMIC_METRIC_HELP.find(([re]) => re.test(label))?.[1]
}

export function radiomicSectionHelp(title: string): string | undefined {
  return RADIOMIC_SECTION_HELP.find(([re]) => re.test(title))?.[1]
}

// Qualifier words that signal an elevated / reassuring finding → colour the pill.
const RADIOMIC_ALERT = /(asymmetr|irregular|notched|multi-?colou?r|suspicious|melanoma|elevated|dense|atypical|high)/i
const RADIOMIC_OK    = /(symmetric|smooth|uniform|benign|regular|low|fatty)/i

export function radiomicTagTone(tag: string): 'alert' | 'ok' | 'neutral' {
  if (RADIOMIC_ALERT.test(tag)) return 'alert'
  if (RADIOMIC_OK.test(tag)) return 'ok'
  return 'neutral'
}

export function parseRadiomics(summary: string): RadiomicChunk[] {
  const out: RadiomicChunk[] = []
  const pushMetric = (piece: string) => {
    // A conclusion line (e.g. "TDS = 8.60 → highly suspicious") can arrive inside a
    // "•"-bullet group; surface it as a prominent result, not a hidden text line.
    if (/→|->/.test(piece)) { out.push({ kind: 'result', text: piece.replace(/->/g, '→') }); return }
    // A trailing-colon fragment (e.g. "Class probabilities:") is a sub-heading.
    if (piece.endsWith(':')) { out.push({ kind: 'title', text: piece.replace(/:$/, '').trim() }); return }
    const m = piece.match(/^(.+?):\s*(.+)$/)
    if (!m) { out.push({ kind: 'text', text: piece }); return }
    let value = m[2].trim()
    let tag: string | undefined
    let hint: string | undefined
    // Pull a SINGLE trailing "(…)" off the value. A short qualifier becomes a pill;
    // a longer note (or one with an em-dash) becomes a hint sub-line. The
    // `!qm[1].includes('(')` guard stops us from grabbing the last item of a list
    // like "benign (0.89), …, malignant (0.83)" and mistaking it for a qualifier.
    const qm = value.match(/^(.*?)\s*\(([^()]+)\)\s*$/)
    if (qm && qm[1].trim() && !qm[1].includes('(')) {
      const paren = qm[2].trim()
      value = qm[1].trim()
      if (paren.length <= 22 && !paren.includes('—')) tag = paren
      else hint = paren
    }
    out.push({ kind: 'metric', label: m[1].trim(), value, tag, hint })
  }

  for (const raw of summary.split('\n')) {
    let line = raw.trim()
    if (!line) continue
    if (line.includes('⚠')) { out.push({ kind: 'warning', text: line.replace(/[•⚠]/g, '').trim() }); continue }
    if (/^NOTE\b[:\s]*/i.test(line)) { out.push({ kind: 'note', text: line.replace(/^NOTE\b[:\s]*/i, '').trim() }); continue }
    // Normalise a leading "- " bullet so it parses like a "•" metric.
    if (/^[-–]\s+/.test(line)) line = '• ' + line.replace(/^[-–]\s+/, '')
    if (line.includes('•')) {
      line.split('•').map(p => p.trim()).filter(Boolean).forEach(pushMetric)
      continue
    }
    if (/→|->/.test(line)) { out.push({ kind: 'result', text: line.replace(/->/g, '→') }); continue }
    if (/^\(.*\)$/.test(line)) { out.push({ kind: 'note', text: line.replace(/^\(|\)$/g, '').trim() }); continue }
    if (line.endsWith(':')) { out.push({ kind: 'title', text: line.replace(/:$/, '').trim() }); continue }
    out.push({ kind: 'text', text: line })
  }
  return out
}

export function RadiomicsSection({ summary, isDark = false }: { summary: string; isDark?: boolean }) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const chunks = parseRadiomics(summary)
  const metricCount = chunks.filter(c => c.kind === 'metric').length
  // Collapsed view keeps the meaningful numbers; notes/legends/prose hide until expanded.
  const visible = expanded ? chunks : chunks.filter(c => c.kind !== 'note' && c.kind !== 'text')

  const pillTone = (tag: string) => {
    const tone = radiomicTagTone(tag)
    return tone === 'alert' ? 'bg-red-500/15 text-red-400'
      : tone === 'ok'       ? 'bg-emerald-500/15 text-emerald-500'
      :                       (isDark ? 'bg-slate-700/40 text-slate-300' : 'bg-slate-200/70 text-slate-600')
  }

  return (
    <div className="space-y-2.5">
      <button onClick={() => setExpanded(e => !e)} className="flex items-center justify-between w-full group">
        <h3 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 group-hover:text-slate-500 transition-colors">
          {t('ai.radiomicFeatures')}
        </h3>
        <span className="text-[10px] text-slate-400 group-hover:text-slate-500 transition-colors font-mono">
          {expanded ? t('ai.collapse') : t('ai.featuresCount', { n: metricCount })}
        </span>
      </button>

      <div className={clsx('rounded-xl border divide-y',
        isDark ? 'bg-[#121924] border-[#1f2835] divide-[#1f2835]' : 'bg-white border-[#e2e8ee] divide-[#eef2f7]')}>
        {visible.map((c, i) => {
          if (c.kind === 'title') {
            const help = radiomicSectionHelp(c.text)
            return (
              <div key={i} className="px-3 pt-2.5 pb-1.5">
                <div className={clsx('text-[10px] font-semibold uppercase tracking-wider',
                  isDark ? 'text-slate-300' : 'text-slate-500')}>
                  {c.text}
                </div>
                {help && (
                  <p className={clsx('text-[10px] mt-1 leading-snug', isDark ? 'text-slate-500' : 'text-slate-400')}>
                    {help}
                  </p>
                )}
              </div>
            )
          }
          if (c.kind === 'metric') {
            const help = radiomicMetricHelp(c.label)
            // Long values (the KNN neighbour list, multi-word measurements) stack
            // under the label instead of fighting it for room — this is what used
            // to collapse the label to zero width and wrap it one letter per line.
            const stacked = c.value.length > 30 // px-free heuristic; tuned for the panel width
            return (
              <div key={i} className="px-3 py-2">
                {stacked ? (
                  <>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>{c.label}</span>
                      {c.tag && <span className={clsx('text-[9px] font-medium px-1.5 py-0.5 rounded', pillTone(c.tag))}>{c.tag}</span>}
                    </div>
                    <p className={clsx('text-xs font-semibold font-mono mt-1 break-words leading-relaxed',
                      isDark ? 'text-slate-100' : 'text-slate-800')}>{c.value}</p>
                  </>
                ) : (
                  <div className="flex items-baseline justify-between gap-3">
                    <span className={clsx('text-xs shrink-0', isDark ? 'text-slate-400' : 'text-slate-500')}>{c.label}</span>
                    <span className="flex items-center gap-1.5 min-w-0 justify-end">
                      <span className={clsx('text-xs font-semibold font-mono text-right break-words',
                        isDark ? 'text-slate-100' : 'text-slate-800')}>{c.value}</span>
                      {c.tag && <span className={clsx('text-[9px] font-medium px-1.5 py-0.5 rounded shrink-0', pillTone(c.tag))}>{c.tag}</span>}
                    </span>
                  </div>
                )}
                {c.hint && (
                  <p className={clsx('text-[10px] mt-1 leading-snug', isDark ? 'text-slate-500' : 'text-slate-400')}>{c.hint}</p>
                )}
                {help && (
                  <p className={clsx('text-[10px] mt-1 leading-snug italic', isDark ? 'text-slate-500' : 'text-slate-400')}>{help}</p>
                )}
              </div>
            )
          }
          if (c.kind === 'result') {
            const tone = radiomicTagTone(c.text)
            return (
              <div key={i} className={clsx('px-3 py-2 text-xs font-semibold',
                tone === 'alert' ? 'bg-red-500/10 text-red-400'
                  : tone === 'ok' ? 'bg-emerald-500/10 text-emerald-500'
                  : isDark ? 'bg-[#0d1219] text-slate-200' : 'bg-slate-50 text-slate-700')}>
                {c.text}
              </div>
            )
          }
          if (c.kind === 'warning') return (
            <div key={i} className="px-3 py-2 text-xs text-amber-500 font-medium flex gap-1.5">
              <span className="shrink-0">⚠</span><span className="min-w-0 break-words">{c.text}</span>
            </div>
          )
          if (c.kind === 'note') return (
            <div key={i} className={clsx('px-3 py-1.5 text-[10px] italic leading-relaxed', isDark ? 'text-slate-500' : 'text-slate-400')}>
              {c.text}
            </div>
          )
          return (
            <div key={i} className={clsx('px-3 py-1.5 text-[11px] leading-relaxed', isDark ? 'text-slate-400' : 'text-slate-500')}>
              {c.text}
            </div>
          )
        })}
      </div>
    </div>
  )
}
