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
import { useAuth } from './context/AuthContext'
import { useAnalysis } from './hooks/useAnalysis'
import { analysisApi, dicomApi, ragApi } from './services/api'
import { useI18n } from './i18n'
import type { TKey } from './i18n'
import type { CancerType, ModelCatalog, PatientContext, UploadResponse } from './types'
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

export default function App() {
  const { t, lang, toggle: toggleLang } = useI18n()
  const { user, loading: authLoading, logout } = useAuth()
  const { job, slices, rawSlices, report, start, signOff, reset } = useAnalysis()
  const [upload, setUpload]               = useState<UploadResponse | null>(null)
  const [cancerType, setCancerType]       = useState<CancerType>('liver')
  const [modelCatalog, setModelCatalog]   = useState<ModelCatalog | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [ctx, setCtx]                     = useState<PatientContext>(DEFAULT_CTX)
  const [previewSlices, setPreviewSlices] = useState<string[]>([])
  const [ragStatus, setRagStatus]         = useState<{ chunks: number; pdf_count: number } | null>(null)
  const [ragLoading, setRagLoading]       = useState(false)
  const [showRaw, setShowRaw]             = useState(false)
  const [showHistory, setShowHistory]     = useState(false)
  const [showAdmin, setShowAdmin]         = useState(false)
  const [showSettings, setShowSettings]   = useState(false)
  const [detection, setDetection]         = useState<{ type: string; confidence: string; reason: string } | null>(null)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [leftOpen, setLeftOpen]           = useState(true)
  const [rightOpen, setRightOpen]         = useState(true)
  const [leftWidth, setLeftWidth]         = useState(288)
  const [rightWidth, setRightWidth]       = useState(400)
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
  useEffect(() => { localStorage.setItem('v2-theme', isDark ? 'dark' : 'light') }, [isDark])

  // Default the model to the current cancer's recommended model whenever the
  // cancer type changes (or once the catalog loads).
  useEffect(() => {
    if (modelCatalog?.[cancerType]) setSelectedModel(modelCatalog[cancerType].default)
  }, [cancerType, modelCatalog])

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
    setDetection(null)
    dicomApi.preview(res.study_id, res.num_files).then(r => setPreviewSlices(r.slices)).catch(() => null)
    // Apply auto-detected cancer type if confidence is high or medium
    if (res.suggested_cancer_type && res.detection_confidence && res.detection_confidence !== 'low') {
      const detected = res.suggested_cancer_type as CancerType
      setCancerType(detected)
      setDetection({
        type: detected,
        confidence: res.detection_confidence,
        reason: res.detection_reason ?? '',
      })
    }
  }
  const handleCancerTypeChange = useCallback(async (ct: CancerType) => {
    setCancerType(ct)
    if (upload) {
      dicomApi.updateCancerType(upload.study_id, ct).catch(() => null)
    }
  }, [upload])
  const handleAnalyse   = useCallback(async () => { if (upload) await start(upload.study_id, ctx, selectedModel ?? undefined) }, [upload, ctx, selectedModel, start])
  const handleReset     = () => { setUpload(null); setCtx(DEFAULT_CTX); setPreviewSlices([]); setShowRaw(false); setDetection(null); reset() }
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
    const onMove = (ev: MouseEvent) => setRightWidth(Math.max(280, Math.min(560, startW + startX - ev.clientX)))
    const onUp = () => { setIsResizing(false); document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [rightWidth])

  const GLASS = clsx('backdrop-blur-xl border shadow-lg', isDark
    ? 'bg-slate-900/80 border-white/[0.07] shadow-black/50'
    : 'bg-white/65 border-white/80 shadow-violet-100/40')

  const INPUT = clsx('w-full rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-accent/50 transition-colors font-mono border', isDark
    ? 'bg-white/5 border-white/[0.08] text-slate-200 placeholder:text-slate-600'
    : 'bg-white/70 border-black/[0.07] text-slate-800 placeholder:text-slate-400')

  const PANEL_BTN = clsx('w-8 h-8 rounded-lg border flex items-center justify-center transition-colors shadow-sm', isDark
    ? 'bg-white/5 hover:bg-white/10 border-white/[0.08] text-slate-400 hover:text-accent'
    : 'bg-white/60 hover:bg-white/90 border-white/80 text-slate-500 hover:text-accent')

  // Auth gate — must be after all hook calls
  if (authLoading) {
    return (
      <div className={clsx('h-screen flex items-center justify-center', isDark ? 'bg-slate-950' : 'bg-surface')}>
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!user) return <LoginScreen isDark={isDark} />

  return (
    <div className={clsx('h-screen flex flex-col overflow-hidden font-sans select-none', isDark ? 'dark bg-slate-950 text-slate-200' : 'bg-surface text-slate-800', isResizing && 'cursor-col-resize')}>

      {/* ── Animated gradient blobs ── */}
      <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-[700px] h-[700px] rounded-full blur-[130px] blob-1"
          style={{ background: 'radial-gradient(circle, rgba(167,139,250,0.38) 0%, transparent 65%)' }} />
        <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full blur-[110px] blob-2"
          style={{ background: 'radial-gradient(circle, rgba(125,211,252,0.32) 0%, transparent 65%)' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full blur-[90px] blob-3"
          style={{ background: 'radial-gradient(circle, rgba(110,231,183,0.18) 0%, transparent 65%)' }} />
        <div className="absolute top-1/4 left-1/4 w-[300px] h-[300px] rounded-full blur-[80px] blob-4"
          style={{ background: 'radial-gradient(circle, rgba(249,168,212,0.18) 0%, transparent 65%)' }} />
      </div>

      {/* ── Glass header ── */}
      <header className={clsx('relative z-40 backdrop-blur-xl border-b flex items-center justify-between px-5 py-3 shrink-0',
        isDark ? 'bg-slate-900/80 border-white/[0.06]' : 'bg-white/60 border-white/80')}>
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
              {cancerType !== 'liver' && (
                <span className="text-[10px] font-medium text-accent">{CANCER_TYPE_META[cancerType]?.icon} {CANCER_TYPE_META[cancerType]?.label}</span>
              )}
            </h1>
            <p className="text-[10px] text-slate-400 leading-tight hidden sm:block">{t('header.subtitle')}</p>
          </div>
        </div>

        {/* LI-RADS badge — shows when analysis is done */}
        {isDone && report?.lesions?.[0] && (
          <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-sm hidden md:flex',
            isDark ? 'bg-slate-800/60 border-white/[0.08]' : 'bg-white/60 border-black/[0.06]')}>
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
                ? 'bg-white/5 hover:bg-white/10 border-white/[0.08] text-slate-300 hover:text-accent'
                : 'bg-white/60 hover:bg-white/90 border-white/80 text-slate-600 hover:text-accent')}
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
              <div className={clsx('absolute right-0 top-10 backdrop-blur-xl border rounded-xl shadow-2xl z-50 p-1.5 min-w-[180px] space-y-0.5',
                isDark ? 'bg-slate-900/95 border-white/10' : 'bg-white/90 border-white/90')}>
                <button onClick={handleIngestRag} disabled={ragLoading} className={clsx('w-full text-left px-3 py-2 rounded-lg text-xs transition-colors font-medium flex items-center gap-2 disabled:opacity-50', isDark ? 'text-slate-300 hover:bg-white/10 hover:text-white' : 'text-slate-700 hover:bg-accent/8 hover:text-accent')}>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                  {ragLoading ? t('settings.ingesting') : t('settings.ingest')}
                </button>
              </div>
            )}
          </div>

          {/* Logged-in user + logout */}
          {user && (
            <div className="flex items-center gap-2 shrink-0 pl-1 border-l border-white/[0.08]">
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
                  className={clsx(PANEL_BTN, 'text-violet-400 hover:!text-violet-300')}
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

      {/* ── Disclaimer ── */}
      <div className={clsx('relative z-30 text-[10px] text-center py-1.5 px-4 shrink-0 font-medium tracking-wide border-b backdrop-blur-sm',
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
          <div className={clsx('flex items-center shrink-0 border-b px-3 py-2', isDark ? 'border-white/[0.05]' : 'border-black/[0.05]', leftOpen ? 'justify-between' : 'justify-center')}>
            {leftOpen && <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">{t('workflow.title')}</span>}
            <button onClick={() => setLeftOpen(o => !o)}
              className={clsx('w-6 h-6 rounded-lg flex items-center justify-center transition-colors shrink-0', isDark ? 'text-slate-500 hover:bg-white/10 hover:text-slate-200' : 'text-slate-400 hover:bg-accent/10 hover:text-accent')}
              title={leftOpen ? t('workflow.collapse') : t('workflow.expand')}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                {leftOpen ? <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /> : <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />}
              </svg>
            </button>
          </div>

          {leftOpen && (
            <div className="flex-1 p-4 space-y-5 overflow-y-auto">

              {/* Cancer type selector */}
              {!uploaded && (
                <div className="space-y-2.5">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Cancer Type</span>
                  <div className="grid grid-cols-2 gap-1.5">
                    {(Object.keys(CANCER_TYPE_META) as CancerType[]).map(ct => {
                      const m = CANCER_TYPE_META[ct]
                      return (
                        <button
                          key={ct}
                          onClick={() => handleCancerTypeChange(ct)}
                          className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-2 rounded-xl text-xs font-medium transition-all border',
                            cancerType === ct
                              ? 'bg-accent text-white border-accent/50 shadow-sm shadow-accent/25'
                              : isDark
                                ? 'bg-white/5 text-slate-400 border-white/[0.08] hover:border-accent/40 hover:text-slate-200'
                                : 'bg-white/60 text-slate-500 border-black/[0.07] hover:border-accent/30 hover:text-slate-700',
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
                    <UploadPanel onUploaded={handleUploaded} cancerType={cancerType} isDark={isDark} />
                  ) : (
                    <div className="space-y-2">
                      <div className={clsx('rounded-xl p-3 space-y-2 border', isDark ? 'border-emerald-800/30 bg-emerald-950/20' : 'border-emerald-200/80 bg-emerald-50/70')}>
                        <div className="flex items-center justify-between">
                          <span className={clsx('text-xs font-semibold', isDark ? 'text-emerald-400' : 'text-emerald-700')}>{t('step.studyLoaded')}</span>
                          <button onClick={handleReset} className="text-[10px] text-slate-400 hover:text-slate-500 transition-colors underline underline-offset-2">{t('step.reset')}</button>
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

                      {/* Auto-detection badge */}
                      {detection && (
                        <div className={clsx('rounded-xl p-3 border space-y-1.5',
                          detection.confidence === 'high'
                            ? isDark ? 'bg-sky-950/40 border-sky-700/40' : 'bg-sky-50 border-sky-200'
                            : isDark ? 'bg-slate-800/40 border-white/[0.08]' : 'bg-white/50 border-black/[0.07]')}>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <svg className={clsx('w-3 h-3 shrink-0',
                                detection.confidence === 'high'
                                  ? isDark ? 'text-sky-400' : 'text-sky-600'
                                  : 'text-slate-400')}
                                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round"
                                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                              </svg>
                              <span className={clsx('text-[10px] font-semibold uppercase tracking-wide',
                                detection.confidence === 'high'
                                  ? isDark ? 'text-sky-400' : 'text-sky-700'
                                  : isDark ? 'text-slate-400' : 'text-slate-500')}>
                                Auto-detected: {CANCER_TYPE_META[detection.type as CancerType]?.icon} {CANCER_TYPE_META[detection.type as CancerType]?.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className={clsx('text-[9px] font-bold uppercase px-1.5 py-0.5 rounded',
                                detection.confidence === 'high'
                                  ? 'bg-sky-500 text-white'
                                  : 'bg-slate-500 text-white')}>
                                {detection.confidence}
                              </span>
                              <button onClick={() => setDetection(null)}
                                className="text-slate-400 hover:text-slate-600 text-xs leading-none">×</button>
                            </div>
                          </div>
                          {detection.reason && (
                            <p className={clsx('text-[9px] font-mono leading-relaxed truncate',
                              isDark ? 'text-slate-500' : 'text-slate-400')}
                              title={detection.reason}>
                              {detection.reason}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Post-upload cancer type override */}
                      <div className="space-y-1.5">
                        <span className={clsx('text-[10px] font-semibold uppercase tracking-widest', isDark ? 'text-slate-500' : 'text-slate-400')}>Cancer Type</span>
                        <div className="grid grid-cols-2 gap-1">
                          {(Object.keys(CANCER_TYPE_META) as CancerType[]).map(ct => {
                            const m = CANCER_TYPE_META[ct]
                            return (
                              <button
                                key={ct}
                                onClick={() => handleCancerTypeChange(ct)}
                                disabled={isRunning}
                                className={clsx(
                                  'flex items-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-all border disabled:opacity-40 disabled:cursor-not-allowed',
                                  cancerType === ct
                                    ? 'bg-accent text-white border-accent/50 shadow-sm shadow-accent/25'
                                    : isDark
                                      ? 'bg-white/5 text-slate-400 border-white/[0.08] hover:border-accent/40 hover:text-slate-200'
                                      : 'bg-white/60 text-slate-500 border-black/[0.07] hover:border-accent/30 hover:text-slate-700',
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
                    {/* Liver-specific context chips */}
                    {cancerType === 'liver' && (<>
                      <div className="flex flex-wrap gap-1.5">
                        {(['cirrhosis', 'hepatitis_b', 'hepatitis_c', 'prior_hcc'] as const).map(key => {
                          const labelKey = { cirrhosis: 'ctx.cirrhosis', hepatitis_b: 'ctx.hepatitis_b', hepatitis_c: 'ctx.hepatitis_c', prior_hcc: 'ctx.prior_hcc' } as const
                          return (
                            <button key={key} onClick={() => setCtx(p => ({ ...p, [key]: !p[key] }))}
                              className={clsx('px-2.5 py-1 rounded-full text-xs font-medium transition-all',
                                ctx[key] ? 'bg-accent text-white shadow-sm shadow-accent/25'
                                  : isDark ? 'bg-white/5 text-slate-500 border border-white/[0.08] hover:border-accent/40 hover:text-slate-300'
                                  : 'bg-white/60 text-slate-500 border border-black/[0.08] hover:border-accent/30 hover:text-slate-700')}>
                              {t(labelKey[key])}
                            </button>
                          )
                        })}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-400 shrink-0">{t('ctx.afp')}</span>
                        <div className="relative flex-1">
                          <input type="number" value={ctx.afp_level ?? ''}
                            onChange={e => setCtx(p => ({ ...p, afp_level: e.target.value ? Number(e.target.value) : null }))}
                            placeholder="—" className={clsx(INPUT, 'pl-2.5 pr-10')} />
                          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-slate-400 pointer-events-none">{t('ctx.afpUnit')}</span>
                        </div>
                      </div>
                    </>)}
                    <textarea value={ctx.notes} onChange={e => setCtx(p => ({ ...p, notes: e.target.value }))}
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
                    {/* Model picker — lets you compare LLMs per cancer */}
                    {modelCatalog?.[cancerType] && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">AI Model</span>
                          {selectedModel === modelCatalog[cancerType].default && (
                            <span className="text-[9px] text-slate-500">recommended</span>
                          )}
                        </div>
                        <select
                          value={selectedModel ?? modelCatalog[cancerType].default}
                          onChange={e => setSelectedModel(e.target.value)}
                          disabled={isRunning}
                          style={{ colorScheme: isDark ? 'dark' : 'light' }}
                          className={clsx('w-full rounded-lg px-2.5 py-2 text-xs font-mono border focus:outline-none focus:border-accent/50 transition-colors disabled:opacity-50',
                            isDark ? 'bg-slate-800 border-white/[0.12] text-slate-100' : 'bg-white border-black/[0.12] text-slate-800')}
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
                    <button onClick={handleAnalyse} disabled={isRunning}
                      className={clsx('w-full py-2.5 rounded-xl font-semibold text-sm transition-all duration-200',
                        isRunning ? 'bg-accent/15 text-accent/60 cursor-not-allowed'
                          : isDone
                            ? isDark ? 'bg-white/5 border border-white/[0.08] text-slate-400 hover:border-accent/40 hover:text-accent' : 'bg-white/60 border border-black/[0.08] text-slate-500 hover:border-accent/30 hover:text-accent'
                            : 'bg-accent hover:bg-violet-600 active:bg-violet-700 text-white shadow-lg shadow-violet-300/30')}>
                      {isRunning ? t('run.analysing') : isDone ? t('run.again') : t('run.start')}
                    </button>
                  </div>
                )}
              </div>

              {/* Progress */}
              {job && (
                <div className={clsx('pt-4 space-y-2 border-t', isDark ? 'border-white/[0.05]' : 'border-black/[0.05]')}>
                  <ProgressTracker job={job} isDark={isDark} />
                  {job.status === 'failed' && job.error && (
                    <div className={clsx('rounded-xl p-3 space-y-1 border', isDark ? 'bg-red-950/30 border-red-900/30' : 'bg-red-50/80 border-red-200/70')}>
                      <p className={clsx('text-xs font-semibold', isDark ? 'text-red-400' : 'text-red-600')}>{t('run.failed')}</p>
                      <p className={clsx('text-[10px] font-mono leading-relaxed break-words', isDark ? 'text-red-400/70' : 'text-red-500')}>{job.error}</p>
                      <button onClick={handleReset} className={clsx('text-[10px] underline underline-offset-2 transition-colors', isDark ? 'text-red-400 hover:text-red-300' : 'text-red-500 hover:text-red-700')}>{t('step.reset')}</button>
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
          )}
        </aside>

        {/* Left resize handle */}
        {leftOpen && (
          <div onMouseDown={startLeftResize}
            className="w-3 shrink-0 flex items-center justify-center cursor-col-resize group self-stretch mx-0.5">
            <div className={clsx('w-px h-12 rounded-full transition-all duration-200 group-hover:w-1 group-hover:h-20', isDark ? 'bg-white/10 group-hover:bg-accent/50' : 'bg-black/[0.07] group-hover:bg-accent/40')} />
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
          />
        </main>

        {/* Right resize handle */}
        {rightOpen && (
          <div onMouseDown={startRightResize}
            className="w-3 shrink-0 flex items-center justify-center cursor-col-resize group self-stretch mx-0.5">
            <div className={clsx('w-px h-12 rounded-full transition-all duration-200 group-hover:w-1 group-hover:h-20', isDark ? 'bg-white/10 group-hover:bg-accent/50' : 'bg-black/[0.07] group-hover:bg-accent/40')} />
          </div>
        )}

        {/* Right glass panel */}
        <aside
          style={{ width: rightOpen ? rightWidth : 40, transition: isResizing ? 'none' : 'width 300ms cubic-bezier(0.4,0,0.2,1)' }}
          className={clsx('shrink-0 flex flex-col overflow-hidden rounded-2xl', GLASS)}
        >
          <div className={clsx('flex items-center shrink-0 border-b px-3 py-2', isDark ? 'border-white/[0.05]' : 'border-black/[0.05]', rightOpen ? 'justify-between' : 'justify-center')}>
            {rightOpen && (
              <div className="flex items-center gap-2">
                <h2 className={clsx('text-sm font-semibold', isDark ? 'text-slate-200' : 'text-slate-700')}>{t('report.title')}</h2>
                {report && (
                  <div className={clsx('flex rounded-lg overflow-hidden border text-[10px] font-mono', isDark ? 'border-white/[0.08]' : 'border-black/[0.07]')}>
                    <button onClick={() => setShowRaw(false)} className={clsx('px-2.5 py-1 transition-colors', !showRaw ? 'bg-accent text-white' : isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-700')}>{t('report.structured')}</button>
                    <button onClick={() => setShowRaw(true)}  className={clsx('px-2.5 py-1 transition-colors', showRaw  ? 'bg-accent text-white' : isDark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-700')}>{t('report.raw')}</button>
                  </div>
                )}
              </div>
            )}
            <button onClick={() => setRightOpen(o => !o)}
              className={clsx('w-6 h-6 rounded-lg flex items-center justify-center transition-colors shrink-0', isDark ? 'text-slate-500 hover:bg-white/10 hover:text-slate-200' : 'text-slate-400 hover:bg-accent/10 hover:text-accent')}
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
                    <div className={clsx('w-12 h-12 rounded-2xl border flex items-center justify-center mx-auto shadow-sm', isDark ? 'bg-white/5 border-white/[0.06]' : 'bg-white/60 border-black/[0.06]')}>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
          onClick={() => setShowShortcuts(false)}>
          <div className={clsx('rounded-2xl p-6 w-80 border shadow-2xl backdrop-blur-xl', isDark ? 'bg-slate-900/95 border-white/10' : 'bg-white/92 border-white/80')}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className={clsx('text-sm font-semibold', isDark ? 'text-slate-100' : 'text-slate-800')}>{t('shortcuts.title')}</h3>
              <button onClick={() => setShowShortcuts(false)} className="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
            </div>
            <div className="space-y-2.5">
              {APP_SHORTCUTS.map(([key, descKey]) => (
                <div key={key} className="flex items-center justify-between gap-4">
                  <kbd className={clsx('text-xs font-mono px-2 py-0.5 rounded-md border', isDark ? 'bg-slate-800 border-white/10 text-accent' : 'bg-slate-100 border-slate-200 text-accent')}>{key}</kbd>
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
