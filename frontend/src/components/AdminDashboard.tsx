import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { adminApi } from '../services/api'
import type { User, UserRole } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  isDark: boolean
  currentUser: User
}

const ROLE_LABELS: Record<UserRole, string> = {
  admin:           'Admin',
  chief_physician: 'Chief Physician',
  radiologist:     'Radiologist',
}

// Solid pill colors — role badges need to stand out on any glass surface
const ROLE_PILL: Record<UserRole, string> = {
  admin:           'bg-teal-600 text-white',
  chief_physician: 'bg-sky-500 text-white',
  radiologist:     'bg-slate-500 text-white',
}

// ── Shared style tokens (mirror App.tsx conventions) ─────────────────────────

const glass = (isDark: boolean) => clsx(
  'border',
  isDark ? 'bg-[#10151d] border-[#1f2835]' : 'bg-white border-[#e2e8ee]',
)

// Inputs: slightly more opaque than the panel so they're visible as distinct fields
const INPUT = (isDark: boolean) => clsx(
  'w-full rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-accent/50 transition-colors border',
  isDark
    ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-500'
    : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
)

const INPUT_SM = (isDark: boolean) => clsx(
  'rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-accent/50 transition-colors border',
  isDark
    ? 'bg-[#121924] border-[#1f2835] text-slate-200 placeholder:text-slate-500'
    : 'bg-white border-[#e2e8ee] text-slate-800 placeholder:text-slate-400',
)

const DIVIDER = (isDark: boolean) => isDark ? 'border-[#1f2835]' : 'border-[#e2e8ee]'

const BTN_GHOST = (isDark: boolean) => clsx(
  'rounded-lg border flex items-center justify-center transition-colors',
  isDark
    ? 'bg-[#121924] hover:bg-[#1a2230] border-[#1f2835] text-slate-300 hover:text-white'
    : 'bg-white hover:bg-slate-100 border-[#e2e8ee] text-slate-600 hover:text-slate-900',
)

// ── Create / Edit modal ───────────────────────────────────────────────────────

interface UserFormData {
  email: string; full_name: string; password: string; role: UserRole; department: string
}

