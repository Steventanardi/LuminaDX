import clsx from 'clsx'
import ProgressTracker from './ProgressTracker'
import UploadPanel from './UploadPanel'
import { useI18n } from '../i18n'
import type { AnalysisJob, CancerType, FeatureCatalog, ModelCatalog, PatientContext, UploadResponse } from '../types'
import { CANCER_TYPE_META } from '../types'

function StepBadge({ n, done, active }: { n: number; done: boolean; active: boolean }) {
  return (
    <div className={clsx(
      'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all duration-300',
      done ? 'bg-emerald-500 text-white' : active ? 'bg-accent text-white ring-2 ring-accent/25' : 'bg-slate-200/90 dark:bg-slate-700 text-slate-400 dark:text-slate-500',
    )}>
      {done ? '✓' : n}
    </div>
  )
}

interface Props {
  uploaded: boolean
  upload: UploadResponse | null
  cancerType: CancerType
  ctx: PatientContext
  job: AnalysisJob | null
  ragStatus: { chunks: number; pdf_count: number } | null
  modelCatalog: ModelCatalog | null
  selectedModel: string | null
  featureCatalog: FeatureCatalog | null
  selectedFeatures: string[]
  isRunning: boolean
  isDone: boolean
  hasCtx: boolean
  isDark: boolean
  onCancerTypeChange: (ct: CancerType) => void
  onUploaded: (res: UploadResponse) => void
  onReset: () => void
  onAnalyse: () => void
  onCtxChange: (patch: Partial<PatientContext>) => void
  onModelChange: (model: string) => void
  onFeaturesChange: (features: string[]) => void
}

