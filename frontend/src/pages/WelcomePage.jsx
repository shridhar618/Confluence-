import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useAnimation, useMotionValue, useTransform } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { ArrowRight, LogOut, Shield, Cpu, Lock, BarChart3, MessageSquare } from 'lucide-react'
import { getRoleMeta } from '../utils/roles'

// ─── Role config ────────────────────────────────────────────────────────────
const ROLE_META = {
  admin: {
    label: 'Administrator',
    badge: 'ADMIN ACCESS',
    color: '#a78bfa',
    glow: 'rgba(167,139,250,0.25)',
    accent: 'rgba(167,139,250,0.12)',
    tagline: 'Full system access · Audit logs · Governance controls',
  },
  hr: {
    label: 'HR Manager',
    badge: 'HR ACCESS',
    color: '#ffb703',
    glow: 'rgba(255,183,3,0.25)',
    accent: 'rgba(255,183,3,0.1)',
    tagline: 'People data · Compliance workflows · PII-safe AI',
  },
  intern: {
    label: 'Intern',
    badge: 'INTERN ACCESS',
    color: '#00e5ff',
    glow: 'rgba(0,229,255,0.25)',
    accent: 'rgba(0,229,255,0.1)',
    tagline: 'Governed AI access · Company knowledge · Secure comms',
  },
}

const FEATURE_CARDS = [
  { icon: Cpu, label: 'AI Chatbot', desc: 'Governed by RBAC policy' },
  { icon: Lock, label: 'Zero Trust', desc: 'Role-based filtering' },
  { icon: MessageSquare, label: 'Secure Msgs', desc: 'Encrypted real-time chat' },
  { icon: BarChart3, label: 'Audit Trail', desc: 'Every query logged' },
]

// ─── Floating orb component ──────────────────────────────────────────────────
function Orb({ x, y, size, color, delay, duration }) {
  return (
    <motion.div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: x, top: y, width: size, height: size,
        background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
        filter: 'blur(40px)',
      }}
      animate={{
        x: [0, 30, -20, 0],
        y: [0, -40, 20, 0],
        scale: [1, 1.15, 0.9, 1],
        opacity: [0.5, 0.8, 0.4, 0.5],
      }}
      transition={{
        duration, delay, repeat: Infinity,
        ease: 'easeInOut', repeatType: 'loop',
      }}
    />
  )
}

