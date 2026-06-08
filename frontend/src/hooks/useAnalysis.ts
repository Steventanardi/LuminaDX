import { useCallback, useEffect, useRef, useState } from 'react'
import { analysisApi } from '../services/api'
import type { AnalysisJob, DiagnosticReport, PatientContext, SignOffDecision } from '../types'

export function useAnalysis() {
  const [job, setJob] = useState<AnalysisJob | null>(null)
  const [slices, setSlices] = useState<string[]>([])
  const [rawSlices, setRawSlices] = useState<string[]>([])
  const [report, setReport] = useState<DiagnosticReport | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const start = useCallback(async (studyId: string, ctx?: PatientContext) => {
    setJob(null); setSlices([]); setRawSlices([]); setReport(null)
    const newJob = await analysisApi.start(studyId, ctx)
    setJob(newJob)
    const ws = new WebSocket(`ws://localhost:8000/api/analysis/ws/${newJob.job_id}`)
    wsRef.current = ws
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as Partial<AnalysisJob>
      setJob(prev => prev ? { ...prev, ...data } : prev)
      if (data.status === 'complete') {
        ws.close()
        analysisApi.slices(newJob.job_id).then(r => { setSlices(r.slices); setRawSlices(r.raw_slices ?? []) })
        analysisApi.report(newJob.job_id).then(setReport)
      }
      if (data.status === 'failed') ws.close()
    }
    ws.onerror = () => ws.close()
    return newJob
  }, [])

  useEffect(() => { return () => wsRef.current?.close() }, [])

  const signOff = useCallback(
    async (radiologist_name: string, decision: SignOffDecision, comments?: string) => {
      if (!job) return
      const updated = await analysisApi.signOff(job.job_id, { radiologist_name, decision, comments })
      setJob(updated)
    },
    [job],
  )

  return { job, slices, rawSlices, report, start, signOff }
}
