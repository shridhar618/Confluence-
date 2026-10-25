import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import { ClipboardList, RefreshCw } from 'lucide-react'

import api from '../utils/api'

const STATUS_STYLES = {
  pending: 'text-warn border-warn/20 bg-warn/10',
  todo: 'text-warn border-warn/20 bg-warn/10',
  in_progress: 'text-accent border-accent/20 bg-accent/10',
  blocked: 'text-danger border-danger/20 bg-danger/10',
  completed: 'text-success border-success/20 bg-success/10',
}

const RISK_STYLES = {
  low: 'text-success border-success/20 bg-success/10',
  medium: 'text-warn border-warn/20 bg-warn/10',
  high: 'text-danger border-danger/20 bg-danger/10',
}

function formatNumber(value) {
  return Number(value || 0).toFixed(2).replace(/\.00$/, '')
}

export default function WorkAssignmentsPage() {
  const [assignments, setAssignments] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState({
    title: '',
    description: '',
    assigned_to_user_id: '',
    expected_units: '',
    weight: '1',
    due_date: '',
  })

  const loadPage = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [assignmentsRes, usersRes] = await Promise.all([
        api.get('/work/assignments'),
        api.get('/users'),
      ])
      setAssignments(assignmentsRes.data.assignments || [])
      setUsers(usersRes.data.users || [])
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load work assignments.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPage()
  }, [loadPage])

  const handleChange = event => {
    const { name, value } = event.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async event => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await api.post('/work/assignments', {
        ...form,
        assigned_to_user_id: Number(form.assigned_to_user_id),
        expected_units: Number(form.expected_units || 0),
        weight: Number(form.weight || 0),
      })
      setForm({
        title: '',
        description: '',
        assigned_to_user_id: '',
        expected_units: '',
        weight: '1',
        due_date: '',
      })
      setSuccess('Assignment created.')
      await loadPage()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create assignment.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Work Assignments</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">
              Create assignments and monitor simple KPI progress
            </p>
          </div>
          <button
            onClick={loadPage}
            className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono"
          >
            <RefreshCw size={13} className="inline mr-1.5" />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <form onSubmit={handleSubmit} className="xl:col-span-1 glass rounded-2xl p-5 border border-white/5 space-y-4">
            <div className="flex items-center gap-2">
              <ClipboardList size={16} className="text-accent" />
              <p className="text-sm font-bold text-white">New Assignment</p>
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Title</label>
              <input
                name="title"
                value={form.title}
                onChange={handleChange}
                required
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
              />
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Description</label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={4}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
              />
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Assign To</label>
              <select
                name="assigned_to_user_id"
                value={form.assigned_to_user_id}
                onChange={handleChange}
                required
                className="w-full rounded-xl border border-white/10 bg-bg-800 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
              >
                <option value="">Select a user</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.username} ({user.role})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Expected Units</label>
                <input
                  name="expected_units"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.expected_units}
                  onChange={handleChange}
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Weight</label>
                <input
                  name="weight"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.weight}
                  onChange={handleChange}
                  required
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Due Date</label>
              <input
                name="due_date"
                type="date"
                value={form.due_date}
                onChange={handleChange}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
              />
            </div>

            {error && <p className="text-xs text-danger">{error}</p>}
            {success && <p className="text-xs text-success">{success}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm font-semibold text-accent hover:bg-accent/20 disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create Assignment'}
            </button>
          </form>

          <div className="xl:col-span-2 glass rounded-2xl border border-white/5 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
              <p className="text-xs font-bold text-white">Assignments</p>
              <span className="text-[10px] text-slate-500 font-mono">{assignments.length} items</span>
            </div>
            <div className="max-h-[70vh] overflow-y-auto">
              {loading ? (
                <p className="text-xs text-slate-500 px-5 py-6">Loading assignments...</p>
              ) : !assignments.length ? (
                <p className="text-xs text-slate-500 px-5 py-6">No assignments created yet.</p>
              ) : (
                assignments.map(item => (
                  <div key={item.id} className="px-5 py-4 border-b border-white/5 last:border-b-0">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">{item.title}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          Assigned to {item.assigned_to_user?.username} by {item.assigned_by_user?.username}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${STATUS_STYLES[item.status] || STATUS_STYLES.pending}`}>
                          {item.status}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${RISK_STYLES[item.capacity_risk?.level] || RISK_STYLES.low}`}>
                          risk: {item.capacity_risk?.level || 'low'}
                        </span>
                      </div>
                    </div>

                    {item.description && <p className="text-xs text-slate-400 mt-3 leading-relaxed">{item.description}</p>}

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4 text-xs">
                      <div className="rounded-xl border border-white/8 bg-white/5 p-3">
                        <p className="text-slate-500 font-mono uppercase text-[10px]">Expected</p>
                        <p className="text-white font-semibold mt-1">{formatNumber(item.kpi?.expected_units)}</p>
                      </div>
                      <div className="rounded-xl border border-white/8 bg-white/5 p-3">
                        <p className="text-slate-500 font-mono uppercase text-[10px]">Completed</p>
                        <p className="text-white font-semibold mt-1">{formatNumber(item.kpi?.total_completed_units)}</p>
                      </div>
                      <div className="rounded-xl border border-white/8 bg-white/5 p-3">
                        <p className="text-slate-500 font-mono uppercase text-[10px]">Completion</p>
                        <p className="text-white font-semibold mt-1">{Math.round((item.kpi?.completion_ratio || 0) * 100)}%</p>
                      </div>
                      <div className="rounded-xl border border-white/8 bg-white/5 p-3">
                        <p className="text-slate-500 font-mono uppercase text-[10px]">Weighted Score</p>
                        <p className="text-white font-semibold mt-1">{formatNumber(item.kpi?.weighted_score)}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-x-5 gap-y-1 mt-4 text-[11px] text-slate-500">
                      <span>Weight: {formatNumber(item.weight)}</span>
                      <span>Due: {item.due_date ? format(new Date(item.due_date), 'MMM dd, yyyy') : 'Not set'}</span>
                      <span>Updates: {item.progress_updates?.length || 0}</span>
                    </div>

                    {!!item.capacity_risk?.reasons?.length && (
                      <div className="mt-4 rounded-xl border border-white/8 bg-bg-800/40 p-3">
                        <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-2">Capacity Risk Signals</p>
                        <div className="space-y-1">
                          {item.capacity_risk.reasons.map(reason => (
                            <p key={reason} className="text-xs text-slate-300">
                              {reason}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
