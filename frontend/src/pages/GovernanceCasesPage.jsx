import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { format, formatDistanceToNow } from 'date-fns'
import {
  ShieldAlert, X, TrendingUp, CheckCircle2,
  AlertTriangle, RotateCcw, ArrowRight, MessageSquare, Eye, RefreshCw,
} from 'lucide-react'
import api from '../utils/api'

const STATUS_CONFIG = {
  open:          { label: 'Open',          color: 'text-warn',    bg: 'bg-warn/10 border-warn/20' },
  under_review:  { label: 'Under Review',  color: 'text-accent',  bg: 'bg-accent/10 border-accent/20' },
  warned:        { label: 'Warned',        color: 'text-warn',    bg: 'bg-warn/10 border-warn/20' },
  restricted:    { label: 'Restricted',    color: 'text-danger',  bg: 'bg-danger/10 border-danger/20' },
  resolved:      { label: 'Resolved',      color: 'text-success', bg: 'bg-success/10 border-success/20' },
  escalated:     { label: 'Escalated',     color: 'text-purple',  bg: 'bg-purple/10 border-purple/20' },
}

const ACTIONS = [
  { type: 'review',   label: 'Review',  icon: Eye,             tone: 'text-accent hover:bg-accent/10 border-accent/20' },
  { type: 'warn',     label: 'Warn',    icon: AlertTriangle,   tone: 'text-warn hover:bg-warn/10 border-warn/20' },
  { type: 'restrict', label: 'Restrict',icon: ShieldAlert,     tone: 'text-danger hover:bg-danger/10 border-danger/20' },
  { type: 'restore',  label: 'Restore', icon: RotateCcw,       tone: 'text-success hover:bg-success/10 border-success/20' },
  { type: 'escalate', label: 'Escalate',icon: ArrowRight,      tone: 'text-purple hover:bg-purple/10 border-purple/20' },
  { type: 'resolve',  label: 'Resolve', icon: CheckCircle2,    tone: 'text-success hover:bg-success/10 border-success/20' },
]

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

