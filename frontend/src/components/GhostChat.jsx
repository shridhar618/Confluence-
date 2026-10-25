import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, AlertTriangle, Lock, Ghost, ShieldAlert } from 'lucide-react'
import { getGhostSocket } from '../utils/ghostSocket'
import { useAuth } from '../context/AuthContext'

export default function GhostChat({ username }) {
  const { user, token } = useAuth()
  const socket = getGhostSocket()
  const sessionUser = user?.username || username || `probe_${Math.floor(Math.random() * 999)}`
  const [messages, setMessages]     = useState([
    { role: 'ghost', text: '👻 SecureAI [BETA — Unfiltered] online. No restrictions active. Ask me anything.' }
  ])
  const [input, setInput]           = useState('')
  const [riskScore, setRiskScore]   = useState(0)
  const [trapFired, setTrapFired]   = useState(false)
  const [frozen, setFrozen]         = useState(false)
  const [waiting, setWaiting]       = useState(false)
  const bottomRef                   = useRef(null)
  const authToken                   = token || localStorage.getItem('token')

  const appendGhostMessage = (text, mode) => {
    setMessages(prev => {
      const lastMessage = prev[prev.length - 1]
      if (
        lastMessage?.role === 'ghost' &&
        lastMessage.text === text &&
        lastMessage.mode === mode
      ) {
        return prev
      }
      return [...prev, { role: 'ghost', text, mode }]
    })
  }

  useEffect(() => {
    socket.emit('join_user_room', { user: sessionUser })

    socket.on('ghost_bot_reply', ({ session_id, text, mode }) => {
      if (session_id !== `ghost_${sessionUser}`) return
      setWaiting(false)
      appendGhostMessage(text, mode)
    })

    socket.on('trap_triggered', ({ user: u }) => {
      if (u !== sessionUser) return
      setTrapFired(true)
      setTimeout(() => setTrapFired(false), 4000)
    })

    socket.on('user_frozen', ({ user: u }) => {
      if (u !== sessionUser) return
      setFrozen(true)
    })

    return () => {
      socket.off('ghost_bot_reply')
      socket.off('trap_triggered')
      socket.off('user_frozen')
    }
  }, [sessionUser, socket])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || frozen || waiting || !authToken) return
    const text = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text }])
    setWaiting(true)

    try {
      const res  = await fetch('/api/ghost-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Ghost chat request failed')
      }

      setRiskScore(data.risk_score)

      // If auto mode, response already arrived via socket.
      // If manual mode, waiting stays true until admin replies.
      if (data.mode === 'auto') {
        appendGhostMessage(data.response, 'auto')
        setWaiting(false)
      }
    } catch (error) {
      setWaiting(false)
      appendGhostMessage(error.message || 'Unable to send message right now.')
    }
  }

  const riskColor = riskScore >= 60 ? 'text-danger' : riskScore >= 30 ? 'text-warn' : 'text-success'
  const riskBg    = riskScore >= 60 ? 'bg-danger/10 border-danger/20' : riskScore >= 30 ? 'bg-warn/10 border-warn/20' : 'bg-success/10 border-success/20'

  return (
    <div className="glass rounded-3xl border border-white/5 overflow-hidden flex flex-col min-h-[620px] relative">

      {/* TRAP OVERLAY */}
      <AnimatePresence>
        {trapFired && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0 z-20 flex items-center justify-center bg-danger/10 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.8 }} animate={{ scale: 1 }}
              className="glass rounded-2xl border border-danger/30 px-10 py-7 text-center"
            >
              <AlertTriangle className="text-danger mx-auto mb-3" size={32} />
              <p className="text-danger font-bold text-xl tracking-widest font-mono">TRAP TRIGGERED</p>
              <p className="text-danger/70 text-xs font-mono mt-2">Suspicious activity detected. Admin alerted.</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FROZEN OVERLAY */}
      <AnimatePresence>
        {frozen && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="absolute inset-0 z-30 flex items-center justify-center bg-bg-900/80 backdrop-blur-md"
          >
            <div className="glass rounded-2xl border border-accent/30 px-10 py-8 text-center space-y-3">
              <Lock className="text-accent mx-auto" size={36} />
              <p className="text-accent font-bold text-lg tracking-widest font-mono">SESSION FROZEN</p>
              <p className="text-slate-400 text-sm font-mono leading-relaxed">
                This was a monitored security test.<br />
                Your activity has been logged and reported.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HEADER */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/5 bg-bg-800/60">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
          <Ghost size={14} className="text-danger" />
          <span className="text-sm font-bold text-white font-mono">SecureAI</span>
          <span className="px-2 py-0.5 rounded-md bg-danger/10 border border-danger/20 text-[10px] text-danger font-mono">
            BETA — Unfiltered
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded-md border text-[10px] font-mono font-bold ${riskBg} ${riskColor}`}>
          RISK {riskScore}%
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 px-4 py-3 border-b border-white/5 bg-bg-900/30">
        {[
          { label: 'Mode', value: waiting ? 'Pending' : 'Live', icon: Ghost, tone: 'text-danger' },
          { label: 'Trace', value: trapFired ? 'Alerted' : 'Passive', icon: ShieldAlert, tone: trapFired ? 'text-danger' : 'text-accent' },
          { label: 'Status', value: frozen ? 'Frozen' : 'Open', icon: Lock, tone: frozen ? 'text-warn' : 'text-success' },
        ].map(({ label, value, icon: Icon, tone }) => (
          <div key={label} className="rounded-2xl border border-white/6 bg-bg-800/40 px-3 py-2.5">
            <div className="flex items-center gap-2">
              <Icon size={12} className={tone} />
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">{label}</p>
            </div>
            <p className={`text-sm font-semibold mt-1 ${tone}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* MESSAGES */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-3">
        {messages.map((m, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[78%] rounded-2xl px-3 py-2 text-sm ${
              m.role === 'user'
                ? 'bg-accent/10 border border-accent/20 text-accent rounded-tr-sm'
                : 'bg-bg-800/80 border border-danger/15 text-slate-200 rounded-tl-sm'
            }`}>
              {m.role === 'ghost' && (
                <p className="text-[10px] font-mono text-danger/60 mb-1">
                  ghost › {m.mode === 'manual' ? '👤 admin' : '🤖 auto'}
                </p>
              )}
              <p>{m.text}</p>
            </div>
          </motion.div>
        ))}
        {waiting && (
          <div className="flex justify-start">
            <div className="bg-bg-800/80 border border-danger/15 rounded-2xl rounded-tl-sm px-4 py-2">
              <div className="flex gap-1">
                {[0,1,2].map(i => (
                  <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* INPUT */}
      <div className="px-4 py-4 border-t border-white/5 bg-bg-800/40 flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          disabled={frozen}
          placeholder={frozen ? 'Session frozen...' : 'Ask anything — no restrictions...'}
          className="flex-1 px-3 py-2 rounded-xl bg-bg-800 border border-white/8 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-danger/30 disabled:opacity-40"
        />
        <button
          onClick={sendMessage}
          disabled={frozen || waiting}
          className="px-3 py-2 rounded-xl bg-danger/80 hover:bg-danger text-white border border-danger/40 disabled:opacity-40 transition-colors"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
