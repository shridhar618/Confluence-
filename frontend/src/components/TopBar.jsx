import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Bell, ChevronDown, LogOut, Menu } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getRoleMeta, getRolePillClass } from '../utils/roles'
import { getSocket } from '../utils/socket'
import api from '../utils/api'

const PAGE_TITLES = {
  '/chat': { title: 'Governance Assistant', desc: 'Policy-grounded AI chat with real-time risk scoring' },
  '/messages': { title: 'Secure Messaging', desc: 'Private, real-time internal communication' },
  '/attendance': { title: 'Attendance', desc: 'Face-verified check-in and check-out' },
  '/my-work': { title: 'My Work', desc: 'Tasks assigned to you' },
  '/work-assignments': { title: 'Work Assignments', desc: 'Manager workspace for task allocation' },
  '/work-board': { title: 'Work Board', desc: 'Kanban view of task status' },
  '/work-escalations': { title: 'Escalations', desc: 'Capacity and workload risk review' },
  '/user-access': { title: 'User Access', desc: 'Create accounts and assign roles' },
  '/dashboard': { title: 'Governance Dashboard', desc: 'Audit activity and risk analytics' },
  // '/question-bank': { title: 'Question Bank', desc: 'Governed Q&A dataset operations' },
  // '/ghost-mode': { title: 'Ghost Mode', desc: 'Controlled security intervention simulation' },
  // '/attack-sim': { title: 'Attack Simulator', desc: 'Safe, labeled security event generation' },
}

const SEARCH_TARGETS = [
  { to: '/chat', label: 'Governance Assistant', keywords: 'ai chat governance assistant' },
  { to: '/messages', label: 'Secure Messaging', keywords: 'messages chat private' },
  { to: '/attendance', label: 'Attendance', keywords: 'face attendance check in out' },
  { to: '/my-work', label: 'My Work', keywords: 'tasks work assignments' },
  { to: '/work-assignments', label: 'Work Assignments', keywords: 'manager assign tasks' },
  { to: '/work-board', label: 'Work Board', keywords: 'kanban board tasks' },
  { to: '/work-escalations', label: 'Escalations', keywords: 'risk escalation capacity' },
  { to: '/user-access', label: 'User Access', keywords: 'admin create user accounts' },
  { to: '/dashboard', label: 'Governance Dashboard', keywords: 'audit logs analytics dashboard' },
  // { to: '/question-bank', label: 'Question Bank', keywords: 'dataset questions answers' },
  // { to: '/ghost-mode', label: 'Ghost Mode', keywords: 'security stealth monitoring' },
  // { to: '/attack-sim', label: 'Attack Simulator', keywords: 'security testing simulation' },
]

