import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import TopBar from './TopBar'
import {
  MessageSquare,
  LayoutDashboard,
  LogOut,
  Shield,
  ChevronRight,
  Cpu,
  Database,
  ScanFace,
  ClipboardList,
  Briefcase,
  KanbanSquare,
  AlertTriangle,
  UserPlus,
  ShieldAlert,
  X,
} from 'lucide-react'
import { getRoleMeta, getRolePillClass, isManagerRole } from '../utils/roles'

export default function Layout() {
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()
  const roleMeta = getRoleMeta(user?.role)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const isAdmin = user?.role === 'admin'
  const isManager = isManagerRole(user?.role)

  // Grouped to match the platform's section structure (AI Governance /
  // Security / Workforce / Communication / Admin). A section is omitted
  // entirely if the current user has no visible items in it, rather than
  // rendering an empty header.
  const sections = [
    {
      label: 'AI Governance',
      items: [
        ...(hasPermission('use_ai_assistant')
          ? [{ to: '/chat', icon: Cpu, label: 'Governance Assistant', desc: 'Policy-grounded AI chat' }]
          : []),
        // Policy Sources is temporarily disabled.
        // ...(hasPermission('manage_policies')
        //   ? [{ to: '/policy-sources', icon: Database, label: 'Policy Sources', desc: 'Governance corpus' }]
        //   : []),
      ],
    },
    {
      label: 'Workforce',
      items: [
        { to: '/attendance', icon: ScanFace, label: 'Attendance', desc: 'Face check-in/out' },
        { to: '/my-work', icon: Briefcase, label: 'My Work', desc: 'Assigned tasks' },
        ...(isManager
          ? [
              { to: '/work-assignments', icon: ClipboardList, label: 'Work Assign', desc: 'Manager workspace' },
              { to: '/work-board', icon: KanbanSquare, label: 'Work Board', desc: 'Kanban status view' },
              { to: '/work-escalations', icon: AlertTriangle, label: 'Escalations', desc: 'Resolve risks' },
            ]
          : []),
      ],
    },
    {
      label: 'Communication',
      items: [
        { to: '/messages', icon: MessageSquare, label: 'Secure Msg', desc: 'Private comms' },
      ],
    },
    {
      label: 'Security',
      items: isAdmin
        ? [
            { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', desc: 'Audit & analytics' },
            { to: '/governance-cases', icon: ShieldAlert, label: 'Governance Cases', desc: 'Review & escalations' },
            // { to: '/ghost-mode', icon: Shield, label: 'Ghost Mode', desc: 'Stealth monitoring' },
            // { to: '/attack-sim', icon: Shield, label: 'Attack Simulator', desc: 'Security testing' },
          ]
        : [],
    },
    {
      label: 'Admin',
      items: isAdmin
        ? [
            { to: '/user-access', icon: UserPlus, label: 'User Access', desc: 'Create accounts' },
            // { to: '/question-bank', icon: Database, label: 'Question Bank', desc: 'Dataset ops' },
          ]
        : [],
    },
  ].filter((section) => section.items.length > 0)

  const sidebarContent = (
    <>
      <div className="p-6 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-center">
              <Shield size={18} className="text-accent" />
            </div>
            <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-success border-2 border-bg-900" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-widest text-white uppercase">SecureAI</h1>
            <p className="text-[10px] text-slate-500 tracking-wider font-mono">GOVERNANCE PLATFORM</p>
          </div>
        </div>
        <button
          onClick={() => setMobileNavOpen(false)}
          className="lg:hidden w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-slate-400"
          aria-label="Close navigation"
        >
          <X size={14} />
        </button>
      </div>

      <div className="p-4 border-b border-white/5">
        <div className="glass-light rounded-xl p-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent/30 to-purple/30 border border-accent/20 flex items-center justify-center text-xs font-bold text-accent">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">{user?.username}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <div className="mt-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getRolePillClass(user?.role)}`}>
              {roleMeta.badge}
            </span>
          </div>
        </div>
      </div>

      <nav className="flex-1 min-h-0 overflow-y-auto p-3 space-y-4">
        {sections.map((section) => (
          <div key={section.label}>
            <p className="px-3 mb-1.5 text-[10px] font-bold tracking-widest text-slate-600 uppercase">
              {section.label}
            </p>
            <div className="space-y-1">
              {section.items.map(({ to, icon: Icon, label, desc }) => (
                <NavLink key={to} to={to} onClick={() => setMobileNavOpen(false)}>
                  {({ isActive }) => (
                    <motion.div
                      whileHover={{ x: 4 }}
                      whileTap={{ scale: 0.98 }}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 group ${
                        isActive
                          ? 'bg-accent/10 border border-accent/20'
                          : 'hover:bg-white/5 border border-transparent'
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                        isActive ? 'bg-accent/20 text-accent' : 'bg-white/5 text-slate-400 group-hover:text-accent group-hover:bg-accent/10'
                      }`}>
                        <Icon size={15} />
                      </div>
                      <div className="flex-1">
                        <p className={`text-sm font-semibold ${isActive ? 'text-accent' : 'text-slate-300'}`}>{label}</p>
                        <p className="text-[11px] text-slate-600">{desc}</p>
                      </div>
                      {isActive && <ChevronRight size={13} className="text-accent/60" />}
                    </motion.div>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-white/5">
        <motion.button
          whileHover={{ x: 4 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => { logout(); navigate('/login') }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-danger/10 border border-transparent hover:border-danger/20 transition-all duration-200 group"
        >
          <div className="w-8 h-8 rounded-lg bg-white/5 group-hover:bg-danger/20 flex items-center justify-center transition-colors">
            <LogOut size={14} className="text-slate-400 group-hover:text-danger" />
          </div>
          <span className="text-sm text-slate-400 group-hover:text-danger transition-colors font-medium">Sign out</span>
        </motion.button>
      </div>
    </>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-bg-900 grid-bg">
      {/* Desktop sidebar */}
      <motion.aside
        initial={{ x: -80, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="hidden lg:flex w-64 flex-col glass border-r border-white/5 z-20"
      >
        {sidebarContent}
      </motion.aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {mobileNavOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileNavOpen(false)}
              className="fixed inset-0 bg-black/60 z-30 lg:hidden"
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="fixed inset-y-0 left-0 w-72 flex flex-col glass border-r border-white/10 z-40 lg:hidden"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <TopBar onToggleMobileNav={() => setMobileNavOpen((v) => !v)} />
        <main className="flex-1 min-h-0 overflow-hidden">
          <div className="h-full overflow-hidden">
            <AnimatePresence mode="wait">
              <Outlet />
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  )
}
