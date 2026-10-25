import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, AlertTriangle, Users, MessageSquare,
  Lock, RefreshCw, Send, Eye, Cpu
} from 'lucide-react'
import { getGhostSocket } from '../utils/ghostSocket'
import { useAuth } from '../context/AuthContext'

function RiskBar({ score }) {
  const color = score >= 60 ? 'bg-danger' : score >= 30 ? 'bg-warn' : 'bg-success'
  const text  = score >= 60 ? 'text-danger' : score >= 30 ? 'text-warn' : 'text-success'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-bg-900 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      <span className={`text-[10px] font-mono font-bold ${text} w-8`}>{score}%</span>
    </div>
  )
}

export default function GhostAdminPanel() {
  const { token } = useAuth()
  const socket = getGhostSocket()
  const [sessions, setSessions] = useState([])
  const [alerts, setAlerts]     = useState([])
  const [selected, setSelected] = useState(null)
  const [adminMsg, setAdminMsg] = useState('')
  const [sending, setSending]   = useState(false)
  const authToken               = token || localStorage.getItem('token')

  const getAuthHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    Authorization: `Bearer ${authToken}`,
  }), [authToken])

  const fetchSessions = useCallback(async () => {
    if (!authToken) return
    const res  = await fetch('/api/ghost-sessions', {
      headers: { Authorization: `Bearer ${authToken}` },
    })
    const data = await res.json()
    if (!res.ok) return
    setSessions(data)
    // keep selected in sync
    if (selected) {
      const updated = data.find(s => s.session_id === selected.session_id)
      if (updated) setSelected(updated)
    }
  }, [authToken, selected])

  useEffect(() => {
    socket.emit('join_admin_room')
    fetchSessions()

    socket.on('trap_triggered', alert => {
      setAlerts(prev => [alert, ...prev].slice(0, 8))
      fetchSessions()
    })
    socket.on('ghost_user_message', () => fetchSessions())
    socket.on('ghost_bot_reply',    () => fetchSessions())
    socket.on('ghost_mode_changed', () => fetchSessions())
    socket.on('user_frozen',        () => fetchSessions())

    return () => {
      socket.off('trap_triggered')
      socket.off('ghost_user_message')
      socket.off('ghost_bot_reply')
      socket.off('ghost_mode_changed')
      socket.off('user_frozen')
    }
  }, [fetchSessions, socket])

  const takeControl = async (sessionId, mode) => {
    if (!authToken) return
    await fetch('/api/ghost-takeover', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId, mode }),
    })
    fetchSessions()
  }

  const sendAdminReply = async () => {
    if (!adminMsg.trim() || !selected || !authToken) return
    setSending(true)
    await fetch('/api/ghost-admin-reply', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        session_id: selected.session_id,
        message: adminMsg.trim(),
      }),
    })
    setAdminMsg('')
    setSending(false)
    fetchSessions()
  }

  const freezeUser = async (user) => {
    if (!authToken) return
    await fetch('/api/ghost-freeze', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ user }),
    })
    fetchSessions()
  }

  const suspiciousSessions = sessions.filter(s => s.risk_score >= 40)

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="h-full overflow-y-auto"
    >
      <div className="px-6 py-6 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">Ghost Mode — Admin Dashboard</h1>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-1">
              Real-time honeypot monitoring · intervention · session control
            </p>
          </div>
          <motion.button whileHover={{ rotate: 180 }} transition={{ duration: 0.35 }}
            onClick={fetchSessions}
            className="p-2 rounded-lg glass-light border border-white/8 text-slate-400 hover:text-accent"
          >
            <RefreshCw size={15} />
          </motion.button>
        </div>

        {/* Stat strip */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Active Sessions', value: sessions.length, icon: Users, color: 'text-accent' },
            { label: 'High-Risk Users', value: suspiciousSessions.length, icon: AlertTriangle, color: 'text-danger' },
            { label: 'Manual Control', value: sessions.filter(s => s.mode === 'manual').length, icon: Cpu, color: 'text-warn' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="glass rounded-2xl p-4 border border-white/5">
              <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className={color} />
                <p className="text-[10px] font-mono text-slate-500 uppercase">{label}</p>
              </div>
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>

        {/* Live alerts */}
        <AnimatePresence>
          {alerts.length > 0 && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
              className="glass rounded-2xl p-5 border border-danger/20"
            >
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={15} className="text-danger" />
                <p className="text-sm font-bold text-white">Live Trap Alerts</p>
                <span className="ml-auto px-2 py-0.5 rounded-md bg-danger/10 border border-danger/20 text-[10px] text-danger font-mono">
                  {alerts.length} triggered
                </span>
              </div>
              <div className="space-y-2">
                {alerts.map((a, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                    className="rounded-xl bg-bg-800/70 border border-danger/15 p-3 grid grid-cols-[1fr_auto_auto] gap-3 items-center"
                  >
                    <div>
                      <span className="text-xs font-mono text-danger font-bold">{a.user}</span>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">"{a.message}"</p>
                    </div>
                    <span className="text-[10px] font-mono text-danger border border-danger/20 px-2 py-1 rounded-lg">
                      {a.risk_score}%
                    </span>
                    <span className="text-[10px] font-mono text-slate-600">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-[0.85fr_1.15fr] gap-6">

          {/* Session list */}
          <div className="glass rounded-2xl p-5 border border-white/5 space-y-3">
            <div className="flex items-center gap-2 mb-1">
              <Users size={15} className="text-accent" />
              <p className="text-sm font-bold text-white">Active Sessions</p>
            </div>
            {sessions.length === 0 && (
              <p className="text-xs text-slate-500 font-mono">No ghost sessions yet.</p>
            )}
            {sessions.map(sess => (
              <button key={sess.session_id} onClick={() => setSelected(sess)}
                className={`w-full text-left rounded-2xl border p-4 transition-colors ${
                  selected?.session_id === sess.session_id
                    ? 'bg-accent/10 border-accent/20'
                    : 'bg-bg-800/70 border-white/8 hover:border-accent/20'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-white font-mono">{sess.user}</span>
                  <div className="flex items-center gap-1.5">
                    {sess.frozen && (
                      <span className="px-1.5 py-0.5 rounded bg-accent/10 border border-accent/20 text-[9px] text-accent font-mono">FROZEN</span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded border text-[9px] font-mono ${
                      sess.mode === 'manual'
                        ? 'bg-warn/10 border-warn/20 text-warn'
                        : 'bg-success/10 border-success/20 text-success'
                    }`}>
                      {sess.mode === 'manual' ? '👤 MANUAL' : '🤖 AUTO'}
                    </span>
                  </div>
                </div>
                <RiskBar score={sess.risk_score} />
                <p className="text-[10px] text-slate-500 font-mono mt-1.5">
                  {sess.history.length} messages
                </p>
              </button>
            ))}
          </div>

          {/* Session detail */}
          <div className="glass rounded-2xl p-5 border border-white/5 flex flex-col gap-4">
            {!selected ? (
              <p className="text-xs text-slate-500 font-mono">Select a session to inspect and control.</p>
            ) : (
              <>
                {/* Controls */}
                <div className="flex flex-wrap gap-2 pb-3 border-b border-white/5">
                  <button
                    onClick={() => takeControl(selected.session_id, 'manual')}
                    disabled={selected.mode === 'manual'}
                    className="px-3 py-2 rounded-xl bg-warn/10 border border-warn/20 text-xs text-warn disabled:opacity-40"
                  >
                    <Cpu size={12} className="inline mr-1.5" />Take Control
                  </button>
                  <button
                    onClick={() => takeControl(selected.session_id, 'auto')}
                    disabled={selected.mode === 'auto'}
                    className="px-3 py-2 rounded-xl bg-success/10 border border-success/20 text-xs text-success disabled:opacity-40"
                  >
                    <Eye size={12} className="inline mr-1.5" />Release to AI
                  </button>
                  <button
                    onClick={() => freezeUser(selected.user)}
                    disabled={selected.frozen}
                    className="px-3 py-2 rounded-xl bg-danger/10 border border-danger/20 text-xs text-danger disabled:opacity-40 ml-auto"
                  >
                    <Lock size={12} className="inline mr-1.5" />
                    {selected.frozen ? 'Session Frozen' : 'Reveal & Freeze'}
                  </button>
                </div>

                {/* Chat history */}
                <div className="flex-1 overflow-y-auto space-y-2 max-h-[320px] pr-1">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageSquare size={13} className="text-accent" />
                    <p className="text-[10px] font-mono text-slate-500 uppercase">
                      Full conversation · {selected.user}
                    </p>
                  </div>
                  {selected.history.map((m, i) => (
                    <div key={i} className={`rounded-xl border p-3 text-xs ${
                      m.role === 'user'
                        ? 'bg-bg-800/70 border-white/8 ml-4'
                        : 'bg-danger/5 border-danger/15 mr-4'
                    }`}>
                      <p className={`text-[10px] font-mono mb-1 ${
                        m.role === 'user' ? 'text-accent' : 'text-danger/70'
                      }`}>
                        {m.role === 'user' ? `👤 ${selected.user}` : `👻 ghost · ${m.mode || 'auto'}`}
                        {m.sent_by && ` (admin: ${m.sent_by})`}
                        {m.risk_score > 0 && (
                          <span className="ml-2 text-danger">⚠ risk {m.risk_score}%</span>
                        )}
                      </p>
                      <p className="text-slate-300">{m.text}</p>
                    </div>
                  ))}
                  {selected.history.length === 0 && (
                    <p className="text-xs text-slate-600 font-mono">No messages yet.</p>
                  )}
                </div>

                {/* Admin reply (only when in manual mode) */}
                {selected.mode === 'manual' && !selected.frozen && (
                  <div className="border-t border-white/5 pt-3">
                    <p className="text-[10px] font-mono text-warn uppercase mb-2">
                      👤 You are in control — reply as Ghost AI
                    </p>
                    <div className="flex gap-2">
                      <input
                        value={adminMsg}
                        onChange={e => setAdminMsg(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && sendAdminReply()}
                        placeholder="Reply as Ghost AI..."
                        className="flex-1 px-3 py-2 rounded-xl bg-bg-800 border border-warn/20 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-warn/40"
                      />
                      <button
                        onClick={sendAdminReply}
                        disabled={sending}
                        className="px-3 py-2 rounded-xl bg-warn/10 border border-warn/20 text-warn disabled:opacity-40"
                      >
                        <Send size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
