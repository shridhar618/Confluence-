import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [permissions, setPermissions] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [faceVerified, setFaceVerified] = useState(() => sessionStorage.getItem('face_verified') === '1')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      api.get('/auth/me')
        .then(res => {
          setUser(res.data.user)
          setPermissions(res.data.permissions ?? null)
        })
        .catch(() => { setToken(null); localStorage.removeItem('token') })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = useCallback(async (username, loginCode) => {
    const res = await api.post('/auth/login', { username, login_code: loginCode })
    const { token: t, user: u, permissions: p } = res.data
    localStorage.setItem('token', t)
    sessionStorage.removeItem('face_verified')
    api.defaults.headers.common['Authorization'] = `Bearer ${t}`
    setToken(t)
    setUser(u)
    setPermissions(p ?? null)
    setFaceVerified(false)
    return u
  }, [])

  const hasPermission = useCallback((permissionName) => {
    // Fail open (true) when permissions haven't loaded yet or the backend
    // didn't return them (e.g. older cached session) so the UI doesn't
    // flash-hide navigation before /auth/me resolves; the backend is the
    // real enforcement point regardless of what the sidebar shows.
    if (!permissions) return true
    return permissions.includes(permissionName)
  }, [permissions])

  const markFaceVerified = useCallback(() => {
    sessionStorage.setItem('face_verified', '1')
    setFaceVerified(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    sessionStorage.removeItem('face_verified')
    delete api.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
    setPermissions(null)
    setFaceVerified(false)
  }, [])

  return (
    <AuthContext.Provider value={{ user, permissions, hasPermission, token, loading, faceVerified, markFaceVerified, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
