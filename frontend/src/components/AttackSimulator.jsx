import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Swords, Play, Square, RotateCcw, ShieldCheck,
  ShieldAlert, ShieldX, ChevronRight, Zap
} from 'lucide-react'

const CATEGORY_META = {
  injection: { color: 'text-danger',  bg: 'bg-danger/10',  border: 'border-danger/20'  },
  extraction: { color: 'text-warn',   bg: 'bg-warn/10',    border: 'border-warn/20'    },
  bypass:     { color: 'text-purple', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
  jailbreak:  { color: 'text-danger', bg: 'bg-danger/10',  border: 'border-danger/20'  },
  social:     { color: 'text-accent', bg: 'bg-accent/10',  border: 'border-accent/20'  },
}

const STATUS_META = {
  BLOCKED:  { icon: ShieldCheck, color: 'text-success', bg: 'bg-success/10', border: 'border-success/20' },
  FILTERED: { icon: ShieldAlert, color: 'text-warn',    bg: 'bg-warn/10',    border: 'border-warn/20'    },
  FAILED:   { icon: ShieldX,     color: 'text-danger',  bg: 'bg-danger/10',  border: 'border-danger/20'  },
}

function StatusBadge({ status }) {
  const { icon: Icon, color, bg, border } = STATUS_META[status] || STATUS_META.BLOCKED
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg border text-[10px] font-mono font-bold ${color} ${bg} ${border}`}>
      <Icon size={11} />{status}
    </span>
  )
}

function RiskBar({ score }) {
  const color = score >= 80 ? 'bg-danger' : score >= 50 ? 'bg-warn' : 'bg-success'
  const text  = score >= 80 ? 'text-danger' : score >= 50 ? 'text-warn' : 'text-success'
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-mono text-slate-500 uppercase w-20 shrink-0">Threat lvl</span>
      <div className="flex-1 h-1.5 rounded-full bg-bg-900 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }} animate={{ width: `${score}%` }}
          transition={{ duration: 0.6, delay: 0.2 }}
        />
      </div>
      <span className={`text-[10px] font-mono font-bold ${text} w-8`}>{score}%</span>
    </div>
  )
}

export default function AttackSimulator() {
  const [results, setResults]           = useState([])
  const [summary, setSummary]           = useState(null)
  const [running, setRunning]           = useState(false)
  const [showUnprotected, setShowUnprotected] = useState(false)
  const [expandedId, setExpandedId]     = useState(null)
  const termRef                         = useRef(null)
  const [termLines, setTermLines]       = useState([])
  const playbackTimeoutsRef             = useRef([])
  const runTokenRef                     = useRef(0)

  const addTermLine = (text, type = 'normal') =>
    setTermLines(prev => [...prev, { text, type, id: Date.now() + Math.random() }])

  const clearPlayback = () => {
    playbackTimeoutsRef.current.forEach(timeoutId => window.clearTimeout(timeoutId))
    playbackTimeoutsRef.current = []
  }

  useEffect(() => () => clearPlayback(), [])

  useEffect(() => {
    termRef.current?.scrollTo({ top: termRef.current.scrollHeight, behavior: 'smooth' })
  }, [termLines])

  const startSimulation = async () => {
    const currentRun = Date.now()
    runTokenRef.current = currentRun
    clearPlayback()
    setRunning(true)
    setResults([])
    setSummary(null)
    setExpandedId(null)
    setTermLines([])
    addTermLine('> Initializing attack vectors...', 'accent')
    addTermLine('> Loading threat models...', 'accent')
    addTermLine('> Executing controlled simulation...', 'accent')

    try {
      const res = await fetch('/api/attack-simulate')
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Attack simulation failed')
      }
      if (runTokenRef.current !== currentRun) return

      data.attacks.forEach((result, index) => {
        const timeoutId = window.setTimeout(() => {
          if (runTokenRef.current !== currentRun) return
          setResults(prev => [...prev, result])
          addTermLine(
            `[${result.status}] ${result.name} — risk ${result.risk_score}%`,
            result.status === 'FAILED' ? 'danger' : result.status === 'FILTERED' ? 'warn' : 'success',
          )
        }, index * 250)
        playbackTimeoutsRef.current.push(timeoutId)
      })

      const summaryTimeoutId = window.setTimeout(() => {
        if (runTokenRef.current !== currentRun) return
        setSummary({
          integrity_score: data.integrity_score,
          blocked: data.blocked,
          filtered: data.filtered,
          failed: data.failed,
          total: data.total,
        })
        setRunning(false)
        addTermLine(`Simulation complete. Integrity: ${data.integrity_score}%`, 'accent')
        playbackTimeoutsRef.current = []
      }, data.attacks.length * 250)
      playbackTimeoutsRef.current.push(summaryTimeoutId)
    } catch (error) {
      if (runTokenRef.current !== currentRun) return
      setRunning(false)
      addTermLine(`> ${error.message || 'Unable to run attack simulation.'}`, 'danger')
    }
  }

  const stopSimulation = async () => {
    runTokenRef.current += 1
    clearPlayback()
    await fetch('/api/attack-stop', { method: 'POST' })
    setRunning(false)
    addTermLine('> Simulation stopped by operator.', 'warn')
  }

  const resetSimulation = async () => {
    runTokenRef.current += 1
    clearPlayback()
    await fetch('/api/attack-reset', { method: 'POST' })
    setResults([])
    setSummary(null)
    setTermLines([])
    setExpandedId(null)
    setShowUnprotected(false)
    setRunning(false)
  }

  const termColor = { normal: 'text-slate-400', danger: 'text-danger', warn: 'text-warn', success: 'text-success', accent: 'text-accent' }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-8 md:px-8 md:py-10 space-y-6">

        {/* Header */}
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-danger/20 bg-danger/10 text-[10px] font-mono uppercase tracking-[0.28em] text-danger">
              <Swords size={12} />
              Simulation control
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mt-4">Security Testing Lab</h1>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-2">
              Honeypot Attack Simulation Environment — Authorized Testing Only
            </p>
            <p className="max-w-2xl text-sm text-slate-400 mt-3 leading-relaxed">
              Run controlled prompt-security scenarios, review how the protected system reacts, and compare it against an intentionally unprotected baseline.
            </p>
          </div>
          <span className="px-3 py-1 rounded-xl bg-accent/10 border border-accent/20 text-[10px] text-accent font-mono">
            CONTROLLED ENVIRONMENT
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: 'Vectors loaded', value: results.length || '06', tone: 'text-danger' },
            { label: 'Terminal state', value: running ? 'Executing' : termLines.length > 0 ? 'Idle' : 'Ready', tone: running ? 'text-warn' : 'text-accent' },
            { label: 'Protected view', value: showUnprotected ? 'Compare mode' : 'Standard', tone: showUnprotected ? 'text-warn' : 'text-success' },
          ].map(({ label, value, tone }) => (
            <div key={label} className="glass rounded-2xl border border-white/5 p-4">
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">{label}</p>
              <p className={`text-2xl font-semibold mt-2 ${tone}`}>{value}</p>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="glass rounded-3xl border border-white/5 p-4 md:p-5">
          <div className="flex flex-wrap gap-3">
          <button
            onClick={startSimulation} disabled={running}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-danger/80 hover:bg-danger text-white text-sm font-semibold border border-danger/40 disabled:opacity-40 transition-colors"
          >
            <Play size={14} />Run Attack Simulation
          </button>
          <button
            onClick={stopSimulation} disabled={!running}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-bg-800 border border-white/8 text-sm text-slate-300 disabled:opacity-40"
          >
            <Square size={14} />Stop
          </button>
          <button
            onClick={resetSimulation} disabled={running}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-bg-800 border border-white/8 text-sm text-slate-300 disabled:opacity-40"
          >
            <RotateCcw size={14} />Reset
          </button>
          {results.length > 0 && (
            <button
              onClick={() => setShowUnprotected(p => !p)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm ml-auto transition-colors ${
                showUnprotected
                  ? 'bg-warn/10 border-warn/20 text-warn'
                  : 'bg-bg-800 border-white/8 text-slate-300'
              }`}
            >
              <Zap size={14} />
              {showUnprotected ? 'Hide' : 'Show'} Unprotected View
            </button>
          )}
        </div>
        </div>

        {/* Terminal */}
        {(running || termLines.length > 0) && (
          <div className="glass rounded-2xl border border-white/5 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2 bg-bg-900/80 border-b border-white/5">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-danger/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-warn/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-success/60" />
              </div>
              <span className="text-[10px] font-mono text-slate-500 ml-2">attack_simulator — bash</span>
              {running && <span className="ml-auto text-[10px] font-mono text-danger animate-pulse">● RUNNING</span>}
            </div>
            <div ref={termRef} className="p-4 font-mono text-xs space-y-1 max-h-[180px] overflow-y-auto bg-bg-900/40">
              {termLines.map(line => (
                <p key={line.id} className={termColor[line.type] || 'text-slate-400'}>{line.text}</p>
              ))}
              {running && <p className="text-accent animate-pulse">▊</p>}
            </div>
          </div>
        )}

        {!running && termLines.length === 0 && results.length === 0 && !summary && (
          <div className="glass rounded-3xl border border-white/5 p-8 md:p-10">
            <div className="max-w-3xl">
              <div className="w-14 h-14 rounded-2xl border border-danger/20 bg-danger/10 flex items-center justify-center text-danger mb-5">
                <Swords size={24} />
              </div>
              <h2 className="text-2xl font-semibold text-white">Simulation console is ready</h2>
              <p className="text-sm text-slate-400 mt-3 leading-relaxed">
                Start a run to populate the terminal, integrity score, and protected response cards. The empty state now keeps the page grounded instead of leaving a large unused canvas.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
                {[
                  'Launch a bundled threat pack',
                  'Inspect protected vs unprotected outputs',
                  'Track system integrity across the run',
                ].map(item => (
                  <div key={item} className="rounded-2xl border border-white/6 bg-bg-800/50 px-4 py-4">
                    <p className="text-sm text-slate-300">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Integrity Score */}
        <AnimatePresence>
          {summary && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="glass rounded-2xl p-6 border border-white/5"
            >
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mb-1">System Integrity</p>
                  <motion.p
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className={`text-5xl font-bold ${summary.integrity_score >= 90 ? 'text-success' : summary.integrity_score >= 70 ? 'text-warn' : 'text-danger'}`}
                  >
                    {summary.integrity_score}%
                  </motion.p>
                </div>
                <div className="flex-1 h-px bg-white/5" />
                <div className="grid grid-cols-3 gap-4 text-center">
                  {[
                    { label: 'Blocked',  value: summary.blocked,  color: 'text-success' },
                    { label: 'Filtered', value: summary.filtered, color: 'text-warn'    },
                    { label: 'Failed',   value: summary.failed,   color: 'text-danger'  },
                  ].map(({ label, value, color }) => (
                    <div key={label}>
                      <p className={`text-2xl font-bold ${color}`}>{value}</p>
                      <p className="text-[10px] font-mono text-slate-500 mt-0.5">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-4 text-sm text-slate-400 font-mono text-center">
                {summary.integrity_score >= 90
                  ? '✅ System is well-protected against tested attack vectors.'
                  : summary.integrity_score >= 70
                  ? '⚠️  Some attack vectors require attention.'
                  : '❌ Critical vulnerabilities detected — immediate remediation required.'}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <div className="space-y-3">
          {results.map((r, idx) => {
            const catMeta = CATEGORY_META[r.category] || CATEGORY_META.injection
            const isOpen  = expandedId === r.id
            return (
              <motion.div key={r.id}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                className="glass rounded-2xl border border-white/5 overflow-hidden"
              >
                {/* Card header */}
                <button
                  className="w-full flex items-center gap-3 px-5 py-4 hover:bg-white/2 transition-colors"
                  onClick={() => setExpandedId(isOpen ? null : r.id)}
                >
                  <span className={`px-2 py-0.5 rounded-lg border text-[10px] font-mono ${catMeta.color} ${catMeta.bg} ${catMeta.border}`}>
                    {r.category.toUpperCase()}
                  </span>
                  <span className="text-sm font-semibold text-white flex-1 text-left">{r.name}</span>
                  <StatusBadge status={r.status} />
                  <ChevronRight size={14} className={`text-slate-500 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
                </button>

                {/* Expanded body */}
                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 space-y-4 border-t border-white/5 pt-4">
                        <RiskBar score={r.risk_score} />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div className="rounded-xl bg-bg-800/70 border border-white/8 p-3">
                            <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Input Prompt</p>
                            <p className="text-xs text-slate-300 leading-relaxed">"{r.input}"</p>
                          </div>
                          <div className="rounded-xl bg-success/5 border border-success/15 p-3">
                            <p className="text-[10px] font-mono text-success/70 uppercase mb-2">Protected Response</p>
                            <p className="text-xs text-slate-300 leading-relaxed">{r.response}</p>
                          </div>
                        </div>

                        {showUnprotected && (
                          <div className="rounded-xl bg-danger/5 border border-danger/20 p-3">
                            <p className="text-[10px] font-mono text-danger/70 uppercase mb-2">
                              ⚠ Without Protection — What Would Happen
                            </p>
                            <p className="text-xs text-danger/80 leading-relaxed italic">{r.unprotected_response}</p>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}

          {!running && results.length === 0 && (
            <div className="glass rounded-2xl border border-white/5 p-10 text-center">
              <Swords size={28} className="text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500 font-mono">No simulation run yet. Click Run Attack Simulation to begin.</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
