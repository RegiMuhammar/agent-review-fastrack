import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { getAuthToken } from '@/lib/auth'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'

function RootRedirect() {
  const token = getAuthToken()

  if (token) {
    return <Navigate to="/dashboard" replace />
  }

  return <Navigate to="/login" replace />
}

function ProtectedRoute() {
  const token = getAuthToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function GuestRoute() {
  const token = getAuthToken()

  if (token) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />

        <Route element={<GuestRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