export default function GovernanceCasesPage() {
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedCase, setSelectedCase] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [noteText, setNoteText] = useState('')
  const [actionPending, setActionPending] = useState(null)

  const loadCases = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await api.get('/governance-cases', { params: statusFilter ? { status: statusFilter } : {} })
      setCases(res.data.cases || [])
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { loadCases() }, [loadCases])

  const openCase = async (caseId) => {
    setDetailLoading(true)
    setNoteText('')
    try {
      const res = await api.get(`/governance-cases/${caseId}`)
      setSelectedCase(res.data.case)
    } catch {
      setSelectedCase(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const takeAction = async (actionType) => {
    if (!selectedCase) return
    setActionPending(actionType)
    try {
      const res = await api.post(`/governance-cases/${selectedCase.id}/actions`, {
        action_type: actionType,
        note: noteText || undefined,
      })
      setSelectedCase(res.data.case)
      setNoteText('')
      loadCases()
    } catch {
      // surfaced implicitly by the button re-enabling; a toast system would be a nice follow-up
    } finally {
      setActionPending(null)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Governance Cases</h1>
          <p className="text-xs text-slate-500 mt-0.5">Cumulative risk escalations awaiting administrator review</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-accent/40"
          >
            <option value="">All statuses</option>
            {Object.keys(STATUS_CONFIG).map(s => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
          <button onClick={loadCases} className="w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-accent transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </motion.div>

      <div className="glass rounded-2xl border border-white/5 overflow-hidden">
        {loading && <div className="p-10 text-center text-xs text-slate-500">Loading cases...</div>}
        {!loading && error && <div className="p-10 text-center text-xs text-danger">Couldn't load governance cases.</div>}
        {!loading && !error && cases.length === 0 && (
          <div className="p-10 text-center">
            <ShieldAlert size={28} className="mx-auto text-slate-700 mb-2" />
            <p className="text-sm text-slate-400">No governance cases</p>
            <p className="text-[11px] text-slate-600 mt-1">Cases open automatically when a user's cumulative risk crosses the configured threshold</p>
          </div>
        )}
        {!loading && !error && cases.length > 0 && (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5 text-slate-500 uppercase text-[10px] tracking-wider">
                <th className="text-left px-4 py-3 font-semibold">Case</th>
                <th className="text-left px-4 py-3 font-semibold">User</th>
                <th className="text-left px-4 py-3 font-semibold">Risk</th>
                <th className="text-left px-4 py-3 font-semibold">Status</th>
                <th className="text-left px-4 py-3 font-semibold">Created</th>
                <th className="text-left px-4 py-3 font-semibold">Assigned</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-mono text-accent">{c.case_code}</td>
                  <td className="px-4 py-3 text-slate-300">{c.username} <span className="text-slate-600">({c.role})</span></td>
                  <td className="px-4 py-3 text-slate-300">{c.risk_score_at_open?.toFixed(2)}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-slate-500">{c.created_at ? formatDistanceToNow(new Date(c.created_at), { addSuffix: true }) : '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{c.assigned_admin_username || '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => openCase(c.id)} className="text-accent hover:text-accent/70 text-[11px] font-semibold">
                      Review →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <AnimatePresence>
        {selectedCase && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setSelectedCase(null)}
              className="fixed inset-0 bg-black/60 z-40"
            />
            <motion.div
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ duration: 0.25, ease: 'easeOut' }}
              className="fixed top-0 right-0 bottom-0 w-full max-w-lg glass border-l border-white/10 z-50 overflow-y-auto"
            >
              <div className="p-5 border-b border-white/5 flex items-center justify-between sticky top-0 glass z-10">
                <div>
                  <h2 className="text-sm font-bold text-white font-mono">{selectedCase.case_code}</h2>
                  <p className="text-[11px] text-slate-500">{selectedCase.username} · {selectedCase.role}</p>
                </div>
                <button onClick={() => setSelectedCase(null)} className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-slate-400 hover:text-white">
                  <X size={14} />
                </button>
              </div>

              <div className="p-5 space-y-5">
                <div className="flex items-center gap-3">
                  <StatusBadge status={selectedCase.status} />
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <TrendingUp size={11} /> Risk at open: {selectedCase.risk_score_at_open?.toFixed(2)}
                  </span>
                </div>

                <div className="glass-light rounded-xl p-3">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Trigger</p>
                  <p className="text-xs text-slate-300 leading-relaxed">{selectedCase.trigger}</p>
                </div>

                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Take action</p>
                  <div className="grid grid-cols-3 gap-2 mb-2">
                    {ACTIONS.map(({ type, label, icon: Icon, tone }) => (
                      <button
                        key={type}
                        disabled={actionPending !== null}
                        onClick={() => takeAction(type)}
                        className={`flex flex-col items-center gap-1 py-2.5 rounded-xl border bg-white/[0.02] transition-colors disabled:opacity-40 ${tone}`}
                      >
                        <Icon size={15} />
                        <span className="text-[10px] font-semibold">{actionPending === type ? '...' : label}</span>
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      placeholder="Optional note for this action..."
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-accent/40"
                    />
                    <button
                      onClick={() => takeAction('note')}
                      disabled={!noteText || actionPending !== null}
                      className="px-3 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-accent disabled:opacity-30 transition-colors"
                    >
                      <MessageSquare size={14} />
                    </button>
                  </div>
                </div>

                {selectedCase.risk_events?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Risk events ({selectedCase.risk_events.length})</p>
                    <div className="space-y-1.5">
                      {selectedCase.risk_events.map(ev => (
                        <div key={ev.id} className="flex items-center justify-between text-[11px] px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5">
                          <span className={ev.risk_level === 'high' ? 'text-danger' : 'text-warn'}>{ev.risk_level.toUpperCase()} · {ev.risk_score?.toFixed(2)}</span>
                          <span className="text-slate-600 font-mono">{ev.created_at ? format(new Date(ev.created_at), 'MMM d, HH:mm') : ''}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Action history</p>
                  {(!selectedCase.actions || selectedCase.actions.length === 0) ? (
                    <p className="text-[11px] text-slate-600">No actions taken yet</p>
                  ) : (
                    <div className="space-y-1.5">
                      {selectedCase.actions.map(a => (
                        <div key={a.id} className="px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-semibold text-slate-300 capitalize">{a.action_type}</span>
                            <span className="text-[10px] text-slate-600 font-mono">{a.created_at ? format(new Date(a.created_at), 'MMM d, HH:mm') : ''}</span>
                          </div>
                          <p className="text-[10px] text-slate-500 mt-0.5">by {a.admin_username}</p>
                          {a.note && <p className="text-[11px] text-slate-400 mt-1">{a.note}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
