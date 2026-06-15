import clsx from 'clsx'
import { useCallback, useEffect, useRef, useState } from 'react'
import AdminDashboard from './components/AdminDashboard'
import AIReportPanel from './components/AIReportPanel'
import DicomViewer from './components/DicomViewer'
import HistoryPanel from './components/HistoryPanel'
import LiRadsScore from './components/LiRadsScore'
import LoginScreen from './components/LoginScreen'
import ProgressTracker from './components/ProgressTracker'
import Toast from './components/Toast'
import UploadPanel from './components/UploadPanel'
import WorkflowPanel from './components/WorkflowPanel'
import { useAuth } from './context/AuthContext'
import { useAnalysis } from './hooks/useAnalysis'
import { analysisApi, dicomApi, ragApi } from './services/api'
import { useI18n } from './i18n'
import type { TKey } from './i18n'
import type { CancerType, FeatureCatalog, ModelCatalog, PatientContext, UploadResponse } from './types'
import { CANCER_TYPE_META } from './types'

const DEFAULT_CTX: PatientContext = {
  cirrhosis: false, hepatitis_b: false, hepatitis_c: false,
  afp_level: null, prior_hcc: false, notes: '',
}

const APP_SHORTCUTS: [string, TKey][] = [
  ['T', 'sc.theme'],
  ['Space', 'sc.run'],
  ['[', 'sc.left'],
  [']', 'sc.right'],
  ['?', 'sc.list'],
  ['Esc', 'sc.esc'],
]


