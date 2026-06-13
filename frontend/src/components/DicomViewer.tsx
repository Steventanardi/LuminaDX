import clsx from 'clsx'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useI18n } from '../i18n'
import type { TKey } from '../i18n'

interface Props {
  slices: string[]
  rawSlices?: string[]
  modality: string | null
  phase?: string | null
  isRunning?: boolean
  cancerType?: string
}

// Per-cancer segmentation overlay legend. Only cancers whose pipeline actually
// draws masks have entries; image-based cancers (skin, breast) draw no masks so
// they get no legend (the "analyzed" view there is the enhanced image).
const SEG_LEGEND: Record<string, [string, TKey][]> = {
  liver:      [['rgba(255,165,0,0.85)', 'dv.liver'], ['rgba(220,20,60,0.85)', 'dv.tumour']],
  lung:       [['rgba(255,165,0,0.85)', 'dv.lung']],
  colorectal: [['rgba(255,165,0,0.85)', 'dv.colon']],
}

const SHORTCUTS: [string, TKey][] = [
  ['← / →', 'dv.prevNext'],
  ['↑ / ↓', 'dv.prevNext'],
  ['Scroll', 'dv.navigate'],
  ['Ctrl+Scroll', 'dv.zoom'],
  ['Drag L/R', 'dv.contrast'],
  ['Drag U/D', 'dv.brightness'],
  ['R', 'dv.resetView'],
  ['?', 'dv.toggleShortcuts'],
]

const MAX_THUMBS = 18

