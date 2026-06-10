import { useCallback, useEffect, useRef, useState } from 'react'
import { analysisApi } from '../services/api'
import type { AnalysisJob, DiagnosticReport, PatientContext, SignOffDecision } from '../types'

export function useAnalysis() {
  const [job, setJob] = useState<AnalysisJob | null>(null)
  const [slices, setSlices] = useState<string[]>([])
  const [rawSlices, setRawSlices] = useState<string[]>([])
  const [report, setReport] = useState<DiagnosticReport | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<number | null>(null)

  const stopPolling = () => {
    if (pollRef.current !== null) { window.clearInterval(pollRef.current); pollRef.current = null }
  }

  const start = useCallback(async (studyId: string, ctx?: PatientContext, model?: string) => {
    setJob(null); setSlices([]); setRawSlices([]); setReport(null)
    stopPolling()
    const newJob = await analysisApi.start(studyId, ctx, model)
    setJob(newJob)

    let finished = false
    const finalize = () => {
      if (finished) return
      finished = true
      stopPolling()
      analysisApi.slices(newJob.job_id).then(r => { setSlices(r.slices); setRawSlices(r.raw_slices ?? []) })
      analysisApi.report(newJob.job_id).then(setReport)
    }

    // Fallback when the WebSocket can't connect or drops mid-run: poll status so
    // the UI never gets stuck on "processing".
    const startPolling = () => {
      if (pollRef.current !== null || finished) return
      pollRef.current = window.setInterval(async () => {
        try {
          const j = await analysisApi.status(newJob.job_id)
          setJob(prev => prev ? { ...prev, ...j } : j)
          if (j.status === 'complete') finalize()
          else if (j.status === 'failed') { finished = true; stopPolling() }
        } catch { /* transient — keep polling */ }
      }, 1500)
    }

    // Derive host from the page (works when accessed from another machine), and
    // pick ws/wss to match http/https.
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.hostname}:8000/api/analysis/ws/${newJob.job_id}`)
    wsRef.current = ws
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as Partial<AnalysisJob>
      setJob(prev => prev ? { ...prev, ...data } : prev)
      if (data.status === 'complete') { ws.close(); finalize() }
      if (data.status === 'failed') { finished = true; ws.close() }
    }
    ws.onerror = () => ws.close()
    ws.onclose = () => { if (!finished) startPolling() }
    return newJob
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    stopPolling()
    setJob(null); setSlices([]); setRawSlices([]); setReport(null)
  }, [])

  useEffect(() => { return () => { wsRef.current?.close(); stopPolling() } }, [])

  const signOff = useCallback(
    async (radiologist_name: string, decision: SignOffDecision, comments?: string) => {
      if (!job) return
      const updated = await analysisApi.signOff(job.job_id, { radiologist_name, decision, comments })
      setJob(updated)
    },
    [job],
  )

  return { job, slices, rawSlices, report, start, signOff, reset }
}
