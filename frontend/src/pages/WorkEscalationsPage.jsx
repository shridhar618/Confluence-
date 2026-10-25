import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw } from 'lucide-react'

import api from '../utils/api'

const STATUS_STYLES = {
  open: 'text-danger border-danger/20 bg-danger/10',
  resolved: 'text-success border-success/20 bg-success/10',
}

const SEVERITY_STYLES = {
  low: 'text-success border-success/20 bg-success/10',
  medium: 'text-warn border-warn/20 bg-warn/10',
  high: 'text-danger border-danger/20 bg-danger/10',
}

export default function WorkEscalationsPage() {
  const sampleScenarios = [
    '2 employees are absent today, we can’t complete tickets',
    'This task is stuck for 3 days and no progress is happening',
    'Too many tasks are assigned to one person and deadlines are near',
  ]
  const [escalations, setEscalations] = useState([])
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [resolvingId, setResolvingId] = useState(null)
  const [suggesting, setSuggesting] = useState(false)
  const [creatingFromSuggestion, setCreatingFromSuggestion] = useState(false)
  const [suggestion, setSuggestion] = useState(null)
  const [suggestForm, setSuggestForm] = useState({
    assignment_id: '',
    message: '',
    include_team_context: true,
  })

  const loadEscalations = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [escalationsRes, assignmentsRes] = await Promise.all([
        api.get('/work/escalations'),
        api.get('/work/assignments'),
      ])
      setEscalations(escalationsRes.data.escalations || [])
      setAssignments((assignmentsRes.data.assignments || []).filter(item => item.status !== 'completed'))
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load escalations.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEscalations()
  }, [loadEscalations])

  useEffect(() => {
    if (!suggestForm.assignment_id && assignments.length) {
      setSuggestForm(prev => ({ ...prev, assignment_id: String(assignments[0].id) }))
    }
  }, [assignments, suggestForm.assignment_id])

  const resolveEscalation = async escalationId => {
    setResolvingId(escalationId)
    setError('')
    setSuccess('')
    try {
      const res = await api.patch(`/work/escalations/${escalationId}`, { status: 'resolved' })
      const updated = res.data.escalation
      setEscalations(prev => prev.map(item => (item.id === escalationId ? updated : item)))
      setSuccess('Escalation resolved.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to resolve escalation.')
    } finally {
      setResolvingId(null)
    }
  }

  const requestSuggestion = async event => {
    event.preventDefault()
    if (!suggestForm.message.trim()) {
      setError('Enter a short operational situation to generate a suggestion.')
      return
    }

    const selectedAssignmentId =
      suggestForm.assignment_id || (assignments[0] ? String(assignments[0].id) : '')

    setSuggesting(true)
    setError('')
    setSuccess('')
    setSuggestion(null)
    try {
      const res = await api.post('/work/escalations/suggest', {
        message: suggestForm.message.trim(),
        assignment_ids: selectedAssignmentId ? [Number(selectedAssignmentId)] : [],
        include_team_context: suggestForm.include_team_context,
      })
      setSuggestion(res.data)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to generate AI escalation suggestion.')
    } finally {
      setSuggesting(false)
    }
  }

  const createEscalationFromSuggestion = async () => {
    const fallbackAssignmentId = suggestion?.affected_assignment_ids?.[0]
    const assignmentId = Number(suggestForm.assignment_id || fallbackAssignmentId)

    if (!suggestion || !assignmentId) return
    setCreatingFromSuggestion(true)
    setError('')
    setSuccess('')
    try {
      const res = await api.post('/work/escalations', {
        assignment_id: assignmentId,
        reason: suggestion.draft_details || suggestion.reason,
      })
      setEscalations(prev => [res.data.escalation, ...prev])
      setSuccess('Escalation created from AI draft.')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create escalation from suggestion.')
    } finally {
      setCreatingFromSuggestion(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Work Escalations</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">
              Review and resolve assignment escalations
            </p>
          </div>
          <button
            onClick={loadEscalations}
            className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono"
          >
            <RefreshCw size={13} className="inline mr-1.5" />
            Refresh
          </button>
        </div>

        {error && <p className="text-xs text-danger">{error}</p>}
        {success && <p className="text-xs text-success">{success}</p>}

        <div className="glass rounded-2xl border border-white/5 p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={15} className="text-accent" />
            <div>
              <p className="text-sm font-bold text-white">AI Escalation Assistant</p>
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">
                Generate a grounded escalation draft from assignment context
              </p>
            </div>
          </div>

          <form onSubmit={requestSuggestion} className="grid gap-4 lg:grid-cols-[240px_1fr]">
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Assignment</label>
                <select
                  value={suggestForm.assignment_id}
                  onChange={event => setSuggestForm(prev => ({ ...prev, assignment_id: event.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-bg-800 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                  disabled={!assignments.length}
                >
                  <option value="">{assignments.length ? 'Select assignment' : 'No active assignments'}</option>
                  {assignments.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={suggestForm.include_team_context}
                  onChange={event => setSuggestForm(prev => ({ ...prev, include_team_context: event.target.checked }))}
                  className="rounded border-white/10 bg-bg-800"
                />
                Include team attendance/workload context
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-1.5">Situation</label>
                <textarea
                  rows={4}
                  value={suggestForm.message}
                  onChange={event => setSuggestForm(prev => ({ ...prev, message: event.target.value }))}
                  placeholder="Example: Two employees are absent today, ticket completion will be delayed."
                  className="w-full rounded-xl border border-white/10 bg-bg-800 px-3 py-2.5 text-sm text-white outline-none focus:border-accent/40"
                  required
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {sampleScenarios.map(sample => (
                  <button
                    key={sample}
                    type="button"
                    onClick={() => setSuggestForm(prev => ({ ...prev, message: sample }))}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-slate-300 hover:border-accent/30 hover:text-accent"
                  >
                    {sample}
                  </button>
                ))}
              </div>
              <button
                type="submit"
                disabled={suggesting || !assignments.length}
                className="rounded-xl border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 disabled:opacity-50"
              >
                {suggesting ? 'Analyzing situation...' : 'Generate Suggestion'}
              </button>
            </div>
          </form>

          {suggestion && (
            <div className="mt-5 rounded-2xl border border-white/8 bg-white/5 p-4 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Issue</p>
                  <p className="text-sm font-semibold text-white mt-1">{suggestion.reason}</p>
                </div>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${SEVERITY_STYLES[suggestion.severity] || SEVERITY_STYLES.medium}`}>
                  Severity: {suggestion.severity}
                </span>
              </div>

              <div className="grid gap-3 lg:grid-cols-3 text-xs">
                <div className="rounded-xl border border-white/8 bg-bg-900/40 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Operational Impact</p>
                  <p className="text-white mt-1">{suggestion.impact}</p>
                </div>
                <div className="rounded-xl border border-white/8 bg-bg-900/40 p-3 lg:col-span-2">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Risk Summary</p>
                  <p className="text-white mt-1">{suggestion.summary}</p>
                </div>
              </div>

              <div className="grid gap-3 lg:grid-cols-2 text-xs">
                <div className="rounded-xl border border-white/8 bg-bg-900/40 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Suggested Action</p>
                  <p className="text-white mt-1">{suggestion.suggestion}</p>
                </div>
                <div className="rounded-xl border border-white/8 bg-bg-900/40 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Draft Escalation Note</p>
                  <p className="text-sm text-slate-200 mt-2 leading-relaxed">{suggestion.draft_details}</p>
                </div>
              </div>

              {!!suggestion.affected_assignments?.length && (
                <div>
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider mb-2">Affected Assignments</p>
                  <div className="space-y-2">
                    {suggestion.affected_assignments.map(item => (
                      <div key={item.id} className="rounded-xl border border-white/8 bg-bg-900/40 px-3 py-2.5">
                        <p className="text-sm text-white">{item.title}</p>
                        <p className="text-[10px] text-slate-500 font-mono mt-1">
                          {item.status} · risk {item.capacity_risk?.level || 'low'} · {item.assignee_username || 'unknown'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={createEscalationFromSuggestion}
                disabled={creatingFromSuggestion}
                className="rounded-xl border border-success/30 bg-success/10 px-4 py-2.5 text-sm font-semibold text-success hover:bg-success/20 disabled:opacity-50"
              >
                {creatingFromSuggestion ? 'Creating...' : 'Create Escalation From Draft'}
              </button>
              {success && (
                <p className="text-[11px] text-success font-medium">Escalation created and added to the list.</p>
              )}
            </div>
          )}
        </div>

        <div className="glass rounded-2xl border border-white/5 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={15} className="text-danger" />
              <p className="text-xs font-bold text-white">Escalations</p>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">{escalations.length} items</span>
          </div>
          <div className="max-h-[70vh] overflow-y-auto">
            {loading ? (
              <p className="text-xs text-slate-500 px-5 py-6">Loading escalations...</p>
            ) : !escalations.length ? (
              <p className="text-xs text-slate-500 px-5 py-6">No escalations yet.</p>
            ) : (
              escalations.map(item => (
                <div key={item.id} className="px-5 py-4 border-b border-white/5 last:border-b-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{item.assignment?.title || item.assignment_title}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        Created by {item.created_by_username} • {item.reason || 'No reason provided.'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${STATUS_STYLES[item.status] || STATUS_STYLES.open}`}>
                        {item.status}
                      </span>
                      {item.status === 'open' && (
                        <button
                          type="button"
                          onClick={() => resolveEscalation(item.id)}
                          disabled={resolvingId === item.id}
                          className="rounded-xl border border-success/30 bg-success/10 px-3 py-2 text-xs font-semibold text-success hover:bg-success/20 disabled:opacity-50"
                        >
                          {resolvingId === item.id ? 'Resolving...' : 'Resolve'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