// ─── Animated grid lines ─────────────────────────────────────────────────────
function GridOverlay() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(0,229,255,0.04)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      {/* Diagonal sweep line */}
      <motion.div
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(105deg, transparent 40%, rgba(0,229,255,0.03) 50%, transparent 60%)',
          backgroundSize: '200% 200%',
        }}
        animate={{ backgroundPosition: ['200% 200%', '-200% -200%'] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

// ─── Particle dots ───────────────────────────────────────────────────────────
function Particles() {
  const dots = Array.from({ length: 28 }, (_, i) => ({
    id: i,
    x: `${(i * 37 + 5) % 100}%`,
    y: `${(i * 53 + 10) % 100}%`,
    delay: (i * 0.4) % 6,
    size: i % 3 === 0 ? 2 : 1.5,
  }))

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {dots.map(d => (
        <motion.div
          key={d.id}
          className="absolute rounded-full bg-cyan-400"
          style={{ left: d.x, top: d.y, width: d.size, height: d.size, opacity: 0 }}
          animate={{ opacity: [0, 0.6, 0], scale: [0.5, 1, 0.5] }}
          transition={{ duration: 4, delay: d.delay, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}
    </div>
  )
}

// ─── Feature card ────────────────────────────────────────────────────────────
function FeatureCard({ icon: Icon, label, desc, index, roleColor }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.1 + index * 0.08, duration: 0.5, ease: 'easeOut' }}
      whileHover={{ y: -4, scale: 1.03 }}
      className="flex flex-col items-center gap-2 px-5 py-4 rounded-2xl cursor-default"
      style={{
        background: 'rgba(13,18,32,0.6)',
        border: '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center"
        style={{ background: `${roleColor}18`, border: `1px solid ${roleColor}30` }}
      >
        <Icon size={16} style={{ color: roleColor }} />
      </div>
      <p className="text-xs font-bold text-white tracking-wide">{label}</p>
      <p className="text-[10px] text-slate-500 text-center leading-relaxed">{desc}</p>
    </motion.div>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────
export default function WelcomePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const role = user?.role || 'intern'
  const roleMeta = getRoleMeta(role)
  const fallbackMeta = ROLE_META.intern
  const meta = ROLE_META[role] || {
    label: roleMeta.label,
    badge: `${roleMeta.badge} ACCESS`,
    color: '#7dd3fc',
    glow: 'rgba(125,211,252,0.2)',
    accent: 'rgba(125,211,252,0.1)',
    tagline: `${roleMeta.desc} · Secure comms · Governed AI`,
  } || fallbackMeta

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const handleGetStarted = () => {
    navigate('/chat', { replace: true })
  }

  // Mouse-parallax on hero text
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const rotateX = useTransform(mouseY, [-300, 300], [4, -4])
  const rotateY = useTransform(mouseX, [-300, 300], [-4, 4])

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    mouseX.set(e.clientX - rect.left - rect.width / 2)
    mouseY.set(e.clientY - rect.top - rect.height / 2)
  }
  const handleMouseLeave = () => { mouseX.set(0); mouseY.set(0) }

  // Stagger container variants
  const container = {
    hidden: {},
    show: { transition: { staggerChildren: 0.1, delayChildren: 0.2 } },
  }
  const item = {
    hidden: { opacity: 0, y: 28, filter: 'blur(4px)' },
    show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
  }

  return (
    <div
      className="relative flex flex-col h-screen w-full overflow-hidden select-none"
      style={{ background: 'radial-gradient(ellipse at 60% 10%, #0d1628 0%, #080c14 55%, #050810 100%)' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {/* ── Ambient background ── */}
      <GridOverlay />
      <Particles />

      {/* Orbs */}
      <Orb x="5%"  y="10%" size={420} color="rgba(0,229,255,0.12)"   delay={0}   duration={14} />
      <Orb x="65%" y="-5%" size={500} color={`${meta.color}20`}      delay={2}   duration={18} />
      <Orb x="75%" y="60%" size={350} color="rgba(167,139,250,0.1)"  delay={1}   duration={16} />
      <Orb x="-5%" y="55%" size={300} color="rgba(0,229,255,0.08)"   delay={3}   duration={20} />

      {/* Vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(5,8,16,0.7) 100%)' }}
      />

      {/* ── Top bar ── */}
      <motion.header
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="relative z-10 flex items-center justify-between px-8 py-6"
      >
        {/* Logo mark */}
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(0,229,255,0.1)', border: '1px solid rgba(0,229,255,0.25)' }}
          >
            <Shield size={14} style={{ color: '#00e5ff' }} />
          </div>
          <span className="text-xs font-bold tracking-widest text-slate-400 uppercase">SecureAI</span>
        </div>

        {/* Logout */}
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 transition-all"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'rgba(255,77,109,0.4)'
            e.currentTarget.style.color = '#ff4d6d'
            e.currentTarget.style.background = 'rgba(255,77,109,0.08)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'
            e.currentTarget.style.color = ''
            e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
          }}
        >
          <LogOut size={12} />
          Sign out
        </motion.button>
      </motion.header>

      {/* ── Hero center ── */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 -mt-8">
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          style={{ perspective: 1200, rotateX, rotateY, transformStyle: 'preserve-3d' }}
          className="flex flex-col items-center text-center max-w-2xl mx-auto"
        >
          {/* Role badge pill */}
          <motion.div variants={item}>
            <motion.div
              initial={{ scale: 0.85 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
              style={{
                background: meta.accent,
                border: `1px solid ${meta.color}30`,
                boxShadow: `0 0 24px ${meta.glow}`,
              }}
            >
              <motion.div
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: meta.color }}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span
                className="text-[10px] font-bold tracking-[0.2em] uppercase font-mono"
                style={{ color: meta.color }}
              >
                {meta.badge}
              </span>
            </motion.div>
          </motion.div>

          {/* Main heading */}
          <motion.div variants={item} className="mb-3">
            <h1 className="text-[clamp(2.2rem,6vw,4.5rem)] font-extrabold leading-[1.05] tracking-tight text-white">
              Welcome back,
            </h1>
          </motion.div>

          {/* Username with gradient glow */}
          <motion.div variants={item} className="mb-6">
            <motion.h2
              className="text-[clamp(2.2rem,6vw,4.5rem)] font-extrabold leading-[1.05] tracking-tight"
              style={{
                background: `linear-gradient(135deg, ${meta.color} 0%, #ffffff 50%, ${meta.color} 100%)`,
                backgroundSize: '200% auto',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                filter: `drop-shadow(0 0 32px ${meta.glow})`,
              }}
              animate={{ backgroundPosition: ['0% center', '200% center'] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
            >
              {user?.username || 'User'}
            </motion.h2>
          </motion.div>

          {/* Platform name */}
          <motion.div variants={item} className="mb-3">
            <p className="text-lg font-semibold text-slate-300 tracking-wide">
              SecureAI Governance Platform
            </p>
          </motion.div>

          {/* Tagline */}
          <motion.div variants={item} className="mb-12">
            <p className="text-sm text-slate-500 tracking-wide font-mono">
              {meta.tagline}
            </p>
          </motion.div>

          {/* CTA button */}
          <motion.div variants={item} className="mb-16">
            <motion.button
              onClick={handleGetStarted}
              whileHover={{ scale: 1.04, y: -2 }}
              whileTap={{ scale: 0.97 }}
              className="relative group inline-flex items-center gap-3 px-8 py-4 rounded-2xl font-bold text-sm tracking-wide overflow-hidden"
              style={{
                background: `linear-gradient(135deg, ${meta.color}ee 0%, ${meta.color}99 100%)`,
                color: '#080c14',
                boxShadow: `0 8px 32px ${meta.glow}, 0 2px 8px rgba(0,0,0,0.4)`,
              }}
            >
              {/* Shimmer sweep */}
              <motion.span
                className="absolute inset-0 pointer-events-none"
                style={{
                  background: 'linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.35) 50%, transparent 70%)',
                  backgroundSize: '200% 100%',
                }}
                animate={{ backgroundPosition: ['-200% 0', '200% 0'] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'linear', repeatDelay: 1 }}
              />

              <span className="relative z-10 font-extrabold">Get Started</span>
              <motion.span
                className="relative z-10"
                animate={{ x: [0, 4, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
              >
                <ArrowRight size={16} />
              </motion.span>
            </motion.button>
          </motion.div>

          {/* Feature cards */}
          <div className="grid grid-cols-4 gap-3 w-full max-w-xl">
            {FEATURE_CARDS.map((card, i) => (
              <FeatureCard key={card.label} {...card} index={i} roleColor={meta.color} />
            ))}
          </div>
        </motion.div>
      </main>

      {/* ── Footer strip ── */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.6, duration: 0.8 }}
        className="relative z-10 flex items-center justify-center gap-6 px-8 py-5"
      >
        {['RBAC Governed', 'Zero Trust', 'Audit Logged', 'SOC 2 Ready'].map((tag, i) => (
          <div key={tag} className="flex items-center gap-1.5">
            {i > 0 && <span className="w-1 h-1 rounded-full bg-slate-700" />}
            <span className="text-[10px] font-mono text-slate-600 tracking-widest uppercase">{tag}</span>
          </div>
        ))}
      </motion.footer>
    </div>
  )
}
