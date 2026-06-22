import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type Lang = 'en' | 'zh'

/** English is the source of truth — keys are typed from it. */
const en = {
  // Language switcher
  'lang.label': 'EN',
  'lang.next': '繁中',
  'lang.title': 'Switch language / 切換語言',

  // Header
  'header.subtitle': '{system} · RAG-Augmented · Local LLM',
  'header.topFinding': 'Top finding',
  'header.guidelines': '{n} guidelines',
  'header.noGuidelines': 'No guidelines',
  'header.guidelinesTitle': 'Guideline library',
  'header.guidelinesChunks': '{n} chunks',
  'header.guidelinesCount': '{n} PDF',
  'header.guidelinesPdfs': 'Guideline PDFs on disk',
  'header.guidelinesNotIndexed': 'PDFs present but not yet ingested — click Ingest',
  'header.guidelinesActive': 'Active',
  'header.guidelinesCited': 'Guidelines cited in the current report',
  'header.guidelinesReingest': 'Ingest {label}',
  'header.guidelinesIngestAll': 'Ingest all guidelines',
  'header.newAnalysis': 'New Analysis',
  'header.newAnalysisTitle': 'Start a new analysis (clears current study, report and images)',
  'header.themeTitle': 'Toggle theme (T)',
  'header.shortcutsTitle': 'Keyboard shortcuts (?)',
  'header.historyTitle': 'History',
  'header.settingsTitle': 'Settings',

  // Settings menu
  'settings.history': 'History',
  'settings.ingesting': 'Ingesting…',
  'settings.ingest': 'Ingest Guidelines',

  // Disclaimer
  'disclaimer.top': '⚠ Decision support only — not a clinical diagnosis. All findings require licensed radiologist review.',

  // Workflow panel
  'workflow.title': 'Workflow',
  'workflow.collapse': 'Collapse [',
  'workflow.expand': 'Expand [',
  'step.upload': 'Upload DICOM',
  'step.studyLoaded': 'Study loaded',
  'step.reset': 'Reset',
  'field.modality': 'Modality',
  'field.files': 'Files',
  'field.series': 'Series',
  'step.context': 'Clinical Context',
  'step.optional': 'optional',
  'ctx.cirrhosis': 'Cirrhosis',
  'ctx.hepatitis_b': 'Hep B',
  'ctx.hepatitis_c': 'Hep C',
  'ctx.prior_hcc': 'Prior HCC',
  'ctx.afp': 'AFP',
  'ctx.afpUnit': 'ng/mL',
  'ctx.notes': 'Clinical notes…',
  'step.model': 'AI Model',
  'step.modelRecommended': 'recommended',
  'step.features': 'Features & Extractors',
  'step.run': 'Run Analysis',
  'run.analysing': 'Analysing…',
  'run.again': '↺ Run Again',
  'run.start': 'Run Analysis (Space)',
  'run.failed': 'Analysis failed',
  'rag.noneTitle': 'No guidelines loaded',
  'rag.noneBody': 'Add PDFs to {path} → Ingest.',

  // Report panel (right column shell)
  'report.title': 'AI Report',
  'report.structured': 'Structured',
  'report.raw': 'Raw',
  'report.emptyTitle': 'No report yet',
  'report.emptyBody': 'Upload a scan and run analysis',
  'right.collapse': 'Collapse ]',
  'right.expand': 'Expand ]',

  // Toasts
  'toast.complete': 'Analysis complete — report ready',
  'toast.failed': 'Analysis failed',

  // Shortcuts modal (app)
  'shortcuts.title': 'Keyboard Shortcuts',
  'shortcuts.closeHint': 'Click anywhere to close · Esc',
  'sc.theme': 'Toggle dark / light theme',
  'sc.run': 'Run analysis (when scan loaded)',
  'sc.left': 'Toggle left panel',
  'sc.right': 'Toggle right panel',
  'sc.list': 'Show this shortcuts list',
  'sc.esc': 'Close overlays',

  // UploadPanel
  'upload.uploading': 'Uploading…',
  'upload.dropHere': 'Drop files here',
  'upload.release': 'Release to upload',
  'upload.browse': 'Drop files or click to browse',
  'upload.formats': 'DICOM · NIfTI · JPG/PNG · max 500 MB',
  'upload.errTooBig': 'One or more files exceed 500 MB',
  'upload.errMinSlices': 'Upload at least 2 DICOM slices.',
  'upload.errFailed': 'Upload failed',

  // ProgressTracker
  'pt.dicom': 'DICOM',
  'pt.segment': 'Segment',
  'pt.radiomics': 'Radiomics',
  'pt.llmrag': 'LLM+RAG',
  'pt.done': 'Done',
  'pt.error': 'Error: {err}',
  'pt.prepare': 'Prepare',
  'pt.features': 'Features',
  'pt.airag': 'AI + RAG',

  // LI-RADS labels
  'lirads.LR-1': 'Definitely Benign',
  'lirads.LR-2': 'Probably Benign',
  'lirads.LR-3': 'Intermediate',
  'lirads.LR-4': 'Probably HCC',
  'lirads.LR-5': 'Definitely HCC',
  'lirads.LR-M': 'Malignant (non-HCC)',
  'lirads.LR-TIV': 'Tumour in Vein',
  'lirads.Indeterminate': 'Indeterminate',

  // AIReportPanel
  'ai.yes': 'Yes',
  'ai.no': 'No',
  'ai.majorFeatures': 'Major Features',
  'ai.ancillaryFeatures': 'Ancillary Features',
  'ai.radiomicFeatures': 'Radiomic Features',
  'ai.attention': 'Model Attention (CNN)',
  'ai.attentionHint': 'Where the CNN backbone focused — warmer = higher activation. Click to enlarge.',
  'ai.collapse': '▲ collapse',
  'ai.featuresCount': '▼ {n} features',
  'ai.approved': '✓ Approved',
  'ai.changesRequested': '⚠ Changes Requested',
  'ai.by': 'by',
  'ai.radiologistReview': 'Radiologist Review',
  'ai.nameId': 'Name / ID',
  'ai.namePlaceholder': 'Dr. Smith / RAD-001',
  'ai.commentsOptional': 'Comments (optional)',
  'ai.notes': 'Notes…',
  'ai.saving': 'Saving…',
  'ai.approve': '✓ Approve',
  'ai.requestChanges': '⚠ Request Changes',
  'ai.ragAugmented': 'RAG-augmented',
  'ai.downloadPdf': 'Download PDF',
  'ai.signOffRequired': 'Sign-off required',
  'ai.fhirJson': 'FHIR R4 JSON',
  'ai.gen': 'Gen…',
  'ai.copied': '✓ Copied',
  'ai.copy': 'Copy',
  'ai.exportHint': 'Sign-off required to enable PDF and FHIR export.',
  'ai.lesions': 'Lesions ({n})',
  'ai.differential': 'Differential Diagnosis',
  'ai.staging': 'Staging',
  'ai.bclcStage': 'BCLC Stage',
  'ai.vascular': 'Vascular',
  'ai.recommendations': 'Recommendations',
  'ai.citations': 'Guideline Citations',
  'ai.disclaimer': '⚠ AI decision support only. Radiologist review required before clinical use.',

  // HistoryPanel
  'hist.title': 'Session History',
  'hist.loading': 'Loading…',
  'hist.empty': 'No analyses yet',
  'hist.lirads': 'LI-RADS',
  'hist.bclc': 'BCLC',
  'hist.time': 'Time',

  // DicomViewer
  'dv.prevNext': 'Previous / next slice',
  'dv.navigate': 'Navigate slices',
  'dv.zoom': 'Zoom in / out',
  'dv.contrast': 'Adjust contrast',
  'dv.brightness': 'Adjust brightness',
  'dv.resetView': 'Reset view',
  'dv.toggleShortcuts': 'Toggle shortcuts',
  'dv.inProgress': 'Analysis in progress…',
  'dv.liver': 'Liver',
  'dv.tumour': 'Tumour',
  'dv.lung': 'Lung',
  'dv.colon': 'Colon',
  'dv.resetR': 'Reset [R]',
  'dv.overlayOn': 'Overlay ON',
  'dv.overlayOff': 'Overlay OFF',
  'dv.wlHint': 'drag to adjust W/L · ctrl+scroll to zoom',
  'dv.noScan': 'No scan loaded',
  'dv.uploadHint': 'Upload DICOM files using the left panel',
  'dv.pressHelp': 'Press ? for keyboard shortcuts',
  'dv.slice': 'Slice {n}',
  'dv.shortcutsTitle': 'Keyboard Shortcuts',
  'dv.closeHint': 'Click anywhere to close',
}

