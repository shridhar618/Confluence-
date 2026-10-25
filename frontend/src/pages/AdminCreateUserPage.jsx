import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle, Camera, CheckCircle2, KeyRound, ScanFace, Search, UserPlus, XCircle } from 'lucide-react'

import api from '../utils/api'
import { FALLBACK_ROLE_NAMES, getRoleMeta, groupRoles, isManagerRole } from '../utils/roles'

export default function AdminCreateUserPage() {
  const [roles, setRoles] = useState(FALLBACK_ROLE_NAMES)
  const [form, setForm] = useState({ username: '', role: 'intern' })
  const [checkForm, setCheckForm] = useState({ username: '', login_code: '' })
  const [roleSearch, setRoleSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [checkLoading, setCheckLoading] = useState(false)
  const [rolesLoading, setRolesLoading] = useState(true)
  const [cameraReady, setCameraReady] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [faceSnapshot, setFaceSnapshot] = useState('')
  const [error, setError] = useState('')
  const [checkError, setCheckError] = useState('')
  const [created, setCreated] = useState(null)
  const [checkResult, setCheckResult] = useState(null)

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const matchingRoles = roles.filter(role => {
    const needle = roleSearch.trim().toLowerCase()
    if (!needle) return true
    const meta = getRoleMeta(role.toLowerCase())
    return `${role} ${meta.category} ${meta.desc}`.toLowerCase().includes(needle)
  })
  const filteredRoles = matchingRoles.length ? matchingRoles : roles
  const groupedRoles = groupRoles(filteredRoles)
  const selectedRoleMeta = getRoleMeta(form.role)

  useEffect(() => {
    let active = true

    api.get('/roles')
      .then(res => {
        if (!active) return
        const nextRoles = (res.data?.roles || []).map(role => role.name).filter(Boolean)
        if (nextRoles.length) {
          setRoles(nextRoles)
          setForm(current => {
            if (nextRoles.some(role => role.toLowerCase() === current.role)) return current
            const defaultRole = nextRoles.find(role => role.toLowerCase() === 'intern') || nextRoles[0]
            return { ...current, role: defaultRole.toLowerCase() }
          })
        }
      })
      .finally(() => {
        if (active) setRolesLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let mounted = true

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        })
        streamRef.current = stream
        if (videoRef.current && mounted) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          setCameraReady(true)
          setCameraError('')
        }
      } catch (err) {
        setCameraError(
          err?.name === 'NotAllowedError'
            ? 'Camera permission denied. Allow access to capture the employee face credential.'
            : 'Unable to access camera on this device/browser.'
        )
      }
    }

    startCamera()
    return () => {
      mounted = false
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const captureFrame = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) return null

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.9)
  }

  const handleCaptureFace = () => {
    const imageBase64 = captureFrame()
    if (!imageBase64) {
      setError('Could not capture the employee face. Please retry.')
      return
    }
    setFaceSnapshot(imageBase64)
    setError('')
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const imageBase64 = faceSnapshot || captureFrame()
      if (!imageBase64) {
        setError('Capture the employee face before creating the account.')
        return
      }

      const res = await api.post('/admin/create-user', { ...form, image_base64: imageBase64 })
      setCreated(res.data)
      setForm(current => ({ ...current, username: '' }))
      setFaceSnapshot('')
    } catch (err) {
      setError(err.response?.data?.error || 'User creation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCodeCheck = async e => {
    e.preventDefault()
    setCheckLoading(true)
    setCheckError('')
    try {
      const res = await api.post('/admin/check-user-code', checkForm)
      setCheckResult(res.data)
    } catch (err) {
      setCheckResult(null)
      setCheckError(err.response?.data?.error || 'Code check failed')
    } finally {
      setCheckLoading(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 max-w-6xl space-y-6">
        <div>
          <h1 className="text-xl font-bold text-white">Admin User Access</h1>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">Create users, issue login codes, and bind face credentials during onboarding</p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="glass rounded-2xl p-6 border border-white/5 shadow-card">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                <UserPlus size={18} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Create User</h2>
                <p className="text-xs text-slate-500">The employee face credential is now mandatory during account creation.</p>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm mb-4">
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Username</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={e => setForm(current => ({ ...current, username: e.target.value }))}
                    className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 transition-all text-sm font-mono"
                    placeholder="new_user"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Find Role</label>
                  <div className="relative mb-2">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
                    <input
                      type="text"
                      value={roleSearch}
                      onChange={e => setRoleSearch(e.target.value)}
                      className="w-full pl-9 pr-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-accent/50 transition-all text-sm"
                      placeholder="Search roles like developer, finance, manager..."
                    />
                  </div>
                  <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Role</label>
                  <select
                    value={form.role}
                    onChange={e => setForm(current => ({ ...current, role: e.target.value }))}
                    disabled={rolesLoading}
                    className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white focus:outline-none focus:border-accent/50 transition-all text-sm disabled:opacity-60"
                  >
                    {Object.entries(groupedRoles).map(([category, categoryRoles]) => (
                      <optgroup key={category} label={category}>
                        {categoryRoles.map(role => (
                          <option key={role} value={role.toLowerCase()}>{role}</option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>
              </div>

              <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">Registration Summary</p>
                    <p className="text-xs text-slate-500">Quick preview before you issue the account.</p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-mono border ${
                    selectedRoleMeta.value === 'admin' ? 'text-purple-400 border-purple-400/20 bg-purple-400/10' :
                    selectedRoleMeta.value === 'hr' ? 'text-warn border-warn/20 bg-warn/10' :
                    selectedRoleMeta.value === 'intern' ? 'text-accent border-accent/20 bg-accent/10' :
                    'text-slate-300 border-white/10 bg-white/5'
                  }`}>
                    {selectedRoleMeta.badge}
                  </span>
                </div>
                <div className="grid gap-3 md:grid-cols-3 mt-4 text-sm">
                  <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                    <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Role Family</p>
                    <p className="text-white mt-1">{selectedRoleMeta.category}</p>
                  </div>
                  <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                    <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Access Type</p>
                    <p className="text-white mt-1">{isManagerRole(form.role) ? 'Manager Workspace' : 'Standard Workspace'}</p>
                  </div>
                  <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                    <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Generated Email</p>
                    <p className="text-white mt-1 break-all">{form.username ? `${form.username}@secureai.local` : 'username@secureai.local'}</p>
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-3">{selectedRoleMeta.desc}</p>
              </div>

              <div className="rounded-2xl border border-white/8 bg-bg-800/60 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-sm font-semibold text-white">Employee Face Credential</p>
                    <p className="text-xs text-slate-500">Capture the face now. This same face will be required for unlock and attendance.</p>
                  </div>
                  <span className={`text-[10px] font-mono px-2 py-1 rounded border ${cameraReady ? 'text-success border-success/20 bg-success/10' : 'text-slate-400 border-white/10 bg-white/5'}`}>
                    {cameraReady ? 'CAMERA READY' : 'CAMERA WAITING'}
                  </span>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <div className="space-y-3">
                    <div className="rounded-xl overflow-hidden border border-white/10 bg-black/30">
                      <video ref={videoRef} autoPlay playsInline muted className="w-full h-[280px] object-cover" />
                    </div>
                    <canvas ref={canvasRef} className="hidden" />
                    {cameraError && <p className="text-xs text-danger">{cameraError}</p>}
                    <button
                      type="button"
                      onClick={handleCaptureFace}
                      disabled={!cameraReady || loading}
                      className="w-full py-3 rounded-xl border border-accent/30 bg-accent/10 text-accent font-semibold hover:bg-accent/20 disabled:opacity-50"
                    >
                      <Camera size={15} className="inline mr-2" />
                      {faceSnapshot ? 'Capture Again' : 'Capture Face Credential'}
                    </button>
                  </div>

                  <div className="rounded-xl border border-dashed border-white/10 bg-black/20 p-3">
                    {faceSnapshot ? (
                      <img src={faceSnapshot} alt="Captured employee face" className="w-full h-[280px] object-cover rounded-lg" />
                    ) : (
                      <div className="h-[280px] rounded-lg bg-white/5 text-slate-500 text-sm flex items-center justify-center text-center px-6">
                        Captured face preview will appear here.
                      </div>
                    )}
                    <div className="mt-3 text-xs text-slate-500 flex items-center gap-2">
                      <ScanFace size={14} className="text-accent" />
                      {faceSnapshot ? 'Face credential ready to save with this user.' : 'Capture before creating the account.'}
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || rolesLoading || !cameraReady}
                className="w-full py-3 rounded-xl bg-accent text-bg-900 font-bold text-sm tracking-wide hover:bg-accent-dim transition-all disabled:opacity-50 shadow-glow"
              >
                {loading ? 'Creating user...' : 'Create User With Face Credential'}
              </button>
            </form>
          </div>

          <div className="glass rounded-2xl p-6 border border-white/5 shadow-card">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-purple-400/10 border border-purple-400/20 flex items-center justify-center text-purple-400">
                <KeyRound size={18} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-white">Issued Login Code</h2>
                <p className="text-xs text-slate-500">Share this once after the face credential is saved.</p>
              </div>
            </div>

            {created ? (
              <div className="space-y-4">
                <div className="rounded-xl bg-bg-800/80 border border-white/8 p-4">
                  <p className="text-xs text-slate-500 font-mono uppercase tracking-wider">Username</p>
                  <p className="text-white font-semibold mt-1">{created.user.username}</p>
                </div>
                <div className="rounded-xl bg-accent/10 border border-accent/20 p-4">
                  <p className="text-xs text-slate-500 font-mono uppercase tracking-wider">Employee Code / Password</p>
                  <p className="text-xl text-accent font-bold font-mono tracking-[0.25em] mt-2">{created.login_code}</p>
                </div>
                <div className="rounded-xl bg-success/10 border border-success/20 p-4 text-sm text-success">
                  Face credential saved successfully. The employee must now use the same face for unlock and attendance.
                </div>
              </div>
            ) : (
              <div className="rounded-xl bg-bg-800/70 border border-dashed border-white/10 p-5 text-sm text-slate-500">
                Create a user with a captured face to generate the login code here.
              </div>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-6 border border-white/5 shadow-card">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-warn/10 border border-warn/20 flex items-center justify-center text-warn">
              <Search size={18} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Employee Code Check</h2>
              <p className="text-xs text-slate-500">Verify whether an employee code matches the stored code.</p>
            </div>
          </div>

          {checkError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm mb-4">
              <AlertCircle size={14} />
              {checkError}
            </div>
          )}

          <form onSubmit={handleCodeCheck} className="grid gap-4 lg:grid-cols-[1fr_1fr_auto] items-end">
            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Username</label>
              <input
                type="text"
                value={checkForm.username}
                onChange={e => setCheckForm(current => ({ ...current, username: e.target.value }))}
                className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-warn/50 transition-all text-sm font-mono"
                placeholder="employee_username"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider mb-1.5">Employee Code</label>
              <input
                type="text"
                value={checkForm.login_code}
                onChange={e => setCheckForm(current => ({ ...current, login_code: e.target.value.toUpperCase() }))}
                className="w-full px-4 py-3 rounded-xl bg-bg-800 border border-white/8 text-white placeholder-slate-600 focus:outline-none focus:border-warn/50 transition-all text-sm font-mono tracking-[0.2em]"
                placeholder="CODE123456"
                required
              />
            </div>

            <button
              type="submit"
              disabled={checkLoading}
              className="px-5 py-3 rounded-xl bg-warn text-bg-900 font-bold text-sm tracking-wide hover:brightness-105 transition-all disabled:opacity-50"
            >
              {checkLoading ? 'Checking...' : 'Check Code'}
            </button>
          </form>

          {checkResult && (
            <div className={`mt-5 rounded-2xl p-5 border ${checkResult.valid ? 'bg-success/10 border-success/20' : 'bg-danger/10 border-danger/20'}`}>
              <div className="flex items-center gap-2 mb-3">
                {checkResult.valid ? <CheckCircle2 size={18} className="text-success" /> : <XCircle size={18} className="text-danger" />}
                <p className={`text-sm font-bold ${checkResult.valid ? 'text-success' : 'text-danger'}`}>{checkResult.message}</p>
              </div>
              <div className="grid gap-3 md:grid-cols-3 text-sm">
                <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Username</p>
                  <p className="text-white mt-1">{checkResult.user.username}</p>
                </div>
                <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Role</p>
                  <p className="text-white mt-1 uppercase">{checkResult.user.role}</p>
                </div>
                <div className="rounded-xl bg-bg-900/40 border border-white/8 p-3">
                  <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Status</p>
                  <p className={`mt-1 font-semibold ${checkResult.valid ? 'text-success' : 'text-danger'}`}>{checkResult.valid ? 'Matched' : 'Not Matched'}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
