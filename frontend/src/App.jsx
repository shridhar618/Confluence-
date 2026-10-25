import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import WelcomePage from './pages/WelcomePage'
import ChatPage from './pages/ChatPage'
import PrivateChatPage from './pages/PrivateChatPage'
import DashboardPage from './pages/DashboardPage'
import GovernanceCasesPage from './pages/GovernanceCasesPage'
import FaceAttendancePage from './pages/FaceAttendancePage'
import FaceUnlockPage from './pages/FaceUnlockPage'
import WorkAssignmentsPage from './pages/WorkAssignmentsPage'
import MyWorkPage from './pages/MyWorkPage'
import WorkBoardPage from './pages/WorkBoardPage'
import WorkEscalationsPage from './pages/WorkEscalationsPage'
import AdminCreateUserPage from './pages/AdminCreateUserPage'
import { isManagerRole } from './utils/roles'

function ProtectedRoute({ children, adminOnly = false, managerOnly = false }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="flex h-full items-center justify-center bg-bg-900">
      <div className="flex gap-2">
        {[0, 1, 2].map(i => (
          <div key={i} className="typing-dot" style={{ animationDelay: `${i * 0.2}s` }} />
        ))}
      </div>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && user.role !== 'admin') return <Navigate to="/chat" replace />
  if (managerOnly && !isManagerRole(user.role)) return <Navigate to="/my-work" replace />
  return children
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/welcome" replace /> : <LoginPage />} />
      <Route path="/register" element={<Navigate to="/login" replace />} />

      <Route path="/welcome" element={
        <ProtectedRoute>
          <WelcomePage />
        </ProtectedRoute>
      } />
      <Route path="/face-unlock" element={
        <ProtectedRoute>
          <FaceUnlockPage />
        </ProtectedRoute>
      } />

      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/welcome" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="messages" element={<PrivateChatPage />} />
        <Route path="attendance" element={<FaceAttendancePage />} />
        <Route path="my-work" element={<MyWorkPage />} />

        <Route path="work-assignments" element={
          <ProtectedRoute managerOnly>
            <WorkAssignmentsPage />
          </ProtectedRoute>
        } />

        <Route path="work-board" element={
          <ProtectedRoute managerOnly>
            <WorkBoardPage />
          </ProtectedRoute>
        } />

        <Route path="work-escalations" element={
          <ProtectedRoute managerOnly>
            <WorkEscalationsPage />
          </ProtectedRoute>
        } />

        <Route path="user-access" element={
          <ProtectedRoute adminOnly>
            <AdminCreateUserPage />
          </ProtectedRoute>
        } />

        {/* <Route path="ghost-mode" element={
          <ProtectedRoute adminOnly>
            <GhostModePage />
          </ProtectedRoute>
        } /> */}

        {/* <Route path="attack-sim" element={
          <ProtectedRoute adminOnly>
            <AttackSimPage />
          </ProtectedRoute>
        } /> */}

        {/* <Route path="question-bank" element={
          <ProtectedRoute adminOnly>
            <QuestionBankPage />
          </ProtectedRoute>
        } /> */}

        <Route path="dashboard" element={
          <ProtectedRoute adminOnly>
            <DashboardPage />
          </ProtectedRoute>
        } />

        <Route path="governance-cases" element={
          <ProtectedRoute adminOnly>
            <GovernanceCasesPage />
          </ProtectedRoute>
        } />

        {/* <Route path="policy-sources" element={
          <ProtectedRoute adminOnly>
            <PolicySourcesPage />
          </ProtectedRoute>
        } /> */}
      </Route>

      <Route path="*" element={<Navigate to="/welcome" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <div className="noise">
        <AppRoutes />
      </div>
    </AuthProvider>
  )
}
