import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertCircle, LockKeyhole, ScanFace } from 'lucide-react'

import { useAuth } from '../context/AuthContext'
import api from '../utils/api'

export default function FaceUnlockPage() {
  const { faceVerified, markFaceVerified } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const [cameraReady, setCameraReady] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const targetPath = location.state?.from || '/welcome'

  useEffect(() => {
    if (faceVerified) navigate(targetPath, { replace: true })
  }, [faceVerified, navigate, targetPath])

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
        }
      } catch (err) {
        setCameraError(
          err?.name === 'NotAllowedError'
            ? 'Camera permission denied. Please allow camera access and retry.'
            : 'Unable to access camera from this browser/device.'
        )
      }
    }

    startCamera()
    return () => {
      mounted = false
      if (streamRef.current) streamRef.current.getTracks().forEach(track => track.stop())
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

  const verifyFace = async () => {
    setError('')
    const imageBase64 = captureFrame()
    if (!imageBase64) {
      setError('Could not capture your face. Please retry.')
      return
    }
    setLoading(true)
    try {
      await api.post('/auth/face-verify', { image_base64: imageBase64 })
      markFaceVerified()
      navigate(targetPath, { replace: true })
    } catch (err) {
      setError(err?.response?.data?.error || 'Face verification failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-900 grid-bg p-4">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[30rem] h-[30rem] bg-accent/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="w-full max-w-xl glass rounded-2xl p-6 shadow-card border border-white/8"
      >
        <div className="text-center mb-5">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent/10 border border-accent/30 mb-3">
            <LockKeyhole size={24} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white">Face Unlock Required</h1>
          <p className="text-slate-500 mt-1 text-sm font-mono tracking-wide">Verify your face to access SecureAI</p>
        </div>

        <div className="rounded-xl overflow-hidden border border-white/10 bg-bg-800">
          <video ref={videoRef} autoPlay playsInline muted className="w-full h-[300px] object-cover" />
        </div>
        <canvas ref={canvasRef} className="hidden" />

        {cameraError && (
          <div className="mt-3 flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm">
            <AlertCircle size={14} />
            {cameraError}
          </div>
        )}
        {error && (
          <div className="mt-3 flex items-center gap-2 p-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-3">
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={verifyFace}
            disabled={!cameraReady || loading}
            className="flex-1 min-w-[14rem] py-3 rounded-xl bg-accent text-bg-900 font-bold text-sm tracking-wide hover:bg-accent-dim disabled:opacity-50 disabled:cursor-not-allowed shadow-glow"
          >
            <ScanFace size={15} className="inline mr-2" />
            {loading ? 'Verifying...' : 'Unlock With Face'}
          </motion.button>
        </div>

        <p className="mt-4 text-xs text-slate-500">
          Face enrollment is completed by admin when your account is created. If unlock fails because no face is enrolled, contact admin.
        </p>
      </motion.div>
    </div>
  )
}