export default function WorkflowPanel({
  uploaded, upload, cancerType, ctx, job, ragStatus,
  modelCatalog, selectedModel, featureCatalog, selectedFeatures,
  isRunning, isDone, hasCtx, isDark,
  onCancerTypeChange, onUploaded, onReset, onAnalyse, onCtxChange,
  onModelChange, onFeaturesChange,
}: Props) {
  const { t } = useI18n()

  const INPUT = clsx(
    'w-full rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-accent/50 transition-colors font-mono border',
    isDark
      ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-600'
      : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
  )

  return (
    <div className="flex-1 p-4 space-y-5 overflow-y-auto">

      {/* Cancer type selector (pre-upload) */}
      {!uploaded && (
        <div className="space-y-2.5">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Cancer Type</span>
          <div className="grid grid-cols-2 gap-1.5">
            {(Object.keys(CANCER_TYPE_META) as CancerType[]).map(ct => {
              const m = CANCER_TYPE_META[ct]
              return (
                <button
                  key={ct}
                  onClick={() => onCancerTypeChange(ct)}
                  className={clsx(
                    'flex items-center gap-1.5 px-2.5 py-2 rounded-xl text-xs font-medium transition-all border',
                    cancerType === ct
                      ? 'bg-accent text-white border-accent/50 shadow-sm shadow-accent/25'
                      : isDark
                        ? 'bg-[#121924] text-slate-400 border-[#1f2835] hover:border-accent/40 hover:text-slate-200'
                        : 'bg-white text-slate-500 border-[#e2e8ee] hover:border-accent/30 hover:text-slate-700',
                  )}
                >
                  <span>{m.icon}</span>
                  <span>{m.label}</span>
                </button>
              )
            })}
          </div>
          <p className={clsx('text-[10px]', isDark ? 'text-slate-600' : 'text-slate-400')}>
            {CANCER_TYPE_META[cancerType]?.scoreSystem} scoring
          </p>
        </div>
      )}

      {/* Step 1 */}
      <div className="space-y-3">
        <div className="flex items-center gap-2.5">
          <StepBadge n={1} done={uploaded} active={!uploaded} />
          <span className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{t('step.upload')}</span>
        </div>
        <div className="pl-8">
          {!uploaded ? (
            <UploadPanel onUploaded={onUploaded} cancerType={cancerType} isDark={isDark} />
          ) : (
            <div className="space-y-2">
              <div className={clsx('rounded-xl p-3 space-y-2 border', isDark ? 'border-emerald-800/30 bg-emerald-950/20' : 'border-emerald-200/80 bg-emerald-50/70')}>
                <div className="flex items-center justify-between">
                  <span className={clsx('text-xs font-semibold', isDark ? 'text-emerald-400' : 'text-emerald-700')}>{t('step.studyLoaded')}</span>
                  <button onClick={onReset} className="text-[10px] text-slate-400 hover:text-slate-500 transition-colors underline underline-offset-2">{t('step.reset')}</button>
                </div>
                <div className="text-[10px] font-mono space-y-1">
                  {[[t('field.modality'), upload?.modality ?? '—'], [t('field.files'), upload?.num_files], [t('field.series'), upload?.series.length]].map(([k, v]) => (
                    <div key={String(k)} className="flex justify-between">
                      <span className="text-slate-400">{k}</span>
                      <span className={isDark ? 'text-slate-200' : 'text-slate-700'}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Post-upload cancer type override */}
              <div className="space-y-1.5">
                <span className={clsx('text-[10px] font-semibold uppercase tracking-widest', isDark ? 'text-slate-500' : 'text-slate-400')}>Cancer Type</span>
                <div className="grid grid-cols-2 gap-1">
                  {(Object.keys(CANCER_TYPE_META) as CancerType[]).map(ct => {
                    const m = CANCER_TYPE_META[ct]
                    return (
                      <button
                        key={ct}
                        onClick={() => onCancerTypeChange(ct)}
                        disabled={isRunning}
                        className={clsx(
                          'flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-all border disabled:opacity-40 disabled:cursor-not-allowed',
                          cancerType === ct
                            ? 'bg-accent text-white border-accent/50 shadow-sm shadow-accent/25'
                            : isDark
                              ? 'bg-[#121924] text-slate-400 border-[#1f2835] hover:border-accent/40 hover:text-slate-200'
                              : 'bg-white text-slate-500 border-[#e2e8ee] hover:border-accent/30 hover:text-slate-700',
                        )}
                      >
                        <span>{m.icon}</span>
                        <span>{m.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Step 2 */}
      <div className={clsx('space-y-3 transition-opacity duration-300', !uploaded && 'opacity-30 pointer-events-none')}>
        <div className="flex items-center gap-2.5">
          <StepBadge n={2} done={hasCtx} active={uploaded && !hasCtx} />
          <span className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{t('step.context')}</span>
          <span className="text-[10px] text-slate-400 ml-auto">{t('step.optional')}</span>
        </div>
        {uploaded && (
          <div className="pl-8 space-y-2.5">
            {cancerType === 'liver' && (<>
              <div className="flex flex-wrap gap-1.5">
                {(['cirrhosis', 'hepatitis_b', 'hepatitis_c', 'prior_hcc'] as const).map(key => {
                  const labelKey = { cirrhosis: 'ctx.cirrhosis', hepatitis_b: 'ctx.hepatitis_b', hepatitis_c: 'ctx.hepatitis_c', prior_hcc: 'ctx.prior_hcc' } as const
                  return (
                    <button key={key} onClick={() => onCtxChange({ [key]: !ctx[key] })}
                      className={clsx('px-2.5 py-1 rounded-full text-xs font-medium transition-all',
                        ctx[key] ? 'bg-accent text-white shadow-sm shadow-accent/25'
                          : isDark ? 'bg-[#121924] text-slate-500 border border-[#1f2835] hover:border-accent/40 hover:text-slate-300'
                          : 'bg-white text-slate-500 border border-[#e2e8ee] hover:border-accent/30 hover:text-slate-700')}>
                      {t(labelKey[key])}
                    </button>
                  )
                })}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 shrink-0">{t('ctx.afp')}</span>
                <div className="relative flex-1">
                  <input type="number" value={ctx.afp_level ?? ''}
                    onChange={e => onCtxChange({ afp_level: e.target.value ? Number(e.target.value) : null })}
                    placeholder="—" className={clsx(INPUT, 'pl-2.5 pr-10')} />
                  <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-slate-400 pointer-events-none">{t('ctx.afpUnit')}</span>
                </div>
              </div>
            </>)}
            <textarea value={ctx.notes} onChange={e => onCtxChange({ notes: e.target.value })}
              rows={2} placeholder={t('ctx.notes')}
              className={clsx(INPUT.replace('font-mono', 'resize-none'), 'px-2.5 py-1.5')} />
          </div>
        )}
      </div>

      {/* Step 3 */}
      <div className={clsx('space-y-3 transition-opacity duration-300', !uploaded && 'opacity-30 pointer-events-none')}>
        <div className="flex items-center gap-2.5">
          <StepBadge n={3} done={isDone} active={uploaded && !isDone} />
          <span className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{t('step.run')}</span>
        </div>
        {uploaded && (
          <div className="pl-8 space-y-2.5">
            {modelCatalog?.[cancerType] && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{t('step.model')}</span>
                  {selectedModel === modelCatalog[cancerType].default && (
                    <span className="text-[9px] text-slate-500">{t('step.modelRecommended')}</span>
                  )}
                </div>
                <select
                  value={selectedModel ?? modelCatalog[cancerType].default}
                  onChange={e => onModelChange(e.target.value)}
                  disabled={isRunning}
                  style={{ colorScheme: isDark ? 'dark' : 'light' }}
                  className={clsx('w-full rounded-lg px-2.5 py-2 text-xs font-mono border focus:outline-none focus:border-accent/50 transition-colors disabled:opacity-50',
                    isDark ? 'bg-slate-800 border-[#1f2835] text-slate-100' : 'bg-white border-[#e2e8ee] text-slate-800')}
                >
                  {modelCatalog[cancerType].options.map(m => (
                    <option key={m.tag} value={m.tag}
                      style={{ backgroundColor: isDark ? '#1e293b' : '#ffffff', color: isDark ? '#f1f5f9' : '#1e293b' }}>
                      {m.label}{m.tag === modelCatalog[cancerType].default ? '  ★' : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {featureCatalog?.[cancerType] && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{t('step.features')}</span>
                <div className="space-y-1">
                  {featureCatalog[cancerType].options.map(f => {
                    const on = selectedFeatures.includes(f.key)
                    return (
                      <label key={f.key}
                        className={clsx('flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs cursor-pointer border transition-colors',
                          isRunning && 'opacity-50 cursor-not-allowed',
                          on
                            ? 'border-accent/40 bg-accent/10 text-accent'
                            : isDark ? 'border-[#1f2835] text-slate-300 hover:bg-[#121924]' : 'border-[#e2e8ee] text-slate-600 hover:bg-slate-100')}>
                        <input type="checkbox" checked={on} disabled={isRunning}
                          onChange={() => onFeaturesChange(
                            on ? selectedFeatures.filter(k => k !== f.key) : [...selectedFeatures, f.key],
                          )}
                          className="accent-accent w-3.5 h-3.5 shrink-0" />
                        <span className="flex-1">{f.label}</span>
                        {f.group === 'cnn' && (
                          <span className="text-[8px] font-semibold uppercase tracking-wider px-1 py-0.5 rounded bg-indigo-500/15 text-indigo-400">CNN</span>
                        )}
                        {f.group === 'classifier' && (
                          <span className="text-[8px] font-semibold uppercase tracking-wider px-1 py-0.5 rounded bg-amber-500/15 text-amber-500">KNN</span>
                        )}
                      </label>
                    )
                  })}
                </div>
              </div>
            )}
            <button onClick={onAnalyse} disabled={isRunning}
              className={clsx('w-full py-2.5 rounded-xl font-semibold text-sm transition-all duration-200',
                isRunning ? 'bg-accent/15 text-accent/60 cursor-not-allowed'
                  : isDone
                    ? isDark ? 'bg-[#121924] border border-[#1f2835] text-slate-400 hover:border-accent/40 hover:text-accent' : 'bg-white border border-[#e2e8ee] text-slate-500 hover:border-accent/30 hover:text-accent'
                    : 'bg-accent hover:bg-teal-700 active:bg-teal-800 text-white shadow-lg shadow-teal-900/20')}>
              {isRunning ? t('run.analysing') : isDone ? t('run.again') : t('run.start')}
            </button>
          </div>
        )}
      </div>

      {/* Progress */}
      {job && (
        <div className={clsx('pt-4 space-y-2 border-t', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
          <ProgressTracker job={job} isDark={isDark} />
          {job.status === 'failed' && job.error && (
            <div className={clsx('rounded-xl p-3 space-y-1 border', isDark ? 'bg-red-950/30 border-red-900/30' : 'bg-red-50/80 border-red-200/70')}>
              <p className={clsx('text-xs font-semibold', isDark ? 'text-red-400' : 'text-red-600')}>{t('run.failed')}</p>
              <p className={clsx('text-[10px] font-mono leading-relaxed break-words', isDark ? 'text-red-400/70' : 'text-red-500')}>{job.error}</p>
              <button onClick={onReset} className={clsx('text-[10px] underline underline-offset-2 transition-colors', isDark ? 'text-red-400 hover:text-red-300' : 'text-red-500 hover:text-red-700')}>{t('step.reset')}</button>
            </div>
          )}
        </div>
      )}

      {ragStatus && ragStatus.chunks === 0 && (
        <div className={clsx('rounded-xl p-3 text-xs space-y-1 border', isDark ? 'bg-amber-950/30 border-amber-900/30' : 'bg-amber-50/80 border-amber-200/60')}>
          <p className={clsx('font-semibold', isDark ? 'text-amber-400/90' : 'text-amber-700')}>{t('rag.noneTitle')}</p>
          <p className={clsx('leading-relaxed text-[10px]', isDark ? 'text-amber-400/60' : 'text-amber-600/80')}>
            {t('rag.noneBody').split('{path}')[0]}
            <code className={clsx('font-mono', isDark ? 'text-amber-300/80' : 'text-amber-600')}>backend/data/knowledge_base/</code>
            {t('rag.noneBody').split('{path}')[1]}
          </p>
        </div>
      )}
    </div>
  )
}
