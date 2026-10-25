import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import api from '../utils/api'
import { getSocket, disconnectSocket } from '../utils/socket'
import { Send, MessageSquare, Circle, Loader } from 'lucide-react'
import { format } from 'date-fns'
import { getRoleMeta } from '../utils/roles'

export default function PrivateChatPage() {
  const { user, token } = useAuth()
  const [users, setUsers] = useState([])
  const [activeUser, setActiveUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [onlineIds, setOnlineIds] = useState([])
  const [typingUsers, setTypingUsers] = useState({})
  const [sending, setSending] = useState(false)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const bottomRef = useRef(null)
  const typingTimer = useRef(null)
  const socketRef = useRef(null)

  // Load users
  useEffect(() => {
    api.get('/users').then(r => setUsers(r.data.users)).catch(() => {})
  }, [])

  // Socket setup
  useEffect(() => {
    const socket = getSocket(token)
    socketRef.current = socket

    socket.on('online_users', ids => setOnlineIds(ids))
    socket.on('new_message', msg => {
      setMessages(prev => {
        if (prev.find(m => m.id === msg.id)) return prev
        return [...prev, msg]
      })
    })
    socket.on('user_typing', ({ user_id }) => {
      setTypingUsers(prev => ({ ...prev, [user_id]: true }))
    })
    socket.on('user_stop_typing', ({ user_id }) => {
      setTypingUsers(prev => { const n = { ...prev }; delete n[user_id]; return n })
    })

    return () => {
      socket.off('online_users')
      socket.off('new_message')
      socket.off('user_typing')
      socket.off('user_stop_typing')
    }
  }, [token])

  // Load conversation
  useEffect(() => {
    if (!activeUser) return
    setLoadingMsgs(true)
    api.get(`/messages/${activeUser.id}`)
      .then(r => setMessages(r.data.messages))
      .catch(() => {})
      .finally(() => setLoadingMsgs(false))
  }, [activeUser])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typingUsers])

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || !activeUser || sending) return
    setInput('')
    setSending(true)

    // Emit via socket for real-time
    socketRef.current?.emit('private_message', {
      token,
      receiver_id: activeUser.id,
      content,
    })

    // Also stop typing
    socketRef.current?.emit('stop_typing', { token, receiver_id: activeUser.id })

    setSending(false)
  }

  const handleInputChange = e => {
    setInput(e.target.value)
    // Typing indicator
    socketRef.current?.emit('typing', { token, receiver_id: activeUser?.id })
    clearTimeout(typingTimer.current)
    typingTimer.current = setTimeout(() => {
      socketRef.current?.emit('stop_typing', { token, receiver_id: activeUser?.id })
    }, 1500)
  }

  const filteredMessages = activeUser
    ? messages.filter(m =>
        (m.sender_id === user.id && m.receiver_id === activeUser.id) ||
        (m.sender_id === activeUser.id && m.receiver_id === user.id)
      )
    : []

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-full"
    >
      {/* User list sidebar */}
      <div className="w-64 flex flex-col border-r border-white/5 glass">
        <div className="px-4 py-4 border-b border-white/5">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <MessageSquare size={14} className="text-accent" />
            Secure Messaging
          </h2>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">
            {onlineIds.length} online
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {users.map(u => (
            <motion.div
              key={u.id}
              whileHover={{ x: 3 }}
              onClick={() => setActiveUser(u)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                activeUser?.id === u.id
                  ? 'bg-accent/10 border border-accent/20'
                  : 'hover:bg-white/5 border border-transparent'
              }`}
            >
              <div className="relative flex-shrink-0">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-bg-900 ${
                  u.role === 'admin' ? 'bg-purple-400' : u.role === 'hr' ? 'bg-warn' : u.role === 'intern' ? 'bg-accent' : 'bg-slate-500'
                }`}>
                  {u.username[0].toUpperCase()}
                </div>
                {onlineIds.includes(u.id) && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-success border-2 border-bg-900" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${activeUser?.id === u.id ? 'text-accent' : 'text-slate-300'}`}>
                  {u.username}
                </p>
                <p className="text-[10px] text-slate-600 font-mono uppercase">{u.role}</p>
              </div>
              {typingUsers[u.id] && (
                <div className="flex gap-0.5">
                  {[0,1,2].map(i => (
                    <div key={i} className="typing-dot w-1 h-1" style={{ animationDelay: `${i*0.2}s` }} />
                  ))}
                </div>
              )}
            </motion.div>
          ))}

          {users.length === 0 && (
            <div className="text-center py-8 text-slate-600 text-xs">
              No other users yet
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {activeUser ? (
          <>
            {/* Chat header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5 glass">
              <div className="relative">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-bg-900 ${
                  activeUser.role === 'admin' ? 'bg-purple-400' : activeUser.role === 'hr' ? 'bg-warn' : activeUser.role === 'intern' ? 'bg-accent' : 'bg-slate-500'
                }`}>
                  {activeUser.username[0].toUpperCase()}
                </div>
                {onlineIds.includes(activeUser.id) && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-success border-2 border-bg-900" />
                )}
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">{activeUser.username}</h3>
                <p className="text-[11px] text-slate-500 font-mono">
                  {onlineIds.includes(activeUser.id) ? (
                    <span className="text-success">● Online</span>
                  ) : (
                    <span>○ Offline</span>
                  )}
                  {' · '}{getRoleMeta(activeUser.role).label}
                </p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-1">
              {loadingMsgs && (
                <div className="flex justify-center py-8">
                  <Loader size={16} className="text-accent animate-spin" />
                </div>
              )}

              <AnimatePresence initial={false}>
                {filteredMessages.map(msg => {
                  const isMe = msg.sender_id === user.id
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 8, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ duration: 0.25 }}
                      className={`flex ${isMe ? 'justify-end' : 'justify-start'} mb-2`}
                    >
                      <div className={`max-w-[70%] px-4 py-2.5 rounded-2xl text-sm ${
                        isMe
                          ? 'bg-accent text-bg-900 font-medium rounded-br-sm'
                          : 'glass-light text-slate-200 rounded-bl-sm'
                      }`}>
                        <p>{msg.content}</p>
                        <p className={`text-[10px] mt-1 ${isMe ? 'text-bg-700/70' : 'text-slate-600'} font-mono`}>
                          {format(new Date(msg.timestamp), 'HH:mm')}
                        </p>
                      </div>
                    </motion.div>
                  )
                })}

                {typingUsers[activeUser?.id] && (
                  <motion.div
                    key="typing"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex justify-start"
                  >
                    <div className="glass-light rounded-2xl rounded-bl-sm px-4 py-3">
                      <div className="flex gap-1.5 items-center">
                        {[0,1,2].map(i => (
                          <div key={i} className="typing-dot" style={{ animationDelay: `${i*0.2}s` }} />
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {filteredMessages.length === 0 && !loadingMsgs && (
                <div className="text-center py-16 text-slate-600">
                  <MessageSquare size={32} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No messages yet</p>
                  <p className="text-xs mt-1">Start a secure conversation with {activeUser.username}</p>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="px-5 py-4 border-t border-white/5">
              <div className="flex gap-3 items-center">
                <input
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 transition-all text-sm font-mono"
                  placeholder={`Message ${activeUser.username}...`}
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={sendMessage}
                  disabled={!input.trim() || sending}
                  className="w-10 h-10 rounded-xl bg-accent text-bg-900 flex items-center justify-center disabled:opacity-40 hover:bg-accent-dim transition-all shadow-glow"
                >
                  <Send size={14} />
                </motion.button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center flex-col gap-4 text-slate-600">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center">
              <MessageSquare size={24} className="opacity-40" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-slate-400">Select a conversation</p>
              <p className="text-xs mt-1">Choose a user from the left to start messaging</p>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
