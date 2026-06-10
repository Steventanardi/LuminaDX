import axios from 'axios'
import type { AnalysisJob, DiagnosticReport, DicomStudy, PatientContext, UploadResponse, User } from '../types'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,   // send httpOnly auth cookie on every request
})

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string): Promise<User> =>
    http.post<User>('/auth/login', { email, password }).then(r => r.data),
  logout: (): Promise<void> =>
    http.post('/auth/logout').then(() => undefined),
  me: (): Promise<User> =>
    http.get<User>('/auth/me').then(r => r.data),
  changePassword: (currentPassword: string, newPassword: string): Promise<void> =>
    http.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }).then(() => undefined),
}

export const adminApi = {
  listUsers: (): Promise<User[]> =>
    http.get<User[]>('/auth/users').then(r => r.data),
  createUser: (data: { email: string; full_name: string; password: string; role?: string; department?: string }): Promise<User> =>
    http.post<User>('/auth/users', data).then(r => r.data),
  updateUser: (id: string, data: { full_name?: string; role?: string; department?: string; is_active?: boolean }): Promise<User> =>
    http.patch<User>(`/auth/users/${id}`, data).then(r => r.data),
  resetPassword: (id: string, newPassword: string): Promise<void> =>
    http.post(`/auth/users/${id}/reset-password`, { new_password: newPassword }).then(() => undefined),
}

// ── DICOM / upload ────────────────────────────────────────────────────────────

export const dicomApi = {
  upload: (files: File[], cancerType: string = 'liver'): Promise<UploadResponse> => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    return http.post<UploadResponse>(`/dicom/upload?cancer_type=${encodeURIComponent(cancerType)}`, form).then(r => r.data)
  },
  preview: (studyId: string, n?: number): Promise<{ slices: string[]; count: number }> =>
    http.get(`/dicom/preview/${studyId}`, { params: n ? { n } : undefined }).then(r => r.data),
  detect: (studyId: string): Promise<{ suggested_cancer_type: string; detection_confidence: string; detection_reason: string }> =>
    http.get(`/dicom/detect/${studyId}`).then(r => r.data),
  updateCancerType: (studyId: string, cancerType: string): Promise<void> =>
    http.patch(`/dicom/studies/${studyId}/cancer-type`, { cancer_type: cancerType }).then(() => undefined),
  listStudies: (): Promise<DicomStudy[]> =>
    http.get<DicomStudy[]>('/dicom/studies').then(r => r.data),
  deleteStudy: (id: string): Promise<void> =>
    http.delete(`/dicom/studies/${id}`).then(() => undefined),
  listFiles: (studyId: string): Promise<{ files: string[]; count: number }> =>
    http.get(`/dicom/files/${studyId}`).then(r => r.data),
}

// ── Analysis ──────────────────────────────────────────────────────────────────

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

// ── RAG ───────────────────────────────────────────────────────────────────────

export const ragApi = {
  ingest: (namespace?: string): Promise<{ message: string }> =>
    http.post('/rag/ingest', null, { params: namespace ? { namespace } : undefined }).then(r => r.data),
  query: (query: string, n_results = 5): Promise<{ context: string; found: boolean }> =>
    http.post('/rag/query', { query, n_results }).then(r => r.data),
  status: (): Promise<{ ready: boolean; chunks: number; pdf_count: number }> =>
    http.get('/rag/status').then(r => r.data),
}