export default function App() {
  const { t, lang, toggle: toggleLang } = useI18n()
  const { user, loading: authLoading, logout } = useAuth()
  const { job, slices, rawSlices, report, start, signOff, reset } = useAnalysis()
  const [upload, setUpload]               = useState<UploadResponse | null>(null)
  const [cancerType, setCancerType]       = useState<CancerType>('liver')
  const [modelCatalog, setModelCatalog]   = useState<ModelCatalog | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [featureCatalog, setFeatureCatalog] = useState<FeatureCatalog | null>(null)
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([])
  const [ctx, setCtx]                     = useState<PatientContext>(DEFAULT_CTX)
  const [previewSlices, setPreviewSlices] = useState<string[]>([])
  const [ragStatus, setRagStatus]         = useState<{ chunks: number; pdf_count: number } | null>(null)
  const [ragLoading, setRagLoading]       = useState(false)
  const [showRaw, setShowRaw]             = useState(false)
  const [showHistory, setShowHistory]     = useState(false)
  const [showAdmin, setShowAdmin]         = useState(false)
  const [showSettings, setShowSettings]   = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [leftOpen, setLeftOpen]           = useState(true)
  const [rightOpen, setRightOpen]         = useState(true)
  const [leftWidth, setLeftWidth]         = useState(288)
  const [rightWidth, setRightWidth]       = useState(() => Number(localStorage.getItem('v2-right-width')) || 480)
  const [isResizing, setIsResizing]       = useState(false)
  const [isDark, setIsDark]               = useState(() => localStorage.getItem('v2-theme') !== 'light')
  const [toast, setToast]                 = useState<{ message: string; type: 'success' | 'info' | 'error' } | null>(null)

  const settingsRef     = useRef<HTMLDivElement>(null)
  const prevJobStatus   = useRef<string | null>(null)

  // Derived state — declared early so useEffects can reference them
  const isRunning = !!job && !['complete', 'failed'].includes(job.status)
  const isDone    = job?.status === 'complete'
  const uploaded  = !!upload
  const hasCtx    = ctx.cirrhosis || ctx.hepatitis_b || ctx.hepatitis_c || ctx.prior_hcc ||
                    ctx.afp_level !== null || ctx.notes.trim() !== ''

  useEffect(() => { ragApi.status().then(setRagStatus).catch(() => null) }, [])
  useEffect(() => { analysisApi.models().then(setModelCatalog).catch(() => null) }, [])
  useEffect(() => { analysisApi.features().then(setFeatureCatalog).catch(() => null) }, [])
  useEffect(() => { localStorage.setItem('v2-theme', isDark ? 'dark' : 'light') }, [isDark])
  useEffect(() => { localStorage.setItem('v2-right-width', String(rightWidth)) }, [rightWidth])

  // Default the model to the current cancer's recommended model whenever the
  // cancer type changes (or once the catalog loads).
  useEffect(() => {
    if (modelCatalog?.[cancerType]) setSelectedModel(modelCatalog[cancerType].default)
  }, [cancerType, modelCatalog])

  // Default the selected features to the current cancer's defaults.
  useEffect(() => {
    if (featureCatalog?.[cancerType]) setSelectedFeatures(featureCatalog[cancerType].defaults)
  }, [cancerType, featureCatalog])

  // Toast on analysis complete
  useEffect(() => {
    if (job?.status === 'complete' && prevJobStatus.current !== 'complete') {
      setToast({ message: t('toast.complete'), type: 'success' })
    }
    if (job?.status === 'failed' && prevJobStatus.current !== 'failed') {
      setToast({ message: t('toast.failed'), type: 'error' })
    }
    prevJobStatus.current = job?.status ?? null
  }, [job?.status, t])

  // Close settings on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node))
        setShowSettings(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleUploaded = (res: UploadResponse) => {
    setUpload(res)
    setPreviewSlices([])
    dicomApi.preview(res.study_id, res.num_files).then(r => setPreviewSlices(r.slices)).catch(() => null)
  }
  const handleCancerTypeChange = useCallback(async (ct: CancerType) => {
    setCancerType(ct)
    if (upload) {
      dicomApi.updateCancerType(upload.study_id, ct).catch(() => null)
    }
  }, [upload])
  const handleAnalyse   = useCallback(async () => { if (upload) await start(upload.study_id, ctx, selectedModel ?? undefined, selectedFeatures) }, [upload, ctx, selectedModel, selectedFeatures, start])
  const handleReset     = () => { setUpload(null); setCtx(DEFAULT_CTX); setPreviewSlices([]); setShowRaw(false); reset() }
  const handleLogout    = async () => { await logout() }
  const handleIngestRag = async () => {
    setRagLoading(true); setShowSettings(false)
    try { await ragApi.ingest(); setTimeout(() => ragApi.status().then(setRagStatus), 3000) }
    finally { setRagLoading(false) }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
      if (e.key === 't' || e.key === 'T') setIsDark(d => !d)
      if (e.key === '?') setShowShortcuts(s => !s)
      if (e.key === 'Escape') { setShowShortcuts(false); setShowSettings(false) }
      if (e.key === '[') setLeftOpen(o => !o)
      if (e.key === ']') setRightOpen(o => !o)
      if (e.key === ' ' && uploaded && !isRunning) { e.preventDefault(); handleAnalyse() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [uploaded, isRunning, handleAnalyse])

  // Panel resize
  const startLeftResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX; const startW = leftWidth
    setIsResizing(true)
    const onMove = (ev: MouseEvent) => setLeftWidth(Math.max(200, Math.min(520, startW + ev.clientX - startX)))
    const onUp = () => { setIsResizing(false); document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [leftWidth])

  const startRightResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX; const startW = rightWidth
    setIsResizing(true)
    const onMove = (ev: MouseEvent) => setRightWidth(Math.max(320, Math.min(820, startW + startX - ev.clientX)))
    const onUp = () => { setIsResizing(false); document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [rightWidth])

  const GLASS = clsx('border', isDark
    ? 'bg-[#10151d] border-[#1f2835] shadow-sm shadow-black/30'
    : 'bg-white border-[#e2e8ee] shadow-sm shadow-slate-200/50')

const PANEL_BTN = clsx('w-8 h-8 rounded-lg border flex items-center justify-center transition-colors shadow-sm', isDark
    ? 'bg-[#121924] hover:bg-[#1a2230] border-[#1f2835] text-slate-400 hover:text-accent'
    : 'bg-white hover:bg-slate-100 border-[#e2e8ee] text-slate-500 hover:text-accent')

  // Auth gate — must be after all hook calls
  if (authLoading) {
    return (
      <div className={clsx('h-screen flex items-center justify-center', isDark ? 'bg-[#0a0e14]' : 'bg-surface')}>
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!user) return <LoginScreen isDark={isDark} />

  return (
    <div className={clsx('h-screen flex flex-col overflow-hidden font-sans select-none', isDark ? 'dark bg-[#0a0e14] text-slate-200' : 'bg-surface text-slate-800', isResizing && 'cursor-col-resize')}>

      {/* Calm flat background — animated blobs removed for clinical reading */}

      {/* ── Glass header ── */}
      <header className={clsx('relative z-40 border-b flex items-center justify-between px-5 py-3 shrink-0',
        isDark ? 'bg-[#0d1219] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
        {/* Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className={clsx('w-8 h-8 rounded-xl border flex items-center justify-center shrink-0', isDark ? 'bg-accent/15 border-accent/25' : 'bg-accent/10 border-accent/20')}>
            <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
            </svg>
          </div>
          <div>
            <h1 className={clsx('text-sm font-semibold leading-tight flex items-center gap-1.5', isDark ? 'text-white' : 'text-slate-900')}>
              LuminaDx
              <span className="text-[10px] font-normal text-slate-500 ml-0.5">v2</span>
              {cancerType !== 'liver' && (
                <span className="text-[10px] font-medium text-accent">{CANCER_TYPE_META[cancerType]?.icon} {CANCER_TYPE_META[cancerType]?.label}</span>
              )}
            </h1>
            <p className="text-[10px] text-slate-400 leading-tight hidden sm:block">{t('header.subtitle', { system: cancerType === 'liver' ? 'LI-RADS v2024' : (CANCER_TYPE_META[cancerType]?.scoreSystem ?? 'Multi-RADS') })}</p>
          </div>
          {uploaded && upload && (
            <div className={clsx('hidden xl:flex items-center gap-2.5 text-[11px] text-slate-400 pl-3 ml-1 border-l', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
              <span>Case <b className={clsx('font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>#{upload.study_id.slice(0, 8)}</b></span>
              {upload.modality && <span>· <b className={clsx('font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{upload.modality}</b></span>}
              {(report?.model || selectedModel) && <span>· <b className={clsx('font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{report?.model || selectedModel}</b></span>}
            </div>
          )}
        </div>

        {/* LI-RADS badge — shows when analysis is done */}
        {isDone && report?.lesions?.[0] && (
          <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-full border hidden md:flex',
            isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
            <span className="text-[10px] text-slate-400">{t('header.topFinding')}</span>
            <LiRadsScore
              category={report.lesions[0].lirads_category}
              score={report.lesions[0].score}
              scoreSystem={report.lesions[0].score_system}
              size="sm"
            />
            {report.bclc_stage && (
              <span className={clsx('text-xs font-bold font-mono', isDark ? 'text-orange-300' : 'text-orange-600')}>
                BCLC-{report.bclc_stage}
              </span>
            )}
          </div>
        )}

        {/* Right actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* New Analysis — appears once a study is loaded; fully clears state */}
          {uploaded && (
            <button
              onClick={handleReset}
              disabled={isRunning}
              title={t('header.newAnalysisTitle')}
              className={clsx(
                'flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-semibold border transition-colors shadow-sm disabled:opacity-40 disabled:cursor-not-allowed',
                isDark
                  ? 'bg-accent/15 border-accent/30 text-accent hover:bg-accent/25'
                  : 'bg-accent/10 border-accent/25 text-accent hover:bg-accent/20',
              )}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              <span className="hidden sm:inline">{t('header.newAnalysis')}</span>
            </button>
          )}

          {/* Language toggle (EN / 繁中) */}
          <button
            onClick={toggleLang}
            title={t('lang.title')}
            aria-label={t('lang.title')}
            className={clsx('px-2.5 h-8 rounded-lg border text-xs font-semibold transition-colors shadow-sm shrink-0',
              isDark
                ? 'bg-[#121924] hover:bg-[#1a2230] border-[#1f2835] text-slate-300 hover:text-accent'
                : 'bg-white hover:bg-slate-100 border-[#e2e8ee] text-slate-600 hover:text-accent')}
          >
            {lang === 'en' ? 'EN' : '繁中'}
          </button>

          {ragStatus && (
            <div className={clsx('flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border hidden sm:flex',
              ragStatus.pdf_count > 0
                ? isDark ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : isDark ? 'bg-amber-950/60 text-amber-400 border-amber-800/40' : 'bg-amber-50 text-amber-700 border-amber-200')}>
              <span className={clsx('w-1.5 h-1.5 rounded-full', ragStatus.pdf_count > 0 ? 'bg-emerald-500' : 'bg-amber-500')} />
              {ragStatus.pdf_count > 0 ? t('header.guidelines', { n: ragStatus.pdf_count }) : t('header.noGuidelines')}
            </div>
          )}

          {/* Theme toggle */}
          <button onClick={() => setIsDark(d => !d)} className={clsx(PANEL_BTN, isDark && 'text-yellow-400 hover:text-yellow-300')} title={t('header.themeTitle')}>
            {isDark
              ? <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>
              : <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" /></svg>
            }
          </button>

          {/* Keyboard shortcuts */}
          <button onClick={() => setShowShortcuts(s => !s)} className={clsx(PANEL_BTN, showShortcuts && '!bg-accent/15 !border-accent/30 !text-accent')} title={t('header.shortcutsTitle')}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
            </svg>
          </button>

          <button onClick={() => setShowHistory(true)} className={PANEL_BTN} title={t('header.historyTitle')}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          <div className="relative" ref={settingsRef}>
            <button onClick={() => setShowSettings(s => !s)} className={clsx(PANEL_BTN, showSettings && '!bg-accent/15 !border-accent/30 !text-accent')} title={t('header.settingsTitle')}>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            {showSettings && (
              <div className={clsx('absolute right-0 top-10 border rounded-xl shadow-2xl z-50 p-1.5 min-w-[180px] space-y-0.5',
                isDark ? 'bg-[#10151d] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
                <button onClick={handleIngestRag} disabled={ragLoading} className={clsx('w-full text-left px-3 py-2 rounded-lg text-xs transition-colors font-medium flex items-center gap-2 disabled:opacity-50', isDark ? 'text-slate-300 hover:bg-[#1a2230] hover:text-white' : 'text-slate-700 hover:bg-accent/8 hover:text-accent')}>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                  {ragLoading ? t('settings.ingesting') : t('settings.ingest')}
                </button>
              </div>
            )}
          </div>

          {/* Logged-in user + logout */}
          {user && (
            <div className="flex items-center gap-2 shrink-0 pl-1 border-l border-[#1f2835]">
              <span className={clsx('text-[10px] font-medium hidden sm:block truncate max-w-[120px]',
                isDark ? 'text-slate-400' : 'text-slate-500')}>
                {user.full_name}
                {user.department && (
                  <span className="ml-1 text-slate-500">· {user.department}</span>
                )}
              </span>

              {/* Admin dashboard button — only visible to admin */}
              {user.role === 'admin' && (
                <button
                  onClick={() => setShowAdmin(true)}
                  title="User Management"
                  className={clsx(PANEL_BTN, 'text-teal-400 hover:!text-teal-300')}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                  </svg>
                </button>
              )}
              <button
                onClick={handleLogout}
                title="Sign out"
                className={clsx(PANEL_BTN, 'text-red-400 hover:!text-red-300')}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ── Differential diagnosis ribbon (real data, no fabricated confidence) ── */}
      {report?.differential_diagnosis && report.differential_diagnosis.length > 0 && (
        <div className={clsx('relative z-30 flex items-center gap-2 px-5 py-2 shrink-0 border-b overflow-x-auto',
          isDark ? 'bg-[#0d1219] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 shrink-0">{t('ai.differential')}</span>
          {report.differential_diagnosis.map((d, i) => (
            <span key={`${d}-${i}`}
              className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs whitespace-nowrap border shrink-0',
                i === 0
                  ? 'border-accent/50 text-accent bg-accent/10'
                  : isDark ? 'border-[#1f2835] text-slate-400' : 'border-[#e2e8ee] text-slate-500')}>
              <span className={clsx('w-1.5 h-1.5 rounded-full', i === 0 ? 'bg-accent' : 'bg-slate-500')} />
              {d}
            </span>
          ))}
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className={clsx('relative z-30 text-[10px] text-center py-1.5 px-4 shrink-0 font-medium tracking-wide border-b ',
        isDark ? 'bg-amber-950/20 border-amber-900/[0.08] text-amber-400/40' : 'bg-amber-50/70 border-amber-200/50 text-amber-700/80')}>
        {t('disclaimer.top')}
      </div>

      {/* ── Main 3-column with resize handles ── */}
      <div className="relative z-10 flex-1 flex p-3 min-h-0 overflow-hidden">

        {/* Left glass panel */}
        <aside
          style={{ width: leftOpen ? leftWidth : 40, transition: isResizing ? 'none' : 'width 300ms cubic-bezier(0.4,0,0.2,1)' }}
          className={clsx('shrink-0 flex flex-col overflow-hidden rounded-2xl', GLASS)}
        >
          <div className={clsx('flex items-center shrink-0 border-b px-3 py-2', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]', leftOpen ? 'justify-between' : 'justify-center')}>
            {leftOpen && <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{t('workflow.title')}</span>}
            <button onClick={() => setLeftOpen(o => !o)}
              className={clsx('w-6 h-6 rounded-lg flex items-center justify-center transition-colors shrink-0', isDark ? 'text-slate-500 hover:bg-[#1a2230] hover:text-slate-200' : 'text-slate-400 hover:bg-accent/10 hover:text-accent')}
              title={leftOpen ? t('workflow.collapse') : t('workflow.expand')}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                {leftOpen ? <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /> : <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />}
              </svg>
            </button>
          </div>

          {leftOpen && (
            <WorkflowPanel
              uploaded={uploaded}
              upload={upload}
              cancerType={cancerType}
              ctx={ctx}
              job={job}
              ragStatus={ragStatus}
              modelCatalog={modelCatalog}
              selectedModel={selectedModel}
              featureCatalog={featureCatalog}
              selectedFeatures={selectedFeatures}
              isRunning={isRunning}
              isDone={isDone}
              hasCtx={hasCtx}
              isDark={isDark}
              onCancerTypeChange={handleCancerTypeChange}
              onUploaded={handleUploaded}
              onReset={handleReset}
              onAnalyse={handleAnalyse}
              onCtxChange={patch => setCtx(p => ({ ...p, ...patch }))}
              onModelChange={setSelectedModel}
              onFeaturesChange={setSelectedFeatures}
            />
          )}
        </aside>

        {/* Left resize handle */}
        {leftOpen && (
          <div onMouseDown={startLeftResize}
            className="w-3 shrink-0 flex items-center justify-center cursor-col-resize group self-stretch mx-0.5">
            <div className={clsx('w-px h-12 rounded-full transition-all duration-200 group-hover:w-1 group-hover:h-20', isDark ? 'bg-[#1f2835] group-hover:bg-accent/50' : 'bg-slate-100 group-hover:bg-accent/40')} />
          </div>
        )}

        {/* DICOM viewer */}
        <main className={clsx('flex-1 min-w-0 rounded-2xl overflow-hidden shadow-2xl bg-black', isDark ? 'ring-1 ring-white/[0.05]' : 'ring-1 ring-black/10')}>
          <DicomViewer
            slices={slices.length ? slices : previewSlices}
            rawSlices={slices.length ? rawSlices : undefined}
            modality={upload?.modality ?? null}
            phase={upload?.series[0]?.phase ?? null}
            isRunning={isRunning}
            cancerType={cancerType}
          />
        </main>

        {/* Right resize handle */}
        {rightOpen && (
          <div onMouseDown={startRightResize}
            className="w-3 shrink-0 flex items-center justify-center cursor-col-resize group self-stretch mx-0.5">
            <div className={clsx('w-px h-12 rounded-full transition-all duration-200 group-hover:w-1 group-hover:h-20', isDark ? 'bg-[#1f2835] group-hover:bg-accent/50' : 'bg-slate-100 group-hover:bg-accent/40')} />
          </div>
        )}

        {/* Right glass panel */}
        <aside
          style={{ width: rightOpen ? rightWidth : 40, transition: isResizing ? 'none' : 'width 300ms cubic-bezier(0.4,0,0.2,1)' }}
          className={clsx('shrink-0 flex flex-col overflow-hidden rounded-2xl', GLASS)}
        >
          <div className={clsx('flex items-center shrink-0 border-b px-3 py-2', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]', rightOpen ? 'justify-between' : 'justify-center')}>
            {rightOpen && (
              <div className="flex items-center gap-2">
                <h2 className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{t('report.title')}</h2>
                {report && (
                  <div className={clsx('flex rounded-lg overflow-hidden border text-[10px] font-mono', isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]')}>
                    <button onClick={() => setShowRaw(false)} className={clsx('px-2.5 py-1 transition-colors', !showRaw ? 'bg-accent text-white' : isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-700')}>{t('report.structured')}</button>
                    <button onClick={() => setShowRaw(true)}  className={clsx('px-2.5 py-1 transition-colors', showRaw  ? 'bg-accent text-white' : isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-700')}>{t('report.raw')}</button>
                  </div>
                )}
              </div>
            )}
            <button onClick={() => setRightOpen(o => !o)}
              className={clsx('w-6 h-6 rounded-lg flex items-center justify-center transition-colors shrink-0', isDark ? 'text-slate-500 hover:bg-[#1a2230] hover:text-slate-200' : 'text-slate-400 hover:bg-accent/10 hover:text-accent')}
              title={rightOpen ? t('right.collapse') : t('right.expand')}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                {rightOpen ? <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /> : <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />}
              </svg>
            </button>
          </div>

          {rightOpen && (
            <div className="flex-1 overflow-hidden p-4">
              {report ? (
                showRaw ? (
                  <pre className={clsx('text-xs whitespace-pre-wrap font-mono overflow-y-auto h-full leading-relaxed', isDark ? 'text-slate-400' : 'text-slate-500')}>{report.raw_llm_output}</pre>
                ) : (
                  <AIReportPanel
                    report={report} jobId={job?.job_id ?? ''} signOff={job?.sign_off ?? null}
                    onSignOff={signOff} isDark={isDark}
                    currentSlice={slices.length ? slices[Math.floor(slices.length / 2)] : undefined}
                    currentUserName={user?.full_name}
                  />
                )
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center space-y-3 max-w-[180px]">
                    <div className={clsx('w-12 h-12 rounded-2xl border flex items-center justify-center mx-auto shadow-sm', isDark ? 'bg-[#121924] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}>
                      <svg className={clsx('w-6 h-6', isDark ? 'text-slate-700' : 'text-slate-300')} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
                      </svg>
                    </div>
                    <div>
                      <p className={clsx('text-sm font-medium', isDark ? 'text-slate-600' : 'text-slate-400')}>{t('report.emptyTitle')}</p>
                      <p className={clsx('text-xs mt-1 leading-relaxed', isDark ? 'text-slate-700' : 'text-slate-300')}>{t('report.emptyBody')}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>

      {/* ── Keyboard shortcuts modal ── */}
      {showShortcuts && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 "
          onClick={() => setShowShortcuts(false)}>
          <div className={clsx('rounded-2xl p-6 w-80 border shadow-2xl ', isDark ? 'bg-[#10151d] border-[#1f2835]' : 'bg-white border-[#e2e8ee]')}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={clsx('text-sm font-semibold', isDark ? 'text-slate-100' : 'text-slate-800')}>{t('shortcuts.title')}</h3>
              <button onClick={() => setShowShortcuts(false)} className="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
            </div>
            <div className="space-y-2.5">
              {APP_SHORTCUTS.map(([key, descKey]) => (
                <div key={key} className="flex items-center justify-between gap-4">
                  <kbd className={clsx('text-xs font-mono px-2 py-0.5 rounded-md border', isDark ? 'bg-slate-800 border-[#1f2835] text-accent' : 'bg-slate-100 border-slate-200 text-accent')}>{key}</kbd>
                  <span className={clsx('text-xs text-right', isDark ? 'text-slate-400' : 'text-slate-500')}>{t(descKey)}</span>
                </div>
              ))}
            </div>
            <p className={clsx('text-[10px] text-center mt-4', isDark ? 'text-slate-700' : 'text-slate-400')}>{t('shortcuts.closeHint')}</p>
          </div>
        </div>
      )}

      <HistoryPanel open={showHistory} onClose={() => setShowHistory(false)} isDark={isDark} />
      {user?.role === 'admin' && (
        <AdminDashboard open={showAdmin} onClose={() => setShowAdmin(false)} isDark={isDark} currentUser={user} />
      )}
      {toast && <Toast message={toast.message} type={toast.type} isDark={isDark} onClose={() => setToast(null)} />}
    </div>
  )
}
