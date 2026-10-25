import { useState } from 'react'
import { motion } from 'framer-motion'
import { Ghost, Shield, Radar, Eye, Sparkles } from 'lucide-react'
import GhostChat from '../components/GhostChat'
import GhostAdminPanel from '../components/GhostAdminPanel'

export default function GhostModePage() {
  const [view, setView] = useState('admin')   // 'admin' | 'user'

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-8 md:px-8 md:py-10 space-y-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/10 text-[10px] font-mono uppercase tracking-[0.28em] text-accent">
              <Radar size={12} />
              Active deception layer
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mt-4">Ghost Mode</h1>
            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest mt-2">
              AI Honeypot · Trap & Track Malicious Users
            </p>
            <p className="max-w-2xl text-sm text-slate-400 mt-3 leading-relaxed">
              Observe how suspicious users interact with the honeypot, then switch into the decoy view to preview the exact interface they see.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setView('admin')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-mono transition-colors ${
                view === 'admin'
                  ? 'bg-accent/10 border-accent/20 text-accent'
                  : 'bg-bg-800 border-white/8 text-slate-400'
              }`}
            >
              <Shield size={12} />Admin View
            </button>
            <button
              onClick={() => setView('user')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-mono transition-colors ${
                view === 'user'
                  ? 'bg-danger/10 border-danger/20 text-danger'
                  : 'bg-bg-800 border-white/8 text-slate-400'
              }`}
            >
              <Ghost size={12} />Honeypot Interface
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_0.9fr] gap-4">
          <div className="glass rounded-3xl border border-white/5 p-5 md:p-6">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${
                view === 'admin'
                  ? 'bg-accent/10 border-accent/20 text-accent'
                  : 'bg-danger/10 border-danger/20 text-danger'
              }`}>
                {view === 'admin' ? <Shield size={20} /> : <Ghost size={20} />}
              </div>
              <div className="flex-1">
                <p className="text-xs font-mono uppercase tracking-[0.24em] text-slate-500">
                  {view === 'admin' ? 'Operator console' : 'Target-facing shell'}
                </p>
                <h2 className="text-lg font-semibold text-white mt-2">
                  {view === 'admin' ? 'Monitor, intervene, and freeze sessions.' : 'Preview the decoy conversation flow.'}
                </h2>
                <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                  {view === 'admin'
                    ? 'Stay inside the security control room with live session state, risk levels, and manual takeover when a probe becomes suspicious.'
                    : 'Test the bait experience from the user side with the same minimal shell, misleading assistant framing, and trap escalation behavior.'}
                </p>
              </div>
            </div>
          </div>

          <div className="glass rounded-3xl border border-white/5 p-5 md:p-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-3">
              {[
                {
                  icon: Eye,
                  label: 'Live visibility',
                  value: 'Realtime',
                  tone: 'text-accent',
                },
                {
                  icon: Sparkles,
                  label: 'Ghost responses',
                  value: view === 'admin' ? 'Human + auto' : 'Decoy UI',
                  tone: 'text-warn',
                },
                {
                  icon: Radar,
                  label: 'Risk posture',
                  value: 'Progressive traps',
                  tone: 'text-danger',
                },
              ].map(({ icon: Icon, label, value, tone }) => (
                <div key={label} className="rounded-2xl border border-white/6 bg-bg-800/50 p-4">
                  <div className="flex items-center gap-2">
                    <Icon size={14} className={tone} />
                    <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">{label}</p>
                  </div>
                  <p className={`text-sm font-semibold mt-2 ${tone}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {view === 'admin' && <GhostAdminPanel />}
        {view === 'user' && (
          <div className="grid grid-cols-1 xl:grid-cols-[0.9fr_1.15fr] gap-6 items-start">
            <div className="glass rounded-3xl border border-white/5 p-5 md:p-6">
              <p className="text-[10px] font-mono text-danger/60 uppercase tracking-widest">
                Demo preview
              </p>
              <h2 className="text-xl font-semibold text-white mt-3">What the target user sees</h2>
              <p className="text-sm text-slate-400 mt-3 leading-relaxed">
                The honeypot should feel believable but not flashy. This panel now keeps the interface closer to the main product style while still looking like a slightly unsafe, unrestricted chat tool.
              </p>
              <div className="mt-5 space-y-3">
                {[
                  'Compact chat shell with persistent risk signal',
                  'More balanced spacing so the screen does not feel empty',
                  'Same visual language as the rest of the platform',
                ].map(item => (
                  <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/6 bg-bg-800/45 px-4 py-3">
                    <div className="w-2 h-2 rounded-full bg-danger" />
                    <p className="text-sm text-slate-300">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="max-w-3xl">
              <GhostChat username="demo_target" />
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
