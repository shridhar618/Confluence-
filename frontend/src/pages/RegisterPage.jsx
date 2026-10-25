import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { Shield, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../utils/api'
import { FALLBACK_ROLE_NAMES } from '../utils/roles'

export default function RegisterPage() {
  const { register } = useAuth()
  const [roles, setRoles] = useState(FALLBACK_ROLE_NAMES)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'intern' })
  const [loading, setLoading] = useState(false)
  const [rolesLoading, setRolesLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    api.get('/roles')
      .then(res => {
        if (!active) return
        const nextRoles = (res.data?.roles || []).map(role => role.name).filter(Boolean)
        if (nextRoles.length) {
          setRoles(nextRoles)
          setForm(current => {
            if (nextRoles.some(role => role.toLowerCase() === current.role)) {
              return current
            }
            const internRole = nextRoles.find(role => role.toLowerCase() === 'intern') || nextRoles[0]
            return { ...current, role: internRole.toLowerCase() }
          })
        }
      })
      .catch(() => {
        if (active) {
          setRoles(FALLBACK_ROLE_NAMES)
        }
      })
      .finally(() => {
        if (active) {
          setRolesLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      toast.success('Account created!')
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-900 grid-bg p-4">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-purple/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 border border-accent/30 mb-4 shadow-glow">
            <Shield size={24} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-slate-500 mt-1 text-sm">Join SecureAI Platform</p>
        </div>

        <div className="glass rounded-2xl p-8 shadow-card">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm mb-4"
            >
              <AlertCircle size={14} />{error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'username', label: 'Username', type: 'text', placeholder: 'john_doe' },
              { key: 'email', label: 'Email', type: 'email', placeholder: 'john@company.com' },
              { key: 'password', label: 'Password', type: 'password', placeholder: '••••••••' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">{label}</label>
                <input
                  type={type}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:shadow-glow transition-all text-sm font-mono"
                  placeholder={placeholder}
                  required
                />
              </div>
            ))}

            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Role</label>
              <select
                value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                disabled={rolesLoading}
                className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 transition-all text-sm disabled:opacity-60"
              >
                {roles.map(role => (
                  <option key={role} value={role.toLowerCase()}>{role}</option>
                ))}
              </select>
            </div>

            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              type="submit"
              disabled={loading || rolesLoading}
              className="w-full py-3 rounded-xl bg-accent text-bg-900 font-bold text-sm tracking-wide hover:bg-accent-dim transition-all disabled:opacity-50 shadow-glow"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </motion.button>
          </form>

          <p className="text-center text-slate-500 text-xs mt-4">
            Already have an account?{' '}
            <Link to="/login" className="text-accent hover:underline">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
