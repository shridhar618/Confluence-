import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import { RefreshCw } from 'lucide-react'

import api from '../utils/api'

const STATUS_STYLES = {
  pending: 'text-warn border-warn/20 bg-warn/10',
  todo: 'text-warn border-warn/20 bg-warn/10',
  in_progress: 'text-accent border-accent/20 bg-accent/10',
  blocked: 'text-danger border-danger/20 bg-danger/10',
  completed: 'text-success border-success/20 bg-success/10',
}

function formatNumber(value) {
  return Number(value || 0).toFixed(2).replace(/\.00$/, '')
}

export default function MyWorkPage() {
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formByAssignment, setFormByAssignment] = useState({})
  const [submittingId, setSubmittingId] = useState(null)

  const loadAssignments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/work/assignments')
      setAssignments(res.data.assignments || [])
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load assignments.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAssignments()
  }, [loadAssignments])

  const updateForm = (assignmentId, key, value) => {
    setFormByAssignment(prev => ({
      ...prev,
      [assignmentId]: {
        completed_units: '',
        note: '',
        ...prev[assignmentId],
        [key]: value,
      },
    }))
  }

  const submitProgress = async assignmentId => {
    const form = formByAssignment[assignmentId] || {}
    setSubmittingId(assignmentId)
    setError('')
    try {
      await api.post(`/work/assignments/${assignmentId}/progress`, {
        completed_units: Number(form.completed_units || 0),
        note: form.note || '',
      })
      setFormByAssignment(prev => ({
        ...prev,
        [assignmentId]: { completed_units: '', note: '' },
      }))
      await loadAssignments()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to submit progress.')
    } finally {
      setSubmittingId(null)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">My Work</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">
              View assigned work and submit progress updates
            </p>
          </div>
          <button
            onClick={loadAssignments}
            className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono"
          >
            <RefreshCw size={13} className="inline mr-1.5" />
            Refresh
          </button>
        </div>

        {error && <p className="text-xs text-danger">{error}</p>}

        <div className="space-y-4">
          {loading ? (
            <div className="glass rounded-2xl border border-white/5 px-5 py-6 text-xs text-slate-500">Loading assignments...</div>
          ) : !assignments.length ? (
            <div className="glass rounded-2xl border border-white/5 px-5 py-6 text-xs text-slate-500">No work assignments yet.</div>
          ) : (
            assignments.map(item => {
              const form = formByAssignment[item.id] || { completed_units: '', note: '' }
              return (
                <div key={item.id} className="glass rounded-2xl border border-white/5 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{item.title}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Assigned by {item.assigned_by_user?.username} • Due {item.due_date ? format(new Date(item.due_date), 'MMM dd, yyyy') : 'Not set'}
                      </p>
                      {!!item.breadcrumbs?.length && (
                        <p className="text-[11px] text-slate-500 mt-1">{item.breadcrumbs.map(crumb => crumb.title).join(' / ')}</p>
                      )}
                    </div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${STATUS_STYLES[item.status] || STATUS_STYLES.pending}`}>
                      {item.status}
                    </span>
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

                  <div className="mt-5 grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
                      <p className="text-xs font-bold text-white mb-3">Submit Progress</p>
                      {item.is_leaf ? (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Completed Units</label>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={form.completed_units}
                              onChange={event => updateForm(item.id, 'completed_units', event.target.value)}
                              className="w-full rounded-xl border border-white/10 bg-bg-800 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Note</label>
                            <textarea
                              rows={3}
                              value={form.note}
                              onChange={event => updateForm(item.id, 'note', event.target.value)}
                              className="w-full rounded-xl border border-white/10 bg-bg-800 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                            />
                          </div>
                          <button
                            onClick={() => submitProgress(item.id)}
                            disabled={submittingId === item.id}
                            className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 disabled:opacity-50"
                          >
                            {submittingId === item.id ? 'Submitting...' : 'Submit Update'}
                          </button>
                        </div>
                      ) : (
                        <p className="text-xs leading-relaxed text-slate-400">
                          Progress is submitted on leaf subtasks. Parent task progress is derived automatically from the task tree.
                        </p>
                      )}
                    </div>

                    <div className="rounded-2xl border border-white/8 bg-white/5 overflow-hidden">
                      <div className="px-4 py-3 border-b border-white/8 flex items-center justify-between">
                        <p className="text-xs font-bold text-white">Recent Updates</p>
                        <span className="text-[10px] text-slate-500 font-mono">{item.progress_updates?.length || 0} entries</span>
                      </div>
                      <div className="max-h-64 overflow-y-auto">
                        {!item.progress_updates?.length ? (
                          <p className="text-xs text-slate-500 px-4 py-5">No progress updates submitted yet.</p>
                        ) : (
                          item.progress_updates.map(update => (
                            <div key={update.id} className="px-4 py-3 border-b border-white/8 last:border-b-0">
                              <div className="flex items-center justify-between gap-3">
                                <p className="text-xs font-semibold text-white">{formatNumber(update.completed_units)} units</p>
                                <span className="text-[10px] text-slate-500 font-mono">
                                  {format(new Date(update.created_at), 'MMM dd HH:mm')}
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 mt-1">{update.note || 'No note provided.'}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </motion.div>
  )
}