export type TKey = keyof typeof en

const zh: Record<TKey, string> = {
  'lang.label': '繁中',
  'lang.next': 'EN',
  'lang.title': '切換語言 / Switch language',

  'header.subtitle': '{system} · RAG 強化 · 本地 LLM',
  'header.topFinding': '主要發現',
  'header.guidelines': '{n} 份指引',
  'header.noGuidelines': '無指引',
  'header.guidelinesTitle': '指引資料庫',
  'header.guidelinesChunks': '{n} 區塊',
  'header.guidelinesCount': '{n} 份 PDF',
  'header.guidelinesPdfs': '磁碟上的指引 PDF',
  'header.guidelinesNotIndexed': 'PDF 已存在但尚未匯入 — 請點擊匯入',
  'header.guidelinesActive': '使用中',
  'header.guidelinesCited': '目前報告引用的指引',
  'header.guidelinesReingest': '匯入 {label}',
  'header.guidelinesIngestAll': '匯入全部指引',
  'header.newAnalysis': '新分析',
  'header.newAnalysisTitle': '開始新的分析（清除目前的研究、報告與影像）',
  'header.themeTitle': '切換主題 (T)',
  'header.shortcutsTitle': '鍵盤快捷鍵 (?)',
  'header.historyTitle': '歷史紀錄',
  'header.settingsTitle': '設定',

  'settings.history': '歷史紀錄',
  'settings.ingesting': '匯入中…',
  'settings.ingest': '匯入指引',

  'disclaimer.top': '⚠ 僅供決策輔助 — 非臨床診斷。所有結果須經合格放射科醫師審查。',

  'workflow.title': '工作流程',
  'workflow.collapse': '收合 [',
  'workflow.expand': '展開 [',
  'step.upload': '上傳 DICOM',
  'step.studyLoaded': '已載入研究',
  'step.reset': '重設',
  'field.modality': '影像類型',
  'field.files': '檔案',
  'field.series': '序列',
  'step.context': '臨床資訊',
  'step.optional': '選填',
  'ctx.cirrhosis': '肝硬化',
  'ctx.hepatitis_b': 'B 型肝炎',
  'ctx.hepatitis_c': 'C 型肝炎',
  'ctx.prior_hcc': '既往肝癌',
  'ctx.afp': 'AFP',
  'ctx.afpUnit': 'ng/mL',
  'ctx.notes': '臨床備註…',
  'step.model': 'AI 模型',
  'step.modelRecommended': '建議',
  'step.features': '特徵與提取器',
  'step.run': '執行分析',
  'run.analysing': '分析中…',
  'run.again': '↺ 重新執行',
  'run.start': '執行分析（空白鍵）',
  'run.failed': '分析失敗',
  'rag.noneTitle': '尚未載入指引',
  'rag.noneBody': '將 PDF 放入 {path} → 匯入。',

  'report.title': 'AI 報告',
  'report.structured': '結構化',
  'report.raw': '原始',
  'report.emptyTitle': '尚無報告',
  'report.emptyBody': '上傳影像並執行分析',
  'right.collapse': '收合 ]',
  'right.expand': '展開 ]',

  'toast.complete': '分析完成 — 報告已就緒',
  'toast.failed': '分析失敗',

  'shortcuts.title': '鍵盤快捷鍵',
  'shortcuts.closeHint': '點擊任意處關閉 · Esc',
  'sc.theme': '切換深色 / 淺色主題',
  'sc.run': '執行分析（已載入影像時）',
  'sc.left': '切換左側面板',
  'sc.right': '切換右側面板',
  'sc.list': '顯示快捷鍵清單',
  'sc.esc': '關閉彈出視窗',

  'upload.uploading': '上傳中…',
  'upload.dropHere': '將檔案拖放至此',
  'upload.release': '放開以上傳',
  'upload.browse': '拖放檔案或點擊瀏覽',
  'upload.formats': 'DICOM · NIfTI · JPG/PNG · 上限 500 MB',
  'upload.errTooBig': '一個或多個檔案超過 500 MB',
  'upload.errMinSlices': '請至少上傳 2 張 DICOM 切片。',
  'upload.errFailed': '上傳失敗',

  'pt.dicom': 'DICOM',
  'pt.segment': '分割',
  'pt.radiomics': '放射組學',
  'pt.llmrag': 'LLM+RAG',
  'pt.done': '完成',
  'pt.error': '錯誤：{err}',
  'pt.prepare': '準備',
  'pt.features': '特徵',
  'pt.airag': 'AI + RAG',

  'lirads.LR-1': '確定良性',
  'lirads.LR-2': '可能良性',
  'lirads.LR-3': '中等可能性',
  'lirads.LR-4': '可能為肝癌',
  'lirads.LR-5': '確定為肝癌',
  'lirads.LR-M': '惡性（非肝癌）',
  'lirads.LR-TIV': '靜脈內腫瘤',
  'lirads.Indeterminate': '無法判定',

  'ai.yes': '是',
  'ai.no': '否',
  'ai.majorFeatures': '主要特徵',
  'ai.ancillaryFeatures': '輔助特徵',
  'ai.radiomicFeatures': '放射組學特徵',
  'ai.attention': '模型注意力 (CNN)',
  'ai.attentionHint': 'CNN 主幹關注的區域 — 顏色越暖表示活化越高。點擊放大。',
  'ai.collapse': '▲ 收合',
  'ai.featuresCount': '▼ {n} 項特徵',
  'ai.approved': '✓ 已核准',
  'ai.changesRequested': '⚠ 要求修改',
  'ai.by': '審查者',
  'ai.radiologistReview': '放射科醫師審查',
  'ai.nameId': '姓名 / 編號',
  'ai.namePlaceholder': '例：王醫師 / RAD-001',
  'ai.commentsOptional': '備註（選填）',
  'ai.notes': '備註…',
  'ai.saving': '儲存中…',
  'ai.approve': '✓ 核准',
  'ai.requestChanges': '⚠ 要求修改',
  'ai.ragAugmented': 'RAG 強化',
  'ai.downloadPdf': '下載 PDF',
  'ai.signOffRequired': '需要簽核',
  'ai.fhirJson': 'FHIR R4 JSON',
  'ai.gen': '產生中…',
  'ai.copied': '✓ 已複製',
  'ai.copy': '複製',
  'ai.exportHint': '需先簽核才能匯出 PDF 與 FHIR。',
  'ai.lesions': '病灶（{n}）',
  'ai.differential': '鑑別診斷',
  'ai.staging': '分期',
  'ai.bclcStage': 'BCLC 分期',
  'ai.vascular': '血管侵犯',
  'ai.recommendations': '建議',
  'ai.citations': '指引引用',
  'ai.disclaimer': '⚠ AI 僅供決策輔助。臨床使用前須經放射科醫師審查。',

  'hist.title': '工作階段紀錄',
  'hist.loading': '載入中…',
  'hist.empty': '尚無分析紀錄',
  'hist.lirads': 'LI-RADS',
  'hist.bclc': 'BCLC',
  'hist.time': '時間',

  'dv.prevNext': '上一張 / 下一張切片',
  'dv.navigate': '瀏覽切片',
  'dv.zoom': '放大 / 縮小',
  'dv.contrast': '調整對比',
  'dv.brightness': '調整亮度',
  'dv.resetView': '重設視圖',
  'dv.toggleShortcuts': '切換快捷鍵',
  'dv.inProgress': '分析進行中…',
  'dv.liver': '肝臟',
  'dv.tumour': '腫瘤',
  'dv.lung': '肺',
  'dv.colon': '結腸',
  'dv.resetR': '重設 [R]',
  'dv.overlayOn': '疊圖開',
  'dv.overlayOff': '疊圖關',
  'dv.wlHint': '拖曳調整窗位/窗寬 · Ctrl+滾輪縮放',
  'dv.noScan': '尚未載入影像',
  'dv.uploadHint': '使用左側面板上傳 DICOM 檔案',
  'dv.pressHelp': '按 ? 查看鍵盤快捷鍵',
  'dv.slice': '切片 {n}',
  'dv.shortcutsTitle': '鍵盤快捷鍵',
  'dv.closeHint': '點擊任意處關閉',
}

const DICTS: Record<Lang, Record<TKey, string>> = { en, zh }

function interpolate(s: string, vars?: Record<string, string | number>) {
  if (!vars) return s
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`))
}

interface I18nValue {
  lang: Lang
  setLang: (l: Lang) => void
  toggle: () => void
  t: (key: TKey, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nValue | null>(null)

const STORAGE_KEY = 'v2-lang'

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'zh' || saved === 'en' ? saved : 'en'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang)
    document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : 'en'
  }, [lang])

  const setLang = useCallback((l: Lang) => setLangState(l), [])
  const toggle = useCallback(() => setLangState(l => (l === 'en' ? 'zh' : 'en')), [])
  const t = useCallback(
    (key: TKey, vars?: Record<string, string | number>) =>
      interpolate(DICTS[lang][key] ?? en[key] ?? key, vars),
    [lang],
  )

  const value = useMemo(() => ({ lang, setLang, toggle, t }), [lang, setLang, toggle, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within LanguageProvider')
  return ctx
}
