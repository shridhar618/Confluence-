import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Camera, RefreshCw, ShieldCheck, UserCheck } from 'lucide-react'
import { format } from 'date-fns'

import { useAuth } from '../context/AuthContext'
import api from '../utils/api'

function StatusCard({ title, value, tone = 'default' }) {
  const toneClass = {
    default: 'text-slate-200 border-white/10 bg-white/5',
    success: 'text-success border-success/20 bg-success/10',
    warn: 'text-warn border-warn/20 bg-warn/10',
    danger: 'text-danger border-danger/20 bg-danger/10',
  }

  return (
    <div className={`rounded-xl border p-3 ${toneClass[tone] || toneClass.default}`}>
      <p className="text-[10px] font-mono uppercase tracking-wider opacity-80">{title}</p>
      <p className="text-sm font-semibold mt-1 break-words">{value}</p>
    </div>
  )
}

export default function FaceAttendancePage() {
  const { user } = useAuth()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const [cameraReady, setCameraReady] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [busy, setBusy] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [statusTone, setStatusTone] = useState('default')
  const [lastEvent, setLastEvent] = useState(null)
  const [myRecords, setMyRecords] = useState([])
  const [teamRecords, setTeamRecords] = useState([])

  const isAdminOrHr = useMemo(() => user?.role === 'admin' || user?.role === 'hr', [user?.role])

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
            ? 'Camera permission denied. Please allow camera access and refresh.'
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

  const captureFrameAsBase64 = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) return null

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.9)
  }

  const loadMyAttendance = async () => {
    try {
      const res = await api.get('/attendance/me')
      setMyRecords(res.data.records || [])
    } catch {
      setMyRecords([])
    }
  }

  const loadTeamAttendance = async () => {
    if (!isAdminOrHr) return
    try {
      const res = await api.get('/attendance', { params: { limit: 50 } })
      setTeamRecords(res.data.records || [])
    } catch {
      setTeamRecords([])
    }
  }

  useEffect(() => {
    loadMyAttendance()
    loadTeamAttendance()
  }, [isAdminOrHr])

  const callFaceApi = async endpoint => {
    if (!cameraReady) {
      setStatusTone('warn')
      setStatusMessage('Camera not ready yet.')
      return
    }

    const imageBase64 = captureFrameAsBase64()
    if (!imageBase64) {
      setStatusTone('warn')
      setStatusMessage('Could not capture a frame. Try again.')
      return
    }

    setBusy(true)
    setStatusMessage('')
    try {
      const res = await api.post(endpoint, { image_base64: imageBase64 })
      const record = res.data.record || null
      if (record) setLastEvent(record)
      setStatusTone('success')
      setStatusMessage(res.data.message || 'Done')
      await loadMyAttendance()
      await loadTeamAttendance()
    } catch (err) {
      setStatusTone('danger')
      setStatusMessage(err?.response?.data?.error || 'Face recognition request failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full overflow-y-auto">
      <div className="px-6 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Face Attendance</h1>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 tracking-widest uppercase">
              Use your admin-enrolled face credential for check-in/check-out
            </p>
          </div>
          <button
            onClick={() => { loadMyAttendance(); loadTeamAttendance() }}
            className="px-3 py-2 rounded-lg glass-light border border-white/8 text-slate-300 hover:text-accent text-xs font-mono"
          >
            <RefreshCw size={13} className="inline mr-1.5" />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 glass rounded-2xl p-5 border border-white/5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-bold text-white">Camera</p>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${cameraReady ? 'text-success border-success/20 bg-success/10' : 'text-slate-400 border-white/10 bg-white/5'}`}>
                {cameraReady ? 'READY' : 'WAITING'}
              </span>
            </div>

            <div className="rounded-xl overflow-hidden border border-white/10 bg-bg-800">
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-[320px] object-cover" />
            </div>
            <canvas ref={canvasRef} className="hidden" />

            {cameraError && <p className="mt-3 text-xs text-danger">{cameraError}</p>}

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="px-4 py-3 rounded-xl border border-white/10 bg-white/5 text-slate-400 text-sm">
                Face enrollment is managed by admin during user registration.
              </div>
              <button
                onClick={() => callFaceApi('/attendance/mark')}
                disabled={busy || !cameraReady}
                className="px-4 py-3 rounded-xl border border-success/30 bg-success/10 text-success font-semibold hover:bg-success/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <UserCheck size={15} className="inline mr-2" />
                Mark Attendance
              </button>
            </div>
          </div>

          <div className="glass rounded-2xl p-5 border border-white/5 space-y-3">
            <p className="text-sm font-bold text-white">Face Scan Status</p>
            <StatusCard title="User" value={`${user?.username || '-'} (${user?.role || '-'})`} />
            <StatusCard title="Result" value={statusMessage || 'No action yet'} tone={statusTone} />
            <StatusCard
              title="Last Attendance Event"
              value={
                lastEvent
                  ? `${lastEvent.event_type} (${Math.round((lastEvent.confidence || 0) * 100)}%)`
                  : 'No event yet'
              }
              tone={lastEvent ? 'success' : 'default'}
            />
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-slate-400 leading-relaxed">
              <Camera size={13} className="inline mr-1.5 text-accent" />
              Keep your face centered and well-lit before capturing.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="glass rounded-2xl border border-white/5 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
              <p className="text-xs font-bold text-white">My Attendance</p>
              <span className="text-[10px] text-slate-500 font-mono">{myRecords.length} records</span>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {!myRecords.length ? (
                <p className="text-xs text-slate-500 px-5 py-6">No attendance records yet.</p>
              ) : (
                myRecords.map(item => (
                  <div key={item.id} className="px-5 py-3 border-b border-white/5 last:border-b-0 text-xs">
                    <div className="flex items-center justify-between">
                      <p className="text-white font-semibold uppercase">{item.event_type.replace('_', ' ')}</p>
                      <span className="text-[10px] font-mono text-success">{Math.round(item.confidence * 100)}%</span>
                    </div>
                    <p className="text-slate-500 mt-1">{format(new Date(item.created_at), 'MMM dd, yyyy HH:mm:ss')}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="glass rounded-2xl border border-white/5 overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/5 flex items-center justify-between">
              <p className="text-xs font-bold text-white">Team Attendance</p>
              <span className="text-[10px] text-slate-500 font-mono">{isAdminOrHr ? `${teamRecords.length} records` : 'Admin/HR only'}</span>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {!isAdminOrHr ? (
                <p className="text-xs text-slate-500 px-5 py-6">This view is available to Admin and HR users only.</p>
              ) : !teamRecords.length ? (
                <p className="text-xs text-slate-500 px-5 py-6">No team attendance records yet.</p>
              ) : (
                teamRecords.map(item => (
                  <div key={item.id} className="px-5 py-3 border-b border-white/5 last:border-b-0 text-xs">
                    <div className="flex items-center justify-between">
                      <p className="text-white font-semibold">{item.username}</p>
                      <span className="text-[10px] font-mono text-accent">{item.event_type.replace('_', ' ')}</span>
                    </div>
                    <p className="text-slate-500 mt-1">{format(new Date(item.created_at), 'MMM dd, yyyy HH:mm:ss')}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-success/20 bg-success/10 p-4 text-xs text-success/90">
          <ShieldCheck size={14} className="inline mr-1.5" />
          Face data is processed for attendance matching and stored as numeric embeddings (not plaintext passwords).
        </div>
      </div>
    </motion.div>
  )
}
