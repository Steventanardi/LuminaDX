import axios from 'axios'
import type { AnalysisJob, DiagnosticReport, DicomStudy, PatientContext, UploadResponse } from '../types'

const http = axios.create({ baseURL: '/api' })

export const dicomApi = {
  upload: (files: File[]): Promise<UploadResponse> => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    return http.post<UploadResponse>('/dicom/upload', form).then(r => r.data)
  },
  preview: (studyId: string, n?: number): Promise<{ slices: string[]; count: number }> =>
    http.get(`/dicom/preview/${studyId}`, { params: n ? { n } : undefined }).then(r => r.data),
  listStudies: (): Promise<DicomStudy[]> =>
    http.get<DicomStudy[]>('/dicom/studies').then(r => r.data),
  deleteStudy: (id: string): Promise<void> =>
    http.delete(`/dicom/studies/${id}`).then(() => undefined),
  listFiles: (studyId: string): Promise<{ files: string[]; count: number }> =>
    http.get(`/dicom/files/${studyId}`).then(r => r.data),
}

export const analysisApi = {
  start: (studyId: string, ctx?: PatientContext): Promise<AnalysisJob> =>
    http.post<AnalysisJob>(`/analysis/start/${studyId}`, ctx).then(r => r.data),
  status: (jobId: string): Promise<AnalysisJob> =>
    http.get<AnalysisJob>(`/analysis/status/${jobId}`).then(r => r.data),
  report: (jobId: string): Promise<DiagnosticReport> =>
    http.get<DiagnosticReport>(`/analysis/report/${jobId}`).then(r => r.data),
  slices: (jobId: string): Promise<{ slices: string[]; raw_slices: string[]; count: number }> =>
    http.get(`/analysis/slices/${jobId}`).then(r => r.data),
  signOff: (jobId: string, data: { radiologist_name: string; decision: string; comments?: string }): Promise<AnalysisJob> =>
    http.post(`/analysis/signoff/${jobId}`, data).then(r => r.data),
  fhirUrl: (jobId: string): string => `/api/analysis/fhir/${jobId}`,
  history: (): Promise<AnalysisJob[]> =>
    http.get<AnalysisJob[]>('/analysis/history').then(r => r.data),
}

export const ragApi = {
  ingest: (): Promise<{ message: string }> =>
    http.post('/rag/ingest').then(r => r.data),
  query: (query: string, n_results = 5): Promise<{ context: string; found: boolean }> =>
    http.post('/rag/query', { query, n_results }).then(r => r.data),
  status: (): Promise<{ ready: boolean; chunks: number; pdf_count: number }> =>
    http.get('/rag/status').then(r => r.data),
}