function UserModal({
  mode, initial, isDark, onSave, onClose,
}: {
  mode: 'create' | 'edit'
  initial?: Partial<UserFormData & { id: string }>
  isDark: boolean
  onSave: (data: UserFormData & { id?: string }) => Promise<void>
  onClose: () => void
}) {
  const [form, setForm] = useState<UserFormData>({
    email:      initial?.email      ?? '',
    full_name:  initial?.full_name  ?? '',
    role:       (initial?.role as UserRole) ?? 'radiologist',
    department: initial?.department ?? '',
    password:   '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const set = (k: keyof UserFormData, v: string) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'create' && form.password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true); setError('')
    try { await onSave({ ...form, id: initial?.id }); onClose() }
    catch (err: unknown) { setError(err instanceof Error ? err.message : 'Save failed') }
    finally { setLoading(false) }
  }

  const IN = INPUT(isDark)
  const LABEL = clsx('block text-[10px] font-semibold uppercase tracking-widest mb-1.5',
    isDark ? 'text-slate-400' : 'text-slate-500')

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 "
      onClick={onClose}>
      <div className={clsx(glass(isDark), 'w-full max-w-md mx-4 rounded-2xl p-6 space-y-4 shadow-2xl')}
        onClick={e => e.stopPropagation()}>

        <h3 className={clsx('text-sm font-semibold', isDark ? 'text-slate-100' : 'text-slate-900')}>
          {mode === 'create' ? 'Create Doctor Account' : 'Edit Account'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className={LABEL}>Full Name</span>
              <input value={form.full_name} onChange={e => set('full_name', e.target.value)}
                placeholder="Dr. Jane Tan" required className={IN} />
            </label>
            <label className="block">
              <span className={LABEL}>Email</span>
              <input type="email" value={form.email} onChange={e => set('email', e.target.value)}
                placeholder="jane@hospital.com" required disabled={mode === 'edit'}
                className={clsx(IN, mode === 'edit' && 'opacity-50 cursor-default')} />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className={LABEL}>Role</span>
              <select value={form.role} onChange={e => set('role', e.target.value as UserRole)}
                className={IN}>
                <option value="radiologist" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Radiologist</option>
                <option value="chief_physician" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Chief Physician</option>
                <option value="admin" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Admin</option>
              </select>
            </label>
            <label className="block">
              <span className={LABEL}>Department</span>
              <input value={form.department} onChange={e => set('department', e.target.value)}
                placeholder="e.g. Radiology" className={IN} />
            </label>
          </div>

          <label className="block">
            <span className={LABEL}>
              {mode === 'create' ? 'Password' : 'New Password — blank to keep current'}
            </span>
            <input type="password" value={form.password} onChange={e => set('password', e.target.value)}
              placeholder={mode === 'create' ? 'Min 8 characters' : ''}
              required={mode === 'create'} className={IN} />
          </label>

          {error && (
            <p className={clsx('text-xs rounded-xl px-3 py-2 border',
              isDark
                ? 'bg-red-950/40 border-red-800/50 text-red-300'
                : 'bg-red-50 border-red-200 text-red-700')}>
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={loading}
              className="flex-1 py-2 rounded-xl bg-accent hover:bg-teal-700 active:bg-teal-800 text-white text-xs font-semibold transition-colors disabled:opacity-40 shadow-sm shadow-accent/20">
              {loading ? 'Saving…' : mode === 'create' ? 'Create Account' : 'Save Changes'}
            </button>
            <button type="button" onClick={onClose}
              className={clsx('flex-1 py-2 rounded-xl text-xs font-semibold border transition-colors',
                isDark
                  ? 'bg-[#121924] border-[#1f2835] text-slate-300 hover:bg-[#1a2230] hover:text-slate-100'
                  : 'bg-white border-[#e2e8ee] text-slate-600 hover:bg-slate-100 hover:text-slate-900')}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main dashboard ────────────────────────────────────────────────────────────

export default function AdminDashboard({ open, onClose, isDark, currentUser }: Props) {
  const [users, setUsers]           = useState<User[]>([])
  const [loading, setLoading]       = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [search, setSearch]         = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')

  const load = () => {
    setLoading(true)
    adminApi.listUsers().then(setUsers).catch(() => null).finally(() => setLoading(false))
  }

  useEffect(() => { if (open) load() }, [open])

  if (!open) return null

  const filtered = users.filter(u => {
    const q = search.toLowerCase()
    return (!q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || (u.department ?? '').toLowerCase().includes(q))
      && (roleFilter === 'all' || u.role === roleFilter)
  })

  const stats = {
    total:       users.length,
    active:      users.filter(u => u.is_active).length,
    admins:      users.filter(u => u.role === 'admin').length,
    chiefs:      users.filter(u => u.role === 'chief_physician').length,
    radiologists: users.filter(u => u.role === 'radiologist').length,
  }

  const handleToggleActive = async (u: User) => {
    if (u.id === currentUser.id) return
    await adminApi.updateUser(u.id, { is_active: !u.is_active })
    load()
  }
  const handleCreate = async (data: UserFormData & { id?: string }) => {
    await adminApi.createUser({ email: data.email, full_name: data.full_name, password: data.password, role: data.role, department: data.department || undefined })
    load()
  }
  const handleEdit = async (data: UserFormData & { id?: string }) => {
    if (!data.id) return
    await adminApi.updateUser(data.id, { full_name: data.full_name, role: data.role, department: data.department || undefined })
    if (data.password) await adminApi.resetPassword(data.id, data.password)
    load()
  }

  const D = DIVIDER(isDark)
  // Section tint — slightly lighter than the main glass panel
  const SECTION = isDark ? 'bg-[#121924]' : 'bg-slate-100'

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/30 "
        onClick={onClose}>

        <div className={clsx(glass(isDark), 'w-full max-w-3xl h-full flex flex-col shadow-2xl overflow-hidden')}
          onClick={e => e.stopPropagation()}>

          {/* ── Header ── */}
          <div className={clsx(SECTION, 'flex items-center justify-between px-6 py-4 border-b shrink-0', D)}>
            <div>
              <h2 className={clsx('text-sm font-semibold', isDark ? 'text-slate-100' : 'text-slate-900')}>
                User Management
              </h2>
              <p className={clsx('text-[10px] mt-0.5', isDark ? 'text-slate-400' : 'text-slate-500')}>
                Admin access · {currentUser.full_name}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowCreate(true)}
                className="flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-semibold bg-accent hover:bg-teal-700 text-white transition-colors shadow-sm">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add User
              </button>
              <button onClick={onClose} className={clsx(BTN_GHOST(isDark), 'w-8 h-8')}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* ── Stats ── */}
          <div className={clsx(SECTION, 'grid grid-cols-5 border-b shrink-0', D)}>
            {[
              { label: 'Total',        value: stats.total,        accent: isDark ? 'text-slate-100' : 'text-slate-900' },
              { label: 'Active',       value: stats.active,       accent: 'text-emerald-400' },
              { label: 'Admins',       value: stats.admins,       accent: 'text-teal-400' },
              { label: 'Chiefs',       value: stats.chiefs,       accent: 'text-sky-400' },
              { label: 'Radiologists', value: stats.radiologists, accent: isDark ? 'text-slate-300' : 'text-slate-600' },
            ].map((s, i, arr) => (
              <div key={s.label}
                className={clsx('flex flex-col items-center py-4',
                  i < arr.length - 1 && `border-r ${D}`)}>
                <span className={clsx('text-2xl font-bold font-mono leading-none', s.accent)}>
                  {s.value}
                </span>
                <span className={clsx('text-[10px] font-medium uppercase tracking-widest mt-1',
                  isDark ? 'text-slate-400' : 'text-slate-500')}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>

          {/* ── Filter bar ── */}
          <div className={clsx('flex items-center gap-2 px-4 py-3 border-b shrink-0', D)}>
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search name, email, department…"
              className={clsx(INPUT_SM(isDark), 'flex-1')} />
            <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}
              className={clsx(INPUT_SM(isDark), 'min-w-[140px]')}>
              <option value="all" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">All roles</option>
              <option value="admin" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Admin</option>
              <option value="chief_physician" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Chief Physician</option>
              <option value="radiologist" className="bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100">Radiologist</option>
            </select>
            <button onClick={load} title="Refresh" className={clsx(BTN_GHOST(isDark), 'w-8 h-8 shrink-0')}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            </button>
          </div>

          {/* ── User table ── */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32 gap-2">
                <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                <span className={clsx('text-xs', isDark ? 'text-slate-400' : 'text-slate-500')}>Loading…</span>
              </div>
            ) : filtered.length === 0 ? (
              <p className={clsx('text-center text-sm py-16', isDark ? 'text-slate-500' : 'text-slate-400')}>
                No users found
              </p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className={clsx('border-b', D, SECTION)}>
                    {['Name / Email', 'Role', 'Department', 'Last Login', 'Status', 'Actions'].map(h => (
                      <th key={h}
                        className={clsx('px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest',
                          isDark ? 'text-slate-300' : 'text-slate-600')}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(u => (
                    <tr key={u.id}
                      className={clsx(
                        'border-b transition-colors',
                        isDark ? `border-[#1f2835] hover:bg-[#121924]` : `border-[#e2e8ee] hover:bg-slate-100`,
                        !u.is_active && 'opacity-50',
                      )}>

                      {/* Name / Email */}
                      <td className="px-4 py-3">
                        <div className={clsx('font-medium', isDark ? 'text-slate-200' : 'text-slate-800')}>
                          {u.full_name}
                          {u.id === currentUser.id && (
                            <span className="ml-1.5 text-[9px] text-accent font-normal">(you)</span>
                          )}
                        </div>
                        <div className={clsx('mt-0.5 font-mono', isDark ? 'text-slate-400' : 'text-slate-500')}>
                          {u.email}
                        </div>
                      </td>

                      {/* Role */}
                      <td className="px-4 py-3">
                        <span className={clsx('px-2.5 py-1 rounded-full text-[10px] font-bold', ROLE_PILL[u.role as UserRole])}>
                          {ROLE_LABELS[u.role as UserRole] ?? u.role}
                        </span>
                      </td>

                      {/* Department */}
                      <td className={clsx('px-4 py-3 font-medium', isDark ? 'text-slate-200' : 'text-slate-700')}>
                        {u.department || <span className={clsx('italic font-normal', isDark ? 'text-slate-500' : 'text-slate-400')}>—</span>}
                      </td>

                      {/* Last login */}
                      <td className={clsx('px-4 py-3', isDark ? 'text-slate-400' : 'text-slate-500')}>
                        {u.last_login
                          ? new Date(u.last_login).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
                          : <span className="italic">Never</span>}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        <span className={clsx('px-2.5 py-1 rounded-full text-[10px] font-bold',
                          u.is_active ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white')}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button onClick={() => setEditTarget(u)}
                            className={clsx(
                              'px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-colors',
                              isDark
                                ? 'bg-[#121924] border-[#1f2835] text-slate-300 hover:bg-[#1a2230] hover:text-slate-100'
                                : 'bg-white border-[#e2e8ee] text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                            )}>
                            Edit
                          </button>
                          {u.id !== currentUser.id && (
                            <button onClick={() => handleToggleActive(u)}
                              title={u.is_active ? 'Deactivate' : 'Activate'}
                              className={clsx(
                                'px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-colors',
                                u.is_active
                                  ? isDark
                                    ? 'bg-red-950/40 border-red-800/40 text-red-300 hover:bg-red-900/60 hover:text-red-200'
                                    : 'bg-red-50/80 border-red-200 text-red-600 hover:bg-red-100'
                                  : isDark
                                    ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-300 hover:bg-emerald-900/60 hover:text-emerald-200'
                                    : 'bg-emerald-50/80 border-emerald-200 text-emerald-700 hover:bg-emerald-100',
                              )}>
                              {u.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* ── Footer ── */}
          <div className={clsx(SECTION, 'px-6 py-3 border-t shrink-0 text-[10px] leading-relaxed', D,
            isDark ? 'text-slate-500' : 'text-slate-400')}>
            Chief physicians can view all cases in their department (read-only).
            Radiologists see only their own cases. Permissions subject to hospital regulation.
          </div>
        </div>
      </div>

      {showCreate && (
        <UserModal mode="create" isDark={isDark} onSave={handleCreate} onClose={() => setShowCreate(false)} />
      )}
      {editTarget && (
        <UserModal
          mode="edit"
          initial={{ id: editTarget.id, email: editTarget.email, full_name: editTarget.full_name,
                     role: editTarget.role as UserRole, department: editTarget.department ?? '' }}
          isDark={isDark} onSave={handleEdit} onClose={() => setEditTarget(null)} />
      )}
    </>
  )
}