export default function DicomViewer({ slices, rawSlices, modality, phase, isRunning, cancerType }: Props) {
  const { t } = useI18n()
  const segLegend = SEG_LEGEND[cancerType ?? 'liver'] ?? []
  const [idx, setIdx]               = useState(0)
  const [splitView, setSplitView]   = useState(false)  // auto-enabled on analysis complete
  const [zoom, setZoom]             = useState(1)
  const [wl, setWl]                 = useState({ brightness: 1, contrast: 1 })
  const [dragging, setDragging]     = useState(false)
  const [dragStart, setDragStart]   = useState({ x: 0, y: 0, b: 1, c: 1 })
  const [showHelp, setShowHelp]     = useState(false)
  const canvasRef    = useRef<HTMLCanvasElement>(null)   // analyzed / overlay
  const rawCanvasRef = useRef<HTMLCanvasElement>(null)   // original / raw
  const containerRef = useRef<HTMLDivElement>(null)
  const filmstripRef = useRef<HTMLDivElement>(null)

  const hasOverlay = !!rawSlices?.length

  // Auto-enable split view whenever analysis finishes (overlay becomes available)
  useEffect(() => {
    if (hasOverlay) setSplitView(true)
  }, [hasOverlay])

  // In non-split mode: toggle between overlay and raw
  const [showOverlay, setShowOverlay] = useState(true)
  const active = (!splitView && hasOverlay && !showOverlay) ? rawSlices! : slices

  const thumbStep   = Math.max(1, Math.ceil(slices.length / MAX_THUMBS))
  const thumbIndices = Array.from({ length: Math.ceil(slices.length / thumbStep) }, (_, i) => i * thumbStep)
  const showFilmstrip = !isRunning && slices.length > 5

  // Draw a slice onto a specific canvas element
  const drawToCanvas = useCallback((
    canvas: HTMLCanvasElement | null,
    pool: string[],
    i: number,
    label: string,
  ) => {
    if (!canvas || !pool[i]) return
    const img = new Image()
    img.onload = () => {
      const ctx = canvas.getContext('2d')!
      canvas.width  = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)
      ctx.fillStyle = 'rgba(0,0,0,0.60)'
      ctx.fillRect(0, canvas.height - 28, canvas.width, 28)
      ctx.font = '12px monospace'
      ctx.fillStyle = label.includes('ORIGINAL') ? '#94a3b8' : '#facc15'
      const phaseLabel = phase ? ` ${phase.charAt(0).toUpperCase() + phase.slice(1)}` : ''
      ctx.fillText(
        `${modality ?? ''}${phaseLabel} ${label} | ${t('dv.slice', { n: `${i + 1} / ${pool.length}` })}`,
        8, canvas.height - 10,
      )
    }
    img.src = `data:image/jpeg;base64,${pool[i]}`
  }, [modality, phase, t])

  const redraw = useCallback((i: number) => {
    if (splitView && hasOverlay) {
      drawToCanvas(canvasRef.current,    slices,       i, '· ANALYZED')
      drawToCanvas(rawCanvasRef.current, rawSlices!,   i, '· ORIGINAL')
    } else {
      drawToCanvas(canvasRef.current, active, i, '')
    }
  }, [splitView, hasOverlay, slices, rawSlices, active, drawToCanvas])

  useEffect(() => { if (slices.length) { setIdx(0); redraw(0) } }, [slices, rawSlices, splitView])
  useEffect(() => { redraw(idx) }, [idx, redraw])

  // Scroll filmstrip active thumb into view
  useEffect(() => {
    if (!filmstripRef.current) return
    const activeTi = Math.floor(idx / thumbStep)
    const thumb = filmstripRef.current.children[activeTi] as HTMLElement
    thumb?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [idx, thumbStep])

  const handleKey = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return
    if (e.key === '?')      { setShowHelp(h => !h); return }
    if (e.key === 'Escape') { setShowHelp(false); return }
    if (e.key === 'r' || e.key === 'R') { setWl({ brightness: 1, contrast: 1 }); setZoom(1); return }
    const len = slices.length
    if (e.key === 'ArrowUp'    || e.key === 'ArrowRight') setIdx(p => Math.min(p + 1, len - 1))
    if (e.key === 'ArrowDown'  || e.key === 'ArrowLeft')  setIdx(p => Math.max(p - 1, 0))
  }, [slices.length])

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    if (e.ctrlKey) setZoom(z => Math.min(5, Math.max(0.25, z - e.deltaY * 0.001)))
    else setIdx(p => e.deltaY > 0 ? Math.min(p + 1, slices.length - 1) : Math.max(p - 1, 0))
  }, [slices.length])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    setDragging(true)
    setDragStart({ x: e.clientX, y: e.clientY, b: wl.brightness, c: wl.contrast })
  }, [wl])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return
    setWl({
      brightness: Math.max(0.1, Math.min(4, dragStart.b - (e.clientY - dragStart.y) * 0.005)),
      contrast:   Math.max(0.1, Math.min(4, dragStart.c + (e.clientX - dragStart.x) * 0.008)),
    })
  }, [dragging, dragStart])

  const handleMouseUp = useCallback(() => setDragging(false), [])

  const wlAdjusted   = wl.brightness !== 1 || wl.contrast !== 1
  const zoomAdjusted = zoom !== 1
  const canvasStyle  = {
    imageRendering: 'pixelated' as const,
    transform: `scale(${zoom})`,
    filter: `brightness(${wl.brightness}) contrast(${wl.contrast})`,
  }

  if (!slices.length && !isRunning) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-slate-800/80 flex items-center justify-center mx-auto">
            <svg className="w-9 h-9 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h14a2 2 0 012 2V19a2 2 0 01-2 2H5a2 2 0 01-2-2V5z" />
              <circle cx="12" cy="10" r="3" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 19c0-3.3 2.7-6 6-6s6 2.7 6 6" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-400">{t('dv.noScan')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('dv.uploadHint')}</p>
            <p className="text-[10px] text-slate-600 mt-1">{t('dv.pressHelp')}</p>
          </div>
        </div>
      </div>
    )
  }

  // ── Shared top-right toolbar ───────────────────────────────────────────────
  const toolbar = !isRunning && (
    <div className="absolute top-2 right-2 z-10 flex items-center gap-1.5" onMouseDown={e => e.stopPropagation()}>
      {(wlAdjusted || zoomAdjusted) && (
        <button onClick={() => { setWl({ brightness: 1, contrast: 1 }); setZoom(1) }}
          className="px-2 py-1 rounded-lg text-[10px] font-mono bg-slate-800/80 text-amber-400 border border-amber-700/40 hover:bg-slate-700 transition-colors">
          {t('dv.resetR')}
        </button>
      )}
      {/* Split / Single view toggle — only shown when overlay is available */}
      {hasOverlay && (
        <button
          onClick={() => setSplitView(s => !s)}
          className={clsx('px-2.5 py-1 rounded-lg text-xs font-semibold transition-all',
            splitView
              ? 'bg-accent text-white shadow-md shadow-accent/20'
              : 'bg-black/60 text-slate-400 border border-slate-700 hover:text-slate-200')}>
          {splitView ? 'Split ▪' : 'Split ◫'}
        </button>
      )}
      {/* Overlay toggle — only in single-view mode */}
      {hasOverlay && !splitView && (
        <button onClick={() => setShowOverlay(o => !o)}
          className={clsx('px-2.5 py-1 rounded-lg text-xs font-semibold transition-all',
            showOverlay ? 'bg-emerald-700/80 text-white' : 'bg-black/60 text-slate-400 border border-slate-700 hover:text-slate-200')}>
          {showOverlay ? t('dv.overlayOn') : t('dv.overlayOff')}
        </button>
      )}
      <button onClick={() => setShowHelp(h => !h)}
        className="w-7 h-7 rounded-lg bg-black/60 text-slate-400 border border-slate-700 hover:text-white flex items-center justify-center text-xs font-bold transition-colors">
        ?
      </button>
    </div>
  )

  // ── Help overlay ───────────────────────────────────────────────────────────
  const helpOverlay = showHelp && (
    <div className="absolute inset-0 z-20 bg-black/85 flex items-center justify-center"
      onClick={() => setShowHelp(false)} onMouseDown={e => e.stopPropagation()}>
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 w-72 space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">{t('dv.shortcutsTitle')}</h3>
          <button onClick={() => setShowHelp(false)} className="text-slate-500 hover:text-slate-200 text-xl leading-none">×</button>
        </div>
        <div className="space-y-2">
          {SHORTCUTS.map(([k, vKey], i) => (
            <div key={`${k}-${i}`} className="flex justify-between gap-4 text-xs">
              <kbd className="text-accent font-mono shrink-0">{k}</kbd>
              <span className="text-slate-400 text-right">{t(vKey)}</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 text-center">{t('dv.closeHint')}</p>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-full">

      {/* ── Canvas area ── */}
      <div
        ref={containerRef}
        className={clsx(
          'flex-1 relative flex overflow-hidden bg-black select-none min-h-0',
          splitView ? 'flex-col' : 'items-center justify-center',
          dragging ? 'cursor-grabbing' : 'cursor-crosshair',
        )}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {isRunning && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 z-10 gap-3">
            <div className="w-9 h-9 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            <p className="text-xs text-slate-400 tracking-wide">{t('dv.inProgress')}</p>
          </div>
        )}

        {splitView && hasOverlay ? (
          /* ── Split view: top = analyzed, bottom = original ── */
          <>
            {/* Top — Analyzed */}
            <div className="flex-1 relative flex items-center justify-center bg-black overflow-hidden min-h-0">
              <canvas ref={canvasRef} className="max-w-full max-h-full" style={canvasStyle} />
              {/* Analyzed label pill */}
              <div className="absolute top-2 left-2 z-10 flex items-center gap-1.5 bg-black/60 rounded-lg px-2.5 py-1.5 backdrop-blur-sm pointer-events-none">
                <div className="w-2 h-2 rounded-full bg-accent shrink-0" />
                <span className="text-[10px] font-bold text-slate-100 uppercase tracking-widest">Analyzed</span>
              </div>
              {/* Segmentation legend (only for cancers that draw masks) */}
              {segLegend.length > 0 && (
                <div className="absolute top-2 left-28 z-10 flex flex-col gap-1 bg-black/55 rounded-lg px-2.5 py-2 backdrop-blur-sm pointer-events-none">
                  {segLegend.map(([color, labelKey]) => (
                    <div key={labelKey} className="flex items-center gap-1.5">
                      <div className="w-3 h-3 rounded-sm" style={{ background: color }} />
                      <span className="text-[11px] text-slate-200 font-mono">{t(labelKey)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="h-px shrink-0 bg-white/[0.08] relative flex items-center justify-center">
              <span className="absolute text-[9px] font-bold uppercase tracking-[0.2em] text-slate-600 bg-black px-3">
                ▲ AI Analysis &nbsp;·&nbsp; Original ▼
              </span>
            </div>

            {/* Bottom — Original */}
            <div className="flex-1 relative flex items-center justify-center bg-black overflow-hidden min-h-0">
              <canvas ref={rawCanvasRef} className="max-w-full max-h-full" style={canvasStyle} />
              {/* Original label pill */}
              <div className="absolute top-2 left-2 z-10 flex items-center gap-1.5 bg-black/60 rounded-lg px-2.5 py-1.5 backdrop-blur-sm pointer-events-none">
                <div className="w-2 h-2 rounded-full bg-slate-400 shrink-0" />
                <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Original</span>
              </div>
            </div>
          </>
        ) : (
          /* ── Single view ── */
          <>
            <canvas ref={canvasRef} className="max-w-full max-h-full" style={canvasStyle} />
            {!isRunning && slices.length > 0 && showOverlay && segLegend.length > 0 && (
              <div className="absolute top-2 left-2 z-10 flex flex-col gap-1 bg-black/55 rounded-lg px-2.5 py-2 backdrop-blur-sm pointer-events-none">
                {segLegend.map(([color, labelKey]) => (
                  <div key={labelKey} className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm" style={{ background: color }} />
                    <span className="text-[11px] text-slate-200 font-mono">{t(labelKey)}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Shared toolbar (top-right) */}
        {toolbar}

        {/* W/L and zoom readouts */}
        {!isRunning && wlAdjusted && (
          <div className="absolute bottom-10 right-2 z-10 text-[10px] font-mono text-slate-400 bg-black/60 px-2 py-1 rounded-lg pointer-events-none">
            B:{wl.brightness.toFixed(2)} C:{wl.contrast.toFixed(2)}
          </div>
        )}
        {!isRunning && zoomAdjusted && (
          <div className="absolute bottom-10 left-2 z-10 text-[10px] font-mono text-slate-400 bg-black/60 px-2 py-1 rounded-lg pointer-events-none">
            {Math.round(zoom * 100)}%
          </div>
        )}
        {!isRunning && slices.length > 0 && !dragging && !wlAdjusted && (
          <div className="absolute bottom-2 right-2 z-10 text-[10px] text-slate-700 pointer-events-none">
            {t('dv.wlHint')}
          </div>
        )}

        {helpOverlay}
      </div>

      {/* ── Scrub slider ── */}
      {!isRunning && slices.length > 0 && (
        <div className="flex items-center gap-3 px-2 py-1 shrink-0 bg-black">
          <span className="text-slate-500 text-xs w-16 shrink-0 font-mono">{idx + 1} / {slices.length}</span>
          <input type="range" min={0} max={slices.length - 1} value={idx}
            onChange={e => setIdx(Number(e.target.value))}
            className="flex-1 h-1.5 accent-accent cursor-pointer" />
          <button onClick={() => setShowHelp(h => !h)}
            className="text-slate-600 hover:text-slate-400 text-xs font-mono transition-colors" title="Keyboard shortcuts (?)">?</button>
        </div>
      )}

      {/* ── Filmstrip ── */}
      {showFilmstrip && (
        <div
          ref={filmstripRef}
          className="flex gap-1 px-2 pb-2 overflow-x-auto shrink-0 bg-black"
          style={{ scrollbarWidth: 'thin' }}
        >
          {thumbIndices.map((sliceIdx, ti) => {
            const isActive = Math.floor(idx / thumbStep) === ti
            return (
              <button
                key={sliceIdx}
                onClick={() => setIdx(sliceIdx)}
                className={clsx(
                  'relative h-10 w-8 rounded overflow-hidden shrink-0 transition-all duration-150 ring-1',
                  isActive ? 'ring-accent scale-110 z-10' : 'ring-white/15 hover:ring-white/40 opacity-60 hover:opacity-100',
                )}
                title={`Slice ${sliceIdx + 1}`}
              >
                <img
                  src={`data:image/jpeg;base64,${slices[sliceIdx]}`}
                  className="h-full w-full object-cover"
                  alt=""
                  loading="lazy"
                />
                {isActive && <div className="absolute inset-x-0 bottom-0 h-0.5 bg-accent" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