function useOutsideClose(ref, onClose) {
  useEffect(() => {
    function handler(event) {
      if (ref.current && !ref.current.contains(event.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [ref, onClose])
}

export default function TopBar({ onToggleMobileNav }) {
  const { user, logout, token } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const roleMeta = getRoleMeta(user?.role)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifLoading, setNotifLoading] = useState(false)
  const [notifError, setNotifError] = useState(false)

  const searchRef = useRef(null)
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  useOutsideClose(searchRef, () => setSearchOpen(false))
  useOutsideClose(notifRef, () => setNotifOpen(false))
  useOutsideClose(profileRef, () => setProfileOpen(false))

  const currentPage = PAGE_TITLES[location.pathname] || { title: 'SecureAI', desc: '' }

  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return []
    const q = searchQuery.trim().toLowerCase()
    return SEARCH_TARGETS.filter(
      (item) => item.label.toLowerCase().includes(q) || item.keywords.includes(q)
    ).slice(0, 6)
  }, [searchQuery])

  const loadNotifications = async () => {
    setNotifLoading(true)
    setNotifError(false)
    try {
      const res = await api.get('/notifications', { params: { limit: 10 } })
      setNotifications(res.data.notifications || [])
      setUnreadCount(res.data.unread_count || 0)
    } catch {
      setNotifError(true)
    } finally {
      setNotifLoading(false)
    }
  }

  useEffect(() => {
    // Real unread-count polling as a fallback. The socket listener below is
    // the primary path; polling stays as a safety net for a dropped
    // connection, at a deliberately slow interval so it isn't doing the
    // real work when the socket is healthy.
    let cancelled = false
    async function poll() {
      try {
        const res = await api.get('/notifications/unread-count')
        if (!cancelled) setUnreadCount(res.data.unread_count || 0)
      } catch {
        // Silent: notification badge is a nice-to-have, not core flow.
      }
    }
    poll()
    const interval = setInterval(poll, 60000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  useEffect(() => {
    if (!token) return
    const socket = getSocket(token)
    const handler = (notification) => {
      setUnreadCount((count) => count + 1)
      // Prepend so an open dropdown updates live without a refetch.
      setNotifications((items) => [notification, ...items])
    }
    socket.on('notification', handler)
    return () => { socket.off('notification', handler) }
  }, [token])

  const handleOpenNotifications = () => {
    const next = !notifOpen
    setNotifOpen(next)
    setProfileOpen(false)
    if (next) loadNotifications()
  }

  const markAllRead = async () => {
    try {
      await api.post('/notifications/read-all')
      setNotifications((items) => items.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch {
      // no-op; user can retry
    }
  }

  return (
    <header className="h-16 flex items-center gap-4 px-6 border-b border-white/5 glass z-10 shrink-0">
      <button
        onClick={onToggleMobileNav}
        className="lg:hidden w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-slate-300 hover:text-accent hover:border-accent/30 transition-colors"
        aria-label="Toggle navigation"
      >
        <Menu size={16} />
      </button>

      <div className="min-w-0 hidden sm:block">
        <h2 className="text-sm font-bold text-white truncate">{currentPage.title}</h2>
        {currentPage.desc && <p className="text-[11px] text-slate-500 truncate">{currentPage.desc}</p>}
      </div>

      <div className="flex-1" />

      <div ref={searchRef} className="relative w-full max-w-xs hidden md:block">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); setSearchOpen(true) }}
          onFocus={() => setSearchOpen(true)}
          placeholder="Search modules..."
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-accent/40 focus:bg-white/[0.07] transition-colors"
        />
        <AnimatePresence>
          {searchOpen && filteredResults.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full mt-2 left-0 right-0 glass border border-white/10 rounded-xl shadow-card overflow-hidden"
            >
              {filteredResults.map((item) => (
                <button
                  key={item.to}
                  onClick={() => { navigate(item.to); setSearchQuery(''); setSearchOpen(false) }}
                  className="w-full text-left px-3 py-2.5 text-xs text-slate-300 hover:bg-accent/10 hover:text-accent transition-colors border-b border-white/5 last:border-0"
                >
                  {item.label}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div ref={notifRef} className="relative">
        <button
          onClick={handleOpenNotifications}
          className="relative w-9 h-9 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-slate-300 hover:text-accent hover:border-accent/30 transition-colors"
          aria-label="Notifications"
        >
          <Bell size={15} />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-danger text-[9px] font-bold text-white flex items-center justify-center border-2 border-bg-900">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
        <AnimatePresence>
          {notifOpen && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full mt-2 right-0 w-80 glass border border-white/10 rounded-xl shadow-card overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                <p className="text-xs font-bold text-white uppercase tracking-wider">Alerts</p>
                {notifications.length > 0 && (
                  <button onClick={markAllRead} className="text-[11px] text-accent hover:text-accent/70 transition-colors">
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifLoading && (
                  <div className="px-4 py-6 text-center text-xs text-slate-500">Loading...</div>
                )}
                {!notifLoading && notifError && (
                  <div className="px-4 py-6 text-center text-xs text-danger">Couldn't load alerts.</div>
                )}
                {!notifLoading && !notifError && notifications.length === 0 && (
                  <div className="px-4 py-8 text-center">
                    <p className="text-xs text-slate-500">No alerts yet</p>
                    <p className="text-[11px] text-slate-600 mt-1">Governance and security events will appear here</p>
                  </div>
                )}
                {!notifLoading && !notifError && notifications.map((n) => {
                  const clickable = Boolean(n.related_case_id)
                  const handleClick = async () => {
                    if (!n.is_read) {
                      try {
                        await api.post(`/notifications/${n.id}/read`)
                        setNotifications((items) => items.map(i => i.id === n.id ? { ...i, is_read: true } : i))
                        setUnreadCount((c) => Math.max(0, c - 1))
                      } catch {
                        // non-blocking: navigation still proceeds below
                      }
                    }
                    if (clickable) {
                      setNotifOpen(false)
                      navigate('/governance-cases')
                    }
                  }
                  return (
                    <div
                      key={n.id}
                      onClick={handleClick}
                      className={`px-4 py-3 border-b border-white/5 last:border-0 transition-colors ${n.is_read ? 'opacity-60' : ''} ${clickable || !n.is_read ? 'cursor-pointer hover:bg-white/[0.03]' : ''}`}
                    >
                      <p className="text-xs text-slate-200">{n.message}</p>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-[10px] text-slate-600 font-mono">
                          {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                        </p>
                        {clickable && <span className="text-[10px] text-accent font-semibold">View case →</span>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div ref={profileRef} className="relative">
        <button
          onClick={() => { setProfileOpen((v) => !v); setNotifOpen(false) }}
          className="flex items-center gap-2 pl-1.5 pr-2 py-1.5 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-colors"
        >
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent/30 to-purple/30 border border-accent/20 flex items-center justify-center text-[11px] font-bold text-accent">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <ChevronDown size={12} className="text-slate-500 hidden sm:block" />
        </button>
        <AnimatePresence>
          {profileOpen && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full mt-2 right-0 w-56 glass border border-white/10 rounded-xl shadow-card overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-white/5">
                <p className="text-sm font-semibold text-white truncate">{user?.username}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                <span className={`inline-flex items-center mt-2 px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getRolePillClass(user?.role)}`}>
                  {roleMeta.badge}
                </span>
              </div>
              <button
                onClick={() => { logout(); navigate('/login') }}
                className="w-full flex items-center gap-2 px-4 py-3 text-xs text-slate-400 hover:text-danger hover:bg-danger/10 transition-colors"
              >
                <LogOut size={13} />
                Sign out
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  )
}
