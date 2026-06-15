import clsx from 'clsx'
import { useState } from 'react'
import LiRadsScore from './LiRadsScore'
import { useI18n } from '../i18n'
import type { DiagnosticReport, LesionFinding, SignOff, SignOffDecision } from '../types'

// ── Utilities ─────────────────────────────────────────────────────────────────

export function deepCopy(r: DiagnosticReport): DiagnosticReport {
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

// ── Radiomics section ─────────────────────────────────────────────────────────

export function RadiomicsSection({ summary, isDark = false }: { summary: string; isDark?: boolean }) {
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
        'text-xs whitespace-pre-wrap break-words font-mono rounded-xl px-3 py-2 leading-relaxed border',
        isDark ? 'bg-[#121924] border-[#1f2835] text-slate-400' : 'bg-white border-[#e2e8ee] text-slate-500',
        !expanded && 'italic',
      )}>
        {expanded ? summary : `${lines.slice(0, 3).join('\n')}${lines.length > 3 ? '\n…' : ''}`}
      </pre>
    </div>
  )
}
