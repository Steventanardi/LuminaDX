import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import clsx from 'clsx'
import { dicomApi } from '../services/api'
import { useI18n } from '../i18n'
import type { UploadResponse } from '../types'

interface Props {
  onUploaded: (res: UploadResponse) => void
  cancerType?: string
  isDark?: boolean
}

function _detectType(files: File[]): 'nifti' | 'image' | 'dicom' {
  const first = files[0]?.name ?? ''
  if (first.endsWith('.nii.gz') || first.endsWith('.nii')) return 'nifti'
  if (/\.(jpg|jpeg|png)$/i.test(first)) return 'image'
  return 'dicom'
}

export default function UploadPanel({ onUploaded, cancerType = 'liver', isDark = false }: Props) {
  const { t } = useI18n()
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return
    setError(null)
    if (accepted.some(f => f.size > 500 * 1024 * 1024)) { setError(t('upload.errTooBig')); return }
    if (_detectType(accepted) === 'dicom' && accepted.length < 2) { setError(t('upload.errMinSlices')); return }
    setUploading(true)
    try { onUploaded(await dicomApi.upload(accepted, cancerType)) }
    catch (e: unknown) { setError(e instanceof Error ? e.message : t('upload.errFailed')) }
    finally { setUploading(false) }
  }, [onUploaded, cancerType, t])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/dicom': ['.dcm', '.DCM'], 'application/octet-stream': ['.dcm', '.nii', '.nii.gz'], 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
    multiple: true, disabled: uploading,
  })

  return (
    <div className="space-y-2">
      <div {...getRootProps()} className={clsx(
        'border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all duration-200',
        isDragActive ? 'border-accent bg-accent/8 scale-[1.01]'
          : isDark ? 'border-white/[0.08] hover:border-accent/40 hover:bg-accent/5' : 'border-slate-200/80 hover:border-accent/40 hover:bg-accent/5',
        uploading && 'opacity-50 cursor-not-allowed scale-100',
      )}>
        <input {...getInputProps()} />
        {uploading ? (
          <div className="space-y-1.5">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-slate-400 text-xs font-medium">{t('upload.uploading')}</p>
          </div>
        ) : isDragActive ? (
          <div className="space-y-1">
            <p className="text-accent text-sm font-semibold">{t('upload.dropHere')}</p>
            <p className="text-accent/60 text-xs">{t('upload.release')}</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            <svg className={clsx('w-7 h-7 mx-auto', isDark ? 'text-slate-600' : 'text-slate-300')} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            <p className={clsx('text-xs font-medium', isDark ? 'text-slate-300' : 'text-slate-600')}>{t('upload.browse')}</p>
            <p className="text-slate-400 text-[10px]">{t('upload.formats')}</p>
          </div>
        )}
      </div>
      {error && (
        <p className={clsx('text-xs rounded-lg px-2.5 py-1.5 border', isDark ? 'text-red-400 bg-red-950/20 border-red-900/30' : 'text-red-600 bg-red-50/80 border-red-200/60')}>{error}</p>
      )}
    </div>
  )
}

